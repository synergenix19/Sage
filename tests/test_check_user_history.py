"""Tests for the cross-session episodic retrieval helper (Task 3.3)."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

# Fixed 1024-dim embedding used across all tests.
FAKE_EMBEDDING = [0.0] * 1024


@pytest.fixture()
def mock_repo():
    repo = AsyncMock()
    return repo


# ---------------------------------------------------------------------------
# 1. Empty string when repo returns no results
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_returns_empty_when_no_results(mock_repo):
    mock_repo.search_session_summaries.return_value = []

    with patch(
        "sage_poc.nodes.tools.check_user_history.get_embedding_async",
        return_value=FAKE_EMBEDDING,
    ):
        from sage_poc.nodes.tools.check_user_history import retrieve_prior_context

        result = await retrieve_prior_context("user-1", "how are you?", mock_repo)

    assert result == ""


# ---------------------------------------------------------------------------
# 2. Empty string when all results are below the 0.6 similarity threshold
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_returns_empty_when_all_below_threshold(mock_repo):
    mock_repo.search_session_summaries.return_value = [
        {
            "session_id": "s1",
            "summary_text": "User discussed anxiety.",
            "safety_level": "moderate",
            "similarity": 0.55,
        },
        {
            "session_id": "s2",
            "summary_text": "User felt overwhelmed.",
            "safety_level": "low",
            "similarity": 0.40,
        },
    ]

    with patch(
        "sage_poc.nodes.tools.check_user_history.get_embedding_async",
        return_value=FAKE_EMBEDDING,
    ):
        from sage_poc.nodes.tools.check_user_history import retrieve_prior_context

        result = await retrieve_prior_context("user-1", "stress at work", mock_repo)

    assert result == ""


# ---------------------------------------------------------------------------
# 3. Correct formatting: attribution prefix + session numbering
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_formats_results_correctly(mock_repo):
    mock_repo.search_session_summaries.return_value = [
        {
            "session_id": "s1",
            "summary_text": "User discussed anxiety.",
            "safety_level": "moderate",
            "similarity": 0.85,
        },
        {
            "session_id": "s2",
            "summary_text": "User felt overwhelmed.",
            "safety_level": "low",
            "similarity": 0.72,
        },
    ]

    with patch(
        "sage_poc.nodes.tools.check_user_history.get_embedding_async",
        return_value=FAKE_EMBEDDING,
    ):
        from sage_poc.nodes.tools.check_user_history import retrieve_prior_context

        result = await retrieve_prior_context("user-1", "anxiety", mock_repo)

    expected = (
        "Prior session context:\n"
        "[Session 1]: User discussed anxiety.\n"
        "[Session 2]: User felt overwhelmed."
    )
    assert result == expected


# ---------------------------------------------------------------------------
# 4. Crisis sessions are excluded via exclude_safety_levels=["crisis"]
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_crisis_sessions_excluded(mock_repo):
    mock_repo.search_session_summaries.return_value = []

    with patch(
        "sage_poc.nodes.tools.check_user_history.get_embedding_async",
        return_value=FAKE_EMBEDDING,
    ):
        from sage_poc.nodes.tools.check_user_history import retrieve_prior_context

        await retrieve_prior_context("user-99", "feeling unsafe", mock_repo)

    _, kwargs = mock_repo.search_session_summaries.call_args
    assert kwargs.get("exclude_safety_levels") == ["crisis"]


# ---------------------------------------------------------------------------
# 5. Partial threshold — only results >= 0.6 appear in output
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_partial_threshold_filters_low_results(mock_repo):
    mock_repo.search_session_summaries.return_value = [
        {
            "session_id": "s1",
            "summary_text": "User discussed coping strategies.",
            "safety_level": "low",
            "similarity": 0.90,
        },
        {
            "session_id": "s2",
            "summary_text": "User mentioned work stress.",
            "safety_level": "low",
            "similarity": 0.50,  # below threshold, should be filtered out
        },
        {
            "session_id": "s3",
            "summary_text": "User practiced breathing exercises.",
            "safety_level": "low",
            "similarity": 0.65,
        },
    ]

    with patch(
        "sage_poc.nodes.tools.check_user_history.get_embedding_async",
        return_value=FAKE_EMBEDDING,
    ):
        from sage_poc.nodes.tools.check_user_history import retrieve_prior_context

        result = await retrieve_prior_context("user-1", "coping", mock_repo)

    expected = (
        "Prior session context:\n"
        "[Session 1]: User discussed coping strategies.\n"
        "[Session 2]: User practiced breathing exercises."
    )
    assert result == expected
    assert "work stress" not in result
