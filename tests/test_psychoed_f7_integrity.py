"""Psychoed Phase 3 Task 8: F7 integrity (Node-8 verbatim hash gate).

FILE-CHOICE (documented per the task brief): a new, standalone file rather than an addition
to tests/test_psychoed_f5_flow.py. F5 is scoped to multi-turn conversational FLOW (menu
loop-back, weave turn-boundaries, carry-forward) driven through the compiled graph; F7 is
scoped to Node-8's OWN integrity gate (hash-verify / re-serve-on-mismatch / fallback-on-
corruption), which -- like Phase 2 Task 11's own test_psychoed_gate.py, the closest existing
analog -- is naturally proven at the NODE level: tampering the emitted text requires an
in-process hook (construct output_gate_node's entry state directly, with a deliberately
drifted `response_en`), not something the compiled graph can organically produce end-to-end
(freeflow_respond_node composes a psychoed serve verbatim from the store; there is no live
graph path that hands output_gate a corrupted response for a real block_id). This file reuses
tests/test_psychoed_gate.py's own state-construction helpers (`_og_state`, `_run_gate`,
`_SERVE_PAYLOAD`, `_COMPOSED`, `_MANIFEST`, `_CATEGORY`, `_BLOCK_ID`) for exactly that
node-level "test hook" pattern, the same reuse-not-duplicate convention this suite already
uses elsewhere (e.g. test_psychoed_fixtures_ci.py imports `_PSYCHOED_CARRY` from
test_psychoed_graph.py). The ONE genuinely new full-graph case (the pass path) is driven
directly through `sage_poc.graph.build_graph()`, mirroring test_psychoed_f5_flow.py's own
pattern, because a real end-to-end serve reaching a real PASS is exactly the case the compiled
graph CAN produce organically -- proving the gate's happy path holds through the whole
pipeline, not just against a hand-built state.

DELTA 3 CITE (corruption fallback chain -- cite the AS-BUILT delta, NOT the spec's superseded
"neutral referral" prose): handoff notes As-built delta 3 (docs/superpowers/plans/
2026-07-28-psychoed-phase2-handoff-notes.md): "payload's own `category` field ->
`psychoed_active_category` -> (both absent, unreachable by construction but held
mechanically, not by convention) CRITICAL log + first-enabled-category `check_in`
(`sorted(config.PSYCHOED_CATEGORIES)[0]`, hardcoded `"1f"` tertiary default if no category is
enabled at all)." Spec §6.2's own prose ("neutral referral template") is superseded by this
as-built chain -- the store is in-process, so a corruption here IS data loss, and the
fallback must itself already be ratified copy (a manifest's own `check_in`), never a
synthesized "neutral referral" string that doesn't exist in this codebase's implementation.
Implemented in output_gate.py's psychoed verbatim hash gate (~L949-996), already proven at
the node level by Phase 2 Task 11's own test_psychoed_gate.py (test_gate_corruption_drops_to_
manifest_check_in / test_gate_corruption_no_category_anywhere_falls_to_enabled_default /
test_gate_corruption_no_category_no_enabled_categories_falls_to_1f) -- this file re-pins the
category-present branch (the common case) for F7's own coverage, citing delta 3 explicitly.

NAMED EXCLUSION (ruled): response_en/history retention divergence is OBSERVED, NOT FIXED.
Handoff notes As-built delta 16: "The Node-8 gate rewrites `final_response` only;
`response_en`/history retain the blocked/tampered text ... on mismatch/corruption it
reassigns `final_response`, never patches `response_en` or the conversation-history entry
already built from it." Verified directly in output_gate.py: the psychoed gate (~L949-996)
only ever reassigns the LOCAL `final_response` variable; `response_en` (the separate local
that seeds both the returned `"response_en"` key at ~L1130 and `new_history`'s assistant
entry at ~L1062-1065) is never touched by either branch. So a hash-mismatch or corruption
incident's user-facing `response` is corrected, but `response_en` and
`conversation_history[-1]["content"]` still carry the ORIGINAL drifted/tampered text. Checked
docs/superpowers/tickets/ (2026-07-31): no ticket file exists for this item (same absence
Task 7 found for the L2-suppression NAMED CASE and this task found for the post-crisis-weave
NAMED CASE in f6_precedence.jsonl) -- cited here as delta 16 + the concrete code locations
above instead. This test file PINS the observed divergence (test_f7_mismatch_response_en_and_
history_retain_drifted_text_delta16 below); it does not fix it, and per the standing
never-adjust-src rule, src/ is untouched.
"""
import asyncio
import logging

import pytest

pytestmark = pytest.mark.safety_gate
from unittest.mock import patch

import sage_poc.config as config
from sage_poc.audit import _build_session_audit_row
from sage_poc.graph import build_graph
from sage_poc.psychoed import store
from tests.conftest import make_mock_llm
from tests.test_graph import make_e2e_state, carry_state
from tests.test_psychoed_graph import _PSYCHOED_CARRY
from tests.test_psychoed_gate import (
    _BLOCK_ID as _NODE_BLOCK_ID,
    _CATEGORY as _NODE_CATEGORY,
    _COMPOSED,
    _MANIFEST,
    _SERVE_PAYLOAD,
    _og_state,
    _run_gate,
)


def _carry_psychoed(prev: dict, raw_message: str, **overrides) -> dict:
    carried = {k: prev.get(k) for k in _PSYCHOED_CARRY if k in prev}
    return carry_state(prev, raw_message, **{**carried, **overrides})


def _mock_intent_route_factory(pinned: dict):
    def _mock(state):
        return {
            "primary_intent": pinned["intent"], "secondary_intent": None,
            "intent_confidence": 0.9, "emotional_intensity": state.get("emotional_intensity", 5),
            "engagement": state.get("engagement", 7), "path": state["path"] + ["intent_route"],
        }
    return _mock


# ---------------------------------------------------------------------------
# (a) Hash-gate PASS path: full graph, genuine menu-pick serve reaching output_gate for real.
# ---------------------------------------------------------------------------

async def test_f7_pass_path_full_graph_audit_gate_action_pass(monkeypatch):
    """1f menu-first trigger, then a menu pick (F5 test 1's own T1/T2 shape, tests/
    test_psychoed_f5_flow.py) -- a genuine block serve (1f-b1) reaches output_gate's
    verbatim hash gate for real, through the whole compiled graph, not a hand-built state.
    The block's own content is a verbatim substring of the composed response (by
    construction), so the gate's `_block_content in final_response` check passes and
    psychoed_gate_action is 'pass' -- the audit row this task's Hash-gate pass path bullet
    asks for.
    """
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    monkeypatch.setattr(config, "PSYCHOED_CATEGORIES", frozenset({"1f"}))

    pinned = {"intent": "info_request"}
    captured: list[dict] = []

    async def _capture_audit(state):
        captured.append(state)

    stub_llm = make_mock_llm(["freeflow stub reply"])

    with patch("sage_poc.graph.intent_route_node", side_effect=_mock_intent_route_factory(pinned)), \
         patch("sage_poc.nodes.output_gate.write_session_audit", new=_capture_audit), \
         patch("sage_poc.graph.write_session_audit", new=_capture_audit), \
         patch("sage_poc.nodes.freeflow_respond.get_responder", return_value=stub_llm), \
         patch("sage_poc.nodes.freeflow_respond.get_fallback_responder", return_value=stub_llm):
        graph = build_graph()

        t1 = await graph.ainvoke(make_e2e_state("Why do I keep worrying?"))
        assert t1["psychoed_menu_offered"] is True

        t2 = await graph.ainvoke(_carry_psychoed(t1, "What is anxiety?"))
        assert t2["skill_match_method"] == "psychoed_resolver"
        block_content = store.get_block("1f-b1")["content"]
        assert block_content in t2["response"], "block content must survive to the final response"

    assert len(captured) == 2  # one write_session_audit call per turn (both via output_gate)
    row_t2 = _build_session_audit_row(captured[-1])
    assert row_t2["psychoed_gate_action"] == "pass"
    assert row_t2["psychoed_block_ids"] == ["1f-b1"]


# ---------------------------------------------------------------------------
# (b) Mismatch branch: Task-11 test hook (tamper response_en directly), re-serve pinned,
#     audit "reserved", ERROR logged.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_f7_mismatch_reserves_pinned_recomposition_and_logs_error(monkeypatch, caplog):
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    tampered = "This reply drifted from the ratified block and never went through the store."
    state = _og_state(response_en=tampered)

    with caplog.at_level(logging.ERROR, logger="sage_poc.nodes.output_gate"):
        result, write_calls = await _run_gate(state)

    assert result["response"] == _COMPOSED["text"], "re-served pinned recomposition, never the drift"
    assert any(
        "psychoed_integrity_incident" in r.message and "kind=mismatch" in r.message
        for r in caplog.records
    ), "ERROR-level integrity incident must be logged"
    row = _build_session_audit_row(write_calls[0])
    assert row["psychoed_gate_action"] == "reserved"


# ---------------------------------------------------------------------------
# (c) Corruption branch: unknown block_id -> DELTA 3 fallback chain (payload category ->
#     active_category -> CRITICAL + first-enabled check_in). Category-present is the common
#     case; the "unreachable by construction but held mechanically" tail is already proven
#     node-level by Task 11's own test_psychoed_gate.py, cited above rather than re-proven.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_f7_corruption_falls_back_to_payload_category_check_in_delta3(monkeypatch, caplog):
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    corrupt_payload = {**_SERVE_PAYLOAD, "block_id": "9z-b9"}  # not in psy_store.block_ids()
    state = _og_state(
        response_en="whatever the model produced for a since-deleted block",
        psychoed_serve=corrupt_payload,
    )

    with caplog.at_level(logging.ERROR, logger="sage_poc.nodes.output_gate"):
        result, write_calls = await _run_gate(state)

    # Delta 3 tier 1: the payload's own "category" field (corrupt_payload still carries
    # _SERVE_PAYLOAD's original "category": _NODE_CATEGORY) -- already-ratified check_in,
    # never a synthesized "neutral referral" string.
    assert result["response"] == _MANIFEST["check_in"]
    assert any(
        "psychoed_integrity_incident" in r.message and "kind=corruption" in r.message
        for r in caplog.records
    ), "ERROR-level integrity incident must be logged"
    row = _build_session_audit_row(write_calls[0])
    assert row["psychoed_gate_action"] == "fallback"


# ---------------------------------------------------------------------------
# (d) NAMED EXCLUSION (delta 16): response_en / conversation_history retain the ORIGINAL
#     drifted text even though `response` is corrected. Not asserted anywhere else in this
#     suite -- this is the new pin the task brief calls for.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_f7_mismatch_response_en_and_history_retain_drifted_text_delta16(monkeypatch):
    """Delta 16: the psychoed gate rewrites `final_response` (-> the returned `response` key)
    ONLY. `response_en` and the conversation_history entry built from it are never patched,
    so they still carry the pre-gate drifted text after a mismatch incident. This is an
    OBSERVED, NOT-FIXED divergence (see module docstring) -- pinned here, not endorsed."""
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    tampered = "This reply drifted from the ratified block and never went through the store."
    state = _og_state(response_en=tampered)

    result, _write_calls = await _run_gate(state)

    assert result["response"] == _COMPOSED["text"], "sanity: response IS corrected"
    assert result["response_en"] == tampered, (
        "delta 16 NAMED EXCLUSION: response_en is NOT scrubbed -- it still carries the "
        "pre-gate drifted text the gate just blocked from reaching the user"
    )
    assert result["conversation_history"][-1] == {"role": "assistant", "content": tampered}, (
        "delta 16 NAMED EXCLUSION: the persisted history entry is built from the "
        "un-scrubbed response_en, so it also retains the drifted text, not the corrected "
        "response the user actually saw"
    )


@pytest.mark.asyncio
async def test_f7_corruption_response_en_and_history_retain_drifted_text_delta16(monkeypatch):
    """Same delta-16 divergence, corruption branch (independent code path, same shape:
    output_gate.py's corruption branch also only ever reassigns final_response)."""
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    corrupt_payload = {**_SERVE_PAYLOAD, "block_id": "9z-b9"}
    drifted = "whatever the model produced for a since-deleted block"
    state = _og_state(response_en=drifted, psychoed_serve=corrupt_payload)

    result, _write_calls = await _run_gate(state)

    assert result["response"] == _MANIFEST["check_in"], "sanity: response falls back per delta 3"
    assert result["response_en"] == drifted, (
        "delta 16 NAMED EXCLUSION: response_en is NOT scrubbed on the corruption branch either"
    )
    assert result["conversation_history"][-1] == {"role": "assistant", "content": drifted}
