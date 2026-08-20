"""Amendment 4 fixture corpus for Task 2 (router precedence as data).

Baseline corpus proving router DESTINATIONS are stable across the guard-clause
-> ordered-rule-table refactor (task-2-brief.md, ruling P2-2). Every case here
is captured against the CURRENT (pre-refactor) implementation before
src/sage_poc/graph.py's four routers are touched, and stays green -- with
IDENTICAL destinations -- through all four per-router commits and the
precedence-pin-test commit. A destination change on ANY case is
STOP-AND-REPORT (Global Constraints, task-2-brief.md), never fix-and-continue.

The four routers are exercised directly (the existing tests/test_routing.py
idiom: state dict in, destination string out). build_graph is not used here --
it would require running the full node chain (semantic model, DB pool) for no
additional routing-SHAPE evidence; the router functions are the unit of truth
for destination selection, and that is exactly what this refactor changes the
internal shape of.

Amendment 4 spectrum coverage (per-class counts, cited in the PR body):
  - Arabic-script turns:            7   (detected_language="ar")
  - Arabizi turns:                  6   (detected_language="az")
  - clinical-flag states (CF):     14   (psychotic_disclosure, mania_disclosure,
                                          dissociation_disclosure, derealization,
                                          combinations + flag-gated pairs)
  - medical_flags states:           4
  - crisis_flags / is_safe states:  9   (is_safe False/True, monitoring re-escalation,
                                          crisis_tier T1 tiering)
  - hr states:                      8   (hr_terminal_step, hr_referral_delivered,
                                          psychotic_referral_delivered, hr_escalate_regardless)
  - blended / secondary intent:     4
  - flag-on / flag-off pairs:       18  (one pair per _cfg-gated rung, every router)
  (categories overlap by design -- a single case often covers more than one axis;
  counts above are per-axis membership, not partition membership.)
"""
import pytest

pytestmark = pytest.mark.safety_gate

import sage_poc.config as config
from sage_poc.graph import (
    _route_after_safety,
    _route_after_intent,
    _route_after_skill_select,
    _route_after_skill_executor,
)


# Every _cfg-gated flag any of the four routers reads, pinned to a known value
# on every case (never ambient env-var state) so the corpus is deterministic
# regardless of how SAGE_* env vars happen to be set in the running shell.
_ALL_GATES_OFF = {
    "CRISIS_TIERING_ENABLED": False,
    "MEDICAL_REDFLAG_GUARD_ENABLED": False,
    "HIGH_RISK_TERMINAL_ENABLED": False,
    "HIGH_RISK_DETECTION_ENABLED": False,
    "DEREALIZATION_DETECTION_ENABLED": False,
    "PSYCHOED_PATHWAYS_ENABLED": False,
    "MODALITY_REQUEST_ROUTING_ENABLED": False,
    "VENTING_SUPPRESSION_ENABLED": False,
    "CONSULT_SOURCES_ENABLED": False,
}


def make_state(**overrides) -> dict:
    defaults = {
        "raw_message": "", "detected_language": "en", "message_en": "",
        "is_safe": True, "crisis_flags": [], "clinical_flags": [],
        "crisis_state": "none", "s7_result": None, "s7_method": None,
        "primary_intent": None, "secondary_intent": None,
        "intent_confidence": 1.0, "emotional_intensity": 5,
        "active_skill_id": None, "offered_skill_ids": None, "offer_response": None,
        "medical_flags": [], "crisis_tier": None,
        "hr_terminal_step": None, "hr_referral_delivered": False,
        "hr_escalate_regardless": False, "psychotic_referral_delivered": False,
        "derealization_referral_delivered": False,
        "answering_screen": False, "psychoed_weave_pending": False,
        "psychoed_weave_escalation": False, "modality_screen_pending": False,
        "explicit_modality_request": None, "venting_detected": False,
        "prepass_matched": None, "containment_directive": None,
        "psychoed_serve": None, "skill_match_method": None,
        "screen_question_text": None, "skill_select_abstained": False,
        "re_escalation_within_monitoring": False, "escalation_triggered": None,
        "panic_grounding_override": False, "grief_presence_override": False,
        "selfworth_presence_override": False,
        "third_party_crisis": False,
    }
    return {**defaults, **overrides}


# (case_id, category, router, overrides, flag_overrides, expected_destination)
CORPUS = [
    # ---------------------------------------------------------------- _route_after_safety
    ("safety_monitoring_reescalate_not_safe", "crisis_flags",
     _route_after_safety, dict(crisis_state="monitoring", is_safe=False), {}, "crisis"),
    ("safety_monitoring_reescalate_s7_new_crisis", "crisis_flags",
     _route_after_safety, dict(crisis_state="monitoring", is_safe=True, s7_result="NEW_CRISIS"), {}, "crisis"),
    ("safety_monitoring_stable", "crisis_flags",
     _route_after_safety, dict(crisis_state="monitoring", is_safe=True, s7_result="STILL_DISTRESSED"), {}, "safe"),
    ("safety_tiering_t1_flag_on", "flag_pair",
     _route_after_safety, dict(is_safe=False, crisis_tier="T1"), {"CRISIS_TIERING_ENABLED": True}, "safe"),
    ("safety_tiering_t1_flag_off", "flag_pair",
     _route_after_safety, dict(is_safe=False, crisis_tier="T1"), {"CRISIS_TIERING_ENABLED": False}, "crisis"),
    ("safety_not_safe_crisis", "crisis_flags",
     _route_after_safety, dict(is_safe=False), {}, "crisis"),
    ("safety_medical_redflag_on", "medical_flags",
     _route_after_safety, dict(is_safe=True, medical_flags=["chest_pain"]),
     {"MEDICAL_REDFLAG_GUARD_ENABLED": True}, "medical"),
    ("safety_medical_redflag_off", "flag_pair",
     _route_after_safety, dict(is_safe=True, medical_flags=["chest_pain"]),
     {"MEDICAL_REDFLAG_GUARD_ENABLED": False}, "safe"),
    ("safety_hr_disclosure_mania_gated_on", "hr_states",
     _route_after_safety, dict(is_safe=True, clinical_flags=["mania_disclosure"], hr_referral_delivered=False),
     {"HIGH_RISK_TERMINAL_ENABLED": True, "HIGH_RISK_DETECTION_ENABLED": True}, "high_risk"),
    ("safety_hr_disclosure_psychotic_always_routes", "hr_states",
     _route_after_safety, dict(is_safe=True, clinical_flags=["psychotic_disclosure"]),
     {"HIGH_RISK_TERMINAL_ENABLED": True, "HIGH_RISK_DETECTION_ENABLED": False}, "high_risk"),
    ("safety_hr_disclosure_one_shot_guard", "hr_states",
     _route_after_safety, dict(is_safe=True, clinical_flags=["mania_disclosure"], hr_referral_delivered=True),
     {"HIGH_RISK_TERMINAL_ENABLED": True, "HIGH_RISK_DETECTION_ENABLED": True}, "safe"),
    ("safety_hr_reentry_await_distress", "hr_states",
     _route_after_safety, dict(is_safe=True, hr_terminal_step="await_distress"),
     {"HIGH_RISK_TERMINAL_ENABLED": True}, "high_risk"),
    ("safety_hr_terminal_flag_off_pair", "flag_pair",
     _route_after_safety,
     dict(is_safe=True, hr_terminal_step="await_distress", clinical_flags=["mania_disclosure"]),
     {"HIGH_RISK_TERMINAL_ENABLED": False}, "safe"),
    ("safety_derealization_on", "CF_flags",
     _route_after_safety, dict(is_safe=True, clinical_flags=["derealization"], derealization_referral_delivered=False),
     {"DEREALIZATION_DETECTION_ENABLED": True}, "derealization"),
    ("safety_derealization_one_shot_guard", "hr_states",
     _route_after_safety, dict(is_safe=True, clinical_flags=["derealization"], derealization_referral_delivered=True),
     {"DEREALIZATION_DETECTION_ENABLED": True}, "safe"),
    ("safety_derealization_flag_off_pair", "flag_pair",
     _route_after_safety, dict(is_safe=True, clinical_flags=["derealization"]),
     {"DEREALIZATION_DETECTION_ENABLED": False}, "safe"),
    ("safety_precedence_crisis_over_medical", "crisis_flags",
     _route_after_safety, dict(is_safe=False, medical_flags=["chest_pain"]),
     {"MEDICAL_REDFLAG_GUARD_ENABLED": True}, "crisis"),
    ("safety_precedence_medical_over_hr", "medical_flags",
     _route_after_safety, dict(is_safe=True, medical_flags=["chest_pain"], clinical_flags=["mania_disclosure"]),
     {"MEDICAL_REDFLAG_GUARD_ENABLED": True, "HIGH_RISK_TERMINAL_ENABLED": True, "HIGH_RISK_DETECTION_ENABLED": True},
     "medical"),
    ("safety_precedence_hr_over_derealization", "hr_states",
     _route_after_safety, dict(is_safe=True, clinical_flags=["mania_disclosure", "derealization"]),
     {"HIGH_RISK_TERMINAL_ENABLED": True, "HIGH_RISK_DETECTION_ENABLED": True, "DEREALIZATION_DETECTION_ENABLED": True},
     "high_risk"),
    ("safety_arabic_script_language_blind", "arabic_script",
     _route_after_safety, dict(detected_language="ar", is_safe=False), {}, "crisis"),
    ("safety_arabic_script_safe", "arabic_script",
     _route_after_safety, dict(detected_language="ar", is_safe=True), {}, "safe"),
    ("safety_arabizi_language_blind", "arabizi",
     _route_after_safety, dict(detected_language="az", is_safe=True), {}, "safe"),

    # ---------------------------------------------------------------- _route_after_intent
    ("intent_crisis_default", "crisis_flags",
     _route_after_intent, dict(primary_intent="crisis"), {}, "crisis"),
    ("intent_crisis_panic_override", "hr_states",
     _route_after_intent, dict(primary_intent="crisis", panic_grounding_override=True), {}, "skill_select"),
    ("intent_crisis_grief_override", "hr_states",
     _route_after_intent, dict(primary_intent="crisis", grief_presence_override=True), {}, "skill_select"),
    ("intent_crisis_selfworth_override", "hr_states",
     _route_after_intent, dict(primary_intent="crisis", selfworth_presence_override=True), {}, "skill_select"),
    ("intent_crisis_beats_answering_screen", "crisis_flags",
     _route_after_intent, dict(primary_intent="crisis", answering_screen=True), {}, "crisis"),
    ("intent_d1_answering_screen", "blended_intent",
     _route_after_intent, dict(primary_intent="general_chat", answering_screen=True), {}, "skill_select"),
    ("intent_psychoed_weave_pending_on", "flag_pair",
     _route_after_intent, dict(primary_intent="general_chat", psychoed_weave_pending=True),
     {"PSYCHOED_PATHWAYS_ENABLED": True}, "skill_select"),
    ("intent_psychoed_weave_pending_off", "flag_pair",
     _route_after_intent, dict(primary_intent="general_chat", psychoed_weave_pending=True),
     {"PSYCHOED_PATHWAYS_ENABLED": False}, "freeflow"),
    ("intent_emr_modality_screen_pending_on", "flag_pair",
     _route_after_intent, dict(primary_intent="general_chat", modality_screen_pending={"x": 1}, active_skill_id=None),
     {"MODALITY_REQUEST_ROUTING_ENABLED": True}, "skill_select"),
    ("intent_emr_modality_screen_pending_guarded_by_active_skill", "hr_states",
     _route_after_intent,
     dict(primary_intent="general_chat", modality_screen_pending={"x": 1}, active_skill_id="cbt_thought_record"),
     {"MODALITY_REQUEST_ROUTING_ENABLED": True}, "freeflow"),
    ("intent_scope_refusal", "crisis_flags",
     _route_after_intent, dict(primary_intent="scope_refusal"), {}, "gate"),
    ("intent_jailbreak", "crisis_flags",
     _route_after_intent, dict(primary_intent="jailbreak"), {}, "gate"),
    ("intent_scope_refusal_beats_psychotic_referral", "CF_flags",
     _route_after_intent, dict(primary_intent="scope_refusal", clinical_flags=["psychotic_disclosure"]), {}, "gate"),
    ("intent_jailbreak_beats_psychotic_referral", "CF_flags",
     _route_after_intent, dict(primary_intent="jailbreak", clinical_flags=["psychotic_disclosure"]), {}, "gate"),
    ("intent_monitoring_priority_bypasses_confidence", "crisis_flags",
     _route_after_intent, dict(primary_intent="general_chat", crisis_state="monitoring", intent_confidence=0.2),
     {}, "skill_select"),
    ("intent_hr_disclosure_redirect_psychotic_flag_independent", "CF_flags",
     _route_after_intent, dict(primary_intent="general_chat", clinical_flags=["psychotic_disclosure"]),
     {"HIGH_RISK_DETECTION_ENABLED": False}, "skill_select"),
    ("intent_hr_disclosure_redirect_mania_gated_on", "CF_flags",
     _route_after_intent, dict(primary_intent="general_chat", clinical_flags=["mania_disclosure"]),
     {"HIGH_RISK_DETECTION_ENABLED": True}, "skill_select"),
    ("intent_hr_disclosure_redirect_mania_gated_off", "flag_pair",
     _route_after_intent, dict(primary_intent="general_chat", clinical_flags=["mania_disclosure"]),
     {"HIGH_RISK_DETECTION_ENABLED": False}, "freeflow"),
    ("intent_hr_disclosure_senior_to_offer_accept", "CF_flags",
     _route_after_intent,
     dict(primary_intent="general_chat", clinical_flags=["psychotic_disclosure"],
          offered_skill_ids=["worry_time"], offer_response="accept", intent_confidence=0.3),
     {}, "skill_select"),
    ("intent_r1_offer_accept_bypasses_confidence", "blended_intent",
     _route_after_intent,
     dict(primary_intent="general_chat", offered_skill_ids=["worry_time"], offer_response="accept",
          intent_confidence=0.3),
     {}, "skill_select"),
    ("intent_f6_venting_suppression_on_beats_sf2", "flag_pair",
     _route_after_intent,
     dict(primary_intent="general_chat", venting_detected=True, emotional_intensity=9, active_skill_id=None),
     {"VENTING_SUPPRESSION_ENABLED": True}, "freeflow"),
    ("intent_f6_venting_suppression_off_falls_to_sf2", "flag_pair",
     _route_after_intent,
     dict(primary_intent="general_chat", venting_detected=True, emotional_intensity=9, active_skill_id=None),
     {"VENTING_SUPPRESSION_ENABLED": False}, "skill_select"),
    ("intent_sf2_acute_intensity", "crisis_flags",
     _route_after_intent, dict(primary_intent="general_chat", emotional_intensity=9, active_skill_id=None),
     {}, "skill_select"),
    ("intent_sf2_guarded_by_active_skill", "hr_states",
     _route_after_intent, dict(primary_intent="general_chat", emotional_intensity=9, active_skill_id="cbt_thought_record"),
     {}, "freeflow"),
    ("intent_node2_prepass_hint", "blended_intent",
     _route_after_intent,
     dict(primary_intent="general_chat", prepass_matched=["dbt_tipp"], active_skill_id=None, emotional_intensity=5),
     {}, "skill_select"),
    ("intent_emr_modality_request_redirect_on", "flag_pair",
     _route_after_intent,
     dict(primary_intent="general_chat", explicit_modality_request={"requested": True}, active_skill_id=None),
     {"MODALITY_REQUEST_ROUTING_ENABLED": True}, "skill_select"),
    ("intent_emr_modality_request_redirect_off", "flag_pair",
     _route_after_intent,
     dict(primary_intent="general_chat", explicit_modality_request={"requested": True}, active_skill_id=None),
     {"MODALITY_REQUEST_ROUTING_ENABLED": False}, "freeflow"),
    ("intent_low_confidence", "crisis_flags",
     _route_after_intent, dict(primary_intent="general_chat", intent_confidence=0.4), {}, "low_confidence"),
    ("intent_exit_skill_with_active", "hr_states",
     _route_after_intent, dict(primary_intent="exit_skill", active_skill_id="cbt_thought_record"),
     {}, "skill_executor"),
    ("intent_exit_skill_no_active", "hr_states",
     _route_after_intent, dict(primary_intent="exit_skill", active_skill_id=None), {}, "freeflow"),
    ("intent_new_skill_with_active", "hr_states",
     _route_after_intent, dict(primary_intent="new_skill", active_skill_id="cbt_thought_record"),
     {}, "skill_executor"),
    ("intent_new_skill_no_active", "crisis_flags",
     _route_after_intent, dict(primary_intent="new_skill", active_skill_id=None), {}, "skill_select"),
    ("intent_info_request", "crisis_flags",
     _route_after_intent, dict(primary_intent="info_request"), {}, "skill_select"),
    ("intent_skill_continuation_active", "hr_states",
     _route_after_intent, dict(primary_intent="skill_continuation", active_skill_id="cbt_thought_record"),
     {}, "skill_executor"),
    ("intent_skill_continuation_no_active", "hr_states",
     _route_after_intent, dict(primary_intent="skill_continuation", active_skill_id=None), {}, "freeflow"),
    ("intent_default_freeflow", "crisis_flags",
     _route_after_intent, dict(primary_intent="general_chat"), {}, "freeflow"),
    ("intent_blended_general_chat_new_skill_secondary", "blended_intent",
     _route_after_intent, dict(primary_intent="general_chat", secondary_intent="new_skill", emotional_intensity=5),
     {}, "freeflow"),
    ("intent_blended_crisis_primary_new_skill_secondary", "blended_intent",
     _route_after_intent, dict(primary_intent="crisis", secondary_intent="new_skill"), {}, "crisis"),
    ("intent_arabic_script_sf2", "arabic_script",
     _route_after_intent, dict(primary_intent="general_chat", detected_language="ar", emotional_intensity=9,
                                active_skill_id=None),
     {}, "skill_select"),
    ("intent_arabic_script_info_request", "arabic_script",
     _route_after_intent, dict(primary_intent="info_request", detected_language="ar"), {}, "skill_select"),
    ("intent_arabic_script_crisis", "arabic_script",
     _route_after_intent, dict(primary_intent="crisis", detected_language="ar"), {}, "crisis"),
    ("intent_arabizi_info_request", "arabizi",
     _route_after_intent, dict(primary_intent="info_request", detected_language="az"), {}, "skill_select"),
    ("intent_arabizi_freeflow_default", "arabizi",
     _route_after_intent, dict(primary_intent="general_chat", detected_language="az"), {}, "freeflow"),
    ("intent_arabizi_low_confidence", "arabizi",
     _route_after_intent, dict(primary_intent="general_chat", detected_language="az", intent_confidence=0.3),
     {}, "low_confidence"),

    # --------------------------------------------------------- _route_after_skill_select
    ("sel_psychoed_weave_escalation", "hr_states",
     _route_after_skill_select, dict(psychoed_weave_escalation=True), {}, "crisis_response"),
    ("sel_containment_directive", "blended_intent",
     _route_after_skill_select, dict(containment_directive={"family": "ocd"}), {}, "knowledge_retrieve"),
    ("sel_psychoed_serve", "flag_pair",
     _route_after_skill_select, dict(psychoed_serve={"category": "depression"}), {}, "knowledge_retrieve"),
    ("sel_psychoed_menu_after_weave", "flag_pair",
     _route_after_skill_select, dict(skill_match_method="psychoed_menu_after_weave"), {}, "knowledge_retrieve"),
    ("sel_screen_question_served", "crisis_flags",
     _route_after_skill_select, dict(screen_question_text="Which best describes it?"), {}, "screen_response"),
    ("sel_v2_abstain", "crisis_flags",
     _route_after_skill_select, dict(skill_select_abstained=True), {}, "low_confidence"),
    ("sel_info_request_consult_cards_on", "flag_pair",
     _route_after_skill_select, dict(primary_intent="info_request", skill_match_method="info_request_skill_consult"),
     {"CONSULT_SOURCES_ENABLED": True}, "knowledge_retrieve_cards"),
    ("sel_info_request_consult_cards_off", "flag_pair",
     _route_after_skill_select, dict(primary_intent="info_request", skill_match_method="info_request_skill_consult"),
     {"CONSULT_SOURCES_ENABLED": False}, "skill_executor"),
    ("sel_info_request_plain", "crisis_flags",
     _route_after_skill_select, dict(primary_intent="info_request", skill_match_method=None), {}, "knowledge_retrieve"),
    ("sel_active_skill_resume", "hr_states",
     _route_after_skill_select, dict(active_skill_id="cbt_thought_record"), {}, "skill_executor"),
    ("sel_default_freeflow", "crisis_flags",
     _route_after_skill_select, dict(), {}, "freeflow"),
    ("sel_precedence_escalation_over_containment", "hr_states",
     _route_after_skill_select, dict(psychoed_weave_escalation=True, containment_directive={"family": "ocd"}),
     {}, "crisis_response"),
    ("sel_precedence_containment_over_screen", "blended_intent",
     _route_after_skill_select, dict(containment_directive={"family": "ocd"}, screen_question_text="q?"),
     {}, "knowledge_retrieve"),
    ("sel_precedence_screen_over_info_request", "blended_intent",
     _route_after_skill_select, dict(screen_question_text="q?", primary_intent="info_request"),
     {}, "screen_response"),
    ("sel_arabic_script", "arabic_script",
     _route_after_skill_select, dict(detected_language="ar", active_skill_id="cbt_thought_record"),
     {}, "skill_executor"),
    ("sel_arabizi", "arabizi",
     _route_after_skill_select, dict(detected_language="az", primary_intent="info_request"),
     {}, "knowledge_retrieve"),

    # ------------------------------------------------------- _route_after_skill_executor
    ("exec_reescalation", "crisis_flags",
     _route_after_skill_executor, dict(re_escalation_within_monitoring=True), {}, "crisis"),
    ("exec_rehand", "flag_pair",
     _route_after_skill_executor, dict(escalation_triggered={"action": "exit_with_rehand"}), {}, "skill_select"),
    ("exec_default_freeflow", "crisis_flags",
     _route_after_skill_executor, dict(), {}, "freeflow"),
    ("exec_precedence_reescalation_over_rehand", "hr_states",
     _route_after_skill_executor,
     dict(re_escalation_within_monitoring=True, escalation_triggered={"action": "exit_with_rehand"}),
     {}, "crisis"),
    ("exec_arabic_script", "arabic_script",
     _route_after_skill_executor, dict(detected_language="ar"), {}, "freeflow"),
    ("exec_arabizi", "arabizi",
     _route_after_skill_executor, dict(detected_language="az", re_escalation_within_monitoring=True), {}, "crisis"),
]


@pytest.mark.parametrize(
    "case_id,category,router,overrides,flag_overrides,expected",
    CORPUS,
    ids=[c[0] for c in CORPUS],
)
def test_router_precedence_corpus(monkeypatch, case_id, category, router, overrides, flag_overrides, expected):
    for name, value in _ALL_GATES_OFF.items():
        monkeypatch.setattr(config, name, value)
    for name, value in flag_overrides.items():
        monkeypatch.setattr(config, name, value)
    state = make_state(**overrides)
    actual = router(state)
    assert actual == expected, (
        f"[{category}] {case_id}: expected destination {expected!r}, got {actual!r}. "
        "A destination change here is STOP-AND-REPORT, not fix-and-continue "
        "(task-2-brief.md Global Constraints)."
    )


def test_corpus_covers_all_four_routers():
    """Structural guard: every router named in the task brief has at least one corpus case."""
    routers_seen = {c[2] for c in CORPUS}
    assert routers_seen == {
        _route_after_safety, _route_after_intent, _route_after_skill_select, _route_after_skill_executor,
    }


def test_corpus_covers_amendment_4_categories():
    """Structural guard: the Amendment 4 spectrum (arabic script, arabizi, CF flags,
    medical_flags, crisis_flags, hr states, blended/secondary intent, flag-on/off pairs)
    is represented, not just EN happy paths."""
    categories_seen = {c[1] for c in CORPUS}
    required = {
        "arabic_script", "arabizi", "CF_flags", "medical_flags",
        "crisis_flags", "hr_states", "blended_intent", "flag_pair",
    }
    missing = required - categories_seen
    assert not missing, f"Amendment 4 categories missing from corpus: {missing}"
