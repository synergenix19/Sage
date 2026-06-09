import json
from pathlib import Path
from typing import Literal
from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator

SKILLS_DIR = Path(__file__).parent


class StepPolicyCondition(BaseModel):
    signal: str       # "emotional_intensity" | "engagement" | etc.
    operator: str     # ">" | "<" | ">=" | "<=" | "=="
    value: int | float
    step: str         # "ANY" or a specific step_id
    # Accepts both "for_turns" (canonical) and legacy "turns" field name used in skill JSONs.
    for_turns: int | None = Field(
        default=None,
        validation_alias=AliasChoices("for_turns", "turns"),
    )


class StepPolicyRule(BaseModel):
    condition: StepPolicyCondition
    action: str
    instruction: str
    next_step_id: str = "current"

    @model_validator(mode='after')
    def validate_exit_warm_closing(self) -> 'StepPolicyRule':
        if self.action == "exit_warm_closing" and self.next_step_id != "exit":
            raise ValueError(
                f"exit_warm_closing rule must have next_step_id='exit', got '{self.next_step_id}'"
            )
        return self


class SkillStep(BaseModel):
    step_id: str
    goal: str
    technique: str
    technique_description: str = ""
    tone: str
    examples: list[str]
    contraindications: str = ""
    completion_criteria: str = ""


class Skill(BaseModel):
    skill_id: str
    skill_name: str
    skill_type: str
    evidence_base: str
    self_evolution: Literal["manual_only"] = "manual_only"
    target_presentations: list[str]
    semantic_description: str = ""   # rich description for embedding-based skill matching
    semantic_anchors: list[str] = Field(default_factory=list)
    steps: list[SkillStep]
    step_policy: list[StepPolicyRule]
    escalation_matrix: dict[str, str]
    cultural_overrides: dict = Field(default_factory=dict)

    @field_validator("cultural_overrides", mode="before")
    @classmethod
    def coerce_none_to_dict(cls, v):
        return v if v is not None else {}


def load_skill(skill_id: str) -> Skill:
    path = SKILLS_DIR / f"{skill_id}.json"
    data = json.loads(path.read_text())
    return Skill.model_validate(data)
