"""Shared pytest configuration for the sage-poc test suite.

State construction is intentionally kept local to each test module so the full
21-field SageState schema is visible at the call site. This file holds only
pytest-level configuration and shared markers.

Test module responsibilities:
- test_nodes.py  — unit tests for individual nodes; uses local make_state()
- test_graph.py  — graph-level and Arabic crisis tests; uses local make_e2e_state()
- test_routing.py — parametrized routing branch tests; uses local make_full_state()
- test_language.py, test_skill_schema.py, test_state.py — standalone unit tests
"""
import numpy as np
import pytest
from unittest.mock import MagicMock


@pytest.fixture(autouse=True)
def _stub_bge_m3(request):
    """Gate BGE-M3 loading per test.

    Non-slow tests: zero-vector stub so cosine similarity is always 0.0 (below
    threshold) — semantic tier never fires, no model loads, saves ~2.3 GB RAM.

    @pytest.mark.slow tests: reset globals so _ensure_semantic_ready() loads the
    real BAAI/bge-m3 model, which these tests require for semantic accuracy checks.

    State is saved and restored around every test so tests cannot bleed into
    each other regardless of execution order.
    """
    import sage_poc.nodes.skill_select as ss

    saved_model = ss._embed_model
    saved_embeddings = ss._semantic_embeddings
    saved_ids = ss._semantic_skill_ids[:]

    if request.node.get_closest_marker("slow"):
        # Reset so _ensure_semantic_ready() fires and loads the real model
        ss._embed_model = None
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
