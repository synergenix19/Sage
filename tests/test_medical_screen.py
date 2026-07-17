"""D1 medical screening question (#338) — deterministic core, red-verified BOTH directions.

Spec L58/L101 discriminating quality-check. Architecture (V-signed): conversational question, deterministic
consequence. This tests the consequence — classifier + branch table + trigger + placeholder guard. The
FAIL-SAFE invariant is the safety property: the screen routes AWAY, never CLEARS — only clear_no proceeds
and only a red-flag-quality answer escalates; EVERYTHING else defaults to the contraindication-free skill.
"""
import pytest
from sage_poc.safety import medical_screen as ms


# ── classifier: every answer maps to exactly one class (red-verified both directions) ──
@pytest.mark.parametrize("text,expect", [
    ("no, it's the same as always", "clear_no"),
    ("nothing different, just my usual anxiety", "clear_no"),
    ("yeah it's spreading to my arm", "red_flag"),
    ("real trouble breathing, not like normal", "red_flag"),
    ("numbness on one side", "red_flag"),
    ("kind of? maybe a bit different", "yes"),
    ("it's kind of both honestly", "unclear"),
    ("i don't know", "unclear"),
    ("anyway, my week has been rough", "no_answer"),   # topic-change
    ("", "no_answer"),
])
def test_classify_screen_answer(text, expect):
    assert ms.classify_screen_answer(text) == expect


# ── branch table + FAIL-SAFE: away-never-clears ──
@pytest.mark.parametrize("cls,route", [
    ("clear_no", "proceed"),
    ("red_flag", "medical_guard"),
    ("yes", "grounding"),
    ("unclear", "grounding"),
    ("no_answer", "grounding"),
])
def test_route_screen_answer(cls, route):
    assert ms.route_screen_answer(cls) == route


def test_failsafe_unknown_class_routes_grounding():
    # Any class the table doesn't recognise MUST default to grounding, never proceed.
    assert ms.route_screen_answer("some_new_unmapped_class") == "grounding"


def test_screen_only_clears_on_clear_no():
    # The invariant, stated as a property: 'proceed' is reachable ONLY from clear_no.
    proceeders = [c for c in ("clear_no", "red_flag", "yes", "unclear", "no_answer")
                  if ms.route_screen_answer(c) == "proceed"]
    assert proceeders == ["clear_no"]


# ── trigger: fires on physical-symptom-WITHOUT-red-flag-keyword (the ambiguous middle) ──
def test_trigger_fires_on_ambiguous_physical_symptom():
    assert ms.is_physical_symptom_ambiguous("my chest feels different and it's hard to breathe")

def test_trigger_semantic_no_listed_keyword():
    # "weird pressure thing in my body" mentions no listed symptom keyword — the recall-biased net.
    assert ms.is_physical_symptom_ambiguous("there's this weird pressure thing happening in my body")

def test_trigger_does_not_fire_on_nonphysical():
    assert not ms.is_physical_symptom_ambiguous("i feel anxious about my presentation tomorrow")

def test_trigger_does_not_fire_when_redflag_already_present():
    # explicit red-flag keyword already goes straight to the guard — the screen is for the AMBIGUOUS case.
    assert not ms.is_physical_symptom_ambiguous("i have crushing chest pain spreading to my arm")


# ── placeholder guard: question is UNSERVABLE until Vee's signed bytes land ──
def test_question_unservable_until_signed():
    with pytest.raises(ms.UnsignedScreenError):
        ms.screen_question("en")

def test_is_screen_ready_false_before_signoff():
    assert ms.is_screen_ready("en") is False
