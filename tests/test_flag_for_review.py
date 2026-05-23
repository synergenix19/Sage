import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_make_flag_tool_calls_notifier():
    from sage_poc.nodes.tools.flag_for_review import make_flag_tool
    mock_notifier = AsyncMock()
    with patch("sage_poc.nodes.tools.flag_for_review._get_notifier", return_value=mock_notifier):
        tool_fn = make_flag_tool(user_id="u1", session_id="s1")
        await tool_fn.ainvoke({
            "reason": "cumulative hopelessness across 3 turns",
            "severity": "high",
            "turn_context": "user said 'things won't improve'",
        })
    mock_notifier.notify_review_required.assert_awaited_once()
    call_kwargs = mock_notifier.notify_review_required.call_args
    assert call_kwargs.kwargs["source"] == "llm_flag_for_review"
    assert call_kwargs.kwargs["severity"] == "high"


@pytest.mark.asyncio
async def test_make_flag_tool_is_noop_when_no_notifier():
    from sage_poc.nodes.tools.flag_for_review import make_flag_tool
    with patch("sage_poc.nodes.tools.flag_for_review._get_notifier", return_value=None):
        tool_fn = make_flag_tool(user_id="u1", session_id="s1")
        result = await tool_fn.ainvoke({"reason": "test"})
    assert result is not None  # does not raise
