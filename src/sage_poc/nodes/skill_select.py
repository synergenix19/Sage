# src/sage_poc/nodes/skill_select.py
from sage_poc.state import SageState
from sage_poc.skills.schema import load_skill

# All available skills — in production this comes from the CMS
SKILL_REGISTRY = ["cbt_thought_record", "grounding_5_4_3_2_1"]

# Pre-load skills at module init so we're not reading JSON on every request
_SKILLS = {sid: load_skill(sid) for sid in SKILL_REGISTRY}


def skill_select_node(state: SageState) -> dict:
    message = state["message_en"].lower()

    for skill_id, skill in _SKILLS.items():
        for keyword in skill.target_presentations:
            if keyword.lower() in message:
                return {
                    "active_skill_id": skill_id,
                    "active_step_id": skill.steps[0].step_id,
                    "path": state["path"] + ["skill_select"],
                }

    return {
        "active_skill_id": None,
        "active_step_id": None,
        "path": state["path"] + ["skill_select"],
    }
