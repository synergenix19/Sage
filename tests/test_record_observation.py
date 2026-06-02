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


# ── R2-triggered path: full chain confirmation ──────────────────────────────
#
# The contamination path this gate exists to block:
#   Phase 1 stay (criteria not met)
#   → Phase 2 resistance fires (score > 6)
#   → step_instruction = "offer skill switch or break"
#   → freeflow LLM receives that instruction and calls record_observation
#     with type="concern" describing the technique as ineffective
#   → profile write happens — GATE must fire, not silent
#
# This test constructs that path end-to-end with the tool call the freeflow
# LLM would produce when interpreting a resistance-triggered step_instruction.

@pytest.mark.asyncio
async def test_r2_triggered_concern_observation_gates_correctly():
    """Simulates the freeflow record_observation call that follows an R2 fire.

    When Phase 2 resistance fires on a stay turn, the step_instruction flowing
    to freeflow says 'offer a break or skill switch.' The LLM may interpret this
    as evidence the technique isn't working and call record_observation with
    type='concern'. This test confirms:
      (a) the write is not silently rejected (observation IS persisted)
      (b) clinician review IS triggered — the gate fires on every concern write
      (c) the audit log entry IS emitted
    """
    from sage_poc.nodes.tools.record_observation import make_record_tool
    import logging

    mock_repo = AsyncMock()
    mock_repo.get_therapeutic_profile = AsyncMock(return_value={
        "observations": [],
        "ineffective_techniques": [],  # pre-existing profile shape
    })
    mock_repo.upsert_therapeutic_profile = AsyncMock()
    mock_notifier = AsyncMock()

    # The exact call the freeflow LLM would make when R2 fires for sleep_hygiene:
    # "user seems unresponsive to current technique — possible resistance"
    r2_triggered_observation = (
        "User has not been engaging with sleep hygiene guidance across multiple turns "
        "and may find the technique ineffective or unhelpful."
    )

    with patch("sage_poc.nodes.tools.record_observation._get_notifier", return_value=mock_notifier):
        tool_fn = make_record_tool(
            user_id="u-test-r2", pool=object(), repo_override=mock_repo, session_id="s-r2"
        )
        with patch("sage_poc.nodes.tools.record_observation._log") as mock_log:
            result = await tool_fn.ainvoke({
                "observation":      r2_triggered_observation,
                "observation_type": "concern",
                "confidence":       "medium",   # LLM would use medium — it's inferred, not explicit
            })

    # (a) Write was not silently rejected
    assert result == "recorded", "concern observation must be persisted, not rejected"
    mock_repo.upsert_therapeutic_profile.assert_awaited_once()

    # (b) Gate fired — clinician review triggered
    mock_notifier.notify_review_required.assert_awaited_once()
    call_kwargs = mock_notifier.notify_review_required.call_args
    reason = (call_kwargs.kwargs or call_kwargs[1]).get("reason", "")
    assert "concern" in reason.lower(), (
        "review reason must identify this as a concern observation"
    )

    # (c) Audit log entry was emitted (profile_write log line)
    log_calls = [str(c) for c in mock_log.info.call_args_list]
    assert any("profile_write" in c for c in log_calls), (
        "profile_write audit log entry must be emitted on every profile write via record_observation"
    )


@pytest.mark.asyncio
async def test_invalid_observation_type_rejected_before_profile_write():
    """observation_type='ineffective_technique' must be rejected — it is not in
    _VALID_OBSERVATION_TYPES and must never reach the profile write path.

    This confirms the LLM cannot directly write to ineffective_techniques via this
    tool, even under prompt injection or miscalibrated tool calls.
    """
    from sage_poc.nodes.tools.record_observation import make_record_tool

    mock_repo = AsyncMock()
    mock_repo.get_therapeutic_profile = AsyncMock(return_value=None)
    mock_repo.upsert_therapeutic_profile = AsyncMock()

    tool_fn = make_record_tool(user_id="u1", pool=object(), repo_override=mock_repo)
    result = await tool_fn.ainvoke({
        "observation":      "sleep_hygiene is not working for this user",
        "observation_type": "ineffective_technique",
        "confidence":       "high",
    })

    assert "invalid" in result.lower(), (
        "invalid observation_type must be rejected before any profile write"
    )
    mock_repo.upsert_therapeutic_profile.assert_not_awaited()
