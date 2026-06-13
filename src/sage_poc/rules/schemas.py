from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class SafetyRule(BaseModel):
    rule_id: str
    version: str = "1.0.0"
    category: Literal["safety"]
    authored_by: str = "sage_clinics"
    approved_by: str | None = None
    effective_date: str
    active: bool = True
    description: str = ""
    match_type: Literal["keyword", "regex"]
    patterns: list[str]
    language: Literal["en", "ar", "az", "any"] = "any"
    modifiers: list[str] = []
    action: dict


class CrisisContentRule(BaseModel):
    rule_id: str
    version: str = "1.0.0"
    category: Literal["crisis_content"]
    authored_by: str = "sage_clinics"
    approved_by: str | None = None
    effective_date: str
    active: bool = True
    description: str = ""
    locale: str
    crisis_level: Literal["acute", "extended"]
    action: dict


class CulturalRule(BaseModel):
    rule_id: str
    version: str = "1.0.0"
    category: Literal["cultural"]
    authored_by: str = "sage_clinics"
    approved_by: str | None = None
    effective_date: str
    active: bool = True
    description: str = ""
    trigger_type: Literal["keyword_match", "code_switch"] = "keyword_match"
    trigger_keywords: list[str] = []
    language: Literal["en", "ar", "any"] = "any"
    action: dict


class PromptInjectionRule(BaseModel):
    rule_id: str
    version: str = "1.0.0"
    category: Literal["prompt_injection"]
    authored_by: str = "sage_clinics"
    approved_by: str | None = None
    effective_date: str
    active: bool = True
    description: str = ""
    trigger_type: Literal[
        "keyword_match", "flag_present", "intent_match",
        "secondary_intent_present", "session_flag_present"
    ]
    trigger_value: str | None = None
    trigger_keywords: list[str] = []
    action: dict


class CulturalOutputRule(BaseModel):
    rule_id: str
    version: str = "1.0.0"
    category: Literal["cultural_output"]
    authored_by: str = "sage_clinics"
    approved_by: str | None = None
    effective_date: str
    active: bool = True
    description: str = ""
    check_type: Literal["blocklist", "allowlist_required"]
    condition_type: Literal["always", "keyword_in_message", "flag_present"]
    condition_keywords: list[str] = []
    condition_value: str | None = None
    patterns: list[str]
    action: dict


# Condition keys _eval_skill_matching resolves at runtime. Any key outside this set
# is spec-present-runtime-inert, the exact failure class behind the 21 dead
# step_policy signals. Reject at load, never skip silently.
_SKILL_MATCHING_CONDITION_KEYS = frozenset({"matched_skill_in", "emotional_intensity_gte"})


class SkillMatchingRule(BaseModel):
    rule_id: str
    version: str = "1.0.0"
    category: Literal["skill_matching"]
    authored_by: str = "sage_clinics"
    approved_by: str | None = None
    effective_date: str
    active: bool = True
    description: str = ""
    priority: int = 100          # ascending; first match wins
    condition: dict = Field(default_factory=dict)   # empty = always matches
    action: dict

    @field_validator("condition")
    @classmethod
    def known_condition_keys_only(cls, v):
        unknown = set(v) - _SKILL_MATCHING_CONDITION_KEYS
        if unknown:
            raise ValueError(
                f"skill_matching condition keys not resolvable at runtime: {sorted(unknown)}. "
                f"Known: {sorted(_SKILL_MATCHING_CONDITION_KEYS)} (dead-signal guard)."
            )
        if "matched_skill_in" in v and not isinstance(v["matched_skill_in"], list):
            raise ValueError(
                "matched_skill_in must be a list of skill ids; a bare string would "
                "silently degrade to a substring test in the evaluator"
            )
        if "emotional_intensity_gte" in v and not isinstance(v["emotional_intensity_gte"], int):
            raise ValueError("emotional_intensity_gte must be an integer")
        return v

    @field_validator("action")
    @classmethod
    def implemented_actions_only(cls, v):
        if "ignore_declined" in v:
            raise ValueError(
                "ignore_declined is removed (clinical decision 2026-06-13); use "
                "on_declined='substitute' with substitute_pool instead. Leaving "
                "ignore_declined in data is silently inert (dead-signal guard)."
            )
        if v.get("type") not in ("enter_direct", "offer"):
            raise ValueError(
                f"skill_matching action.type must be 'enter_direct' or 'offer', got {v.get('type')!r}"
            )
        if v.get("type") == "offer":
            if not isinstance(v.get("max_offered"), int) or v["max_offered"] < 1:
                raise ValueError("offer action requires integer max_offered >= 1")
            if v.get("declined_scope", "session") != "session":
                raise ValueError(
                    "declined_scope: only 'session' is implemented. Declaring other scopes "
                    "in data without runtime support recreates the dead-signal failure class."
                )
        if "on_declined" in v:
            if v["on_declined"] not in ("substitute", "offer"):
                raise ValueError(
                    f"on_declined must be 'substitute' or 'offer', got {v.get('on_declined')!r}"
                )
            if v["on_declined"] == "substitute":
                pool = v.get("substitute_pool")
                if not isinstance(pool, list) or not pool:
                    raise ValueError(
                        "on_declined 'substitute' requires a non-empty list substitute_pool; "
                        "a substitute action with no pool is silently inert (dead-signal guard)."
                    )
        return v


@dataclass
class FiredRule:
    rule_id: str
    version: str
    action: dict
    suppressed: bool = False
    matched_span: tuple[int, int] | None = None  # (start, end) of match in normalised text


@dataclass
class EvalResult:
    fired: list[FiredRule] = field(default_factory=list)

    @property
    def actions(self) -> list[dict]:
        return [
            r.action for r in self.fired
            if not r.suppressed and r.action.get("type") != "crisis_suppress"
        ]

    @property
    def fired_ids(self) -> list[str]:
        return [r.rule_id for r in self.fired]

    @property
    def suppressed_rules(self) -> list["FiredRule"]:
        return [r for r in self.fired if r.suppressed]

    def __bool__(self) -> bool:
        """True if any NON-suppressed rule fired. Use fired_ids for full audit."""
        return any(not r.suppressed for r in self.fired)
