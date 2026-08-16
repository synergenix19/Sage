"""Audit-row classifier provenance — SAGE_AUDIT_CLASSIFIER_PROVENANCE (default OFF).

Node-2 bistability finding (2026-07-28), consequence 3 (PDPL auditability): with
path-level nondeterminism, the existing audit trail is necessary but not sufficient to
reconstruct a classifier decision. When the flag is ON the session-audit row gains:
  classifier_model        — from config (CLASSIFIER_MODEL)
  classifier_provider     — LLM response metadata "provider" if OpenRouter returns it,
                            else the SAGE_OPENROUTER_PROVIDER_PIN value, else null
  classifier_seed         — the SAGE_CLASSIFIER_SEED value or null
  classifier_context_hash — sha256 hex of the exact assembled classifier prompt
                            messages, computed in intent_route immediately before
                            invocation (captures the stochastic-history component)

Conditional-column discipline (crisis_tier / precedence / medical_flags / hr / screen
convention, migration 012 style): flag-OFF rows must be BYTE-IDENTICAL to today.
Migration 016 is the flag-flip deploy gate.

The hash travels via the DECLARED SageState channels classifier_context_hash /
classifier_provider (LangGraph drops undeclared keys between nodes — the SG-2 seam
class); the graph-level seam test lives in test_state_channel_survival.py.
"""
import hashlib
import importlib
import json
from unittest.mock import patch

import pytest

import sage_poc.config as cfg
from sage_poc.audit import _build_session_audit_row


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _audit_state(**kwargs) -> dict:
    defaults = {
        "session_id": "test-session-classifier-provenance",
        "turn_number": 2,
        "path": ["safety_check", "intent_route"],
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "intent_confidence": 0.9,
        "active_skill_id": None,
        "active_step_id": None,
        "skill_match_method": None,
        "knowledge_passages": [],
        "knowledge_abstain": False,
        "knowledge_source": "",
        "crisis_state": "none",
        "crisis_flags": [],
        "clinical_flags": [],
        "engagement": 7,
        "emotional_intensity": 4,
        "model_version": "test-model",
        "latency_ms": None,
        "user_id": None,
    }
    return {**defaults, **kwargs}


def make_state(**kwargs):
    defaults = {
        "raw_message": "",
        "detected_language": "en",
        "message_en": "",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "active_step_id": None,
        "gate_path": None,
        "path": [],
        "turn_count": 0,
        "turn_number": 0,
        "conversation_history": [],
    }
    return {**defaults, **kwargs}


def _expected_hash(messages: list[dict]) -> str:
    return hashlib.sha256(
        json.dumps(messages, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")
    ).hexdigest()


# ---------------------------------------------------------------------------
# config flag
# ---------------------------------------------------------------------------

def test_provenance_flag_defaults_off(monkeypatch):
    monkeypatch.delenv("SAGE_AUDIT_CLASSIFIER_PROVENANCE", raising=False)
    importlib.reload(cfg)
    try:
        assert cfg.AUDIT_CLASSIFIER_PROVENANCE_ENABLED is False
    finally:
        monkeypatch.undo()
        importlib.reload(cfg)


def test_provenance_flag_on_when_true(monkeypatch):
    monkeypatch.setenv("SAGE_AUDIT_CLASSIFIER_PROVENANCE", "true")
    importlib.reload(cfg)
    try:
        assert cfg.AUDIT_CLASSIFIER_PROVENANCE_ENABLED is True
    finally:
        monkeypatch.undo()
        importlib.reload(cfg)


# ---------------------------------------------------------------------------
# audit row builder — conditional columns (migration 012 discipline)
# ---------------------------------------------------------------------------

def test_flag_off_row_byte_identical_to_baseline(monkeypatch):
    """Check-B discipline: with the flag OFF (the default), a row built from a state
    that even CARRIES provenance keys must be byte-identical to a row built from a
    state without them — the conditional block introduces zero drift when dark."""
    monkeypatch.setattr(cfg, "AUDIT_CLASSIFIER_PROVENANCE_ENABLED", False)
    baseline = _build_session_audit_row(_audit_state())
    with_keys = _build_session_audit_row(_audit_state(
        classifier_context_hash="a" * 64, classifier_provider="OpenAI",
        classifier_system_fingerprint="fp_x",
    ))
    assert with_keys == baseline
    assert not any(k.startswith("classifier_") for k in baseline)


def test_flag_on_row_gains_provenance_columns(monkeypatch):
    monkeypatch.setattr(cfg, "AUDIT_CLASSIFIER_PROVENANCE_ENABLED", True)
    monkeypatch.setattr(cfg, "CLASSIFIER_SEED", 777)
    monkeypatch.setattr(cfg, "OPENROUTER_PROVIDER_PIN", None)
    row = _build_session_audit_row(_audit_state(
        classifier_context_hash="b" * 64, classifier_provider="OpenAI",
    ))
    assert row["classifier_model"] == cfg.CLASSIFIER_MODEL
    assert row["classifier_provider"] == "OpenAI"       # live metadata wins
    assert row["classifier_seed"] == 777
    assert row["classifier_context_hash"] == "b" * 64


def test_flag_on_provider_falls_back_to_pin_then_null(monkeypatch):
    monkeypatch.setattr(cfg, "AUDIT_CLASSIFIER_PROVENANCE_ENABLED", True)
    monkeypatch.setattr(cfg, "CLASSIFIER_SEED", None)
    # no live metadata, pin set -> pin value
    monkeypatch.setattr(cfg, "OPENROUTER_PROVIDER_PIN", "openai")
    row = _build_session_audit_row(_audit_state(classifier_context_hash="c" * 64))
    assert row["classifier_provider"] == "openai"
    assert row["classifier_seed"] is None
    # no live metadata, no pin -> null
    monkeypatch.setattr(cfg, "OPENROUTER_PROVIDER_PIN", None)
    row = _build_session_audit_row(_audit_state(classifier_context_hash="c" * 64))
    assert row["classifier_provider"] is None


# ---------------------------------------------------------------------------
# intent_route — hash computed over the exact assembled messages, pre-invocation
# ---------------------------------------------------------------------------

_CLASSIFIER_JSON = ('{"primary_intent": "general_chat", "secondary_intent": null, '
                    '"emotional_intensity": 4, "engagement": 6, "intent_confidence": 0.9}')


async def _fake_invoke_factory(meta: dict | None = None):
    async def _fake(llm, messages, *, node, language="en", fallback_llm=None,
                    meta_out=None, **_kw):
        if meta is not None and meta_out is not None:
            meta_out.update(meta)
        return _CLASSIFIER_JSON
    return _fake


@pytest.mark.asyncio
async def test_intent_route_stamps_context_hash_when_flag_on(monkeypatch):
    from sage_poc.nodes.intent_route import (
        intent_route_node, build_intent_prompt, INTENT_SYSTEM,
    )
    monkeypatch.setattr(cfg, "AUDIT_CLASSIFIER_PROVENANCE_ENABLED", True)
    monkeypatch.setattr(cfg, "OPENROUTER_PROVIDER_PIN", None)
    state = make_state(message_en="I feel a bit low today", raw_message="I feel a bit low today")
    expected_messages = [
        {"role": "system", "content": INTENT_SYSTEM},
        {"role": "user", "content": build_intent_prompt(state)},
    ]
    with patch("sage_poc.nodes.intent_route.resilient_invoke",
               new=await _fake_invoke_factory()):
        result = await intent_route_node(state)
    assert result["classifier_context_hash"] == _expected_hash(expected_messages)
    assert result["classifier_provider"] is None   # no metadata, no pin


@pytest.mark.asyncio
async def test_intent_route_provider_chain_metadata_wins_over_pin(monkeypatch):
    from sage_poc.nodes.intent_route import intent_route_node
    monkeypatch.setattr(cfg, "AUDIT_CLASSIFIER_PROVENANCE_ENABLED", True)
    monkeypatch.setattr(cfg, "OPENROUTER_PROVIDER_PIN", "openai")
    state = make_state(message_en="hello", raw_message="hello")
    with patch("sage_poc.nodes.intent_route.resilient_invoke",
               new=await _fake_invoke_factory({"provider": "Azure"})):
        result = await intent_route_node(state)
    assert result["classifier_provider"] == "Azure"


@pytest.mark.asyncio
async def test_intent_route_provider_falls_back_to_pin_without_metadata(monkeypatch):
    from sage_poc.nodes.intent_route import intent_route_node
    monkeypatch.setattr(cfg, "AUDIT_CLASSIFIER_PROVENANCE_ENABLED", True)
    monkeypatch.setattr(cfg, "OPENROUTER_PROVIDER_PIN", "openai")
    state = make_state(message_en="hello", raw_message="hello")
    with patch("sage_poc.nodes.intent_route.resilient_invoke",
               new=await _fake_invoke_factory()):
        result = await intent_route_node(state)
    assert result["classifier_provider"] == "openai"


@pytest.mark.asyncio
async def test_intent_route_flag_off_result_carries_no_provenance_keys(monkeypatch):
    """Dark default: flag OFF -> the node's state update is byte-identical to today
    (no provenance keys at all, not None-valued ones)."""
    from sage_poc.nodes.intent_route import intent_route_node
    monkeypatch.setattr(cfg, "AUDIT_CLASSIFIER_PROVENANCE_ENABLED", False)
    state = make_state(message_en="hello", raw_message="hello")
    with patch("sage_poc.nodes.intent_route.resilient_invoke",
               new=await _fake_invoke_factory({"provider": "Azure"})):
        result = await intent_route_node(state)
    assert "classifier_context_hash" not in result
    assert "classifier_provider" not in result


# ---------------------------------------------------------------------------
# resilience — meta_out capture (backward-compatible optional out-param)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resilient_invoke_populates_meta_out():
    from sage_poc.resilience import resilient_invoke

    class _Msg:
        content = "ok "
        response_metadata = {"model_name": "openai/gpt-4o-mini", "provider": "OpenAI"}

    class _FakeLLM:
        model_name = "meta-out-test-model"
        openai_api_base = "https://test.invalid/v1"

        async def ainvoke(self, messages):
            return _Msg()

    meta: dict = {}
    out = await resilient_invoke(_FakeLLM(), [], node="intent_route", meta_out=meta)
    assert out == "ok"
    assert meta.get("provider") == "OpenAI"


# ---------------------------------------------------------------------------
# Q-a: pinned-provider failure mode (review criterion)
#
# Contract implemented: with SAGE_OPENROUTER_PROVIDER_PIN set and allow_fallbacks:false,
# a pinned-provider outage must NEVER silently retry without the pin. Guarantees:
#   1. The fallback classifier carries the SAME pin as the primary (constructor test in
#      test_llm_determinism_pins.py covers get_fallback_classifier) — no unpinned LLM
#      call exists anywhere in the intent path.
#   2. If primary AND pinned fallback both fail, resilient_invoke degrades to the STATIC
#      neutral fallback copy (no LLM call at all). intent_route then parses no JSON ->
#      general_chat @ confidence 0.5 -> _route_after_intent returns "low_confidence"
#      (Node 3) — the architecture's explicit "classification unavailable" route.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pinned_provider_failure_degrades_to_static_fallback_not_unpinned_retry(monkeypatch):
    """Primary (pinned) fails retryably; pinned fallback also fails. The result must be
    the static neutral fallback — and no unpinned invocation may ever occur."""
    import sage_poc.resilience as res
    monkeypatch.setattr(res, "LLM_BACKOFF_BASE", 0.001)
    monkeypatch.setattr(res, "LLM_BACKOFF_MAX", 0.002)
    import httpx

    calls = []

    class _PinnedDown:
        model_name = "pinned-down-primary"
        openai_api_base = "https://test-qa.invalid/v1"
        extra_body = {"provider": {"order": ["openai"], "allow_fallbacks": False}}

        async def ainvoke(self, messages):
            calls.append(("primary", self.extra_body))
            raise httpx.ConnectError("pinned provider down")

    class _PinnedFallbackDown:
        model_name = "pinned-down-fallback"
        openai_api_base = "https://test-qa.invalid/v1"
        extra_body = {"provider": {"order": ["openai"], "allow_fallbacks": False}}

        async def ainvoke(self, messages):
            calls.append(("fallback", self.extra_body))
            raise httpx.ConnectError("pinned provider down")

    out = await res.resilient_invoke(
        _PinnedDown(), [], node="intent_route", fallback_llm=_PinnedFallbackDown(),
    )
    # Static neutral copy served — a string, not an exception, and not an LLM product.
    assert isinstance(out, str) and out
    # Every LLM attempt that happened carried the pin; none was silently unpinned.
    assert calls, "expected at least one pinned attempt"
    for _, extra_body in calls:
        assert extra_body == {"provider": {"order": ["openai"], "allow_fallbacks": False}}


@pytest.mark.asyncio
async def test_pinned_provider_total_failure_routes_to_low_confidence(monkeypatch):
    """End-to-end degraded route: classification unavailable (static fallback text, no
    JSON) -> general_chat @ 0.5 -> _route_after_intent == "low_confidence" (Node 3)."""
    from sage_poc.nodes.intent_route import intent_route_node
    from sage_poc.graph import _route_after_intent

    async def _degraded(llm, messages, *, node, language="en", fallback_llm=None,
                        meta_out=None, **_kw):
        return "I'm here with you. Please give me just a moment."  # static fallback shape

    state = make_state(message_en="the weather is nice here",
                       raw_message="the weather is nice here")
    with patch("sage_poc.nodes.intent_route.resilient_invoke", new=_degraded):
        result = await intent_route_node(state)
    assert result["primary_intent"] == "general_chat"
    assert result["intent_confidence"] == 0.5
    assert _route_after_intent({**state, **result}) == "low_confidence"


# ---------------------------------------------------------------------------
# Q-b: seed honor, not seed request — system_fingerprint capture
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_intent_route_captures_system_fingerprint_when_returned(monkeypatch):
    from sage_poc.nodes.intent_route import intent_route_node
    monkeypatch.setattr(cfg, "AUDIT_CLASSIFIER_PROVENANCE_ENABLED", True)
    state = make_state(message_en="hello", raw_message="hello")
    with patch("sage_poc.nodes.intent_route.resilient_invoke",
               new=await _fake_invoke_factory({"system_fingerprint": "fp_44709d6fcb"})):
        result = await intent_route_node(state)
    assert result["classifier_system_fingerprint"] == "fp_44709d6fcb"


@pytest.mark.asyncio
async def test_intent_route_fingerprint_null_when_absent_or_empty(monkeypatch):
    """langchain-openai defaults a missing system_fingerprint to "" — that carries no
    honor signal and must be recorded as null, never fabricated."""
    from sage_poc.nodes.intent_route import intent_route_node
    monkeypatch.setattr(cfg, "AUDIT_CLASSIFIER_PROVENANCE_ENABLED", True)
    state = make_state(message_en="hello", raw_message="hello")
    with patch("sage_poc.nodes.intent_route.resilient_invoke",
               new=await _fake_invoke_factory({"system_fingerprint": ""})):
        result = await intent_route_node(state)
    assert result["classifier_system_fingerprint"] is None


def test_flag_on_row_records_system_fingerprint(monkeypatch):
    monkeypatch.setattr(cfg, "AUDIT_CLASSIFIER_PROVENANCE_ENABLED", True)
    row = _build_session_audit_row(_audit_state(
        classifier_context_hash="d" * 64,
        classifier_system_fingerprint="fp_44709d6fcb",
    ))
    assert row["classifier_system_fingerprint"] == "fp_44709d6fcb"
    row = _build_session_audit_row(_audit_state(classifier_context_hash="d" * 64))
    assert row["classifier_system_fingerprint"] is None


# ---------------------------------------------------------------------------
# per-turn reset (_build_state) — SG-2 stale-value discipline
# ---------------------------------------------------------------------------

def test_build_state_resets_provenance_channels_every_turn():
    from sage_poc.server_helpers import _build_state, _RequestLike, _MessageLike
    state = _build_state(_RequestLike(
        messages=[_MessageLike(role="user", content="hi")],
        session_id="s1",
    ))
    assert state["classifier_context_hash"] is None
    assert state["classifier_provider"] is None
    assert state["classifier_system_fingerprint"] is None
