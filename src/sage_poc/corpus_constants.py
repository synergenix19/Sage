"""Shared constants for corpus and skill integrity checks.

Imported by scripts/audit_corpus.py and tests/test_corpus_integrity.py.
No side effects at import time — no model loads, no DB connections.
"""

# EN articles that intentionally have no AR pair this sprint.
# Update this dict when an article ships its AR pair and remove its entry.
DEFERRED_AR: dict[str, str] = {
    "therapy-001":   "lower priority; no paired skill; Tier 2 path",
    "trauma-001":    "requires clinical review — same gate as crisis content",
    "grounding-001": "covered by grounding_5_4_3_2_1 skill; KB pair low value",
    "breathing-001": "covered by box_breathing skill; KB pair low value",
    "cbt-001":       "covered by psychoed skills and cbt_thought_record skill",
    "cbt-002":       "covered by psychoed skills and cbt_thought_record skill",
}

# These four never get AR pairs without dual-clinician sign-off.
CRISIS_GATE: frozenset[str] = frozenset({
    "crisis-001", "crisis-002", "crisis-003", "crisis-004",
})

# Any of these strings in an AR article's JSON is a publication blocker.
PLACEHOLDER_MARKERS: tuple[str, ...] = (
    "[CONTENT AUTHOR",
    "[CLINICAL",
    "[same as EN",
    "TBD",
    "TODO",
)

# Minimum required step_policy signals for every skill.
#
# v7 §9.2 lists: emotional_intensity, clarity, resistance, engagement, prior_exposure.
# user_stop_request is not in §9.2 but is required here as a safety signal (v7 rule #5:
# "I want to stop" → exit gracefully, no persuasion).
#
# clarity and prior_exposure (skip/efficiency logic) are NOT required by this check.
# That is a conscious decision: this check enforces the minimum safety floor; §9.2
# compliance including clarity and prior_exposure is verified in the clinical review phase.
# If you want CI to enforce the full §9.2 set, add them to this frozenset.
REQUIRED_POLICY_SIGNALS: frozenset[str] = frozenset({
    "emotional_intensity",  # high-distress interrupt — safety
    "resistance",           # resistance handling — clinical
    "engagement",           # disengagement check — clinical
    "user_stop_request",    # graceful exit, no persuasion — safety (v7 rule #5)
    # Intentionally excluded: "clarity", "prior_exposure" — see comment above
})

# Skills intentionally absent from CLINICAL_CLUSTERS, with reasons.
CLUSTER_EXCLUSIONS: dict[str, str] = {
    "post_crisis_check_in": (
        "activates via post_crisis_auto_select in skill_select_node, "
        "not via semantic matching — adding it to a cluster would mislead "
        "the calibration gap calculation"
    ),
    "psychotic_referral": (
        "single-step referral skill activated via psychotic_disclosure clinical flag, "
        "not via keyword or semantic matching — cluster assignment would create spurious "
        "routing paths"
    ),
}

# Skills exempt from the structural floor checks in test_skill_structural_floors.
#
# These are non-standard single-purpose skills that do not follow the
# multi-step structured-therapy template (≥2 steps, full step_policy,
# complete escalation matrix, non-empty semantic_description).
# They are activated by a dedicated routing path (not keyword/semantic) and
# their clinical parameters are intentionally minimal pending full sign-off.
#
# Add a skill here only when it has a non-standard single-purpose architecture
# that makes the structural floor checks inappropriate. Include the reason.
STRUCTURAL_FLOOR_EXEMPTIONS: dict[str, str] = {
    "psychotic_referral": (
        "single-step clinical referral skill, inactive pending sign-off; "
        "activated via psychotic_disclosure flag not by multi-step skill routing; "
        "semantic_description and target_presentations intentionally empty"
    ),
}

# Skills exempt from the ≥20 target_presentations floor check.
#
# The floor exists to ensure enough keyword triggers for Tier 1 routing.
# Skills that do NOT route via keyword matching (state-driven auto-select) have
# no routing use for target_presentations — their list is documentation only.
# Padding those lists to satisfy the floor creates spurious keyword routes that
# activate the wrong skill for non-crisis users (skill_select_node line 108
# iterates target_presentations for ALL skills when crisis_state != "monitoring").
#
# Add a skill here only when it is activated by a mechanism other than
# keyword/semantic matching. Include the reason.
PRESENTATIONS_FLOOR_EXEMPTIONS: dict[str, str] = {
    "post_crisis_check_in": (
        "activated via post_crisis_auto_select when crisis_state == 'monitoring' "
        "(skill_select_node line 89) — excluded from keyword and semantic matching "
        "via KEYWORD_SEMANTIC_SKIP; target_presentations are documentation only"
    ),
}

# Skills that must never be reached via keyword or semantic matching.
# Each entry is activated by a dedicated routing path that runs BEFORE the matching loops.
#
# This constant is imported by skill_select_node to exclude these skills from:
#   (a) the Tier 1 keyword loop
#   (b) the BGE-M3 semantic embedding matrix
#
# Correctness audit 2026-05-31 confirmed that omitting a skill from this set while
# leaving it in SKILL_REGISTRY causes its target_presentations to trigger the keyword
# loop for non-qualifying sessions. Enforcement belongs in code, not in comments:
# tests/test_routing.py::test_post_crisis_phrases_not_reachable_outside_monitoring
# asserts the routing invariant directly.
KEYWORD_SEMANTIC_SKIP: frozenset[str] = frozenset({
    "post_crisis_check_in",  # activated via post_crisis_auto_select (crisis_state=='monitoring')
    "psychotic_referral",    # activated via psychotic_disclosure clinical flag; not keyword/semantic routed
})
