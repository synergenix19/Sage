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
async def test_observation_list_capped_at_50():
    """When the stored profile already has 55 observations, adding one more must
    result in exactly 50 observations in the upserted profile (the 6 oldest dropped).
    """
    from sage_poc.nodes.tools.record_observation import make_record_tool
    existing_observations = [
        {"text": f"obs {i}", "type": "insight", "confidence": "high", "recorded_at": "2026-01-01"}
        for i in range(55)
    ]
    mock_repo = AsyncMock()
    mock_repo.get_therapeutic_profile = AsyncMock(return_value={"observations": existing_observations})
    mock_repo.upsert_therapeutic_profile = AsyncMock()

    tool_fn = make_record_tool(user_id="u1", pool=object(), repo_override=mock_repo)
    await tool_fn.ainvoke({
        "observation": "New observation after cap.",
        "observation_type": "progress",
        "confidence": "high",
    })

    upserted_profile = mock_repo.upsert_therapeutic_profile.call_args.kwargs.get(
        "profile"
    ) or mock_repo.upsert_therapeutic_profile.call_args.args[1]
    assert len(upserted_profile["observations"]) == 50


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


@pytest.mark.asyncio
async def test_concern_observation_always_flags_for_review():
    """concern type must trigger clinician review regardless of confidence level.

    A discretionary LLM write of clinical consequence (a 'concern' about a user's
    engagement with a technique) must not be silently persisted — it requires a
    human review checkpoint independent of confidence.
    """
    from sage_poc.nodes.tools.record_observation import make_record_tool
    mock_repo = AsyncMock()
    mock_repo.get_therapeutic_profile = AsyncMock(return_value=None)
    mock_repo.upsert_therapeutic_profile = AsyncMock()
    mock_notifier = AsyncMock()

    with patch("sage_poc.nodes.tools.record_observation._get_notifier", return_value=mock_notifier):
        tool_fn = make_record_tool(user_id="u1", pool=object(), repo_override=mock_repo, session_id="s1")
        await tool_fn.ainvoke({
            "observation": "User seemed resistant to sleep hygiene technique",
            "observation_type": "concern",
            "confidence": "high",  # high confidence — would skip the low-confidence gate
        })

    mock_notifier.notify_review_required.assert_awaited_once(), (
        "concern observations must always trigger review even at high confidence"
    )


@pytest.mark.asyncio
async def test_non_profile_modifying_high_confidence_skips_review():
    """insight/progress/agency at high confidence must NOT trigger review.

    The review gate is for profile-modifying and low-confidence writes only.
    Flagging routine positive observations defeats the purpose of the gate.
    """
    from sage_poc.nodes.tools.record_observation import make_record_tool
    mock_repo = AsyncMock()
    mock_repo.get_therapeutic_profile = AsyncMock(return_value=None)
    mock_repo.upsert_therapeutic_profile = AsyncMock()
    mock_notifier = AsyncMock()

    with patch("sage_poc.nodes.tools.record_observation._get_notifier", return_value=mock_notifier):
        tool_fn = make_record_tool(user_id="u1", pool=object(), repo_override=mock_repo, session_id="s1")
        await tool_fn.ainvoke({
            "observation": "User identified their own cognitive distortion unprompted",
            "observation_type": "insight",
            "confidence": "high",
        })

    mock_notifier.notify_review_required.assert_not_awaited(), (
        "high-confidence insight observations must not trigger clinician review"
    )
