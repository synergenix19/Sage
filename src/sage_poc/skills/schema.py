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


class SkillMediaItem(BaseModel):
    # Item 3 (SkillStep.media): a single media resource for one language.
    # Provider-agnostic full URL (never a bare id), same contract as Source.url.
    type: Literal["video"] = "video"
    url: str
    title: str = ""
    provider: str = ""                # attribution, e.g. "UCLA Health"


class SkillStep(BaseModel):
    step_id: str
    goal: str
    technique: str
    technique_description: str = ""
    tone: str
    examples: list[str]
    contraindications: str = ""
    completion_criteria: str = ""
    # Item 3: optional per-language media, keyed by language ("en", "ar"), mirroring
    # the bilingual `examples` pattern. null = no media (byte-identical pre-Item-3).
    media: dict[str, SkillMediaItem] | None = None


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
    criteria_hold_budget: int | None = Field(
        default=None, ge=1,
        description="Max consecutive criteria holds per step before soft advance. "
                    "null = no budget (hold indefinitely, current behavior). "
                    "Clinician-ownable per skill.",
    )
    hold_ceiling: int | None = Field(
        default=None, ge=1,
        description="Max consecutive deterministic non-safety rule-holds at one step before "
                    "the hold surfaces the user-owned exit ramp instead of re-probing. "
                    "null = unbounded (current behavior). Clinical holds stay senior (no forced "
                    "advance); this only bounds re-probing. Clinician-ownable per skill.",
    )

    @field_validator("cultural_overrides", mode="before")
    @classmethod
    def coerce_none_to_dict(cls, v):
        return v if v is not None else {}


def load_skill(skill_id: str) -> Skill:
    path = SKILLS_DIR / f"{skill_id}.json"
    data = json.loads(path.read_text())
    return Skill.model_validate(data)
