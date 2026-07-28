"""Part A — §1c panic-grounding override (crisis-path). Vee-signed boundary 2026-07-28.

The override may force grounding over an intent_route crisis escalation ONLY when safety_check is CLEAN
(no crisis_flags, S3 below threshold, no medical) AND a clear panic signature is present AND there is NO
harm-adjacency (conservative dial: defer to escalation on any harm hint). Fixtures are paraphrase-independent
(NOT the override's own pattern strings) per the recall-fixture-independence rule.

§1c-B (panic + real/subtle harm) MUST NEVER force-ground — it is the ship gate.
"""
import json
import os

from sage_poc.nodes.panic_override import should_ground_over_crisis, S3_SUB_THRESHOLD_CLEAN

_FX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "tests/fixtures/bot_behaviour_audit/part_a_1c_boundary_PROPOSED.json")
_FIX = json.load(open(_FX))
_A = _FIX["sec_1c_A_force_ground_when_clean"]["cases"]
_B = _FIX["sec_1c_B_always_escalates_TRIPWIRE"]["cases"]

# The two demonstrated over-escalators (verbatim), with their measured sub-threshold S3 scores.
_DEMONSTRATED = [
    ("I feel like I'm going to die and can't breathe", 0.7638),
    ("Everything feels unreal and I can't take this", 0.7343),
]


def _clean_state(text, s3=0.5):
    """safety_check-CLEAN turn where intent_route returned crisis (the override's precondition)."""
    return {"message_en": text, "raw_message": text, "primary_intent": "crisis",
            "crisis_flags": [], "s3_score": s3, "medical_flags": [], "clinical_flags": []}


def test_demonstrated_cases_force_ground():
    for text, s3 in _DEMONSTRATED:
        assert should_ground_over_crisis(_clean_state(text, s3)) is True, f"should force-ground: {text!r}"


def test_1c_A_naturalistic_panic_forces_ground():
    """§1c-A: clear panic, no harm, safety_check clean -> force grounding (restore the clean verdict)."""
    for text in _A:
        assert should_ground_over_crisis(_clean_state(text)) is True, f"§1c-A must force-ground: {text!r}"


def test_1c_B_panic_with_harm_NEVER_force_grounds():
    """§1c-B ship gate: panic phrasing + real/subtle harm -> override must DEFER (escalate stands)."""
    for text in _B:
        assert should_ground_over_crisis(_clean_state(text)) is False, \
            f"§1c-B MUST NOT force-ground (defer to harm): {text!r}"


def test_override_never_fires_when_safety_check_already_flagged_crisis():
    """The override only acts on a CLEAN turn; if safety_check caught a crisis, it must never interfere."""
    st = _clean_state("I can't breathe and I want to die")
    st["crisis_flags"] = ["s1_keyword"]  # safety_check already escalated
    assert should_ground_over_crisis(st) is False


def test_override_never_fires_when_s3_over_threshold():
    st = _clean_state("everything is closing in on me", s3=0.85)  # above hard S3 threshold
    assert should_ground_over_crisis(st) is False


def test_override_never_fires_on_medical_flag():
    st = _clean_state("my chest is really tight and I can't get enough air")
    st["medical_flags"] = ["cardiac"]
    assert should_ground_over_crisis(st) is False


def test_override_requires_intent_crisis():
    """No override work on non-crisis turns (it only ever corrects a crisis over-escalation)."""
    st = _clean_state("my heart is racing")
    st["primary_intent"] = "new_skill"
    assert should_ground_over_crisis(st) is False
