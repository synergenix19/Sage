# src/sage_poc/nodes/skill_executor.py
import re
from sage_poc.state import SageState
from sage_poc.skills.schema import Skill, load_skill

_OPERATOR_MAP = {
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
}

# L1 escalation: user wants to stop the skill.
# Bare single words ("stop", "quit", "leave") excluded: too many false positives in therapeutic
# contexts ("I can't stop thinking", "I want to quit smoking", "can't leave my house").
# System-internal vocabulary ("exercise", "skill") also excluded: users don't know those terms.
# All phrases below are natural exit language validated against the clinical audit false-positive set.
L1_EXIT_PHRASES = [
    "i don't want to do this anymore",
    "don't want to do this anymore",
    "not doing this anymore",
    "not doing this",
    "can we do something else",
    "can we talk about something else",
    "talk about something else",
    "change the subject",
    "let's move on",
    "let's stop this",
    "i want to stop this",
    "i'm done",
    "i am done",
    "want to leave this",
]


def check_escalation(message_en: str, clinical_flags: list[str]) -> dict | None:
    """Evaluates escalation matrix before step_policy. Returns escalation dict or None."""
    message_lower = message_en.lower()

    # L1: user requests to stop — substring match is safe here because all phrases are
    # multi-word or low-ambiguity single words; "stop" and "leave" removed (see L1_EXIT_PHRASES)
    if any(phrase in message_lower for phrase in L1_EXIT_PHRASES):
        return {
            "level": "L1",
            "reason": "User requested to stop the skill",
            "action": "exit_skill",
        }

    # L2: clinical flag detected (substance, trauma, eating, medication)
    if clinical_flags:
        return {
            "level": "L2",
            "reason": f"Clinical flags detected: {', '.join(clinical_flags)}",
            "action": "flag_clinician",
        }

    return None


def _meets_completion_criteria(message_en: str) -> bool:
    """Heuristic: > 10 words signals the user engaged with the step. Empty string → skip check."""
    if not message_en:
        return True
    return len(message_en.split()) > 10


def evaluate_step_policy(
    skill: Skill,
    current_step_id: str,
    emotional_intensity: int,
    engagement: int,
    message_en: str = "",
) -> dict:
    signals = {
        "emotional_intensity": emotional_intensity,
        "engagement": engagement,
    }

    for rule in skill.step_policy:
        cond = rule.condition
        if cond.step not in ("ANY", current_step_id):
            continue
        signal_value = signals.get(cond.signal)
        if signal_value is None:
            continue
        op_fn = _OPERATOR_MAP.get(cond.operator)
        if op_fn and op_fn(signal_value, cond.value):
            return {
                "action": rule.action,
                "instruction": rule.instruction,
                "next_step_id": current_step_id if rule.next_step_id == "current" else rule.next_step_id,
                "skill_complete": False,
            }

    # No rule fired — check completion_criteria before advancing
    step = next((s for s in skill.steps if s.step_id == current_step_id), None)
    if step is None:
        return {
            "action": "stay",
            "instruction": f"[Step '{current_step_id}' not found in skill — holding position]",
            "next_step_id": current_step_id,
            "skill_complete": False,
        }
    step_instruction = (
        f"Goal: {step.goal}. "
        f"Technique: {step.technique}. "
        f"Tone: {step.tone}. "
        f"Example approaches: {'; '.join(step.examples[:2])}"
    )

    if not _meets_completion_criteria(message_en):
        return {
            "action": "stay",
            "instruction": step_instruction,
            "next_step_id": current_step_id,
            "skill_complete": False,
        }

    # Criteria met — advance to next step in sequence
    step_ids = [s.step_id for s in skill.steps]
    current_idx = step_ids.index(current_step_id)
    next_id = step_ids[current_idx + 1] if current_idx + 1 < len(step_ids) else None

    return {
        "action": "advance" if next_id else "complete",
        "instruction": step_instruction,
        "next_step_id": next_id or current_step_id,
        "skill_complete": next_id is None,
    }


def skill_executor_node(state: SageState) -> dict:
    skill_id = state["active_skill_id"]
    step_id = state["active_step_id"]
    skill = load_skill(skill_id)

    # Evaluate escalation matrix BEFORE step_policy (per architecture spec §9.3)
    escalation = check_escalation(
        message_en=state["message_en"],
        clinical_flags=state.get("clinical_flags", []),
    )
    if escalation:
        matrix_instruction = skill.escalation_matrix.get(
            escalation["level"], "Follow escalation protocol."
        )
        return {
            "step_instruction": f"[{escalation['level']}] {matrix_instruction}",
            "executed_step_id": step_id,
            "active_step_id": step_id,
            "active_skill_id": None if escalation["action"] == "exit_skill" else skill_id,
            "escalation_triggered": escalation,
            "path": state["path"] + ["skill_executor"],
        }

    result = evaluate_step_policy(
        skill=skill,
        current_step_id=step_id,
        emotional_intensity=state["emotional_intensity"],
        engagement=state["engagement"],
        message_en=state["message_en"],
    )

    return {
        "step_instruction": result["instruction"],
        "executed_step_id": step_id,           # which step's instruction was used THIS turn
        "active_step_id": result["next_step_id"],  # where NEXT turn starts from
        "active_skill_id": None if result.get("skill_complete") else skill_id,
        "escalation_triggered": None,
        "path": state["path"] + ["skill_executor"],
    }
