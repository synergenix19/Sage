"""Wave-2 — the 5 Video-format skills adopt delivery_format=video_all_at_once.

H2 ruling (2026-07-10) + Vee clinical sign-off (2026-07-10). Structural adoption: these skills
now deliver all-at-once (F2 fix — no longer chopped into typed turns). The polished collapsed
EN copy is approved and pairs with the AR translation as a follow-on; this test guards the
structural flag on the signed set.
"""
import pytest

from sage_poc.skills.schema import load_skill

VIDEO_SKILLS = [
    "box_breathing",
    "progressive_muscle_relaxation",
    "mindfulness_meditation",
    "mindfulness_body_scan",
    "safe_place_visualization",
]


@pytest.mark.parametrize("skill_id", VIDEO_SKILLS)
def test_video_skill_is_all_at_once(skill_id):
    assert load_skill(skill_id).delivery_format == "video_all_at_once", (
        f"{skill_id} must deliver all-at-once (H2 + Vee sign-off)"
    )


def test_guided_conversation_skills_unchanged():
    # turn-by-turn skills must stay turn-by-turn (TIPP, grounding, STOP)
    assert load_skill("dbt_tipp").delivery_format == "guided_conversation"
    assert load_skill("grounding_5_4_3_2_1").delivery_format == "guided_conversation"
