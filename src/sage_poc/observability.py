"""Log-only per-stage latency instrumentation for the latency campaign.

Deliberately log-only (no DB / no schema change): two of the campaign's stages — the S3
crisis encode and the skill_select embedding — sit on or beside the Layer 1 safety path,
where a log emit is behaviour-change-zero but a schema write near that path is a larger
surface to reason about. The campaign needs before/after deltas on a handful of stages,
which `grep`-over-structured-log-lines gives without queryability.

Each line carries enough correlation to JOIN across stages and SLICE the two test shapes:
- `session_id` + `turn`  → join a turn's stages together
- `lang`                 → separate EN from AR (AR pays the gate translate)
- cold-vs-warm is a HARNESS-side label per session (first post-restart call = cold), joined
  back via session_id — the server cannot reliably self-classify cold without extra state.

Emitted under logger "sage.latency" at INFO. Grep: `event":"stage_latency"`.
"""
from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager

_log = logging.getLogger("sage.latency")


def log_stage_latency(
    stage: str,
    ms: int,
    *,
    session_id: str | None = None,
    turn: int | None = None,
    lang: str | None = None,
) -> None:
    """Emit one structured stage-latency line. Never raises (observability must not break a turn)."""
    try:
        _log.info(json.dumps({
            "event": "stage_latency",
            "stage": stage,
            "ms": ms,
            "session_id": session_id,
            "turn": turn,
            "lang": lang,
        }))
    except Exception:  # pragma: no cover - observability must never break the request
        pass


@contextmanager
def stage_timer(
    stage: str,
    *,
    session_id: str | None = None,
    turn: int | None = None,
    lang: str | None = None,
):
    """Context manager that times the wrapped block and logs it on exit (even on exception)."""
    start = time.monotonic()
    try:
        yield
    finally:
        log_stage_latency(
            stage,
            int((time.monotonic() - start) * 1000),
            session_id=session_id,
            turn=turn,
            lang=lang,
        )
