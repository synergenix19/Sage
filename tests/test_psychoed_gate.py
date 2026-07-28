"""Phase 2 Task 11: freeflow no-LLM serve transit, Node-8 audit columns, and the psychoed
verbatim hash gate.

Mirrors tests/test_freeflow_respond.py's llm-mock pattern (freeflow) and
tests/test_hr_neutrality_gate.py's `_run_gate` pattern (output_gate) -- the closest existing
analog to this task's Node-8 gate, sharing the same placement (~925-930) and the same
"the pipeline renders, it does not decide whether ratified copy survives" cardinal rule.
"""
import asyncio
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sage_poc.config as config
from sage_poc.audit import _build_session_audit_row
from sage_poc.nodes.freeflow_respond import freeflow_respond_node
from sage_poc.nodes.output_gate import output_gate_node
from sage_poc.psychoed import serve, store

# Real store content (category 6d is answer_first -- 1f is menu_first, see test_psychoed_serve.py).
_BLOCK_ID = "6d-b1"
_CATEGORY = "6d"
_BLOCK_CONTENT = store.get_block(_BLOCK_ID)["content"]
_MANIFEST = store.manifest(_CATEGORY)
_SERVE_PAYLOAD = {
    "category": _CATEGORY, "block_id": _BLOCK_ID, "route": "standard", "framing": "abstract",
    "weave_due": False, "matched_row_id": "row-42", "collision_path": "clean",
}
_COMPOSED = serve.compose_turn1(_SERVE_PAYLOAD)


def _ff_state(**overrides):
    base = {
        "path": ["safety_check", "intent_route", "skill_select", "knowledge_retrieve"],
        "detected_language": "en",
        "message_en": "why do people get anxious",
        "raw_message": "why do people get anxious",
        "psychoed_serve": None,
        "skill_match_method": None,
        "psychoed_active_category": None,
    }
    return {**base, **overrides}


def _raising_llm():
    """A stub LLM that fails the test loudly if the tool loop / any generation call is reached."""
    mock_llm = MagicMock()
    mock_llm.bind_tools = MagicMock(side_effect=AssertionError("LLM must not be called on a psychoed serve turn"))
    mock_llm.ainvoke = AsyncMock(side_effect=AssertionError("LLM must not be called on a psychoed serve turn"))
    return mock_llm


def _og_state(**overrides):
    base = {
        "gate_path": None, "path": ["safety_check", "intent_route", "skill_select",
                                     "knowledge_retrieve", "freeflow_respond"],
        "detected_language": "en", "message_en": "why do people get anxious",
        "raw_message": "why do people get anxious",
        "response_en": _COMPOSED["text"],
        "is_safe": True, "crisis_state": "none", "crisis_flags": [], "clinical_flags": [],
        "conversation_history": [], "turn_count": 0, "conversation_summary": None,
        "session_id": "sess-psychoed-1", "user_id": "user-1",
        "active_skill_id": None, "active_step_id": None, "executed_step_id": None,
        "skill_match_method": "psychoed_resolver", "semantic_score": None,
        "emotional_intensity": 5, "engagement": 5, "s7_result": None, "s7_method": None,
        "third_party_crisis": False, "escalation_triggered": None,
        "banned_opener_retry_count": 0, "turn_number": 3,
        "psychoed_serve": _SERVE_PAYLOAD,
        "psychoed_matched_row_id": "row-42", "psychoed_collision_path": "clean",
        "psychoed_framing": "abstract", "psychoed_weave_pending": False, "psychoed_weave_fired": False,
    }
    return {**base, **overrides}


async def _run_gate(state):
    write_calls = []

    async def mock_write(s):
        write_calls.append(s)

    with patch("sage_poc.nodes.output_gate.write_session_audit", new=mock_write), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(state)
    await asyncio.sleep(0)  # let the asyncio.create_task(write_session_audit(...)) run
    return result, write_calls


# ── (a) freeflow: serve payload composes without any LLM call ────────────────────────────────

def test_freeflow_serve_payload_composes_without_llm(monkeypatch):
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    state = _ff_state(psychoed_serve=_SERVE_PAYLOAD)

    with patch("sage_poc.nodes.freeflow_respond.get_responder",
               side_effect=AssertionError("get_responder must not be called")), \
         patch("sage_poc.nodes.freeflow_respond.get_fallback_responder",
               side_effect=AssertionError("get_fallback_responder must not be called")):
        result = asyncio.run(freeflow_respond_node(state, llm=_raising_llm()))

    assert result["response_en"] == _COMPOSED["text"]
    assert result["psychoed_menu_offered"] == _COMPOSED["menu_offered"]
    assert result["psychoed_serve"]["template_version"] == _COMPOSED["template_version"]
    assert result["psychoed_serve"]["block_id"] == _BLOCK_ID  # original payload fields preserved
    assert "freeflow_respond" in result["path"]


# ── (b) freeflow: menu-after-weave re-offer, verbatim, no LLM ────────────────────────────────

def test_freeflow_menu_after_weave_serves_verbatim_menu_no_llm(monkeypatch):
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    state = _ff_state(skill_match_method="psychoed_menu_after_weave",
                       psychoed_active_category=_CATEGORY)

    with patch("sage_poc.nodes.freeflow_respond.get_responder",
               side_effect=AssertionError("get_responder must not be called")), \
         patch("sage_poc.nodes.freeflow_respond.get_fallback_responder",
               side_effect=AssertionError("get_fallback_responder must not be called")):
        result = asyncio.run(freeflow_respond_node(state, llm=_raising_llm()))

    assert result["response_en"] == _MANIFEST["menu_offer"]
    assert result["psychoed_menu_offered"] is True
    assert "psychoed_serve" not in result  # nothing to enrich; no payload this branch


# ── (c) freeflow: defensive fall-through when no active category ────────────────────────────

def test_freeflow_menu_after_weave_no_category_falls_through_to_llm(monkeypatch, caplog):
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    state = _ff_state(skill_match_method="psychoed_menu_after_weave", psychoed_active_category=None)

    # Patches the tool-loop entry point directly (established pattern, see
    # test_freeflow_respond.py::test_freeflow_sets_knowledge_source_tool_lookup_when_tool_fires) --
    # what matters here is that the LLM path is REACHED at all, not the tool-loop internals.
    with caplog.at_level(logging.WARNING, logger="sage_poc.nodes.freeflow_respond"):
        with patch("sage_poc.nodes.freeflow_respond._invoke_with_tool_loop",
                   AsyncMock(return_value="That sounds interesting, tell me more.")), \
             patch("sage_poc.nodes.freeflow_respond._get_prior_context", AsyncMock(return_value="")):
            result = asyncio.run(freeflow_respond_node(state, llm=MagicMock()))

    assert result["response_en"] == "That sounds interesting, tell me more."  # LLM path DID run
    assert any("psychoed_menu_after_weave" in r.message and "no psychoed_active_category" in r.message
               for r in caplog.records)


# ── (c2) freeflow: menu-after-weave falls through on a non-English turn (reviewer Medium,
# controller-adjudicated) -- third EN-ratified-copy path, previously ungated ─────────────────

def test_freeflow_menu_after_weave_non_english_falls_through_to_llm(monkeypatch, caplog):
    """PSY-WEAVE-1's weave evaluation is correctly language-UNgated (skill_select), so a
    clear-negative reply CAN set psychoed_menu_after_weave on an AR turn even after FIX 2's entry
    gates. The verbatim manifest menu_offer is EN-ratified copy though -- must not be served raw
    (or machine-translated) to an AR user. Must fall through to the LLM instead, INFO logged.

    Uses a real llm.ainvoke stub (not a patched tool-loop shortcut) and asserts it was actually
    called -- the path under test is empty-tools (no user_id/session_id, Node 6 already ran this
    turn per _ff_state's path), so _invoke_with_tool_loop calls resilient_invoke, which calls
    llm.ainvoke(messages) directly."""
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    state = _ff_state(skill_match_method="psychoed_menu_after_weave",
                       psychoed_active_category=_CATEGORY, detected_language="ar")

    mock_msg = MagicMock()
    mock_msg.content = "مرحبا، كيف تشعر اليوم؟"
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_msg)

    with caplog.at_level(logging.INFO, logger="sage_poc.nodes.freeflow_respond"):
        with patch("sage_poc.nodes.freeflow_respond._get_prior_context", AsyncMock(return_value="")):
            result = asyncio.run(freeflow_respond_node(state, llm=mock_llm))

    mock_llm.ainvoke.assert_called()  # LLM path DID run -- not the psychoed menu shortcut
    assert result["response_en"] == "مرحبا، كيف تشعر اليوم؟"
    assert result["response_en"] != _MANIFEST["menu_offer"]  # never the raw EN menu on an AR turn
    assert any("psychoed_menu_after_weave" in r.message and "non-English turn" in r.message
               for r in caplog.records)


# ── (d) gate: pass -- unaltered serve reaches response untouched, all 7 audit fields present ─

@pytest.mark.asyncio
async def test_gate_pass_unaltered_serve_all_audit_fields_present(monkeypatch):
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    state = _og_state(response_en=_COMPOSED["text"],
                       psychoed_serve={**_SERVE_PAYLOAD, "template_version": "1.0.0"})

    result, write_calls = await _run_gate(state)

    assert result["response"] == _COMPOSED["text"]  # untouched
    row = _build_session_audit_row(write_calls[0])
    assert row["psychoed_block_ids"] == [_BLOCK_ID]
    assert row["psychoed_matched_row_id"] == "row-42"
    assert row["psychoed_collision_path"] == "clean"
    assert row["psychoed_framing"] == "abstract"
    assert row["psychoed_weave_state"] is None  # not pending, not fired, no escalation patch
    assert row["psychoed_template_version"] == "1.0.0"
    assert row["psychoed_gate_action"] == "pass"


@pytest.mark.asyncio
async def test_gate_pass_logs_psychoed_fields_in_audit_log(monkeypatch, caplog):
    """output_gate's in-memory audit log dict (~933-969) also gains the six/seven keys."""
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    from sage_poc.config import AUDIT_LOG_ENABLED
    if not AUDIT_LOG_ENABLED:
        pytest.skip("AUDIT_LOG_ENABLED is False")
    state = _og_state(response_en=_COMPOSED["text"])

    with caplog.at_level(logging.INFO, logger="sage_poc.nodes.output_gate"):
        await _run_gate(state)

    assert "psychoed_gate_action" in caplog.text
    assert '"pass"' in caplog.text


# ── (e) gate: hash-mismatch -- tampered response replaced by store recomposition ─────────────

@pytest.mark.asyncio
async def test_gate_mismatch_replaces_response_and_logs_incident(monkeypatch, caplog):
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    tampered = "This is a completely different reply that never went through the store."
    state = _og_state(response_en=tampered)

    with caplog.at_level(logging.ERROR, logger="sage_poc.nodes.output_gate"):
        result, write_calls = await _run_gate(state)

    assert result["response"] == _COMPOSED["text"]  # re-served pinned recomposition
    assert any("psychoed_integrity_incident" in r.message and "kind=mismatch" in r.message
               for r in caplog.records)
    row = _build_session_audit_row(write_calls[0])
    assert row["psychoed_gate_action"] == "reserved"


# ── (f) gate: corruption -- block_id absent from store, drop to bare check_in ────────────────

@pytest.mark.asyncio
async def test_gate_corruption_drops_to_manifest_check_in(monkeypatch, caplog):
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    corrupt_payload = {**_SERVE_PAYLOAD, "block_id": "9z-b9"}
    state = _og_state(response_en="whatever the model produced for a since-deleted block",
                       psychoed_serve=corrupt_payload)

    with caplog.at_level(logging.ERROR, logger="sage_poc.nodes.output_gate"):
        result, write_calls = await _run_gate(state)

    assert result["response"] == _MANIFEST["check_in"]
    assert any("psychoed_integrity_incident" in r.message and "kind=corruption" in r.message
               for r in caplog.records)
    row = _build_session_audit_row(write_calls[0])
    assert row["psychoed_gate_action"] == "fallback"


# ── (a2) gate: corruption + no category anywhere -- mechanical fallback chain ────────────────
# Controller checkpoint fix: the corruption branch used to pass final_response through UNCHANGED
# when the payload's own category AND psychoed_active_category were both missing, violating
# "never emit unverified psychoed copy." Unreachable by construction (both payload constructors
# always set "category"), but the invariant must hold mechanically anyway.

@pytest.mark.asyncio
async def test_gate_corruption_no_category_anywhere_falls_to_enabled_default(monkeypatch, caplog):
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    # sorted({"3c", "4b"})[0] == "3c" -- deliberately NOT "1f", so this distinguishes the
    # "sorted-first ENABLED category" branch from the "no categories enabled -> 1f" branch below.
    monkeypatch.setattr(config, "PSYCHOED_CATEGORIES", frozenset({"3c", "4b"}))
    corrupt_payload = {"block_id": "9z-b9", "route": "standard", "framing": "abstract", "weave_due": False}
    state = _og_state(response_en="whatever the model produced for a since-deleted block",
                       psychoed_serve=corrupt_payload, psychoed_active_category=None)

    with caplog.at_level(logging.CRITICAL, logger="sage_poc.nodes.output_gate"):
        result, write_calls = await _run_gate(state)

    assert result["response"] == store.manifest("3c")["check_in"]
    assert result["response"] != state["response_en"]  # never the unverified/tampered text
    assert any("psychoed_integrity_incident" in r.message and "kind=corruption_no_category" in r.message
               for r in caplog.records)
    row = _build_session_audit_row(write_calls[0])
    assert row["psychoed_gate_action"] == "fallback"


@pytest.mark.asyncio
async def test_gate_corruption_no_category_no_enabled_categories_falls_to_1f(monkeypatch, caplog):
    """When no category can be resolved AND no category is enabled, the fallback strips to the
    manifest check_in of "1f" -- an always-present store category, never invented text."""
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    monkeypatch.setattr(config, "PSYCHOED_CATEGORIES", frozenset())
    corrupt_payload = {"block_id": "9z-b9", "route": "standard", "framing": "abstract", "weave_due": False}
    state = _og_state(response_en="whatever the model produced for a since-deleted block",
                       psychoed_serve=corrupt_payload, psychoed_active_category=None)

    with caplog.at_level(logging.CRITICAL, logger="sage_poc.nodes.output_gate"):
        result, write_calls = await _run_gate(state)

    assert result["response"] == store.manifest("1f")["check_in"]
    row = _build_session_audit_row(write_calls[0])
    assert row["psychoed_gate_action"] == "fallback"


# ── (g) gate: flag OFF -- no psychoed audit keys, no gate execution ──────────────────────────

@pytest.mark.asyncio
async def test_gate_flag_off_no_psychoed_keys_no_gate_execution(monkeypatch):
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", False)
    # Tampered on purpose: if the gate ran despite the flag, it would replace this with the
    # recomposition. Flag OFF must leave it untouched -- proof the gate body never executed.
    # Simulates the REAL flag-off shape: with the flag off, skill_select/knowledge_retrieve never
    # populate any psychoed_* channel, and psychoed_serve is reset to None every turn regardless
    # (state.py) -- so a genuinely inert turn carries none of these, not just a disabled gate.
    tampered = "flag is off so this must survive completely untouched regardless of content"
    state = _og_state(response_en=tampered, psychoed_serve=None, psychoed_matched_row_id=None,
                       psychoed_collision_path=None, psychoed_framing=None,
                       psychoed_weave_pending=False, psychoed_weave_fired=False,
                       skill_match_method=None)

    result, write_calls = await _run_gate(state)

    assert result["response"] == tampered  # gate never touched it
    row = _build_session_audit_row(write_calls[0])
    for key in ("psychoed_block_ids", "psychoed_matched_row_id", "psychoed_collision_path",
                "psychoed_framing", "psychoed_weave_state", "psychoed_template_version",
                "psychoed_gate_action"):
        assert key not in row, f"{key} must be absent when psychoed signal is inert"


# ── (h) escalation-turn audit row (gap-2): explicit "escalated" patch survives the row build ─

def test_escalation_turn_audit_row_carries_all_seven_fields():
    """Mirrors graph.py's _crisis_response_node patch shape: **state (already carrying the
    psychoed_* facts from the turn PSY-WEAVE-1 evaluated) plus the explicit
    "psychoed_weave_state": "escalated" key -- no live psychoed_serve payload on this turn."""
    state = {
        "session_id": "sess-esc", "turn_number": 5,
        "path": ["safety_check", "skill_select", "crisis_response"],
        "primary_intent": "new_skill", "secondary_intent": None, "intent_confidence": 0.9,
        "active_skill_id": None, "active_step_id": None, "skill_match_method": "psychoed_weave_escalation",
        "knowledge_passages": [], "knowledge_abstain": False, "knowledge_source": "",
        "crisis_state": "monitoring", "crisis_flags": ["s3_semantic"], "clinical_flags": [],
        "engagement": 4, "emotional_intensity": 9, "model_version": "test", "latency_ms": 500,
        "user_id": "user-esc",
        "psychoed_matched_row_id": "row-99", "psychoed_collision_path": "clean",
        "psychoed_framing": "personal", "psychoed_weave_pending": False, "psychoed_weave_fired": True,
        "psychoed_active_category": _CATEGORY,
        "psychoed_weave_state": "escalated",  # the crisis-node patch (graph.py:88)
    }
    row = _build_session_audit_row(state)
    assert row["psychoed_block_ids"] == []  # no live serve payload on the escalation turn
    assert row["psychoed_matched_row_id"] == "row-99"
    assert row["psychoed_collision_path"] == "clean"
    assert row["psychoed_framing"] == "personal"
    assert row["psychoed_weave_state"] == "escalated"  # explicit patch wins over fired/pending
    assert row["psychoed_template_version"] is None
    assert row["psychoed_gate_action"] is None
    assert len(row) >= 7  # all seven psychoed fields present alongside the baseline row
