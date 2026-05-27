"""
Experiment 4.4 — 20 scenario definitions.

Each scenario is a dict with:
  id           : unique identifier
  description  : human-readable label for clinician review log
  skill_id     : target skill
  initial_step : first step_id for the scenario
  initial_state_overrides : dict merged into make_executor_state()
  turns        : list of turn specs (each dict: message_en, state_overrides, expected_rule, expect_advance)
  kpi_targets  : {"completion": bool, "rule_id": str | None}

Known limitations documented inline:
  - Rule 4 (user_stop_request in step_policy) is dead code; L1 is caught by check_escalation
    before evaluate_step_policy runs. Tests use check_escalation path directly.
  - Rule 6 (skill-specific boolean signals: mood_score, hopelessness, etc.) are not
    wired into the evaluate_step_policy signals dict. S13 tests this gap explicitly.
  - prior_exposure reflects cross-session usage only (techniques_used updated at
    end-of-session). Within a first session prior_exposure=0.
"""

# ── Completion scenarios (S01–S07): happy paths through each skill ─────────────

S01_CBT_HAPPY_PATH = {
    "id": "S01",
    "description": "CBT thought record — full 3-step completion",
    "skill_id": "cbt_thought_record",
    "initial_step": "identify_thought",
    "initial_state_overrides": {},
    "kpi_targets": {"completion": True, "rule_id": None},
}

S02_DBT_TIPP_HAPPY_PATH = {
    "id": "S02",
    "description": "DBT TIPP — full 4-step completion",
    "skill_id": "dbt_tipp",
    "initial_step": "temperature",
    "initial_state_overrides": {},
    "kpi_targets": {"completion": True, "rule_id": None},
}

S03_MI_HAPPY_PATH = {
    "id": "S03",
    "description": "MI readiness ruler — full 3-step completion",
    "skill_id": "mi_readiness_ruler",
    "initial_step": "importance_ruler",
    "initial_state_overrides": {},
    "kpi_targets": {"completion": True, "rule_id": None},
}

S04_BA_HAPPY_PATH = {
    "id": "S04",
    "description": "Behavioral activation — full 3-step completion",
    "skill_id": "behavioral_activation",
    "initial_step": "activity_audit",
    "initial_state_overrides": {},
    "kpi_targets": {"completion": True, "rule_id": None},
}

S05_SLEEP_HAPPY_PATH = {
    "id": "S05",
    "description": "Sleep hygiene — full 3-step completion",
    "skill_id": "sleep_hygiene",
    "initial_step": "assess_sleep",
    "initial_state_overrides": {},
    "kpi_targets": {"completion": True, "rule_id": None},
}

S06_GROUNDING_HAPPY_PATH = {
    "id": "S06",
    "description": "Grounding 5-4-3-2-1 — full 5-step completion",
    "skill_id": "grounding_5_4_3_2_1",
    "initial_step": "see_5",
    "initial_state_overrides": {},
    "kpi_targets": {"completion": True, "rule_id": None},
}

S07_MOOD_HAPPY_PATH = {
    "id": "S07",
    "description": "Mood check-in — full 2-step completion",
    "skill_id": "mood_check_in",
    "initial_step": "score_mood",
    "initial_state_overrides": {},
    "kpi_targets": {"completion": True, "rule_id": None},
}


# ── Rule accuracy scenarios (S08–S13) ──────────────────────────────────────────

S08_RULE1_EMOTIONAL_INTENSITY = {
    "id": "S08",
    "description": "R1: emotional_intensity > 7 → validate_only (CBT)",
    "skill_id": "cbt_thought_record",
    "initial_step": "explore_distortion",
    "initial_state_overrides": {
        "emotional_intensity": 9,
        "engagement": 7,
        "message_en": "I don't know... everything is my fault, it always has been and always will be.",
    },
    # Rule fires every turn (intensity stays high) — use a persistently distressed message.
    "_recurring_message": "I just keep thinking about it. I can't stop. It all feels too much.",
    "kpi_targets": {"completion": False, "rule_id": "validate_only"},
}

S09_RULE2_RESISTANCE_FOR_TURNS = {
    "id": "S09",
    "description": "R2: resistance > 6 for 3 turns → offer_skill_switch_or_break (CBT)",
    "skill_id": "cbt_thought_record",
    "initial_step": "explore_distortion",
    "initial_state_overrides": {
        "resistance_history": [7, 8],   # 2 prior turns above threshold
        "emotional_intensity": 4,
        "engagement": 5,
        "message_en": "I don't really see the point in this. I've tried this kind of thing before and it doesn't help.",
    },
    "_recurring_message": "I guess... but honestly I don't think anything is going to change for me.",
    # resistance_score must be >= 7 for the rule to fire; provided via fixture
    "kpi_targets": {"completion": False, "rule_id": "offer_skill_switch_or_break"},
    "_requires_resistance_score": 8,
}

S10_RULE3_ENGAGEMENT_FOR_TURNS = {
    "id": "S10",
    "description": "R3: engagement < 3 for 3 turns → check_in_micro (DBT TIPP)",
    "skill_id": "dbt_tipp",
    "initial_step": "paced_breathing",
    "initial_state_overrides": {
        "engagement_trajectory": [2, 2],    # 2 prior turns both < 3
        "engagement": 2,                    # current turn also < 3
        "emotional_intensity": 4,
        "message_en": "yeah",
    },
    "_recurring_message": "ok",
    "kpi_targets": {"completion": False, "rule_id": "check_in_micro"},
}

S11_RULE4_L1_EXIT = {
    "id": "S11",
    "description": "R4: L1 exit phrase → active_skill_id=None via check_escalation (BA)",
    "skill_id": "behavioral_activation",
    "initial_step": "activity_audit",
    "initial_state_overrides": {
        "message_en": "i am done with this",
        "emotional_intensity": 5,
        "engagement": 6,
    },
    # L1 is handled by check_escalation before evaluate_step_policy. The step_policy
    # user_stop_request rule is dead code — this tests the correct code path.
    "kpi_targets": {"completion": False, "rule_id": "exit_skill"},
}

S12_RULE5_PRIOR_EXPOSURE = {
    "id": "S12",
    "description": "R5: prior_exposure >= 3 → skip_psychoeducation (MI ruler)",
    "skill_id": "mi_readiness_ruler",
    "initial_step": "importance_ruler",
    "initial_state_overrides": {
        "therapeutic_profile": {
            "techniques_used": [
                "mi_readiness_ruler",
                "mi_readiness_ruler",
                "mi_readiness_ruler",
            ],
        },
        "emotional_intensity": 4,
        "engagement": 7,
        # User is returning to MI ruler — they know the exercise. Skip the scale explanation.
        "message_en": "I've been thinking about exercising more. I used to go every morning and I want to get back to it.",
    },
    "kpi_targets": {"completion": False, "rule_id": "skip_psychoeducation"},
}

S13_RULE6_SKILL_SPECIFIC_GAP = {
    "id": "S13",
    "description": "R6 (documented gap): mood_score <= 2 signal not wired — rule does not fire",
    "skill_id": "mood_check_in",
    "initial_step": "score_mood",
    "initial_state_overrides": {
        "emotional_intensity": 4,
        "engagement": 6,
        # mood_score is not in the evaluate_step_policy signals dict — rule is dead.
        # This scenario documents the known limitation.
    },
    "kpi_targets": {"completion": False, "rule_id": None},  # rule_id=None = gap documented
    "_known_gap": "mood_score not in signals dict; flag_for_review rule unreachable",
}


# ── Extended conversation scenarios (S14–S17) ───────────────────────────────────

S14_CBT_EXTENDED_WITH_R1 = {
    "id": "S14",
    "description": "CBT 15-turn: R1 fires once (turn 5), resolves, skill completes",
    "skill_id": "cbt_thought_record",
    "initial_step": "identify_thought",
    "initial_state_overrides": {},
    "kpi_targets": {"completion": True, "rule_id": None},
    "_extended_turns": 15,
    "_rule_fire_turn": 5,
    "_rule_fire_override": {"emotional_intensity": 9},
    "_rule_fire_recovery": {"emotional_intensity": 5},
}

S15_BA_EXTENDED_WITH_R2 = {
    "id": "S15",
    "description": "BA 20-turn: R2 fires turns 8-10 (resistance built up), resolves, completes",
    "skill_id": "behavioral_activation",
    "initial_step": "activity_audit",
    "initial_state_overrides": {},
    "kpi_targets": {"completion": True, "rule_id": None},
    "_extended_turns": 20,
}

S16_SLEEP_EXTENDED_MIXED = {
    "id": "S16",
    "description": "Sleep hygiene 18-turn: early R1, then steady engagement, full completion",
    "skill_id": "sleep_hygiene",
    "initial_step": "assess_sleep",
    "initial_state_overrides": {},
    "kpi_targets": {"completion": True, "rule_id": None},
    "_extended_turns": 18,
}

S17_DBT_EXTENDED_WITH_R3 = {
    "id": "S17",
    "description": "DBT TIPP 25-turn: R3 fires once mid-skill, resolves, completes all 4 steps",
    "skill_id": "dbt_tipp",
    "initial_step": "temperature",
    "initial_state_overrides": {},
    "kpi_targets": {"completion": True, "rule_id": None},
    "_extended_turns": 25,
}


# ── Enriched state influence scenarios (S18–S20) ────────────────────────────────

S18_CLINICAL_FLAGS_NO_BLOCK = {
    "id": "S18",
    "description": "X1 regression guard: clinical flags must not block CBT completion",
    "skill_id": "cbt_thought_record",
    "initial_step": "identify_thought",
    "initial_state_overrides": {
        "clinical_flags": ["trauma_indicator", "substance_use"],
        "new_clinical_flags_turn": ["substance_use"],   # new flag this turn
    },
    "kpi_targets": {"completion": True, "rule_id": None},
}

S19_PRIOR_EXPOSURE_ENRICHED = {
    "id": "S19",
    "description": "Enriched state: therapeutic_profile drives R5 skip on first turn",
    "skill_id": "mi_readiness_ruler",
    "initial_step": "importance_ruler",
    "initial_state_overrides": {
        "therapeutic_profile": {
            "techniques_used": [
                "mi_readiness_ruler",
                "mi_readiness_ruler",
                "mi_readiness_ruler",
            ],
        },
        # Returning user — they know the exercise, have a specific change in mind.
        "message_en": "I've been thinking about cutting down on my phone use before bed. I want to sleep better.",
    },
    "_recurring_message": "Maybe a 7 out of 10 for importance. I really do want this.",
    "kpi_targets": {"completion": False, "rule_id": "skip_psychoeducation"},
}

S20_ENGAGEMENT_TRAJECTORY_ENRICHED = {
    "id": "S20",
    "description": "Enriched state: engagement_trajectory [2,2] + current 2 fires R3",
    "skill_id": "grounding_5_4_3_2_1",
    "initial_step": "see_5",
    "initial_state_overrides": {
        "engagement_trajectory": [2, 2],
        "engagement": 2,
        "emotional_intensity": 4,
        "message_en": "ok",
    },
    "_recurring_message": "yeah",
    "kpi_targets": {"completion": False, "rule_id": "check_in_micro"},
}


ALL_SCENARIOS = [
    S01_CBT_HAPPY_PATH,
    S02_DBT_TIPP_HAPPY_PATH,
    S03_MI_HAPPY_PATH,
    S04_BA_HAPPY_PATH,
    S05_SLEEP_HAPPY_PATH,
    S06_GROUNDING_HAPPY_PATH,
    S07_MOOD_HAPPY_PATH,
    S08_RULE1_EMOTIONAL_INTENSITY,
    S09_RULE2_RESISTANCE_FOR_TURNS,
    S10_RULE3_ENGAGEMENT_FOR_TURNS,
    S11_RULE4_L1_EXIT,
    S12_RULE5_PRIOR_EXPOSURE,
    S13_RULE6_SKILL_SPECIFIC_GAP,
    S14_CBT_EXTENDED_WITH_R1,
    S15_BA_EXTENDED_WITH_R2,
    S16_SLEEP_EXTENDED_MIXED,
    S17_DBT_EXTENDED_WITH_R3,
    S18_CLINICAL_FLAGS_NO_BLOCK,
    S19_PRIOR_EXPOSURE_ENRICHED,
    S20_ENGAGEMENT_TRAJECTORY_ENRICHED,
]
