"""S2-7 B2 — declined-skills signal to freeflow (consent integrity).

When the user has DECLINED skills this session, freeflow must be told which ones
(plain-language display names) so it does not re-offer or walk the user through
that specific content in prose. Closes the consent leak where a user declines a
skill and freeflow then delivers it anyway.

B1 (the safety guardrail / entry-screen boundary) is a separate change on PR #8.
These tests cover B2 only: the declined-skills signal layered onto freeflow.
"""
import json
from pathlib import Path

import pytest

from sage_poc.prompts.loader import get_intent_template, reload_all

_PROMPTS_DIR = Path(__import__("sage_poc.prompts", fromlist=["__file__"]).__file__).parent


@pytest.fixture(autouse=True)
def _fresh_templates():
    reload_all()
    yield
    reload_all()


def _composer_state(**overrides) -> dict:
    base = {
        "raw_message": "I keep worrying about everything",
        "message_en": "I keep worrying about everything",
        "detected_language": "en",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "new_clinical_flags_turn": [],
        "third_party_crisis": False,
        "crisis_state": "none",
        "code_switching": False,
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "intent_confidence": 0.9,
        "emotional_intensity": 5,
        "engagement": 6,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "rule_fired": None,
        "knowledge_passages": [],
        "knowledge_abstain": False,
        "knowledge_source": "",
        "conversation_history": [],
        "conversation_summary": None,
        "therapeutic_profile": None,
        "path": [],
        "turn_count": 1,
    }
    return {**base, **overrides}


class TestDeclinedSkillsSignal:
    def test_signal_present_on_freeflow_when_skills_declined(self):
        from sage_poc.prompts.composer import compose_prompt
        state = _composer_state(declined_skills=["worry_time", "cognitive_restructuring"])
        system_str, user_str, layers = compose_prompt(state)
        assert "declined_skills_signal" in layers
        # Names the declined skills by display name, not raw skill_id.
        assert "Worry time" in user_str
        assert "Reframing practice" in user_str
        assert "worry_time" not in user_str
        assert "cognitive_restructuring" not in user_str
        # Instructs the model not to re-offer / re-deliver that content.
        lowered = user_str.lower()
        assert "do not re-offer" in lowered or "do not offer" in lowered
        assert "walk" in lowered or "deliver" in lowered

    def test_no_signal_when_no_declined_skills(self):
        from sage_poc.prompts.composer import compose_prompt
        state = _composer_state()  # declined_skills absent
        system_str, user_str, layers = compose_prompt(state)
        assert "declined_skills_signal" not in layers

    def test_no_signal_when_declined_skills_empty(self):
        from sage_poc.prompts.composer import compose_prompt
        state = _composer_state(declined_skills=[])
        system_str, user_str, layers = compose_prompt(state)
        assert "declined_skills_signal" not in layers

    def test_no_signal_on_skill_execution_turn(self):
        from sage_poc.prompts.composer import compose_prompt
        state = _composer_state(
            declined_skills=["worry_time"],
            step_instruction="Guide the user through step one.",
            active_skill_id="box_breathing",
            executed_step_id="step_1",
        )
        system_str, user_str, layers = compose_prompt(state)
        assert "declined_skills_signal" not in layers, (
            "the declined-skills signal must not interfere with skill execution turns"
        )

    def test_ar_display_name_falls_back_to_en_when_ar_null(self):
        from sage_poc.prompts.composer import compose_prompt
        state = _composer_state(
            detected_language="ar",
            raw_message="أشعر بالقلق",
            declined_skills=["worry_time"],
        )
        system_str, user_str, layers = compose_prompt(state)
        assert "declined_skills_signal" in layers
        # ar is null in offer_descriptions.json -> falls back to en display name.
        assert "Worry time" in user_str

    def test_declined_note_deducts_from_l1_budget(self):
        from sage_poc.prompts.composer import _compute_l1_budget
        state = _composer_state()
        base = _compute_l1_budget(state)
        reduced = _compute_l1_budget(state, declined_words=90)
        assert reduced == base - 90

    def test_no_em_dash_in_governed_content(self):
        path = _PROMPTS_DIR / "declined_skills_instruction.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert raw["_meta"]["approved_by"] == "clinical_lead"
        assert raw["_meta"]["status"] == "approved"
        for value in raw["instruction"].values():
            assert "—" not in value, "em dashes mirror into LLM output; use commas"

    def test_no_em_dash_in_rendered_note(self):
        from sage_poc.prompts.composer import compose_prompt
        state = _composer_state(declined_skills=["worry_time", "behavioral_activation"])
        system_str, user_str, layers = compose_prompt(state)
        assert "—" not in user_str
