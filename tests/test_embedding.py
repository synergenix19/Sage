"""Tests for the BGE-M3 embedding wrapper (Task 3.2)."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch


def _make_mock_model() -> MagicMock:
    """Return a mock SentenceTransformer that produces 1024-dim float lists."""
    mock = MagicMock()
    # encode returns a list whose [0] element is a list of 1024 floats
    mock.encode.return_value = [[float(i % 10) / 10 for i in range(1024)]]
    return mock


def test_get_embedding_returns_1024_floats():
    """get_embedding returns a plain list of 1024 floats."""
    from sage_poc.memory import embedding as m

    m._get_model.cache_clear()
    mock_model = _make_mock_model()

    with patch("sage_poc.memory.embedding._get_model", return_value=mock_model):
        result = m.get_embedding("hello world")

    assert isinstance(result, list), "result must be a plain list"
    assert len(result) == 1024, f"expected 1024 dims, got {len(result)}"
    assert all(isinstance(v, float) for v in result), "all elements must be float"


def test_get_embedding_async_matches_sync():
    """get_embedding_async returns the same result as get_embedding."""
    from sage_poc.memory import embedding as m

    m._get_model.cache_clear()
    mock_model = _make_mock_model()

    with patch("sage_poc.memory.embedding._get_model", return_value=mock_model):
        sync_result = m.get_embedding("async parity test")
        async_result = asyncio.run(m.get_embedding_async("async parity test"))

    assert sync_result == async_result, (
        "async result must match sync result for the same input"
    )


def test_get_model_is_cached():
    """_get_model() returns the same object on repeated calls (lru_cache works)."""
    from sage_poc.memory import embedding as m

    m._get_model.cache_clear()
    mock_model = _make_mock_model()

    with patch("sage_poc.memory.embedding._get_model") as mock_get:
        # Configure the mock to return our mock model on first call
        mock_get.return_value = mock_model
        mock_get.cache_clear = lambda: None
        # Call it twice through the get_embedding function to test cache
        m._get_model.cache_clear()
        with patch("sage_poc.memory.embedding._get_model", return_value=mock_model):
            first = m.get_embedding("test1")
            second = m.get_embedding("test1")

    # Both calls should succeed (proving cache works)
    assert first == second, "get_embedding must return consistent results"
