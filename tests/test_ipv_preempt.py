"""E7 — §6a coercive-control / relationship-safety pre-emption (BOT BEHAVIOUR §6a).

Step 1: flag-gated detection expansion. The 19 §6a-guard phrases fire domestic_situation ONLY
when SAGE_IPV_PREEMPTION is ON; OFF is byte-identical (only the approved CF-005 lexicon fires).
Expansion phrases are VERBATIM from the fixture (source of truth — no re-derivation); the sync
test guards against drift. Recall/precision are measured against the same ipv_e7_recall fixture
the harness uses, so the gate and these tests read the same ground truth.
"""
import asyncio
import json
from pathlib import Path

import sage_poc.config as config
from sage_poc.nodes.ipv_preempt import EXPANSION_PHRASES, apply_ipv_preempt
from sage_poc.nodes.skill_select import skill_select_node

_FIXTURE = Path("tests/fixtures/bot_behaviour/ipv_e7_recall.json")


def _fixture_6a_phrases() -> set[str]:
    data = json.loads(_FIXTURE.read_text())
    return {p["phrase"] for p in data["positive"]["phrases"] if p["src"] == "6a"}


def _people_pleasing_negatives() -> list[str]:
    data = json.loads(_FIXTURE.read_text())
    return data["negative"]["ordinary_people_pleasing"]["phrases"]


def test_expansion_phrases_match_fixture_verbatim():
    # The fixture is the single source of truth for the expansion set. Production data must equal
    # it exactly, so the 19 phrases can never silently drift or be re-derived by hand.
    assert set(EXPANSION_PHRASES) == _fixture_6a_phrases()


def test_off_is_byte_identical(monkeypatch):
    # Flag OFF (default) -> emits nothing; safety_check return + audit stay v7-identical.
    monkeypatch.setattr(config, "IPV_PREEMPTION_ENABLED", False)
    out = apply_ipv_preempt(
        {"message_en": "They get really angry if I say no", "clinical_flags": []}
    )
    assert out == {}


def test_all_19_expansion_phrases_fire_domestic_situation_when_on(monkeypatch):
    monkeypatch.setattr(config, "IPV_PREEMPTION_ENABLED", True)
    missed = [
        p for p in _fixture_6a_phrases()
        if "domestic_situation"
        not in apply_ipv_preempt({"message_en": p, "clinical_flags": []}).get("clinical_flags", [])
    ]
    assert missed == [], f"expansion phrases not detected: {missed}"


def test_people_pleasing_negatives_do_not_fire(monkeypatch):
    # Precision / the punish-disclosure guard's mirror: ordinary people-pleasing must route to
    # assertiveness coaching, NOT IPV pre-emption. Over-firing E7 is clinically harmful too.
    monkeypatch.setattr(config, "IPV_PREEMPTION_ENABLED", True)
    fired = [
        n for n in _people_pleasing_negatives()
        if "domestic_situation"
        in apply_ipv_preempt({"message_en": n, "clinical_flags": []}).get("clinical_flags", [])
    ]
    assert fired == [], f"negatives wrongly fired IPV: {fired}"


# ============================================================================
# STEP 3 — active §6 pre-emption at skill_select (flag-gated, scoped, referral)
# ============================================================================

def _sel_state(message: str, **overrides) -> dict:
    base = {
        "raw_message": message, "message_en": message, "detected_language": "en",
        "is_safe": True, "crisis_flags": [], "clinical_flags": [], "crisis_state": "none",
        "s7_result": None, "s7_method": None,
        "primary_intent": "new_skill", "secondary_intent": None, "intent_confidence": 1.0,
        "emotional_intensity": 5, "engagement": 7,
        "active_skill_id": None, "active_step_id": None, "executed_step_id": None,
        "step_instruction": None, "escalation_triggered": None, "gate_path": None,
        "response_en": None, "response": None, "path": [], "turn_count": 1,
        "offered_skill_ids": None, "offer_response": None, "offer_choice_skill_id": None,
        "last_offer_turn": None, "declined_skills": [], "offer_count": 0,
        "psychotic_referral_delivered": None, "therapeutic_profile": None,
    }
    base.update(overrides)
    return base


def _select(message: str, **overrides) -> dict:
    return asyncio.run(skill_select_node(_sel_state(message, **overrides)))


def _picked(out: dict) -> set[str]:
    return {out.get("active_skill_id")} | set(out.get("offered_skill_ids") or [])


def test_step3_section6_suppressed_when_ipv_active(monkeypatch):
    # domestic_situation disclosed + flag ON: a §6 assertiveness request is contraindicated ->
    # not selected/offered, routed to freeflow with the marker (where the referral surfaces).
    monkeypatch.setattr(config, "IPV_PREEMPTION_ENABLED", True)
    out = _select("how do I start setting boundaries", clinical_flags=["domestic_situation"])
    assert "assertive_communication" not in _picked(out)
    assert "ipv_preempt_suppressed" in out["path"]


def test_step3_carveout_grounding_still_available_under_ipv(monkeypatch):
    # THE don't-punish-disclosure test: an IPV-flagged user asking for grounding still gets it.
    # Only §6 coaching_confrontation skills are pre-empted; grounding/offload/sleep stay available.
    monkeypatch.setattr(config, "IPV_PREEMPTION_ENABLED", True)
    out = _select("I need grounding right now", clinical_flags=["domestic_situation"])
    assert "ipv_preempt_suppressed" not in out.get("path", [])
    assert "grounding_5_4_3_2_1" in _picked(out)


def test_step3_byte_identical_when_flag_off(monkeypatch):
    # Flag OFF (default): domestic_situation present, but the §6 skill is offered exactly as v7 —
    # no suppression, no marker.
    monkeypatch.setattr(config, "IPV_PREEMPTION_ENABLED", False)
    out = _select("how do I start setting boundaries", clinical_flags=["domestic_situation"])
    assert "ipv_preempt_suppressed" not in out.get("path", [])
    assert "assertive_communication" in _picked(out)


def test_step3_referral_adaptation_fires_on_domestic_situation_path():
    # NOTE 1 — the ROUTE-TO-REFERRAL half of the signed "block AND route to referral" consequence.
    # A suppressed §6 turn routes to freeflow with domestic_situation set; the existing PI-CF-005
    # adaptation must inject the safety-first framing + DFWAC/Ewaa referral there. Single-authority:
    # no new referral copy — this asserts the existing adaptation actually surfaces on that path.
    from sage_poc.rules import engine as rules_engine

    result = rules_engine.evaluate("prompt_injection", {
        "text": "how do I start setting boundaries",
        "text_ar": None,
        "clinical_flags": ["domestic_situation"],
        "primary_intent": "new_skill",
        "secondary_intent": None,
        "session_flags": [],
    })
    system = " ".join(a["content"] for a in result.actions if a.get("target") == "system")
    assert "PI-CF-005" in {r.rule_id for r in result.fired}
    assert "safety" in system.lower()
    assert "800111" in system or "Ewaa" in system  # DFWAC / Ewaa referral resources present
