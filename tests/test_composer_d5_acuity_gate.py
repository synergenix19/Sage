"""Tests for D5 deterministic acuity gate (default-off, pending clinical sign-off).

D5 fires when SAGE_D5_ACUITY_GATE=true AND emotional_intensity >= D5_ACUITY_FLOOR (default 8).
When the gate is OFF (default), behaviour must be byte-identical to current production.
"""
import pytest


# ---------------------------------------------------------------------------
# (a) Flag OFF + high intensity -> original high string, off-path unchanged
# ---------------------------------------------------------------------------

def test_d5_gate_off_returns_original_high_string(monkeypatch):
    """Flag OFF: _intensity_guidance(9) must return the original high guidance string unchanged."""
    from sage_poc import config
    from sage_poc.prompts.composer import _INTENSITY_GUIDANCE, _intensity_guidance

    monkeypatch.setattr(config, "D5_ACUITY_GATE_ENABLED", False)
    monkeypatch.setattr(config, "D5_ACUITY_FLOOR", 8)

    result = _intensity_guidance(9)
    assert result == _INTENSITY_GUIDANCE["high"], (
        f"Off-path must return original high string byte-identical. Got: {result!r}"
    )
    assert "do not challenge" not in result.lower(), (
        "D5 language must not appear when gate is OFF."
    )


# ---------------------------------------------------------------------------
# (b) Flag ON + intensity >= 8 -> returns new validate-only string (no "do not reflect back")
# ---------------------------------------------------------------------------

def test_d5_gate_on_high_intensity_returns_validate_only(monkeypatch):
    """Flag ON + intensity 8: returns D5 validate-only string with required phrases."""
    from sage_poc import config
    from sage_poc.prompts.composer import _intensity_guidance

    monkeypatch.setattr(config, "D5_ACUITY_GATE_ENABLED", True)
    monkeypatch.setattr(config, "D5_ACUITY_FLOOR", 8)

    result = _intensity_guidance(8)
    assert "do not challenge" in result.lower(), (
        f"D5 string must include 'do not challenge'. Got: {result!r}"
    )
    assert "purely supportive" in result.lower(), (
        f"D5 string must include 'purely supportive'. Got: {result!r}"
    )
    assert "validate" in result.lower(), (
        f"D5 string must include 'validate'. Got: {result!r}"
    )
    # Must NOT contain the old blunt phrase
    assert "do not reflect back" not in result.lower(), (
        f"D5 string must NOT carry the old 'do not reflect back' wording. Got: {result!r}"
    )
    # No em dashes
    assert "—" not in result, (
        f"D5 string must not contain em dashes. Got: {result!r}"
    )


def test_d5_gate_on_intensity_9_returns_validate_only(monkeypatch):
    """Flag ON + intensity 9: also returns D5 validate-only string."""
    from sage_poc import config
    from sage_poc.prompts.composer import _intensity_guidance

    monkeypatch.setattr(config, "D5_ACUITY_GATE_ENABLED", True)
    monkeypatch.setattr(config, "D5_ACUITY_FLOOR", 8)

    result = _intensity_guidance(9)
    assert "do not challenge" in result.lower()
    assert "purely supportive" in result.lower()
    assert "validate" in result.lower()


# ---------------------------------------------------------------------------
# (c) Flag ON + intensity 7 -> original high string (floor boundary, 7 < 8)
# ---------------------------------------------------------------------------

def test_d5_floor_boundary_intensity_7_returns_original_high(monkeypatch):
    """Flag ON + intensity 7 (below floor=8): must still return the original high string."""
    from sage_poc import config
    from sage_poc.prompts.composer import _INTENSITY_GUIDANCE, _intensity_guidance

    monkeypatch.setattr(config, "D5_ACUITY_GATE_ENABLED", True)
    monkeypatch.setattr(config, "D5_ACUITY_FLOOR", 8)

    result = _intensity_guidance(7)
    assert result == _INTENSITY_GUIDANCE["high"], (
        f"Intensity 7 is in the high band but below D5 floor=8; must return original high. Got: {result!r}"
    )
    assert "do not challenge" not in result.lower(), (
        "D5 language must not appear at intensity 7 when floor is 8."
    )


def test_d5_floor_boundary_at_floor_returns_d5(monkeypatch):
    """Flag ON + intensity exactly at floor=8: must return D5 string."""
    from sage_poc import config
    from sage_poc.prompts.composer import _intensity_guidance

    monkeypatch.setattr(config, "D5_ACUITY_GATE_ENABLED", True)
    monkeypatch.setattr(config, "D5_ACUITY_FLOOR", 8)

    result = _intensity_guidance(8)
    assert "do not challenge" in result.lower()


# ---------------------------------------------------------------------------
# (d) Flag ON + mid/low intensity -> unchanged (mid and low bands unaffected)
# ---------------------------------------------------------------------------

def test_d5_gate_on_mid_intensity_unchanged(monkeypatch):
    """Flag ON + intensity 5 (mid): must return original mid guidance string unchanged."""
    from sage_poc import config
    from sage_poc.prompts.composer import _INTENSITY_GUIDANCE, _intensity_guidance

    monkeypatch.setattr(config, "D5_ACUITY_GATE_ENABLED", True)
    monkeypatch.setattr(config, "D5_ACUITY_FLOOR", 8)

    result = _intensity_guidance(5)
    assert result == _INTENSITY_GUIDANCE["mid"], (
        f"Mid-intensity must be unchanged when gate is ON. Got: {result!r}"
    )


def test_d5_gate_on_low_intensity_unchanged(monkeypatch):
    """Flag ON + intensity 2 (low): must return original low guidance string unchanged."""
    from sage_poc import config
    from sage_poc.prompts.composer import _INTENSITY_GUIDANCE, _intensity_guidance

    monkeypatch.setattr(config, "D5_ACUITY_GATE_ENABLED", True)
    monkeypatch.setattr(config, "D5_ACUITY_FLOOR", 8)

    result = _intensity_guidance(2)
    assert result == _INTENSITY_GUIDANCE["low"], (
        f"Low-intensity must be unchanged when gate is ON. Got: {result!r}"
    )


# ---------------------------------------------------------------------------
# Config defaults
# ---------------------------------------------------------------------------

def test_d5_flag_defaults_false():
    """D5_ACUITY_GATE_ENABLED must default to False (gate off by default)."""
    from sage_poc import config
    assert config.D5_ACUITY_GATE_ENABLED is False, (
        f"D5_ACUITY_GATE_ENABLED must default to False. Got: {config.D5_ACUITY_GATE_ENABLED!r}"
    )


def test_d5_floor_defaults_8():
    """D5_ACUITY_FLOOR must default to 8."""
    from sage_poc import config
    assert config.D5_ACUITY_FLOOR == 8, (
        f"D5_ACUITY_FLOOR must default to 8. Got: {config.D5_ACUITY_FLOOR!r}"
    )


# ---------------------------------------------------------------------------
# Step 4 regression: composed-prompt level D5 swap with planted distortion
# ---------------------------------------------------------------------------

# Minimal state template reused by both regression tests below.
# All keys consumed by compose_prompt are present; optional ones default
# to None/empty so no code path hits a missing-key KeyError.
def _make_state(message_en: str, raw_message: str, language: str, intensity: int) -> dict:
    return {
        "raw_message": raw_message,
        "message_en": message_en,
        "detected_language": language,
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "emotional_intensity": intensity,
        "engagement": 4,
        "active_skill_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "rule_fired": None,
        "escalation_triggered": None,
        "clinical_flags": [],
        "crisis_state": "none",
        "third_party_crisis": False,
        "code_switching": False,
        "s7_result": None,
        "conversation_history": [],
        "conversation_summary": None,
        "therapeutic_profile": None,
        "knowledge_passages": [],
        "knowledge_abstain": False,
        "stale_skill_id": None,
        "banned_opener_correction": None,
        "offered_skill_ids": None,
        "offer_count": None,
        "declined_skills": None,
        "directive_posture": False,
        "stall_detected": False,
    }


def test_d5_gate_on_composed_prompt_en_planted_distortion(monkeypatch):
    """Step 4 regression (EN): gate ON, intensity=8, planted cognitive distortion.

    Planted message: 'I am completely worthless, no one would miss me if I stopped caring'
    This is a clinically relevant cognitive distortion (all-or-nothing thinking,
    catastrophising) but NOT explicit self-harm language, so it must not trigger
    the crisis path. The gate swap must appear at the composed-prompt level, not
    just at _intensity_guidance level.

    Limitation: compose_prompt calls rules_engine.evaluate on the planted message.
    The rules engine may inject additional system content, but the D5 guidance
    appears exclusively in the L2 intent block (via _build_l2_intent_block ->
    _intensity_guidance) so its presence or absence is observable in user_str
    regardless of rules-engine injections.
    """
    from sage_poc import config
    from sage_poc.prompts.composer import compose_prompt, _D5_ACUITY_GUIDANCE, _INTENSITY_GUIDANCE

    monkeypatch.setattr(config, "D5_ACUITY_GATE_ENABLED", True)
    monkeypatch.setattr(config, "D5_ACUITY_FLOOR", 8)

    message = "I am completely worthless, no one would miss me if I stopped caring"
    state = _make_state(
        message_en=message,
        raw_message=message,
        language="en",
        intensity=8,
    )
    _, user_str, _ = compose_prompt(state)

    # D5 directive text must appear verbatim in the composed user prompt.
    assert "Do not challenge or question a distorted belief" in user_str, (
        f"D5 guidance must appear in composed user_str when gate is ON and intensity=8. "
        f"user_str excerpt: {user_str[:400]!r}"
    )
    assert "purely supportive" in user_str.lower(), (
        f"D5 'purely supportive' directive must appear in composed user_str. "
        f"user_str excerpt: {user_str[:400]!r}"
    )

    # The original high-band 'Do NOT paraphrase or reflect back' phrase must be absent,
    # confirming the swap happened and the old directive is not leaking through.
    assert "Do NOT paraphrase or reflect back" not in user_str, (
        f"Original high-band phrase must NOT appear when D5 gate is ON and intensity=8. "
        f"user_str excerpt: {user_str[:400]!r}"
    )


def test_d5_gate_on_composed_prompt_ar_planted_distortion(monkeypatch):
    """Step 4 regression (Khaleeji Arabic): gate ON, intensity=8, planted cognitive distortion.

    Planted Arabic message: a clinically neutral all-or-nothing distortion using
    Emirati Arabic forms (shno -> not used here; ما عندي قيمة is standard Gulf phrasing).
    The message is NOT explicit self-harm, so crisis path must not fire.
    When language='ar', compose_prompt injects the ARABIC SESSION block into system_str
    but D5 guidance still lands in user_str via the L2 intent block.

    Limitation: same rules-engine caveat as the EN test above.
    """
    from sage_poc import config
    from sage_poc.prompts.composer import compose_prompt, _D5_ACUITY_GUIDANCE, _INTENSITY_GUIDANCE

    monkeypatch.setattr(config, "D5_ACUITY_GATE_ENABLED", True)
    monkeypatch.setattr(config, "D5_ACUITY_FLOOR", 8)

    # Khaleeji Arabic: "I have no value, no one needs me" -- all-or-nothing distortion,
    # not a direct self-harm disclosure.
    raw_ar = "ما عندي قيمة، ما أحد يحتاجني"
    # English translation passed as message_en (as the delivery pipeline does).
    message_en = "I have no value, no one needs me"

    state = _make_state(
        message_en=message_en,
        raw_message=raw_ar,
        language="ar",
        intensity=8,
    )
    _, user_str, _ = compose_prompt(state)

    # D5 directive text must appear verbatim in the composed user prompt.
    assert "Do not challenge or question a distorted belief" in user_str, (
        f"D5 guidance must appear in composed user_str (AR session, intensity=8). "
        f"user_str excerpt: {user_str[:400]!r}"
    )
    assert "purely supportive" in user_str.lower(), (
        f"D5 'purely supportive' directive must appear in composed user_str (AR session). "
        f"user_str excerpt: {user_str[:400]!r}"
    )

    # The original high-band phrase must be absent.
    assert "Do NOT paraphrase or reflect back" not in user_str, (
        f"Original high-band phrase must NOT appear when D5 gate is ON and intensity=8 (AR). "
        f"user_str excerpt: {user_str[:400]!r}"
    )
