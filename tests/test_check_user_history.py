import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_retrieve_prefixes_attribution():
    from sage_poc.nodes.tools.check_user_history import retrieve_prior_context
    mock_repo = AsyncMock()
    mock_repo.search_session_summaries = AsyncMock(return_value=[{
        "summary_text": "User discussed anxiety about work",
        "safety_level": "normal",
        "similarity": 0.88,
    }])
    with patch("sage_poc.nodes.tools.check_user_history.get_embedding_async", return_value=[0.1]*1024):
        result = await retrieve_prior_context(
            user_id="u1", query="work anxiety", repo=mock_repo
        )
    assert "In an earlier conversation" in result

@pytest.mark.asyncio
async def test_retrieve_excludes_crisis_summaries():
    from sage_poc.nodes.tools.check_user_history import retrieve_prior_context
    mock_repo = AsyncMock()
    mock_repo.search_session_summaries = AsyncMock(return_value=[])
    with patch("sage_poc.nodes.tools.check_user_history.get_embedding_async", return_value=[0.1]*1024):
        await retrieve_prior_context(user_id="u1", query="anything", repo=mock_repo)
    call_kwargs = mock_repo.search_session_summaries.call_args
    assert "crisis" in (call_kwargs.kwargs.get("exclude_safety_levels") or [])

@pytest.mark.asyncio
async def test_retrieve_filters_low_similarity():
    from sage_poc.nodes.tools.check_user_history import retrieve_prior_context
    mock_repo = AsyncMock()
    mock_repo.search_session_summaries = AsyncMock(return_value=[{
        "summary_text": "Some text",
        "safety_level": "normal",
        "similarity": 0.4,  # below 0.6 threshold
    }])
    with patch("sage_poc.nodes.tools.check_user_history.get_embedding_async", return_value=[0.1]*1024):
        result = await retrieve_prior_context(user_id="u1", query="q", repo=mock_repo)
    assert result == ""
