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
