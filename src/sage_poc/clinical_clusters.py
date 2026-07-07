"""Canonical CLINICAL_CLUSTERS map.

Imported by scripts/calibrate_threshold.py, scripts/audit_corpus.py,
and tests/test_corpus_integrity.py.

No side effects at import time. No model imports. No DB connections.

Clusters group skills that are semantically adjacent BY DESIGN because they share
clinical vocabulary. Within-cluster overlap is expected and exempt from the
calibration gap gate. Disambiguation within a cluster is handled by keyword rules
(Tier 1) in skill_select_node, not by embeddings.
"""

CLINICAL_CLUSTERS: dict[str, list[str]] = {
    "somatic_distress": [
        "grounding_5_4_3_2_1",
        "box_breathing",
        "dbt_tipp",
        "progressive_muscle_relaxation",
        "mindfulness_body_scan",
        "mindfulness_meditation",
    ],
    "sleep": ["sleep_hygiene"],
    # cognitive_restructuring is adjacent to cbt_thought_record by design.
    # Disambiguation: prefer cognitive_restructuring for first-time users;
    # cbt_thought_record for structured or experienced CBT work.
    "ruminative_anxiety": [
        "worry_time",
        "cbt_thought_record",
        "cognitive_restructuring",
    ],
    "mood_engagement": ["mood_check_in", "behavioral_activation"],
    # Deliberately split into single-skill clusters (conservative default).
    # A shared cluster grants argmax routing-authority below SEMANTIC_THRESHOLD.
    # MI and STOP occupy different vocabulary domains (ambivalence vs impulse control)
    # and the pairing lacked clinical affirmation. Single-skill clusters disable
    # argmax for these two skills and fall back to the absolute threshold.
    # To re-pair: get explicit clinical rationale and restore the combined cluster.
    "impulse_pause": ["stop_technique"],
    "psychoeducation": [
        "psychoed_anxiety",
        "psychoed_depression",
        "psychoed_stress",
    ],
    # interpersonal_effectiveness is adjacent to assertive_communication by design.
    # Disambiguation: prefer interpersonal_effectiveness for relationship navigation;
    # assertive_communication for expressing a specific need or boundary.
    "values_communication": [
        "values_clarification",
        "assertive_communication",
        "interpersonal_effectiveness",
    ],
    "self_compassion": ["self_compassion_break"],
    "visualization": ["safe_place_visualization"],
    # financial_anxiety uses Gulf-specific vocabulary (kafala, remittance, provider role)
    # semantically distinct from the ruminative_anxiety cluster.
    # If calibration gap < 0.03, sharpen semantic_description further — do not widen cluster.
    "financial_stress": ["financial_anxiety"],
    # Cluster name intentionally differs from skill_id to avoid confusion.
    "grief_and_loss": ["grief_loss"],
    # PST is semantically adjacent to worry_time (both involve practical problems) but
    # distinct: PST is for real, actionable problems with options; worry_time contains
    # and sorts hypothetical/rumination-driven worry. Keyword tier handles disambiguation.
    "structured_problem_solving": ["problem_solving_therapy"],
    # ACT is designed for multi-problem presentations and CBT-experienced users.
    # Adjacent to ruminative_anxiety (thought work) and values_communication (values compass)
    # but must remain distinct from both — see semantic_description calibration note in spec.
    "psychological_flexibility": ["act_psychological_flexibility"],
    # post_crisis_check_in is excluded — see corpus_constants.CLUSTER_EXCLUSIONS.
}
