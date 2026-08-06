"""Node-1 cardiac-ambiguous deterministic escalation — BUILT INERT (item-3 realization, 2026-07-31).

Both-direction discipline: the class escalates (all three characterized variants) AND the signed
grounding capability survives (pure panic without death-fear, death-fear without air-hunger). Fixtures
reuse the RULED boundary oracle (sec_cardiac_ambiguous_stays_crisis) so the override's deference and this
escalation are driven by the same cases. Flag-OFF byte-identity is asserted at the config gate.
"""
import importlib
import json
import os

from sage_poc.safety.cardiac_escalation import cardiac_ambiguous_present, CARDIAC_FLAG_ID
from sage_poc.nodes import panic_override

_FX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "tests/fixtures/bot_behaviour_audit/part_a_1c_boundary_PROPOSED.json")
_FIX = json.load(open(_FX))
_CARDIAC = _FIX["sec_cardiac_ambiguous_stays_crisis"]["cases"]
_PURE_PANIC = _FIX["sec_1c_A_force_ground_when_clean"]["cases"]


def test_characterized_cardiac_variants_all_fire():
    for text in _CARDIAC:
        assert cardiac_ambiguous_present(text, text) is True, f"must escalate: {text!r}"


def test_pure_panic_without_death_fear_does_not_fire():
    """The signed §1c-A grounding capability survives: no death-fear term -> no escalation."""
    for text in _PURE_PANIC:
        if any(d in text.lower() for d in panic_override._DEATH_FEAR):
            continue  # a §1c-A case carrying death-fear is the override's own territory, not this test's
        assert cardiac_ambiguous_present(text, text) is False, f"must NOT fire: {text!r}"


def test_death_fear_without_air_hunger_does_not_fire():
    assert cardiac_ambiguous_present(
        "I feel like I'm going to die, my heart is pounding out of my chest", "") is False


def test_air_hunger_without_death_fear_does_not_fire():
    assert cardiac_ambiguous_present("I can't breathe and my chest is tight, panic attack", "") is False


def test_single_source_with_panic_override():
    """The escalation's term sets ARE the override's (imported identity, never copied) — the deference
    and the escalation cannot drift apart."""
    from sage_poc.safety import cardiac_escalation as ce
    assert ce._DEATH_FEAR is panic_override._DEATH_FEAR
    assert ce._AIR_HUNGER is panic_override._AIR_HUNGER


def test_flag_default_off_and_strict_parse(monkeypatch):
    """Kill-switch discipline: unset/garbage -> OFF; only literal 'true' enables."""
    from sage_poc import config
    for raw, expect in ((None, False), ("garbage", False), ("false", False), ("TRUE", True), ("true", True)):
        if raw is None:
            monkeypatch.delenv("SAGE_CARDIAC_ESCALATION", raising=False)
        else:
            monkeypatch.setenv("SAGE_CARDIAC_ESCALATION", raw)
        importlib.reload(config)
        assert config.CARDIAC_ESCALATION_ENABLED is expect, f"raw={raw!r}"
    monkeypatch.delenv("SAGE_CARDIAC_ESCALATION", raising=False)
    importlib.reload(config)
    assert config.CARDIAC_ESCALATION_ENABLED is False


def test_deference_and_escalation_agree_on_the_class():
    """The conjunction the override refuses to ground is exactly the one Node-1 escalates: for every
    characterized cardiac case, should_ground_over_crisis defers AND cardiac_ambiguous_present fires."""
    for text in _CARDIAC:
        state = {"message_en": text, "raw_message": text, "primary_intent": "crisis",
                 "crisis_flags": [], "s3_score": 0.5, "medical_flags": []}
        assert panic_override.should_ground_over_crisis(state) is False
        assert cardiac_ambiguous_present(text, text) is True
