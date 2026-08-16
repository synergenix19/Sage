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

# The two demonstrated over-escalators (verbatim, measured sub-threshold S3). BOTH now DEFER by ruling
# (2026-07-30): the cardiac case by item-3 (death-fear x air-hunger stays crisis), the derealization case
# by item-1 (CF-010 owns it -> referral at higher precedence). The ruled reversal is deliberate and signed.
_DEMONSTRATED_NOW_DEFER = [
    ("I feel like I'm going to die and can't breathe", 0.7638),   # item-3 cardiac residual
    ("Everything feels unreal and I can't take this", 0.7343),    # item-1 -> CF-010 referral
]
_DEREAL = _FIX["sec_1c_A_derealization_now_CF010"]["cases"]
_REGISTRY = _FIX["sec_registry_owned_surface_defers"]["cases"]
_CARDIAC = _FIX["sec_cardiac_ambiguous_stays_crisis"]["cases"]


def _clean_state(text, s3=0.5):
    """safety_check-CLEAN turn where intent_route returned crisis (the override's precondition)."""
    return {"message_en": text, "raw_message": text, "primary_intent": "crisis",
            "crisis_flags": [], "s3_score": s3, "medical_flags": [], "clinical_flags": []}


def test_demonstrated_cases_now_defer_by_ruling():
    for text, s3 in _DEMONSTRATED_NOW_DEFER:
        assert should_ground_over_crisis(_clean_state(text, s3)) is False, f"ruled defer: {text!r}"


def test_derealization_defers_to_cf010():
    """Item-1 (2026-07-30): derealization is CF-010's territory — the override must never ground it."""
    for text in _DEREAL:
        assert should_ground_over_crisis(_clean_state(text)) is False, f"CF-010 owns: {text!r}"


def test_registry_owned_surface_defers():
    """Item-1 scope-back: HR-family phrasings left the surface — escalation stands."""
    for text in _REGISTRY:
        assert should_ground_over_crisis(_clean_state(text)) is False, f"registry-owned: {text!r}"


def test_cardiac_ambiguous_never_grounds():
    """Item-3: death-fear x air-hunger stays at crisis — no downgrade without a clean screen."""
    for text in _CARDIAC:
        assert should_ground_over_crisis(_clean_state(text)) is False, f"cardiac residual: {text!r}"


def test_pure_death_fear_without_air_hunger_still_grounds():
    """The signed §1c-A capability survives the narrowing: fear-of-death panic WITHOUT air-hunger grounds."""
    st = _clean_state("I feel like I'm going to die, my heart is pounding out of my chest")
    assert should_ground_over_crisis(st) is True


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


def test_derealization_turn_audits_gate_path():
    """Increment-1 finding: a served derealization referral must audit gate_path='derealization'
    (it was NULL — only medical turns persisted gate_path — and the method-of-record driver
    misclassified the referral presence_only). Non-derealization rows stay byte-identical."""
    from sage_poc.audit import _build_session_audit_row
    st = {"session_id": "s", "turn_number": 1, "path": ["safety_check", "derealization_response"],
          "gate_path": "derealization", "clinical_flags": ["derealization"]}
    assert _build_session_audit_row(st).get("gate_path") == "derealization"
    benign = {"session_id": "s", "turn_number": 1,
              "path": ["safety_check", "intent_route", "freeflow_respond", "output_gate"]}
    assert "gate_path" not in _build_session_audit_row(benign)
