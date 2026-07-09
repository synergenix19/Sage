"""Wave-2 P0b — delivery_format schema field (BOT BEHAVIOUR Format column; H2 ruling 2026-07-10).

The field is additive with a default of guided_conversation, so every existing skill keeps its
current turn-by-turn behavior byte-for-byte. video_all_at_once is the new one-turn delivery for
the five Video-format skills, which were set to it (H2 tick + Vee sign-off 2026-07-10, structural
adoption); their collapsed EN copy is a separate follow-on that pairs with the AR translation.
"""
import json

import pytest
from pydantic import ValidationError

from sage_poc.skills.schema import SKILLS_DIR, Skill, load_skill


def test_delivery_format_defaults_to_guided_conversation():
    # Skills that do NOT set the field keep the default (current turn-by-turn behavior).
    # The 5 Video skills are explicitly video_all_at_once (see test_video_skills_delivery_format);
    # assert the default only on skills NOT in that set.
    assert load_skill("dbt_tipp").delivery_format == "guided_conversation"
    assert load_skill("grounding_5_4_3_2_1").delivery_format == "guided_conversation"
    assert load_skill("stop_technique").delivery_format == "guided_conversation"


def test_delivery_format_accepts_the_three_valid_values():
    data = json.loads((SKILLS_DIR / "box_breathing.json").read_text())
    for value in ("guided_conversation", "video_all_at_once", "single_message"):
        data["delivery_format"] = value
        assert Skill.model_validate(data).delivery_format == value


def test_delivery_format_rejects_unknown_value():
    data = json.loads((SKILLS_DIR / "box_breathing.json").read_text())
    data["delivery_format"] = "bogus"
    with pytest.raises(ValidationError):
        Skill.model_validate(data)
