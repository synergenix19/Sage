"""LLM Resilience Layer — timeout, retry, circuit breaker, warm fallback."""
from __future__ import annotations

import asyncio
import json
import logging
import pathlib
import random
import time
from collections.abc import AsyncGenerator, AsyncIterator, Callable
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# ── Configuration (migrates to config store in Full Build) ────────────────────

LLM_TIMEOUT_SECONDS: float = 30.0
LLM_MAX_RETRIES: int = 2
LLM_BACKOFF_BASE: float = 1.0
LLM_BACKOFF_MAX: float = 8.0
EMBEDDING_TIMEOUT_SECONDS: float = 10.0
CIRCUIT_BREAKER_THRESHOLD: int = 5
CIRCUIT_BREAKER_RESET_SECONDS: float = 60.0

# ── Error classification ──────────────────────────────────────────────────────

_RETRYABLE_HTTP_CODES = {429, 502, 503, 504}


def _is_retryable(exc: Exception) -> bool:
    try:
        import httpx
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code in _RETRYABLE_HTTP_CODES
        if isinstance(exc, (httpx.ConnectError, httpx.RemoteProtocolError)):
            return True
    except ImportError:
        pass
    return isinstance(exc, (asyncio.TimeoutError, TimeoutError, OSError))


# ── Fallback response loader ──────────────────────────────────────────────────

_FALLBACKS_PATH = pathlib.Path(__file__).parent / "fallbacks.json"
_fallbacks_cache: list[dict] | None = None


def _load_fallbacks() -> list[dict]:
    global _fallbacks_cache
    if _fallbacks_cache is None:
        _fallbacks_cache = json.loads(_FALLBACKS_PATH.read_text())
    return _fallbacks_cache


def get_fallback_response(node: str, language: str = "en") -> str:
    """Return a pre-authored fallback response for the given node and language.

    Precedence (most to least specific), resolved as a single lookup table:
      1. (node, language)      exact match
      2. (node, "en")          node match, English
      3. ("default", language) generic, requested language
      4. ("default", "en")     generic, English
    fallbacks.json carries no duplicate (node, language) pairs, so a dict built
    from it is equivalent to the first list match at each tier (verified by
    test_fallbacks_json_valid's uniqueness expectations).
    """
    by_key = {(e["node"], e["language"]): e["response"] for e in _load_fallbacks()}
    for key in ((node, language), (node, "en"), ("default", language), ("default", "en")):
        if key in by_key:
            return by_key[key]
    return "I'm here with you. Please give me just a moment."


# ── Circuit breaker ───────────────────────────────────────────────────────────

_circuit_state: dict[str, dict] = {}


def _circuit_key_from_model(model_name: str, base_url: str) -> str:
    return f"{base_url}/{model_name}"


def _is_open(key: str) -> bool:
    s = _circuit_state.get(key)
    if s is None or s.get("state") != "open":
        return False
    if datetime.utcnow() >= s["reset_at"]:
        s["state"] = "closed"
        s["consecutive_failures"] = 0
        logger.info('{"event": "circuit_breaker_reset", "endpoint": "%s"}', key)
        return False
    return True


def _record_success(key: str) -> None:
    s = _circuit_state.setdefault(key, {})
    s["consecutive_failures"] = 0
    s["state"] = "closed"


def _record_failure(key: str) -> None:
    s = _circuit_state.setdefault(
        key, {"consecutive_failures": 0, "state": "closed"}
    )
    s["consecutive_failures"] = s.get("consecutive_failures", 0) + 1
    if (
        s["consecutive_failures"] >= CIRCUIT_BREAKER_THRESHOLD
        and s.get("state") != "open"
    ):
        s["state"] = "open"
        s["reset_at"] = datetime.utcnow() + timedelta(
            seconds=CIRCUIT_BREAKER_RESET_SECONDS
        )
        logger.warning(
            '{"event": "circuit_breaker_tripped", "endpoint": "%s", '
            '"consecutive_failures": %d}',
            key,
            s["consecutive_failures"],
        )


# ── Backoff ───────────────────────────────────────────────────────────────────

def _backoff(attempt: int) -> float:
    delay = min(LLM_BACKOFF_BASE * (2**attempt), LLM_BACKOFF_MAX)
    jitter = random.uniform(-0.2, 0.2) * delay
    return max(0.0, delay + jitter)


# ── Internal single-attempt invoke ───────────────────────────────────────────

async def _invoke_once(
    llm: Any,
    messages: list[dict],
    node: str,
    *,
    is_fallback: bool = False,
    meta_out: dict | None = None,
    log: bool = True,
) -> str:
    """Single timeout-guarded llm.ainvoke() call, shared by every call site that needs
    exactly one request/response round trip (the warm-fallback LLM at both of
    resilient_invoke's fallback points, and — via `log=False` — resilient_invoke's own
    per-attempt primary call, which logs its OWN differently-shaped `llm_call` line
    around this instead; see resilient_invoke and the log-event baseline in
    tests/test_resilience.py).
    """
    response_msg = await asyncio.wait_for(
        llm.ainvoke(messages), timeout=LLM_TIMEOUT_SECONDS
    )
    if meta_out is not None:
        try:
            meta_out.update(getattr(response_msg, "response_metadata", None) or {})
        except Exception:  # metadata capture must never fail the call
            pass
    if log:
        logger.info(
            '{"event": "llm_call", "node": "%s", "model": "%s", "is_fallback": %s, "status": "success"}',
            node,
            getattr(llm, "model_name", "unknown"),
            str(is_fallback).lower(),
        )
    return response_msg.content.strip()


async def _try_fallback(
    fallback_llm: Any | None,
    messages: list[dict],
    node: str,
    meta_out: dict | None,
) -> str | None:
    """Attempt the warm-fallback LLM once. Returns its response on success, or None
    when there is no fallback_llm configured or it also raised — logging
    llm_invoke_fallback_failed in the latter case. Shared by resilient_invoke's two
    fallback call sites (breaker-open and exhausted-retries) so both get the same
    failure visibility; previously only the exhausted-retries site logged this event
    (Task 6 symmetry fix — the one new emission in this refactor)."""
    if fallback_llm is None:
        return None
    try:
        return await _invoke_once(fallback_llm, messages, node, is_fallback=True, meta_out=meta_out)
    except Exception as fb_exc:
        logger.error(
            '{"event": "llm_invoke_fallback_failed", "node": "%s", "error_type": "%s"}',
            node,
            type(fb_exc).__name__,
        )
        return None


# ── Shared attempt/backoff/circuit-breaker loop ──────────────────────────────

class _NonRetryable(Exception):
    """Raised by _attempt_loop when call() fails with a non-retryable error."""

    def __init__(self, exc: Exception, attempt: int) -> None:
        super().__init__(str(exc))
        self.exc = exc
        self.attempt = attempt  # zero-based


class _Exhausted(Exception):
    """Raised by _attempt_loop once every attempt has failed with a retryable error."""


async def _attempt_loop(
    call: Callable[[], AsyncIterator[Any]],
    *,
    key: str,
    max_retries: int,
    on_retry: Callable[[int, float], None] | None = None,
    attempt_out: dict[str, int] | None = None,
) -> AsyncGenerator[Any, None]:
    """Attempt/backoff/circuit-breaker loop shared by all three public wrappers.

    `call()` returns a FRESH async generator on every invocation (called once per
    attempt); every item it yields is re-yielded live to our caller. This covers both
    call shapes in this module: resilient_invoke/resilient_message_invoke's call()
    yields exactly one item (the response), resilient_stream's call() yields one item
    per chunk — so a single loop serves single-response and streaming wrappers alike,
    including retrying the WHOLE per-attempt body (not just the first item) on
    failure, matching pre-refactor per-wrapper behavior exactly.

    On natural completion (call()'s generator exhausts without raising), circuit
    breaker success is recorded and this generator returns normally. On a retryable
    failure, breaker failure is recorded, backoff is computed and (if attempts
    remain) `on_retry(attempt, backoff)` fires before sleeping and starting a brand
    new attempt. A non-retryable failure raises _NonRetryable(exc, attempt)
    immediately; exhausting every attempt on retryable failures raises _Exhausted().

    Deliberately owns none of the logging: each wrapper supplies its own
    success/retry/exhaustion log SHAPE (they differ per wrapper — see the log-event
    baseline in tests/test_resilience.py) via `on_retry` and by inspecting what this
    generator yielded / which exception it raised. `attempt_out` (if given) is set
    in place to {"attempt": N} — the zero-based attempt index that succeeded — since
    the number of items call() yields is unrelated to which attempt succeeded (a
    single-response wrapper yields exactly one item no matter how many attempts it
    took; a failed attempt yields nothing at all).
    """
    for attempt in range(max_retries + 1):
        try:
            async for item in call():
                yield item
            _record_success(key)
            if attempt_out is not None:
                attempt_out["attempt"] = attempt
            return
        except Exception as exc:
            if not _is_retryable(exc):
                raise _NonRetryable(exc, attempt) from exc
            _record_failure(key)
            if attempt < max_retries:
                backoff = _backoff(attempt)
                if on_retry is not None:
                    on_retry(attempt, backoff)
                await asyncio.sleep(backoff)
    raise _Exhausted()


# ── resilient_invoke ──────────────────────────────────────────────────────────

async def resilient_invoke(
    llm: Any,
    messages: list[dict],
    *,
    node: str,
    language: str = "en",
    fallback_llm: Any | None = None,
    meta_out: dict | None = None,
) -> str:
    """Call llm.ainvoke() with timeout, retry, circuit breaker, and fallback.

    meta_out (optional, backward-compatible): a caller-supplied dict populated with the
    successful response's `response_metadata` — primary or the (equally pinned) fallback
    LLM (classifier provenance audit, SAGE_AUDIT_CLASSIFIER_PROVENANCE). Left untouched
    when the STATIC fallback copy is served (no LLM call succeeded), so an empty dict
    signals "no LLM metadata captured". Never affects control flow.
    """
    key = _circuit_key_from_model(
        getattr(llm, "model_name", "unknown"),
        getattr(llm, "openai_api_base", ""),
    )

    if _is_open(key):
        logger.warning(
            '{"event": "circuit_breaker_short_circuit", "node": "%s", '
            '"circuit_breaker_state": "open"}',
            node,
        )
        result = await _try_fallback(fallback_llm, messages, node, meta_out)
        if result is not None:
            return result
        return get_fallback_response(node, language)

    async def _call() -> AsyncGenerator[str, None]:
        # log=False: the shared success shape below (attempt/latency_ms/timeout_ms/
        # circuit_breaker_state) differs from _invoke_once's own is_fallback shape,
        # so this attempt logs itself once _attempt_loop confirms success.
        yield await _invoke_once(llm, messages, node, is_fallback=False, meta_out=meta_out, log=False)

    def _on_retry(attempt: int, backoff: float) -> None:
        logger.warning(
            '{"event": "llm_call_retrying", "node": "%s", "attempt": %d, "backoff_s": %.2f}',
            node,
            attempt + 1,
            backoff,
        )

    start = time.monotonic()
    attempt_out: dict[str, int] = {}
    content: str | None = None
    try:
        async for item in _attempt_loop(
            _call, key=key, max_retries=LLM_MAX_RETRIES, on_retry=_on_retry,
            attempt_out=attempt_out,
        ):
            content = item
    except _NonRetryable as nr:
        logger.error(
            '{"event": "llm_call_failed", "node": "%s", "attempt": %d, '
            '"error_type": "non_retryable", "fallback_used": "fallback_response"}',
            node,
            nr.attempt + 1,
        )
        return get_fallback_response(node, language)
    except _Exhausted:
        result = await _try_fallback(fallback_llm, messages, node, meta_out)
        if result is not None:
            return result
        logger.error(
            '{"event": "llm_call_failed", "node": "%s", "retry_count": %d, '
            '"fallback_used": "fallback_response"}',
            node,
            LLM_MAX_RETRIES,
        )
        return get_fallback_response(node, language)

    latency_ms = int((time.monotonic() - start) * 1000)
    logger.info(
        '{"event": "llm_call", "node": "%s", "model": "%s", "attempt": %d, '
        '"latency_ms": %d, "status": "success", "timeout_ms": %d, '
        '"circuit_breaker_state": "closed"}',
        node,
        getattr(llm, "model_name", "unknown"),
        attempt_out["attempt"] + 1,
        latency_ms,
        int(LLM_TIMEOUT_SECONDS * 1000),
    )
    assert content is not None  # _attempt_loop's call() always yields exactly one item
    return content


# ── resilient_message_invoke ──────────────────────────────────────────────────

async def resilient_message_invoke(
    llm: Any,
    messages: list[dict],
    *,
    node: str,
    max_retries: int = 1,
) -> Any | None:
    """Timeout + bounded-retry + circuit-breaker wrapper that PRESERVES the response
    message object (unlike resilient_invoke, which collapses it to a `.content` string).

    Exists for the freeflow tool loop, which must inspect `response.tool_calls` to dispatch
    tools — a string return would break that. Returns the response message on success, or
    `None` on breaker-open / non-retryable error / exhausted retries. The caller treats
    `None` as its existing "empty generation" signal and substitutes a gate-traversing
    fallback, so NO degraded content can bypass output_gate (Cardinal Rule 4).

    Idempotency: retry wraps ONLY the generation call (the model returning tool_use
    requests), never tool execution — so a retry cannot double-fire a write tool
    (record_observation, flag_for_review). `max_retries` defaults to 1 (below
    resilient_invoke's 2): the tool loop can issue up to MAX_ITERATIONS generations under
    the single outer graph timeout (AINVOKE_TIMEOUT_SECONDS), so aggressive per-call retry
    would risk that budget. Retries fire only on retryable errors, never on a healthy-slow
    completion.
    """
    key = _circuit_key_from_model(
        getattr(llm, "model_name", "unknown"),
        getattr(llm, "openai_api_base", ""),
    )
    if _is_open(key):
        logger.warning(
            '{"event": "circuit_breaker_short_circuit", "node": "%s", '
            '"circuit_breaker_state": "open", "wrapper": "message_invoke"}',
            node,
        )
        return None

    async def _call() -> AsyncGenerator[Any, None]:
        yield await asyncio.wait_for(llm.ainvoke(messages), timeout=LLM_TIMEOUT_SECONDS)

    def _on_retry(attempt: int, backoff: float) -> None:
        # Same event name as resilient_invoke so one grep counts retries across BOTH
        # wrappers per run. A retried call reads as a slow call; in the ① baseline this
        # makes rate-limit retries separable from genuine pool contention.
        logger.warning(
            '{"event": "llm_call_retrying", "node": "%s", "attempt": %d, '
            '"backoff_s": %.2f, "wrapper": "message_invoke"}',
            node, attempt + 1, backoff,
        )

    start = time.monotonic()
    attempt_out: dict[str, int] = {}
    response_msg: Any = None
    try:
        async for item in _attempt_loop(
            _call, key=key, max_retries=max_retries, on_retry=_on_retry,
            attempt_out=attempt_out,
        ):
            response_msg = item
    except _NonRetryable as nr:
        logger.error(
            '{"event": "llm_message_invoke_failed", "node": "%s", "attempt": %d, '
            '"error_type": "non_retryable"}',
            node, nr.attempt + 1,
        )
        return None
    except _Exhausted:
        logger.error(
            '{"event": "llm_message_invoke_failed", "node": "%s", "retry_count": %d, '
            '"error_type": "exhausted"}',
            node, max_retries,
        )
        return None

    latency_ms = int((time.monotonic() - start) * 1000)
    # Parity with resilient_invoke's llm_call log so the freeflow tool-loop
    # generation (the single biggest LLM cost) is attributable in the latency baseline.
    logger.info(
        '{"event": "llm_call", "node": "%s", "model": "%s", "attempt": %d, '
        '"latency_ms": %d, "status": "success", "wrapper": "message_invoke"}',
        node,
        getattr(llm, "model_name", "unknown"),
        attempt_out["attempt"] + 1,
        latency_ms,
    )
    return response_msg


# ── resilient_stream ──────────────────────────────────────────────────────────

async def resilient_stream(
    llm: Any,
    messages: list[dict],
    *,
    node: str,
    language: str = "en",
    fallback_llm: Any | None = None,
) -> AsyncGenerator[str, None]:
    """Async generator wrapping astream() with first-chunk timeout and retry."""
    key = _circuit_key_from_model(
        getattr(llm, "model_name", "unknown"),
        getattr(llm, "openai_api_base", ""),
    )
    start = time.monotonic()

    if _is_open(key):
        yield get_fallback_response(node, language)
        return

    async def _call() -> AsyncGenerator[str, None]:
        stream = llm.astream(messages)
        first = await asyncio.wait_for(stream.__anext__(), timeout=LLM_TIMEOUT_SECONDS)
        if isinstance(first.content, str) and first.content:
            yield first.content
        # POC: no per-chunk timeout after first chunk; mid-stream hangs are
        # bounded by the caller's outer graph timeout, not this wrapper. This whole
        # body (first chunk through the last) is one retry attempt: a failure here,
        # even after some chunks were already re-yielded below, restarts the entire
        # stream on the next attempt — unchanged from pre-refactor behavior.
        async for chunk in stream:
            if isinstance(chunk.content, str) and chunk.content:
                yield chunk.content

    def _on_retry(attempt: int, backoff: float) -> None:
        logger.warning(
            '{"event": "llm_stream_retrying", "node": "%s", "attempt": %d, "backoff_s": %.2f}',
            node,
            attempt + 1,
            backoff,
        )

    attempt_out: dict[str, int] = {}
    try:
        async for chunk in _attempt_loop(
            _call, key=key, max_retries=LLM_MAX_RETRIES, on_retry=_on_retry,
            attempt_out=attempt_out,
        ):
            yield chunk
    except _NonRetryable:
        logger.error(
            '{"event": "llm_stream_failed", "node": "%s", "error_type": "non_retryable"}',
            node,
        )
        yield get_fallback_response(node, language)
        return
    except _Exhausted:
        if fallback_llm is not None:
            try:
                async for chunk in fallback_llm.astream(messages):
                    if isinstance(chunk.content, str) and chunk.content:
                        yield chunk.content
                return
            except Exception as fb_exc:
                logger.error(
                    '{"event": "llm_stream_fallback_failed", "node": "%s", "error_type": "%s"}',
                    node,
                    type(fb_exc).__name__,
                )
        logger.error(
            '{"event": "llm_stream_failed", "node": "%s", "retry_count": %d, '
            '"fallback_used": "fallback_response"}',
            node,
            LLM_MAX_RETRIES,
        )
        yield get_fallback_response(node, language)
        return

    latency_ms = int((time.monotonic() - start) * 1000)
    logger.info(
        '{"event": "llm_call", "node": "%s", "model": "%s", "attempt": %d, '
        '"latency_ms": %d, "status": "success"}',
        node,
        getattr(llm, "model_name", "unknown"),
        attempt_out["attempt"] + 1,
        latency_ms,
    )
