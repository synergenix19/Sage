"""Wave-2 P0b — delivery_format schema field (BOT BEHAVIOUR Format column; H2 ruling 2026-07-10).

The field is additive with a default of guided_conversation, so every existing skill keeps its
current turn-by-turn behavior byte-for-byte. video_all_at_once is the new one-turn delivery for
the five Video-format skills (executor branch built separately; the 5 skills adopt it only after
the collapsed-copy sign-off).
"""
import json

import pytest
from pydantic import ValidationError

from sage_poc.skills.schema import SKILLS_DIR, Skill, load_skill


def test_delivery_format_defaults_to_guided_conversation():
    # existing skills unchanged: default = current turn-by-turn behavior
    assert load_skill("box_breathing").delivery_format == "guided_conversation"
    assert load_skill("dbt_tipp").delivery_format == "guided_conversation"


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
