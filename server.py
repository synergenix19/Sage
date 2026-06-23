from __future__ import annotations
import asyncio
import json
import logging
import hmac
import os
import pathlib
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from sage_poc.graph import build_graph
from sage_poc.config import RESPONDER_MODEL
from sage_poc.language import text_direction
from sage_poc.server_helpers import _build_state, _stale_skill_overrides, _void_unseen_offer
from sage_poc.llm import get_classifier
from sage_poc.skills.conformance import SCHEMA_CONFORMANCE, get_conformance_report

_log = logging.getLogger(__name__)
CRISIS_SIGNAL = "[[CRISIS_DETECTED]]"
AINVOKE_TIMEOUT_SECONDS: float = float(os.environ.get("AINVOKE_TIMEOUT_SECONDS", "30"))

# Gate: True once BGE-M3 warmup completes (or is intentionally skipped).
# /health/ready and /chat both check this; Railway healthcheck holds LB traffic until ready.
_bge_ready: bool = False


async def require_api_key(x_sage_api_key: str | None = Header(default=None)) -> None:
    _expected_key = os.environ.get("SAGE_API_KEY", "")
    if _expected_key and (
        x_sage_api_key is None
        or not hmac.compare_digest(x_sage_api_key, _expected_key)
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")


async def require_ready() -> None:
    if not _bge_ready:
        raise HTTPException(
            status_code=503,
            detail="Service warming up — BGE-M3 index not ready",
        )

_cors_origins_raw = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
_CORS_ORIGINS: list[str] = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]


def _warmup_bge_m3() -> None:
    from sage_poc.nodes.skill_select import _ensure_semantic_ready
    _ensure_semantic_ready()
    # Build S3 crisis phrase index at startup so it's ready before the first
    # request. Without this, index build runs under the 5s per-request timeout
    # on Railway CPU (no ANE), causing permanent S1-only degradation.
    from sage_poc.safety.s3_semantic import _ensure_s3_ready
    _ensure_s3_ready()


async def _warmup_task() -> None:
    """Run BGE-M3 warmup in background so the HTTP server starts immediately.

    Lifespan yielding before warmup completes means the port opens right away;
    /health/ready returns 503 while this task runs and 200 once it sets _bge_ready.
    Railway's healthcheck then polls a real HTTP response instead of getting
    connection-refused for the full 5-minute window (which caused staging failures
    on lower-CPU Railway instances where warmup takes > 5 minutes).

    This task also warms the OpenRouter TCP connection (classifier pool) before
    setting _bge_ready = True. Without this, the first real user call pays 4.7s
    of TCP/TLS cold-start regardless of model load time — the httpx pool has no
    established connection until the first actual request.

    The classifier warmup MUST complete before _bge_ready is set — this is what
    makes the Railway readiness probe (/health/ready) actually gate on a warm
    connection, not just a started process. If this call is moved after _bge_ready
    or into a separate fire-and-forget task, the readiness guarantee is broken.
    """
    global _bge_ready
    try:
        await asyncio.to_thread(_warmup_bge_m3)
        _log.info("[sage/startup] BGE-M3 warmup complete")
    except Exception as exc:
        # Keep _bge_ready = False; /health/ready stays 503; /chat stays gated.
        _log.error(
            "[sage/startup] BGE-M3 warmup failed — service is NOT ready: %s", exc
        )
        return

    # Warm the OpenRouter classifier TCP connection so the first real user does not
    # pay cold-start latency. Uses the same _ASYNC_HTTP_CLIENT pool that handles all
    # real LLM calls — a throwaway client here would warm a different pool and have
    # no effect on production latency.
    try:
        from sage_poc.llm import get_classifier
        from sage_poc.resilience import resilient_invoke
        await resilient_invoke(
            get_classifier(),
            [{"role": "user", "content": "ping"}],
            node="warmup",
        )
        _log.info("[sage/startup] classifier connection warmed")
    except Exception as exc:
        # Non-fatal: real calls will establish their own connection.
        # Log as WARNING — a cold first user call is a latency degradation, not a crash.
        _log.warning("[sage/startup] classifier warmup failed: %s; first user may see cold-start latency", exc)

    _bge_ready = True


async def _corpus_sync_task(pool) -> None:
    """Reconcile the on-disk knowledge corpus into pgvector on startup.

    Idempotent and fail-open: unchanged articles are skipped (no re-embed), so this
    is cheap on every boot; any failure logs a WARNING and leaves retrieval to
    abstain (never crashes startup). Waits for BGE-M3 warmup first because
    ingestion embeds each new/changed chunk with the same model.

    Disable with SAGE_SYNC_CORPUS=0. Prune DB-only articles with SAGE_CORPUS_PRUNE=1.
    """
    if os.environ.get("SAGE_SYNC_CORPUS", "1") == "0":
        _log.info("[sage/startup] corpus sync skipped (SAGE_SYNC_CORPUS=0)")
        return
    # Embeddings need the model loaded; wait for warmup (bounded).
    for _ in range(300):  # up to ~10 min at 2s
        if _bge_ready:
            break
        await asyncio.sleep(2)
    if not _bge_ready:
        _log.warning("[sage/startup] corpus sync skipped — BGE-M3 not ready in time")
        return
    try:
        from sage_poc.knowledge.sync import sync_corpus
        default_dir = pathlib.Path(__file__).resolve().parent / "data" / "knowledge_corpus"
        corpus_dir = os.environ.get("SAGE_CORPUS_DIR", str(default_dir))
        prune = os.environ.get("SAGE_CORPUS_PRUNE", "0") == "1"
        result = await sync_corpus(corpus_dir, pool, prune=prune)
        _log.info(
            "[sage/startup] corpus sync: ingested=%d skipped=%d pruned=%d chunks=%d locked_out=%s",
            result.ingested, result.skipped, result.pruned, result.chunks, result.locked_out,
        )
    except Exception as exc:
        _log.warning("[sage/startup] corpus sync failed (retrieval will abstain): %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bge_ready
    if os.environ.get("SAGE_WARMUP_BGE", "1") != "0":
        # Schedule warmup as a background task — server starts immediately.
        # /health/ready returns 503 until the task finishes and sets _bge_ready = True.
        asyncio.create_task(_warmup_task())
        _log.info("[sage/startup] BGE-M3 warmup started in background")
    else:
        _log.info("[sage/startup] BGE-M3 warmup skipped (SAGE_WARMUP_BGE=0)")
        _bge_ready = True  # intentionally unwarmed; allow traffic

    for _field, _info in SCHEMA_CONFORMANCE.items():
        _log.info("[sage/startup] schema %-42s → %s", _field, _info["status"])

    if os.environ.get("DATABASE_URL"):
        # Two connection objects:
        #   saver_pool — psycopg AsyncConnectionPool for AsyncPostgresSaver (checkpointing)
        #   asyncpg_pool — asyncpg pool for PostgresMemoryRepository (uses asyncpg directly)
        # setup() runs CREATE INDEX CONCURRENTLY which can't run inside a transaction, so we
        # bootstrap it via a single autocommit connection before handing off to the pool.
        db_url = os.environ["DATABASE_URL"]
        # CHECKPOINT_DATABASE_URL lets the checkpointer use a separate connection string
        # (typically PgBouncer transaction mode, port 6543) while the asyncpg pool for
        # PostgresMemoryRepository stays on session mode. When unset, both share db_url.
        checkpoint_url = os.environ.get("CHECKPOINT_DATABASE_URL", db_url)
        try:
            # setup() runs CREATE INDEX CONCURRENTLY which requires a stable session-level
            # connection and breaks through PgBouncer transaction pooling. Always connect
            # via db_url (session mode) even when CHECKPOINT_DATABASE_URL is set.
            async with await AsyncConnection.connect(
                db_url, autocommit=True, prepare_threshold=0, row_factory=dict_row
            ) as setup_conn:
                await AsyncPostgresSaver(setup_conn).setup()
            # prepare_threshold=None: disables psycopg prepared-statement cache so the
            # pool is safe under PgBouncer transaction mode (port 6543). Without this,
            # psycopg caches a PREPARE on one backend and the next request may land on a
            # different backend, raising "prepared statement does not exist".
            saver_pool = AsyncConnectionPool(
                conninfo=checkpoint_url,
                open=False,
                kwargs={"prepare_threshold": None},
            )
            await saver_pool.open()
            asyncpg_pool = await asyncpg.create_pool(
                db_url,
                min_size=1,
                max_size=5,
                max_inactive_connection_lifetime=300,  # recycle connections idle >5 min
            )
        except Exception as exc:
            _log.error("[sage/startup] database connection failed: %s", exc)
            app.state._db_pool = None
            app.state._graph = build_graph(checkpointer=None)
            yield
            return
        app.state._db_pool = asyncpg_pool
        saver = AsyncPostgresSaver(saver_pool)
        app.state._graph = build_graph(checkpointer=saver)
        _log.info("[sage/startup] checkpointer ready")
        # Auto-load/refresh the knowledge corpus once embeddings are warm.
        # Background + fail-open: never blocks readiness, never crashes startup.
        asyncio.create_task(_corpus_sync_task(asyncpg_pool))
        yield
        await saver_pool.close()
        await asyncpg_pool.close()
    else:
        _log.warning("[sage/startup] DATABASE_URL not set — running without persistence")
        app.state._db_pool = None
        app.state._graph = build_graph(checkpointer=None)
        yield


# Single instantiation — must come after lifespan definition
app = FastAPI(title="SageAI API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages:   list[Message]
    session_id: str
    user_id:    str | None = None
    # Ferry fields removed — all cross-turn state lives in the LangGraph checkpoint


class ExtractProfileRequest(BaseModel):
    session_id: str
    user_id:    str


class NameSessionRequest(BaseModel):
    session_id: str
    user_id:    str
    message:    str


@app.post("/chat")
async def chat(
    req: ChatRequest,
    _: None = Depends(require_api_key),
    _ready: None = Depends(require_ready),
) -> StreamingResponse:
    if not req.session_id or not req.session_id.strip():
        raise HTTPException(status_code=400, detail="session_id is required")
    if not req.messages or req.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="Last message must be from the user")

    state = _build_state(req)
    graph = app.state._graph

    # Session-resume staleness: park skill context if the checkpoint is too old.
    # Runs before ainvoke so nodes see a clean active_skill_id and stale_skill_id is set.
    # Non-fatal — any failure leaves state unchanged (skill context persists as-is).
    #
    # No asyncio.wait_for wrapper here: cancelling the aget coroutine mid-flight
    # causes psycopg's AsyncConnectionPool to discard rather than return the
    # connection (PgBouncer transaction-mode leaves it in an unclean state), leaking
    # one pool slot per turn under concurrent load and collapsing pool capacity.
    # aget is a single SELECT; it blocks at most until a pool slot is free, then
    # completes quickly and returns the connection cleanly.
    try:
        snap = await graph.checkpointer.aget(
            {"configurable": {"thread_id": req.session_id}}
        )
        if snap:
            checkpoint_values = snap.get("channel_values") or {}
            overrides = _stale_skill_overrides(checkpoint_values)
            state.update(overrides)
    except Exception as exc:
        _log.warning("[sage/chat] stale-skill check failed: %s", exc, exc_info=True)

    # Load therapeutic profile for L5 injection — non-fatal if DB is unavailable
    state["therapeutic_profile"] = None
    if app.state._db_pool and req.user_id:
        try:
            from sage_poc.memory.postgres_repository import PostgresMemoryRepository
            repo = PostgresMemoryRepository(app.state._db_pool)
            state["therapeutic_profile"] = await repo.get_therapeutic_profile(req.user_id)
        except Exception as exc:
            _log.warning("[sage/chat] therapeutic profile load failed: %s", exc)
    _request_start = time.monotonic()  # consumed by Tasks 3+4 (latency audit)
    try:
        result = await asyncio.wait_for(
            graph.ainvoke(
                state,
                config={"configurable": {"thread_id": req.session_id}},
            ),
            timeout=AINVOKE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        _log.error(
            "[sage/graph] ainvoke timed out after %.1fs for session %s",
            AINVOKE_TIMEOUT_SECONDS,
            req.session_id,
        )
        # S1-1b: the checkpoint may have persisted an offer the user never saw
        # (response is [[SERVER_ERROR]]). Void it so the next turn cannot promote
        # an unseen offer. Never raises (logged WARNING inside on failure).
        await _void_unseen_offer(graph, req.session_id)

        async def _timeout_err() -> AsyncGenerator[bytes, None]:
            yield b"[[SERVER_ERROR]]"

        return StreamingResponse(_timeout_err(), media_type="text/plain; charset=utf-8")
    except Exception as exc:
        _log.error("[sage/graph] invoke failed: %s", exc)
        # S1-1b compensating cleanup — see timeout branch above. Never raises.
        await _void_unseen_offer(graph, req.session_id)

        async def _err() -> AsyncGenerator[bytes, None]:
            yield b"\n[[SERVER_ERROR]]"

        return StreamingResponse(_err(), media_type="text/plain; charset=utf-8")

    path: list[str] = result.get("path") or []
    is_safe: bool = result.get("is_safe", True)
    response_text: str = result.get("response") or ""

    async def _body() -> AsyncGenerator[bytes, None]:
        if not is_safe:
            yield (CRISIS_SIGNAL + "\n").encode()
        for word in response_text.split():
            yield (word + " ").encode()

    return StreamingResponse(
        _body(),
        media_type="text/plain; charset=utf-8",
        headers={
            "X-Sage-Node-Path":             json.dumps(path),
            "X-Sage-Model":                 RESPONDER_MODEL,
            "X-Sage-Skill-Id":              result.get("active_skill_id") or result.get("completed_skill_id") or "",
            "X-Sage-Step-Id":               result.get("executed_step_id") or "",
            "X-Sage-Active-Step-Id":        result.get("active_step_id") or "",
            "X-Sage-Gate-Path":             result.get("gate_path") or "",
            "X-Sage-Crisis-Flags":          json.dumps(result.get("crisis_flags") or []),
            "X-Sage-Clinical-Flags":        json.dumps(result.get("clinical_flags") or []),
            "X-Sage-Emotional-Intensity":   str(result.get("emotional_intensity") or 0),
            "X-Sage-Crisis-State":          result.get("crisis_state") or "none",
            "X-Sage-Direction":             text_direction(result.get("detected_language")),
            "X-Sage-Distress-Trajectory":   json.dumps(result.get("distress_trajectory") or []),
            "X-Sage-Engagement-Trajectory": json.dumps(result.get("engagement_trajectory") or []),
            "X-Sage-Conversation-Summary":  result.get("conversation_summary") or "",
            "X-Sage-Intent":                result.get("primary_intent") or "",
            "X-Sage-Secondary-Intent":      result.get("secondary_intent") or "",
            "X-Sage-Semantic-Score":        str(result.get("semantic_score") or ""),
            "X-Sage-Prompt-Layers":         json.dumps(result.get("prompt_layers") or []),
            "X-Sage-Token-Usage":           json.dumps(result.get("token_usage") or {}),
            "X-Sage-Turn-Number":           str(result.get("turn_count") or 0),
        },
    )


@app.post("/extract-profile")
async def extract_profile(
    req: ExtractProfileRequest,
    _: None = Depends(require_api_key),
):

    if not app.state._db_pool:
        return {"status": "skipped", "detail": "no database"}

    graph = app.state._graph
    try:
        checkpoint = await graph.checkpointer.aget(
            {"configurable": {"thread_id": req.session_id}}
        )
    except Exception as exc:
        _log.error("[extract-profile] checkpoint fetch failed: %s", exc)
        return {"status": "error", "detail": "checkpoint unavailable"}

    if not checkpoint:
        return {"status": "skipped", "detail": "no checkpoint for session"}

    history = (checkpoint.get("channel_values") or {}).get("conversation_history", [])
    turn_count = (checkpoint.get("channel_values") or {}).get("turn_count", 0)
    clinical_flags = (checkpoint.get("channel_values") or {}).get("clinical_flags", []) or []

    from sage_poc.memory.profile_extractor import extract_session_profile
    from sage_poc.memory.postgres_repository import PostgresMemoryRepository

    repo = PostgresMemoryRepository(app.state._db_pool)
    existing = await repo.get_therapeutic_profile(req.user_id) or {}

    last_extraction_turn = existing.get("last_extraction_turn", 0)

    if turn_count - last_extraction_turn < 5:
        return {"status": "skipped", "detail": "fewer than 5 new turns since last extraction"}

    delta_history = history[last_extraction_turn * 2:]
    if len(delta_history) < 4:
        return {"status": "skipped", "detail": "insufficient delta"}

    profile = await extract_session_profile(delta_history, clinical_flags=clinical_flags)
    if not profile:
        return {"status": "error", "detail": "extraction failed"}

    session_count = existing.get("session_count", 0)
    mood_traj = list(existing.get("mood_trajectory", []))
    if profile.get("mood_score"):
        mood_traj.append({"session": session_count + 1, "mood_score": profile["mood_score"]})
        mood_traj = mood_traj[-20:]

    merged = {
        "effective_techniques": list(set(
            existing.get("effective_techniques", []) + profile.get("effective_techniques", [])
        )),
        "ineffective_techniques": list(set(
            existing.get("ineffective_techniques", []) + profile.get("ineffective_techniques", [])
        )),
        "distortion_patterns": list(set(
            existing.get("distortion_patterns", []) + profile.get("distortion_patterns", [])
        )),
        "disclosed_concerns": list(set(
            existing.get("disclosed_concerns", []) + profile.get("disclosed_concerns", [])
        )),
        "communication_style": profile.get("communication_style") or existing.get("communication_style"),
        "cultural_preferences": {
            **existing.get("cultural_preferences", {}),
            **profile.get("cultural_preferences", {}),
        },
        "mood_trajectory":          mood_traj,
        "total_skills_completed":   existing.get("total_skills_completed", 0) + profile.get("skills_completed", 0),
        "session_count":            session_count + 1,
        "last_extraction_turn":     turn_count,
    }

    await repo.upsert_therapeutic_profile(
        user_id=req.user_id,
        profile=merged,
        session_id=req.session_id,
    )
    return {"status": "ok", "turns_extracted": turn_count - last_extraction_turn}


@app.post("/name-session")
async def name_session(
    req: NameSessionRequest,
    _: None = Depends(require_api_key),
):

    if not app.state._db_pool:
        return {"status": "skipped", "detail": "no database"}

    row = await app.state._db_pool.fetchrow(
        "SELECT name FROM chat_sessions WHERE id = $1",
        req.session_id,
    )
    if not row or row["name"]:
        return {"status": "skipped", "detail": "already named"}

    llm = get_classifier()
    try:
        response = await llm.ainvoke([
            {"role": "user", "content": (
                f'Give this conversation a short title (3-5 words, no quotes, no punctuation):\n\n"{req.message}"'
            )},
        ])
        name = response.content.strip()[:60]
        if not name:
            name = req.message.strip()[:30]
    except Exception as exc:
        _log.warning("[name-session] LLM failed: %s", exc)
        name = req.message.strip()[:30]

    await app.state._db_pool.execute(
        "UPDATE chat_sessions SET name = $1, updated_at = now() WHERE id = $2",
        name,
        req.session_id,
    )
    return {"status": "ok", "name": name}


@app.get("/health/ready")
async def health_ready():
    """Railway healthcheck target. Returns 503 until BGE-M3 warmup completes.
    Configure in Railway: healthcheck path = /health/ready, timeout >= 120s.
    """
    if not _bge_ready:
        raise HTTPException(
            status_code=503,
            detail="Service warming up — BGE-M3 index not ready",
        )
    return {"status": "ready"}


@app.get("/health/schema-conformance")
async def health_schema_conformance():
    return get_conformance_report()
