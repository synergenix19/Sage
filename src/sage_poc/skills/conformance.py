"""Schema field conformance registry.

Declares which fields in the Skill/SkillStep JSON schema are USED at runtime
vs STORED_ONLY. Surfaced at startup (log) and via GET /health/schema-conformance.
"""

SCHEMA_CONFORMANCE: dict[str, dict] = {
    # ---- SkillStep fields ----
    "step.goal": {
        "status": "USED",
        "injected_by": "compose_prompt → _build_l3_skill_block → L3_skill_wrapper ({step_goal})",
        "note": "Injected into user role on every skill turn.",
    },
    "step.technique": {
        "status": "USED",
        "injected_by": "compose_prompt → _build_l3_skill_block → L3_skill_wrapper ({technique_name})",
        "note": "Injected into user role on every skill turn.",
    },
    "step.technique_description": {
        "status": "USED",
        "injected_by": "compose_prompt → _build_l3_skill_block → L3_skill_wrapper ({technique_description})",
        "note": "Optional. Appended to technique name when non-empty.",
    },
    "step.tone": {
        "status": "USED",
        "injected_by": "compose_prompt → _build_l3_skill_block → L3_skill_wrapper ({tone_instruction})",
        "note": "Injected into user role on every skill turn.",
    },
    "step.examples": {
        "status": "USED",
        "injected_by": "compose_prompt → _build_l3_skill_block → _select_few_shot_examples ({few_shot_block})",
        "note": "Up to 2 examples selected; Arabic examples prioritised for ar-language users.",
    },
    "step.contraindications": {
        "status": "USED",
        "injected_by": "compose_prompt → _build_l3_skill_block ({contraindication_block})",
        "note": "Injected as 'Important: ...' block when non-empty.",
    },
    "step.completion_criteria": {
        "status": "PARTIAL",
        "injected_by": "skill_executor_node → evaluate_completion_criteria (LLM path only)",
        "note": (
            "LLM evaluator reads the criterion text for _LLM_CRITERIA_SKILLS "
            "(post_crisis_check_in, cbt_thought_record, behavioral_activation, assertive_communication). "
            "For all other skills, a word-count heuristic is used and this field text is ignored."
        ),
    },
    # ---- Skill-level fields ----
    "skill.cultural_overrides": {
        "status": "USED",
        "injected_by": "compose_prompt (system role, SKILL-SPECIFIC CULTURAL CONTEXT block)",
        "note": (
            "All key-value pairs injected into the system prompt after global cultural rules, "
            "within a 200-word budget. Active on every turn where active_skill_id is set."
        ),
    },
    "skill.escalation_matrix.L1": {
        "status": "USED",
        "injected_by": "skill_executor_node",
        "note": "Read as the exit instruction when primary_intent=exit_skill.",
    },
    "skill.escalation_matrix.L2": {
        "status": "STORED_ONLY",
        "injected_by": None,
        "note": "Parsed and validated. Not evaluated at runtime in this version.",
    },
    "skill.escalation_matrix.L3": {
        "status": "STORED_ONLY",
        "injected_by": None,
        "note": "Parsed and validated. Not evaluated at runtime in this version.",
    },
    "skill.escalation_matrix.L4": {
        "status": "STORED_ONLY",
        "injected_by": None,
        "note": "Parsed and validated. Not evaluated at runtime in this version.",
    },
    "skill.evidence_base": {
        "status": "STORED_ONLY",
        "injected_by": None,
        "note": "Parsed and validated. Not used in any prompt or gate.",
    },
    "skill.skill_type": {
        "status": "STORED_ONLY",
        "injected_by": None,
        "note": "Parsed and validated. Not used in routing or prompt construction.",
    },
    "skill.self_evolution": {
        "status": "STORED_ONLY",
        "injected_by": None,
        "note": "Parsed and validated (enum: manual_only). Not evaluated at runtime.",
    },
}


def get_conformance_report() -> dict:
    """Return the schema conformance matrix as a JSON-serializable dict."""
    used = [k for k, v in SCHEMA_CONFORMANCE.items() if v["status"] == "USED"]
    partial = [k for k, v in SCHEMA_CONFORMANCE.items() if v["status"] == "PARTIAL"]
    stored_only = [k for k, v in SCHEMA_CONFORMANCE.items() if v["status"] == "STORED_ONLY"]
    return {
        "summary": {
            "used": len(used),
            "partial": len(partial),
            "stored_only": len(stored_only),
            "total": len(SCHEMA_CONFORMANCE),
        },
        "fields": SCHEMA_CONFORMANCE,
    }
