"""Wave-2 P0b — video_all_at_once executor branch (BOT BEHAVIOUR Format=Video; H2 ruling).

A skill whose delivery_format is 'video_all_at_once' is delivered in ONE turn once past the
entry-screen safety gate: the whole remaining sequence (technique framing + video + closing
check-in) is concatenated and the skill completes, instead of one instruction per turn. The
entry_screen contraindication gate (SG-2 class) is NEVER bypassed.
"""
from sage_poc.nodes.skill_executor import evaluate_step_policy
from sage_poc.skills.schema import Skill, SkillStep


def _step(step_id, goal):
    return SkillStep(step_id=step_id, goal=goal, technique="t", tone="warm",
                     examples=["ex"], completion_criteria="c")


def _skill(delivery_format, steps):
    return Skill(
        skill_id="s", skill_name="S", skill_type="somatic", evidence_base="test",
        target_presentations=[], steps=steps, step_policy=[],
        escalation_matrix={"L1": "Exit"}, delivery_format=delivery_format,
    )


def test_video_all_at_once_delivers_whole_skill_in_one_turn():
    skill = _skill("video_all_at_once",
                   [_step("s1", "frame"), _step("s2", "middle"), _step("check_in", "close and notice")])
    result = evaluate_step_policy(skill=skill, current_step_id="s1",
                                  emotional_intensity=5, engagement=7, message_en="ok", criteria_met=True)
    assert result["skill_complete"] is True, "video_all_at_once must complete in one turn, not advance step-by-step"
    assert "close and notice" in result["instruction"], "all remaining steps must be concatenated into one delivery"


def test_video_all_at_once_never_bypasses_entry_screen():
    skill = _skill("video_all_at_once",
                   [_step("entry_screen", "safety gate"), _step("content", "video"), _step("check_in", "close")])
    result = evaluate_step_policy(skill=skill, current_step_id="entry_screen",
                                  emotional_intensity=5, engagement=7, message_en="ok", criteria_met=None)
    assert result.get("skill_complete") is not True, "entry_screen must gate first; no all-at-once here"
    assert result["next_step_id"] == "entry_screen"


def test_guided_conversation_still_advances_one_step():
    skill = _skill("guided_conversation", [_step("s1", "a"), _step("s2", "b"), _step("s3", "c")])
    result = evaluate_step_policy(skill=skill, current_step_id="s1",
                                  emotional_intensity=5, engagement=7, message_en="ok", criteria_met=True)
    assert result["next_step_id"] == "s2"
    assert result["skill_complete"] is False
