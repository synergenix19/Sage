# src/sage_poc/nodes/skill_executor.py
import json
import logging
import re
from pathlib import Path

from sage_poc.state import SageState
from sage_poc.skills.schema import Skill, load_skill
from sage_poc.nodes.criteria_eval import evaluate_completion_criteria

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

# Actions that should fire once (entry turn) then allow normal step advancement.
# Default for any action NOT in this set: hold the step (fire every turn until
# the triggering condition resolves). This is intentionally conservative —
# new actions default to hold behavior. Add here only after verifying the
# action's instruction is a one-time modification, not an ongoing clinical hold.
_SKIP_ONCE_ACTIONS: frozenset[str] = frozenset({"skip_psychoeducation"})

# Phase 2 actions that are safety-critical and always take precedence over Phase 1
# advancement.  Every other Phase 2 action is a non-safety hold (resistance/engagement
# management) and cannot override a Phase 1 advance or complete — criteria-met
# advancement beats resistance.  See precedence resolver in skill_executor_node.
_SAFETY_HOLD_ACTIONS: frozenset[str] = frozenset({"validate_only"})

# Skills where word-count heuristic is clinically insufficient — these require
# LLM evaluation of completion_criteria after Phase 1 returns _criteria_blocked.
_LLM_CRITERIA_SKILLS: frozenset[str] = frozenset({
    "post_crisis_check_in",
    "cbt_thought_record",
    "behavioral_activation",
    "assertive_communication",
    # Word-count heuristic cannot enforce qualitative bars in these skills:
    # their completion criteria require named specifics, multi-condition AND logic,
    # or explicitly reject vague agreement — all indetectable by token count alone.
    "sleep_hygiene",
    "values_clarification",
    "worry_time",
    "cognitive_restructuring",
    "interpersonal_effectiveness",
    "financial_anxiety",
    "grief_loss",
    # Entry-screen skills: LLM evaluation is the safety gate itself.
    # Without these IDs the entry_screen completion_criteria degrades silently to
    # word-count (>1 word passes anything). The load-time guard below enforces this.
    "dbt_tipp",
    "progressive_muscle_relaxation",
    "mindfulness_body_scan",
    "safe_place_visualization",
    # ACT: passive-SI / giving-up-orientation gate (distinct from somatic safety above).
    "act_psychological_flexibility",
})

# Load-time guard: every skill whose first step is "entry_screen" MUST be in
# _LLM_CRITERIA_SKILLS, or the entry screen completion_criteria silently degrades
# to word-count (>1 word passes anything) — same failure mode as dead signals.
def _validate_entry_screen_coverage() -> None:
    skills_dir = Path(__file__).parent.parent / "skills"
    missing: list[str] = []
    for path in sorted(skills_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        steps = data.get("steps", [])
        if steps and steps[0].get("step_id") == "entry_screen":
            skill_id = path.stem
            if skill_id not in _LLM_CRITERIA_SKILLS:
                missing.append(skill_id)
    if missing:
        raise RuntimeError(
            f"Entry-screen skills not in _LLM_CRITERIA_SKILLS — gate is silently inert: {missing}. "
            "Add each skill ID to _LLM_CRITERIA_SKILLS in skill_executor.py."
        )


_validate_entry_screen_coverage()

# Signals that evaluate_step_policy actually resolves. Any step_policy rule whose
# condition.signal is NOT in this set will be silently skipped at runtime
# (signals.get(unknown) → None → continue). This is the class of failure that produced
# the 18 dead signals: spec present, runtime inert, no alarm.
#
# user_stop_request is intentionally absent: it's handled by check_escalation (L1) before
# step_policy runs. A step_policy rule for it is architecturally dead — L1 fires first —
# but the intent is honored. Do not add it here or the coverage guard will suppress the error.
#
# Upgrade path: once the pre-existing dead signals (physical_contraindication_disclosed,
# pain_or_injury_mention, dissociation_or_dizziness_reported, dissociation_signal) are
# removed from skill JSONs, flip _validate_step_policy_signal_coverage to raise RuntimeError
# instead of logging at ERROR.
_KNOWN_STEP_POLICY_SIGNALS: frozenset[str] = frozenset({
    "emotional_intensity",
    "engagement",
    "re_escalation_detected",
    "prior_exposure",
    "resistance",
    "user_stop_request",  # handled by L1 check_escalation — step_policy rule is dead but intent is honored
})


def _get_dead_step_policy_signals() -> list[tuple[str, str]]:
    """Return (skill_id, signal_name) for every step_policy rule whose signal never resolves.

    The test_dead_step_policy_signal_count_is_pinned test calls this to assert the count
    stays at exactly 21. Any addition raises a red CI run rather than logging another
    ERROR line into a wall of 21 that teams learn to ignore.
    """
    skills_dir = Path(__file__).parent.parent / "skills"
    dead: list[tuple[str, str]] = []
    for path in sorted(skills_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        for rule in data.get("step_policy", []):
            signal = rule.get("condition", {}).get("signal", "")
            if signal and signal not in _KNOWN_STEP_POLICY_SIGNALS:
                dead.append((path.stem, signal))
    return dead


def _validate_step_policy_signal_coverage() -> None:
    """Log ERROR for any step_policy rule whose signal can never resolve at runtime.

    Does NOT raise — pre-existing dead signals (physical_contraindication_disclosed etc.)
    would crash startup. This surfaces them visibly at every server start so they cannot
    be ignored, without blocking the system. See upgrade path comment above.
    """
    dead = _get_dead_step_policy_signals()
    if dead:
        _log.error(
            "[skill_executor] Step-policy rules reference signals that never resolve "
            "at runtime — these rules are SILENTLY INERT: %s. "
            "Wire the signal into evaluate_step_policy or remove the rule. "
            "See _KNOWN_STEP_POLICY_SIGNALS for the upgrade path to RuntimeError.",
            dead,
        )


_validate_step_policy_signal_coverage()

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
    """Heuristic: > 1 word signals the user engaged with the step. Empty string → skip check."""
    if not message_en:
        return True
    return len(message_en.split()) > 1


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
        from sage_poc.llm import get_resistance_model
        from sage_poc.resilience import resilient_invoke
        llm = get_resistance_model()
        raw = await resilient_invoke(
            llm,
            [{"role": "user", "content": prompt}],
            node="skill_executor",
        )
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
    criteria_met: bool | None = None,
    prev_step_id: str | None = None,
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
            _completion = criteria_met if criteria_met is not None else _meets_completion_criteria(message_en)
            if (                                                    # continuation-turn skip
                rule.action in _SKIP_ONCE_ACTIONS
                and rule.next_step_id in ("current", current_step_id)
                and prev_step_id == current_step_id
                and _completion
            ):
                continue                                            # let completion advance naturally
            return {
                "action":           rule.action,
                "instruction":      rule.instruction,
                "next_step_id":     current_step_id if rule.next_step_id == "current" else rule.next_step_id,
                "skill_complete":   rule.action == "complete",
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
                _completion = criteria_met if criteria_met is not None else _meets_completion_criteria(message_en)
                if (                                                # continuation-turn skip (Phase 2)
                    rule.action in _SKIP_ONCE_ACTIONS
                    and rule.next_step_id in ("current", current_step_id)
                    and prev_step_id == current_step_id
                    and _completion
                ):
                    continue
                return {
                    "action":        rule.action,
                    "instruction":   rule.instruction,
                    "next_step_id":  current_step_id if rule.next_step_id == "current" else rule.next_step_id,
                    "skill_complete": rule.action == "complete",
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

    # entry_screen steps must always route through LLM evaluation — the word-count
    # heuristic passes any multi-word message including "I have a pacemaker", which is
    # exactly the input the gate exists to catch. Forcing heuristic_met=False ensures
    # _criteria_blocked is always set, so the caller always calls evaluate_completion_criteria.
    if current_step_id == "entry_screen":
        heuristic_met = False
    else:
        heuristic_met = _meets_completion_criteria(message_en)
    met = criteria_met if criteria_met is not None else heuristic_met
    if not met:
        return {
            "action":            "stay",
            "instruction":       step_instruction,
            "next_step_id":      current_step_id,
            "skill_complete":    False,
            "_criteria_blocked": True,
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

    # prev_step_id: the step executed on the PREVIOUS turn (persists via LangGraph checkpoint;
    # absent from _build_state so it is NOT reset each turn). When prev_step_id == step_id,
    # we are on a continuation turn — skip-once rules may be bypassed so completion can advance.
    prev_step_id: str | None = state.get("prev_step_id")

    # Per-step resistance_history reset: a saturated history from a prior step must not
    # pre-arm R2 on the first turn of the next step (which is always a stay before criteria
    # are met). Without this, [7,7,7] from step N fires R2 immediately at step N+1 turn 1.
    if prev_step_id is not None and prev_step_id != step_id:
        resistance_history = []
        _log.debug("[skill_executor] resistance_history reset: step change %s → %s", prev_step_id, step_id)

    _base_policy_kwargs = {
        "skill":                skill,
        "current_step_id":      step_id,
        "emotional_intensity":  state["emotional_intensity"],
        "engagement":           state["engagement"],
        "message_en":           state["message_en"],
        "resistance_history":   resistance_history,
        "re_escalation_detected": re_escalation_detected,
        "engagement_trajectory": engagement_trajectory,
        "prior_exposure":       prior_exposure,
        "prev_step_id":         prev_step_id,
    }

    def _clean_policy_result(r: dict) -> dict:
        r.pop("_det_rule_fired", None)
        r.pop("_criteria_blocked", None)
        return r

    # Phase 1: deterministic rules only (resistance_score=None → resistance rules skipped).
    # Returns a result dict. If a deterministic rule fires, its action will be present.
    # We detect "Phase 1 fired a rule" by checking the private sentinel key.
    p1_result = evaluate_step_policy(**_base_policy_kwargs, resistance_score=None)
    _p1_action = p1_result.get("action")

    # Phase 2: resistance scoring — only if the skill references 'resistance' rules AND
    # Phase 1 did not fire a deterministic rule. Phase 1 exclusively evaluates non-resistance
    # rules; when it fires one, it sets "_det_rule_fired": True in the result.
    new_resistance_score: int | None = None
    needs_resistance = any(r.condition.signal == "resistance" for r in skill.step_policy)
    p1_det_fired = p1_result.pop("_det_rule_fired", False)

    result = p1_result

    # LLM criteria evaluation — only for the 11 target skills, only when Phase 1
    # returned _criteria_blocked (word-count heuristic blocked advancement, no rule fired).
    p1_criteria_blocked = result.pop("_criteria_blocked", False)
    # Track whether the LLM confirmed criteria met, so resistance Phase 2 re-run can
    # honour it (avoids the heuristic re-blocking an LLM-approved advance).
    llm_criteria_met: bool | None = None
    if p1_criteria_blocked and skill_id in _LLM_CRITERIA_SKILLS:
        step_obj = next((s for s in skill.steps if s.step_id == step_id), None)
        if step_obj and step_obj.completion_criteria:
            llm_criteria_met = await evaluate_completion_criteria(
                state["message_en"],
                step_obj.completion_criteria,
                fail_closed=(step_id == "entry_screen"),
            )
            if llm_criteria_met:
                result = _clean_policy_result(evaluate_step_policy(
                    **_base_policy_kwargs, resistance_score=None, criteria_met=True,
                ))
                _p1_action = result.get("action")  # update after LLM-confirmed advance
                p1_result = result  # keep p1_result in sync so precedence resolver restores correct action

    _p2_action: str | None = None
    if needs_resistance and not p1_det_fired:
        new_resistance_score = await _score_resistance_via_rules_service(state["message_en"])
        if new_resistance_score is not None:
            p2_result = _clean_policy_result(evaluate_step_policy(
                **_base_policy_kwargs,
                resistance_score=new_resistance_score,
                criteria_met=llm_criteria_met,
            ))
            _p2_action = p2_result.get("action")
            result = p2_result

    if new_resistance_score is not None:
        resistance_history = (resistance_history + [new_resistance_score])[-3:]

    # Cross-phase precedence resolver.
    # Clinical rule: criteria-met advancement beats resistance/engagement holds.
    # A non-safety Phase 2 hold cannot override a Phase 1 advance or complete.
    # Safety holds (validate_only) always win regardless.
    # "Phase 2 wins by returning last" was the implicit bug; this is the explicit rule.
    if (
        _p2_action is not None                              # Phase 2 ran
        and _p1_action in ("advance", "complete")           # Phase 1 cleared criteria
        and _p2_action not in ("advance", "complete")       # Phase 2 is a hold
        and _p2_action not in _SAFETY_HOLD_ACTIONS          # hold is not safety-critical
    ):
        result = p1_result
        _log.info(
            "[skill_executor] precedence: Phase 1 %s overrides Phase 2 %s "
            "(criteria met; non-safety hold discarded) skill=%s step=%s",
            _p1_action, _p2_action, skill_id, step_id,
        )

    crisis_state_update: dict = {}
    if result.get("skill_complete") and skill_id == "post_crisis_check_in":
        crisis_state_update = {"crisis_state": "resolved"}

    # NOTE: psychotic_referral_delivered is set at skill_executor time (skill_complete),
    # not after freeflow_respond delivers the response. If the LLM response fails on
    # the referral turn (and resilience fallback also fails), the referral will not be
    # re-delivered in future turns. This is an accepted tradeoff — clinician review
    # queue entry (severity=medium) will still fire via output_gate, preserving the
    # audit trail. If a no-silencing guarantee is required, this flag must be moved
    # to a post-freeflow_respond hook, which the current graph architecture does not
    # support without a new output_gate specialisation.
    psychotic_referral_update: dict = {}
    if result.get("skill_complete") and skill_id == "psychotic_referral":
        psychotic_referral_update = {"psychotic_referral_delivered": True}

    return {
        "step_instruction":    result["instruction"],
        "executed_step_id":    step_id,
        "active_step_id":      result["next_step_id"],
        "active_skill_id":     None if result.get("skill_complete") else skill_id,
        "rule_fired":          result.get("action") not in ("advance", "complete", "stay", None),
        "prev_step_id":        step_id,   # persists via LangGraph checkpoint; absent from _build_state
        "escalation_triggered": l2,  # advisory stored for audit; None if no L2 this turn
        "resistance_score":    new_resistance_score,
        "resistance_history":  resistance_history,
        "path": state["path"] + ["skill_executor"],
        # CSM-2: explicit per-turn write so stale checkpoint value from prior
        # crisis_response does not persist into the routing decision.
        "re_escalation_within_monitoring": re_escalation_detected,
        **crisis_state_update,
        **psychotic_referral_update,
    }
