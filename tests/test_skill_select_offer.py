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


async def test_acute_direct_entry_ignores_declined():
    """ignore_declined in the acute rule: a prior decline must not block acute entry."""
    kw = load_skill("box_breathing").target_presentations[0]
    state = make_state(
        message_en=f"Help, {kw}",
        emotional_intensity=9,
        declined_skills=["box_breathing"],
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "box_breathing", "safety over preference"


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
