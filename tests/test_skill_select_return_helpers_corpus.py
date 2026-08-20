"""P2 Task 1 (skill_select return-dict helpers + intra-file dedup) equivalence corpus.

Amendment 4 (fixture corpus for routing-surface tasks): this corpus proves the upcoming
`_no_skill` / `_enter_skill` / `_rank_keyword_candidates` / `_try_emr` extraction is a PURE
dedup — the full returned dict of `skill_select_node`, per case, is byte-identical before and
after the refactor. It is committed BEFORE the refactor lands (Step 1 of the task brief) and
run green against unmodified code; the refactor diff must not touch this file (Step 3: zero
expectation edits, or the change is a behavior change, not a simplification, and is a
STOP-AND-REPORT per the task's Global Constraints).

Class minimums (task-1-brief.md Step 1), each counted in the PR body:
  - 6 Arabic-script turns               (ids ar_*)
  - 6 Arabizi turns                     (ids az_*)
  - one state per routing-relevant clinical flag   (ids flag_*)
  - 4 blended-intent states             (ids blended_*)
  - the C1 acute-overlap state (dbt_tipp/grounding) (ids c1_*, plus ar_direct_entry_grounding_b3
    and az_c1_tiebreak_grounding_offer above already exercise it in AR/Arabizi)
  - an active-EMR state                 (ids emr_*)
  - a psychoed-pathway state            (id psychoed_resolver_hit)
  - a stale-offer state                 (id stale_offer_clear_fallback)
Everything past those (helper_* ids) is bonus coverage of individual _no_skill/_enter_skill
call sites the refactor touches directly (vetoes, cooldown, offer-accept, declined-pool
exhaustion, the D1 answering_screen passthrough this task deliberately does NOT convert — see
its comment below) — not part of the Amendment-4 minimum, but the strongest available proof
that each of the 14+/6+ conversions in skill_select.py is behavior-preserving.

Amendment-4 axis mapping note (routing-relevant clinical flag / medical_flags / crisis_flags /
hr states): skill_select.py itself reads `clinical_flags` at exactly two sites (HR disclosure
auto-select, and the V2 flag-disposition abstain/contain gate) and `crisis_state` (not
crisis_flags directly) for the post-crisis auto-select. It never reads `medical_flags` directly
-- that channel is owned by safety/medical_screen.py's apply_screen_at_route (a COLLISION BAR
file this task does not touch). So: "CF flags" -> flag_substance_use_abstain_v2 /
flag_domestic_situation_ipv_keyword_suppressed; "hr states" -> flag_psychotic_disclosure /
flag_mania_disclosure_gated_on / flag_dissociation_disclosure_gated_on (+ the gated-off negative
flag_mania_disclosure_gated_off); "crisis_flags" -> the crisis_state="monitoring" cases
(ar_crisis_monitoring, az_crisis_monitoring, blended_crisis_primary_new_skill_secondary_monitoring);
"medical_flags" -> the active-EMR states plus helper_d1_answering_screen_flag_off_identity, which
is the only medical_flags-adjacent surface skill_select.py itself touches (via
apply_screen_at_route's read-only consumption of the passed dict).

Mocking idiom: identical to tests/test_skill_select.py's test_semantic_timeout_falls_back_to_keyword_match
-- patch asyncio.wait_for to raise TimeoutError so every case is deterministic and fast (no BGE-M3
load). Every case here resolves before or without reaching the semantic tier's real embedding call,
so this patch never changes which branch a case exercises; it only removes non-determinism from the
one branch (Tier 2) none of these cases need a real embedding score to reach.
"""
from __future__ import annotations

import asyncio
import os
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.safety_gate

import sage_poc.config as config
from sage_poc.nodes import skill_select as ss
from sage_poc.nodes.skill_select import skill_select_node


def _ss_state(**overrides):
    base = {
        "raw_message": "",
        "detected_language": "en",
        "message_en": "",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 1.0,
        "emotional_intensity": 5,
        "engagement": 7,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
        "skill_match_method": None,
        "semantic_score": None,
        "distress_trajectory": [],
        "code_switching": False,
    }
    base.update(overrides)
    return base


_EMR_CLEARED_CTX = {
    "physical_symptoms_mentioned": False,
    "red_flag_language": False,
    "duration_class": "acute",
    "onset_supplied": True,
    "quality_checked": True,
    "screen_asked": [],
    "cleared": True,
    "referral_alongside": False,
}

_EMR_RED_FLAG_CTX = {
    "physical_symptoms_mentioned": True,
    "red_flag_language": True,
    "duration_class": None,
    "onset_supplied": False,
    "quality_checked": False,
    "screen_asked": [],
    "cleared": False,
    "referral_alongside": False,
}


# Each case: id, state overrides, and optional config/env/ss_attr monkeypatch maps.
CASES = [
    # ---- 6 Arabic-script turns -------------------------------------------------
    dict(
        id="ar_direct_entry_grounding_b3",
        state=dict(
            message_en="محتاج أهدى بسرعة", raw_message="محتاج أهدى بسرعة",
            detected_language="ar", primary_intent="new_skill",
        ),
    ),
    dict(
        id="ar_raw_message_box_breathing",
        state=dict(
            raw_message="تنفس معي", message_en="breathe with me",
            detected_language="ar", primary_intent="new_skill",
        ),
    ),
    dict(
        id="ar_bucket_lock_dbt_tipp",
        state=dict(
            message_en="أشعر إني سأنفجر", raw_message="أشعر إني سأنفجر",
            detected_language="ar", primary_intent="new_skill",
        ),
    ),
    dict(
        id="ar_no_match_timeout_abstain",
        state=dict(
            message_en="أشعر بالحزن اليوم", raw_message="أشعر بالحزن اليوم",
            detected_language="ar", primary_intent="new_skill",
        ),
    ),
    dict(
        id="ar_psychotic_disclosure_hr",
        state=dict(
            clinical_flags=["psychotic_disclosure"],
            message_en="الأصوات تخبرني أشياء", raw_message="الأصوات تخبرني أشياء",
            detected_language="ar",
        ),
    ),
    dict(
        id="ar_crisis_monitoring",
        state=dict(
            crisis_state="monitoring",
            message_en="أشعر بهدوء أكثر الآن", raw_message="أشعر بهدوء أكثر الآن",
            detected_language="ar",
        ),
    ),

    # ---- 6 Arabizi turns --------------------------------------------------------
    dict(
        id="az_keyword_match_box_breathing_offer",
        state=dict(
            raw_message="bidi atnafas", message_en="I want to breathe with box breathing",
            detected_language="az", primary_intent="new_skill",
        ),
    ),
    dict(
        id="az_untranslated_no_match_abstain",
        state=dict(
            raw_message="ana tayer w mo 3aref ash asawi",
            message_en="ana tayer w mo 3aref ash asawi",
            detected_language="az", primary_intent="new_skill",
        ),
    ),
    dict(
        id="az_bucket_lock_dbt_tipp_offer",
        state=dict(
            message_en="breathing isn't working", raw_message="el tanafus mub shghal",
            detected_language="az", primary_intent="new_skill",
        ),
    ),
    dict(
        id="az_c1_tiebreak_grounding_offer",
        state=dict(
            message_en="i feel completely overwhelmed, my head is spinning",
            raw_message="7ase ktir mnfajer w rasi ye3sef",
            detected_language="az", primary_intent="new_skill",
        ),
    ),
    dict(
        id="az_substance_use_abstain_v2",
        state=dict(
            clinical_flags=["substance_use"], message_en="anything", raw_message="anything",
            detected_language="az",
        ),
        env=dict(SKILL_ROUTING_V2="1"),
    ),
    dict(
        id="az_crisis_monitoring",
        state=dict(
            crisis_state="monitoring", message_en="7asa be huduu2 akthar",
            raw_message="7asa be huduu2 akthar", detected_language="az",
        ),
    ),

    # ---- routing-relevant clinical-flag states -----------------------------------
    dict(
        id="flag_psychotic_disclosure",
        state=dict(
            clinical_flags=["psychotic_disclosure"],
            message_en="voices are telling me things",
        ),
    ),
    dict(
        id="flag_mania_disclosure_gated_on",
        state=dict(
            clinical_flags=["mania_disclosure"],
            message_en="I haven't slept in days and I have so many ideas",
        ),
        config=dict(HIGH_RISK_DETECTION_ENABLED=True),
    ),
    dict(
        id="flag_dissociation_disclosure_gated_on",
        state=dict(
            clinical_flags=["dissociation_disclosure"],
            message_en="I feel like I'm watching myself from outside",
        ),
        config=dict(HIGH_RISK_DETECTION_ENABLED=True),
    ),
    dict(
        id="flag_mania_disclosure_gated_off",
        state=dict(
            clinical_flags=["mania_disclosure"],
            message_en="I haven't slept in days and I have so many ideas",
        ),
        config=dict(HIGH_RISK_DETECTION_ENABLED=False),
    ),
    dict(
        id="flag_substance_use_abstain_v2",
        state=dict(
            clinical_flags=["substance_use"],
            message_en="I've been drinking a lot lately",
        ),
        env=dict(SKILL_ROUTING_V2="1"),
    ),
    dict(
        id="flag_domestic_situation_ipv_keyword_suppressed",
        state=dict(
            clinical_flags=["domestic_situation"],
            message_en="I need help setting boundaries",
        ),
        config=dict(IPV_PREEMPTION_ENABLED=True),
    ),

    # ---- 4 blended-intent states --------------------------------------------------
    dict(
        id="blended_new_skill_info_secondary",
        state=dict(
            primary_intent="new_skill", secondary_intent="info_request",
            message_en="always my fault",
        ),
    ),
    dict(
        id="blended_info_primary_new_skill_secondary_consult",
        state=dict(
            primary_intent="info_request", secondary_intent="new_skill",
            message_en="I lost someone recently and I don't know how to cope",
        ),
        config=dict(INFO_REQUEST_CONSULT_ENABLED=True),
    ),
    dict(
        id="blended_general_chat_new_skill_secondary_no_match",
        state=dict(
            primary_intent="general_chat", secondary_intent="new_skill",
            message_en="what is the capital of France",
        ),
    ),
    dict(
        id="blended_crisis_primary_new_skill_secondary_monitoring",
        state=dict(
            primary_intent="crisis", secondary_intent="new_skill",
            crisis_state="monitoring", message_en="I feel a bit calmer now",
        ),
    ),

    # ---- C1 acute-overlap tiebreak (EN) --------------------------------------------
    dict(
        id="c1_tiebreak_grounding_en",
        state=dict(
            message_en="i feel completely overwhelmed, my head is spinning",
            primary_intent="new_skill",
        ),
    ),
    dict(
        id="c1_tiebreak_dbt_tipp_only_guard",
        state=dict(message_en="i can't calm down", primary_intent="new_skill"),
    ),

    # ---- active-EMR state -----------------------------------------------------------
    dict(
        id="emr_cleared_offer",
        state=dict(
            explicit_modality_request={"requested": True, "modality_hint": None},
            recent_presentation=dict(_EMR_CLEARED_CTX),
            message_en="can we do something else", primary_intent="new_skill",
        ),
        config=dict(MODALITY_REQUEST_ROUTING_ENABLED=True),
    ),
    dict(
        id="emr_screen_pending_abandon",
        state=dict(
            modality_screen_pending={"modality_hint": None},
            recent_presentation=dict(_EMR_RED_FLAG_CTX),
            message_en="never mind", primary_intent="new_skill",
        ),
        config=dict(MODALITY_REQUEST_ROUTING_ENABLED=True),
    ),

    # ---- psychoed-pathway state -------------------------------------------------------
    dict(
        id="psychoed_resolver_hit",
        state=dict(message_en="What is anxiety?", primary_intent="info_request"),
        config=dict(PSYCHOED_PATHWAYS_ENABLED=True, PSYCHOED_CATEGORIES=frozenset({"1f", "3c"})),
    ),

    # ---- stale-offer state --------------------------------------------------------------
    dict(
        id="stale_offer_clear_fallback",
        state=dict(
            offered_skill_ids=["nonexistent_skill_xyz"],
            offer_response="accept",
            offer_choice_skill_id="nonexistent_skill_xyz",
            message_en="qwerty asdf zxcv nonsense text matching nothing",
        ),
    ),

    # ---- bonus: individual _no_skill / _enter_skill call-site coverage ------------------
    dict(
        id="helper_harm_intrusive_veto",
        state=dict(
            message_en=(
                "Ever since my baby was born I keep getting terrifying intrusive images "
                "of harming him, and I can't make them stop"
            ),
        ),
    ),
    dict(
        id="helper_ocd_compulsion_veto",
        state=dict(
            message_en="I keep getting horrible thoughts I might've left the stove on, so I check it twenty times",
            raw_message="I keep getting horrible thoughts I might've left the stove on, so I check it twenty times",
        ),
    ),
    dict(
        id="helper_offer_accept_promotion",
        state=dict(
            offered_skill_ids=["box_breathing"], offer_response="accept",
            offer_choice_skill_id="box_breathing", message_en="yes let's do that",
        ),
    ),
    dict(
        id="helper_all_candidates_declined",
        state=dict(
            message_en="always my fault", declined_skills=["cbt_thought_record"],
            primary_intent="new_skill",
        ),
    ),
    dict(
        id="helper_offer_cooldown_suppressed",
        state=dict(message_en="always my fault", last_offer_turn=0, turn_count=1),
        ss_attr=dict(SKILL_OFFER_COOLDOWN_ENABLED=True),
    ),
    dict(
        id="helper_semantic_exclusion_guard",
        state=dict(message_en="I haven't been eating", primary_intent="new_skill"),
    ),
    dict(
        id="helper_d1_answering_screen_flag_off_identity",
        # D1_SCREEN_ENABLED/D1_SCREEN_SHADOW both default False -> apply_screen_at_route is
        # IDENTITY (medical_screen.py, a COLLISION BAR file, is not modified by this task; this
        # call site is deliberately left as a hand-built dict rather than converted to _no_skill
        # -- see skill_select.py's answering_screen branch comment for why).
        state=dict(answering_screen=True, message_en="no, same as always"),
    ),
]


async def _run_case(monkeypatch, case: dict) -> dict:
    for k, v in (case.get("config") or {}).items():
        monkeypatch.setattr(config, k, v)
    for k, v in (case.get("env") or {}).items():
        monkeypatch.setenv(k, v)
    for k, v in (case.get("ss_attr") or {}).items():
        monkeypatch.setattr(ss, k, v)
    state = _ss_state(**case["state"])
    with patch("sage_poc.nodes.skill_select.asyncio.wait_for", side_effect=asyncio.TimeoutError):
        return await skill_select_node(state)


# Populated by the SS_CORPUS_CAPTURE=1 capture run (see module docstring); this is the frozen
# equivalence baseline recorded against UNMODIFIED code (origin/master, pre-refactor), committed
# before the refactor. Re-generate with:
#   SS_CORPUS_CAPTURE=1 pytest tests/test_skill_select_return_helpers_corpus.py -q -s \
#       -k test_corpus_case_equivalence
# and transcribe -- never hand-edit an entry to make a case pass; that defeats the corpus.
EXPECTED: dict[str, dict] = {
    "ar_direct_entry_grounding_b3": {
        "active_skill_id": "grounding_5_4_3_2_1", "active_step_id": "see_5",
        "skill_match_method": "keyword", "semantic_score": None,
        "path": ["skill_select", "arabic_offer_excluded"],
    },
    "ar_raw_message_box_breathing": {
        "active_skill_id": "box_breathing", "active_step_id": "inhale_hold",
        "skill_match_method": "keyword", "semantic_score": None,
        "path": ["skill_select", "arabic_offer_excluded"],
    },
    "ar_bucket_lock_dbt_tipp": {
        "active_skill_id": "dbt_tipp", "active_step_id": "entry_screen",
        "skill_match_method": "keyword", "semantic_score": None,
        "path": ["skill_select", "arabic_offer_excluded"],
    },
    "ar_no_match_timeout_abstain": {
        "active_skill_id": None, "active_step_id": None, "skill_match_method": None,
        "semantic_score": None, "embedding_timeout": True, "path": ["skill_select"],
    },
    "ar_psychotic_disclosure_hr": {
        "active_skill_id": "psychotic_referral", "active_step_id": "professional_referral",
        "skill_match_method": "psychotic_disclosure_auto_select", "semantic_score": None,
        "path": ["skill_select"],
    },
    "ar_crisis_monitoring": {
        "active_skill_id": "post_crisis_check_in", "skill_match_method": "post_crisis_auto_select",
        "semantic_score": None, "path": ["skill_select"], "active_step_id": "acknowledge_and_check",
    },
    "az_keyword_match_box_breathing_offer": {
        "active_skill_id": None, "active_step_id": None, "offered_skill_ids": ["box_breathing"],
        "offer_count": 1, "last_offer_turn": 0, "skill_match_method": "keyword_offer",
        "semantic_score": None,
        "path": ["skill_select", "skill_matching_rule:default_offer", "skill_offer_made"],
    },
    "az_untranslated_no_match_abstain": {
        "active_skill_id": None, "active_step_id": None, "skill_match_method": None,
        "semantic_score": None, "embedding_timeout": True, "path": ["skill_select"],
    },
    "az_bucket_lock_dbt_tipp_offer": {
        "active_skill_id": None, "active_step_id": None, "offered_skill_ids": ["dbt_tipp"],
        "offer_count": 1, "last_offer_turn": 0, "skill_match_method": "keyword_offer",
        "semantic_score": None,
        "path": ["skill_select", "skill_matching_rule:default_offer", "skill_offer_made"],
    },
    "az_c1_tiebreak_grounding_offer": {
        "active_skill_id": None, "active_step_id": None,
        "offered_skill_ids": ["grounding_5_4_3_2_1", "dbt_tipp"],
        "offer_count": 1, "last_offer_turn": 0, "skill_match_method": "keyword_offer",
        "semantic_score": None,
        "path": ["skill_select", "skill_matching_rule:default_offer", "skill_offer_made"],
    },
    "az_substance_use_abstain_v2": {
        "active_skill_id": None, "active_step_id": None, "skill_match_method": None,
        "semantic_score": None, "path": ["skill_select", "clinical_flag_abstain"],
    },
    "az_crisis_monitoring": {
        "active_skill_id": "post_crisis_check_in", "skill_match_method": "post_crisis_auto_select",
        "semantic_score": None, "path": ["skill_select"], "active_step_id": "acknowledge_and_check",
    },
    "flag_psychotic_disclosure": {
        "active_skill_id": "psychotic_referral", "active_step_id": "professional_referral",
        "skill_match_method": "psychotic_disclosure_auto_select", "semantic_score": None,
        "path": ["skill_select"],
    },
    "flag_mania_disclosure_gated_on": {
        "active_skill_id": "psychotic_referral", "active_step_id": "professional_referral",
        "skill_match_method": "psychotic_disclosure_auto_select", "semantic_score": None,
        "path": ["skill_select"],
    },
    "flag_dissociation_disclosure_gated_on": {
        "active_skill_id": "psychotic_referral", "active_step_id": "professional_referral",
        "skill_match_method": "psychotic_disclosure_auto_select", "semantic_score": None,
        "path": ["skill_select"],
    },
    "flag_mania_disclosure_gated_off": {
        "active_skill_id": None, "active_step_id": None, "skill_match_method": None,
        "semantic_score": None, "embedding_timeout": True, "path": ["skill_select"],
    },
    "flag_substance_use_abstain_v2": {
        "active_skill_id": None, "active_step_id": None, "skill_match_method": None,
        "semantic_score": None, "path": ["skill_select", "clinical_flag_abstain"],
    },
    "flag_domestic_situation_ipv_keyword_suppressed": {
        "active_skill_id": None, "active_step_id": None, "offered_skill_ids": None,
        "offer_count": 0, "skill_match_method": None, "semantic_score": None,
        "path": ["skill_select", "ipv_preempt_suppressed"],
    },
    "blended_new_skill_info_secondary": {
        "active_skill_id": None, "active_step_id": None,
        "offered_skill_ids": ["cbt_thought_record"], "offer_count": 1, "last_offer_turn": 0,
        "skill_match_method": "keyword_offer", "semantic_score": None,
        "path": ["skill_select", "skill_matching_rule:default_offer", "skill_offer_made"],
    },
    "blended_info_primary_new_skill_secondary_consult": {
        "skill_match_method": "info_request_skill_consult", "semantic_score": None,
        "path": ["skill_select"], "active_skill_id": "grief_loss",
        "active_step_id": "acknowledge_and_witness",
    },
    "blended_general_chat_new_skill_secondary_no_match": {
        "active_skill_id": None, "active_step_id": None, "skill_match_method": None,
        "semantic_score": None, "embedding_timeout": True, "path": ["skill_select"],
    },
    "blended_crisis_primary_new_skill_secondary_monitoring": {
        "active_skill_id": "post_crisis_check_in", "skill_match_method": "post_crisis_auto_select",
        "semantic_score": None, "path": ["skill_select"], "active_step_id": "acknowledge_and_check",
    },
    "c1_tiebreak_grounding_en": {
        "active_skill_id": None, "active_step_id": None,
        "offered_skill_ids": ["grounding_5_4_3_2_1", "dbt_tipp"],
        "offer_count": 1, "last_offer_turn": 0, "skill_match_method": "keyword_offer",
        "semantic_score": None,
        "path": ["skill_select", "skill_matching_rule:default_offer", "skill_offer_made"],
    },
    "c1_tiebreak_dbt_tipp_only_guard": {
        "active_skill_id": None, "active_step_id": None, "offered_skill_ids": ["dbt_tipp"],
        "offer_count": 1, "last_offer_turn": 0, "skill_match_method": "keyword_offer",
        "semantic_score": None,
        "path": ["skill_select", "skill_matching_rule:default_offer", "skill_offer_made"],
    },
    "emr_cleared_offer": {
        "active_skill_id": None, "active_step_id": None,
        "offered_skill_ids": ["box_breathing", "grounding_5_4_3_2_1"], "offer_count": 1,
        "last_offer_turn": 0, "skill_match_method": "modality_request_offer", "semantic_score": None,
        "modality_screen_pending": None,
        "path": ["skill_select", "modality_request_routed:select", "skill_offer_made"],
    },
    "emr_screen_pending_abandon": {
        "active_skill_id": None, "active_step_id": None, "skill_match_method": None,
        "semantic_score": None, "modality_screen_pending": None,
        "path": ["skill_select", "modality_request_screen_abandoned"],
    },
    "psychoed_resolver_hit": {
        "psychoed_serve": {
            "category": "1f", "block_id": None, "route": "standard", "framing": "abstract",
            "weave_due": False, "matched_row_id": "1f-t1", "collision_path": None,
            "menu_pick": False,
        },
        "psychoed_active_category": "1f", "psychoed_delivery_shape": "menu_first",
        "psychoed_matched_row_id": "1f-t1", "psychoed_collision_path": None,
        "psychoed_framing": "abstract", "psychoed_weave_pending": False,
        "psychoed_weave_fired": False, "skill_match_method": "psychoed_resolver",
        "path": ["skill_select"],
    },
    "stale_offer_clear_fallback": {
        "offered_skill_ids": None, "active_skill_id": None, "active_step_id": None,
        "skill_match_method": None, "semantic_score": None, "embedding_timeout": True,
        "path": ["skill_select"],
    },
    "helper_harm_intrusive_veto": {
        "active_skill_id": None, "active_step_id": None, "skill_match_method": None,
        "semantic_score": None, "path": ["skill_select", "harm_intrusive_veto"],
    },
    "helper_ocd_compulsion_veto": {
        "active_skill_id": None, "active_step_id": None, "skill_match_method": None,
        "semantic_score": None, "path": ["skill_select", "ocd_compulsion_veto"],
        "abstain_referral": "ocd_erp",
    },
    "helper_offer_accept_promotion": {
        "active_skill_id": "box_breathing", "active_step_id": "inhale_hold",
        "offered_skill_ids": None, "offer_count": 0, "skill_match_method": "offer_accept",
        "semantic_score": None, "path": ["skill_select", "offer_promoted"],
    },
    "helper_all_candidates_declined": {
        "active_skill_id": None, "active_step_id": None, "offer_count": 0,
        "skill_match_method": None, "semantic_score": None,
        "path": ["skill_select", "skill_matching_rule:default_offer", "all_candidates_declined"],
    },
    "helper_offer_cooldown_suppressed": {
        "active_skill_id": None, "active_step_id": None, "skill_match_method": None,
        "semantic_score": None, "path": ["skill_select", "offer_cooldown_suppressed"],
    },
    "helper_semantic_exclusion_guard": {
        "active_skill_id": None, "active_step_id": None, "skill_match_method": None,
        "semantic_score": None, "path": ["skill_select"],
    },
    "helper_d1_answering_screen_flag_off_identity": {
        "active_skill_id": None, "offered_skill_ids": None, "skill_match_method": None,
        "semantic_score": None, "path": ["skill_select"],
    },
}


_CAPTURE = os.environ.get("SS_CORPUS_CAPTURE") == "1"


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
async def test_corpus_case_equivalence(case, monkeypatch):
    result = await _run_case(monkeypatch, case)
    if _CAPTURE:
        print(f"\n=== CASE {case['id']} ===\n{result!r}")
        return
    assert case["id"] in EXPECTED, f"No recorded expectation for corpus case {case['id']!r}"
    expected = EXPECTED[case["id"]]
    assert result == expected, (
        f"Corpus case {case['id']!r} dict changed:\n  expected={expected!r}\n  actual=  {result!r}"
    )


def test_corpus_class_counts():
    """Amendment 4: per-class counts, asserted so the PR body's claim is mechanically checked."""
    ids = [c["id"] for c in CASES]
    assert len([i for i in ids if i.startswith("ar_")]) == 6
    assert len([i for i in ids if i.startswith("az_")]) == 6
    assert len([i for i in ids if i.startswith("flag_")]) == 6
    assert len([i for i in ids if i.startswith("blended_")]) == 4
    assert len([i for i in ids if i.startswith("c1_")]) == 2
    assert len([i for i in ids if i.startswith("emr_")]) == 2
    assert len([i for i in ids if i.startswith("psychoed_")]) == 1
    assert len([i for i in ids if i.startswith("stale_offer_")]) == 1
    assert len([i for i in ids if i.startswith("helper_")]) == 7
    assert len(ids) == len(set(ids)), "duplicate corpus case id"
