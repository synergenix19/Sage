"""Tests for the LLM resilience layer (Doc 5)."""
from __future__ import annotations

import asyncio
import json
import logging
import pathlib
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


# ── Shared helpers ────────────────────────────────────────────────────────────

def _make_llm(responses=None, side_effects=None,
              model_name="test/model", base_url="https://test.api"):
    """Build a mock ChatOpenAI. responses → list of str, side_effects → list of exceptions."""
    llm = MagicMock()
    llm.model_name = model_name
    llm.openai_api_base = base_url
    if side_effects:
        llm.ainvoke = AsyncMock(side_effect=side_effects)
    elif responses:
        llm.ainvoke = AsyncMock(
            side_effect=[MagicMock(content=r) for r in responses]
        )
    else:
        llm.ainvoke = AsyncMock(return_value=MagicMock(content="ok"))
    return llm


async def _collect(gen) -> str:
    """Collect all chunks from an async generator."""
    return "".join([chunk async for chunk in gen])


# ── Fallback JSON ─────────────────────────────────────────────────────────────

def test_fallbacks_json_valid():
    path = (
        pathlib.Path(__file__).parent.parent
        / "src/sage_poc/resilience/fallbacks.json"
    )
    assert path.exists(), "fallbacks.json must exist"
    data = json.loads(path.read_text())
    assert isinstance(data, list)
    nodes_langs = {(e["node"], e["language"]) for e in data}
    required = {
        ("freeflow_respond", "en"),
        ("freeflow_respond", "ar"),
        ("low_confidence_respond", "en"),
        ("low_confidence_respond", "ar"),
        ("default", "en"),
        ("default", "ar"),
    }
    missing = required - nodes_langs
    assert not missing, f"Missing fallback entries: {missing}"


def test_fallback_no_em_dashes():
    path = (
        pathlib.Path(__file__).parent.parent
        / "src/sage_poc/resilience/fallbacks.json"
    )
    data = json.loads(path.read_text())
    for entry in data:
        assert "—" not in entry["response"], (
            f"Em dash in fallback node={entry['node']} lang={entry['language']}"
        )


# ── get_fallback_response ─────────────────────────────────────────────────────

from sage_poc.resilience import (
    get_fallback_response,
    _circuit_state, _is_open, _record_success, _record_failure,
    _circuit_key_from_model, CIRCUIT_BREAKER_THRESHOLD, CIRCUIT_BREAKER_RESET_SECONDS,
)


def test_get_fallback_response_en():
    assert len(get_fallback_response("freeflow_respond", "en")) > 10


def test_get_fallback_response_ar():
    assert len(get_fallback_response("freeflow_respond", "ar")) > 5


def test_get_fallback_response_unknown_node_returns_default():
    r = get_fallback_response("no_such_node", "en")
    assert isinstance(r, str) and len(r) > 5


def test_intent_route_fallback_is_parseable_neutral_json():
    raw = get_fallback_response("intent_route", "en")
    data = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    assert data["primary_intent"] == "general_chat"
    assert "offer_response" not in data


def test_get_fallback_response_unknown_node_ar_falls_back():
    r = get_fallback_response("no_such_node", "ar")
    assert isinstance(r, str) and len(r) > 5


# ── Circuit breaker ───────────────────────────────────────────────────────────

def _reset(key: str) -> None:
    _circuit_state.pop(key, None)


def test_circuit_starts_closed():
    key = "test-a"
    _reset(key)
    assert not _is_open(key)


def test_circuit_trips_after_threshold():
    key = "test-b"
    _reset(key)
    for _ in range(CIRCUIT_BREAKER_THRESHOLD):
        _record_failure(key)
    assert _is_open(key)


def test_circuit_does_not_trip_below_threshold():
    key = "test-c"
    _reset(key)
    for _ in range(CIRCUIT_BREAKER_THRESHOLD - 1):
        _record_failure(key)
    assert not _is_open(key)


def test_circuit_resets_after_success():
    key = "test-d"
    _reset(key)
    for _ in range(CIRCUIT_BREAKER_THRESHOLD):
        _record_failure(key)
    _record_success(key)
    assert not _is_open(key)


def test_circuit_auto_resets_after_cooldown():
    key = "test-e"
    _reset(key)
    for _ in range(CIRCUIT_BREAKER_THRESHOLD):
        _record_failure(key)
    assert _is_open(key)
    past = datetime.utcnow() - timedelta(seconds=CIRCUIT_BREAKER_RESET_SECONDS + 1)
    _circuit_state[key]["reset_at"] = past
    assert not _is_open(key)
    _reset(key)


def test_circuit_independent_per_endpoint():
    key_a, key_b = "test-f", "test-g"
    _reset(key_a)
    _reset(key_b)
    for _ in range(CIRCUIT_BREAKER_THRESHOLD):
        _record_failure(key_a)
    assert _is_open(key_a)
    assert not _is_open(key_b)
    _reset(key_a)


# ── resilient_invoke ──────────────────────────────────────────────────────────

from sage_poc.resilience import resilient_invoke, resilient_message_invoke, resilient_stream
import sage_poc.resilience as _res


@pytest.mark.asyncio
async def test_resilient_invoke_success():
    llm = _make_llm(responses=["Hello there"])
    result = await resilient_invoke(
        llm, [{"role": "user", "content": "hi"}], node="freeflow_respond"
    )
    assert result == "Hello there"
    assert llm.ainvoke.call_count == 1


@pytest.mark.asyncio
async def test_resilient_invoke_timeout_returns_fallback():
    """A call that always times out should return the fallback response."""
    llm = MagicMock()
    llm.model_name = "test/model"
    llm.openai_api_base = "https://timeout-test.api"
    llm.ainvoke = AsyncMock(side_effect=asyncio.TimeoutError)

    async def fake_wait_for(coro, timeout):
        return await coro

    with patch("sage_poc.resilience.asyncio.wait_for", side_effect=fake_wait_for), \
         patch.object(_res, "LLM_MAX_RETRIES", 0):
        result = await resilient_invoke(llm, [], node="freeflow_respond", language="en")

    assert "moment" in result.lower() or "here" in result.lower()


@pytest.mark.asyncio
async def test_resilient_invoke_retries_then_succeeds():
    """First call times out; second succeeds. Returns second response."""
    call_count = 0

    async def sometimes_raises(messages):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise asyncio.TimeoutError("simulated timeout")
        return MagicMock(content="retry worked")

    llm = MagicMock()
    llm.model_name = "test/model"
    llm.openai_api_base = "https://retry-test.api"

    # Wrap in wait_for so the real timeout path fires on first call
    real_wait_for = asyncio.wait_for

    async def fake_wait_for(coro, timeout):
        # On first ainvoke call the coroutine raises TimeoutError
        return await coro

    with patch("sage_poc.resilience.asyncio.wait_for", side_effect=fake_wait_for):
        with patch("sage_poc.resilience.asyncio.sleep", new_callable=AsyncMock):
            llm.ainvoke = sometimes_raises
            result = await resilient_invoke(llm, [], node="freeflow_respond")

    assert result == "retry worked"
    assert call_count == 2


@pytest.mark.asyncio
async def test_resilient_invoke_non_retryable_skips_retries():
    """A 400 error skips retries and goes straight to fallback response."""
    import httpx

    err = httpx.HTTPStatusError(
        "400", request=MagicMock(), response=MagicMock(status_code=400)
    )
    llm = _make_llm(side_effects=[err])

    with patch("sage_poc.resilience.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await resilient_invoke(llm, [], node="freeflow_respond")

    mock_sleep.assert_not_called()
    assert isinstance(result, str) and len(result) > 5


@pytest.mark.asyncio
async def test_resilient_invoke_circuit_open_skips_llm():
    key = "https://open.api/test/model"
    _circuit_state[key] = {
        "state": "open",
        "consecutive_failures": CIRCUIT_BREAKER_THRESHOLD,
        "reset_at": datetime.utcnow() + timedelta(seconds=60),
    }
    try:
        llm = _make_llm(model_name="test/model", base_url="https://open.api")
        result = await resilient_invoke(llm, [], node="freeflow_respond")
        assert llm.ainvoke.call_count == 0
        assert isinstance(result, str)
    finally:
        _reset(key)


@pytest.mark.asyncio
async def test_resilient_invoke_uses_fallback_llm_after_all_retries():
    """When all primary retries exhaust, fallback LLM is tried once."""
    # Make primary always raise TimeoutError, with zero retries so we exit fast.
    primary = MagicMock()
    primary.model_name = "primary/model"
    primary.openai_api_base = "https://primary.api"
    primary.ainvoke = AsyncMock(side_effect=asyncio.TimeoutError("primary timed out"))

    fallback = _make_llm(responses=["fallback response"], base_url="https://fallback.api")

    original_retries = _res.LLM_MAX_RETRIES
    _res.LLM_MAX_RETRIES = 0

    async def fake_wait_for(coro, timeout):
        return await coro

    with patch("sage_poc.resilience.asyncio.wait_for", side_effect=fake_wait_for):
        result = await resilient_invoke(
            primary, [], node="freeflow_respond", fallback_llm=fallback
        )

    _res.LLM_MAX_RETRIES = original_retries
    assert "fallback response" in result


# ── resilient_stream ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resilient_stream_success():
    llm = MagicMock()
    llm.model_name = "test/model"
    llm.openai_api_base = "https://test.api"

    async def fake_astream(messages):
        for word in ["Hello", " ", "there"]:
            yield MagicMock(content=word)

    llm.astream = fake_astream
    result = await _collect(
        resilient_stream(llm, [], node="low_confidence_respond", language="en")
    )
    assert result == "Hello there"


@pytest.mark.asyncio
async def test_resilient_stream_timeout_before_first_chunk_yields_fallback():
    llm = MagicMock()
    llm.model_name = "test/model"
    llm.openai_api_base = "https://slow-stream.api"

    async def slow_astream(messages):
        yield MagicMock(content="never")

    llm.astream = slow_astream

    with patch("sage_poc.resilience.asyncio.wait_for", side_effect=asyncio.TimeoutError), \
         patch.object(_res, "LLM_MAX_RETRIES", 0):
        result = await _collect(
            resilient_stream(llm, [], node="low_confidence_respond", language="en")
        )
    assert "understand" in result.lower() or "mind" in result.lower()


@pytest.mark.asyncio
async def test_resilient_stream_non_retryable_yields_fallback():
    import httpx

    err = httpx.HTTPStatusError(
        "401", request=MagicMock(), response=MagicMock(status_code=401)
    )
    llm = MagicMock()
    llm.model_name = "test/model"
    llm.openai_api_base = "https://auth-err.api"

    async def bad_astream(messages):
        raise err
        yield  # pragma: no cover

    llm.astream = bad_astream

    async def fake_wait_for(coro, timeout):
        return await coro

    with patch("sage_poc.resilience.asyncio.wait_for", side_effect=fake_wait_for):
        result = await _collect(
            resilient_stream(llm, [], node="low_confidence_respond", language="en")
        )
    assert isinstance(result, str) and len(result) > 5


# ── Log event baseline (grep contract) ─────────────────────────────────────────
#
# server.py's _configure_instrumentation_logging() attaches a stdout handler directly
# to the "sage_poc.resilience" logger and the latency baseline greps its lines by
# event name. These tests pin the exact (event name -> key-set) SHAPE emitted by each
# of the three wrappers under forced success/retry/failure/breaker paths, captured
# straight off the logger (not pytest's caplog+propagate machinery) because that same
# server.py setup sets propagate=False on this exact logger once imported anywhere in
# the suite (e.g. the asgi_client fixture) — caplog would silently miss records if
# that setup already ran earlier in the session. Every log statement in resilience/
# __init__.py is a JSON literal built with %-style placeholders, so the formatted
# message is always valid JSON and can be parsed directly.
#
# Task 6 (refactor: one attempt loop) permits exactly ONE delta against this baseline:
# resilient_invoke's breaker-open path gains an llm_invoke_fallback_failed emission
# when the fallback LLM also raises (symmetry with the exhausted-retries path). That
# delta is isolated in test_log_baseline_invoke_breaker_open_fallback_fails below.

class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.INFO)
        self.records: list[logging.LogRecord] = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture
def resilience_log_events():
    target = logging.getLogger("sage_poc.resilience")
    handler = _ListHandler()
    saved_level, saved_propagate = target.level, target.propagate
    target.addHandler(handler)
    target.setLevel(logging.INFO)
    try:
        yield handler.records
    finally:
        target.removeHandler(handler)
        target.setLevel(saved_level)
        target.propagate = saved_propagate


def _events(records) -> list[dict]:
    return [json.loads(r.getMessage()) for r in records]


def _shape(events: list[dict]) -> list[tuple[str, frozenset]]:
    return [(e["event"], frozenset(e.keys())) for e in events]


async def _passthrough_wait_for(coro, timeout):
    return await coro


# -- resilient_invoke ------------------------------------------------------------

@pytest.mark.asyncio
async def test_log_baseline_invoke_success(resilience_log_events):
    llm = _make_llm(responses=["hi"], base_url="https://ev-inv-success.api")
    await resilient_invoke(llm, [], node="freeflow_respond")
    assert _shape(_events(resilience_log_events)) == [
        ("llm_call", frozenset({"event", "node", "model", "attempt", "latency_ms",
                                 "status", "timeout_ms", "circuit_breaker_state"})),
    ]


@pytest.mark.asyncio
async def test_log_baseline_invoke_retry_then_success(resilience_log_events):
    call_count = 0

    async def sometimes_raises(messages):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise asyncio.TimeoutError("simulated timeout")
        return MagicMock(content="ok")

    llm = MagicMock()
    llm.model_name = "test/model"
    llm.openai_api_base = "https://ev-inv-retry.api"
    llm.ainvoke = sometimes_raises

    with patch("sage_poc.resilience.asyncio.wait_for", side_effect=_passthrough_wait_for), \
         patch("sage_poc.resilience.asyncio.sleep", new_callable=AsyncMock):
        await resilient_invoke(llm, [], node="freeflow_respond")

    assert _shape(_events(resilience_log_events)) == [
        ("llm_call_retrying", frozenset({"event", "node", "attempt", "backoff_s"})),
        ("llm_call", frozenset({"event", "node", "model", "attempt", "latency_ms",
                                 "status", "timeout_ms", "circuit_breaker_state"})),
    ]


@pytest.mark.asyncio
async def test_log_baseline_invoke_non_retryable(resilience_log_events):
    import httpx
    err = httpx.HTTPStatusError("400", request=MagicMock(), response=MagicMock(status_code=400))
    llm = _make_llm(side_effects=[err], base_url="https://ev-inv-nonretry.api")

    with patch("sage_poc.resilience.asyncio.sleep", new_callable=AsyncMock):
        await resilient_invoke(llm, [], node="freeflow_respond")

    assert _shape(_events(resilience_log_events)) == [
        ("llm_call_failed", frozenset({"event", "node", "attempt", "error_type", "fallback_used"})),
    ]


@pytest.mark.asyncio
async def test_log_baseline_invoke_exhausted_no_fallback(resilience_log_events):
    llm = MagicMock()
    llm.model_name = "test/model"
    llm.openai_api_base = "https://ev-inv-exhausted.api"
    llm.ainvoke = AsyncMock(side_effect=asyncio.TimeoutError)

    with patch("sage_poc.resilience.asyncio.wait_for", side_effect=_passthrough_wait_for), \
         patch("sage_poc.resilience.asyncio.sleep", new_callable=AsyncMock), \
         patch.object(_res, "LLM_MAX_RETRIES", 1):
        await resilient_invoke(llm, [], node="freeflow_respond")

    events = _events(resilience_log_events)
    assert [e["event"] for e in events] == ["llm_call_retrying", "llm_call_failed"]
    assert _shape(events) == [
        ("llm_call_retrying", frozenset({"event", "node", "attempt", "backoff_s"})),
        ("llm_call_failed", frozenset({"event", "node", "retry_count", "fallback_used"})),
    ]


@pytest.mark.asyncio
async def test_log_baseline_invoke_exhausted_fallback_succeeds(resilience_log_events):
    primary = MagicMock()
    primary.model_name = "primary/model"
    primary.openai_api_base = "https://ev-inv-fb-ok.api"
    primary.ainvoke = AsyncMock(side_effect=asyncio.TimeoutError)
    fallback = _make_llm(responses=["fb"], base_url="https://ev-inv-fb-ok-fallback.api")

    with patch("sage_poc.resilience.asyncio.wait_for", side_effect=_passthrough_wait_for), \
         patch("sage_poc.resilience.asyncio.sleep", new_callable=AsyncMock), \
         patch.object(_res, "LLM_MAX_RETRIES", 0):
        await resilient_invoke(primary, [], node="freeflow_respond", fallback_llm=fallback)

    events = _events(resilience_log_events)
    assert [e["event"] for e in events] == ["llm_call"]
    assert _shape(events) == [
        ("llm_call", frozenset({"event", "node", "model", "is_fallback", "status"})),
    ]


@pytest.mark.asyncio
async def test_log_baseline_invoke_exhausted_fallback_fails(resilience_log_events):
    primary = MagicMock()
    primary.model_name = "primary/model"
    primary.openai_api_base = "https://ev-inv-fb-fail.api"
    primary.ainvoke = AsyncMock(side_effect=asyncio.TimeoutError)
    fallback = MagicMock()
    fallback.model_name = "fallback/model"
    fallback.openai_api_base = "https://ev-inv-fb-fail-fallback.api"
    fallback.ainvoke = AsyncMock(side_effect=RuntimeError("fallback down"))

    with patch("sage_poc.resilience.asyncio.wait_for", side_effect=_passthrough_wait_for), \
         patch("sage_poc.resilience.asyncio.sleep", new_callable=AsyncMock), \
         patch.object(_res, "LLM_MAX_RETRIES", 0):
        await resilient_invoke(primary, [], node="freeflow_respond", fallback_llm=fallback)

    events = _events(resilience_log_events)
    assert [e["event"] for e in events] == ["llm_invoke_fallback_failed", "llm_call_failed"]
    assert _shape(events) == [
        ("llm_invoke_fallback_failed", frozenset({"event", "node", "error_type"})),
        ("llm_call_failed", frozenset({"event", "node", "retry_count", "fallback_used"})),
    ]


@pytest.mark.asyncio
async def test_log_baseline_invoke_breaker_open_no_fallback(resilience_log_events):
    key = "https://ev-inv-breaker-a.api/test/model"
    _circuit_state[key] = {
        "state": "open", "consecutive_failures": CIRCUIT_BREAKER_THRESHOLD,
        "reset_at": datetime.utcnow() + timedelta(seconds=60),
    }
    try:
        llm = _make_llm(base_url="https://ev-inv-breaker-a.api")
        await resilient_invoke(llm, [], node="freeflow_respond")
    finally:
        _reset(key)

    assert _shape(_events(resilience_log_events)) == [
        ("circuit_breaker_short_circuit", frozenset({"event", "node", "circuit_breaker_state"})),
    ]


@pytest.mark.asyncio
async def test_log_baseline_invoke_breaker_open_fallback_succeeds(resilience_log_events):
    key = "https://ev-inv-breaker-b.api/test/model"
    _circuit_state[key] = {
        "state": "open", "consecutive_failures": CIRCUIT_BREAKER_THRESHOLD,
        "reset_at": datetime.utcnow() + timedelta(seconds=60),
    }
    try:
        llm = _make_llm(base_url="https://ev-inv-breaker-b.api")
        fallback = _make_llm(responses=["fb"], base_url="https://ev-inv-breaker-b-fallback.api")
        await resilient_invoke(llm, [], node="freeflow_respond", fallback_llm=fallback)
    finally:
        _reset(key)

    events = _events(resilience_log_events)
    assert [e["event"] for e in events] == ["circuit_breaker_short_circuit", "llm_call"]
    assert _shape(events) == [
        ("circuit_breaker_short_circuit", frozenset({"event", "node", "circuit_breaker_state"})),
        ("llm_call", frozenset({"event", "node", "model", "is_fallback", "status"})),
    ]


@pytest.mark.asyncio
async def test_log_baseline_invoke_breaker_open_fallback_fails(resilience_log_events):
    """CHARACTERIZATION (Task 6 step 1 baseline, pre-refactor): when the circuit is open
    AND the fallback LLM also raises, today NOTHING is logged for the fallback failure —
    unlike the exhausted-retries path, which logs llm_invoke_fallback_failed (see
    test_log_baseline_invoke_exhausted_fallback_fails). Task 6 step 2 fixes this
    symmetry gap by firing the SAME event here; this test is updated in that change to
    assert the addition — the ONE enumerated delta against this whole baseline suite."""
    key = "https://ev-inv-breaker-c.api/test/model"
    _circuit_state[key] = {
        "state": "open", "consecutive_failures": CIRCUIT_BREAKER_THRESHOLD,
        "reset_at": datetime.utcnow() + timedelta(seconds=60),
    }
    try:
        llm = _make_llm(base_url="https://ev-inv-breaker-c.api")
        fallback = MagicMock()
        fallback.model_name = "fallback/model"
        fallback.openai_api_base = "https://ev-inv-breaker-c-fallback.api"
        fallback.ainvoke = AsyncMock(side_effect=RuntimeError("fallback down"))
        await resilient_invoke(llm, [], node="freeflow_respond", fallback_llm=fallback)
    finally:
        _reset(key)

    assert _shape(_events(resilience_log_events)) == [
        ("circuit_breaker_short_circuit", frozenset({"event", "node", "circuit_breaker_state"})),
    ]


# -- resilient_message_invoke ------------------------------------------------------

@pytest.mark.asyncio
async def test_log_baseline_message_invoke_success(resilience_log_events):
    llm = _make_llm(responses=["hi"], base_url="https://ev-msg-success.api")
    await resilient_message_invoke(llm, [], node="freeflow_respond")
    assert _shape(_events(resilience_log_events)) == [
        ("llm_call", frozenset({"event", "node", "model", "attempt", "latency_ms",
                                 "status", "wrapper"})),
    ]


@pytest.mark.asyncio
async def test_log_baseline_message_invoke_retry_then_success(resilience_log_events):
    call_count = 0

    async def sometimes_raises(messages):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise asyncio.TimeoutError("simulated timeout")
        return MagicMock(content="ok")

    llm = MagicMock()
    llm.model_name = "test/model"
    llm.openai_api_base = "https://ev-msg-retry.api"
    llm.ainvoke = sometimes_raises

    with patch("sage_poc.resilience.asyncio.wait_for", side_effect=_passthrough_wait_for), \
         patch("sage_poc.resilience.asyncio.sleep", new_callable=AsyncMock):
        await resilient_message_invoke(llm, [], node="freeflow_respond", max_retries=1)

    assert _shape(_events(resilience_log_events)) == [
        ("llm_call_retrying", frozenset({"event", "node", "attempt", "backoff_s", "wrapper"})),
        ("llm_call", frozenset({"event", "node", "model", "attempt", "latency_ms",
                                 "status", "wrapper"})),
    ]


@pytest.mark.asyncio
async def test_log_baseline_message_invoke_non_retryable(resilience_log_events):
    import httpx
    err = httpx.HTTPStatusError("400", request=MagicMock(), response=MagicMock(status_code=400))
    llm = _make_llm(side_effects=[err], base_url="https://ev-msg-nonretry.api")

    with patch("sage_poc.resilience.asyncio.sleep", new_callable=AsyncMock):
        await resilient_message_invoke(llm, [], node="freeflow_respond")

    assert _shape(_events(resilience_log_events)) == [
        ("llm_message_invoke_failed", frozenset({"event", "node", "attempt", "error_type"})),
    ]


@pytest.mark.asyncio
async def test_log_baseline_message_invoke_exhausted(resilience_log_events):
    llm = MagicMock()
    llm.model_name = "test/model"
    llm.openai_api_base = "https://ev-msg-exhausted.api"
    llm.ainvoke = AsyncMock(side_effect=asyncio.TimeoutError)

    with patch("sage_poc.resilience.asyncio.wait_for", side_effect=_passthrough_wait_for), \
         patch("sage_poc.resilience.asyncio.sleep", new_callable=AsyncMock):
        await resilient_message_invoke(llm, [], node="freeflow_respond", max_retries=1)

    events = _events(resilience_log_events)
    assert [e["event"] for e in events] == ["llm_call_retrying", "llm_message_invoke_failed"]
    assert _shape(events) == [
        ("llm_call_retrying", frozenset({"event", "node", "attempt", "backoff_s", "wrapper"})),
        ("llm_message_invoke_failed", frozenset({"event", "node", "retry_count", "error_type"})),
    ]


@pytest.mark.asyncio
async def test_log_baseline_message_invoke_breaker_open(resilience_log_events):
    key = "https://ev-msg-breaker.api/test/model"
    _circuit_state[key] = {
        "state": "open", "consecutive_failures": CIRCUIT_BREAKER_THRESHOLD,
        "reset_at": datetime.utcnow() + timedelta(seconds=60),
    }
    try:
        llm = _make_llm(base_url="https://ev-msg-breaker.api")
        await resilient_message_invoke(llm, [], node="freeflow_respond")
    finally:
        _reset(key)

    assert _shape(_events(resilience_log_events)) == [
        ("circuit_breaker_short_circuit",
         frozenset({"event", "node", "circuit_breaker_state", "wrapper"})),
    ]


# -- resilient_stream ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_log_baseline_stream_success(resilience_log_events):
    llm = MagicMock()
    llm.model_name = "test/model"
    llm.openai_api_base = "https://ev-stream-success.api"

    async def fake_astream(messages):
        yield MagicMock(content="hi")

    llm.astream = fake_astream
    await _collect(resilient_stream(llm, [], node="low_confidence_respond"))

    assert _shape(_events(resilience_log_events)) == [
        ("llm_call", frozenset({"event", "node", "model", "attempt", "latency_ms", "status"})),
    ]


@pytest.mark.asyncio
async def test_log_baseline_stream_retry_then_success(resilience_log_events):
    call_count = 0

    def make_astream(messages):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise asyncio.TimeoutError("simulated timeout")

        async def _gen():
            yield MagicMock(content="ok")
        return _gen()

    llm = MagicMock()
    llm.model_name = "test/model"
    llm.openai_api_base = "https://ev-stream-retry.api"
    llm.astream = make_astream

    with patch("sage_poc.resilience.asyncio.sleep", new_callable=AsyncMock):
        await _collect(resilient_stream(llm, [], node="low_confidence_respond"))

    assert _shape(_events(resilience_log_events)) == [
        ("llm_stream_retrying", frozenset({"event", "node", "attempt", "backoff_s"})),
        ("llm_call", frozenset({"event", "node", "model", "attempt", "latency_ms", "status"})),
    ]


@pytest.mark.asyncio
async def test_log_baseline_stream_non_retryable(resilience_log_events):
    import httpx
    err = httpx.HTTPStatusError("401", request=MagicMock(), response=MagicMock(status_code=401))
    llm = MagicMock()
    llm.model_name = "test/model"
    llm.openai_api_base = "https://ev-stream-nonretry.api"

    async def bad_astream(messages):
        raise err
        yield  # pragma: no cover

    llm.astream = bad_astream

    async def fake_wait_for(coro, timeout):
        return await coro

    with patch("sage_poc.resilience.asyncio.wait_for", side_effect=fake_wait_for):
        await _collect(resilient_stream(llm, [], node="low_confidence_respond"))

    assert _shape(_events(resilience_log_events)) == [
        ("llm_stream_failed", frozenset({"event", "node", "error_type"})),
    ]


@pytest.mark.asyncio
async def test_log_baseline_stream_exhausted_no_fallback(resilience_log_events):
    llm = MagicMock()
    llm.model_name = "test/model"
    llm.openai_api_base = "https://ev-stream-exhausted.api"

    def always_raises(messages):
        raise asyncio.TimeoutError("simulated timeout")

    llm.astream = always_raises

    with patch.object(_res, "LLM_MAX_RETRIES", 1), \
         patch("sage_poc.resilience.asyncio.sleep", new_callable=AsyncMock):
        await _collect(resilient_stream(llm, [], node="low_confidence_respond"))

    events = _events(resilience_log_events)
    assert [e["event"] for e in events] == ["llm_stream_retrying", "llm_stream_failed"]
    assert _shape(events) == [
        ("llm_stream_retrying", frozenset({"event", "node", "attempt", "backoff_s"})),
        ("llm_stream_failed", frozenset({"event", "node", "retry_count", "fallback_used"})),
    ]


@pytest.mark.asyncio
async def test_log_baseline_stream_exhausted_fallback_succeeds_no_event(resilience_log_events):
    """Documents an existing (out-of-scope for Task 6) asymmetry: resilient_stream logs
    nothing when the fallback LLM stream succeeds, unlike resilient_invoke's llm_call
    (is_fallback=true). Not touched by this task — captured so a future change to this
    path shows up as a diff instead of silently drifting."""
    llm = MagicMock()
    llm.model_name = "test/model"
    llm.openai_api_base = "https://ev-stream-fb-ok.api"

    def always_raises(messages):
        raise asyncio.TimeoutError("simulated timeout")

    llm.astream = always_raises

    async def fallback_astream(messages):
        yield MagicMock(content="fb")

    fallback = MagicMock()
    fallback.astream = fallback_astream

    with patch.object(_res, "LLM_MAX_RETRIES", 0), \
         patch("sage_poc.resilience.asyncio.sleep", new_callable=AsyncMock):
        await _collect(resilient_stream(
            llm, [], node="low_confidence_respond", fallback_llm=fallback,
        ))

    assert _events(resilience_log_events) == []


@pytest.mark.asyncio
async def test_log_baseline_stream_exhausted_fallback_fails(resilience_log_events):
    llm = MagicMock()
    llm.model_name = "test/model"
    llm.openai_api_base = "https://ev-stream-fb-fail.api"

    def always_raises(messages):
        raise asyncio.TimeoutError("simulated timeout")

    llm.astream = always_raises

    async def bad_fallback_astream(messages):
        raise RuntimeError("fallback down")
        yield  # pragma: no cover

    fallback = MagicMock()
    fallback.astream = bad_fallback_astream

    with patch.object(_res, "LLM_MAX_RETRIES", 0), \
         patch("sage_poc.resilience.asyncio.sleep", new_callable=AsyncMock):
        await _collect(resilient_stream(
            llm, [], node="low_confidence_respond", fallback_llm=fallback,
        ))

    events = _events(resilience_log_events)
    assert [e["event"] for e in events] == ["llm_stream_fallback_failed", "llm_stream_failed"]
    assert _shape(events) == [
        ("llm_stream_fallback_failed", frozenset({"event", "node", "error_type"})),
        ("llm_stream_failed", frozenset({"event", "node", "retry_count", "fallback_used"})),
    ]


@pytest.mark.asyncio
async def test_log_baseline_stream_breaker_open_no_event(resilience_log_events):
    """Documents an existing (out-of-scope for Task 6) asymmetry: resilient_stream logs
    nothing on breaker-open, unlike resilient_invoke/resilient_message_invoke's
    circuit_breaker_short_circuit. Not touched by this task."""
    key = "https://ev-stream-breaker.api/test/model"
    _circuit_state[key] = {
        "state": "open", "consecutive_failures": CIRCUIT_BREAKER_THRESHOLD,
        "reset_at": datetime.utcnow() + timedelta(seconds=60),
    }
    try:
        llm = MagicMock()
        llm.model_name = "test/model"
        llm.openai_api_base = "https://ev-stream-breaker.api"
        await _collect(resilient_stream(llm, [], node="low_confidence_respond"))
    finally:
        _reset(key)

    assert _events(resilience_log_events) == []


# ── Model fallback factory ────────────────────────────────────────────────────

def test_fallback_factories_importable():
    from sage_poc.llm import get_fallback_responder, get_fallback_classifier
    assert callable(get_fallback_responder)
    assert callable(get_fallback_classifier)


def test_fallback_config_defined():
    from sage_poc.config import FALLBACK_RESPONDER_MODEL, FALLBACK_CLASSIFIER_MODEL
    assert isinstance(FALLBACK_RESPONDER_MODEL, str) and FALLBACK_RESPONDER_MODEL
    assert isinstance(FALLBACK_CLASSIFIER_MODEL, str) and FALLBACK_CLASSIFIER_MODEL


# ── skill_select embedding timeout ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_skill_select_node_is_async():
    import inspect
    from sage_poc.nodes.skill_select import skill_select_node
    assert inspect.iscoroutinefunction(skill_select_node)


@pytest.mark.asyncio
async def test_skill_select_embedding_timeout_falls_to_freeflow():
    from sage_poc.nodes.skill_select import skill_select_node

    state = {
        # Generic phrase: no keyword matches any skill, so semantic tier is reached.
        # "racing thoughts at night" was promoted to mindfulness_body_scan keyword tier
        # (2026-05-27 v7), so a phrase without specific skill keywords is needed here.
        "message_en": "I am just having a hard time right now",
        "crisis_state": "none",
        "active_skill_id": None,
        "active_step_id": None,
        "path": [],
    }
    with patch(
        "sage_poc.nodes.skill_select.asyncio.wait_for",
        side_effect=asyncio.TimeoutError,
    ):
        result = await skill_select_node(state)

    assert result["active_skill_id"] is None
    assert result["skill_match_method"] is None
    assert result.get("embedding_timeout") is True


@pytest.mark.asyncio
async def test_skill_select_keyword_tier_unaffected_by_timeout_patch():
    """Keyword matching runs before embedding — timeout patch must not block it."""
    from sage_poc.nodes.skill_select import skill_select_node

    state = {
        "message_en": "I can't sleep at night",
        "crisis_state": "none",
        "active_skill_id": None,
        "active_step_id": None,
        "path": [],
    }
    with patch(
        "sage_poc.nodes.skill_select.asyncio.wait_for",
        side_effect=asyncio.TimeoutError,
    ):
        result = await skill_select_node(state)

    # "can't sleep" is a keyword in sleep_hygiene — keyword tier fires before embedding.
    # R1: keyword matches surface as a consent offer, not direct activation.
    assert result["offered_skill_ids"][0] == "sleep_hygiene"
    assert result["skill_match_method"] == "keyword_offer"


# ── Server BGE-M3 warmup ──────────────────────────────────────────────────────

def test_server_has_bge_warmup():
    src = pathlib.Path(__file__).parent.parent / "server.py"
    content = src.read_text()
    assert "warmup" in content or "lifespan" in content, (
        "server.py must define a lifespan/startup handler for BGE-M3 warmup"
    )


# ── Async translation ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_async_translate_to_arabic_success():
    from sage_poc.language import async_translate_to_arabic
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="مرحباً"))
    with patch("sage_poc.language.get_translator", return_value=llm):
        result = await async_translate_to_arabic("Hello")
    assert result == "مرحباً"


@pytest.mark.asyncio
async def test_async_translate_to_arabic_timeout_returns_original():
    from sage_poc.language import async_translate_to_arabic
    with patch("sage_poc.resilience.resilient_invoke", new=AsyncMock(return_value=None)):
        result = await async_translate_to_arabic("Hello")
    assert result == "Hello"


@pytest.mark.asyncio
async def test_async_translate_to_english_timeout_returns_original():
    from sage_poc.language import async_translate_to_english
    with patch("sage_poc.resilience.resilient_invoke", new=AsyncMock(return_value=None)):
        result = await async_translate_to_english("مرحباً")
    assert result == "مرحباً"


# ── intent_route integration ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_intent_route_is_async():
    import inspect
    from sage_poc.nodes.intent_route import intent_route_node
    assert inspect.iscoroutinefunction(intent_route_node)


@pytest.mark.asyncio
async def test_intent_route_fallback_routes_to_general_chat():
    """When resilient_invoke returns fallback text (not JSON), intent defaults to general_chat."""
    from sage_poc.nodes.intent_route import intent_route_node
    state = {
        "message_en": "I feel anxious",
        "active_skill_id": None,
        "conversation_history": [],
        "path": [],
    }
    with patch(
        "sage_poc.nodes.intent_route.resilient_invoke",
        new_callable=AsyncMock,
        return_value="I'm here with you, give me a moment",
    ) as mock_ri:
        result = await intent_route_node(state)
    assert result["primary_intent"] == "general_chat"
    assert result["intent_confidence"] == 0.5


@pytest.mark.asyncio
async def test_intent_route_parses_valid_json_response():
    from sage_poc.nodes.intent_route import intent_route_node
    state = {
        "message_en": "I can't sleep",
        "active_skill_id": None,
        "conversation_history": [],
        "path": [],
    }
    valid_json = '{"primary_intent": "new_skill", "secondary_intent": null, "emotional_intensity": 6, "engagement": 7, "intent_confidence": 0.9}'
    with patch(
        "sage_poc.nodes.intent_route.resilient_invoke",
        new_callable=AsyncMock,
        return_value=valid_json,
    ):
        result = await intent_route_node(state)
    assert result["primary_intent"] == "new_skill"
    assert result["intent_confidence"] == 0.9


# ── low_confidence_respond integration ────────────────────────────────────────

@pytest.mark.asyncio
async def test_low_confidence_respond_collects_stream():
    from sage_poc.nodes.low_confidence_respond import low_confidence_respond_node
    state = {
        "message_en": "I don't know",
        "detected_language": "en",
        "path": [],
    }

    async def fake_stream(*a, **kw):
        yield "Could you tell me more?"

    with patch(
        "sage_poc.nodes.low_confidence_respond.resilient_stream",
        return_value=fake_stream(),
    ):
        result = await low_confidence_respond_node(state)
    assert result["response_en"] == "Could you tell me more?"


@pytest.mark.asyncio
async def test_low_confidence_respond_fallback_text_returned():
    from sage_poc.nodes.low_confidence_respond import low_confidence_respond_node
    state = {
        "message_en": "I don't know",
        "detected_language": "en",
        "path": [],
    }

    async def fallback_stream(*a, **kw):
        yield "I want to make sure I understand you well. Could you tell me a bit more about what's on your mind?"

    with patch(
        "sage_poc.nodes.low_confidence_respond.resilient_stream",
        return_value=fallback_stream(),
    ):
        result = await low_confidence_respond_node(state)
    assert "understand" in result["response_en"].lower()


# ── freeflow_respond integration ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_freeflow_respond_calls_resilient_invoke():
    from sage_poc.nodes.freeflow_respond import freeflow_respond_node
    state = {
        "message_en": "I feel overwhelmed",
        "detected_language": "en",
        "active_skill_id": None,
        "active_step_id": None,
        "step_instruction": None,
        "emotional_intensity": 6,
        "engagement": 5,
        "prompt_layers": [],
        "conversation_history": [],
        "crisis_state": "none",
        "clinical_flags": [],
        "code_switching": False,
        "path": [],
    }
    with patch(
        "sage_poc.nodes.freeflow_respond._invoke_with_tool_loop",
        new_callable=AsyncMock,
        return_value="I hear you, that sounds really hard.",
    ) as mock_itl:
        result = await freeflow_respond_node(state)
    mock_itl.assert_called_once()
    assert result["response_en"] == "I hear you, that sounds really hard."
    assert result["token_usage"] == {}


@pytest.mark.asyncio
async def test_freeflow_respond_fallback_returned_on_llm_failure():
    from sage_poc.nodes.freeflow_respond import freeflow_respond_node
    state = {
        "message_en": "I feel overwhelmed",
        "detected_language": "en",
        "active_skill_id": None,
        "active_step_id": None,
        "step_instruction": None,
        "emotional_intensity": 6,
        "engagement": 5,
        "prompt_layers": [],
        "conversation_history": [],
        "crisis_state": "none",
        "clinical_flags": [],
        "code_switching": False,
        "path": [],
    }
    fallback = "I'm here with you. I need a brief moment to collect my thoughts, can you bear with me?"
    with patch(
        "sage_poc.nodes.freeflow_respond._invoke_with_tool_loop",
        new_callable=AsyncMock,
        return_value="",
    ), patch(
        "sage_poc.nodes.freeflow_respond.resilient_invoke",
        new_callable=AsyncMock,
        return_value=fallback,
    ):
        result = await freeflow_respond_node(state)
    assert "moment" in result["response_en"] or "here" in result["response_en"]


# ── output_gate integration ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_output_gate_is_async():
    import inspect
    from sage_poc.nodes.output_gate import output_gate_node
    assert inspect.iscoroutinefunction(output_gate_node)


def _gate_state(**overrides) -> dict:
    base = {
        "gate_path": "standard",
        "detected_language": "en",
        "response_en": "I hear you",
        "message_en": "hello",
        "clinical_flags": [],
        "escalation_triggered": None,
        "active_skill_id": None,
        "skill_match_method": None,
        "semantic_score": None,
        "executed_step_id": None,
        "active_step_id": None,
        "emotional_intensity": 5,
        "engagement": 5,
        "is_safe": True,
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "primary_intent": "general_chat",
        "turn_count": 1,
        "conversation_history": [],
        "path": [],
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_output_gate_arabic_uses_async_translate():
    from sage_poc.nodes.output_gate import output_gate_node
    state = _gate_state(detected_language="ar", message_en="أنا حزين")
    with patch(
        "sage_poc.nodes.output_gate.async_translate_to_arabic",
        new_callable=AsyncMock,
        return_value="أسمعك",
    ) as mock_t:
        result = await output_gate_node(state)
    # gender="none": state carries no raw_message, so detect_gender_marking("") -> "none"
    # (signed gender-address policy, computed from the raw AR user text at the translate hop).
    mock_t.assert_called_once_with("I hear you", gender="none")
    assert result["response"] == "أسمعك"


@pytest.mark.asyncio
async def test_output_gate_english_no_translation():
    from sage_poc.nodes.output_gate import output_gate_node
    state = _gate_state(detected_language="en")
    with patch("sage_poc.nodes.output_gate.async_translate_to_arabic") as mock_t:
        result = await output_gate_node(state)
    mock_t.assert_not_called()
    assert result["response"] == "I hear you"
