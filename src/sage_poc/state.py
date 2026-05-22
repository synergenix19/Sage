from typing import TypedDict, Optional, Literal

Intent = Literal[
    "skill_continuation", "new_skill", "general_chat",
    "crisis", "info_request", "exit_skill",
    "scope_refusal", "jailbreak",
]

class SageState(TypedDict):
    raw_message: str
    detected_language: str
    message_en: str

    is_safe: bool
    crisis_flags: list[str]
    clinical_flags: list[str]   # substance_use, trauma_indicator, eating_concern, medication_mention
    third_party_crisis: bool    # user is concerned about someone else's safety, not their own

    crisis_state: str              # "none" | "active" | "monitoring" | "resolved"
    s7_result: Optional[str]       # "RECOVERING" | "STILL_DISTRESSED" | "UNCLEAR" | "NEW_CRISIS"
    s7_method: Optional[str]       # "keyword" | "llm"
    distress_trajectory: list[int]
    engagement_trajectory: list[int]
    conversation_summary: Optional[str]
    code_switching: bool

    primary_intent: Optional[Intent]
    secondary_intent: Optional[Intent]  # blended intent — e.g. "info_request" alongside "new_skill"
    intent_confidence: float
    emotional_intensity: int   # 1–10
    engagement: int            # 1–10

    active_skill_id: Optional[str]
    active_step_id: Optional[str]      # step the NEXT turn will start from
    executed_step_id: Optional[str]    # step whose instruction was used THIS turn (for audit)
    step_instruction: Optional[str]
    skill_match_method: Optional[str]   # "keyword" | "semantic" | None
    semantic_score: Optional[float]     # cosine similarity if semantic match
    prompt_layers: list[str]            # layer names included in the composed LLM prompt
    token_usage: dict                   # {"input": N, "output": N, "total": N} from LLM
    escalation_triggered: Optional[dict]  # {"level": "L1"|"L2", "reason": str, "action": str}

    cultural_output_violations: list[str]  # rule_ids fired in output_gate cultural check

    gate_path: Optional[Literal["standard", "scope_refusal", "jailbreak", "crisis"]]

    response_en: Optional[str]
    response: Optional[str]

    path: list[str]
    turn_count: int
    conversation_history: list[dict]
