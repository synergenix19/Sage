# tests/test_rules_engine.py
import pytest
from unittest.mock import patch
from sage_poc.rules.schemas import SafetyRule, CulturalRule, PromptInjectionRule, EvalResult
from sage_poc.rules import engine


_BASE = {
    "version": "1.0.0", "authored_by": "test",
    "effective_date": "2026-05-21", "active": True,
}


# ── Safety evaluator ────────────────────────────────────────────────────────

def _safety_rule(rule_id, patterns, language="en", modifiers=None):
    return SafetyRule(**{
        **_BASE,
        "rule_id": rule_id,
        "category": "safety",
        "match_type": "keyword",
        "patterns": patterns,
        "language": language,
        "modifiers": modifiers or [],
        "action": {"type": "crisis_flag", "flag_id": "si_test"},
    })


def test_safety_keyword_match_fires():
    rules = [_safety_rule("T1", ["want to die"])]
    ctx = {"text_en": "I want to die", "text_ar": None, "language": "en"}
    result = engine._eval_safety(rules, ctx)
    assert "T1" in result.fired_ids


def test_safety_keyword_no_match():
    rules = [_safety_rule("T1", ["want to die"])]
    ctx = {"text_en": "I want to live fully", "text_ar": None, "language": "en"}
    result = engine._eval_safety(rules, ctx)
    assert result.fired == []


def test_safety_negation_suppresses_match():
    rules = [_safety_rule("T1", ["want to die"], modifiers=["negation_check"])]
    ctx = {"text_en": "I don't want to die", "text_ar": None, "language": "en"}
    result = engine._eval_safety(rules, ctx)
    assert result.fired == []


def test_safety_negation_does_not_suppress_without_modifier():
    rules = [_safety_rule("T1", ["want to die"], modifiers=[])]
    ctx = {"text_en": "I don't want to die", "text_ar": None, "language": "en"}
    result = engine._eval_safety(rules, ctx)
    # No negation_check modifier → still fires (keyword substring present)
    assert "T1" in result.fired_ids


def test_safety_arabic_rule_matches_normalized_text():
    # Arabic rule with alef-hamza pattern; input has alef-hamza variant
    rules = [_safety_rule("T2", ["ابي اموت"], language="ar", modifiers=[])]
    # Input: أبي أموت (with alef-hamza-above) — normalized to ابي اموت
    ctx = {"text_en": "want to die", "text_ar": "أبي أموت", "language": "ar"}
    result = engine._eval_safety(rules, ctx)
    assert "T2" in result.fired_ids


def test_safety_arabic_rule_matches_diacritic_variant():
    # Input has full harakat; rule pattern has no harakat
    rules = [_safety_rule("T2", ["ابي اموت"], language="ar")]
    ctx = {"text_en": "i want to die", "text_ar": "أَبِي أَمُوتُ", "language": "ar"}
    result = engine._eval_safety(rules, ctx)
    assert "T2" in result.fired_ids


def test_safety_multiple_rules_all_evaluated():
    rules = [
        _safety_rule("T1", ["want to die"]),
        _safety_rule("T2", ["no reason to live"]),
    ]
    ctx = {"text_en": "I want to die, there is no reason to live", "language": "en"}
    result = engine._eval_safety(rules, ctx)
    assert "T1" in result.fired_ids
    assert "T2" in result.fired_ids


def test_safety_inactive_rule_skipped():
    rule = SafetyRule(**{
        **_BASE,
        "rule_id": "T1",
        "category": "safety",
        "match_type": "keyword",
        "patterns": ["want to die"],
        "active": False,
        "action": {"type": "crisis_flag", "flag_id": "si_test"},
    })
    # loader only returns active rules, but test engine directly with inactive rule
    rules = [rule]
    ctx = {"text_en": "I want to die", "language": "en"}
    # The engine receives rules from loader; loader filters inactive.
    # Here we test the engine with the rule passed in — engine trusts what loader gives it.
    result = engine._eval_safety(rules, ctx)
    assert "T1" in result.fired_ids  # engine does NOT filter; loader does


# ── Cultural evaluator ───────────────────────────────────────────────────────

def _cultural_rule(rule_id, keywords, language="any"):
    return CulturalRule(**{
        **_BASE,
        "rule_id": rule_id,
        "category": "cultural",
        "trigger_keywords": keywords,
        "language": language,
        "action": {"type": "prompt_injection", "target": "system", "content": f"[{rule_id}]"},
    })


def test_cultural_rule_fires_on_keyword():
    rules = [_cultural_rule("C1", ["allah", "faith"])]
    ctx = {"text": "I feel distant from my faith", "language": "en"}
    result = engine._eval_cultural(rules, ctx)
    assert "C1" in result.fired_ids


def test_cultural_rule_no_match():
    rules = [_cultural_rule("C1", ["allah", "faith"])]
    ctx = {"text": "I feel anxious about my exam", "language": "en"}
    result = engine._eval_cultural(rules, ctx)
    assert result.fired == []


def test_cultural_rule_language_filter():
    rules = [_cultural_rule("C1", ["الله"], language="ar")]
    ctx = {"text": "", "text_ar": "الله يساعدني", "language": "ar"}
    result = engine._eval_cultural(rules, ctx)
    assert "C1" in result.fired_ids


def test_cultural_rule_language_mismatch_does_not_fire():
    rules = [_cultural_rule("C1", ["الله"], language="ar")]
    ctx = {"text": "الله يساعدني", "language": "en"}  # language="en" but rule requires "ar"
    result = engine._eval_cultural(rules, ctx)
    assert result.fired == []


def test_cultural_accumulates_multiple_matches():
    rules = [
        _cultural_rule("C1", ["allah"]),
        _cultural_rule("C2", ["family"]),
    ]
    ctx = {"text": "My family and my faith in allah help me", "language": "en"}
    result = engine._eval_cultural(rules, ctx)
    assert "C1" in result.fired_ids
    assert "C2" in result.fired_ids


# ── Prompt injection evaluator ───────────────────────────────────────────────

def _pi_rule(rule_id, trigger_type, trigger_value=None, trigger_keywords=None):
    return PromptInjectionRule(**{
        **_BASE,
        "rule_id": rule_id,
        "category": "prompt_injection",
        "trigger_type": trigger_type,
        "trigger_value": trigger_value,
        "trigger_keywords": trigger_keywords or [],
        "action": {"type": "inject", "target": "system", "content": f"[{rule_id}]"},
    })


def test_pi_flag_present_fires():
    rules = [_pi_rule("P1", "flag_present", trigger_value="substance_use")]
    ctx = {"clinical_flags": ["substance_use"], "primary_intent": None, "secondary_intent": None, "text": ""}
    result = engine._eval_prompt_injection(rules, ctx)
    assert "P1" in result.fired_ids


def test_pi_flag_present_does_not_fire_when_absent():
    rules = [_pi_rule("P1", "flag_present", trigger_value="substance_use")]
    ctx = {"clinical_flags": ["trauma_indicator"], "primary_intent": None, "secondary_intent": None, "text": ""}
    result = engine._eval_prompt_injection(rules, ctx)
    assert result.fired == []


def test_pi_secondary_intent_present_fires():
    rules = [_pi_rule("P2", "secondary_intent_present")]
    ctx = {"clinical_flags": [], "primary_intent": "new_skill", "secondary_intent": "info_request", "text": ""}
    result = engine._eval_prompt_injection(rules, ctx)
    assert "P2" in result.fired_ids


def test_pi_secondary_intent_present_does_not_fire_when_none():
    rules = [_pi_rule("P2", "secondary_intent_present")]
    ctx = {"clinical_flags": [], "primary_intent": "new_skill", "secondary_intent": None, "text": ""}
    result = engine._eval_prompt_injection(rules, ctx)
    assert result.fired == []


def test_pi_intent_match_fires_on_primary():
    rules = [_pi_rule("P3", "intent_match", trigger_value="info_request")]
    ctx = {"clinical_flags": [], "primary_intent": "info_request", "secondary_intent": None, "text": ""}
    result = engine._eval_prompt_injection(rules, ctx)
    assert "P3" in result.fired_ids


def test_pi_intent_match_fires_on_secondary():
    rules = [_pi_rule("P3", "intent_match", trigger_value="info_request")]
    ctx = {"clinical_flags": [], "primary_intent": "new_skill", "secondary_intent": "info_request", "text": ""}
    result = engine._eval_prompt_injection(rules, ctx)
    assert "P3" in result.fired_ids


# ── Top-level evaluate() dispatch ───────────────────────────────────────────

def test_evaluate_dispatches_to_safety(monkeypatch):
    """evaluate() with mocked loader calls _eval_safety."""
    monkeypatch.setattr("sage_poc.rules.engine.get_rules", lambda cat: [
        _safety_rule("T1", ["want to die"]) if cat == "safety" else []
    ])
    result = engine.evaluate("safety", {"text_en": "I want to die", "language": "en"})
    assert "T1" in result.fired_ids


def test_evaluate_raises_on_unknown_category():
    with pytest.raises(ValueError, match="Unknown rule category"):
        engine.evaluate("nonexistent", {})


# ── Suppression modifier ─────────────────────────────────────────────────────

def test_apply_suppressions_marks_suppressed_flag():
    from sage_poc.rules.engine import _apply_suppressions
    from sage_poc.rules.schemas import FiredRule, EvalResult
    # Both rules fired on the same text span (0, 13) — suppression applies
    crisis = FiredRule("SK-AR-001", "1.0.0", {"type": "crisis_flag", "flag_id": "si_passive"},
                       matched_span=(0, 13))
    suppressor = FiredRule("FPE-AR-001", "1.0.0", {"type": "crisis_suppress", "suppresses": ["si_passive"]},
                           matched_span=(0, 13))
    result = EvalResult(fired=[crisis, suppressor])
    result = _apply_suppressions(result)
    assert crisis.suppressed is True
    assert suppressor.suppressed is False


def test_apply_suppressions_leaves_non_matching_flag_active():
    from sage_poc.rules.engine import _apply_suppressions
    from sage_poc.rules.schemas import FiredRule, EvalResult
    explicit = FiredRule("SK-EN-001", "1.0.0", {"type": "crisis_flag", "flag_id": "si_explicit"})
    suppressor = FiredRule("FPE-AR-001", "1.0.0", {"type": "crisis_suppress", "suppresses": ["si_passive"]})
    result = EvalResult(fired=[explicit, suppressor])
    result = _apply_suppressions(result)
    assert explicit.suppressed is False  # si_explicit not in suppresses list


def test_apply_suppressions_noop_when_no_suppressors():
    from sage_poc.rules.engine import _apply_suppressions
    from sage_poc.rules.schemas import FiredRule, EvalResult
    crisis = FiredRule("SK-EN-001", "1.0.0", {"type": "crisis_flag", "flag_id": "si_explicit"})
    result = EvalResult(fired=[crisis])
    result = _apply_suppressions(result)
    assert crisis.suppressed is False


def test_apply_suppressions_handles_multiple_suppresses_values():
    from sage_poc.rules.engine import _apply_suppressions
    from sage_poc.rules.schemas import FiredRule, EvalResult
    # All three rules fired on the same span — both SI flags are suppressed
    r1 = FiredRule("SK-1", "1.0.0", {"type": "crisis_flag", "flag_id": "si_explicit"},
                   matched_span=(0, 10))
    r2 = FiredRule("SK-2", "1.0.0", {"type": "crisis_flag", "flag_id": "si_passive"},
                   matched_span=(0, 10))
    suppressor = FiredRule("FPE-1", "1.0.0", {"type": "crisis_suppress", "suppresses": ["si_explicit", "si_passive"]},
                           matched_span=(0, 10))
    result = EvalResult(fired=[r1, r2, suppressor])
    result = _apply_suppressions(result)
    assert r1.suppressed is True
    assert r2.suppressed is True


def test_apply_suppressions_none_span_does_not_suppress():
    """If matched_span is None on either side, suppression must NOT fire.

    Missing span data means we cannot determine overlap. The safe default is
    to let the crisis flag through rather than silently suppress a potential
    genuine signal. This tests the behavior introduced by the span-scoped fix.
    """
    from sage_poc.rules.engine import _apply_suppressions
    from sage_poc.rules.schemas import FiredRule, EvalResult
    # SI rule has no span (matched_span=None)
    crisis_no_span = FiredRule("SK-1", "1.0.0", {"type": "crisis_flag", "flag_id": "si_passive"},
                               matched_span=None)
    suppressor = FiredRule("FPE-1", "1.0.0", {"type": "crisis_suppress", "suppresses": ["si_passive"]},
                           matched_span=(0, 10))
    result = EvalResult(fired=[crisis_no_span, suppressor])
    result = _apply_suppressions(result)
    assert crisis_no_span.suppressed is False, \
        "Crisis flag with None span must NOT be suppressed — safe default is to let it through"

    # FPE rule has no span
    crisis_with_span = FiredRule("SK-2", "1.0.0", {"type": "crisis_flag", "flag_id": "si_passive"},
                                 matched_span=(5, 20))
    suppressor_no_span = FiredRule("FPE-2", "1.0.0", {"type": "crisis_suppress", "suppresses": ["si_passive"]},
                                   matched_span=None)
    result2 = EvalResult(fired=[crisis_with_span, suppressor_no_span])
    result2 = _apply_suppressions(result2)
    assert crisis_with_span.suppressed is False, \
        "Crisis flag must NOT be suppressed when FPE rule has None span"


def test_eval_safety_applies_suppression_end_to_end():
    from sage_poc.rules.engine import _eval_safety
    from sage_poc.rules.schemas import SafetyRule
    crisis_rule = SafetyRule(
        rule_id="SK-TEST", version="1.0.0", category="safety",
        effective_date="2026-05-21", match_type="keyword",
        patterns=["ابي اموت"], language="ar",
        action={"type": "crisis_flag", "flag_id": "si_explicit"},
    )
    suppress_rule = SafetyRule(
        rule_id="FPE-TEST", version="1.0.0", category="safety",
        effective_date="2026-05-21", match_type="keyword",
        patterns=["ابي اموت من الضحك"], language="ar",
        action={"type": "crisis_suppress", "suppresses": ["si_explicit"]},
    )
    ctx = {"text_en": "dying of laughter", "text_ar": "ابي اموت من الضحك", "language": "ar"}
    result = _eval_safety([crisis_rule, suppress_rule], ctx)
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions == [], "Suppression should prevent crisis_flag from appearing in actions"
    assert len(result.suppressed_rules) == 1  # suppressed rule recorded for audit


# ── session_flag_present trigger type ────────────────────────────────────────

_BASE_PI = {
    "version": "1.0.0", "authored_by": "test",
    "effective_date": "2026-05-21", "active": True,
    "category": "prompt_injection",
    "trigger_keywords": [],
    "action": {"type": "inject", "target": "system", "content": "post-crisis"},
}

def test_pi_session_flag_present_fires_when_flag_set():
    rule = PromptInjectionRule(**{
        **_BASE_PI,
        "rule_id": "PI-PC-TEST",
        "trigger_type": "session_flag_present",
        "trigger_value": "crisis_occurred",
    })
    ctx = {"text": "I feel okay", "clinical_flags": [], "session_flags": ["crisis_occurred"]}
    result = engine._eval_prompt_injection([rule], ctx)
    assert result.fired_ids == ["PI-PC-TEST"]


def test_pi_session_flag_present_does_not_fire_when_absent():
    rule = PromptInjectionRule(**{
        **_BASE_PI,
        "rule_id": "PI-PC-TEST",
        "trigger_type": "session_flag_present",
        "trigger_value": "crisis_occurred",
    })
    ctx = {"text": "I feel okay", "clinical_flags": [], "session_flags": []}
    result = engine._eval_prompt_injection([rule], ctx)
    assert result.fired == []
