"""D1 screen terminal (#338): emit the SIGNED contraindication-screen question -> END, bypassing
output_gate. Mirrors medical_response's terminal pattern (own audit, full-turn latency), with ONE
deliberate difference: it PRESERVES the per-session hold (screen_pending, screen_held_skill) so the next
turn is recognised as the answer and the held skill can resume. The served text is SCREEN_QUESTION_EN
verbatim (the manifest-pinned, clinician-confirmed bytes) — no LLM rendering (that is a separately-gated
future increment)."""
import logging

from sage_poc.state import SageState
from sage_poc.safety.terminal import safety_exit_result, turn_latency_ms

_log = logging.getLogger(__name__)


async def screen_response_node(state: SageState) -> dict:
    # The served bytes ARE the signed question already resolved in skill_select (screen_question_text);
    # fall back to nothing servable only if it is somehow absent (fail-safe: never invent copy).
    text = state.get("screen_question_text") or ""
    path = state["path"] + ["screen_response"]
    latency_ms = turn_latency_ms(state)

    # Own audit (output_gate is bypassed on this terminal, like medical_response). Records screen_asked so the
    # contraindication-decision trail is present (#160 alert-or-fail; PDPL). Fire-and-forget, loud on error.
    #
    # DELIBERATE OVERRIDE (unlike medical_response's plain active-skill clear): the D1 hold must survive to the
    # answer turn. active_skill_id stays None (the question is this turn's whole output) via safety_exit_result's
    # default; the held skill id and screen_pending are passed as an explicit `extra` override, merged on top of
    # the defaults, so they persist via the checkpointer and next turn resumes/resolves.
    #
    # PRESERVE, never force: D1's apply_screen_at_route sets screen_pending=True itself at serve time, so D1
    # flows arrive here True and stay True (unchanged). EMR screens (2026-08-12) share this terminal but carry
    # their OWN pending channel (modality_screen_pending); forcing True here armed D1's answer machinery on an
    # EMR duration answer — the crossed-wires defect the screen-completion family caught.
    return safety_exit_result(
        state,
        path=path,
        gate_path="screen",
        response=text,
        latency_ms=latency_ms,
        log=_log,
        log_prefix="screen_response",
        audit_extra={"screen_asked": True},
        extra={
            "screen_asked": True,
            "screen_pending": bool(state.get("screen_pending")),
            "screen_held_skill": state.get("screen_held_skill"),
        },
    )
