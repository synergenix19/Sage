# tests/test_psychoed_carry_forward.py
#
# Phase 2 Task 9: family-exposure carry-forward via the declared session channel
# `psychoed_family_exposures` (Task 3), read alongside the existing (dead)
# techniques_used-based prior_exposure computation in skill_executor.py.
#
# Binding seam finding (verified 2026-07-28, carried into this task's dispatch):
# therapeutic_profile["techniques_used"] has no writer anywhere in the codebase and
# no DB column (postgres_repository.py:16-40) -> prior_exposure via that path is
# always 0. This task does NOT touch that dead key. It adds
# _psychoed_family_exposure(state, skill), folded in additively via max() so the
# dead read stays harmless and the live family-carry-forward signal takes over.
#
# The skip condition counts the FAMILY of the skill's kb_ref, never
# prior_exposure[skill_id] -- exposures.count(family_of(skill.kb_ref)) >= threshold.

import pytest

pytestmark = pytest.mark.safety_gate

from sage_poc.nodes.skill_executor import _psychoed_family_exposure, evaluate_step_policy
from sage_poc.skills.schema import Skill, SkillStep, StepPolicyCondition, StepPolicyRule


def _skill_kwargs(**overrides) -> dict:
    base = dict(
        skill_id="test_psychoed_carry_forward_skill",
        skill_name="Test Psychoed Carry-Forward Skill",
        skill_type="psychoeducation",
        evidence_base="test-fixture",
        target_presentations=["anxiety"],
        steps=[
            SkillStep(
                step_id="intro",
                goal="Introduce the topic.",
                technique="Psychoeducation.",
                tone="warm",
                examples=["Let's talk about anxiety."],
            ),
        ],
        step_policy=[],
        escalation_matrix={"L1": "Exit gracefully if user requests to stop."},
    )
    base.update(overrides)
    return base


def _make_skill(kb_ref: str | None = "understanding_anxiety", **overrides) -> Skill:
    kwargs = _skill_kwargs(kb_ref=kb_ref, **overrides)
    return Skill(**kwargs)


class TestPsychoedFamilyExposureHelper:
    """_psychoed_family_exposure(state, skill) -> int"""

    def test_counts_matching_family_exposures(self):
        skill = _make_skill(kb_ref="understanding_anxiety")
        state = {"psychoed_family_exposures": ["understanding_anxiety"] * 3}
        assert _psychoed_family_exposure(state, skill) == 3

    def test_skill_without_kb_ref_returns_zero(self):
        skill = _make_skill(kb_ref=None)
        state = {"psychoed_family_exposures": ["understanding_anxiety"] * 3}
        assert _psychoed_family_exposure(state, skill) == 0

    def test_unknown_kb_ref_returns_zero(self):
        skill = _make_skill(kb_ref="not_a_real_kb_ref_or_family")
        state = {"psychoed_family_exposures": ["understanding_anxiety"] * 3}
        assert _psychoed_family_exposure(state, skill) == 0

    def test_missing_exposures_key_returns_zero(self):
        skill = _make_skill(kb_ref="understanding_anxiety")
        state = {}
        assert _psychoed_family_exposure(state, skill) == 0

    def test_different_family_does_not_count(self):
        """Exposures for a DIFFERENT family must not contribute to this skill's count."""
        skill = _make_skill(kb_ref="understanding_anxiety")
        state = {"psychoed_family_exposures": ["understanding_depression"] * 5}
        assert _psychoed_family_exposure(state, skill) == 0

    def test_mixed_families_counts_only_the_matching_one(self):
        skill = _make_skill(kb_ref="understanding_anxiety")
        state = {
            "psychoed_family_exposures": (
                ["understanding_depression", "understanding_anxiety"] * 2
                + ["understanding_anxiety"]
            )
        }
        assert _psychoed_family_exposure(state, skill) == 3


class TestStepPolicyIntegration:
    """evaluate_step_policy skip_psychoeducation fires on family-exposure carry-forward,
    mirroring the real rule shape from mi_readiness_ruler.json:163 /
    problem_solving_therapy.json:208 (signal="prior_exposure", operator=">=", value=N,
    step=<step_id>, action="skip_psychoeducation")."""

    THRESHOLD = 2

    def _skill_with_skip_rule(self) -> Skill:
        return _make_skill(
            kb_ref="understanding_anxiety",
            step_policy=[
                StepPolicyRule(
                    condition=StepPolicyCondition(
                        signal="prior_exposure",
                        operator=">=",
                        value=self.THRESHOLD,
                        step="intro",
                    ),
                    action="skip_psychoeducation",
                    instruction="User has covered this psychoeducation before. Skip the framing.",
                    next_step_id="intro",
                ),
            ],
        )

    def test_skip_fires_when_family_exposures_meet_threshold(self):
        skill = self._skill_with_skip_rule()
        state = {"psychoed_family_exposures": ["understanding_anxiety"] * self.THRESHOLD}
        prior_exposure = _psychoed_family_exposure(state, skill)
        result = evaluate_step_policy(
            skill=skill,
            current_step_id="intro",
            emotional_intensity=4,
            engagement=7,
            message_en="I've been feeling anxious again.",
            prior_exposure=prior_exposure,
        )
        assert result["action"] == "skip_psychoeducation"
        assert result["next_step_id"] == "intro"

    def test_skip_does_not_fire_below_threshold(self):
        skill = self._skill_with_skip_rule()
        state = {"psychoed_family_exposures": ["understanding_anxiety"] * (self.THRESHOLD - 1)}
        prior_exposure = _psychoed_family_exposure(state, skill)
        result = evaluate_step_policy(
            skill=skill,
            current_step_id="intro",
            emotional_intensity=4,
            engagement=7,
            message_en="I've been feeling anxious again.",
            prior_exposure=prior_exposure,
        )
        assert result["action"] != "skip_psychoeducation"

    def test_different_family_exposures_do_not_trigger_skip(self):
        """Exposures accrued under a DIFFERENT family must not trigger this skill's skip."""
        skill = self._skill_with_skip_rule()
        state = {
            "psychoed_family_exposures": ["understanding_depression"] * (self.THRESHOLD + 5)
        }
        prior_exposure = _psychoed_family_exposure(state, skill)
        assert prior_exposure == 0
        result = evaluate_step_policy(
            skill=skill,
            current_step_id="intro",
            emotional_intensity=4,
            engagement=7,
            message_en="I've been feeling anxious again.",
            prior_exposure=prior_exposure,
        )
        assert result["action"] != "skip_psychoeducation"
