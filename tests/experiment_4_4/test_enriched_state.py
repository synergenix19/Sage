# tests/experiment_4_4/test_enriched_state.py
#
# Experiment 4.4 — Enriched state influence on executor behavior
# Scenarios S18, S19, S20.
#
# These tests verify that fields from the enriched SageState actually
# reach evaluate_step_policy and alter outcomes:
#   S18 — clinical_flags must NOT block skill completion (X1 regression guard)
#   S19 — therapeutic_profile.techniques_used drives R5 skip_psychoeducation
#   S20 — engagement_trajectory [2,2] + current engagement=2 fires R3
#
# Observable behavior from skill_executor_node:
#   R5 (skip_psychoeducation) on importance_ruler → active_step_id stays "importance_ruler"
#     vs. normal advance → active_step_id = "confidence_ruler"
#   R3 (check_in_micro) on see_5 → active_step_id stays "see_5"
#     vs. normal advance → active_step_id = "touch_4"

import pytest
from unittest.mock import patch, AsyncMock

from sage_poc.nodes.skill_executor import evaluate_step_policy, skill_executor_node
from sage_poc.skills.schema import load_skill

from .conftest import make_executor_state
from .test_completion import _run_to_completion


# ── S18: X1 regression guard ──────────────────────────────────────────────────

class TestClinicalFlagsDoNotBlockCompletion:
    """clinical_flags must not block executor advancement or skill completion.

    X1 was the bug where the prompt injected flag context that caused the LLM
    to refuse to advance steps. The executor itself must be indifferent to
    clinical_flags — they are advisory context for Node 7 (freeflow_respond),
    not a gate in Node 5 (skill_executor).
    """

    async def test_clinical_flags_do_not_prevent_step_advance(self):
        """Single-turn: clinical flags present → step still advances normally."""
        state = make_executor_state(
            skill_id="cbt_thought_record",
            step_id="identify_thought",
            clinical_flags=["trauma_indicator", "substance_use"],
            new_clinical_flags_turn=["substance_use"],
            emotional_intensity=5,
            engagement=7,
        )
        skill = load_skill("cbt_thought_record")
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=skill), \
             patch("sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
                   new=AsyncMock(return_value=None)):
            result = await skill_executor_node(state)

        assert result["active_skill_id"] == "cbt_thought_record", (
            "clinical_flags must not trigger skill exit"
        )
        assert result["active_step_id"] != "identify_thought" or result.get("skill_complete"), (
            "clinical_flags must not hold the step on identify_thought"
        )

    async def test_clinical_flags_do_not_block_full_completion(self):
        """Multi-turn: skill runs to completion even with clinical flags present throughout."""
        completed, turns = await _run_to_completion(
            skill_id="cbt_thought_record",
            first_step_id="identify_thought",
            initial_overrides={
                "clinical_flags": ["trauma_indicator", "substance_use"],
                "new_clinical_flags_turn": ["substance_use"],
            },
        )
        assert completed, (
            f"CBT must complete with clinical flags present "
            f"(completed={completed}, turns={turns})"
        )

    async def test_multiple_flags_do_not_block_ba_completion(self):
        """Behavioral activation also completes when several clinical flags are set."""
        completed, turns = await _run_to_completion(
            skill_id="behavioral_activation",
            first_step_id="activity_audit",
            initial_overrides={
                "clinical_flags": ["trauma_indicator", "substance_use", "hopelessness_indicator"],
                "new_clinical_flags_turn": [],
            },
        )
        assert completed, (
            f"BA must complete with multiple clinical flags present "
            f"(completed={completed}, turns={turns})"
        )

    async def test_new_flag_mid_skill_does_not_exit(self):
        """A brand-new flag arriving in new_clinical_flags_turn must not force an exit."""
        state = make_executor_state(
            skill_id="sleep_hygiene",
            step_id="assess_sleep",
            clinical_flags=[],
            new_clinical_flags_turn=["trauma_indicator"],  # new flag this turn
            emotional_intensity=5,
            engagement=7,
        )
        skill = load_skill("sleep_hygiene")
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=skill), \
             patch("sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
                   new=AsyncMock(return_value=None)):
            result = await skill_executor_node(state)

        assert result["active_skill_id"] == "sleep_hygiene", (
            "New clinical flag must not exit the skill"
        )


# ── S19: R5 prior_exposure via therapeutic_profile ────────────────────────────

class TestPriorExposureViaTherapeuticProfile:
    """therapeutic_profile.techniques_used count drives R5 skip_psychoeducation.

    prior_exposure is computed in skill_executor_node as:
        therapeutic_profile["techniques_used"].count(skill_id)
    This is cross-session — first-session prior_exposure is always 0.

    R5 fires on importance_ruler with next_step_id="importance_ruler" (stays).
    Normal advance (no R5) moves to confidence_ruler.
    So: with 3 prior exposures, step STAYS; without prior exposure, step ADVANCES.
    """

    def test_three_prior_exposures_fire_r5(self):
        """Unit: prior_exposure=3 → skip_psychoeducation action on importance_ruler."""
        skill = load_skill("mi_readiness_ruler")
        result = evaluate_step_policy(
            skill=skill,
            current_step_id="importance_ruler",
            emotional_intensity=4,
            engagement=7,
            prior_exposure=3,
        )
        assert result["action"] == "skip_psychoeducation", (
            "prior_exposure=3 must fire R5 on importance_ruler"
        )

    def test_fewer_than_three_exposures_do_not_fire_r5(self):
        """Unit: 0, 1, or 2 prior exposures → R5 must not fire."""
        skill = load_skill("mi_readiness_ruler")
        for count in (0, 1, 2):
            result = evaluate_step_policy(
                skill=skill,
                current_step_id="importance_ruler",
                emotional_intensity=4,
                engagement=7,
                prior_exposure=count,
            )
            assert result["action"] != "skip_psychoeducation", (
                f"prior_exposure={count} must NOT fire R5"
            )

    async def test_r5_via_node_holds_step_when_profile_has_three_uses(self):
        """Node path: with 3 prior uses, R5 fires and step stays at importance_ruler.

        Without prior exposure, the step would advance to confidence_ruler (criteria met).
        The difference is observable as active_step_id.
        """
        skill = load_skill("mi_readiness_ruler")

        # State with 3 prior uses → R5 fires → step must stay
        state_with = make_executor_state(
            skill_id="mi_readiness_ruler",
            step_id="importance_ruler",
            therapeutic_profile={
                "techniques_used": [
                    "mi_readiness_ruler",
                    "mi_readiness_ruler",
                    "mi_readiness_ruler",
                ],
            },
            emotional_intensity=4,
            engagement=7,
        )
        # State with 0 prior uses → no R5 → step advances
        state_without = make_executor_state(
            skill_id="mi_readiness_ruler",
            step_id="importance_ruler",
            therapeutic_profile={},
            emotional_intensity=4,
            engagement=7,
        )

        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=skill), \
             patch("sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
                   new=AsyncMock(return_value=None)):
            result_with = await skill_executor_node(state_with)
            result_without = await skill_executor_node(state_without)

        assert result_with["active_step_id"] == "importance_ruler", (
            "R5 must hold step at importance_ruler when prior_exposure=3"
        )
        assert result_without["active_step_id"] == "confidence_ruler", (
            "Without R5, step must advance to confidence_ruler"
        )

    def test_r5_is_step_specific_to_importance_ruler(self):
        """R5 is declared on importance_ruler only; other mi steps must not fire it."""
        skill = load_skill("mi_readiness_ruler")
        for step_id in ("confidence_ruler", "next_step"):
            result = evaluate_step_policy(
                skill=skill,
                current_step_id=step_id,
                emotional_intensity=4,
                engagement=7,
                prior_exposure=5,
            )
            assert result["action"] != "skip_psychoeducation", (
                f"R5 must be step-specific; fired unexpectedly on {step_id}"
            )

    async def test_other_skill_ids_in_techniques_used_do_not_count(self):
        """Only the current skill's entries in techniques_used count toward prior_exposure."""
        skill = load_skill("mi_readiness_ruler")
        # 3 CBT uses + 1 DBT use — but 0 MI uses, so R5 must not fire
        state = make_executor_state(
            skill_id="mi_readiness_ruler",
            step_id="importance_ruler",
            therapeutic_profile={
                "techniques_used": [
                    "cbt_thought_record",
                    "cbt_thought_record",
                    "cbt_thought_record",
                    "dbt_tipp",
                ],
            },
            emotional_intensity=4,
            engagement=7,
        )
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=skill), \
             patch("sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
                   new=AsyncMock(return_value=None)):
            result = await skill_executor_node(state)

        # Other skills don't count → no R5 → step advances (to confidence_ruler)
        assert result["active_step_id"] == "confidence_ruler", (
            "Other skills in techniques_used must not count toward prior_exposure; "
            "step must advance normally"
        )


# ── S20: engagement_trajectory fires R3 with enriched state ───────────────────

class TestEngagementTrajectoryFiresR3:
    """engagement_trajectory [2,2] + current engagement=2 must fire R3 check_in_micro.

    This is the enriched-state integration test: the trajectory list arrives from
    SageState (maintained by safety_check_node) and must be forwarded to
    evaluate_step_policy via skill_executor_node.

    R3 fires on see_5 with next_step_id="see_5" (stays).
    Normal advance (no R3) moves to touch_4.
    So: with full trajectory + low engagement, step STAYS; without, step ADVANCES.
    """

    def test_r3_fires_with_full_trajectory(self):
        """Unit: trajectory=[2,2] + engagement=2 → check_in_micro action."""
        skill = load_skill("grounding_5_4_3_2_1")
        result = evaluate_step_policy(
            skill=skill,
            current_step_id="see_5",
            emotional_intensity=4,
            engagement=2,
            engagement_trajectory=[2, 2],
        )
        assert result["action"] == "check_in_micro", (
            "R3 must fire when engagement_trajectory=[2,2] and current engagement=2"
        )

    def test_r3_does_not_fire_with_empty_trajectory(self):
        """Unit: no prior turns → R3 must not fire even with low engagement."""
        skill = load_skill("grounding_5_4_3_2_1")
        result = evaluate_step_policy(
            skill=skill,
            current_step_id="see_5",
            emotional_intensity=4,
            engagement=2,
            engagement_trajectory=[],
        )
        assert result["action"] != "check_in_micro", (
            "R3 must not fire with empty trajectory (only 1 turn, for_turns=3 not met)"
        )

    def test_r3_does_not_fire_with_one_prior_low_turn(self):
        """Unit: trajectory=[2] + engagement=2 = 2 consecutive turns → not enough for for_turns=3."""
        skill = load_skill("grounding_5_4_3_2_1")
        result = evaluate_step_policy(
            skill=skill,
            current_step_id="see_5",
            emotional_intensity=4,
            engagement=2,
            engagement_trajectory=[2],
        )
        assert result["action"] != "check_in_micro", (
            "R3 must not fire with only 1 prior low turn"
        )

    async def test_trajectory_state_field_reaches_evaluate_step_policy(self):
        """Node path: engagement_trajectory in SageState is forwarded (not silently dropped).

        With trajectory=[2,2] + engagement=2: R3 fires → step stays at see_5.
        With trajectory=[] + engagement=2: no R3 → criteria met → step advances to touch_4.
        """
        skill = load_skill("grounding_5_4_3_2_1")

        state_with_trajectory = make_executor_state(
            skill_id="grounding_5_4_3_2_1",
            step_id="see_5",
            engagement_trajectory=[2, 2],
            engagement=2,
            emotional_intensity=4,
        )
        state_without_trajectory = make_executor_state(
            skill_id="grounding_5_4_3_2_1",
            step_id="see_5",
            engagement_trajectory=[],
            engagement=2,
            emotional_intensity=4,
        )

        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=skill), \
             patch("sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
                   new=AsyncMock(return_value=None)):
            result_with = await skill_executor_node(state_with_trajectory)
            result_without = await skill_executor_node(state_without_trajectory)

        assert result_with["active_step_id"] == "see_5", (
            "With full trajectory, R3 must hold step at see_5"
        )
        assert result_without["active_step_id"] == "touch_4", (
            "Without trajectory, step must advance to touch_4"
        )

    async def test_r3_fires_via_node_with_enriched_state_dbt(self):
        """Node path: same R3 behavior on dbt_tipp paced_breathing step."""
        skill = load_skill("dbt_tipp")
        # Get the second step (paced_breathing) and the one after it
        steps = [s.step_id for s in skill.steps]
        paced_idx = steps.index("paced_breathing")
        next_after_paced = steps[paced_idx + 1] if paced_idx + 1 < len(steps) else None

        state_with = make_executor_state(
            skill_id="dbt_tipp",
            step_id="paced_breathing",
            engagement_trajectory=[2, 2],
            engagement=2,
            emotional_intensity=4,
        )
        state_without = make_executor_state(
            skill_id="dbt_tipp",
            step_id="paced_breathing",
            engagement_trajectory=[],
            engagement=2,
            emotional_intensity=4,
        )

        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=skill), \
             patch("sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
                   new=AsyncMock(return_value=None)):
            result_with = await skill_executor_node(state_with)
            result_without = await skill_executor_node(state_without)

        assert result_with["active_step_id"] == "paced_breathing", (
            "R3 must hold step at paced_breathing when trajectory=[2,2] + engagement=2"
        )
        assert result_without["active_step_id"] == next_after_paced, (
            "Without R3, step must advance"
        )
