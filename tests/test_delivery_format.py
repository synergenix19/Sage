"""P0b — delivery_format. THE FOUNDING TEST (written RED; green is P0b's build, a later session).

This is the assertion the whole thread opened with at 8/34: box_breathing carries
`Format: Video` in the BOT BEHAVIOUR doc (a real table row — see the P0b grounding), yet it
is delivered as a WALL OF TEXT — its coached, step-by-step breathing body — instead of a
short video handoff (a psychoeducation line, a video reference, a check-in).

Guardrails honored:
  - Asserts ONLY the video-handoff BEHAVIOR (doc-traced Format=Video for box_breathing), NOT
    any enum-value string still sitting unsigned in the ratification queue.
  - RIGHT-REASON red: the failure must be "box_breathing still emits its step-coaching
    walkthrough," not a fixture/import error. The executor renders box_breathing's step
    `inhale_hold` goal ("Coach the user through the inhale and hold...") today; that verbatim
    marker IS the text wall, and its presence is the founding failure.
  - RED until P0b's video renderer lands. Do NOT make it green in the session that wrote it.
"""
import pytest

from sage_poc import config
from sage_poc.nodes.skill_executor import skill_executor_node

# Reuse the executor test's state builder so the RED is behavioral, not a malformed-state error.
from tests.test_skill_executor import _make_executor_state

# The verbatim step-coaching marker from box_breathing.json step `inhale_hold`. A video handoff
# must NOT walk this; its presence in the delivered instruction is the text-wall failure mode.
_TEXT_WALL_MARKER = "coach the user through"


@pytest.mark.asyncio
async def test_founding_box_breathing_renders_as_video_handoff_not_text_wall(monkeypatch):
    # raising=False: the flag does not exist yet (P0b Task 4 adds SAGE_DELIVERY_FORMAT). Setting
    # it now means the test flips to a real pass/fail the day the renderer lands, not a rewrite.
    monkeypatch.setattr(config, "DELIVERY_FORMAT_ENABLED", True, raising=False)

    state = _make_executor_state(
        active_skill_id="box_breathing",
        active_step_id="inhale_hold",
        message_en="ok let's try it",
        raw_message="ok let's try it",
    )
    result = await skill_executor_node(state)

    delivered = " ".join(
        str(result.get(k) or "")
        for k in ("step_instruction", "executed_step_id", "step_mandatory_caveat")
    ).lower()

    assert _TEXT_WALL_MARKER not in delivered, (
        "FOUNDING FAILURE (expected RED until P0b's video renderer lands): box_breathing "
        "(doc Format=Video) was delivered as its step-coaching walkthrough — the text wall — "
        "instead of a video handoff. This is the 8/34 complaint, now expressed as a test."
    )
