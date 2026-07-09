"""P1(mid) freeflow response-shape floor — structural + coupling regression guards.

Background (2026-06-25 band-attribution + floor test):
The screenshotted "cold reply" defect was attributed to PURE_FREEFLOW + mid band +
no skill + no step_policy, and shown to be a VARIANCE problem: 5 samples of the same
mid pure-freeflow case ranged 19-38 words, all under the P-2 validation band (40-80),
because the mid intensity-guidance string imposes no shape or length floor. P1 injects
a response-shape floor (validation-first, one open question, ~40-80 words) ONLY on mid
pure-freeflow turns, via _MID_FREEFLOW_SHAPE appended to the freeflow guardrail block.

These tests are the deterministic (no-LLM, CI-safe) half of the promotion gate. They
assert:
  * the shape fires exactly where intended (mid + general_chat + no-step + no-offer),
  * the two named negative controls stay inert (low band / offer path) — promoted to
    permanent regressions so a future composer edit cannot silently widen the gate,
  * the >=7 acute surface is excluded and high-band (§15.3) guidance is left untouched,
  * P1 carries no P2 (normalization) or P3 (menu/fork) content,
  * the LOAD-BEARING coupling: P1 only works because it invokes a clinician-signed L0
    exception. test_l0_longer_reply_exception_present fails loudly if that clause leaves
    L0, instead of the dog case quietly going cold with no engineering signal.

The behavioral half (does the floor actually move post-LLM, in EN and AR, and is the
acute path untouched end-to-end) lives in tests/eval/p1_mid_freeflow_eval.py — it needs
live LLM calls and is run on demand, not in CI.
"""
import pytest

from sage_poc.prompts.composer import compose_prompt, _MID_FREEFLOW_SHAPE, _INTENSITY_GUIDANCE

SHAPE_MARKER = "RESPONSE SHAPE: This is a turn that needs more"

# Exact clinician-signed L0 clause that P1 rides. If L0 is re-authored and this exact
# substring leaves the template, P1 silently reverts to cold — so this string is the
# canary. Keep it character-identical to L0_persona.json::content.
L0_LONGER_REPLY_EXCEPTION = (
    "two to four sentences unless the person needs more; a heavy disclosure deserves a "
    "longer, more present reply even when it is brief"
)


def _state(intensity=5, intent="general_chat", language="en", step=None, offer=None):
    """Minimal SageState for compose_prompt. Defaults to a mid pure-freeflow turn."""
    return {
        "raw_message": "x",
        "message_en": "x",
        "detected_language": language,
        "primary_intent": intent,
        "secondary_intent": None,
        "emotional_intensity": intensity,
        "engagement": 5,
        "active_skill_id": None,
        "executed_step_id": None,
        "step_instruction": step,
        "offered_skill_ids": offer,
        "rule_fired": None,
        "escalation_triggered": None,
        "clinical_flags": [],
        "crisis_state": "none",
        "third_party_crisis": False,
    }


def _prompt_blob(state):
    system_str, user_str, layers = compose_prompt(state)
    return system_str + "\n" + user_str, layers


# --- positive: fires where intended ----------------------------------------

def test_shape_fires_on_mid_general_chat():
    blob, layers = _prompt_blob(_state(intensity=5))
    assert SHAPE_MARKER in blob
    assert "freeflow_guardrail" in layers


@pytest.mark.parametrize("intensity", [4, 5, 6])
def test_shape_fires_across_full_mid_band(intensity):
    blob, _ = _prompt_blob(_state(intensity=intensity))
    assert SHAPE_MARKER in blob, f"shape missing at mid-band intensity {intensity}"


# --- negative controls: promoted to permanent regressions ------------------

def test_control_low_band_never_injects():
    """good_news control: intensity<=3 must NOT get the shape (light moments stay light)."""
    for intensity in (1, 2, 3):
        blob, _ = _prompt_blob(_state(intensity=intensity))
        assert SHAPE_MARKER not in blob, f"P1 leaked into low band at intensity {intensity}"


def test_control_offer_path_never_injects():
    """work_stress control: a live skill offer must NOT get the shape (offer has its own contract)."""
    blob, layers = _prompt_blob(_state(intensity=5, offer=["box_breathing"]))
    assert SHAPE_MARKER not in blob
    assert "freeflow_guardrail" not in layers  # guardrail itself suppressed on offer turns


def test_control_skill_step_never_injects():
    """An active skill step must NOT get the shape (R-7 slot is technique, not a question)."""
    blob, _ = _prompt_blob(_state(intensity=5, intent="new_skill", step="Do the technique step"))
    assert SHAPE_MARKER not in blob


# --- >=7 acute exclusion + high-band (§15.3) left untouched -----------------

@pytest.mark.parametrize("intensity", [7, 8, 9, 10])
def test_acute_band_excluded(intensity):
    blob, _ = _prompt_blob(_state(intensity=intensity))
    assert SHAPE_MARKER not in blob, f"P1 must not fire on the acute surface (intensity {intensity})"


def test_high_band_guidance_untouched_when_shape_absent():
    """At intensity 8 the shape is absent AND the high-band guidance still governs the turn."""
    blob, _ = _prompt_blob(_state(intensity=8))
    assert SHAPE_MARKER not in blob
    assert _INTENSITY_GUIDANCE["high"] in blob


# --- Arabic: same English L0, language-agnostic gate -----------------------

def test_shape_fires_arabic_mid_with_translation_contract():
    """AR mid turns generate in English against the same L0, so the shape fires identically
    and the ARABIC SESSION translation contract is present. (Translation survival of the
    floor is a behavioral check, not asserted here.)"""
    blob, layers = _prompt_blob(_state(intensity=5, language="ar"))
    assert SHAPE_MARKER in blob
    assert "arabic_register" in layers
    assert "ARABIC SESSION" in blob


# --- P1 carries no P2 / P3 content -----------------------------------------

def test_shape_is_single_question_not_menu():
    # Mandate one question; forbid P3 user-facing option/fork phrasing. (Note: a bare " or "
    # is NOT a tell — "three or four sentences" is internal instruction, not a menu offered
    # to the user; match the menu intent, not the conjunction.)
    assert "single question, not several" in _MID_FREEFLOW_SHAPE
    low = _MID_FREEFLOW_SHAPE.lower()
    for menu_phrase in ("or something else", "would you prefer", "options", "choice", "menu", "two or three"):
        assert menu_phrase not in low, f"P3 menu/fork leaked into P1: {menu_phrase!r}"


def test_shape_has_no_normalization_or_em_dash():
    # No P2 normalization claim ("normal", "common", "everyone", "makes sense that")
    low = _MID_FREEFLOW_SHAPE.lower()
    for p2_word in ("normal", "common", "everyone", "makes sense"):
        assert p2_word not in low, f"P2 normalization leaked into P1: {p2_word!r}"
    assert "—" not in _MID_FREEFLOW_SHAPE  # em dash mirrors into output


# --- LOAD-BEARING coupling guard -------------------------------------------

def test_l0_longer_reply_exception_present():
    """P1's floor only clears because it invokes this clinician-signed L0 exception.
    If a future L0 re-authoring drops it, P1 reverts to cold with no other signal — so
    this test must fail loudly, naming the coupling, BEFORE that regression ships."""
    import json
    import pathlib
    l0 = json.loads(
        (pathlib.Path(__file__).parent.parent
         / "src/sage_poc/prompts/templates/L0_persona.json").read_text()
    )
    assert L0_LONGER_REPLY_EXCEPTION in l0["content"], (
        "L0 longer-reply exception clause is GONE. P1(mid) silently reverts to cold replies. "
        "Either restore the clause in L0_persona.json or re-home the P1 floor onto a different, "
        "still-present L0 anchor and update _MID_FREEFLOW_SHAPE's coupling comment + this test."
    )
