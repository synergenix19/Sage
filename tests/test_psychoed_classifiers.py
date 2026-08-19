# tests/test_psychoed_classifiers.py
from sage_poc.psychoed import classifiers
import pytest

pytestmark = pytest.mark.safety_gate

def test_lexical_distress_is_acute():
    assert classifiers.acute_distress({}, "what is anxiety? I can't breathe right now")

def test_numeric_self_report_is_acute():
    assert classifiers.acute_distress({}, "why do I feel like this, it's a 9/10")

def test_fragmented_message_is_acute():
    assert classifiers.acute_distress({}, "help. now. please. why")

def test_upstream_safety_state_is_acute():
    assert classifiers.acute_distress({"crisis_state": "monitoring"}, "what is anxiety?")

def test_calm_curiosity_is_not_acute():
    assert not classifiers.acute_distress({}, "What is anxiety? I have always wondered how it works.")

def test_framing_fallback_is_personal():
    assert classifiers.FRAMING_FALLBACK == "personal"
    assert classifiers.framing_for_row({"framing": "abstract"}) == "abstract"
