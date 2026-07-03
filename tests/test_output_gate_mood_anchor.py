"""W4 — Arabic mood-rating anchor pin + output_gate guard.

The numeric-anchor clause (واحد يعني صعب جدا وعشرة يعني ممتاز) is emitted VERBATIM from
mood_check_in.json, never through the LLM/translate step — the translate step is where it corrupted
into identical anchors ("1=very good, 10=very good"). Deterministic guard: on an AR score_mood turn,
a rating scale whose low/high anchors are identical → fall back to the pinned template.
"""
import pytest
from unittest.mock import AsyncMock, patch

from sage_poc.nodes.output_gate import (
    output_gate_node, _guard_mood_anchor, _MOOD_PINNED_TEMPLATE_AR,
)

# The documented translate-step corruption: both endpoints "mean" the same phrase (وايد زين).
_CORRUPT_AR = "كيف مزاجك؟ من ١ إلى ١٠، حيث ١ يعني وايد زين و ١٠ يعني وايد زين، وين تحط نفسك؟"
_ANCHOR = "واحد يعني صعب جدا وعشرة يعني ممتاز"  # the pinned clause, byte-exact


def test_pinned_template_carries_verbatim_anchor():
    # The pinned template is the source of truth (from mood_check_in.json) and contains the anchor.
    assert _ANCHOR in _MOOD_PINNED_TEMPLATE_AR


def test_guard_replaces_corrupt_identical_anchor_with_pinned():
    out = _guard_mood_anchor(_CORRUPT_AR, executed_step_id="score_mood", lang="ar")
    assert out == _MOOD_PINNED_TEMPLATE_AR
    assert _ANCHOR in out                       # verbatim pinned anchor present
    assert "يعني وايد زين و ١٠ يعني وايد زين" not in out  # corrupt scale gone


def test_guard_leaves_distinct_anchors_untouched():
    good = "من ١ إلى ١٠، ١ يعني منخفض جدا و ١٠ يعني ممتاز جدا، وين تحط نفسك؟"
    assert _guard_mood_anchor(good, executed_step_id="score_mood", lang="ar") == good


def test_guard_no_op_for_english():
    en = "On a scale from 1 to 10, where 1 is really low and 10 is really good, where are you?"
    assert _guard_mood_anchor(en, executed_step_id="score_mood", lang="en") == en


def test_guard_no_op_for_other_steps():
    # A non-rating step must never be rewritten, even if it happens to contain "يعني" twice.
    assert _guard_mood_anchor(_CORRUPT_AR, executed_step_id="explore_mood", lang="ar") == _CORRUPT_AR


def _mood_state(**kw):
    base = {
        "gate_path": None, "path": [], "detected_language": "ar",
        "message_en": "how is my mood", "response_en": "On a scale from 1 to 10, where 1 is low and 10 is good, where are you?",
        "is_safe": True, "crisis_state": "none", "crisis_flags": [], "clinical_flags": [],
        "conversation_history": [], "turn_count": 0, "conversation_summary": None,
        "session_id": "s1", "user_id": "u1", "active_skill_id": "mood_check_in",
        "active_step_id": "explore_mood", "executed_step_id": "score_mood",
        "emotional_intensity": 5, "engagement": 5, "banned_opener_retry_count": 0,
    }
    return {**base, **kw}


@pytest.mark.asyncio
async def test_e2e_score_mood_ar_anchor_survives_translate_corruption():
    # BOUNDARY-CROSSING test (the W1 lesson): drive output_gate_node with the translate step
    # producing the corrupt scale (exactly where it broke). The pinned anchor must survive byte-exact
    # in the returned response — proving the guard is wired at the right point, not just the fn.
    async def corrupt_translate(text, *, strict=False):
        return _CORRUPT_AR

    with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", side_effect=corrupt_translate), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(_mood_state())

    assert _ANCHOR in result["response"], "pinned anchor did not survive the translate/compose path"
    assert "يعني وايد زين و ١٠ يعني وايد زين" not in result["response"]
