import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from sage_poc.nodes.tools.flag_for_review import make_flag_tool


def test_make_flag_tool_returns_langchain_tool():
    """Test that make_flag_tool returns an object with the 'flag_for_review' name."""
    tool = make_flag_tool("uid", "sid")
    assert hasattr(tool, "name")
    assert tool.name == "flag_for_review"


@pytest.mark.asyncio
async def test_flag_tool_calls_notifier_with_correct_source():
    """Test that the tool calls PostgresNotifier.notify with source='llm_flag_for_review'."""
    user_id = "test_user_123"
    session_id = "test_session_456"
    reason = "Concerning thought pattern detected"
    severity = "high"

    # Create mock pool
    mock_pool = MagicMock()

    # Create mock PostgresNotifier
    mock_notifier = AsyncMock()

    # Create a fake server module
    fake_server_module = MagicMock()
    fake_server_module.app.state._db_pool = mock_pool

    tool = make_flag_tool(user_id, session_id)

    with patch.dict(sys.modules, {"server": fake_server_module}):
        with patch(
            "sage_poc.nodes.tools.flag_for_review.PostgresNotifier",
            return_value=mock_notifier,
        ) as mock_notifier_class:
            result = await tool.ainvoke({"reason": reason, "severity": severity})

            # Assert PostgresNotifier was instantiated with the correct pool
            mock_notifier_class.assert_called_once_with(mock_pool)

            # Assert notify was called with the correct arguments
            mock_notifier.notify.assert_awaited_once()
            call_kwargs = mock_notifier.notify.await_args.kwargs
            assert call_kwargs["session_id"] == session_id
            assert call_kwargs["user_id"] == user_id
            assert call_kwargs["source"] == "llm_flag_for_review"
            assert call_kwargs["severity"] == severity
            assert call_kwargs["reason"] == reason


@pytest.mark.asyncio
async def test_flag_tool_returns_flagged_for_review_on_success():
    """Test that the tool returns 'flagged for review' on success."""
    mock_pool = MagicMock()
    mock_notifier = AsyncMock()

    fake_server_module = MagicMock()
    fake_server_module.app.state._db_pool = mock_pool

    tool = make_flag_tool("uid", "sid")

    with patch.dict(sys.modules, {"server": fake_server_module}):
        with patch(
            "sage_poc.nodes.tools.flag_for_review.PostgresNotifier",
            return_value=mock_notifier,
        ):
            result = await tool.ainvoke({"reason": "test", "severity": "medium"})

    assert result == "flagged for review"


@pytest.mark.asyncio
async def test_flag_tool_returns_skip_message_when_pool_none():
    """Test that the tool returns a skip message when pool is None."""
    fake_server_module = MagicMock()
    fake_server_module.app.state._db_pool = None

    tool = make_flag_tool("uid", "sid")

    with patch.dict(sys.modules, {"server": fake_server_module}):
        result = await tool.ainvoke({"reason": "test", "severity": "medium"})

    assert "skipped" in result or "unavailable" in result


@pytest.mark.asyncio
async def test_flag_tool_returns_error_string_on_exception():
    """Test that the tool returns an error string when notifier.notify raises an exception."""
    mock_pool = MagicMock()
    mock_notifier = AsyncMock()
    mock_notifier.notify.side_effect = ValueError("Database connection failed")

    fake_server_module = MagicMock()
    fake_server_module.app.state._db_pool = mock_pool

    tool = make_flag_tool("uid", "sid")

    with patch.dict(sys.modules, {"server": fake_server_module}):
        with patch(
            "sage_poc.nodes.tools.flag_for_review.PostgresNotifier",
            return_value=mock_notifier,
        ):
            result = await tool.ainvoke({"reason": "test", "severity": "medium"})

    assert result.startswith("review flag failed:")
    assert "Database connection failed" in result
