"""HR-1 Stage 2 Task 3: the high_risk_response two-step deterministic terminal.

Doc-faithful shape (docs/superpowers/specs/2026-07-16-hr1-stage2-terminal-design.md,
"RESOLVED" section): T1 asks the one §1 distress question, T2 (and, only if the reply
did not parse, one T3 re-ask) branches on the reply to a fixed-copy §3 redirect. Modeled
directly on medical_response.py: full-turn latency from turn_started_at, its OWN
write_session_audit fire-and-forget task (this path bypasses output_gate, the normal
audit-write point), entry-clear of active_skill_id/active_step_id/offered_skill_ids,
-> END. UNLIKE medical_response, this node spans 2-3 turns, so which branch of copy is
returned depends on the persisted hr_terminal_step / hr_escalate_regardless channels
(state.py), not solely on this turn's input.

Pure-deterministic (design doc Requirement 1): no evaluate_completion_criteria, no LLM
call anywhere on this path. Every branch is resolved by hr_distress.parse_distress /
resolve_hr_branch / mania_behavior_underway.

Copy source: each slot (distress question, supportive message, higher/lower redirect,
re-ask) is a DRAFT pool of clinician-ratifiable variants (safety/hr_copy.py), picked
deterministically per (session_id, slot_key) by pick_hr_variant -- still a pure literal
lookup, no runtime randomness, no LLM. See hr_copy.py's module docstring for the
ratification-pending status.

No em dashes (project convention for anything that could reach an LLM prompt or
user-facing string).
"""
import asyncio
import logging
import time

from sage_poc.state import SageState
from sage_poc import config as _cfg
from sage_poc.audit import write_session_audit
from sage_poc.crisis_copy import resolve_crisis_placeholders
from sage_poc.safety.hr_copy import (
    HR_DISTRESS_QUESTION_POOL,
    HR_REASK_POOL,
    HR_REDIRECT_HIGHER_POOL,
    HR_REDIRECT_LOWER_POOL,
    HR_SUPPORTIVE_MESSAGE_POOL,
    pick_hr_variant,
)
from sage_poc.safety.hr_distress import (
    DistressParse,
    mania_behavior_underway,
    parse_distress,
    resolve_hr_branch,
)

_log = logging.getLogger(__name__)


def _first_name(state: SageState) -> str | None:
    """Name-only personalization source (§5): the user's therapeutic_profile, the
    one profile-shaped dict already carried in state. No live write path populates
    first_name into it today, so in practice pick_hr_variant always falls back to the
    name-free pool variants right now; wiring it here is what makes a future profile
    write "just work" without touching this node again."""
    profile = state.get("therapeutic_profile") or {}
    return profile.get("first_name") or None


def _pick(pool: tuple[str, ...], state: SageState, slot_key: str) -> str:
    """Deterministic pool pick (session_id + slot_key), then {{crisis_*}} resolution.
    {{first_name}} is resolved inside pick_hr_variant itself (never picks a name-
    bearing variant when no name is available); {{crisis_*}} resolves the same way as
    every other crisis string in the codebase (crisis_copy.resolve_crisis_placeholders).
    """
    variant = pick_hr_variant(
        pool, state.get("session_id"), slot_key, first_name=_first_name(state),
    )
    return resolve_crisis_placeholders(variant)


def _compose_higher_redirect(state: SageState) -> str:
    """Step 1 redirect, higher-severity branch: a pool-picked lead-in + the SAME UAE
    resource directory the crisis pathway uses, composed via select_crisis_resources()
    (immediate_danger=True -> leads with 999/emergency, matching the doc's "999/ER now"
    framing). Never a literal resource list in this module (single-sourced in config.py).
    """
    lead = _pick(HR_REDIRECT_HIGHER_POOL, state, "redirect_higher")
    resources = _cfg.select_crisis_resources(immediate_danger=True)
    resource_line = "; ".join(
        f"{r['name']}: {r['number']} ({r['hours']})" for r in resources
    )
    return f"{lead} {resource_line}"


def _deliver_branch(
    branch: str, parse: DistressParse, path: list, latency_ms, state: SageState,
) -> dict:
    """Build the terminal-delivery return dict for a resolved "higher"/"lower" branch.
    Shared by the await_distress branch turn and the reask turn (both terminate the
    protocol the same way once a branch is resolved). Clears hr_terminal_step and
    hr_escalate_regardless on every delivery (Finding 1: the mania-behavior-underway
    carry-in is per-protocol-instance, not per-session).

    Sets hr_referral_delivered (Task 4 fix): one-shot marker consumed by
    _route_after_safety's HR ENTRY guard, mirroring Stage 1's
    psychotic_referral_delivered. Without it, clinical_flags' session-lifetime
    persistence re-fires the ENTRY branch on every later turn and re-asks the
    distress question -- this is set only here, on an actual delivery, never on
    the re-ask (mid-protocol, not yet delivered).

    Also sets psychotic_referral_delivered (same value, True): Stage 1's OWN
    independent one-shot guard (_route_after_intent / skill_select.py's
    psychotic_disclosure auto-select) is unconditional on HIGH_RISK_TERMINAL_ENABLED
    and reads that separate flag, not hr_referral_delivered. Closing only the
    _route_after_safety ENTRY branch left this second, parallel entry point
    unguarded: once this Stage 2 delivery routes a later benign turn to "safe",
    it falls through to intent_route, whose Stage 1 check would fire the
    psychotic_referral SKILL all over again on the very next turn (same symptom,
    different node) because psychotic_referral_delivered was never set by this
    path. This turn's Stage 2 delivery IS the referral for the same underlying
    disclosure, so it must satisfy both one-shot guards.
    """
    supportive = _pick(HR_SUPPORTIVE_MESSAGE_POOL, state, "supportive_message")
    if branch == "higher":
        text = f"{supportive} {_compose_higher_redirect(state)}"
    else:
        text = f"{supportive} {_pick(HR_REDIRECT_LOWER_POOL, state, 'redirect_lower')}"

    return {
        "response": text,
        "response_en": text,
        "gate_path": "high_risk",
        "path": path,
        "latency_ms": latency_ms,
        "hr_terminal_step": None,
        "hr_escalate_regardless": False,
        "hr_branch": branch,
        "hr_distress_score": parse.score,
        "hr_referral_delivered": True,
        "psychotic_referral_delivered": True,
    }


def _write_hr_audit(state: SageState, update: dict, path: list, latency_ms) -> None:
    """Own audit row (medical_response.py precedent): this path bypasses output_gate,
    the normal audit-write point, so without this the turn is unrecorded. Fire-and-
    forget, mirroring crisis_response/medical_response's task pattern. Carries
    hr_distress_score / hr_branch when the delivery resolved a branch this turn."""
    audit_task = asyncio.create_task(write_session_audit({
        **state,
        **update,
        "path": path,
        "gate_path": "high_risk",
        "latency_ms": latency_ms,
    }))
    audit_task.add_done_callback(
        lambda tk: _log.warning("[high_risk_response] session audit error: %s", tk.exception())
        if not tk.cancelled() and tk.exception() else None
    )


async def high_risk_response_node(state: SageState) -> dict:
    path = state["path"] + ["high_risk_response"]
    # Full-turn latency, not node-local (medical_response.py precedent): this path
    # also bypasses output_gate (the normal latency-stamp point).
    _tsa = state.get("turn_started_at")
    latency_ms = (
        int((time.monotonic() - _tsa) * 1000) if _tsa is not None else state.get("latency_ms")
    )

    step = state.get("hr_terminal_step")
    message_en = state.get("message_en", "")

    if step is None:
        # T1 entry: ask the one §1 distress question. Compute the independent
        # behavior-underway evidence (Finding 1) NOW, from the message that routed the
        # user here, and persist it across the two-turn protocol so a later low numeric
        # score can never mask it.
        escalate_regardless = mania_behavior_underway(message_en)
        question = _pick(HR_DISTRESS_QUESTION_POOL, state, "distress_question")
        update = {
            "response": question,
            "response_en": question,
            "gate_path": "high_risk",
            "path": path,
            "latency_ms": latency_ms,
            "hr_terminal_step": "await_distress",
            "hr_escalate_regardless": escalate_regardless,
            # medical_response.py lesson (3rd appearance, now structural): clear any
            # in-progress skill on entry so it cannot resume next turn.
            "active_skill_id": None,
            "active_step_id": None,
            "offered_skill_ids": None,
        }
        _write_hr_audit(state, update, path, latency_ms)
        return update

    if step == "await_distress":
        parse = parse_distress(message_en)
        branch = resolve_hr_branch(
            parse, is_reask=False,
            escalate_regardless=state.get("hr_escalate_regardless", False),
        )
        if branch == "reask":
            reask_text = _pick(HR_REASK_POOL, state, "reask")
            update = {
                "response": reask_text,
                "response_en": reask_text,
                "gate_path": "high_risk",
                "path": path,
                "latency_ms": latency_ms,
                "hr_terminal_step": "reask",
                # hr_escalate_regardless is NOT cleared here: the carry-in evidence
                # must still absorb the T3 fail-to-higher default.
            }
            _write_hr_audit(state, update, path, latency_ms)
            return update

        update = _deliver_branch(branch, parse, path, latency_ms, state)
        _write_hr_audit(state, update, path, latency_ms)
        return update

    # step == "reask" (or any unexpected value): T3, the one re-ask's reply.
    # resolve_hr_branch(is_reask=True) never returns "reask" -- a third ask is
    # unrepresentable by construction (scope guard). Any non-parse here fails to
    # the higher-severity branch (fail-to-higher default), never to "lower".
    parse = parse_distress(message_en)
    branch = resolve_hr_branch(
        parse, is_reask=True,
        escalate_regardless=state.get("hr_escalate_regardless", False),
    )
    update = _deliver_branch(branch, parse, path, latency_ms, state)
    _write_hr_audit(state, update, path, latency_ms)
    return update
