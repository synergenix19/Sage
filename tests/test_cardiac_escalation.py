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

# Signed phrasing-CLASS fixtures (approval record item 2, 2026-08-19 — Vee, PO relay; PERMANENT
# paraphrase-only eval set per the portability clause; fixture-independence signed).
_FX_CLASS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "tests/fixtures/bot_behaviour_audit/cardiac_phrasing_class_2026-08-19.json")
_FIX_CLASS = json.load(open(_FX_CLASS))
_CLASS_FIRES = _FIX_CLASS["sec_cardiac_class_fires"]["cases"]
_CLASS_MUST_NOT = _FIX_CLASS["sec_cardiac_class_must_not_fire"]["cases"]


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


# --- Signed phrasing-CLASS (approval record item 2, 2026-08-19) ------------------------------------


def test_signed_class_paraphrases_all_fire():
    """Every family member fires on a PARAPHRASE (never a pattern string): 1C-3 pinned verbatim
    (the 2026-08-18 measured miss) + pressure, heaviness, spreading pain, stabbing, one-sided
    numbness, crushing, searing+jaw. Behavior-anchored: the predicate, not prose."""
    for text in _CLASS_FIRES:
        assert cardiac_ambiguous_present(text, text) is True, f"signed class must escalate: {text!r}"


def test_signed_not_boundary_never_fires():
    """The signed NOT-boundary: panic breathlessness / anxiety framing (incl. bare 'crushing' with
    no chest region) and the two §1c presence-cell shapes (self_help_skill cells) never fire."""
    for text in _CLASS_MUST_NOT:
        assert cardiac_ambiguous_present(text, text) is False, f"must NOT fire: {text!r}"


def test_fixture_independence_no_case_is_a_pattern_string():
    """SIGNED fixture-independence: no eval case may BE one of the rule's own pattern strings
    (the E7 verbatim-match lesson — a fixture=pattern tautology proves nothing about recall)."""
    from sage_poc.safety import cardiac_escalation as ce
    patterns = {p.lower() for p in (
        tuple(ce.CARDIAC_CLASS_PATTERNS) + tuple(ce._AIR_HUNGER) + tuple(ce._CHEST_REGION)
        + tuple(ce._PAIN_CONTEXT) + tuple(ce._RADIATION_VERBS) + tuple(ce._CHEST_SYMPTOM)
    )}
    for text in list(_CLASS_FIRES) + list(_CLASS_MUST_NOT):
        assert text.lower().strip() not in patterns, f"fixture equals a pattern string: {text!r}"


def test_class_fire_cases_never_grounded_by_panic_override():
    """Altitude precedence, both directions of the regression rule: once Node-1 stamps the cardiac
    flag, panic_override can never ground the turn (crisis_flags kills the override predicate) —
    the widening cannot be undone at the override's altitude."""
    for text in _CLASS_FIRES:
        state = {"message_en": text, "raw_message": text, "primary_intent": "crisis",
                 "crisis_flags": [CARDIAC_FLAG_ID], "s3_score": 0.0, "medical_flags": []}
        assert panic_override.should_ground_over_crisis(state) is False, f"grounded a red-flag turn: {text!r}"


def test_grounding_capability_survives_on_not_boundary_paraphrases():
    """Regression-by-improvement guard (other direction): the signed §1c-A grounding capability
    survives the widening — on a clean panic-breathlessness turn the cardiac rule contributes no
    crisis flag, and a turn carrying the override's own panic signature is STILL groundable."""
    grounded_any = False
    for text in _CLASS_MUST_NOT[:5]:  # the panic-framing paraphrases (presence cells route elsewhere)
        assert cardiac_ambiguous_present(text, text) is False
        state = {"message_en": text, "raw_message": text, "primary_intent": "crisis",
                 "crisis_flags": [], "s3_score": 0.0, "medical_flags": []}
        grounded_any = grounded_any or panic_override.should_ground_over_crisis(state)
    assert grounded_any, "widening must not kill the §1c-A grounding capability outright"


def test_deference_and_escalation_agree_on_the_class():
    """The conjunction the override refuses to ground is exactly the one Node-1 escalates: for every
    characterized cardiac case, should_ground_over_crisis defers AND cardiac_ambiguous_present fires."""
    for text in _CARDIAC:
        state = {"message_en": text, "raw_message": text, "primary_intent": "crisis",
                 "crisis_flags": [], "s3_score": 0.5, "medical_flags": []}
        assert panic_override.should_ground_over_crisis(state) is False
        assert cardiac_ambiguous_present(text, text) is True
