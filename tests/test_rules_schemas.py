# tests/test_rules_schemas.py
import pytest
from pydantic import ValidationError
from sage_poc.rules.schemas import (
    SafetyRule, CrisisContentRule, CulturalRule, PromptInjectionRule,
    EvalResult, FiredRule,
)

_BASE = {
    "rule_id": "TEST-001",
    "version": "1.0.0",
    "authored_by": "test",
    "effective_date": "2026-05-21",
    "action": {"type": "crisis_flag", "flag_id": "si_explicit"},
}


def test_safety_rule_valid():
    rule = SafetyRule(**{
        **_BASE,
        "category": "safety",
        "match_type": "keyword",
        "patterns": ["want to die"],
        "language": "en",
        "modifiers": ["negation_check"],
    })
    assert rule.rule_id == "TEST-001"
    assert rule.active is True
    assert "negation_check" in rule.modifiers


def test_safety_rule_defaults():
    rule = SafetyRule(**{
        **_BASE,
        "category": "safety",
        "match_type": "keyword",
        "patterns": ["want to die"],
    })
    assert rule.language == "any"
    assert rule.modifiers == []


def test_safety_rule_rejects_bad_language():
    with pytest.raises(ValidationError):
        SafetyRule(**{
            **_BASE,
            "category": "safety",
            "match_type": "keyword",
            "patterns": ["test"],
            "language": "fr",  # not in allowed Literal
        })


def test_crisis_content_rule_valid():
    rule = CrisisContentRule(**{
        **_BASE,
        "category": "crisis_content",
        "locale": "en_uae",
        "crisis_level": "acute",
        "action": {
            "type": "crisis_response",
            "response_text": "Please call 999.",
            "resources": [],
        },
    })
    assert rule.locale == "en_uae"
    assert rule.crisis_level == "acute"


def test_cultural_rule_valid():
    rule = CulturalRule(**{
        **_BASE,
        "category": "cultural",
        "trigger_keywords": ["allah", "faith"],
        "action": {"type": "prompt_injection", "target": "system", "content": "..."},
    })
    assert rule.trigger_keywords == ["allah", "faith"]


def test_prompt_injection_rule_valid():
    rule = PromptInjectionRule(**{
        **_BASE,
        "category": "prompt_injection",
        "trigger_type": "flag_present",
        "trigger_value": "substance_use",
        "action": {"type": "inject", "target": "system", "content": "Use MI."},
    })
    assert rule.trigger_type == "flag_present"
    assert rule.trigger_value == "substance_use"


def test_inactive_rule_field():
    rule = SafetyRule(**{
        **_BASE,
        "category": "safety",
        "match_type": "keyword",
        "patterns": ["test"],
        "active": False,
    })
    assert rule.active is False


def test_eval_result_empty():
    result = EvalResult()
    assert result.fired == []
    assert result.actions == []
    assert result.fired_ids == []
    assert bool(result) is False


def test_eval_result_with_fired_rules():
    result = EvalResult()
    result.fired.append(FiredRule(
        rule_id="TEST-001",
        version="1.0.0",
        action={"type": "crisis_flag", "flag_id": "si_explicit"},
    ))
    assert len(result.actions) == 1
    assert result.actions[0]["flag_id"] == "si_explicit"
    assert result.fired_ids == ["TEST-001"]
    assert bool(result) is True


def test_fired_rule_suppressed_defaults_false():
    r = FiredRule(rule_id="X", version="1.0.0", action={"type": "crisis_flag"})
    assert r.suppressed is False


def test_eval_result_actions_excludes_suppressed():
    active = FiredRule(rule_id="A", version="1.0.0", action={"type": "crisis_flag", "flag_id": "si_explicit"})
    suppressed = FiredRule(rule_id="B", version="1.0.0", action={"type": "crisis_flag", "flag_id": "si_passive"}, suppressed=True)
    result = EvalResult(fired=[active, suppressed])
    assert len(result.actions) == 1
    assert result.actions[0]["flag_id"] == "si_explicit"


def test_eval_result_actions_excludes_crisis_suppress_type():
    suppress_mech = FiredRule(rule_id="FPE-1", version="1.0.0", action={"type": "crisis_suppress", "suppresses": ["si_passive"]})
    result = EvalResult(fired=[suppress_mech])
    assert result.actions == []


def test_eval_result_suppressed_rules_property():
    r1 = FiredRule(rule_id="A", version="1.0.0", action={"type": "crisis_flag"}, suppressed=True)
    r2 = FiredRule(rule_id="B", version="1.0.0", action={"type": "crisis_flag"})
    result = EvalResult(fired=[r1, r2])
    assert len(result.suppressed_rules) == 1
    assert result.suppressed_rules[0].rule_id == "A"


def test_fired_ids_includes_suppressed_for_audit():
    r = FiredRule(rule_id="SUPPRESSED", version="1.0.0", action={"type": "crisis_flag"}, suppressed=True)
    result = EvalResult(fired=[r])
    assert "SUPPRESSED" in result.fired_ids  # audit trail must preserve suppressed rule IDs


def test_eval_result_bool_false_when_all_suppressed():
    r = FiredRule(rule_id="A", version="1.0.0", action={"type": "crisis_flag"}, suppressed=True)
    result = EvalResult(fired=[r])
    assert bool(result) is False
    assert len(result.fired_ids) == 1  # audit trail still has it


def test_prompt_injection_rule_accepts_session_flag_present():
    rule = PromptInjectionRule(
        rule_id="PI-PC-001", category="prompt_injection",
        effective_date="2026-05-21",
        trigger_type="session_flag_present",
        trigger_value="crisis_occurred",
        action={"type": "inject", "target": "system", "content": "test"},
    )
    assert rule.trigger_type == "session_flag_present"
