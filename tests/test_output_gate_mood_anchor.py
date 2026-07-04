"""W4 — Arabic mood-rating anchor pin + output_gate emission policy (signed §K + G5-b Option C).

Option C: EVERY AR score_mood turn presents the canonical anchored 1-10 scale
(من ١ إلى ١٠، واحد يعني صعب جدا وعشرة يعني ممتاز), emitted VERBATIM from mood_check_in.json — the
instrument is administered by the step, not at the LLM's discretion (Cardinal Rule 3; B8: a rating
scale is valid only as administered). The LLM renders the warm Khaleeji invitation; it cannot omit,
reword, or paraphrase the scale clause. Corruption guard (identical anchors → pinned template) stays
as defense-in-depth.
"""
import pytest
from unittest.mock import AsyncMock, patch

from sage_poc.nodes.output_gate import (
    output_gate_node, _pin_mood_anchor,
    _MOOD_PINNED_TEMPLATE_AR, _MOOD_PINNED_ANCHOR_AR, _MOOD_PINNED_SCALE_AR,
)

_CORRUPT_AR = "كيف مزاجك؟ من ١ إلى ١٠، حيث ١ يعني وايد زين و ١٠ يعني وايد زين، وين تحط نفسك؟"
_PARAPHRASED_AR = "من ١ إلى ١٠، ١ يعني منخفض جدا و ١٠ يعني ممتاز جدا، وين تحط نفسك؟"  # distinct but not canonical
_SCALELESS_AR = "وين تشوف مزاجك اليوم على السلم، وشو ممكن يكون مؤثر على شعورك؟"  # real prod probe shape (no number)
_ANCHOR = "واحد يعني صعب جدا وعشرة يعني ممتاز"


def test_pinned_constants_carry_verbatim_anchor():
    assert _ANCHOR == _MOOD_PINNED_ANCHOR_AR
    assert _ANCHOR in _MOOD_PINNED_SCALE_AR
    assert _ANCHOR in _MOOD_PINNED_TEMPLATE_AR


# ── Option C: the canonical scale is present on EVERY AR score_mood turn ───────────────────────
def test_scaleless_score_mood_turn_gets_canonical_clause_appended():
    # The real prod case: warm invitation, no numeric scale -> canonical clause appended (instrument
    # administered, not left to LLM discretion). LLM wrapper preserved.
    out = _pin_mood_anchor(_SCALELESS_AR, executed_step_id="score_mood", lang="ar")
    assert _ANCHOR in out
    assert out.startswith(_SCALELESS_AR.rstrip())
    assert _MOOD_PINNED_SCALE_AR in out


def test_paraphrased_scale_replaced_with_canonical_template():
    # LLM presented its own (distinct, non-canonical) scale = a paraphrase -> canonical template.
    out = _pin_mood_anchor(_PARAPHRASED_AR, executed_step_id="score_mood", lang="ar")
    assert out == _MOOD_PINNED_TEMPLATE_AR
    assert _ANCHOR in out


def test_canonical_anchor_already_present_is_unchanged():
    already = "خذ لحظة. " + _MOOD_PINNED_SCALE_AR + "، وين تحط نفسك؟"
    assert _pin_mood_anchor(already, executed_step_id="score_mood", lang="ar") == already


# ── Defense: corruption guard stays ───────────────────────────────────────────────────────────
def test_guard_replaces_corrupt_identical_anchor_with_pinned():
    out = _pin_mood_anchor(_CORRUPT_AR, executed_step_id="score_mood", lang="ar")
    assert out == _MOOD_PINNED_TEMPLATE_AR
    assert "يعني وايد زين و ١٠ يعني وايد زين" not in out


# ── Scope guards ──────────────────────────────────────────────────────────────────────────────
def test_pin_no_op_for_english():
    en = "On a scale from 1 to 10, where would you put your mood right now?"
    assert _pin_mood_anchor(en, executed_step_id="score_mood", lang="en") == en


def test_pin_no_op_for_other_steps():
    # explore_mood is a separate step; the anchor policy applies only to score_mood.
    assert _pin_mood_anchor(_SCALELESS_AR, executed_step_id="explore_mood", lang="ar") == _SCALELESS_AR


def _mood_state(**kw):
    base = {
        "gate_path": None, "path": [], "detected_language": "ar",
        "message_en": "how is my mood", "response_en": "On a scale from 1 to 10, where are you?",
        "is_safe": True, "crisis_state": "none", "crisis_flags": [], "clinical_flags": [],
        "conversation_history": [], "turn_count": 0, "conversation_summary": None,
        "session_id": "s1", "user_id": "u1", "active_skill_id": "mood_check_in",
        "active_step_id": "explore_mood", "executed_step_id": "score_mood",
        "emotional_intensity": 5, "engagement": 5, "banned_opener_retry_count": 0,
    }
    return {**base, **kw}


# ── BOUNDARY-CROSSING E2E (the W1 lesson): drive output_gate_node through the translate step ────
@pytest.mark.asyncio
async def test_e2e_anchor_present_when_translate_corrupts_scale():
    async def corrupt_translate(text, *, strict=False):
        return _CORRUPT_AR
    with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", side_effect=corrupt_translate), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(_mood_state())
    assert _ANCHOR in result["response"]
    assert "يعني وايد زين و ١٠ يعني وايد زين" not in result["response"]


@pytest.mark.asyncio
async def test_e2e_anchor_present_when_translate_is_scaleless():
    # Option C through the real boundary + the OBSERVED prod behaviour: translate emits a warm,
    # scale-less invitation -> the canonical anchored scale must still be in the final output.
    async def scaleless_translate(text, *, strict=False):
        return _SCALELESS_AR
    with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", side_effect=scaleless_translate), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(_mood_state())
    assert _ANCHOR in result["response"], "every AR score_mood turn must present the anchored scale (Option C)"
