import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_make_record_tool_writes_observation():
    from sage_poc.nodes.tools.record_observation import make_record_tool
    mock_repo = AsyncMock()
    mock_repo.get_therapeutic_profile = AsyncMock(return_value={"observations": []})
    mock_repo.upsert_therapeutic_profile = AsyncMock()

    tool_fn = make_record_tool(user_id="u1", pool=object(), repo_override=mock_repo)
    await tool_fn.ainvoke({
        "observation": "User identified their own catastrophising without prompting.",
        "observation_type": "insight",
        "confidence": "high",
    })
    mock_repo.upsert_therapeutic_profile.assert_awaited_once()

@pytest.mark.asyncio
async def test_low_confidence_observation_also_flags_for_review():
    from sage_poc.nodes.tools.record_observation import make_record_tool
    mock_repo = AsyncMock()
    mock_repo.get_therapeutic_profile = AsyncMock(return_value=None)
    mock_repo.upsert_therapeutic_profile = AsyncMock()
    mock_notifier = AsyncMock()

    with patch("sage_poc.nodes.tools.record_observation._get_notifier", return_value=mock_notifier):
        tool_fn = make_record_tool(user_id="u1", pool=object(), repo_override=mock_repo, session_id="s1")
        await tool_fn.ainvoke({
            "observation": "Possible dissociation pattern",
            "observation_type": "context_update",
            "confidence": "low",
        })
    mock_notifier.notify_review_required.assert_awaited_once()
