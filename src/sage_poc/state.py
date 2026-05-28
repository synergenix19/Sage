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
    new_clinical_flags_turn: list[str]  # flags detected THIS turn only; reset each turn in _build_state()
    third_party_crisis: bool    # user is concerned about someone else's safety, not their own

    crisis_state: str              # "none" | "active" | "monitoring" | "resolved"
    s7_result: Optional[str]       # "RECOVERING" | "STILL_DISTRESSED" | "UNCLEAR" | "NEW_CRISIS"
    s7_method: Optional[str]       # "keyword" | "llm"
    re_escalation_within_monitoring: Optional[bool]  # True when crisis fires while crisis_state was already "monitoring"
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
    rule_fired: Optional[bool]         # True when a step_policy rule override replaced the default step instruction; reset each turn
    prev_step_id: Optional[str]        # step executed on the PREVIOUS turn; persists via LangGraph checkpoint for continuation detection
    skill_match_method: Optional[str]   # "keyword" | "semantic" | None
    semantic_score: Optional[float]     # cosine similarity if semantic match
    prompt_layers: list[str]            # layer names included in the composed LLM prompt
    token_usage: dict                   # {"input": N, "output": N, "total": N} from LLM
    escalation_triggered: Optional[dict]  # {"level": "L1"|"L2", "reason": str, "action": str}
    resistance_history: list[int]       # rolling 3-turn Falcon-3B resistance scores; persists via LangGraph checkpoint across turns within a session
    resistance_score: Optional[int]     # current turn's resistance score; reset each turn in _build_state()

    cultural_output_violations: list[str]  # rule_ids fired in output_gate cultural check

    knowledge_passages: list[dict]  # [{text, source_id, citation, relevance_score}]
    knowledge_abstain: bool         # True when no relevant evidence found
    knowledge_source: str           # "node_6" | "tool_lookup" | "" (empty when no retrieval)

    gate_path: Optional[Literal["standard", "scope_refusal", "jailbreak", "crisis"]]

    response_en: Optional[str]
    response: Optional[str]

    path: list[str]
    turn_count: int
    turn_number: int   # incremented by safety_check_node on every message; used for session_audit
    conversation_history: list[dict]
    therapeutic_profile: Optional[dict]  # loaded at turn start; injected into L5
    user_id:    Optional[str]            # authenticated user UUID from request
    session_id: Optional[str]            # = thread_id; needed by tools and summary persistence
    last_turn_at: Optional[str]          # UTC ISO timestamp of last completed turn (output_gate)
    stale_skill_id: Optional[str]        # skill parked due to session gap; cleared after re-entry prompt fires
    identity_substitution_rule_id: Optional[str]  # rule_id of CUO-ID-001 if response was substituted
    original_response_hash: Optional[str]          # sha256[:16] of original response — tamper-proof reference in main audit log
    original_response_text: Optional[str]          # full original response — written to restricted identity_substitution_audit table only
