from __future__ import annotations
import asyncio
import json
import logging
import hmac
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from sage_poc.graph import build_graph
from sage_poc.config import RESPONDER_MODEL
from sage_poc.server_helpers import _build_state

_log = logging.getLogger(__name__)
CRISIS_SIGNAL = "[[CRISIS_DETECTED]]"

_cors_origins_raw = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
_CORS_ORIGINS: list[str] = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]


def _warmup_bge_m3() -> None:
    from sage_poc.nodes.skill_select import _ensure_semantic_ready
    _ensure_semantic_ready()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await asyncio.to_thread(_warmup_bge_m3)
        _log.info("[sage/startup] BGE-M3 warmup complete")
    except Exception as exc:
        _log.warning("[sage/startup] BGE-M3 warmup failed: %s", exc)

    if os.environ.get("DATABASE_URL"):
        # Single pool shared by checkpointer + repository — prevents connection exhaustion
        # under Supabase connection limits. AsyncPostgresSaver accepts the pool directly.
        try:
            pool = await asyncpg.create_pool(os.environ["DATABASE_URL"])
        except Exception as exc:
            _log.error("[sage/startup] database connection failed: %s", exc)
            app.state._db_pool = None
            app.state._graph = build_graph(checkpointer=None)
            yield
            return
        app.state._db_pool = pool
        saver = AsyncPostgresSaver(pool)
        await saver.setup()  # idempotent: creates LangGraph checkpoint tables if missing
        app.state._graph = build_graph(checkpointer=saver)
        _log.info("[sage/startup] checkpointer ready")
        yield
        await pool.close()
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


@app.post("/chat")
async def chat(
    req: ChatRequest,
    x_sage_api_key: str | None = Header(default=None),
) -> StreamingResponse:
    _expected_key = os.environ.get("SAGE_API_KEY", "")
    if _expected_key and (
        x_sage_api_key is None
        or not hmac.compare_digest(x_sage_api_key, _expected_key)
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not req.session_id or not req.session_id.strip():
        raise HTTPException(status_code=400, detail="session_id is required")
    if not req.messages or req.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="Last message must be from the user")

    state = _build_state(req)

    # Load therapeutic profile for L5 injection
    if app.state._db_pool and req.user_id:
        from sage_poc.memory.postgres_repository import PostgresMemoryRepository
        repo = PostgresMemoryRepository(app.state._db_pool)
        state["therapeutic_profile"] = await repo.get_therapeutic_profile(req.user_id)
    else:
        state["therapeutic_profile"] = None

    graph = app.state._graph
    try:
        result = await graph.ainvoke(
            state,
            config={"configurable": {"thread_id": req.session_id}},
        )
    except Exception as exc:
        _log.error("[sage/graph] invoke failed: %s", exc)

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
            await asyncio.sleep(0.025)

    return StreamingResponse(
        _body(),
        media_type="text/plain; charset=utf-8",
        headers={
            "X-Sage-Node-Path":             json.dumps(path),
            "X-Sage-Model":                 RESPONDER_MODEL,
            "X-Sage-Skill-Id":              result.get("active_skill_id") or "",
            "X-Sage-Step-Id":               result.get("executed_step_id") or "",
            "X-Sage-Active-Step-Id":        result.get("active_step_id") or "",
            "X-Sage-Gate-Path":             result.get("gate_path") or "",
            "X-Sage-Crisis-Flags":          json.dumps(result.get("crisis_flags") or []),
            "X-Sage-Clinical-Flags":        json.dumps(result.get("clinical_flags") or []),
            "X-Sage-Emotional-Intensity":   str(result.get("emotional_intensity") or 0),
            "X-Sage-Crisis-State":          result.get("crisis_state") or "none",
            "X-Sage-Distress-Trajectory":   json.dumps(result.get("distress_trajectory") or []),
            "X-Sage-Engagement-Trajectory": json.dumps(result.get("engagement_trajectory") or []),
            "X-Sage-Conversation-Summary":  result.get("conversation_summary") or "",
            "X-Sage-Intent":                result.get("primary_intent") or "",
            "X-Sage-Semantic-Score":        str(result.get("semantic_score") or ""),
            "X-Sage-Prompt-Layers":         json.dumps(result.get("prompt_layers") or []),
            "X-Sage-Token-Usage":           json.dumps(result.get("token_usage") or {}),
            "X-Sage-Turn-Number":           str(result.get("turn_count") or 0),
        },
    )


@app.post("/extract-profile")
async def extract_profile(
    req: ExtractProfileRequest,
    x_sage_api_key: str | None = Header(default=None),
):
    _expected_key = os.environ.get("SAGE_API_KEY", "")
    if _expected_key and (
        x_sage_api_key is None
        or not hmac.compare_digest(x_sage_api_key, _expected_key)
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")

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

    profile = await extract_session_profile(delta_history)
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
