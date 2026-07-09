"""The ONLY sink for native-Arabic shadow measurement data. Writes to
shadow_register_eval — a dedicated restricted table isolated from session_audit
(shadow text never touches SageState or the main audit row). Never returns data
into SageState.
"""
from __future__ import annotations

import logging

_log = logging.getLogger(__name__)


def build_shadow_eval_row(
    state: dict,
    payload: dict | None,
    *,
    tool_loop_iterations: int,
    timed_out: bool,
) -> dict:
    """Pure row builder. `payload` is None on a censored (timed-out) observation —
    in that case shadow_arabic_text/prompt_hash/exemplar_version/generation_language/
    gen_latency_ms are all absent, but tool_loop_iterations is still recorded (the
    English-arm tool count is meaningful even when the shadow generation itself
    was censored).
    """
    p = payload or {}
    return {
        "session_id":              state.get("session_id", ""),
        "turn_number":              state.get("turn_number", 0),
        "message_en":               state.get("message_en"),
        "clinical_flags":           state.get("clinical_flags") or [],
        "shadow_arabic_text":       p.get("text"),
        "shadow_prompt_hash":       p.get("prompt_hash"),
        "shadow_exemplar_version":  p.get("exemplar_version"),
        "generation_language":      p.get("generation_language"),
        "shadow_gen_latency_ms":    p.get("gen_latency_ms"),
        "tool_loop_iterations":     tool_loop_iterations,
        "shadow_timed_out":         timed_out,
    }


async def write_shadow_eval_row(
    state: dict,
    payload: dict | None,
    *,
    tool_loop_iterations: int,
    timed_out: bool,
) -> None:
    """Thin insert; fail-open (measurement must never break the served turn).

    Any exception — including a missing/misconfigured Supabase connection — is
    caught and logged as a warning; this function never raises and never
    returns data usable by the caller (return is always None).
    """
    try:
        row = build_shadow_eval_row(
            state, payload,
            tool_loop_iterations=tool_loop_iterations,
            timed_out=timed_out,
        )
        from sage_poc.audit import _supabase_insert  # reuse the project's REST insert helper  # noqa: PLC0415
        await _supabase_insert("shadow_register_eval", row)
    except Exception as exc:
        _log.warning("[shadow_eval] write failed (fail-open): %s", exc)
