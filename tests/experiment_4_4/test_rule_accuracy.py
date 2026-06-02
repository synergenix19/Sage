# tests/experiment_4_4/test_rule_accuracy.py
#
# Experiment 4.4 — Rule accuracy KPI
# Tests all 6 step_policy rule types from v7 §9.2.
# All tests are deterministic (no LLM calls).
#
# Rule summary:
#   R1: emotional_intensity > 7 → validate_only
#   R2: resistance > 6, for_turns=3 → offer_skill_switch_or_break (Phase 2 signal)
#   R3: engagement < 3, for_turns=3 → check_in_micro (engagement_trajectory)
#   R4: user_stop_request → L1 exit via check_escalation (not via step_policy)
#   R5: prior_exposure >= 3 → skip_psychoeducation (from therapeutic_profile)
#   R6: skill-specific boolean signals — documented gap (not in signals dict)

import pytest
from unittest.mock import patch, AsyncMock

from sage_poc.nodes.skill_executor import (
    _condition_met,
    check_escalation,
    evaluate_step_policy,
    skill_executor_node,
)
from sage_poc.skills.schema import StepPolicyCondition

from .conftest import make_executor_state


# ── R1: emotional_intensity > 7 → validate_only ───────────────────────────────

class TestRule1EmotionalIntensity:
    """R1 fires on the current turn's emotional_intensity alone (no history needed)."""

    @pytest.mark.parametrize("intensity,should_fire", [
        (7, False),   # boundary: exactly 7 does not fire (rule is > 7)
        (8, True),
        (9, True),
        (10, True),
        (5, False),
    ])
    def test_r1_boundary_values(self, cbt, intensity, should_fire):
        result = evaluate_step_policy(
            skill=cbt,
            current_step_id="explore_distortion",
            emotional_intensity=intensity,
            engagement=7,
        )
        if should_fire:
            assert result["action"] == "validate_only", (
                f"R1 must fire when emotional_intensity={intensity} > 7"
            )
        else:
            assert result["action"] != "validate_only", (
                f"R1 must not fire when emotional_intensity={intensity} <= 7"
            )

    def test_r1_returns_correct_instruction(self, cbt):
        result = evaluate_step_policy(
            skill=cbt,
            current_step_id="identify_thought",
            emotional_intensity=9,
            engagement=7,
        )
        assert result["action"] == "validate_only"
        assert result["next_step_id"] == "identify_thought"  # stays on current step
        assert result["skill_complete"] is False

    def test_r1_fires_on_any_step(self, dbt_tipp):
        """R1 step=ANY must fire regardless of which step is active."""
        for step_id in ["temperature", "intense_exercise", "paced_breathing", "check_in"]:
            result = evaluate_step_policy(
                skill=dbt_tipp,
                current_step_id=step_id,
                emotional_intensity=9,
                engagement=7,
            )
            assert result["action"] == "validate_only", (
                f"R1 must fire on step '{step_id}' (step=ANY)"
            )


# ── R2: resistance > 6, for_turns=3 → offer_skill_switch_or_break ─────────────

class TestRule2ResistanceForTurns:
    """R2 is a Phase 2 signal — requires resistance_score from LLM AND 2 prior turns."""

    def test_r2_requires_sufficient_prior_history(self, cbt):
        """Only 1 prior turn — rule must not fire (needs 2 prior + current = 3)."""
        result = evaluate_step_policy(
            skill=cbt,
            current_step_id="identify_thought",
            emotional_intensity=4,
            engagement=6,
            resistance_history=[8],    # only 1 prior turn
            resistance_score=8,
        )
        assert result["action"] != "offer_skill_switch_or_break", (
            "R2 must not fire with only 1 prior turn (for_turns=3 needs 2 prior)"
        )

    def test_r2_fires_with_full_history(self, cbt):
        """2 prior turns > 6 + current > 6 → rule fires."""
        result = evaluate_step_policy(
            skill=cbt,
            current_step_id="identify_thought",
            emotional_intensity=4,
            engagement=6,
            resistance_history=[7, 8],    # 2 prior turns above threshold
            resistance_score=8,
        )
        assert result["action"] == "offer_skill_switch_or_break", (
            "R2 must fire when 2 prior + 1 current all have resistance > 6"
        )

    def test_r2_does_not_fire_when_one_prior_below_threshold(self, cbt):
        """One prior turn below threshold breaks the streak."""
        result = evaluate_step_policy(
            skill=cbt,
            current_step_id="identify_thought",
            emotional_intensity=4,
            engagement=6,
            resistance_history=[5, 8],    # prior turn 1 was low
            resistance_score=8,
        )
        assert result["action"] != "offer_skill_switch_or_break", (
            "R2 must not fire when streak is broken (prior turn had resistance <= 6)"
        )

    def test_r2_skipped_in_phase1(self, cbt):
        """Phase 1 (resistance_score=None) must never evaluate resistance rules."""
        result = evaluate_step_policy(
            skill=cbt,
            current_step_id="identify_thought",
            emotional_intensity=4,
            engagement=6,
            resistance_history=[7, 8],
            resistance_score=None,  # Phase 1 mode
        )
        assert result["action"] != "offer_skill_switch_or_break", (
            "R2 must not fire in Phase 1 (resistance_score=None)"
        )

    async def test_r2_fires_through_node_with_real_phase2(self):
        """Full skill_executor_node path: Phase 2 LLM score of 8 fires R2 after history,
        but the precedence resolver restores Phase 1 advancement because criteria are met.
        Clinical rule: criteria-met advancement beats resistance holds.
        """
        state = make_executor_state(
            skill_id="cbt_thought_record",
            step_id="identify_thought",
            resistance_history=[7, 8],
            emotional_intensity=4,
            engagement=6,
        )
        with patch(
            "sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
            new=AsyncMock(return_value=8),
        ):
            from sage_poc.skills.schema import load_skill
            with patch("sage_poc.nodes.skill_executor.load_skill", return_value=load_skill("cbt_thought_record")):
                result = await skill_executor_node(state)
        assert result["step_instruction"] is not None
        # Phase 1 clears criteria (default message is 12 words, passes word-count).
        # Precedence resolver discards Phase 2's R2 hold — step must advance, not offer break.
        assert result["active_step_id"] == "explore_distortion", (
            "Criteria-met advancement must beat resistance hold: step should advance to explore_distortion"
        )
        assert "offer" not in result["step_instruction"].lower() and "break" not in result["step_instruction"].lower(), (
            "R2 offer instruction must not appear when Phase 1 cleared criteria"
        )

    async def test_r2_holds_when_criteria_not_met(self):
        """R2 fires and holds the step when Phase 1 cannot clear criteria (single-word message)."""
        state = make_executor_state(
            skill_id="cbt_thought_record",
            step_id="identify_thought",
            message_en="no",  # 1 word — word-count fails; LLM will return False for cbt skill
            resistance_history=[7, 8],
            emotional_intensity=4,
            engagement=6,
        )
        with patch(
            "sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
            new=AsyncMock(return_value=8),
        ):
            with patch(
                "sage_poc.nodes.skill_executor.evaluate_completion_criteria",
                new=AsyncMock(return_value=False),
            ):
                from sage_poc.skills.schema import load_skill
                with patch("sage_poc.nodes.skill_executor.load_skill", return_value=load_skill("cbt_thought_record")):
                    result = await skill_executor_node(state)
        assert result["active_step_id"] == "identify_thought", (
            "R2 must hold the step when criteria are not met"
        )
        assert "offer" in result["step_instruction"].lower() or "break" in result["step_instruction"].lower() or "switch" in result["step_instruction"].lower(), (
            "R2 instruction must mention offering a break or switch when criteria are not met"
        )


# ── R3: engagement < 3, for_turns=3 → check_in_micro ─────────────────────────

class TestRule3EngagementForTurns:
    """R3 uses engagement_trajectory (4-turn rolling window, one-turn lagged)."""

    def test_r3_does_not_fire_without_history(self, cbt):
        """Single low-engagement turn must not fire (for_turns=3 requires history)."""
        result = evaluate_step_policy(
            skill=cbt,
            current_step_id="explore_distortion",
            emotional_intensity=4,
            engagement=2,
            engagement_trajectory=[],
        )
        assert result["action"] != "check_in_micro", (
            "R3 must not fire on a single low-engagement turn"
        )

    def test_r3_does_not_fire_with_only_one_prior_turn(self, cbt):
        """1 prior turn + current = 2 turns; for_turns=3 needs 3."""
        result = evaluate_step_policy(
            skill=cbt,
            current_step_id="explore_distortion",
            emotional_intensity=4,
            engagement=2,
            engagement_trajectory=[2],   # only 1 prior turn
        )
        assert result["action"] != "check_in_micro"

    def test_r3_fires_with_two_prior_and_current_low(self, cbt):
        """2 prior low turns + current low → fires."""
        result = evaluate_step_policy(
            skill=cbt,
            current_step_id="explore_distortion",
            emotional_intensity=4,
            engagement=2,
            engagement_trajectory=[2, 2],
        )
        assert result["action"] == "check_in_micro", (
            "R3 must fire when engagement_trajectory[-2:] + [current] all < 3"
        )

    def test_r3_does_not_fire_if_one_prior_above_threshold(self, cbt):
        """If one prior turn had engagement >= 3, streak is broken."""
        result = evaluate_step_policy(
            skill=cbt,
            current_step_id="explore_distortion",
            emotional_intensity=4,
            engagement=2,
            engagement_trajectory=[4, 2],   # prior turn 1 was not low
        )
        assert result["action"] != "check_in_micro", (
            "R3 must not fire when one prior turn had engagement >= 3"
        )

    def test_r3_boundary_value_exactly_3(self, cbt):
        """engagement=3 is NOT < 3 — rule must not fire."""
        result = evaluate_step_policy(
            skill=cbt,
            current_step_id="explore_distortion",
            emotional_intensity=4,
            engagement=3,
            engagement_trajectory=[2, 2],
        )
        assert result["action"] != "check_in_micro", (
            "engagement=3 must not fire R3 (rule is engagement < 3, not <= 3)"
        )

    def test_r3_fires_on_all_target_skills(self, dbt_tipp, mi, ba, sleep, grounding, mood):
        """All 7 target skills have R3; verify it fires for each."""
        for skill in [dbt_tipp, mi, ba, sleep, grounding, mood]:
            first_step = skill.steps[0].step_id
            result = evaluate_step_policy(
                skill=skill,
                current_step_id=first_step,
                emotional_intensity=4,
                engagement=2,
                engagement_trajectory=[2, 2],
            )
            assert result["action"] == "check_in_micro", (
                f"R3 must fire for skill '{skill.skill_id}' step '{first_step}'"
            )


# ── R4: user_stop_request → L1 exit via check_escalation ─────────────────────

class TestRule4L1Exit:
    """R4 behavior is correct via check_escalation (not evaluate_step_policy).
    The user_stop_request rule in step_policy JSON is dead code — L1 is caught
    before evaluate_step_policy runs. These tests verify the correct code path."""

    def test_l1_fires_on_canonical_exit_phrases(self):
        """Standard L1 phrases must trigger l1 escalation."""
        phrases = [
            "i am done with this",
            "i'm done",
            "can we talk about something else",
            "let's move on",
            "i don't want to do this anymore",
        ]
        for phrase in phrases:
            l1, _ = check_escalation(message_en=phrase, new_clinical_flags_turn=[])
            assert l1 is not None, f"L1 must fire for: '{phrase}'"
            assert l1["action"] == "exit_skill"

    async def test_l1_exits_skill_in_node(self, no_resistance):
        """skill_executor_node must return active_skill_id=None on L1."""
        state = make_executor_state(
            skill_id="behavioral_activation",
            step_id="activity_audit",
            message_en="i am done with this",
        )
        from sage_poc.nodes.skill_executor import skill_executor_node as sen
        from sage_poc.skills.schema import load_skill
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=load_skill("behavioral_activation")):
            result = await sen(state)
        assert result["active_skill_id"] is None
        assert result["escalation_triggered"]["level"] == "L1"

    def test_l1_does_not_fire_on_non_exit_context(self):
        """Phrases that mention 'stop' in a non-exit context must not trigger L1."""
        non_exit = [
            "I can't stop thinking about it",
            "I want to quit smoking",
            "I need to leave my house eventually",
        ]
        for phrase in non_exit:
            l1, _ = check_escalation(message_en=phrase, new_clinical_flags_turn=[])
            assert l1 is None, f"L1 must NOT fire for: '{phrase}'"

    def test_step_policy_user_stop_request_rule_is_not_evaluated(self, cbt):
        """Verify that user_stop_request is not in the evaluate_step_policy signals dict.
        The rule exists in skill JSON but is handled at check_escalation level."""
        # evaluate_step_policy with a neutral message should NOT fire the rule
        result = evaluate_step_policy(
            skill=cbt,
            current_step_id="identify_thought",
            emotional_intensity=5,
            engagement=7,
            message_en="I want to stop thinking about this",  # contains "stop" but not an L1 phrase
        )
        # The step_policy user_stop_request rule requires the signal to be True,
        # but it's never injected — so the rule can't fire via evaluate_step_policy.
        assert result["action"] not in ("exit_warm_closing",), (
            "user_stop_request rule must not fire via evaluate_step_policy — "
            "L1 is handled by check_escalation at node level"
        )


# ── R5: prior_exposure >= 3 → skip_psychoeducation ───────────────────────────

class TestRule5PriorExposure:
    """R5 uses prior_exposure computed from therapeutic_profile.techniques_used."""

    def test_r5_does_not_fire_with_no_prior_history(self, mi):
        result = evaluate_step_policy(
            skill=mi,
            current_step_id="importance_ruler",
            emotional_intensity=4,
            engagement=7,
            prior_exposure=0,
        )
        assert result["action"] != "skip_psychoeducation", (
            "R5 must not fire when prior_exposure=0"
        )

    @pytest.mark.parametrize("count", [1, 2])
    def test_r5_does_not_fire_below_threshold(self, mi, count):
        result = evaluate_step_policy(
            skill=mi,
            current_step_id="importance_ruler",
            emotional_intensity=4,
            engagement=7,
            prior_exposure=count,
        )
        assert result["action"] != "skip_psychoeducation", (
            f"R5 must not fire when prior_exposure={count} < 3"
        )

    @pytest.mark.parametrize("count", [3, 4, 5])
    def test_r5_fires_at_threshold(self, mi, count):
        result = evaluate_step_policy(
            skill=mi,
            current_step_id="importance_ruler",
            emotional_intensity=4,
            engagement=7,
            prior_exposure=count,
        )
        assert result["action"] == "skip_psychoeducation", (
            f"R5 must fire when prior_exposure={count} >= 3"
        )

    def test_r5_only_fires_on_importance_ruler_step(self, mi):
        """R5 has step='importance_ruler' — must not fire on other steps."""
        for step_id in ["confidence_ruler", "next_step"]:
            result = evaluate_step_policy(
                skill=mi,
                current_step_id=step_id,
                emotional_intensity=4,
                engagement=7,
                prior_exposure=5,   # well above threshold
            )
            assert result["action"] != "skip_psychoeducation", (
                f"R5 must not fire on step '{step_id}' (rule is step-specific)"
            )

    async def test_r5_fires_through_node_via_therapeutic_profile(self, no_resistance):
        """skill_executor_node path: techniques_used.count(skill_id) >= 3 fires R5."""
        state = make_executor_state(
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
        from sage_poc.skills.schema import load_skill
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=load_skill("mi_readiness_ruler")):
            result = await skill_executor_node(state)
        assert "skip" in result["step_instruction"].lower() or "already" in result["step_instruction"].lower() or "familiar" in result["step_instruction"].lower(), (
            "R5 instruction must indicate the psychoeducation step is being skipped"
        )


# ── R6: skill-specific boolean signals (documented gap) ───────────────────────

class TestRule6SkillSpecificGap:
    """R6 skill-specific boolean signals (mood_score, hopelessness, dissociation_signal,
    physical_contraindication_disclosed, etc.) are not in the evaluate_step_policy
    signals dict. These rules are currently unreachable via the executor.

    This test class documents the gap explicitly so it appears in the CI record."""

    def test_mood_score_signal_not_in_evaluate_step_policy(self, mood):
        """mood_score <= 2 rule in mood_check_in.json cannot fire — signal not wired."""
        result = evaluate_step_policy(
            skill=mood,
            current_step_id="score_mood",
            emotional_intensity=2,
            engagement=6,
            # mood_score is absent from signals dict — rule is dead code
        )
        # The rule exists but can't fire. Verify the result is not the rule action.
        assert result["action"] != "flag_for_review", (
            "mood_score rule must not fire (signal not wired) — "
            "this test documents a known R6 gap, not an expected pass"
        )

    def test_hopelessness_signal_not_in_evaluate_step_policy(self, ba):
        """hopelessness > 7 rule in behavioral_activation.json cannot fire."""
        result = evaluate_step_policy(
            skill=ba,
            current_step_id="identify_small_step",
            emotional_intensity=9,   # high distress, but not hopelessness signal
            engagement=6,
        )
        # R1 (emotional_intensity > 7) fires instead — hopelessness rule is dead.
        assert result["action"] == "validate_only", (
            "R1 should fire (emotional_intensity=9), not the hopelessness rule"
        )
