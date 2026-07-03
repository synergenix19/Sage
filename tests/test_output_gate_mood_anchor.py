"""W4 — Arabic mood-rating anchor pin + output_gate guard (signed §K).

Two signed mechanisms on an AR score_mood turn:
  PRIMARY (always-emit) — the anchor clause (واحد يعني صعب جدا وعشرة يعني ممتاز) is emitted VERBATIM
    from mood_check_in.json, never through the LLM/translate. A presented 1-10 scale is never left
    un-anchored (B8: an unanchored scale is an un-administered instrument).
  DEFENSE (guard) — a scale whose low/high anchors are IDENTICAL (the translate corruption
    "1=very good, 10=very good") falls back to the pinned template.
"""
import pytest
from unittest.mock import AsyncMock, patch

from sage_poc.nodes.output_gate import (
    output_gate_node, _pin_mood_anchor, _MOOD_PINNED_TEMPLATE_AR, _MOOD_PINNED_ANCHOR_AR,
)

_CORRUPT_AR = "كيف مزاجك؟ من ١ إلى ١٠، حيث ١ يعني وايد زين و ١٠ يعني وايد زين، وين تحط نفسك؟"
_SCALE_NO_ANCHOR_AR = "تحب تقيم مزاجك اليوم من ١ إلى ١٠؟ شو الرقم اللي تعطيه لمزاجك الحين؟"  # probe-2 shape
_EXPLORATORY_AR = "كيف توصف الأشياء اللي تأثر على مزاجك اليوم؟"  # no scale presented
_ANCHOR = "واحد يعني صعب جدا وعشرة يعني ممتاز"


def test_pinned_constants_carry_verbatim_anchor():
    assert _ANCHOR == _MOOD_PINNED_ANCHOR_AR
    assert _ANCHOR in _MOOD_PINNED_TEMPLATE_AR


# ── PRIMARY: always-emit verbatim ─────────────────────────────────────────────────────────────
def test_pin_appends_anchor_when_scale_presented_without_anchors():
    # probe-2 case: "1 to 10" with NO anchor definitions -> the verbatim clause is concatenated.
    out = _pin_mood_anchor(_SCALE_NO_ANCHOR_AR, executed_step_id="score_mood", lang="ar")
    assert _ANCHOR in out
    assert out.startswith(_SCALE_NO_ANCHOR_AR.rstrip())  # LLM reply kept; clause appended after


def test_pin_no_append_on_exploratory_turn_without_a_scale():
    # A score_mood turn that presents no 1-10 scale must NOT get an anchor bolted on.
    assert _pin_mood_anchor(_EXPLORATORY_AR, executed_step_id="score_mood", lang="ar") == _EXPLORATORY_AR


# ── DEFENSE: guard on corruption ──────────────────────────────────────────────────────────────
def test_guard_replaces_corrupt_identical_anchor_with_pinned():
    out = _pin_mood_anchor(_CORRUPT_AR, executed_step_id="score_mood", lang="ar")
    assert out == _MOOD_PINNED_TEMPLATE_AR
    assert _ANCHOR in out
    assert "يعني وايد زين و ١٠ يعني وايد زين" not in out


def test_pin_leaves_distinct_anchors_untouched():
    good = "من ١ إلى ١٠، ١ يعني منخفض جدا و ١٠ يعني ممتاز جدا، وين تحط نفسك؟"
    assert _pin_mood_anchor(good, executed_step_id="score_mood", lang="ar") == good


# ── Scope guards ──────────────────────────────────────────────────────────────────────────────
def test_pin_no_op_for_english():
    en = "On a scale from 1 to 10, where would you put your mood right now?"
    assert _pin_mood_anchor(en, executed_step_id="score_mood", lang="en") == en


def test_pin_no_op_for_other_steps():
    assert _pin_mood_anchor(_CORRUPT_AR, executed_step_id="explore_mood", lang="ar") == _CORRUPT_AR


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
async def test_e2e_anchor_survives_when_translate_corrupts_scale():
    async def corrupt_translate(text, *, strict=False):
        return _CORRUPT_AR
    with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", side_effect=corrupt_translate), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(_mood_state())
    assert _ANCHOR in result["response"]
    assert "يعني وايد زين و ١٠ يعني وايد زين" not in result["response"]


@pytest.mark.asyncio
async def test_e2e_anchor_appended_when_translate_omits_it():
    # The signed PRIMARY mechanism through the real boundary: translate emits a scale with NO anchor
    # -> the final output still carries the verbatim clause (a scale is never left un-anchored).
    async def scale_no_anchor_translate(text, *, strict=False):
        return _SCALE_NO_ANCHOR_AR
    with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", side_effect=scale_no_anchor_translate), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(_mood_state())
    assert _ANCHOR in result["response"], "pinned anchor clause not concatenated on an un-anchored scale"
