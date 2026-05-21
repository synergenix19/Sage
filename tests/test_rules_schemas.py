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
