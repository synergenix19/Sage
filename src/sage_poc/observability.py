"""Log-only per-stage latency instrumentation for the latency campaign, plus small
fire-and-forget task helpers shared across nodes.

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

import asyncio
import json
import logging
import time
from contextlib import contextmanager
from typing import Coroutine

_log = logging.getLogger("sage.latency")
_task_log = logging.getLogger(__name__)


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


# Fix round 3 (item 3, P2 Task 7a/7b delegation): strong-ref hold for every task spawn_logged
# creates. asyncio's own docs are explicit about the hazard this closes: "the event loop only
# keeps weak references to tasks. A task that isn't referenced elsewhere may get garbage
# collected at any time, even before it's done" -- and several of this helper's call sites
# (the fire-and-forget audit/notify/summary tasks converted in P2 Task 7a) assign the returned
# Task to a local variable whose scope ends when the enclosing node function returns, well
# before the task itself has necessarily completed. The event loop's weak reference alone is
# not a correctness guarantee. This module-level set is the standard idiom recommended by the
# asyncio docs for exactly this shape: hold a strong reference until the task's own
# done-callback discards it, so a task can never be collected mid-flight regardless of what its
# caller does with the returned reference.
_background_tasks: set[asyncio.Task] = set()


def spawn_logged(
    coro: Coroutine,
    label: str,
    *,
    log: logging.Logger | None = None,
    message: str = "[%s] background task error: %s",
) -> asyncio.Task:
    """Fire-and-forget an async coroutine as a background task, logging (never raising)
    if it fails.

    P2 Task 7a (mechanical dedup): before this helper, every audit write, notification,
    and summary-persist call that needed "don't block the served turn, but don't let a
    failure vanish silently either" hand-copied the same three lines --
    `asyncio.create_task(...)` followed by an `add_done_callback` lambda that logs a
    warning when the task raised and wasn't cancelled. Eleven call sites across graph.py
    and the node modules had independently retyped that idiom, which is exactly the kind
    of copy-paste surface that drifts silently (a missing `not t.cancelled()` guard, a
    swapped exception check) on a safety-audit-adjacent code path. One helper means one
    place to get the cancellation/exception handling right.

    Fix round 3 (P2 Task 7 review, ruling M2): `safety/terminal.py`'s `spawn_safety_audit`
    (the SAFETY-EXIT terminal class's own fire-and-forget helper, from a sibling PR that
    landed independently) now DELEGATES to this function instead of reimplementing the same
    idiom a second time -- one idiom, one implementation. It keeps its own distinct log
    message ("[%s] session audit error: %s") via the `message` parameter below, so the three
    SAFETY-EXIT terminals' pinned log text is unchanged even though the task-creation,
    strong-ref, and done-callback machinery is now shared. Every caller that wants the
    default wording never needs to pass `message` at all.

    The callback itself is wrapped so a bad `label` or `log` argument -- or any other
    surprise inside the logging call -- cannot propagate back into the event loop and
    disrupt an unrelated turn. These tasks exist to be forgotten; even the "let me tell
    you it failed" path must not be able to fail loudly.
    """
    task = asyncio.create_task(coro)
    logger = log if log is not None else _task_log

    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    def _on_done(t: asyncio.Task, _label=label, _logger=logger, _message=message) -> None:
        try:
            if t.cancelled():
                return
            exc = t.exception()
            if exc is not None:
                _logger.warning(_message, _label, exc)
        except Exception:  # pragma: no cover - the whole point is this never raises
            pass

    task.add_done_callback(_on_done)
    return task
