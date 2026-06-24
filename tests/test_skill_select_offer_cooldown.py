import pytest
from unittest.mock import patch
from sage_poc.nodes import skill_select as ss

@pytest.mark.asyncio
async def test_offer_suppressed_within_cooldown():
    state = {"primary_intent":"new_skill","crisis_state":"none","clinical_flags":[],
             "offered_skill_ids":None,"message_en":"i keep overthinking","raw_message":"i keep overthinking",
             "detected_language":"en","path":["safety_check","intent_route"],"declined_skills":[],
             "therapeutic_profile":{}, "emotional_intensity":5,
             "turn_count":6, "last_offer_turn":5}  # 1 turn since last offer, cooldown=2
    with patch.object(ss,"_semantic_match_with_runner_up",return_value=("worry_time",0.62,None)):
        result = await ss.skill_select_node(state)
    assert result["active_skill_id"] is None
    assert not result.get("offered_skill_ids")
    assert "offer_cooldown_suppressed" in result["path"]
