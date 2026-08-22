"""Shared plumbing for the SAFETY-EXIT terminal class: medical_response, screen_response,
high_risk_response (and, on a separate future commit gated on #490, derealization_response
once that Vee-draft file is resolved -- it is NOT touched by this module or its adopters).

Each of these nodes bypasses output_gate -- the normal latency-stamp and audit-write point
-- so each must compute its own full-turn latency and write its own session-audit row. This
module factors out the two identical pieces (the latency snippet and the fire-and-forget
audit-task idiom) so a future change to either happens once, at one call site.

Fix round 3 (P2 Task 7 review, ruling M2 -- one idiom, one implementation): `spawn_safety_audit`
below originally reimplemented the fire-and-forget "asyncio.create_task(...) + add_done_callback
warn-on-error" idiom byte-for-behavior on its own, because the sibling PR consolidating that same
idiom into `observability.spawn_logged` (P2 Task 7a) was unmerged and independent at the time.
Now that both have landed, `spawn_safety_audit` DELEGATES to `spawn_logged` instead of carrying a
second copy of the same task-creation/strong-ref/done-callback machinery -- it keeps its own name
and its own distinct log text ("[%s] session audit error: %s", via `spawn_logged`'s `message`
parameter) so nothing about the three SAFETY-EXIT terminals' observable behavior changes, but the
underlying mechanics (including `spawn_logged`'s strong-ref task-set, which now protects these
terminal audit tasks too) live in exactly one place.
"""
import asyncio
import logging
import time

from sage_poc.observability import spawn_logged
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
    """Fire-and-forget write_session_audit(...) task for the SAFETY-EXIT terminal class.
    write_session_audit takes the FULL state and builds the row internally via
    _build_session_audit_row (reads fields with .get()); payload_extra is layered over
    state the same way each site already builds its dict ({**state, "path": ...,
    "gate_path": ..., ...}) -- this function only factors out the container code around
    the call, never the audit call's payload semantics.

    Fix round 3 (ruling M2): delegates to observability.spawn_logged for the actual
    task-creation/strong-ref/done-callback machinery -- one idiom, one implementation --
    while keeping this function's own name and its own distinct log text ("[%s] session
    audit error: %s", not spawn_logged's default "[%s] background task error: %s") via
    spawn_logged's `message` parameter. Every SAFETY-EXIT terminal's pinned log shape is
    unchanged; spawn_logged's strong-ref task-set now also protects these audit tasks."""
    return spawn_logged(
        write_session_audit({**state, **payload_extra}),
        log_prefix,
        log=log,
        message="[%s] session audit error: %s",
    )


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
