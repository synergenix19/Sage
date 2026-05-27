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


def test_post_crisis_check_in_skill_loads_and_validates():
    skill = load_skill("post_crisis_check_in")
    assert skill.skill_id == "post_crisis_check_in"
    assert len(skill.steps) == 2
    assert skill.steps[0].step_id == "acknowledge_and_check"
    assert skill.steps[1].step_id == "bridge_or_close"
    assert len(skill.target_presentations) >= 1  # populated in 7-pass audit (was empty [])
    assert skill.semantic_description != ""
    assert len(skill.step_policy) == 7  # upgraded to 7 rules post M-7 audit
    assert skill.step_policy[0].condition.signal == "re_escalation_detected"  # highest priority: NEW_CRISIS


def test_skill_step_has_technique_description_field():
    from sage_poc.skills.schema import SkillStep
    step = SkillStep(
        step_id="test", goal="g", technique="t", tone="t",
        examples=[], technique_description="A detailed description."
    )
    assert step.technique_description == "A detailed description."


def test_skill_step_technique_description_defaults_empty():
    from sage_poc.skills.schema import SkillStep
    step = SkillStep(step_id="test", goal="g", technique="t", tone="t", examples=[])
    assert step.technique_description == ""


def test_cbt_thought_record_steps_have_technique_descriptions():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("cbt_thought_record")
    for step in skill.steps:
        assert step.technique_description, (
            f"Step '{step.step_id}' has empty technique_description in cbt_thought_record.json"
        )


def test_load_skill_without_technique_description_defaults_empty():
    from sage_poc.skills.schema import load_skill
    # behavioral_activation.json has no technique_description field on steps
    skill = load_skill("behavioral_activation")
    for step in skill.steps:
        assert step.technique_description == "", (
            f"Step '{step.step_id}' should default to empty technique_description"
        )


def test_cultural_overrides_field_is_not_dropped():
    """Skills with cultural_overrides in JSON must have the field accessible on the model."""
    from sage_poc.skills.schema import Skill
    raw = {
        "skill_id": "test_skill",
        "skill_name": "Test Skill",
        "skill_type": "structured",
        "evidence_base": "Test evidence",
        "target_presentations": ["test phrase"],
        "steps": [],
        "step_policy": [],
        "escalation_matrix": {"L1": "exit", "L2": "flag", "L3": "crisis", "L4": "handoff"},
        "cultural_overrides": {"gulf_arab": "adjust tone"},
    }
    skill = Skill.model_validate(raw)
    assert skill.cultural_overrides == {"gulf_arab": "adjust tone"}


def test_cultural_overrides_null_coerced_to_empty_dict():
    """Skills with cultural_overrides: null in JSON must load as empty dict, not None."""
    from sage_poc.skills.schema import Skill
    raw = {
        "skill_id": "test_skill2",
        "skill_name": "Test Skill 2",
        "skill_type": "structured",
        "evidence_base": "Test evidence",
        "target_presentations": [],
        "steps": [],
        "step_policy": [],
        "escalation_matrix": {"L1": "exit", "L2": "flag", "L3": "crisis", "L4": "handoff"},
        "cultural_overrides": None,
    }
    skill = Skill.model_validate(raw)
    assert skill.cultural_overrides == {}
    assert isinstance(skill.cultural_overrides, dict)


def test_cbt_thought_record_has_cultural_overrides():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("cbt_thought_record")
    assert isinstance(skill.cultural_overrides, dict)
    assert len(skill.cultural_overrides) > 0, "cultural_overrides must be populated, not empty"


def test_grounding_has_cultural_overrides():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("grounding_5_4_3_2_1")
    assert isinstance(skill.cultural_overrides, dict)
    assert len(skill.cultural_overrides) > 0


def test_sleep_hygiene_cultural_overrides_is_populated_dict():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("sleep_hygiene")
    assert isinstance(skill.cultural_overrides, dict)
    assert len(skill.cultural_overrides) > 0, "sleep_hygiene cultural_overrides must be populated, not null/empty"


def test_post_crisis_check_in_cultural_overrides_is_populated_dict():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("post_crisis_check_in")
    assert isinstance(skill.cultural_overrides, dict)
    assert len(skill.cultural_overrides) > 0


def test_post_crisis_check_in_steps_have_technique_description():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("post_crisis_check_in")
    for step in skill.steps:
        assert step.technique_description, (
            f"step '{step.step_id}' is missing technique_description"
        )


def test_dbt_tipp_loads_and_validates():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("dbt_tipp")
    assert skill.skill_id == "dbt_tipp"
    assert skill.skill_type == "structured"
    assert len(skill.steps) == 4
    assert skill.steps[0].step_id == "temperature"
    assert skill.steps[1].step_id == "intense_exercise"
    assert skill.steps[2].step_id == "paced_breathing"
    assert skill.steps[3].step_id == "check_in"

def test_dbt_tipp_all_steps_fully_populated():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("dbt_tipp")
    for step in skill.steps:
        assert step.technique_description, f"step '{step.step_id}' missing technique_description"
        assert step.contraindications, f"step '{step.step_id}' missing contraindications"
        assert step.completion_criteria, f"step '{step.step_id}' missing completion_criteria"
        arabic_examples = [e for e in step.examples if any('؀' <= c <= 'ۿ' for c in e)]
        assert arabic_examples, f"step '{step.step_id}' has no Arabic examples"

def test_dbt_tipp_has_cultural_overrides():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("dbt_tipp")
    assert len(skill.cultural_overrides) > 0

def test_dbt_tipp_in_skill_registry():
    from sage_poc.skill_ids import SKILL_REGISTRY
    assert "dbt_tipp" in SKILL_REGISTRY
