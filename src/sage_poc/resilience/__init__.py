"""LLM Resilience Layer — timeout, retry, circuit breaker, warm fallback."""
from __future__ import annotations

import asyncio
import json
import logging
import pathlib
import random
import time
from collections.abc import AsyncGenerator
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
    """Return a pre-authored fallback response for the given node and language."""
    fb = _load_fallbacks()
    for entry in fb:
        if entry["node"] == node and entry["language"] == language:
            return entry["response"]
    for entry in fb:
        if entry["node"] == node and entry["language"] == "en":
            return entry["response"]
    for entry in fb:
        if entry["node"] == "default" and entry["language"] == language:
            return entry["response"]
    for entry in fb:
        if entry["node"] == "default" and entry["language"] == "en":
            return entry["response"]
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
) -> str:
    response_msg = await asyncio.wait_for(
        llm.ainvoke(messages), timeout=LLM_TIMEOUT_SECONDS
    )
    logger.info(
        '{"event": "llm_call", "node": "%s", "model": "%s", "is_fallback": %s, "status": "success"}',
        node,
        getattr(llm, "model_name", "unknown"),
        str(is_fallback).lower(),
    )
    return response_msg.content.strip()


# ── resilient_invoke ──────────────────────────────────────────────────────────

async def resilient_invoke(
    llm: Any,
    messages: list[dict],
    *,
    node: str,
    language: str = "en",
    fallback_llm: Any | None = None,
) -> str:
    """Call llm.ainvoke() with timeout, retry, circuit breaker, and fallback."""
    key = _circuit_key_from_model(
        getattr(llm, "model_name", "unknown"),
        getattr(llm, "openai_api_base", ""),
    )
    start = time.monotonic()

    if _is_open(key):
        logger.warning(
            '{"event": "circuit_breaker_short_circuit", "node": "%s", '
            '"circuit_breaker_state": "open"}',
            node,
        )
        if fallback_llm is not None:
            try:
                return await _invoke_once(
                    fallback_llm, messages, node, is_fallback=True
                )
            except Exception:
                pass
        return get_fallback_response(node, language)

    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            response_msg = await asyncio.wait_for(
                llm.ainvoke(messages), timeout=LLM_TIMEOUT_SECONDS
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            _record_success(key)
            logger.info(
                '{"event": "llm_call", "node": "%s", "model": "%s", "attempt": %d, '
                '"latency_ms": %d, "status": "success", "timeout_ms": %d, '
                '"circuit_breaker_state": "closed"}',
                node,
                getattr(llm, "model_name", "unknown"),
                attempt + 1,
                latency_ms,
                int(LLM_TIMEOUT_SECONDS * 1000),
            )
            return response_msg.content.strip()
        except Exception as exc:
            if not _is_retryable(exc):
                logger.error(
                    '{"event": "llm_call_failed", "node": "%s", "attempt": %d, '
                    '"error_type": "non_retryable", "fallback_used": "fallback_response"}',
                    node,
                    attempt + 1,
                )
                return get_fallback_response(node, language)
            _record_failure(key)
            if attempt < LLM_MAX_RETRIES:
                backoff = _backoff(attempt)
                logger.warning(
                    '{"event": "llm_call_retrying", "node": "%s", "attempt": %d, '
                    '"backoff_s": %.2f}',
                    node,
                    attempt + 1,
                    backoff,
                )
                await asyncio.sleep(backoff)

    if fallback_llm is not None:
        try:
            return await _invoke_once(
                fallback_llm, messages, node, is_fallback=True
            )
        except Exception as fb_exc:
            logger.error(
                '{"event": "llm_invoke_fallback_failed", "node": "%s", "error_type": "%s"}',
                node,
                type(fb_exc).__name__,
            )

    logger.error(
        '{"event": "llm_call_failed", "node": "%s", "retry_count": %d, '
        '"fallback_used": "fallback_response"}',
        node,
        LLM_MAX_RETRIES,
    )
    return get_fallback_response(node, language)


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
    start = time.monotonic()
    for attempt in range(max_retries + 1):
        try:
            response_msg = await asyncio.wait_for(
                llm.ainvoke(messages), timeout=LLM_TIMEOUT_SECONDS
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            _record_success(key)
            # Parity with resilient_invoke's llm_call log so the freeflow tool-loop
            # generation (the single biggest LLM cost) is attributable in the latency baseline.
            logger.info(
                '{"event": "llm_call", "node": "%s", "model": "%s", "attempt": %d, '
                '"latency_ms": %d, "status": "success", "wrapper": "message_invoke"}',
                node,
                getattr(llm, "model_name", "unknown"),
                attempt + 1,
                latency_ms,
            )
            return response_msg
        except Exception as exc:
            if not _is_retryable(exc):
                logger.error(
                    '{"event": "llm_message_invoke_failed", "node": "%s", "attempt": %d, '
                    '"error_type": "non_retryable"}',
                    node, attempt + 1,
                )
                return None
            _record_failure(key)
            if attempt < max_retries:
                backoff = _backoff(attempt)
                # Same event name as resilient_invoke so one grep counts retries across BOTH
                # wrappers per run. A retried call reads as a slow call; in the ① baseline this
                # makes rate-limit retries separable from genuine pool contention.
                logger.warning(
                    '{"event": "llm_call_retrying", "node": "%s", "attempt": %d, '
                    '"backoff_s": %.2f, "wrapper": "message_invoke"}',
                    node, attempt + 1, backoff,
                )
                await asyncio.sleep(backoff)
    logger.error(
        '{"event": "llm_message_invoke_failed", "node": "%s", "retry_count": %d, '
        '"error_type": "exhausted"}',
        node, max_retries,
    )
    return None


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

    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            stream = llm.astream(messages)
            first = await asyncio.wait_for(
                stream.__anext__(), timeout=LLM_TIMEOUT_SECONDS
            )
            if isinstance(first.content, str) and first.content:
                yield first.content
            # POC: no per-chunk timeout after first chunk; mid-stream hangs are
            # bounded by the caller's outer graph timeout, not this wrapper.
            async for chunk in stream:
                if isinstance(chunk.content, str) and chunk.content:
                    yield chunk.content
            latency_ms = int((time.monotonic() - start) * 1000)
            _record_success(key)
            logger.info(
                '{"event": "llm_call", "node": "%s", "model": "%s", "attempt": %d, '
                '"latency_ms": %d, "status": "success"}',
                node,
                getattr(llm, "model_name", "unknown"),
                attempt + 1,
                latency_ms,
            )
            return
        except Exception as exc:
            if not _is_retryable(exc):
                logger.error(
                    '{"event": "llm_stream_failed", "node": "%s", '
                    '"error_type": "non_retryable"}',
                    node,
                )
                yield get_fallback_response(node, language)
                return
            _record_failure(key)
            if attempt < LLM_MAX_RETRIES:
                backoff = _backoff(attempt)
                logger.warning(
                    '{"event": "llm_stream_retrying", "node": "%s", "attempt": %d, '
                    '"backoff_s": %.2f}',
                    node,
                    attempt + 1,
                    backoff,
                )
                await asyncio.sleep(backoff)

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
