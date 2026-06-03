"""Tests for psychotic_referral auto-select routing and delivered guard."""
import asyncio
import pytest


def make_state(**kwargs):
    defaults = {
        "raw_message": "I've been hearing voices in my head",
        "message_en": "I've been hearing voices in my head",
        "detected_language": "en",
        "clinical_flags": ["psychotic_disclosure"],
        "crisis_flags": [],
        "is_safe": True,
        "crisis_state": "none",
        "active_skill_id": None,
        "active_step_id": None,
        "primary_intent": "general_chat",
        "path": ["safety_check", "intent_route"],
        "therapeutic_profile": None,
        "turn_number": 2,
        "psychotic_referral_delivered": None,
    }
    defaults.update(kwargs)
    return defaults


@pytest.mark.asyncio
async def test_psychotic_disclosure_auto_selects_referral_skill():
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_state()
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "psychotic_referral"
    assert result["skill_match_method"] == "psychotic_disclosure_auto_select"
    assert result["active_step_id"] == "professional_referral"


@pytest.mark.asyncio
async def test_delivered_guard_prevents_reselection():
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_state(psychotic_referral_delivered=True)
    result = await skill_select_node(state)
    assert result.get("active_skill_id") != "psychotic_referral", (
        "psychotic_referral must not be re-selected when psychotic_referral_delivered=True"
    )


@pytest.mark.asyncio
async def test_post_crisis_takes_precedence():
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_state(crisis_state="monitoring", clinical_flags=["psychotic_disclosure"])
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "post_crisis_check_in"


@pytest.mark.asyncio
async def test_normal_message_without_flag_unaffected():
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_state(
        raw_message="I've been feeling stressed",
        message_en="I've been feeling stressed",
        clinical_flags=[],
    )
    result = await skill_select_node(state)
    assert result.get("active_skill_id") != "psychotic_referral"


def test_skill_executor_sets_delivered_flag_on_completion():
    from sage_poc.nodes import skill_executor
    import inspect
    src = inspect.getsource(skill_executor)
    assert "psychotic_referral_delivered" in src, (
        "skill_executor must set psychotic_referral_delivered when psychotic_referral completes"
    )
