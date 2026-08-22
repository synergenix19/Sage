"""B1 medical red-flag terminal: static referral text -> END, bypassing output_gate.
UNLIKE crisis_response's historical gap, it writes its OWN session audit record — a
medical-emergency turn is the most consequential the system emits and must be fully
traceable (path, flags, latency). Interim target per doc Section 6 (Q1-terminal stub)."""
import logging

from sage_poc.state import SageState
from sage_poc import config as _cfg
from sage_poc.safety.terminal import safety_exit_result, turn_latency_ms

_log = logging.getLogger(__name__)


async def medical_response_node(state: SageState) -> dict:
    text = _cfg.MEDICAL_REFERRAL_TEXT
    medical_flags = state.get("medical_flags", [])
    path = state["path"] + ["medical_response"]
    # Full-turn latency, not node-local: mirror _crisis_response_node (graph.py:70,77) —
    # this path also bypasses output_gate (the normal latency-stamp point), so it must
    # compute from the turn start itself, not re-stamp a near-zero node-entry timer.
    latency_ms = turn_latency_ms(state)

    # Explicit audit: output_gate (the normal audit-write point) is bypassed on this
    # path, so without this the single most consequential turn is unrecorded. Fire-and-
    # forget, mirroring crisis_response's task pattern (graph.py:70) — but here it is
    # NOT optional (Defect 3). write_session_audit takes the FULL state and builds the
    # row internally via _build_session_audit_row (reads fields with .get()).
    #
    # Clearing the active-skill trio here mirrors crisis_response (graph.py:137-139):
    # the checkpointer-persisted active-skill fields are cleared so a coping skill in
    # progress cannot resume next turn right after a medical-emergency referral. This
    # is safety_exit_result's DEFAULT behavior, so no override is passed.
    return safety_exit_result(
        state,
        path=path,
        gate_path="medical",
        response=text,
        latency_ms=latency_ms,
        log=_log,
        log_prefix="medical_response",
        audit_extra={"medical_flags": medical_flags},
        extra={"medical_flags": medical_flags},
    )
