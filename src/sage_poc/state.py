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
    s3_score: Optional[float]    # advisory BGE-M3 cosine similarity; 0 recall adds at 0.8059 per CRADLE sweep
    clinical_flags: list[str]   # substance_use, trauma_indicator, eating_concern, medication_mention
    new_clinical_flags_turn: list[str]  # flags detected THIS turn only; reset each turn in _build_state()
    third_party_crisis: bool    # user is concerned about someone else's safety, not their own

    crisis_state: str              # "none" | "active" | "monitoring" | "resolved"
    # v7.1 crisis tiering (flag-gated). MUST be declared channels: LangGraph silently DROPS any key
    # a node returns that is not in this TypedDict, so without these, safety_check's crisis_tier never
    # reaches _route_after_safety or the audit (graph state = NULL) even though the node computed it.
    # This absence was invisible to every unit/proof test because they read safety_check's RETURN dict
    # directly, never the post-reducer graph state (bug #2, 2026-07-04).
    crisis_tier: Optional[str]         # "T1" warm | "T2" acute | "none"; None/absent when flag OFF
    tier_rule_id: Optional[str]        # tier_routing.json rule id that resolved the tier (audit trail)
    supportive_posture: bool           # T1 warm-posture instruction injected into freeflow this turn
    t1_count: int                      # G1b session counter: # of T1 turns (2nd triggers one flag_for_review)
    psychotic_referral_delivered: Optional[bool]   # True after psychotic_referral completes; prevents re-selection loop within session
    s7_result: Optional[str]       # "RECOVERING" | "STILL_DISTRESSED" | "UNCLEAR" | "NEW_CRISIS"
    s7_method: Optional[str]       # "keyword" | "llm"
    re_escalation_within_monitoring: Optional[bool]  # True when crisis fires while crisis_state was already "monitoring"
    monitoring_clear_turns: int    # W2/G4: count of CONSECUTIVE S7-clear (RECOVERING + is_safe) monitoring turns; 2 -> step down monitoring->supportive. Declared channel (LangGraph drops undeclared keys).
    # B0 (BOT BEHAVIOUR §4.5) deterministic safety-route precedence — flag-gated (SAGE_ROUTE_PRECEDENCE,
    # default OFF). ABSENT when OFF (byte-identical master). Declared channels: LangGraph silently DROPS
    # any key a node returns that is not in this TypedDict (same class as the crisis_tier bug #2 2026-07-04).
    precedence_winner: Optional[str]     # highest-precedence safety route that fired this turn (crisis>medical>hr>ipv), or None
    fired_safety_routes: list[str]       # ALL safety routes that fired this turn — recorded even when precedence suppressed the lower ones (§4.5 never-dropped); consumed by the audit row
    distress_trajectory: list[int]
    engagement_trajectory: list[int]
    conversation_summary: Optional[str]
    code_switching: bool
    directive_posture: bool   # deterministic flag: user explicitly delegated / is frustrated by questions and wants direct guidance (set in intent_route, NOT the LLM classifier)
    prepass_matched: list[str]    # v7.2 Node-2 keyword pre-pass: skill_ids whose triggers matched deterministically (rules-first, before the classifier). Routing HINT only; never force-enters. Declared channel (reducer drops undeclared keys).
    prepass_rule_id: Optional[str]  # provenance of the pre-pass match for the audit trail
    self_reference: bool      # deterministic flag: user is asking to recall their own prior disclosure (set in intent_route); sole consumer is composer eviction-exemption

    primary_intent: Optional[Intent]
    secondary_intent: Optional[Intent]  # blended intent — e.g. "info_request" alongside "new_skill"
    intent_confidence: float
    emotional_intensity: int   # 1–10
    engagement: int            # 1–10

    active_skill_id: Optional[str]
    completed_skill_id: Optional[str]  # set on skill_complete turn for audit attribution; reset to None each turn via _build_state
    active_step_id: Optional[str]      # step the NEXT turn will start from
    executed_step_id: Optional[str]    # step whose instruction was used THIS turn (for audit)
    step_instruction: Optional[str]
    rule_fired: Optional[bool]         # True when a step_policy rule override replaced the default step instruction; reset each turn
    prev_step_id: Optional[str]        # step executed on the PREVIOUS turn; persists via LangGraph checkpoint for continuation detection
    prev_primary_intent: Optional[Intent]  # primary_intent of the PREVIOUS turn; persists via checkpoint (absent from _build_state, not reset). Used to detect a CONSECUTIVE info_request ("lookup mode") so the composer switches info_request from the question-close base to the statement-bridge repeat variant. An intervening non-info_request turn resets it, restoring the question-close (re-triage after a context switch).
    skill_match_method: Optional[str]   # "keyword" | "semantic" | None
    semantic_score: Optional[float]     # cosine similarity if semantic match
    offered_skill_ids: Optional[list[str]]  # R1: 1-2 skills offered, pending accept/decline; persists via checkpoint; cleared on accept (skill_select), decline/ignore (intent_route), crisis (crisis_response), stale gap
    last_offer_turn: Optional[int]           # D3: turn_count when the last skill offer was made; used by offer cooldown in skill_select
    offer_response: Optional[str]           # R1: "accept" | "decline" | "other"; per-turn, reset in _build_state
    offer_choice_skill_id: Optional[str]    # R1: skill chosen on accept; per-turn, reset in _build_state
    declined_skills: list[str]              # R1: skills declined this session; never re-offered (declined_scope "session" in skill_matching rules); persists via checkpoint; cleared at 4h stale gap
    offer_count: int                        # consecutive turns the current offer has been shown: set to 1 when an offer is first made (skill_select), +1 each re-ask (offer_unparsed in intent_route), 0 when no/resolved offer; persists via checkpoint; cleared at 4h stale gap. Drives the composer's reoffer variant.
    prompt_layers: list[str]            # layer names included in the composed LLM prompt
    token_usage: dict                   # {"input": N, "output": N, "total": N} from LLM
    escalation_triggered: Optional[dict]  # {"level": "L1"|"L2", "reason": str, "action": str}
    resistance_history: list[int]       # rolling 3-turn Falcon-3B resistance scores; persists via LangGraph checkpoint across turns within a session
    resistance_score: Optional[int]     # current turn's resistance score; reset each turn in _build_state()
    criteria_hold_count: int                 # R5: consecutive criteria holds at the current step; persists via LangGraph checkpoint
    criteria_hold_step_id: Optional[str]     # R5: step the hold counter belongs to; persists via LangGraph checkpoint
    rule_hold_count: int                  # D/S2-4: consecutive deterministic non-safety rule-holds at the current step; persists via checkpoint
    rule_hold_step_id: Optional[str]       # D/S2-4: step the rule-hold counter belongs to; persists via checkpoint

    cultural_output_violations: list[str]  # rule_ids fired in output_gate cultural check

    knowledge_passages: list[dict]  # [{text, source_id, citation, relevance_score, source_url, title, video_url}]
    knowledge_abstain: bool         # True when no relevant evidence found
    knowledge_source: str           # "node_6" | "tool_lookup" | "" (empty when no retrieval)
    knowledge_query_raw: str        # query as submitted (pre-normalization)
    knowledge_query_searched: str   # query actually searched (post-normalization)
    knowledge_top_similarity: float | None  # best cosine sim in the returned pack; drives abstain

    gate_path: Optional[Literal["standard", "scope_refusal", "jailbreak", "crisis"]]

    response_en: Optional[str]
    response: Optional[str]

    path: list[str]
    skill_select_abstained: bool   # per-turn (reset by _build_state): True only when the V2 reranker
    abstain_referral: Optional[str]   # #218: 'ocd_erp' on a vetoed-OCD abstain turn -> Node-8 pins the ERP referral; per-turn reset
    containment_directive: Optional[dict]   # Phase-2 T1: {family, flag_level, kb_topics, containment_skill_id?, rule_id} set ONLY by deterministic rules; per-turn reset; default None (inert until T2 contain-action + T3 edge wire it)
                                   # ABSTAINed (below-τ or keyword-veto) → routes to Node 3, not freeflow
    turn_count: int
    turn_number: int   # incremented by safety_check_node on every message; used for session_audit
    turn_started_at: float   # time.monotonic() stamped before ainvoke (server.py); output_gate uses it to compute latency_ms
    latency_ms: int          # per-turn graph latency, computed in output_gate from turn_started_at; written to session_audit
    freeflow_gen_ms: Optional[int]   # served English-arm generation time (_invoke_with_tool_loop), ms; set unconditionally by freeflow_respond_node (all languages, shadow flag on/off); written to session_audit
    translate_out_ms: Optional[int]  # served translate-out time (async_translate_to_arabic + strict retry), ms; set by output_gate_node, None when translate-out doesn't run; written to session_audit
    conversation_history: list[dict]
    stall_detected: Optional[bool]       # deterministic stall-guard signal (per-turn); set in intent_route, read by composer
    venting_detected: bool   # F6: deterministic PI-VI-001 don't-fix signal; consumed by _route_after_intent to suppress skill imposition (route to presence). Declared channel.
    therapeutic_profile: Optional[dict]  # loaded at turn start; injected into L5
    user_id:    Optional[str]            # authenticated user UUID from request
    session_id: Optional[str]            # = thread_id; needed by tools and summary persistence
    last_turn_at: Optional[str]          # UTC ISO timestamp of last completed turn (output_gate)
    stale_skill_id: Optional[str]        # skill parked due to session gap; cleared after re-entry prompt fires
    identity_substitution_rule_id: Optional[str]  # rule_id of CUO-ID-001 if response was substituted
    original_response_hash: Optional[str]          # sha256[:16] of original response — tamper-proof reference in main audit log
    original_response_text: Optional[str]          # full original response — written to restricted identity_substitution_audit table only
    banned_opener_retry_count: int
    banned_opener_correction: Optional[str]
    banned_opener_violation: bool          # True if banned opener persisted after retry AND passed through to user (no fallback)
    banned_opener_fallback_used: bool      # True when _VETTED_FALLBACK_RESPONSE substituted after exhausted retry
