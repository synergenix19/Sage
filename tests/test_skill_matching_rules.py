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
        assert res.fired[0].action["on_declined"] == "substitute"
        assert res.fired[0].action["substitute_pool"][0] == "grounding_5_4_3_2_1"

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

    def test_none_intensity_falls_back_to_default(self):
        res = rules_engine.evaluate("skill_matching", {
            "matched_skill_id": "box_breathing", "emotional_intensity": None})
        assert res.fired and res.fired[0].rule_id == "default_offer", (
            "None intensity must default to 5, below the acute threshold, never crash"
        )


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

    def test_string_matched_skill_in_rejected(self):
        with pytest.raises(ValidationError, match="list of skill ids"):
            SkillMatchingRule.model_validate(
                {**self._BASE, "condition": {"matched_skill_in": "box_breathing"}})

    def test_non_int_intensity_threshold_rejected(self):
        with pytest.raises(ValidationError, match="integer"):
            SkillMatchingRule.model_validate(
                {**self._BASE, "condition": {"emotional_intensity_gte": "8"}})

    def test_unknown_on_declined_value_rejected(self):
        with pytest.raises(ValidationError):
            SkillMatchingRule.model_validate(
                {**self._BASE,
                 "action": {"type": "enter_direct", "on_declined": "teleport"}})

    def test_substitute_without_pool_rejected(self):
        with pytest.raises(ValidationError, match="substitute_pool"):
            SkillMatchingRule.model_validate(
                {**self._BASE,
                 "action": {"type": "enter_direct", "on_declined": "substitute"}})

    def test_ignore_declined_rejected_at_load(self):
        with pytest.raises(ValidationError, match="ignore_declined"):
            SkillMatchingRule.model_validate(
                {**self._BASE,
                 "action": {"type": "enter_direct", "ignore_declined": True}})


class TestEvaluatorIsolated:
    """Direct _eval_skill_matching tests with constructed rules: no-rule-fires is a
    distinct meaningful outcome (skill_select falls back to consent offer)."""

    def _rule(self, **kwargs):
        base = dict(
            rule_id="r1", category="skill_matching", effective_date="2026-06-12",
            action={"type": "enter_direct"},
        )
        return SkillMatchingRule.model_validate({**base, **kwargs})

    def test_empty_rules_list_fires_nothing(self):
        from sage_poc.rules.engine import _eval_skill_matching
        res = _eval_skill_matching([], _ctx())
        assert res.fired == []

    def test_equal_priority_resolves_in_list_order(self):
        # Contract (2026-06-12): the loader pre-sorts by priority (stable, file order
        # on ties); the evaluator iterates in list order. Direct callers own ordering.
        from sage_poc.rules.engine import _eval_skill_matching
        r_a = self._rule(rule_id="a", priority=50)
        r_b = self._rule(rule_id="b", priority=50)
        res = _eval_skill_matching([r_a, r_b], _ctx())
        assert res.fired[0].rule_id == "a", "loader-sorted input: equal priority = list order"
