"""D1 screen terminal (#338): emit the SIGNED contraindication-screen question -> END, bypassing
output_gate. Mirrors medical_response's terminal pattern (own audit, full-turn latency), with ONE
deliberate difference: it PRESERVES the per-session hold (screen_pending, screen_held_skill) so the next
turn is recognised as the answer and the held skill can resume. The served text is SCREEN_QUESTION_EN
verbatim (the manifest-pinned, clinician-confirmed bytes) — no LLM rendering (that is a separately-gated
future increment)."""
import asyncio
import logging
import time

from sage_poc.state import SageState
from sage_poc.audit import write_session_audit

_log = logging.getLogger(__name__)


async def screen_response_node(state: SageState) -> dict:
    # The served bytes ARE the signed question already resolved in skill_select (screen_question_text);
    # fall back to nothing servable only if it is somehow absent (fail-safe: never invent copy).
    text = state.get("screen_question_text") or ""
    path = state["path"] + ["screen_response"]
    _tsa = state.get("turn_started_at")
    latency_ms = (
        int((time.monotonic() - _tsa) * 1000) if _tsa is not None else state.get("latency_ms")
    )

    # Own audit (output_gate is bypassed on this terminal, like medical_response). Records screen_asked so the
    # contraindication-decision trail is present (#160 alert-or-fail; PDPL). Fire-and-forget, loud on error.
    _audit_task = asyncio.create_task(write_session_audit({
        **state,
        "path": path,
        "gate_path": "screen",
        "screen_asked": True,
        "latency_ms": latency_ms,
    }))
    _audit_task.add_done_callback(
        lambda tk: _log.warning("[screen_response] session audit error: %s", tk.exception())
        if not tk.cancelled() and tk.exception() else None
    )

    return {
        "response": text,
        "response_en": text,
        "gate_path": "screen",
        "path": path,
        "latency_ms": latency_ms,
        "screen_asked": True,
        # DELIBERATELY PRESERVED (unlike medical_response's active-skill clear): the hold must survive to the
        # answer turn. active_skill_id stays None (the question is this turn's whole output); the held skill
        # id and screen_pending persist via the checkpointer so next turn resumes/resolves.
        "active_skill_id": None,
        "active_step_id": None,
        "offered_skill_ids": None,
        "screen_pending": True,
        "screen_held_skill": state.get("screen_held_skill"),
    }
