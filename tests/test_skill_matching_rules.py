"""skill_matching rules category: first-match-wins by priority over named signals.
The fired rule's action drives skill_select's offer-vs-direct-entry decision;
the fired rule_id goes into the audit path."""
import pytest
from pydantic import ValidationError

from sage_poc.rules import engine as rules_engine
from sage_poc.rules.loader import reload_all
from sage_poc.rules.schemas import SkillMatchingRule


def _ctx(**overrides) -> dict:
    base = {"matched_skill_id": "cbt_thought_record", "emotional_intensity": 5}
    return {**base, **overrides}


class TestEvaluator:
    def setup_method(self):
        reload_all()

    def test_acute_match_high_intensity_fires_enter_direct(self):
        res = rules_engine.evaluate("skill_matching", _ctx(
            matched_skill_id="box_breathing", emotional_intensity=9))
        assert res.fired and res.fired[0].rule_id == "acute_direct_entry"
        assert res.fired[0].action["type"] == "enter_direct"
        assert res.fired[0].action["ignore_declined"] is True

    def test_acute_skill_low_intensity_falls_to_default_offer(self):
        res = rules_engine.evaluate("skill_matching", _ctx(
            matched_skill_id="box_breathing", emotional_intensity=4))
        assert res.fired and res.fired[0].rule_id == "default_offer"
        assert res.fired[0].action["type"] == "offer"
        assert res.fired[0].action["max_offered"] == 2
        assert res.fired[0].action["declined_scope"] == "session"

    def test_non_acute_skill_high_intensity_still_offers(self):
        res = rules_engine.evaluate("skill_matching", _ctx(
            matched_skill_id="cbt_thought_record", emotional_intensity=9))
        assert res.fired and res.fired[0].rule_id == "default_offer"

    def test_exactly_one_rule_fires(self):
        res = rules_engine.evaluate("skill_matching", _ctx())
        assert len(res.fired) == 1, "first-match-wins: exactly one rule fires"


class TestSchemaGuards:
    _BASE = dict(
        rule_id="x", category="skill_matching", effective_date="2026-06-12",
        action={"type": "offer", "max_offered": 2, "declined_scope": "session"},
    )

    def test_unknown_condition_key_rejected_at_load(self):
        with pytest.raises(ValidationError, match="dead-signal"):
            SkillMatchingRule.model_validate(
                {**self._BASE, "condition": {"moon_phase_gte": 3}})

    def test_unknown_action_type_rejected(self):
        with pytest.raises(ValidationError):
            SkillMatchingRule.model_validate(
                {**self._BASE, "action": {"type": "teleport"}})

    def test_unimplemented_declined_scope_rejected(self):
        with pytest.raises(ValidationError, match="session"):
            SkillMatchingRule.model_validate(
                {**self._BASE,
                 "action": {"type": "offer", "max_offered": 2, "declined_scope": "persistent"}})
