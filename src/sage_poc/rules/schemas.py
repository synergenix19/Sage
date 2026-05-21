from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
from pydantic import BaseModel


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
    language: Literal["en", "ar", "any"] = "any"
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
    trigger_keywords: list[str]
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
        "keyword_match", "flag_present", "intent_match", "secondary_intent_present"
    ]
    trigger_value: str | None = None
    trigger_keywords: list[str] = []
    action: dict


@dataclass
class FiredRule:
    rule_id: str
    version: str
    action: dict
    suppressed: bool = False


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
