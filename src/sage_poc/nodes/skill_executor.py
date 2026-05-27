# src/sage_poc/nodes/skill_executor.py
import json
import logging
import re
from pathlib import Path

from sage_poc.state import SageState
from sage_poc.skills.schema import Skill, load_skill

_log = logging.getLogger(__name__)

_OPERATOR_MAP = {
    ">":  lambda a, b: a > b,
    "<":  lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
}

_RESISTANCE_PROMPT_PATH = (
    Path(__file__).parent.parent
    / "rules" / "data" / "resistance_scoring" / "resistance_prompt.json"
)

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


def check_escalation(
    message_en: str,
    new_clinical_flags_turn: list[str],
) -> tuple[dict | None, dict | None]:
    """Returns (l1_escalation, l2_advisory).

    L1 is blocking — caller must exit the skill immediately.
    L2 is advisory — caller logs and continues normal step_policy execution.
    Both are based only on this turn's signals so they can't accumulate stale state.
    """
    message_lower = message_en.lower()

    l1 = None
    if any(phrase in message_lower for phrase in L1_EXIT_PHRASES):
        l1 = {
            "level":  "L1",
            "reason": "User requested to stop the skill",
            "action": "exit_skill",
        }

    # L2 fires only on flags detected THIS turn, not the full accumulated set (X1 fix).
    l2 = None
    if new_clinical_flags_turn:
        l2 = {
            "level":  "L2",
            "reason": f"Clinical flags detected this turn: {', '.join(new_clinical_flags_turn)}",
            "action": "flag_clinician",
        }

    return l1, l2


def _meets_completion_criteria(message_en: str) -> bool:
    """Heuristic: > 10 words signals the user engaged with the step. Empty string → skip check."""
    if not message_en:
        return True
    return len(message_en.split()) > 10


async def _score_resistance_via_rules_service(
    message_en: str,
    recent_context: str = "",
) -> int | None:
    """Score user resistance 1-10 via LLM using the clinician-authored resistance prompt.

    Returns None on any failure so callers treat it as a missing signal rather than crashing.
    Latency: ~400-800ms on OpenRouter. Only called when a skill step_policy references 'resistance'.
    """
    try:
        template = json.loads(_RESISTANCE_PROMPT_PATH.read_text(encoding="utf-8"))
        prompt = (
            template["prompt"]
            .replace("{message_en}", message_en)
            .replace("{recent_context}", recent_context or "")
        )
        from sage_poc.llm import get_classifier
        llm = get_classifier()
        response = await llm.ainvoke([{"role": "user", "content": prompt}])
        raw = response.content.strip()
        match = re.search(r'\b(10|[1-9])\b', raw)
        if match:
            score = int(match.group(1))
            if 1 <= score <= 10:
                return score
    except Exception as exc:
        _log.warning("[skill_executor] resistance scoring failed: %s", exc)
    return None


def _condition_met(
    cond,
    signal_value: int,
    resistance_history: list[int],
) -> bool:
    """Check whether a step_policy condition is satisfied, honouring for_turns if set."""
    op_fn = _OPERATOR_MAP.get(cond.operator)
    if op_fn is None:
        return False

    for_turns = getattr(cond, "for_turns", None)
    if for_turns is None or for_turns <= 1:
        return op_fn(signal_value, cond.value)

    # Need (for_turns - 1) prior turns + current turn all satisfying the condition.
    needed_prior = for_turns - 1
    prior = resistance_history[-needed_prior:]
    if len(prior) < needed_prior:
        return False  # insufficient history — wait for more turns
    return all(op_fn(v, cond.value) for v in prior + [signal_value])


async def evaluate_step_policy(
    skill: Skill,
    current_step_id: str,
    emotional_intensity: int,
    engagement: int,
    message_en: str = "",
    resistance_history: list[int] | None = None,
) -> tuple[dict, int | None]:
    """Two-phase policy evaluation. Returns (result_dict, new_resistance_score).

    Phase 1 — deterministic: emotional_intensity and engagement rules evaluated instantly.
    Phase 2 — LLM: resistance scoring fired only when any rule references 'resistance',
               adding ~400-800ms. Score returned so caller can append to resistance_history.
    """
    resistance_history = resistance_history or []

    needs_resistance = any(r.condition.signal == "resistance" for r in skill.step_policy)
    resistance_score: int | None = None
    if needs_resistance:
        resistance_score = await _score_resistance_via_rules_service(message_en)

    signals: dict[str, int] = {
        "emotional_intensity": emotional_intensity,
        "engagement":          engagement,
    }
    if resistance_score is not None:
        signals["resistance"] = resistance_score

    for rule in skill.step_policy:
        cond = rule.condition
        if cond.step not in ("ANY", current_step_id):
            continue
        signal_value = signals.get(cond.signal)
        if signal_value is None:
            continue
        if _condition_met(cond, signal_value, resistance_history):
            return {
                "action":        rule.action,
                "instruction":   rule.instruction,
                "next_step_id":  current_step_id if rule.next_step_id == "current" else rule.next_step_id,
                "skill_complete": False,
            }, resistance_score

    # No rule fired — check completion_criteria before advancing
    step = next((s for s in skill.steps if s.step_id == current_step_id), None)
    if step is None:
        return {
            "action":        "stay",
            "instruction":   f"[Step '{current_step_id}' not found in skill — holding position]",
            "next_step_id":  current_step_id,
            "skill_complete": False,
        }, resistance_score

    step_instruction = (
        f"Goal: {step.goal}. "
        f"Technique: {step.technique}. "
        f"Tone: {step.tone}. "
        f"Example approaches: {'; '.join(step.examples[:2])}"
    )

    if not _meets_completion_criteria(message_en):
        return {
            "action":        "stay",
            "instruction":   step_instruction,
            "next_step_id":  current_step_id,
            "skill_complete": False,
        }, resistance_score

    # Criteria met — advance to next step in sequence
    step_ids = [s.step_id for s in skill.steps]
    current_idx = step_ids.index(current_step_id)
    next_id = step_ids[current_idx + 1] if current_idx + 1 < len(step_ids) else None

    return {
        "action":        "advance" if next_id else "complete",
        "instruction":   step_instruction,
        "next_step_id":  next_id or current_step_id,
        "skill_complete": next_id is None,
    }, resistance_score


async def skill_executor_node(state: SageState) -> dict:
    skill_id = state["active_skill_id"]
    step_id  = state["active_step_id"]
    skill    = load_skill(skill_id)

    # Evaluate escalation matrix BEFORE step_policy (per architecture spec §9.3).
    # Uses new_clinical_flags_turn (this turn only) — not the full accumulated set.
    l1, l2 = check_escalation(
        message_en=state["message_en"],
        new_clinical_flags_turn=state.get("new_clinical_flags_turn") or [],
    )

    # L2: advisory — log and continue; skill execution is NOT blocked.
    if l2:
        _log.info("[skill_executor] L2 advisory: %s", l2["reason"])

    # L1: blocking — exit skill immediately, no step_policy evaluation.
    if l1:
        matrix_instruction = skill.escalation_matrix.get("L1", "Follow escalation protocol.")
        crisis_update: dict = {}
        if skill_id == "post_crisis_check_in":
            crisis_update = {"crisis_state": "resolved"}
        return {
            "step_instruction":    f"[L1] {matrix_instruction}",
            "executed_step_id":    step_id,
            "active_step_id":      step_id,
            "active_skill_id":     None,
            "escalation_triggered": l1,
            "resistance_score":    None,
            "path": state["path"] + ["skill_executor"],
            **crisis_update,
        }

    resistance_history = list(state.get("resistance_history") or [])
    result, new_resistance_score = await evaluate_step_policy(
        skill=skill,
        current_step_id=step_id,
        emotional_intensity=state["emotional_intensity"],
        engagement=state["engagement"],
        message_en=state["message_en"],
        resistance_history=resistance_history,
    )

    if new_resistance_score is not None:
        resistance_history = (resistance_history + [new_resistance_score])[-3:]

    crisis_state_update: dict = {}
    if result.get("skill_complete") and skill_id == "post_crisis_check_in":
        crisis_state_update = {"crisis_state": "resolved"}

    return {
        "step_instruction":    result["instruction"],
        "executed_step_id":    step_id,
        "active_step_id":      result["next_step_id"],
        "active_skill_id":     None if result.get("skill_complete") else skill_id,
        "escalation_triggered": l2,  # advisory stored for audit; None if no L2 this turn
        "resistance_score":    new_resistance_score,
        "resistance_history":  resistance_history,
        "path": state["path"] + ["skill_executor"],
        **crisis_state_update,
    }
