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
}
