"""Tests for the LLM resilience layer (Doc 5)."""
from __future__ import annotations

import asyncio
import json
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

from sage_poc.resilience import resilient_invoke, resilient_stream
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
        "message_en": "I have racing thoughts at night",
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

    # "can't sleep" is a keyword in sleep_hygiene — keyword tier fires before embedding
    assert result["active_skill_id"] == "sleep_hygiene"
    assert result["skill_match_method"] == "keyword"


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
    with patch("sage_poc.language.asyncio.wait_for", side_effect=asyncio.TimeoutError):
        result = await async_translate_to_arabic("Hello")
    assert result == "Hello"


@pytest.mark.asyncio
async def test_async_translate_to_english_timeout_returns_original():
    from sage_poc.language import async_translate_to_english
    with patch("sage_poc.language.asyncio.wait_for", side_effect=asyncio.TimeoutError):
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
    mock_t.assert_called_once_with("I hear you")
    assert result["response"] == "أسمعك"


@pytest.mark.asyncio
async def test_output_gate_english_no_translation():
    from sage_poc.nodes.output_gate import output_gate_node
    state = _gate_state(detected_language="en")
    with patch("sage_poc.nodes.output_gate.async_translate_to_arabic") as mock_t:
        result = await output_gate_node(state)
    mock_t.assert_not_called()
    assert result["response"] == "I hear you"
