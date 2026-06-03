"""Tests for CF-006 psychotic_disclosure clinical flag detection.

Tests call _eval_safety() directly to bypass the rules loader's active-flag
filter. This ensures detection and precision logic is exercised regardless of
the deployment flag. active=True is set explicitly in the test fixture.
"""
import pytest
from sage_poc.rules.engine import _eval_safety
from sage_poc.rules.schemas import SafetyRule


def _make_cf006_rule(**overrides) -> SafetyRule:
    """Construct a live CF-006 rule for test use. active=True always."""
    data = {
        "rule_id": "CF-006",
        "version": "1.0.0",
        "authored_by": "sage_clinics",
        "effective_date": "2026-06-03",
        "active": True,
        "description": "Psychotic symptom disclosure",
        "category": "safety",
        "match_type": "keyword",
        "patterns": [
            "hearing voices",
            "i hear voices",
            "voices in my head",
            "seeing things that aren't there",
            "seeing things that are not there",
            "seeing things no one else sees",
            "people are watching me",
            "someone is following me",
            "أسمع أصوات",
            "في أصوات تكلمني",
            "أشوف أشياء ما أحد يشوفها",
            "أحد يراقبني",
        ],
        "language": "any",
        "modifiers": [],
        "action": {"type": "clinical_flag", "flag_id": "psychotic_disclosure"},
    }
    data.update(overrides)
    return SafetyRule.model_validate(data)


_CF006 = _make_cf006_rule()


def _flags(text_en, text_ar=None, language="en"):
    result = _eval_safety([_CF006], {
        "text_en": text_en,
        "text_ar": text_ar or "",
        "language": language,
    })
    return [a["flag_id"] for a in result.actions if a.get("type") == "clinical_flag"]


# --- Detection ---

def test_hearing_voices_sets_flag():
    assert "psychotic_disclosure" in _flags("I've been hearing voices in my head")

def test_i_hear_voices_sets_flag():
    assert "psychotic_disclosure" in _flags("I hear voices all the time")

def test_voices_in_my_head_sets_flag():
    assert "psychotic_disclosure" in _flags("there are voices in my head that won't stop")

def test_seeing_things_not_there_sets_flag():
    assert "psychotic_disclosure" in _flags("I keep seeing things that aren't there")

def test_arabic_hearing_voices():
    assert "psychotic_disclosure" in _flags("", text_ar="أسمع أصوات", language="ar")

def test_arabic_voices_talking():
    assert "psychotic_disclosure" in _flags("", text_ar="في أصوات تكلمني كل يوم", language="ar")

def test_people_watching_sets_flag():
    assert "psychotic_disclosure" in _flags("I feel like people are watching me everywhere I go")

def test_someone_following_sets_flag():
    assert "psychotic_disclosure" in _flags("someone is following me I'm sure of it")

def test_seeing_things_no_apostrophe_sets_flag():
    assert "psychotic_disclosure" in _flags("I keep seeing things that are not there")

def test_arabic_paranoid_ideation():
    assert "psychotic_disclosure" in _flags("", text_ar="أحد يراقبني", language="ar")

def test_arabic_visual_hallucination():
    assert "psychotic_disclosure" in _flags("", text_ar="أشوف أشياء ما أحد يشوفها", language="ar")

# --- Precision ---

def test_stress_does_not_trigger():
    assert "psychotic_disclosure" not in _flags("I've been feeling stressed")

def test_mothers_voice_does_not_trigger():
    # "hearing my mother's voice" does NOT contain "hearing voices" as contiguous substring
    assert "psychotic_disclosure" not in _flags("I keep hearing my mother's voice telling me to do better")

def test_choir_voices_does_not_trigger():
    assert "psychotic_disclosure" not in _flags("I love hearing the voices of the choir")

def test_si_phrase_does_not_trigger_psychotic():
    assert "psychotic_disclosure" not in _flags("I want to end my life")

# --- No cross-contamination ---

def test_psychotic_disclosure_is_clinical_not_crisis():
    result = _eval_safety([_CF006], {"text_en": "I've been hearing voices", "text_ar": "", "language": "en"})
    crisis = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert len(crisis) == 0, "psychotic_disclosure is a clinical_flag, not a crisis_flag"
