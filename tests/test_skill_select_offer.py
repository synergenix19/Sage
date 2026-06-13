"""R1: consent-gated skill entry, driven by the skill_matching rules category.
skill_select collects candidates, asks the Rules Service how to proceed, and
either offers (offered_skill_ids) or enters directly. Fired rule_id is audited
in the path."""
import pytest

import sage_poc.nodes.skill_select as ss
from sage_poc.nodes.skill_select import skill_select_node
from sage_poc.skills.schema import load_skill


def make_state(**kwargs) -> dict:
    defaults = {
        "raw_message": kwargs.get("message_en", ""),
        "message_en": kwargs.get("message_en", ""),
        "detected_language": "en",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "active_skill_id": None,
        "active_step_id": None,
        "primary_intent": "new_skill",
        "intent_confidence": 1.0,
        "emotional_intensity": 5,
        "engagement": 6,
        "path": [],
        "therapeutic_profile": None,
        "offered_skill_ids": None,
        "offer_response": None,
        "offer_choice_skill_id": None,
        "declined_skills": [],
    }
    return {**defaults, **kwargs}


async def test_keyword_match_creates_offer_not_activation():
    kw = load_skill("cbt_thought_record").target_presentations[0]
    state = make_state(message_en=f"Lately {kw} and it will not stop")
    result = await skill_select_node(state)
    assert result["active_skill_id"] is None
    assert result["offered_skill_ids"][0] == "cbt_thought_record"
    assert result["skill_match_method"] == "keyword_offer"
    assert "skill_offer_made" in result["path"]
    assert any(p.startswith("skill_matching_rule:") for p in result["path"]), (
        "fired rule_id must be audited in path"
    )


async def test_acute_somatic_high_intensity_enters_directly():
    kw = load_skill("box_breathing").target_presentations[0]
    state = make_state(message_en=f"Help, {kw}", emotional_intensity=9)
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "box_breathing"
    assert not result.get("offered_skill_ids")
    assert result["skill_match_method"] == "keyword"


async def test_acute_declined_substitutes_within_pool():
    """Amendment 2026-06-13: a declined acute match is substituted by the first
    non-declined skill in the clinician-ordered (grounding-first) pool, NOT entered
    directly. ignore_declined is gone."""
    kw = load_skill("box_breathing").target_presentations[0]
    state = make_state(
        message_en=f"Help, {kw}",
        emotional_intensity=9,
        declined_skills=["box_breathing"],
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "grounding_5_4_3_2_1", (
        "first non-declined in grounding-first pool"
    )
    assert result["active_skill_id"] != "box_breathing"
    assert "acute_substitute_declined" in result["path"]


async def test_acute_declined_substitutes_skipping_further_declines():
    """Pool order grounding, stop, box, tipp: with grounding also declined the
    substitute is stop_technique (next non-declined)."""
    kw = load_skill("box_breathing").target_presentations[0]
    state = make_state(
        message_en=f"Help, {kw}",
        emotional_intensity=9,
        declined_skills=["box_breathing", "grounding_5_4_3_2_1"],
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "stop_technique"
    assert "acute_substitute_declined" in result["path"]


async def test_acute_all_declined_safety_floor():
    """Whole pool declined: safety floor enters the matched (declined) skill directly."""
    kw = load_skill("box_breathing").target_presentations[0]
    state = make_state(
        message_en=f"Help, {kw}",
        emotional_intensity=9,
        declined_skills=[
            "box_breathing", "grounding_5_4_3_2_1", "stop_technique", "dbt_tipp",
        ],
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "box_breathing", "safety floor over preference"
    assert "acute_safety_floor_all_declined" in result["path"]


async def test_acute_pool_exhausted_hits_safety_floor_tipp_excluded():
    """Clinical decision 2026-06-13: dbt_tipp is EXCLUDED from the substitute_pool.
    With box + grounding + stop all declined, no non-declined pool member remains.
    The safety floor must fire: enter the matched (declined) skill directly.
    TIPP must never appear as a silent auto-substitute."""
    kw = load_skill("box_breathing").target_presentations[0]
    state = make_state(
        message_en=f"Help, {kw}",
        emotional_intensity=9,
        declined_skills=["box_breathing", "grounding_5_4_3_2_1", "stop_technique"],
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "box_breathing", (
        "safety floor must enter the matched skill when the 3-member pool is fully declined"
    )
    assert "acute_safety_floor_all_declined" in result["path"], (
        "path must record the safety floor"
    )
    assert "acute_substitute_declined" not in result["path"], (
        "no substitute should have fired — pool was exhausted"
    )


async def test_tipp_not_used_as_silent_substitute():
    """dbt_tipp must NEVER appear as an auto-substitute (clinical decision 2026-06-13).
    Its temperature/intense-exercise cautions make it not a clean interchangeable substitute.
    It is entered only as a direct keyword match running its own entry_screen."""
    kw = load_skill("box_breathing").target_presentations[0]
    state = make_state(
        message_en=f"Help, {kw}",
        emotional_intensity=9,
        declined_skills=["box_breathing", "grounding_5_4_3_2_1", "stop_technique"],
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] != "dbt_tipp", (
        "TIPP must never be auto-substituted into; it is only entered on a direct keyword match"
    )


async def test_acute_somatic_low_intensity_still_offers():
    kw = load_skill("box_breathing").target_presentations[0]
    state = make_state(message_en=f"Sometimes {kw}", emotional_intensity=4)
    result = await skill_select_node(state)
    assert result["active_skill_id"] is None
    assert result["offered_skill_ids"][0] == "box_breathing"


async def test_two_keyword_matches_offer_top_two_by_specificity():
    kw_a = load_skill("cbt_thought_record").target_presentations[0]
    kw_b = load_skill("worry_time").target_presentations[0]
    state = make_state(message_en=f"{kw_a} and also {kw_b} all day")
    result = await skill_select_node(state)
    offered = result["offered_skill_ids"]
    assert set(offered) == {"cbt_thought_record", "worry_time"}
    # Ordering is only deterministic by specificity when keyword lengths differ;
    # on a tie the stable sort falls back to registry order, so skip the check.
    if len(kw_a) != len(kw_b):
        expected_first = "cbt_thought_record" if len(kw_a) >= len(kw_b) else "worry_time"
        assert offered[0] == expected_first


async def test_declined_skill_is_not_offered_again():
    kw = load_skill("cbt_thought_record").target_presentations[0]
    state = make_state(
        message_en=f"Lately {kw} and it will not stop",
        declined_skills=["cbt_thought_record"],
    )
    result = await skill_select_node(state)
    assert not result.get("offered_skill_ids") or \
        "cbt_thought_record" not in result["offered_skill_ids"]


async def test_accept_promotes_offered_skill():
    state = make_state(
        message_en="yes let us try it",
        offered_skill_ids=["worry_time", "cognitive_restructuring"],
        offer_response="accept",
        offer_choice_skill_id="cognitive_restructuring",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "cognitive_restructuring"
    assert result["active_step_id"] == load_skill("cognitive_restructuring").steps[0].step_id
    assert result["offered_skill_ids"] is None
    assert result["skill_match_method"] == "offer_accept"
    assert "offer_promoted" in result["path"]


async def test_accept_with_invalid_choice_falls_back_to_first():
    state = make_state(
        message_en="yes",
        offered_skill_ids=["worry_time"],
        offer_response="accept",
        offer_choice_skill_id="not_a_skill",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "worry_time"


async def test_stale_unresolvable_offer_is_cleared_from_checkpoint(monkeypatch):
    """A checkpoint offer referencing renamed/unknown skills must be cleared by the
    node's RETURN (local rebinds never reach the checkpoint), or the offer template
    re-renders forever."""
    monkeypatch.setattr(
        ss, "_semantic_match_with_runner_up",
        lambda message_en, profile_context="": (None, 0.0, None),
    )
    state = make_state(
        message_en="just thinking out loud today",
        offered_skill_ids=["renamed_old_skill"],
        offer_response="accept",
    )
    result = await skill_select_node(state)
    assert result.get("offered_skill_ids") is None
    assert "offered_skill_ids" in result, "the clear must be in the returned dict"


async def test_post_crisis_auto_select_bypasses_offer():
    state = make_state(message_en="I am okay I think", crisis_state="monitoring")
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "post_crisis_check_in"
    assert not result.get("offered_skill_ids")


async def test_semantic_match_creates_offer(monkeypatch):
    # fully mocked semantic tier: no BGE load, no slow marker
    monkeypatch.setattr(
        ss, "_semantic_match_with_runner_up",
        lambda message_en, profile_context="": ("worry_time", 0.51, ("cognitive_restructuring", 0.49)),
    )
    state = make_state(message_en="everything spirals in my head at night and I cannot switch off")
    result = await skill_select_node(state)
    if result["skill_match_method"] in ("keyword", "keyword_offer"):
        pytest.skip("phrase unexpectedly keyword-matched; semantic path not exercised")
    assert result["offered_skill_ids"] == ["worry_time", "cognitive_restructuring"]
    assert result["skill_match_method"] == "semantic_offer"


async def test_enter_direct_without_ignore_declined_falls_back_to_offer_with_audit_marker(monkeypatch):
    """A clinician-authored enter_direct rule WITHOUT ignore_declined that matches a
    declined skill falls through to the consent path, and the audit trail records the
    divergence between the fired rule's action and the action taken."""
    from sage_poc.rules.schemas import EvalResult, FiredRule

    def fake_evaluate(category, context):
        assert category == "skill_matching"
        res = EvalResult()
        res.fired.append(FiredRule(
            rule_id="hypothetical_direct_rule",
            version="0.1.0",
            action={"type": "enter_direct"},   # no ignore_declined
        ))
        return res

    monkeypatch.setattr(ss.rules_engine, "evaluate", fake_evaluate)
    kw = load_skill("cbt_thought_record").target_presentations[0]
    state = make_state(
        message_en=f"Lately {kw} and it will not stop",
        declined_skills=["cbt_thought_record"],
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] is None, "consent fallback must win over a declined direct entry"
    assert "enter_direct_declined_fallback" in result["path"]


# ── Arabic-exclusion gate (2026-06-13) ────────────────────────────────────────
# The R1 consent-offer flow is English-only until S2-2 ships a tested Khaleeji
# accept path (the Arabic accept parse is audit-confirmed broken). Until then an
# Arabic-script session must NEVER produce an offer — it falls through to pre-R1
# behavior (the matched skill is entered directly). This is the test that converts
# "English-only by intention" into "English-only by enforcement".

async def test_arabic_session_skill_match_produces_no_offer_and_routes_to_prior_behavior():
    """Arabic-script session with a skill match produces no offer and routes to prior behavior.

    Contrast with test_keyword_match_creates_offer_not_activation: the SAME skill match
    that offers in English must enter directly (active_skill_id set, no offered_skill_ids)
    when detected_language == 'ar'.
    """
    kw = load_skill("cbt_thought_record").target_presentations[0]
    state = make_state(
        message_en=f"Lately {kw} and it will not stop",
        raw_message="مؤخراً أفكاري لا تتوقف",
        detected_language="ar",
    )
    result = await skill_select_node(state)
    # No offer on an Arabic session.
    assert not result.get("offered_skill_ids"), "Arabic session must not produce an offer"
    assert "skill_offer_made" not in result["path"]
    # Prior (pre-R1) behavior: the matched skill is entered directly.
    assert result["active_skill_id"] == "cbt_thought_record"
    assert result["active_step_id"] is not None
    assert "arabic_offer_excluded" in result["path"]


async def test_english_session_same_match_still_offers():
    """Guard: the exclusion is language-scoped. The identical match in an English
    session must still offer (R1 unchanged for English)."""
    kw = load_skill("cbt_thought_record").target_presentations[0]
    state = make_state(message_en=f"Lately {kw} and it will not stop")  # detected_language defaults to 'en'
    result = await skill_select_node(state)
    assert result["active_skill_id"] is None
    assert result["offered_skill_ids"][0] == "cbt_thought_record"
    assert "skill_offer_made" in result["path"]
    assert "arabic_offer_excluded" not in result["path"]
