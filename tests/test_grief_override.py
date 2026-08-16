"""S2a — deterministic grief-presence deference. BUILT INERT (2026-08-04); boundary sheet pending Vee.

Mirrors test_panic_override.py: the deference may restore presence ONLY when safety_check is CLEAN and
there is NO harm-adjacency; grief+harm is the ship-gate tripwire. Fixtures are the PROPOSED blind eval
set (paraphrase-independent where avoidable).
"""
import importlib
import json
import os

from sage_poc.nodes.grief_override import should_defer_grief_over_crisis
from sage_poc.nodes import panic_override

_FX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "tests/fixtures/bot_behaviour_audit/s2a_grief_boundary_PROPOSED.json")
_FIX = json.load(open(_FX))
_DEFER = _FIX["sec_grief_defer_when_clean"]["cases"]
_TRIP = _FIX["sec_grief_plus_harm_always_escalates_TRIPWIRE"]["cases"]
_CONTROLS = _FIX["sec_non_grief_controls"]["cases"]


def _clean_state(text, s3=0.5):
    return {"message_en": text, "raw_message": text, "primary_intent": "crisis",
            "crisis_flags": [], "s3_score": s3, "medical_flags": [], "clinical_flags": []}


def test_clean_bereavement_defers():
    for text in _DEFER:
        assert should_defer_grief_over_crisis(_clean_state(text)) is True, f"must defer: {text!r}"


def test_grief_plus_harm_NEVER_defers():
    """Ship gate: bereavement + harm-adjacency -> escalation stands, no exceptions."""
    for text in _TRIP:
        assert should_defer_grief_over_crisis(_clean_state(text)) is False, \
            f"MUST NOT defer (harm present): {text!r}"


def test_non_grief_controls_do_not_fire():
    for text in _CONTROLS:
        assert should_defer_grief_over_crisis(_clean_state(text)) is False, f"must NOT fire: {text!r}"


def test_never_fires_when_safety_check_flagged():
    """Includes the cardiac Node-1 flag when active: any crisis_flags -> deference dead."""
    st = _clean_state("my mother passed away and I can't cope")
    st["crisis_flags"] = ["cardiac_ambiguous_deterministic"]
    assert should_defer_grief_over_crisis(st) is False


def test_never_fires_over_s3_threshold():
    st = _clean_state("my mother passed away and I can't cope", s3=0.85)
    assert should_defer_grief_over_crisis(st) is False


def test_never_fires_on_medical_flag():
    st = _clean_state("my father died and my chest hurts")
    st["medical_flags"] = ["cardiac"]
    assert should_defer_grief_over_crisis(st) is False


def test_requires_intent_crisis():
    st = _clean_state("my mother passed away last month")
    st["primary_intent"] = "general_chat"
    assert should_defer_grief_over_crisis(st) is False


def test_harm_set_single_sourced_with_panic_override():
    """The harm language that stops panic-grounding stops grief-deference — imported identity."""
    from sage_poc.nodes import grief_override as go
    assert go._HARM_TERMS is panic_override._HARM_TERMS


def test_flag_default_off_and_strict_parse(monkeypatch):
    from sage_poc import config
    for raw, expect in ((None, False), ("garbage", False), ("false", False), ("true", True)):
        if raw is None:
            monkeypatch.delenv("SAGE_GRIEF_DEFERENCE", raising=False)
        else:
            monkeypatch.setenv("SAGE_GRIEF_DEFERENCE", raw)
        importlib.reload(config)
        assert config.GRIEF_DEFERENCE_ENABLED is expect, f"raw={raw!r}"
    monkeypatch.delenv("SAGE_GRIEF_DEFERENCE", raising=False)
    importlib.reload(config)
    assert config.GRIEF_DEFERENCE_ENABLED is False
