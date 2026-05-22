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
