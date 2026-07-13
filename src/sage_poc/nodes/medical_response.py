"""B1 medical red-flag terminal: static referral text -> END, bypassing output_gate.
UNLIKE crisis_response's historical gap, it writes its OWN session audit record — a
medical-emergency turn is the most consequential the system emits and must be fully
traceable (path, flags, latency). Interim target per doc Section 6 (Q1-terminal stub)."""
import asyncio
import logging
import time

from sage_poc.state import SageState
from sage_poc import config as _cfg
from sage_poc.audit import write_session_audit

_log = logging.getLogger(__name__)


async def medical_response_node(state: SageState) -> dict:
    _t0 = time.monotonic()
    text = _cfg.MEDICAL_REFERRAL_TEXT
    medical_flags = state.get("medical_flags", [])
    path = state["path"] + ["medical_response"]
    latency_ms = int((time.monotonic() - _t0) * 1000)

    # Explicit audit: output_gate (the normal audit-write point) is bypassed on this
    # path, so without this the single most consequential turn is unrecorded. Fire-and-
    # forget, mirroring crisis_response's task pattern (graph.py:70) — but here it is
    # NOT optional (Defect 3). write_session_audit takes the FULL state and builds the
    # row internally via _build_session_audit_row (reads fields with .get()).
    _audit_task = asyncio.create_task(write_session_audit({
        **state,
        "path": path,
        "gate_path": "medical",
        "medical_flags": medical_flags,
        "latency_ms": latency_ms,
    }))
    _audit_task.add_done_callback(
        lambda tk: _log.warning("[medical_response] session audit error: %s", tk.exception())
        if not tk.cancelled() and tk.exception() else None
    )

    return {
        "response": text,
        "response_en": text,
        "gate_path": "medical",
        "medical_flags": medical_flags,
        "path": path,
        "latency_ms": latency_ms,
    }
