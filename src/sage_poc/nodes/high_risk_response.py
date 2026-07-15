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

No em dashes (project convention for anything that could reach an LLM prompt or
user-facing string).
"""
import asyncio
import logging
import time

from sage_poc.state import SageState
from sage_poc import config as _cfg
from sage_poc.audit import write_session_audit
from sage_poc.safety.hr_distress import (
    DistressParse,
    mania_behavior_underway,
    parse_distress,
    resolve_hr_branch,
)

_log = logging.getLogger(__name__)


def _compose_higher_redirect() -> str:
    """Step 1 redirect, higher-severity branch: the fixed lead-in + the SAME UAE
    resource directory the crisis pathway uses, composed via select_crisis_resources()
    (immediate_danger=True -> leads with 999/emergency, matching the doc's "999/ER now"
    framing). Never a literal resource list in this module (single-sourced in config.py).
    """
    resources = _cfg.select_crisis_resources(immediate_danger=True)
    resource_line = "; ".join(
        f"{r['name']}: {r['number']} ({r['hours']})" for r in resources
    )
    return f"{_cfg.HR_REDIRECT_HIGHER_LEAD} {resource_line}"


def _deliver_branch(branch: str, parse: DistressParse, path: list, latency_ms) -> dict:
    """Build the terminal-delivery return dict for a resolved "higher"/"lower" branch.
    Shared by the await_distress branch turn and the reask turn (both terminate the
    protocol the same way once a branch is resolved). Clears hr_terminal_step and
    hr_escalate_regardless on every delivery (Finding 1: the mania-behavior-underway
    carry-in is per-protocol-instance, not per-session).
    """
    if branch == "higher":
        text = f"{_cfg.HR_SUPPORTIVE_MESSAGE} {_compose_higher_redirect()}"
    else:
        text = f"{_cfg.HR_SUPPORTIVE_MESSAGE} {_cfg.HR_REDIRECT_LOWER}"

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
        update = {
            "response": _cfg.HR_DISTRESS_QUESTION,
            "response_en": _cfg.HR_DISTRESS_QUESTION,
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
            update = {
                "response": _cfg.HR_REASK,
                "response_en": _cfg.HR_REASK,
                "gate_path": "high_risk",
                "path": path,
                "latency_ms": latency_ms,
                "hr_terminal_step": "reask",
                # hr_escalate_regardless is NOT cleared here: the carry-in evidence
                # must still absorb the T3 fail-to-higher default.
            }
            _write_hr_audit(state, update, path, latency_ms)
            return update

        update = _deliver_branch(branch, parse, path, latency_ms)
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
    update = _deliver_branch(branch, parse, path, latency_ms)
    _write_hr_audit(state, update, path, latency_ms)
    return update
