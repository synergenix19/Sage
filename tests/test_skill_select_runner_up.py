import pytest
from unittest.mock import patch
from sage_poc.nodes import skill_select as ss


def test_runner_up_dropped_when_below_min():
    ranked = [("worry_time", 0.62), ("financial_anxiety", 0.47)]
    assert ss._select_runner_up(ranked, "worry_time", 0.62) is None  # 0.47 < MIN 0.50


def test_runner_up_dropped_when_outside_margin():
    ranked = [("worry_time", 0.70), ("grief_loss", 0.51)]
    # 0.51 >= MIN but 0.70-0.51=0.19 > MARGIN 0.05
    assert ss._select_runner_up(ranked, "worry_time", 0.70) is None


def test_runner_up_kept_when_strong_and_close():
    ranked = [("worry_time", 0.62), ("psychoed_stress", 0.59)]
    assert ss._select_runner_up(ranked, "worry_time", 0.62) == ("psychoed_stress", 0.59)


@pytest.mark.asyncio
async def test_noise_band_primary_routes_to_freeflow():
    """A semantic match in the noise band (below the offer floor) must not be offered."""
    state = {
        "primary_intent": "new_skill", "crisis_state": "none", "clinical_flags": [],
        "offered_skill_ids": None, "message_en": "i feel a bit off today",
        "raw_message": "i feel a bit off today", "detected_language": "en",
        "path": ["safety_check", "intent_route"], "declined_skills": [],
        "therapeutic_profile": {}, "emotional_intensity": 4,
    }
    with patch.object(ss, "_semantic_match_with_runner_up", return_value=("worry_time", 0.47, None)):
        result = await ss.skill_select_node(state)
    assert result["active_skill_id"] is None
    assert not result.get("offered_skill_ids")
    assert "offer_floor_freeflow" in result["path"]
