import json
from pathlib import Path
from sage_poc.skills.schema import Skill, load_skill


def test_load_cbt_skill():
    skill = load_skill("cbt_thought_record")
    assert skill.skill_id == "cbt_thought_record"
    assert skill.skill_type == "structured"
    assert len(skill.steps) == 3
    assert len(skill.step_policy) >= 2


def test_skill_step_has_required_fields():
    skill = load_skill("cbt_thought_record")
    for step in skill.steps:
        assert step.step_id
        assert step.goal
        assert step.technique
        assert step.tone
        assert len(step.examples) >= 2


def test_skill_policy_rule_structure():
    skill = load_skill("cbt_thought_record")
    for rule in skill.step_policy:
        assert rule.condition.signal
        assert rule.condition.operator
        assert rule.condition.value is not None
        assert rule.action
        assert rule.instruction
