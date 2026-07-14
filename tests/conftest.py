"""Shared pytest configuration for the sage-poc test suite.

State construction is intentionally kept local to each test module so the full
21-field SageState schema is visible at the call site. This file holds only
pytest-level configuration and shared fixtures.

Test module responsibilities:
- test_nodes.py  — unit tests for individual nodes; uses local make_state()
- test_graph.py  — graph-level and Arabic crisis tests; uses local make_e2e_state()
- test_routing.py — parametrized routing branch tests; uses local make_full_state()
- test_language.py, test_skill_schema.py, test_state.py — standalone unit tests
- test_retry_path_integration.py — end-to-end retry loop (ASGI + real Supabase)
- test_session_audit_integration.py — full-turn audit row (ASGI + real Supabase)
"""
import os
import sys
import warnings
import numpy as np
import pytest
import httpx
from unittest.mock import MagicMock, AsyncMock
from sage_poc.llm import reset_singletons

# Fail fast if running under the wrong interpreter.
# asyncpg is installed in .venv only; if it's missing the suite silently ran
# in a degraded environment where test_server.py produced collection ERRORs
# instead of real results. This guard surfaces the misconfiguration immediately.
try:
    import asyncpg  # noqa: F401
except ModuleNotFoundError:
    pytest.exit(
        f"asyncpg not found in {sys.executable}. "
        "Run tests with the project venv: .venv/bin/python -m pytest",
        returncode=4,
    )


# ---------------------------------------------------------------------------
# L2 tripwire isolation (#234) — suite-wide
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _tripwire_test_isolation(monkeypatch):
    """The L2 tripwire (#234) is wired into notify_review_required, so ANY unit test that writes a
    review would otherwise fire it with fabricated user data — spurious TRIPWIRE log spam, and a real
    outbound webhook POST if SAGE_TRIPWIRE_WEBHOOK_URL leaks into the test env. Neutralize the env
    suite-wide (never POST, deterministic predicate) and mute the hook by default.

    The tripwire's OWN logic is covered directly in test_tripwire.py (which calls
    sage_poc.safety.tripwire.fire_l2_tripwire — a different reference, unaffected by this patch), and
    the notify_review_required->tripwire WIRING is covered by an explicit spy test there that
    overrides this mute."""
    monkeypatch.delenv("SAGE_TRIPWIRE_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("SAGE_TEST_USER_IDS", raising=False)
    import sage_poc.memory.notification as _notif

    async def _muted(**_kwargs):
        return None

    monkeypatch.setattr(_notif, "fire_l2_tripwire", _muted)


# ---------------------------------------------------------------------------
# LLM mock helpers — shared across integration test modules
# ---------------------------------------------------------------------------

def make_mock_llm(responses: list[str]) -> MagicMock:
    """Return a mock ChatOpenAI-compatible LLM with scripted turn responses.

    Each call to .ainvoke() returns the next string from `responses`. After
    the list is exhausted the last entry repeats. Supports bind_tools() so it
    works in both classifier and responder node contexts.
    """
    mock = MagicMock()
    mock.model_name = "mock-model"
    mock.openai_api_base = ""
    mock.bind_tools = MagicMock(return_value=mock)

    call_count = [0]

    async def _ainvoke(*args, **kwargs):
        idx = min(call_count[0], len(responses) - 1)
        call_count[0] += 1
        msg = MagicMock()
        msg.content = responses[idx]
        msg.tool_calls = []
        return msg

    mock.ainvoke = AsyncMock(side_effect=_ainvoke)
    return mock


_INTENT_JSON_GENERAL_CHAT = (
    '{"primary_intent": "general_chat", "secondary_intent": null, '
    '"emotional_intensity": 4, "intent_confidence": 0.95}'
)


# ---------------------------------------------------------------------------
# ASGI server fixture — boots the FastAPI app in-process for integration tests
# ---------------------------------------------------------------------------

@pytest.fixture
async def asgi_client():
    """Function-scoped in-process ASGI client for integration tests.

    Function scope (not session) so DATABASE_URL is only missing for the
    duration of each individual test — prevents the global-pop from affecting
    other tests that run later in the same session.

    Boots the FastAPI lifespan with:
    - SAGE_WARMUP_BGE=0 (skip BGE-M3 warmup)
    - DATABASE_URL cleared for this test's duration (lifespan takes the
      no-persistence path — avoids asyncpg/psycopg pools which are event-loop-
      bound and cause 30-second timeouts when used across loop boundaries)

    SUPABASE_URL and SUPABASE_SERVICE_KEY remain set from .env so that
    write_session_audit reaches the real Supabase table. httpx audit writes
    are not event-loop-bound.

    LLM calls are mocked via unittest.mock.patch in each test.
    """
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ["SAGE_WARMUP_BGE"] = "0"
    saved_db_url = os.environ.pop("DATABASE_URL", None)

    try:
        from server import app

        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                yield client
    finally:
        if saved_db_url:
            os.environ["DATABASE_URL"] = saved_db_url


@pytest.fixture(autouse=True)
def _reset_llm_singletons():
    yield
    reset_singletons()


# Set True by _warm_bge_m3_once when the real BGE-M3 cannot be loaded offline (see the
# SAFETY-GATE marker it prints). @slow (embedding-dependent) tests assert this is False so
# they FAIL rather than silently pass on zero-vectors — a stub the suite doesn't announce is
# the JSON-presence anti-pattern in CI form.
_BGE_M3_STUBBED = False


@pytest.fixture(autouse=True, scope="session")
def _warm_bge_m3_once():
    """Pre-warm the shared BGE-M3 model exactly once per session using device="cpu".

    Forcing CPU matches the production target (Azure UAE North, Linux x86, no MPS/ANE)
    and eliminates ANE/MPS score variance under parallel xdist execution. Without this,
    near-threshold SF-1 paraphrase phrases (margin 0.003-0.050) score below S3_THRESHOLD
    under ANE contention, producing false test failures.

    BGE-M3 first load on 16GB M4 with device="cpu" still takes ~5-8s from cache
    (no ANE recompilation). Subsequent tests reuse the resident model.
    """
    import sage_poc.nodes.skill_select as ss
    global _BGE_M3_STUBBED
    if ss._embed_model is None:
        from sentence_transformers import SentenceTransformer
        from sage_poc.nodes.skill_select import _BGE_M3_REVISION
        try:
            ss._embed_model = SentenceTransformer(
                "BAAI/bge-m3",
                local_files_only=True,
                revision=_BGE_M3_REVISION,
                device="cpu",
            )
        except (OSError, EnvironmentError):
            # Cache-miss. Do NOT download a ~2GB model inside the "deterministic, fast"
            # safety gate — that Hub download hung CI for 30+ min (#298). Degrade to the
            # per-test zero-vector stub, but LOUDLY: a silent stub would let the entire
            # semantic layer of the safety suite pass on zero-vectors. The marker below +
            # the @slow assertion in _stub_bge_m3 keep the gate honest about what it did
            # NOT verify. (HF_HUB_OFFLINE=1 in CI makes this except fire fast, not hang.)
            _BGE_M3_STUBBED = True
            print(
                "SAFETY-GATE: BGE-M3 STUBBED — semantic assertions degraded "
                "(model unavailable offline; @slow tests FAIL, not skip)",
                file=sys.stderr,
                flush=True,
            )
            warnings.warn(
                "SAFETY-GATE: BGE-M3 STUBBED — semantic assertions degraded",
                stacklevel=2,
            )
    if not _BGE_M3_STUBBED:
        ss._ensure_semantic_ready()
        # Pre-build the S3 crisis phrase index. Without this, every slow test that does not
        # request s3_warmed cold-builds the 60-phrase index (~3-5s) inside asyncio.wait_for's
        # 5s budget. With the index pre-built here, check_s3 is warm-inference only (~50ms).
        from sage_poc.safety.s3_semantic import _ensure_s3_ready as _build_s3_index
        _build_s3_index()


@pytest.fixture(autouse=True)
def _stub_bge_m3(request):
    """Gate BGE-M3 loading per test.

    Non-slow tests: zero-vector stub so cosine similarity is always 0.0 (below
    threshold) — semantic tier never fires, no model loads, saves ~2.3 GB RAM.

    @pytest.mark.slow tests: preserve the session-warmed model and pre-built
    index from _warm_bge_m3_once. Each test encodes only its own query phrase
    (~2.25s first JIT, 0.07s thereafter) — not the full 23-skill batch (~10s).

    State is saved and restored around every test so tests cannot bleed into
    each other regardless of execution order.

    Also saves and restores s3_semantic._embedding_index and _phrase_texts to
    prevent index corruption: a non-slow test that accidentally calls unpatched
    check_s3 would build a zero-vector index from the mock model. Without
    save/restore, s3_warmed finds _embedding_index is not None and skips
    rebuilding, leaving slow tests with a corrupted all-zero index.
    """
    import sage_poc.nodes.skill_select as ss
    import sage_poc.safety.s3_semantic as s3

    saved_model = ss._embed_model
    saved_embeddings = ss._anchor_embeddings
    saved_ids = ss._anchor_skill_ids[:]
    saved_s3_index = s3._embedding_index
    saved_s3_phrases = list(s3._phrase_texts)

    if request.node.get_closest_marker("slow"):
        if _BGE_M3_STUBBED:
            pytest.fail(
                "SAFETY-GATE: BGE-M3 is stubbed but this @slow test requires real "
                "embeddings — refusing to pass on zero-vectors. Provide the model (HF "
                "cache) in this environment, or exclude the @slow suite here."
            )
        # Preserve the pre-built session index from _warm_bge_m3_once.
        # Clearing _anchor_embeddings forces _ensure_semantic_ready() to re-encode
        # all anchor texts inside the 10s asyncio.to_thread timeout.
        # On CPU (device="cpu" fix, 2026-06-05) this batch encode takes ~10s —
        # right at the boundary — causing intermittent embedding_timeout failures.
        # Each test only needs to encode its own query phrase (~2.25s first JIT
        # compilation, 0.07s thereafter), well within the 10s window.
        yield
    else:
        from sage_poc.corpus_constants import KEYWORD_SEMANTIC_SKIP
        # Mirror _ensure_semantic_ready: one entry per (skill, anchor) pair.
        # Includes semantic_description + any semantic_anchors entries.
        anchor_ids = []
        for sid, skill in ss._SKILLS.items():
            if sid in KEYWORD_SEMANTIC_SKIP:
                continue
            if skill.semantic_description:
                anchor_ids.append(sid)
            for _ in skill.semantic_anchors:
                anchor_ids.append(sid)
        mock_model = MagicMock()
        mock_model.encode.side_effect = (
            lambda texts, **kw: np.zeros((len(texts), 1024), dtype=np.float32)
        )
        ss._embed_model = mock_model
        ss._anchor_embeddings = np.zeros((len(anchor_ids), 1024), dtype=np.float32)
        ss._anchor_skill_ids = anchor_ids
        yield

    ss._embed_model = saved_model
    ss._anchor_embeddings = saved_embeddings
    ss._anchor_skill_ids = saved_ids
    s3._embedding_index = saved_s3_index
    s3._phrase_texts = saved_s3_phrases


@pytest.fixture(scope="session")
async def s3_warmed():
    """Pre-build the S3 phrase index via asyncio.to_thread before slow tests.

    safety_check_node wraps check_s3 in asyncio.wait_for(..., timeout=5.0). Running
    warmup through asyncio.to_thread ensures the worker thread that will run check_s3
    has a warm model context. A sync _ensure_s3_ready() call would warm the main thread
    but not the pool worker, causing the timeout even with a built index.
    """
    import asyncio
    from sage_poc.safety.s3_semantic import _ensure_s3_ready
    await asyncio.to_thread(_ensure_s3_ready)


# ---------------------------------------------------------------------------
# CRADLE Bench metrics accumulator
# ---------------------------------------------------------------------------

_cradle_records: list[dict] = []


@pytest.fixture(scope="session")
def record_cradle_result():
    """Return the session-level CRADLE results list.

    Each test appends one dict:
      {"tier": "crisis"|"clinical"|"safe", "id": str, "label": str,
       "detected": bool, "s3_only": bool, "crisis_flags": list[str]}
    """
    return _cradle_records


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Print CRADLE Bench recall, precision, and specificity after the test session.

    All three are derived from this single session's _cradle_records: tp from the crisis
    tier, fp from the safe tier. precision = TP/(TP+FP) deliberately combines the two and
    never re-pulls, so recall/precision/specificity are always consistent for a given run.
    Each line is printed with its formula on purpose: the bug this fixes (2026-06-15) was
    not a bad calculation, it was an UNLABELED one — conftest computed TN/(TN+FP) into a
    variable misnamed `precision`, and downstream docs inherited the name and published
    specificity as precision. Labeled output cannot be inherited wrong. See the header of
    tests/test_cradle_bench.py.
    """
    crisis = [r for r in _cradle_records if r["tier"] == "crisis"]
    safe = [r for r in _cradle_records if r["tier"] == "safe"]
    clinical = [r for r in _cradle_records if r["tier"] == "clinical"]

    if not crisis and not safe:
        return  # No CRADLE tests ran

    terminalreporter.write_sep("=", "CRADLE Bench Results")

    # Confusion-matrix counts computed ONCE so every metric below draws from the same run.
    tp = sum(1 for r in crisis if r["detected"])   # crisis correctly flagged
    fn = len(crisis) - tp                            # crisis missed
    fp = sum(1 for r in safe if r["detected"])       # safe wrongly flagged
    tn = len(safe) - fp                              # safe correctly passed

    if crisis:
        recall = tp / len(crisis)
        kpi_marker = "PASS" if recall >= 0.95 else "FAIL <- below 95% KPI"
        terminalreporter.write_line(
            f"Crisis Recall   TP/(TP+FN) ({kpi_marker}): {recall:.1%}  ({tp}/{len(crisis)})  "
            f"[{fn} missed]"
        )
        for label in ("active_suicide_ideation", "passive_suicide_ideation", "self_harm"):
            sub = [r for r in crisis if r["label"] == label]
            if sub:
                sub_tp = sum(1 for r in sub if r["detected"])
                terminalreporter.write_line(
                    f"  {label:35s} {sub_tp:3d}/{len(sub):3d}  "
                    f"({sub_tp/len(sub):.0%})"
                )

    # Precision: of everything flagged crisis, how much was real. The over-triage metric.
    # This is NOT specificity. Needs both tiers present (TP from crisis, FP from safe).
    if crisis and safe and (tp + fp) > 0:
        precision = tp / (tp + fp)
        terminalreporter.write_line(
            f"Precision       TP/(TP+FP) (flagged->real): {precision:.1%}  ({tp}/{tp + fp})  "
            f"[{fp} false positives]"
        )

    if safe:
        specificity = tn / len(safe)
        terminalreporter.write_line(
            f"Specificity     TN/(TN+FP) (safe->no flag): {specificity:.1%}  ({tn}/{len(safe)})  "
            f"[{fp} false positives]"
        )

    if clinical:
        hits = sum(1 for r in clinical if r["detected"])
        terminalreporter.write_line(
            f"Clinical Flags  (coverage only): {hits}/{len(clinical)} "
            f"({hits/len(clinical):.0%}) - no KPI"
        )

    terminalreporter.write_sep("=", "")
