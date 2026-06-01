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


@pytest.fixture(autouse=True, scope="session")
def _warm_bge_m3_once():
    """Pre-warm the shared BGE-M3 model exactly once per session.

    BGE-M3 first load on 16GB M4 triggers ANE recompilation and takes >10s,
    exceeding the asyncio.wait_for timeout in skill_select_node. Loading here
    keeps the model resident for all subsequent @pytest.mark.slow tests.
    """
    import sage_poc.nodes.skill_select as ss
    if ss._embed_model is None:
        ss._ensure_semantic_ready()


@pytest.fixture(autouse=True)
def _stub_bge_m3(request):
    """Gate BGE-M3 loading per test.

    Non-slow tests: zero-vector stub so cosine similarity is always 0.0 (below
    threshold) — semantic tier never fires, no model loads, saves ~2.3 GB RAM.

    @pytest.mark.slow tests: preserve the session-warmed model; clear only the
    embeddings matrix so _ensure_semantic_ready() re-indexes against the live
    model without triggering a cold-start reload from disk.

    State is saved and restored around every test so tests cannot bleed into
    each other regardless of execution order.
    """
    import sage_poc.nodes.skill_select as ss

    saved_model = ss._embed_model
    saved_embeddings = ss._semantic_embeddings
    saved_ids = ss._semantic_skill_ids[:]

    if request.node.get_closest_marker("slow"):
        # Clear embeddings so _ensure_semantic_ready() re-indexes, but keep
        # _embed_model resident (pre-warmed by _warm_bge_m3_once) to avoid
        # the cold-start ANE recompilation timeout.
        ss._semantic_embeddings = None
        ss._semantic_skill_ids = []
        yield
    else:
        from sage_poc.corpus_constants import KEYWORD_SEMANTIC_SKIP
        routable_ids = [k for k in ss._SKILLS if k not in KEYWORD_SEMANTIC_SKIP]
        n_skills = len(routable_ids)
        mock_model = MagicMock()
        mock_model.encode.side_effect = (
            lambda texts, **kw: np.zeros((len(texts), 1024), dtype=np.float32)
        )
        ss._embed_model = mock_model
        ss._semantic_embeddings = np.zeros((n_skills, 1024), dtype=np.float32)
        ss._semantic_skill_ids = routable_ids
        yield

    ss._embed_model = saved_model
    ss._semantic_embeddings = saved_embeddings
    ss._semantic_skill_ids = saved_ids
