"""§1c Part A — anxiety-track derealization terminal: ONE deterministic signed referral -> END,
bypassing intent_route AND output_gate (the LLM never decides this turn — Cardinal Rule 4).

The 4th member of the SAFETY-EXIT class (crisis_response, medical_response, high_risk_response,
derealization_response). Routed from _route_after_safety at rank 4 (crisis > medical > hr >
derealization) and gated by DEREALIZATION_DETECTION_ENABLED, so the whole path is inert until the
copy is Vee-signed + flipped. Mirrors medical_response: static templated text, writes its OWN
session audit (output_gate — the normal audit-write point — is bypassed), clears active-skill fields
so an in-progress coping skill cannot resume after the referral, and sets a one-shot delivered guard.
"""
import asyncio
import logging
import time

from sage_poc.state import SageState
from sage_poc.audit import write_session_audit
from sage_poc.safety.derealization_copy import derealization_referral_text

_log = logging.getLogger(__name__)


async def derealization_response_node(state: SageState) -> dict:
    lang = state.get("detected_language", "en")
    text = derealization_referral_text(lang)
    path = state["path"] + ["derealization_response"]

    # Full-turn latency, not node-local: this path bypasses output_gate (the normal latency-stamp
    # point), so compute from turn start (mirror medical_response / _crisis_response_node).
    _tsa = state.get("turn_started_at")
    latency_ms = (
        int((time.monotonic() - _tsa) * 1000) if _tsa is not None else state.get("latency_ms")
    )

    # Explicit audit: output_gate (normal audit-write point) is bypassed here, so without this the
    # referral turn is unrecorded. Fire-and-forget, mirroring medical_response.
    _audit_task = asyncio.create_task(write_session_audit({
        **state,
        "path": path,
        "gate_path": "derealization",
        "derealization_referral_delivered": True,
        "latency_ms": latency_ms,
    }))
    _audit_task.add_done_callback(
        lambda tk: _log.warning("[derealization_response] session audit error: %s", tk.exception())
        if not tk.cancelled() and tk.exception() else None
    )

    return {
        "response": text,
        "response_en": text,
        "gate_path": "derealization",
        "derealization_referral_delivered": True,
        "path": path,
        "latency_ms": latency_ms,
        # Mirror medical/crisis: clear checkpointer-persisted active-skill fields so a coping skill
        # in progress cannot resume the turn after an anxiety-track referral is delivered.
        "active_skill_id": None,
        "active_step_id": None,
        "offered_skill_ids": None,
    }
