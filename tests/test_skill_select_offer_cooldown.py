import pytest
from unittest.mock import patch
from sage_poc.nodes import skill_select as ss


def _within_cooldown_state():
    # 1 turn since last offer, cooldown=2 -> within window
    return {"primary_intent":"new_skill","crisis_state":"none","clinical_flags":[],
            "offered_skill_ids":None,"message_en":"i keep overthinking","raw_message":"i keep overthinking",
            "detected_language":"en","path":["safety_check","intent_route"],"declined_skills":[],
            "therapeutic_profile":{}, "emotional_intensity":5,
            "turn_count":6, "last_offer_turn":5}


@pytest.mark.asyncio
async def test_offer_suppressed_within_cooldown_when_gate_on():
    # Gate ON: within the cooldown window, a fresh offer is suppressed.
    state = _within_cooldown_state()
    with patch.object(ss, "SKILL_OFFER_COOLDOWN_ENABLED", True), \
         patch.object(ss, "_semantic_match_with_runner_up", return_value=("worry_time", 0.62, None)):
        result = await ss.skill_select_node(state)
    assert result["active_skill_id"] is None
    assert not result.get("offered_skill_ids")
    assert "offer_cooldown_suppressed" in result["path"]


@pytest.mark.asyncio
async def test_cooldown_inert_when_gate_off_default():
    # Gate OFF (production default): the cooldown block is skipped entirely, even within
    # the window. Behaviour is byte-identical to pre-cooldown. The flip to ON is the
    # C3-gated signed decision; merging the code must not change behaviour.
    state = _within_cooldown_state()
    with patch.object(ss, "SKILL_OFFER_COOLDOWN_ENABLED", False), \
         patch.object(ss, "_semantic_match_with_runner_up", return_value=("worry_time", 0.62, None)):
        result = await ss.skill_select_node(state)
    assert "offer_cooldown_suppressed" not in result["path"]


def test_cooldown_flag_defaults_off():
    # The module-bound flag must be False when the env var is unset, so merging ships inert.
    import sage_poc.config as cfg
    assert cfg.SKILL_OFFER_COOLDOWN_ENABLED is False
