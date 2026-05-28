"""Shared pytest configuration for the sage-poc test suite.

State construction is intentionally kept local to each test module so the full
21-field SageState schema is visible at the call site. This file holds only
pytest-level configuration and shared fixtures.

Test module responsibilities:
- test_nodes.py  — unit tests for individual nodes; uses local make_state()
- test_graph.py  — graph-level and Arabic crisis tests; uses local make_e2e_state()
- test_routing.py — parametrized routing branch tests; uses local make_full_state()
- test_language.py, test_skill_schema.py, test_state.py — standalone unit tests
"""
import numpy as np
import pytest
from unittest.mock import MagicMock
from sage_poc.llm import reset_singletons


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
        n_skills = len(ss._SKILLS)
        mock_model = MagicMock()
        mock_model.encode.side_effect = (
            lambda texts, **kw: np.zeros((len(texts), 1024), dtype=np.float32)
        )
        ss._embed_model = mock_model
        ss._semantic_embeddings = np.zeros((n_skills, 1024), dtype=np.float32)
        ss._semantic_skill_ids = list(ss._SKILLS.keys())
        yield

    ss._embed_model = saved_model
    ss._semantic_embeddings = saved_embeddings
    ss._semantic_skill_ids = saved_ids
