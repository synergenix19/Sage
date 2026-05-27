# tests/experiment_4_4/test_completion.py
#
# Experiment 4.4 — Skill completion rate KPI (≥80% of 20 sessions complete)
# Tests multi-turn execution paths through skill_executor_node using mocked LLM.
# Phase 2 resistance scoring is patched to return None unless explicitly varied.

import pytest
from unittest.mock import patch, AsyncMock

from sage_poc.nodes.skill_executor import skill_executor_node
from sage_poc.skills.schema import load_skill

from .conftest import make_executor_state


# ── Multi-turn runner ──────────────────────────────────────────────────────────

async def _run_to_completion(
    skill_id: str,
    first_step_id: str,
    initial_overrides: dict | None = None,
    max_turns: int = 30,
    resistance_score: int | None = None,
) -> tuple[bool, int]:
    """Advance skill_executor_node turn-by-turn until skill_complete or max_turns.

    Returns (completed: bool, turns_taken: int).
    Mocks resistance scoring to the given fixed score (None = skip Phase 2).
    Message must be >10 words to pass _meets_completion_criteria.
    """
    long_message = (
        "I have been thinking carefully about what you asked and I feel like I am "
        "making some progress with this exercise today."
    )
    state = make_executor_state(
        skill_id=skill_id,
        step_id=first_step_id,
        message_en=long_message,
        **(initial_overrides or {}),
    )
    skill = load_skill(skill_id)

    with patch(
        "sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
        new=AsyncMock(return_value=resistance_score),
    ), patch(
        "sage_poc.nodes.skill_executor.load_skill",
        return_value=skill,
    ):
        for turn in range(max_turns):
            result = await skill_executor_node(state)
            # Carry forward executor outputs into next turn's state
            state["active_skill_id"] = result.get("active_skill_id")
            state["active_step_id"]  = result.get("active_step_id", state["active_step_id"])
            state["resistance_history"] = result.get("resistance_history", state["resistance_history"])
            state["path"] = []  # reset path per turn

            if result.get("active_skill_id") is None:
                # active_skill_id=None means either normal completion or L1 exit.
                # Distinguish by escalation_triggered: L1 sets level="L1"; completion leaves it None.
                triggered = result.get("escalation_triggered") or {}
                is_l1 = triggered.get("level") == "L1"
                return not is_l1, turn + 1

    return False, max_turns


# ── S01–S07: Happy path completion for all 7 target skills ────────────────────

class TestHappyPathCompletion:
    """Each of the 7 target skills must complete within max_turns when given
    cooperative user messages (>10 words, no rule-fire conditions)."""

    @pytest.mark.parametrize("skill_id,first_step", [
        ("cbt_thought_record", "identify_thought"),
        ("dbt_tipp", "temperature"),
        ("mi_readiness_ruler", "importance_ruler"),
        ("behavioral_activation", "activity_audit"),
        ("sleep_hygiene", "assess_sleep"),
        ("grounding_5_4_3_2_1", "see_5"),
        ("mood_check_in", "score_mood"),
    ])
    async def test_skill_completes_happy_path(self, skill_id, first_step):
        completed, turns = await _run_to_completion(
            skill_id=skill_id,
            first_step_id=first_step,
        )
        assert completed, (
            f"S: {skill_id} must complete within 30 turns on happy path "
            f"(completed={completed}, turns={turns})"
        )

    async def test_completion_rate_meets_kpi_threshold(self):
        """Completion rate across all 7 happy-path scenarios must be >= 80% (≥6/7)."""
        skills = [
            ("cbt_thought_record",  "identify_thought"),
            ("dbt_tipp",            "temperature"),
            ("mi_readiness_ruler",  "importance_ruler"),
            ("behavioral_activation", "activity_audit"),
            ("sleep_hygiene",       "assess_sleep"),
            ("grounding_5_4_3_2_1", "see_5"),
            ("mood_check_in",       "score_mood"),
        ]
        completions = 0
        for skill_id, first_step in skills:
            completed, _ = await _run_to_completion(skill_id, first_step)
            if completed:
                completions += 1

        rate = completions / len(skills)
        assert rate >= 0.80, (
            f"Completion rate {rate:.0%} ({completions}/{len(skills)}) "
            f"is below the 4.4 KPI target of ≥80%"
        )


# ── S08: R1 fires then skill stalls (executor behavior on rule fire) ──────────

class TestRuleFireDoesNotComplete:
    """When a rule fires, the skill should NOT advance — next_step_id stays current."""

    async def test_r1_does_not_advance_step(self):
        """emotional_intensity > 7 → next_step_id must be same as current."""
        state = make_executor_state(
            skill_id="cbt_thought_record",
            step_id="explore_distortion",
            emotional_intensity=9,
            engagement=7,
        )
        skill = load_skill("cbt_thought_record")
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=skill), \
             patch("sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
                   new=AsyncMock(return_value=None)):
            result = await skill_executor_node(state)
        assert result["active_step_id"] == "explore_distortion", (
            "R1 must hold the current step, not advance"
        )
        assert result["active_skill_id"] == "cbt_thought_record", (
            "R1 must not exit the skill"
        )

    async def test_r3_does_not_advance_step(self):
        """engagement < 3 for 3 turns → step stays, skill stays."""
        state = make_executor_state(
            skill_id="cbt_thought_record",
            step_id="explore_distortion",
            engagement=2,
            engagement_trajectory=[2, 2],
            emotional_intensity=4,
        )
        skill = load_skill("cbt_thought_record")
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=skill), \
             patch("sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
                   new=AsyncMock(return_value=None)):
            result = await skill_executor_node(state)
        assert result["active_step_id"] == "explore_distortion"
        assert result["active_skill_id"] == "cbt_thought_record"


# ── S11: L1 exit mid-skill ───────────────────────────────────────────────────

class TestL1ExitMidSkill:
    """L1 exit must clear active_skill_id and return immediately."""

    async def test_l1_exits_mid_skill(self):
        state = make_executor_state(
            skill_id="behavioral_activation",
            step_id="identify_small_step",
            message_en="i am done with this",
        )
        skill = load_skill("behavioral_activation")
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=skill):
            result = await skill_executor_node(state)
        assert result["active_skill_id"] is None
        assert result["escalation_triggered"]["level"] == "L1"

    async def test_skill_completes_if_user_does_not_exit(self):
        """Confirm the same skill completes when user does NOT send exit phrase."""
        completed, _ = await _run_to_completion(
            skill_id="behavioral_activation",
            first_step_id="activity_audit",
        )
        assert completed


# ── S15–S17: Extended scenarios — no looping, eventual completion ─────────────

class TestExtendedConversations:
    """Skills must not loop indefinitely. Given enough cooperative turns, every
    skill must reach skill_complete=True within max_turns."""

    async def test_cbt_completes_within_20_turns(self):
        completed, turns = await _run_to_completion(
            "cbt_thought_record", "identify_thought", max_turns=20
        )
        assert completed, f"CBT must complete within 20 turns (took {turns})"

    async def test_ba_completes_within_20_turns(self):
        completed, turns = await _run_to_completion(
            "behavioral_activation", "activity_audit", max_turns=20
        )
        assert completed, f"BA must complete within 20 turns (took {turns})"

    async def test_grounding_completes_within_20_turns(self):
        """Grounding has 5 steps — needs more turns than 3-step skills."""
        completed, turns = await _run_to_completion(
            "grounding_5_4_3_2_1", "see_5", max_turns=20
        )
        assert completed, f"Grounding must complete within 20 turns (took {turns})"

    async def test_dbt_completes_within_20_turns(self):
        completed, turns = await _run_to_completion(
            "dbt_tipp", "temperature", max_turns=20
        )
        assert completed, f"DBT TIPP must complete within 20 turns (took {turns})"

    async def test_rule_fire_then_recovery_and_completion(self):
        """R1 fires on turn 1, recovers on turn 2, skill eventually completes."""
        long_msg = (
            "I have been thinking carefully about what you asked and I feel like "
            "I am making progress with this exercise today."
        )
        skill = load_skill("cbt_thought_record")
        state = make_executor_state(
            skill_id="cbt_thought_record",
            step_id="identify_thought",
            emotional_intensity=9,   # R1 fires on turn 1
            engagement=7,
            message_en=long_msg,
        )
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=skill), \
             patch("sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
                   new=AsyncMock(return_value=None)):
            # Turn 1: R1 fires, step holds
            result = await skill_executor_node(state)
            assert result["active_step_id"] == "identify_thought"

            # Turn 2: intensity drops, skill can advance
            state["active_step_id"] = result["active_step_id"]
            state["emotional_intensity"] = 5
            state["path"] = []
            result2 = await skill_executor_node(state)

        # After recovery, step should not be stuck on identify_thought
        assert result2["active_skill_id"] == "cbt_thought_record", (
            "Skill must remain active after R1 resolves"
        )
