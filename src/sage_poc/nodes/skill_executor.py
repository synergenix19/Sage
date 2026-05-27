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
    engagement_trajectory: list[int] | None = None,
) -> bool:
    """Check whether a step_policy condition is satisfied, honouring for_turns if set.

    for_turns temporal logic is supported for two signals:
    - 'resistance': uses resistance_history (rolling 3-turn buffer, current turn appended by caller)
    - 'engagement': uses engagement_trajectory (4-turn window, one-turn lagged — safety_check
      appends the prior turn's score; intent_route sets the current turn's score afterward).
      signal_value is the current turn's engagement, so trajectory[-N:] + [signal_value]
      forms N+1 consecutive turns.
    For all other signals, for_turns is ignored and only the current value is checked.
    """
    op_fn = _OPERATOR_MAP.get(cond.operator)
    if op_fn is None:
        return False

    for_turns = getattr(cond, "for_turns", None)
    if for_turns is None or for_turns <= 1:
        return op_fn(signal_value, cond.value)

    if cond.signal == "resistance":
        history = resistance_history
    elif cond.signal == "engagement":
        history = list(engagement_trajectory or [])
    else:
        # for_turns not supported for this signal — evaluate current value only.
        return op_fn(signal_value, cond.value)

    needed_prior = for_turns - 1
    prior = history[-needed_prior:]
    if len(prior) < needed_prior:
        return False  # insufficient history — wait for more turns
    return all(op_fn(v, cond.value) for v in prior + [signal_value])


def evaluate_step_policy(
    skill: Skill,
    current_step_id: str,
    emotional_intensity: int,
    engagement: int,
    message_en: str = "",
    resistance_history: list[int] | None = None,
    resistance_score: int | None = None,
    re_escalation_detected: bool = False,
    engagement_trajectory: list[int] | None = None,
    prior_exposure: int = 0,
) -> dict:
    """Synchronous two-phase policy evaluation. Returns a result dict.

    Phase 1 — deterministic: emotional_intensity, engagement (with for_turns via
    engagement_trajectory), prior_exposure, and boolean event signals evaluated instantly.
    If any fires, returns immediately.

    Phase 2 — resistance: evaluated only when the caller provides a resistance_score.
    Caller (skill_executor_node) fetches the resistance score via LLM only after Phase 1
    finds no match, avoiding the 400-800ms cost on turns where a deterministic rule fires.

    When resistance_score is None, resistance rules are silently skipped (signal not
    present in signals dict → signal_value is None → continue).

    prior_exposure reflects cross-session skill usage only (techniques_used is updated
    at end-of-session). Within a first session, prior_exposure=0 regardless of repetitions.
    """
    resistance_history = resistance_history or []

    # Build signals dict. Resistance is included only when caller provides a score.
    signals: dict[str, int | bool] = {
        "emotional_intensity":    emotional_intensity,
        "engagement":             engagement,
        "re_escalation_detected": re_escalation_detected,
        "prior_exposure":         prior_exposure,
    }
    if resistance_score is not None:
        signals["resistance"] = resistance_score

    # Phase 1: deterministic rules (non-resistance signals only).
    # Resistance rules are skipped here because signals["resistance"] is absent when
    # resistance_score=None — the `if signal_value is None: continue` guard handles it.
    for rule in skill.step_policy:
        cond = rule.condition
        if cond.signal == "resistance":
            continue  # explicit skip: resistance is Phase 2 only
        if cond.step not in ("ANY", current_step_id):
            continue
        val = signals.get(cond.signal)
        if val is None:
            continue
        if _condition_met(cond, val, resistance_history, engagement_trajectory):
            return {
                "action":           rule.action,
                "instruction":      rule.instruction,
                "next_step_id":     current_step_id if rule.next_step_id == "current" else rule.next_step_id,
                "skill_complete":   False,
                "_det_rule_fired":  True,  # sentinel: Phase 1 fired; skip Phase 2 in node
            }

    # Phase 2: resistance rules — only when caller provides a score.
    if resistance_score is not None:
        for rule in skill.step_policy:
            cond = rule.condition
            if cond.signal != "resistance":
                continue
            if cond.step not in ("ANY", current_step_id):
                continue
            if _condition_met(cond, resistance_score, resistance_history):
                return {
                    "action":        rule.action,
                    "instruction":   rule.instruction,
                    "next_step_id":  current_step_id if rule.next_step_id == "current" else rule.next_step_id,
                    "skill_complete": False,
                }

    # No rule fired — check completion criteria before advancing.
    step = next((s for s in skill.steps if s.step_id == current_step_id), None)
    if step is None:
        return {
            "action":        "stay",
            "instruction":   f"[Step '{current_step_id}' not found in skill — holding position]",
            "next_step_id":  current_step_id,
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
            "action":        "stay",
            "instruction":   step_instruction,
            "next_step_id":  current_step_id,
            "skill_complete": False,
        }

    # Criteria met — advance to next step in sequence.
    step_ids = [s.step_id for s in skill.steps]
    current_idx = step_ids.index(current_step_id)
    next_id = step_ids[current_idx + 1] if current_idx + 1 < len(step_ids) else None

    return {
        "action":        "advance" if next_id else "complete",
        "instruction":   step_instruction,
        "next_step_id":  next_id or current_step_id,
        "skill_complete": next_id is None,
    }


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

    resistance_history    = list(state.get("resistance_history") or [])
    engagement_trajectory = list(state.get("engagement_trajectory") or [])
    re_escalation_detected = state.get("s7_result") == "NEW_CRISIS"

    # prior_exposure: number of times this skill appears in techniques_used from the
    # therapeutic profile. Reflects cross-session usage only — techniques_used is
    # updated at end-of-session, so within a first session prior_exposure=0.
    therapeutic_profile = state.get("therapeutic_profile") or {}
    techniques_used = therapeutic_profile.get("techniques_used") or []
    prior_exposure = techniques_used.count(skill_id)

    # Phase 1: deterministic rules only (resistance_score=None → resistance rules skipped).
    # Returns a result dict. If a deterministic rule fires, its action will be present.
    # We detect "Phase 1 fired a rule" by checking the private sentinel key.
    p1_result = evaluate_step_policy(
        skill=skill,
        current_step_id=step_id,
        emotional_intensity=state["emotional_intensity"],
        engagement=state["engagement"],
        message_en=state["message_en"],
        resistance_history=resistance_history,
        resistance_score=None,
        re_escalation_detected=re_escalation_detected,
        engagement_trajectory=engagement_trajectory,
        prior_exposure=prior_exposure,
    )

    # Phase 2: resistance scoring — only if the skill references 'resistance' rules AND
    # Phase 1 did not fire a deterministic rule. Phase 1 exclusively evaluates non-resistance
    # rules; when it fires one, it sets "_det_rule_fired": True in the result.
    new_resistance_score: int | None = None
    needs_resistance = any(r.condition.signal == "resistance" for r in skill.step_policy)
    p1_det_fired = p1_result.pop("_det_rule_fired", False)

    result = p1_result
    if needs_resistance and not p1_det_fired:
        new_resistance_score = await _score_resistance_via_rules_service(state["message_en"])
        if new_resistance_score is not None:
            result = evaluate_step_policy(
                skill=skill,
                current_step_id=step_id,
                emotional_intensity=state["emotional_intensity"],
                engagement=state["engagement"],
                message_en=state["message_en"],
                resistance_history=resistance_history,
                resistance_score=new_resistance_score,
                re_escalation_detected=re_escalation_detected,
                engagement_trajectory=engagement_trajectory,
                prior_exposure=prior_exposure,
            )
            result.pop("_det_rule_fired", None)

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
