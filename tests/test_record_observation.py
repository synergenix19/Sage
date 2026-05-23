import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch, call
from sage_poc.nodes.tools.record_observation import make_record_tool


def test_tool_name():
    """make_record_tool returns a tool with name == 'record_observation'."""
    tool = make_record_tool("uid", "sid")
    assert hasattr(tool, "name")
    assert tool.name == "record_observation"


@pytest.mark.asyncio
async def test_invalid_type_returns_error():
    """Calling with an unknown observation_type returns an error string immediately."""
    tool = make_record_tool("uid", "sid")
    result = await tool.ainvoke({"observation_type": "unknown", "content": "some content"})
    assert "invalid observation_type" in result


@pytest.mark.asyncio
async def test_records_observation_to_profile():
    """Valid call appends a new observation and upserts the profile."""
    mock_pool = MagicMock()
    mock_repo = AsyncMock()
    mock_repo.get_therapeutic_profile.return_value = {}

    fake_server = MagicMock()
    fake_server.app.state._db_pool = mock_pool

    tool = make_record_tool("uid", "sid", repo_override=mock_repo)

    with patch.dict(sys.modules, {"server": fake_server}):
        result = await tool.ainvoke({
            "observation_type": "insight",
            "content": "User responds well to grounding exercises",
        })

    assert result == "observation recorded: insight"
    mock_repo.upsert_therapeutic_profile.assert_awaited_once()
    call_args = mock_repo.upsert_therapeutic_profile.await_args
    profile_arg = call_args.args[1]  # (user_id, profile, session_id)
    assert "observations" in profile_arg
    observations = profile_arg["observations"]
    assert len(observations) == 1
    assert observations[0]["type"] == "insight"


@pytest.mark.asyncio
async def test_observation_cap_at_50():
    """When there are already 50 observations, the oldest is dropped before appending."""
    mock_pool = MagicMock()
    existing_observations = [
        {"type": "insight", "content": f"obs {i}", "confidence": 0.8, "session_id": "old"}
        for i in range(50)
    ]
    mock_repo = AsyncMock()
    mock_repo.get_therapeutic_profile.return_value = {"observations": existing_observations}

    fake_server = MagicMock()
    fake_server.app.state._db_pool = mock_pool

    tool = make_record_tool("uid", "sid", repo_override=mock_repo)

    with patch.dict(sys.modules, {"server": fake_server}):
        result = await tool.ainvoke({
            "observation_type": "progress",
            "content": "New observation after cap",
        })

    assert result == "observation recorded: progress"
    mock_repo.upsert_therapeutic_profile.assert_awaited_once()
    call_args = mock_repo.upsert_therapeutic_profile.await_args
    profile_arg = call_args.args[1]
    observations = profile_arg["observations"]
    assert len(observations) == 50
    # The last entry should be the newly appended one
    assert observations[-1]["content"] == "New observation after cap"
    assert observations[-1]["type"] == "progress"


@pytest.mark.asyncio
async def test_concern_with_low_confidence_notifies():
    """concern type with confidence < 0.7 triggers a PostgresNotifier.notify call."""
    mock_pool = MagicMock()
    mock_repo = AsyncMock()
    mock_repo.get_therapeutic_profile.return_value = {}
    mock_notifier = AsyncMock()

    fake_server = MagicMock()
    fake_server.app.state._db_pool = mock_pool

    tool = make_record_tool("uid", "sid", repo_override=mock_repo)

    with patch.dict(sys.modules, {"server": fake_server}):
        with patch(
            "sage_poc.memory.notification.PostgresNotifier",
            return_value=mock_notifier,
        ) as mock_notifier_class:
            result = await tool.ainvoke({
                "observation_type": "concern",
                "content": "User expressed hopelessness",
                "confidence": 0.5,
            })

    assert result == "observation recorded: concern"
    mock_notifier.notify.assert_awaited_once()
    notify_kwargs = mock_notifier.notify.await_args.kwargs
    assert notify_kwargs["source"] == "llm_flag_for_review"
    assert notify_kwargs["severity"] == "medium"
    assert notify_kwargs["session_id"] == "sid"
    assert notify_kwargs["user_id"] == "uid"


@pytest.mark.asyncio
async def test_concern_with_high_confidence_does_not_notify():
    """concern type with confidence >= 0.7 does NOT trigger a notification."""
    mock_pool = MagicMock()
    mock_repo = AsyncMock()
    mock_repo.get_therapeutic_profile.return_value = {}
    mock_notifier = AsyncMock()

    fake_server = MagicMock()
    fake_server.app.state._db_pool = mock_pool

    tool = make_record_tool("uid", "sid", repo_override=mock_repo)

    with patch.dict(sys.modules, {"server": fake_server}):
        with patch(
            "sage_poc.memory.notification.PostgresNotifier",
            return_value=mock_notifier,
        ) as mock_notifier_class:
            result = await tool.ainvoke({
                "observation_type": "concern",
                "content": "User mentioned mild anxiety",
                "confidence": 0.9,
            })

    assert result == "observation recorded: concern"
    mock_notifier.notify.assert_not_awaited()


@pytest.mark.asyncio
async def test_pool_none_returns_skip_message():
    """When pool is None, the tool returns a message containing 'skipped'."""
    fake_server = MagicMock()
    fake_server.app.state._db_pool = None

    tool = make_record_tool("uid", "sid")

    with patch.dict(sys.modules, {"server": fake_server}):
        result = await tool.ainvoke({
            "observation_type": "insight",
            "content": "Some observation",
        })

    assert "skipped" in result
