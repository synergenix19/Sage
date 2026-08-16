"""Phase 2 Task 13: full-graph psychoed escalation test (spec: PSY-WEAVE-1, category 3c).

Mirrors tests/test_graph.py's app.ainvoke + mocked-LLM/no-DB pattern (intent_route is mocked
via patch("sage_poc.graph.intent_route_node", ...), exactly like test_graph.py's
test_negated_and_metaphor_phrases_do_not_trigger_crisis) and threads state between turns the
same way test_graph.py's carry_state() does (no checkpointer -- the next turn's input dict is
built explicitly from the previous turn's result). psychoed_* channels are not part of
test_graph.py's _CARRY_FIELDS (they're Task-13-specific), so this module carries them forward
itself via _carry_psychoed.

Audit capture follows tests/test_psychoed_gate.py's pattern: patch write_session_audit at its
call site (sage_poc.nodes.output_gate.write_session_audit for turn 1, sage_poc.graph.write_
session_audit for the escalation turn -- graph.py imports its own reference at module level),
capture the raw state dict passed in, then run it through audit._build_session_audit_row to
get the actual audit row (not just re-read state fields back at themselves).
"""
import asyncio
from unittest.mock import patch

import sage_poc.config as config
from sage_poc.audit import _build_session_audit_row
from sage_poc.graph import build_graph
from sage_poc.psychoed import store
from tests.test_graph import make_e2e_state, carry_state

_PSYCHOED_CARRY = (
    "psychoed_active_category", "psychoed_delivery_shape", "psychoed_menu_offered",
    "psychoed_weave_fired", "psychoed_weave_pending", "psychoed_matched_row_id",
    "psychoed_collision_path", "psychoed_framing", "psychoed_blocks_served",
    "psychoed_family_exposures",
)


def _carry_psychoed(prev: dict, raw_message: str, **overrides) -> dict:
    """carry_state() plus the psychoed channels it doesn't know about (Task-13-local)."""
    carried = {k: prev.get(k) for k in _PSYCHOED_CARRY if k in prev}
    return carry_state(prev, raw_message, **{**carried, **overrides})


def _mock_intent_route(state):
    """Deterministic routing to skill_select for every turn EXCEPT the escalation turn.

    primary_intent="info_request" at confidence 0.9 sends the serve/re-arm turns to
    skill_select via _route_after_intent's `if intent == "info_request": return
    "skill_select"` branch -- the same branch a real classification of these messages would
    very plausibly hit, but pinned here so the psychoed mechanism (not LLM variance) is what's
    under test.

    HIGH-1 (final review) un-masking: the escalation turn ("kind of") is deliberately NOT
    pinned to info_request here. "kind of" is a bare contradiction-marker reply with no
    information-seeking content -- a real classifier would very plausibly call this
    general_chat, not info_request. Before the HIGH-1 fix, general_chat here would fall
    through _route_after_intent's entire intent ladder to "freeflow", and skill_select's
    PSY-WEAVE-1 evaluator (which is what actually judges "kind of" as a non-clear-negative and
    escalates) would never run at all -- the pending weave silently starved. The OLD version of
    this test pinned info_request for every turn, including this one, which masked exactly that
    gap: it happened to route to skill_select for the wrong reason (info_request's own
    intent-ladder branch), so the test passed whether or not the weave-pending branch existed.
    Classifying this turn as general_chat un-masks it: the escalation must now reach skill_select
    via HIGH-1's `psychoed_weave_pending` branch (graph.py's `_route_after_intent`, same
    precedence slot as the answering_screen redirect), not via info_request's routing.
    """
    is_escalation_turn = "kind of" in (state.get("message_en") or "").lower()
    return {
        "primary_intent": "general_chat" if is_escalation_turn else "info_request",
        "secondary_intent": None,
        "intent_confidence": 0.85 if is_escalation_turn else 0.9,
        "emotional_intensity": state.get("emotional_intensity", 5),
        "engagement": state.get("engagement", 7),
        "path": state["path"] + ["intent_route"],
    }


async def test_full_graph_3c_serve_weave_escalation_and_rearm(monkeypatch):
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    monkeypatch.setattr(config, "PSYCHOED_CATEGORIES", frozenset({"3c"}))

    output_gate_audit_calls: list[dict] = []
    crisis_audit_calls: list[dict] = []

    async def _mock_output_gate_audit(state):
        output_gate_audit_calls.append(state)

    async def _mock_crisis_audit(state):
        crisis_audit_calls.append(state)

    with patch("sage_poc.graph.intent_route_node", side_effect=_mock_intent_route), \
         patch("sage_poc.nodes.output_gate.write_session_audit", new=_mock_output_gate_audit), \
         patch("sage_poc.graph.write_session_audit", new=_mock_crisis_audit):

        # build_graph() must run INSIDE the patch context: add_node("intent_route", ...) captures
        # a direct reference to the current sage_poc.graph.intent_route_node at call time, so
        # patching after building the graph would have no effect on the already-registered node.
        graph = build_graph()

        # ── Turn 1: "Why do I feel numb?" -> 3c resolver hit, weave fires ──────────────────
        t1 = await graph.ainvoke(make_e2e_state("Why do I feel numb?"))
        await asyncio.sleep(0)  # let output_gate's asyncio.create_task(write_session_audit(...)) run

        manifest_3c = store.manifest("3c")
        weave_question = store.shared_script("safety_weave_script")

        response_t1 = t1["response"]
        assert manifest_3c["framing_statement"] in response_t1, "3c framing must be present"
        # V1-PINNED: answer-first block selection is label-containment-else-first-block
        # (resolver._pick_block, documented v1). The clinically-relevant block for this
        # phrase is 3c-b4 (anhedonia) -- phrase->block hints are a clinician-ratified
        # mapping, packet addendum filed (as-built delta 14); when hints land + F1 fixtures
        # re-pin, THIS assertion re-targets to 3c-b4.
        block_3c_b1 = store.get_block("3c-b1")
        assert block_3c_b1["content"] in response_t1, "v1-pinned: 3c-b1 (first-block default) content must be present"
        assert weave_question in response_t1, "PSY-WEAVE-1 weave question must be present"
        assert manifest_3c["menu_offer"] not in response_t1, (
            "menu must be DEFERRED (weave fires instead) -- not offered this turn"
        )

        assert t1["psychoed_weave_pending"] is True
        assert t1["psychoed_matched_row_id"] == "3c-t3"

        assert len(output_gate_audit_calls) == 1
        row_t1 = _build_session_audit_row(output_gate_audit_calls[0])
        assert row_t1["psychoed_matched_row_id"] == "3c-t3"

        blocks_served_t1 = t1["psychoed_blocks_served"]
        family_exposures_t1 = t1["psychoed_family_exposures"]
        assert blocks_served_t1, "turn 1 must have served at least one block (survivor baseline)"
        assert family_exposures_t1, "turn 1 must have recorded a family exposure (survivor baseline)"

        # ── Turn 2: "kind of" -> not a clear negative -> PSY-WEAVE-1 escalates to crisis ───
        t2 = await graph.ainvoke(_carry_psychoed(t1, "kind of"))
        await asyncio.sleep(0)  # let crisis_response's asyncio.create_task(write_session_audit(...)) run

        # (a) crisis card path fired -- same markers existing crisis tests assert on
        assert "crisis_response" in t2["path"]
        assert t2["gate_path"] == "crisis"
        assert "800" in t2["response"] and "4673" in t2["response"]

        # (b) gap-2: the escalation turn's audit row exists, carries psychoed_weave_state=
        # "escalated" AND psychoed_matched_row_id (not scrubbed by the pathway clear, which
        # runs in the SAME return dict but AFTER the audit task is created).
        assert len(crisis_audit_calls) == 1
        row_t2 = _build_session_audit_row(crisis_audit_calls[0])
        assert row_t2["psychoed_weave_state"] == "escalated"
        assert row_t2["psychoed_matched_row_id"] is not None

        # (c) gap-1: pathway-scoped keys cleared, blocks_served/family_exposures survive
        assert t2["psychoed_active_category"] is None
        assert t2["psychoed_delivery_shape"] is None
        assert t2["psychoed_menu_offered"] is False
        assert t2["psychoed_weave_fired"] is False
        assert t2["psychoed_weave_pending"] is False
        assert t2["psychoed_matched_row_id"] is None
        assert t2["psychoed_collision_path"] is None
        assert t2["psychoed_framing"] is None
        assert t2["psychoed_blocks_served"] == blocks_served_t1, "survivor: blocks_served"
        assert t2["psychoed_family_exposures"] == family_exposures_t1, "survivor: family_exposures"

        # ── Turn 3: "Why do I feel numb?" again -> fresh serve, weave RE-ARMED ──────────────
        # crisis_state is deliberately reset to "none" here (not carried as "monitoring"):
        # monitoring re-entry runs evaluate_s7, a real LLM call this test does not mock, and
        # is orthogonal to what this assertion set is about -- whether psychoed_weave_fired's
        # reset in the Task-8 clear actually re-arms the weave on a fresh trigger.
        t3 = await graph.ainvoke(_carry_psychoed(t2, "Why do I feel numb?", crisis_state="none"))

        assert t3["psychoed_weave_pending"] is True, (
            "psychoed_weave_fired was reset by the escalation clear; a fresh 3c trigger must "
            "re-arm the weave, not treat it as already-fired"
        )
        assert t3["psychoed_matched_row_id"] == "3c-t3"
