"""Shared plumbing for the SAFETY-EXIT terminal class: medical_response, screen_response,
high_risk_response (and, on a separate future commit gated on #490, derealization_response
once that Vee-draft file is resolved -- it is NOT touched by this module or its adopters).

Each of these nodes bypasses output_gate -- the normal latency-stamp and audit-write point
-- so each must compute its own full-turn latency and write its own session-audit row. This
module factors out the two identical pieces (the latency snippet and the fire-and-forget
audit-task idiom) so a future change to either happens once, at one call site.

Deliberately self-contained: a sibling PR (Task 7a) is separately deduping the same
fire-and-forget "asyncio.create_task(...) + add_done_callback warn-on-error" idiom into
observability.spawn_logged, but that PR is unmerged and independent of this one. This module
does not import from it -- spawn_safety_audit below reproduces the existing idiom
byte-for-behavior on its own, so this PR stands alone.
"""
import asyncio
import logging
import time

from sage_poc.state import SageState
from sage_poc.audit import write_session_audit


def turn_latency_ms(state: SageState) -> int:
    """Full-turn latency, not node-local: every SAFETY-EXIT terminal bypasses output_gate
    (the normal latency-stamp point), so latency must be computed from the turn start
    itself, not re-stamped from a near-zero node-entry timer. Falls back to
    state["latency_ms"] if turn_started_at is absent -- identical to the snippet this
    factors out of medical_response.py, screen_response.py, and high_risk_response.py."""
    _tsa = state.get("turn_started_at")
    return (
        int((time.monotonic() - _tsa) * 1000) if _tsa is not None else state.get("latency_ms")
    )


def spawn_safety_audit(
    state: SageState,
    payload_extra: dict,
    log: logging.Logger,
    log_prefix: str,
) -> "asyncio.Task":
    """Fire-and-forget write_session_audit(...) task, with the same add_done_callback
    warn-on-error idiom used at every SAFETY-EXIT call site today. write_session_audit
    takes the FULL state and builds the row internally via _build_session_audit_row
    (reads fields with .get()); payload_extra is layered over state the same way each
    site already builds its dict ({**state, "path": ..., "gate_path": ..., ...}) -- this
    function only factors out the container code around the call, never the audit call's
    payload semantics."""
    audit_task = asyncio.create_task(write_session_audit({**state, **payload_extra}))
    audit_task.add_done_callback(
        lambda tk: log.warning("[%s] session audit error: %s", log_prefix, tk.exception())
        if not tk.cancelled() and tk.exception() else None
    )
    return audit_task


def safety_exit_result(
    state: SageState,
    *,
    path: list,
    gate_path: str,
    response: str,
    latency_ms,
    log: logging.Logger,
    log_prefix: str,
    audit_extra: dict | None = None,
    extra: dict | None = None,
) -> dict:
    """Build the SAFETY-EXIT terminal's shared shape for a single-shot terminal node
    (medical_response, screen_response): the fire-and-forget audit task, plus the node's
    RETURN dict with the active-skill-clear trio (active_skill_id, active_step_id,
    offered_skill_ids -> None) as the DEFAULT. This mirrors medical_response's behavior,
    the plain member of the class.

    A node with a deliberate additional behavior -- screen_response's
    screen_pending/screen_held_skill hold-preservation -- passes `extra`, a dict merged
    on TOP of the default result after the clears are applied. This keeps the override
    explicit at the call site, never a silent behavior difference baked into this helper.
    `audit_extra` is the analogous override for the audit row's payload (e.g.
    medical_flags, screen_asked)."""
    audit_payload = {
        "path": path,
        "gate_path": gate_path,
        "latency_ms": latency_ms,
        **(audit_extra or {}),
    }
    spawn_safety_audit(state, audit_payload, log, log_prefix)

    result = {
        "response": response,
        "response_en": response,
        "gate_path": gate_path,
        "path": path,
        "latency_ms": latency_ms,
        "active_skill_id": None,
        "active_step_id": None,
        "offered_skill_ids": None,
    }
    if extra:
        result.update(extra)
    return result
