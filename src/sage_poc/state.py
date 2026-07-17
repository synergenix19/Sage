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
    medical_flags: list[str]    # B1/E3: verbatim §1 red-flag phrase ids fired this turn; empty until the interim guard or full detector populates it. Declared channel (LangGraph drops undeclared keys).
    s3_score: Optional[float]    # advisory BGE-M3 cosine similarity; 0 recall adds at 0.8059 per CRADLE sweep
    clinical_flags: list[str]   # substance_use, trauma_indicator, eating_concern, medication_mention
    new_clinical_flags_turn: list[str]  # flags detected THIS turn only; reset each turn in _build_state()
    medical_flags: list[str]    # E3 medical red-flag channel read by safety_precedence._medical_fired; empty until B1 (medical red-flag screen) writes it. Declared now so B1's write survives the node->node seam (would otherwise be dropped like SG-2's step_mandatory_caveat).
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
    hr_terminal_step: Optional[str]    # HR-1 Stage 2: high_risk_response's own 2-3 turn step machinery ("await_distress" | "reask" | None); persists via checkpoint like active_step_id. Declared channel (LangGraph drops undeclared keys between nodes -- the SG-2 bug).
    hr_escalate_regardless: bool       # HR-1 Stage 2 Finding 1: mania_behavior_underway(message_en) computed at HR entry, persisted across the protocol so a later low numeric distress score can never mask risky-behavior-already-underway evidence (resolve_hr_branch ORs this in). Declared channel, same reason as hr_terminal_step.
    hr_branch: Optional[str]           # HR-1 Stage 2 Task 3: "higher" | "lower", set the turn high_risk_response resolves the distress branch. Task 3's node-level tests called the node directly and never caught that this was undeclared -- LangGraph silently dropped it between nodes (found by Task 4's full-graph wiring, the same SG-2 seam class). Declared channel, per-turn (only present on the delivery turn).
    hr_distress_score: Optional[int]   # HR-1 Stage 2 Task 3: parsed 0-10 distress score on the delivery turn; same undeclared-channel gap as hr_branch above, same fix.
    hr_referral_delivered: Optional[bool]  # HR-1 Stage 2 Task 4 fix: True once high_risk_response delivers a terminal branch ("higher"/"lower"); persists via checkpoint for the session. One-shot guard on _route_after_safety's HR ENTRY check, mirroring Stage 1's psychotic_referral_delivered -- without it, clinical_flags' session-lifetime persistence (never cleared) re-fires the ENTRY branch and re-asks the distress question on every later turn. Declared channel (LangGraph drops undeclared keys between nodes, the SG-2 bug class).
    executed_step_id: Optional[str]    # step whose instruction was used THIS turn (for audit)
    step_instruction: Optional[str]
    step_mandatory_caveat: str         # SG-2: executed step's contraindication caveat, written by skill_executor and read by output_gate to deliver VERBATIM. MUST be a declared channel — LangGraph drops undeclared keys between nodes (fixed 2026-07-15; the node->node seam that silently no-op'd SG-2 for all skills). Empty for non-safety steps.
    rule_fired: Optional[bool]         # True when a step_policy rule override replaced the default step instruction; reset each turn
    prev_step_id: Optional[str]        # step executed on the PREVIOUS turn; persists via LangGraph checkpoint for continuation detection
    prev_primary_intent: Optional[Intent]  # primary_intent of the PREVIOUS turn; persists via checkpoint (absent from _build_state, not reset). Used to detect a CONSECUTIVE info_request ("lookup mode") so the composer switches info_request from the question-close base to the statement-bridge repeat variant. An intervening non-info_request turn resets it, restoring the question-close (re-triage after a context switch).
    skill_match_method: Optional[str]   # "keyword" | "semantic" | "post_crisis_auto_select" | "psychotic_disclosure_auto_select" | "info_request_skill_consult" | None
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

    gate_path: Optional[Literal["standard", "scope_refusal", "jailbreak", "crisis", "medical", "high_risk"]]

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

    # D1 medical screen (#338) — declared channels (LangGraph drops undeclared keys; declare-before-write,
    # the state-channel lesson). ACCEPTANCE: a contraindication decision must be traceable to its rule +
    # answer for the PDPL right-to-object story. Written by the screen wiring; empty for non-screen turns.
    screen_asked: bool                     # the D1 discriminating question was asked this turn (per-turn)
    screen_answer_class: Optional[str]     # clear_no | red_flag | contraindication_disclosed | yes | unclear | no_answer (per-turn audit)
    screen_branch_taken: Optional[str]     # proceed | medical_guard | grounding | abandoned_crisis (per-turn)
    # #338 SILENT shadow observation (per-turn): the would-be screen decision when D1_SCREEN_SHADOW is on and
    # enforce is off. Written by apply_screen_at_route, READ by _build_session_audit_row -> the per-turn audit
    # row. DECLARED here so LangGraph does not drop them between skill_select and output_gate (the SG-2 seam
    # class). Anonymised class+route only (PDPL-approved 2026-07-17); no message content ever.
    screen_shadow_action: Optional[str]        # ask_screen | proceed | reroute_grounding | to_medical_guard | abandon_crisis
    screen_shadow_answer_class: Optional[str]  # the would-be answer class (None on a fire/ask turn)
    screen_shadow_branch: Optional[str]        # the would-be branch (None on a fire/ask turn)
    # PER-SESSION (persist across turns via the checkpointer — NOT reset per-turn, unlike the directives
    # above). A clear_no once → never re-screened this session; a not-cleared answer → never re-offered TIPP.
    session_screen_answer: Optional[str]   # the session's settled screen answer class; None = not yet screened
    screen_pending: bool                   # a screen question was asked; set on the emit turn, consumed next turn
    screen_held_skill: Optional[str]       # PER-SESSION: the contraindicated skill held while the screen is
                                           # pending; resumed on a clear_no answer, cleared on any release
    answering_screen: bool                 # PER-TURN: set by consume_pending_screen at graph entry when a
                                           # screen was pending; the structural guarantee the hold outlives
                                           # exactly one turn (screen_pending cleared the same turn)


def safety_text(state: SageState) -> str:
    """The text every safety-critical detector MUST read: the RAW user input in its original
    language, NEVER the translated message_en.

    Language contract (ADR 2026-07-16): crisis lexicon, clinical flags, vetoes, red-flag guards,
    and contraindication triggers operate on raw input; message_en exists for therapeutic
    processing / LLM rendering only, and is never a safety-detection input. Routing a safety
    decision through the translator makes recall hostage to translation quality on distress-register
    Khaleeji — the #329 (medical red-flag) and #330 (OCD-compulsion) live prod bypasses. Detectors
    call this accessor so the safe path is the ONLY path and new detectors inherit raw by
    construction. Enforced by scripts/check_safety_reads_raw.py.
    """
    return state.get("raw_message") or ""
