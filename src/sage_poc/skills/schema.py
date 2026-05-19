import json
from pathlib import Path
from pydantic import BaseModel

SKILLS_DIR = Path(__file__).parent


class StepPolicyCondition(BaseModel):
    signal: str       # "emotional_intensity" | "engagement" | etc.
    operator: str     # ">" | "<" | ">=" | "<=" | "=="
    value: int | float
    step: str         # "ANY" or a specific step_id


class StepPolicyRule(BaseModel):
    condition: StepPolicyCondition
    action: str
    instruction: str
    next_step_id: str = "current"


class SkillStep(BaseModel):
    step_id: str
    goal: str
    technique: str
    tone: str
    examples: list[str]


class Skill(BaseModel):
    skill_id: str
    skill_name: str
    skill_type: str
    evidence_base: str
    target_presentations: list[str]
    steps: list[SkillStep]
    step_policy: list[StepPolicyRule]
    escalation_matrix: dict[str, str]


def load_skill(skill_id: str) -> Skill:
    path = SKILLS_DIR / f"{skill_id}.json"
    data = json.loads(path.read_text())
    return Skill.model_validate(data)
