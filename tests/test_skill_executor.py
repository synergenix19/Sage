# tests/test_skill_executor.py
#
# Tests for clinical flag lifecycle: X1 fix, L2 advisory, for_turns temporal
# condition, and post_crisis_check_in crisis resolution on L1.
#
# T1: check_escalation uses new_clinical_flags_turn (X1 fix)
# T4: L2 advisory does not block skill execution
# T6: post_crisis_check_in resolves crisis_state on L1
# T7: for_turns temporal condition on resistance signal

import pytest
from unittest.mock import patch, AsyncMock

from sage_poc.nodes.skill_executor import (
    check_escalation,
    evaluate_step_policy,
    _condition_met,
    skill_executor_node,
)
from sage_poc.skills.schema import Skill, SkillStep, StepPolicyRule, StepPolicyCondition


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_skill(
    with_resistance_rule: bool = False,
    for_turns: int | None = None,
    skill_id: str = "test_skill",
) -> Skill:
    step_policy = [
        StepPolicyRule(
            condition=StepPolicyCondition(
                signal="emotional_intensity", operator=">", value=8, step="ANY"
            ),
            action="slow_down",
            instruction="Take it gently.",
            next_step_id="current",
        )
    ]
    if with_resistance_rule:
        step_policy.append(
            StepPolicyRule(
                condition=StepPolicyCondition(
                    signal="resistance", operator=">", value=6, step="ANY",
                    for_turns=for_turns,
                ),
                action="offer_break",
                instruction="Would you like to take a break from this exercise?",
                next_step_id="current",
            )
        )
    return Skill(
        skill_id=skill_id,
        skill_name="Test Skill",
        skill_type="cbt",
        evidence_base="test",
        target_presentations=["anxiety"],
        steps=[
            SkillStep(
                step_id="step_1",
                goal="Test goal",
                technique="Socratic questioning",
                tone="warm",
                examples=["What are you thinking right now?", "Can you say more?"],
            )
        ],
        step_policy=step_policy,
        escalation_matrix={
            "L1": "Let's try something different.",
            "L2": "I've made a note of this.",
        },
    )


def _make_executor_state(**kwargs) -> dict:
    defaults = {
        "active_skill_id":      "test_skill",
        "active_step_id":       "step_1",
        "message_en":           "I feel a bit stuck right now.",
        "raw_message":          "I feel a bit stuck right now.",
        "new_clinical_flags_turn": [],
        "clinical_flags":       [],
        "emotional_intensity":  5,
        "engagement":           7,
        "resistance_history":   [],
        "resistance_score":     None,
        "path":                 [],
        "crisis_state":         "none",
    }
    return {**defaults, **kwargs}


# ── T1: check_escalation uses new_clinical_flags_turn only (X1 fix) ──────────

class TestT1CheckEscalationX1Fix:
    """X1 fix: L2 must fire on new_clinical_flags_turn (this turn), not the
    full accumulated clinical_flags set. Prior-turn-only flags must not block."""

    def test_accumulated_flags_only_do_not_trigger_l2(self):
        """If a flag was set on a prior turn but NOT re-detected this turn, L2 must not fire."""
        l1, l2 = check_escalation(
            message_en="I'm feeling fine today.",
            new_clinical_flags_turn=[],   # no new flags this turn
        )
        assert l2 is None, (
            "L2 must not fire when new_clinical_flags_turn is empty, "
            "even if clinical_flags accumulated prior-turn flags."
        )

    def test_new_flag_this_turn_triggers_l2(self):
        """A flag detected on the current turn triggers the L2 advisory."""
        l1, l2 = check_escalation(
            message_en="I've been drinking heavily.",
            new_clinical_flags_turn=["substance_use"],
        )
        assert l2 is not None
        assert l2["level"] == "L2"
        assert l2["action"] == "flag_clinician"
        assert "substance_use" in l2["reason"]

    def test_l1_fires_on_exit_phrase(self):
        """L1 still fires correctly on recognized exit phrases."""
        l1, l2 = check_escalation(
            message_en="i am done with this.",
            new_clinical_flags_turn=[],
        )
        assert l1 is not None
        assert l1["level"] == "L1"
        assert l1["action"] == "exit_skill"

    def test_l1_and_l2_can_coexist(self):
        """L1 and L2 can both fire in the same turn — caller handles L1 first."""
        l1, l2 = check_escalation(
            message_en="i'm done with this and I've been drinking.",
            new_clinical_flags_turn=["substance_use"],
        )
        assert l1 is not None
        assert l2 is not None


# ── T4: L2 advisory does not block skill execution ───────────────────────────

class TestT4L2Advisory:
    """L2 is advisory — when new_clinical_flags_turn fires, the skill must
    continue executing (step_policy runs). skill_executor_node must NOT
    return an early [L2] escalation response."""

    async def test_l2_does_not_exit_skill(self):
        # Use a 1-word message so completion criteria (> 1) doesn't fire and the
        # skill stays active — isolating the L2 advisory behaviour.
        state = _make_executor_state(
            new_clinical_flags_turn=["substance_use"],
            message_en="okay",
        )
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=_make_skill()):
            result = await skill_executor_node(state)

        # Skill must remain active (not exited due to L2)
        assert result["active_skill_id"] == "test_skill", (
            "L2 advisory must not clear active_skill_id — skill continues"
        )
        # step_instruction must NOT come from the escalation_matrix L2 entry
        assert "[L2]" not in (result.get("step_instruction") or ""), (
            "step_instruction must come from step_policy, not the L2 escalation_matrix"
        )

    async def test_l2_stored_in_escalation_triggered_for_audit(self):
        state = _make_executor_state(new_clinical_flags_turn=["trauma_indicator"])
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=_make_skill()):
            result = await skill_executor_node(state)

        assert result.get("escalation_triggered") is not None
        assert result["escalation_triggered"]["level"] == "L2"

    async def test_no_escalation_when_no_new_flags_and_no_exit(self):
        state = _make_executor_state(new_clinical_flags_turn=[])
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=_make_skill()):
            result = await skill_executor_node(state)

        assert result.get("escalation_triggered") is None


# ── T6: post_crisis_check_in resolves crisis_state on L1 ─────────────────────

class TestT6PostCrisisL1Resolution:
    """When active_skill_id is 'post_crisis_check_in' and L1 fires (user exits),
    crisis_state must be set to 'resolved'. L2 must NOT trigger resolution."""

    async def test_l1_resolves_crisis_state_in_post_crisis_skill(self):
        state = _make_executor_state(
            active_skill_id="post_crisis_check_in",
            message_en="i am done with this",
            new_clinical_flags_turn=[],
        )
        pci_skill = _make_skill(skill_id="post_crisis_check_in")
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=pci_skill):
            result = await skill_executor_node(state)

        assert result["crisis_state"] == "resolved", (
            "post_crisis_check_in must set crisis_state='resolved' on L1 exit"
        )
        assert result["active_skill_id"] is None
        assert result["escalation_triggered"]["level"] == "L1"

    async def test_l2_does_not_resolve_crisis_state(self):
        """L2 advisory must not set crisis_state='resolved' — only L1 does."""
        # Use a 1-word message so completion criteria (> 1) doesn't fire;
        # otherwise the single-step mock skill completes and sets crisis_state='resolved'.
        state = _make_executor_state(
            active_skill_id="post_crisis_check_in",
            message_en="okay",
            new_clinical_flags_turn=["medication_mention"],
        )
        pci_skill = _make_skill(skill_id="post_crisis_check_in")
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=pci_skill):
            result = await skill_executor_node(state)

        assert result.get("crisis_state") != "resolved", (
            "L2 advisory must not resolve crisis_state — only L1 exit does"
        )


# ── T7: for_turns temporal condition on resistance signal ─────────────────────

class TestT7ForTurnsCondition:
    """for_turns requires N consecutive turns satisfying the condition before firing.
    resistance_history holds prior-turn scores; current turn's score is added by caller."""

    def test_condition_met_without_for_turns_uses_current_value(self):
        cond = StepPolicyCondition(signal="resistance", operator=">", value=6, step="ANY")
        assert _condition_met(cond, signal_value=7, resistance_history=[]) is True
        assert _condition_met(cond, signal_value=5, resistance_history=[]) is False

    def test_for_turns_requires_sufficient_prior_history(self):
        """for_turns=3 with only 1 prior turn in history must not fire."""
        cond = StepPolicyCondition(
            signal="resistance", operator=">", value=6, step="ANY", for_turns=3
        )
        # Only 1 prior score — need 2 prior + current = 3 total
        assert _condition_met(cond, signal_value=8, resistance_history=[8]) is False

    def test_for_turns_fires_when_full_history_satisfies(self):
        """for_turns=3 with 2 prior turns all > 6 plus current > 6 must fire."""
        cond = StepPolicyCondition(
            signal="resistance", operator=">", value=6, step="ANY", for_turns=3
        )
        assert _condition_met(cond, signal_value=8, resistance_history=[7, 8]) is True

    def test_for_turns_does_not_fire_if_one_prior_turn_below_threshold(self):
        cond = StepPolicyCondition(
            signal="resistance", operator=">", value=6, step="ANY", for_turns=3
        )
        # Prior turn 2 was low — streak broken
        assert _condition_met(cond, signal_value=8, resistance_history=[5, 8]) is False

    def test_for_turns_1_behaves_like_no_for_turns(self):
        """for_turns=1 should behave identically to no for_turns (check current turn only)."""
        cond_with = StepPolicyCondition(
            signal="resistance", operator=">", value=6, step="ANY", for_turns=1
        )
        cond_without = StepPolicyCondition(
            signal="resistance", operator=">", value=6, step="ANY"
        )
        for signal_value in [5, 6, 7, 10]:
            assert (
                _condition_met(cond_with, signal_value, resistance_history=[])
                == _condition_met(cond_without, signal_value, resistance_history=[])
            )

    def test_evaluate_step_policy_fires_resistance_rule_after_consecutive_turns(self):
        """Full evaluate_step_policy path: resistance rule with for_turns=3 fires only
        after sufficient consecutive turns. evaluate_step_policy is synchronous;
        resistance_score is passed directly by the caller."""
        skill = _make_skill(with_resistance_rule=True, for_turns=3)

        # Only 1 prior turn — rule must not fire (resistance_score=8, but only 1 prior)
        result_early = evaluate_step_policy(
            skill=skill,
            current_step_id="step_1",
            emotional_intensity=5,
            engagement=7,
            message_en="This exercise isn't for me.",
            resistance_history=[8],   # only 1 prior — need 2
            resistance_score=8,
        )
        assert result_early["action"] != "offer_break", (
            "for_turns=3 must not fire with only 1 prior turn in history"
        )

        # 2 prior turns — all > 6 + current > 6 → rule fires
        result_full = evaluate_step_policy(
            skill=skill,
            current_step_id="step_1",
            emotional_intensity=5,
            engagement=7,
            message_en="This exercise isn't for me.",
            resistance_history=[7, 8],  # 2 prior turns > 6
            resistance_score=8,
        )
        assert result_full["action"] == "offer_break", (
            "for_turns=3 must fire when 2 prior turns + current all satisfy the condition"
        )

    async def test_resistance_score_written_to_history(self):
        """skill_executor_node must append the turn's resistance score to resistance_history."""
        skill = _make_skill(with_resistance_rule=True)
        state = _make_executor_state(
            new_clinical_flags_turn=[],
            resistance_history=[5, 6],  # existing history (2 turns)
        )
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=skill), \
             patch(
                 "sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
                 new=AsyncMock(return_value=4),
             ):
            result = await skill_executor_node(state)

        # History should now have 3 entries (capped at 3), ending with 4
        history = result["resistance_history"]
        assert history[-1] == 4
        assert len(history) <= 3


# ── M5 fix: re_escalation_detected wired from s7_result into step_policy ──────

class TestM5ReEscalationDetected:
    """M5 fix: when s7_result == "NEW_CRISIS" during post-crisis monitoring, the
    re_escalation_detected signal must reach evaluate_step_policy() so the
    step_policy rule in post_crisis_check_in.json can fire."""

    def test_re_escalation_detected_fires_step_policy_rule(self):
        """evaluate_step_policy: re_escalation_detected=True fires matching rule."""
        from sage_poc.skills.schema import load_skill
        skill = load_skill("post_crisis_check_in")
        result = evaluate_step_policy(
            skill=skill,
            current_step_id=skill.steps[0].step_id,
            emotional_intensity=4,
            engagement=6,
            re_escalation_detected=True,
        )
        assert result["action"] == "exit_to_crisis_protocol", (
            "re_escalation_detected=True must fire the exit_to_crisis_protocol rule"
        )

    def test_re_escalation_not_detected_does_not_fire_rule(self):
        """evaluate_step_policy: re_escalation_detected=False must not fire the rule."""
        from sage_poc.skills.schema import load_skill
        skill = load_skill("post_crisis_check_in")
        result = evaluate_step_policy(
            skill=skill,
            current_step_id=skill.steps[0].step_id,
            emotional_intensity=4,
            engagement=6,
            re_escalation_detected=False,
        )
        assert result["action"] != "exit_to_crisis_protocol", (
            "re_escalation_detected=False must not fire the re-escalation rule"
        )

    async def test_s7_new_crisis_triggers_re_escalation_in_node(self):
        """skill_executor_node: s7_result='NEW_CRISIS' must cause the
        re_escalation_detected step_policy rule to fire in post_crisis_check_in."""
        from sage_poc.skills.schema import load_skill
        skill = load_skill("post_crisis_check_in")
        state = _make_executor_state(
            active_skill_id="post_crisis_check_in",
            active_step_id=skill.steps[0].step_id,
            s7_result="NEW_CRISIS",
            crisis_state="monitoring",
            emotional_intensity=4,
            engagement=6,
            new_clinical_flags_turn=[],
        )
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=skill):
            result = await skill_executor_node(state)

        assert result.get("step_instruction") and "Exit" in result["step_instruction"], (
            "s7_result=NEW_CRISIS must produce the exit_to_crisis_protocol instruction"
        )


# ── Task 7: criteria_met param and _criteria_blocked sentinel ─────────────────

def test_evaluate_step_policy_criteria_blocked_sentinel():
    """When heuristic blocks advancement (single-word response), result must contain _criteria_blocked=True."""
    skill = Skill(
        skill_id="test_cbt",
        skill_name="Test CBT",
        skill_type="cbt",
        evidence_base="test",
        target_presentations=[],
        steps=[
            SkillStep(
                step_id="step_1",
                goal="Share a thought",
                technique="Cognitive",
                tone="warm",
                examples=["example"],
                completion_criteria="User has shared a specific thought they are struggling with",
            )
        ],
        step_policy=[],
        escalation_matrix={"L1": "Exit"},
    )
    result = evaluate_step_policy(
        skill=skill,
        current_step_id="step_1",
        emotional_intensity=5,
        engagement=7,
        message_en="ok",  # single word — heuristic blocks
    )
    assert result.get("_criteria_blocked") is True
    assert result["skill_complete"] is False


def test_evaluate_step_policy_criteria_met_true_advances():
    """When criteria_met=True is passed, step must advance regardless of word count."""
    skill = Skill(
        skill_id="test_cbt",
        skill_name="Test CBT",
        skill_type="cbt",
        evidence_base="test",
        target_presentations=[],
        steps=[
            SkillStep(
                step_id="step_1",
                goal="Share a thought",
                technique="Cognitive",
                tone="warm",
                examples=["example"],
                completion_criteria="User has shared a specific thought",
            ),
            SkillStep(
                step_id="step_2",
                goal="Challenge it",
                technique="Socratic",
                tone="warm",
                examples=["example"],
                completion_criteria="",
            ),
        ],
        step_policy=[],
        escalation_matrix={"L1": "Exit"},
    )
    result = evaluate_step_policy(
        skill=skill,
        current_step_id="step_1",
        emotional_intensity=5,
        engagement=7,
        message_en="ok",  # single word — would fail heuristic
        criteria_met=True,  # LLM says yes
    )
    assert result["action"] == "advance"
    assert result["next_step_id"] == "step_2"
    assert result.get("_criteria_blocked") is None


def test_evaluate_step_policy_criteria_met_false_blocks():
    """When criteria_met=False is passed, step must stay even for multi-word message."""
    skill = Skill(
        skill_id="test_cbt",
        skill_name="Test CBT",
        skill_type="cbt",
        evidence_base="test",
        target_presentations=[],
        steps=[
            SkillStep(
                step_id="step_1",
                goal="Share a thought",
                technique="Cognitive",
                tone="warm",
                examples=["example"],
                completion_criteria="User has named a specific thought",
            )
        ],
        step_policy=[],
        escalation_matrix={"L1": "Exit"},
    )
    result = evaluate_step_policy(
        skill=skill,
        current_step_id="step_1",
        emotional_intensity=5,
        engagement=7,
        message_en="I guess I feel bad",  # multi-word — would pass heuristic
        criteria_met=False,  # LLM says no
    )
    assert result["action"] == "stay"
    assert result["skill_complete"] is False
    assert result.get("_criteria_blocked") is True
