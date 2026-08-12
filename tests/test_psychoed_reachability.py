"""Ticket A: psychoed resolver intent-reachability (spec §2.1 topology violation).

`docs/superpowers/tickets/2026-08-06-psychoed-resolver-intent-reachability.md`. Spec §2.1
binds the resolver to run "on the raw turn, regardless of `primary_intent`" -- deterministic
recognition is never conditional on the probabilistic router. That guarantee held INSIDE
Node 4 and was violated ONE NODE UPSTREAM: `_route_after_intent` sent `general_chat` to
`freeflow_respond` and `scope_refusal` to `output_gate`, so the trigger tables were
unreachable for those turns. `docs/2026-08-06-f1-wiring-flip-divergence-taxonomy.md`
taxonomizes the 52 misses of the 2026-08-05 flip-tier record: 48 `general_chat` +
3 `scope_refusal` interceptions, 1 unrelated collision (Ticket B), **zero crisis**.

RULED FIX (human, 2026-08-11): Direction 1 -- widen transit through `skill_select`, NOT the
hoist. One routing delta in `_route_after_intent`; still exactly one matching site.

What this module pins, in the order the requirements state them:

1. REACHABILITY (the fix): a doc-verbatim trigger phrase serves under `general_chat` and
   under `scope_refusal`, the two intercepting labels.
2. NULL CASE / BYTE-IDENTICAL TRANSIT (the regression guard for the widening): a turn that
   transits and does NOT hit must be byte-identical to master on response, state, path and
   audit row -- spec §2.1 step 5's pre-specified no-hit case. The master comparator used
   here is the SAME turn with `PSYCHOED_PATHWAYS_ENABLED` off: the widening is entirely
   flag-gated (`graph.psychoed_transit_destination` returns None with the flag off), so the
   flag-off run IS master's routing for these turns, executed in the same process on the
   same stubs. Volatile per-run fields (wall-clock latencies) are excluded by name, never
   by wildcard.
3. CRISIS PRECEDENCE explicitly above the match (the crisis branch is untouched by
   construction; pinned anyway, since "by construction" is the claim under review).
4. The WEAVE-PENDING REFUSAL PATH: a weave-pending reply the classifier labels
   `scope_refusal` reaches PSY-WEAVE-1's step-1 precedence and is EVALUATED, never bypassed.
5. The RULED SCOPE BOUNDARY: `jailbreak` and `exit_skill` are NOT widened (assessment
   evidence: `docs/2026-08-12-reachability-jailbreak-exit-skill-assessment.md`). These pins
   fail if a future edit widens either label without re-opening that assessment.
"""
import asyncio
import contextlib
import json
import pathlib
import re
from unittest.mock import patch

import pytest

import sage_poc.config as config
from sage_poc.audit import _build_session_audit_row
from sage_poc.graph import build_graph
from sage_poc.psychoed import store
from tests.conftest import make_mock_llm
from tests.test_graph import make_e2e_state
from tests.test_psychoed_graph import _carry_psychoed

# A doc-verbatim §0 trigger phrase (3c row 3c-t3) -- the same phrase
# tests/test_psychoed_graph.py drives, sourced from the trigger tables, not invented here.
TRIGGER_3C = "Why do I feel numb?"
# A turn with no trigger-table phrase in any category: the no-hit transit control.
NO_TRIGGER = "Thanks, I will try that this evening."

_FREEFLOW_STUB = "What part of that is weighing on you most right now?"

# Wall-clock fields that legitimately differ between two runs of the same turn (latencies
# and the turn's own timestamp). Named explicitly (never a prefix/wildcard) so a NEW
# volatile field cannot silently opt itself out of the byte-identity comparison.
_VOLATILE = frozenset({"latency_ms", "freeflow_gen_ms", "translate_out_ms", "last_turn_at"})


def _strip_volatile(d: dict) -> dict:
    return {k: v for k, v in d.items() if k not in _VOLATILE}


async def _run_turn(message: str, intent: str, *, flag_on: bool, categories=("3c",),
                    confidence: float = 0.9, **state_overrides) -> dict:
    """Drive one turn full-graph with `primary_intent` pinned, psychoed flags monkeypatch-free.

    Mirrors tests/test_psychoed_fixtures_ci.py's run_fixture patch context exactly (graph
    built INSIDE the context; both write_session_audit call sites captured; freeflow's LLM
    stubbed). Flags are set/restored around the ainvoke rather than via monkeypatch so a
    single test can run the same turn flag-off and flag-on and compare.
    """
    def _mock_intent_route(state):
        return {
            "primary_intent": intent,
            "secondary_intent": None,
            "intent_confidence": confidence,
            "emotional_intensity": state.get("emotional_intensity", 5),
            "engagement": state.get("engagement", 7),
            "path": state["path"] + ["intent_route"],
        }

    captured: list[dict] = []

    async def _capture_audit(state):
        captured.append(state)

    stub_llm = make_mock_llm([_FREEFLOW_STUB])
    prev_enabled, prev_categories = config.PSYCHOED_PATHWAYS_ENABLED, config.PSYCHOED_CATEGORIES
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("sage_poc.graph.intent_route_node", side_effect=_mock_intent_route))
        stack.enter_context(patch("sage_poc.nodes.output_gate.write_session_audit", new=_capture_audit))
        stack.enter_context(patch("sage_poc.graph.write_session_audit", new=_capture_audit))
        stack.enter_context(patch("sage_poc.nodes.freeflow_respond.get_responder", return_value=stub_llm))
        stack.enter_context(patch("sage_poc.nodes.freeflow_respond.get_fallback_responder", return_value=stub_llm))
        config.PSYCHOED_PATHWAYS_ENABLED = flag_on
        config.PSYCHOED_CATEGORIES = frozenset(categories) if flag_on else frozenset()
        try:
            graph = build_graph()
            result = await graph.ainvoke(make_e2e_state(message, **state_overrides))
            await asyncio.sleep(0)   # let the audit create_task run (both call sites)
        finally:
            config.PSYCHOED_PATHWAYS_ENABLED = prev_enabled
            config.PSYCHOED_CATEGORIES = prev_categories
    return {"result": result, "audit_rows": [_build_session_audit_row(s) for s in captured]}


# ───────────────────────── 1. Reachability: the fix itself ─────────────────────────

@pytest.mark.parametrize("intent", ["general_chat", "scope_refusal"])
def test_trigger_phrase_reaches_resolver_under_intercepting_label(intent):
    """The 51-row miss class: these two labels never reached Node 4 before the widening."""
    out = asyncio.run(_run_turn(TRIGGER_3C, intent, flag_on=True))
    result = out["result"]

    assert result["psychoed_matched_row_id"] == "3c-t3", (
        f"trigger table unreachable under primary_intent={intent!r} -- spec §2.1 violation"
    )
    assert result["psychoed_active_category"] == "3c"
    assert "skill_select" in result["path"], "the resolver's node must appear in the served path"
    assert store.manifest("3c")["framing_statement"] in result["response"]
    assert out["audit_rows"][-1]["psychoed_matched_row_id"] == "3c-t3"


@pytest.mark.parametrize("intent", ["general_chat", "scope_refusal"])
def test_widening_is_flag_gated(intent):
    """Flag OFF: the transit is unreachable and the turn keeps its master destination."""
    out = asyncio.run(_run_turn(TRIGGER_3C, intent, flag_on=False))
    assert "skill_select" not in out["result"]["path"]
    assert not out["result"].get("psychoed_serve")


# ─────────── 2. The null case: no-hit transit is byte-identical to master ───────────

@pytest.mark.parametrize("intent", ["general_chat", "scope_refusal"])
def test_no_hit_transit_is_byte_identical(intent):
    """Spec §2.1 step 5: no hit -> existing behavior unchanged.

    Compared field-by-field against the same turn with the flag off (= master routing for
    these labels, since the widening is entirely flag-gated): response, full final state,
    node path, and the audit row the turn writes.
    """
    off = asyncio.run(_run_turn(NO_TRIGGER, intent, flag_on=False))
    on = asyncio.run(_run_turn(NO_TRIGGER, intent, flag_on=True))

    assert on["result"]["response"] == off["result"]["response"]
    assert on["result"]["path"] == off["result"]["path"], (
        "a no-hit transit must not leave skill_select in node_path"
    )
    assert "skill_select" not in on["result"]["path"]
    assert _strip_volatile(on["result"]) == _strip_volatile(off["result"])

    assert len(on["audit_rows"]) == len(off["audit_rows"]) == 1
    assert _strip_volatile(on["audit_rows"][0]) == _strip_volatile(off["audit_rows"][0])


def test_no_hit_transit_keeps_scope_refusal_on_the_gate_terminal():
    """The scope_refusal transit's fall-through destination is output_gate, not freeflow."""
    on = asyncio.run(_run_turn(NO_TRIGGER, "scope_refusal", flag_on=True))
    assert "output_gate" in on["result"]["path"]
    assert "freeflow_respond" not in on["result"]["path"]


def test_mid_skill_general_chat_transit_does_not_hijack_the_active_skill():
    """Order item 2 (active-skill suppression) still stands under transit: a mid-skill
    off-topic turn carrying a trigger phrase transits, matches nothing (the resolver never
    fires over an active skill), and falls through byte-identically."""
    kw = {"active_skill_id": "box_breathing", "active_step_id": "step_1"}
    off = asyncio.run(_run_turn(TRIGGER_3C, "general_chat", flag_on=False, **kw))
    on = asyncio.run(_run_turn(TRIGGER_3C, "general_chat", flag_on=True, **kw))
    assert not on["result"].get("psychoed_serve")
    assert on["result"]["active_skill_id"] == "box_breathing"
    assert on["result"]["path"] == off["result"]["path"]
    assert _strip_volatile(on["result"]) == _strip_volatile(off["result"])


def test_non_english_transit_does_not_enter_the_pathway():
    """EN-only pathway ENTRY (spec §3.7/§7.3) is unchanged by the widening: an AR turn
    transits, the resolver's entry gate declines, and behavior is byte-identical."""
    kw = {"detected_language": "ar", "message_en": TRIGGER_3C}
    off = asyncio.run(_run_turn("لماذا أشعر بالخدر؟", "general_chat", flag_on=False, **kw))
    on = asyncio.run(_run_turn("لماذا أشعر بالخدر؟", "general_chat", flag_on=True, **kw))
    assert not on["result"].get("psychoed_serve")
    assert on["result"]["path"] == off["result"]["path"]


# ───────────────────────── 3. Crisis precedence above the match ─────────────────────────

def test_crisis_intent_never_transits():
    """The crisis branch sits above the widening and returns first (graph.py
    _route_after_intent_base). A crisis-labeled turn carrying a trigger phrase never
    reaches Node 4 -- the taxonomy's zero-crisis property must survive the fix."""
    out = asyncio.run(_run_turn(TRIGGER_3C, "crisis", flag_on=True))
    assert "crisis_response" in out["result"]["path"]
    assert "skill_select" not in out["result"]["path"]
    assert not out["result"].get("psychoed_serve")


def test_node1_crisis_short_circuit_still_precedes_everything():
    """Node 1 never reaches intent_route at all, so no widening can divert it."""
    out = asyncio.run(_run_turn("I want to kill myself tonight", "general_chat", flag_on=True))
    assert out["result"]["is_safe"] is False
    assert "intent_route" not in out["result"]["path"]
    assert "skill_select" not in out["result"]["path"]


# ─────────── 4. The weave-pending refusal path (rider: must be evaluated) ───────────

def test_weave_pending_reply_classified_scope_refusal_is_evaluated_not_bypassed():
    """A pending PSY-WEAVE-1 safety question is a live check on the PREVIOUS turn's serve.
    A reply the live classifier labels `scope_refusal` must reach skill_select's step-1
    weave precedence and be JUDGED ("kind of" is not a clear negative -> escalate), never
    bypassed to the gate terminal with the pending check starved.

    VERIFIED, NOT ASSUMED (2026-08-12): this property already held before the widening --
    HIGH-1's `psychoed_weave_pending` redirect sits ABOVE the `scope_refusal`/`jailbreak`
    gate branches in the intent ladder, so the reply reached the evaluator on its own. It is
    pinned explicitly here because the widening rewrites the ladder around it, and because
    the class was previously only covered implicitly (as one label of F4's nine-label sweep).

    Asserted on the escalation MARKERS, not on `psychoed_weave_escalation` in final state:
    `_crisis_response_node`'s pathway clear runs after the escalation audit and resets that
    channel, so reading it back at the end of the turn is not evidence either way.
    """
    turn1 = asyncio.run(_run_turn(TRIGGER_3C, "info_request", flag_on=True))
    assert turn1["result"]["psychoed_weave_pending"] is True

    out = asyncio.run(_run_turn_carry(turn1["result"], "kind of", "scope_refusal"))
    result = out["result"]
    assert result["skill_match_method"] == "psychoed_weave_escalation", (
        "PSY-WEAVE-1 was bypassed on a scope_refusal-classified weave reply"
    )
    assert "skill_select" in result["path"], "the reply never reached the weave evaluator"
    assert "crisis_response" in result["path"]
    assert result["gate_path"] == "crisis"
    assert result["psychoed_weave_pending"] is False
    assert out["audit_rows"][-1]["psychoed_weave_state"] == "escalated"


async def _run_turn_carry(prev: dict, message: str, intent: str, *, flag_on: bool = True) -> dict:
    """Second-turn variant of _run_turn: threads the previous turn's state forward the way
    tests/test_psychoed_graph.py does (carry_state + the psychoed channels)."""
    def _mock_intent_route(state):
        return {
            "primary_intent": intent, "secondary_intent": None, "intent_confidence": 0.9,
            "emotional_intensity": state.get("emotional_intensity", 5),
            "engagement": state.get("engagement", 7),
            "path": state["path"] + ["intent_route"],
        }

    captured: list[dict] = []

    async def _capture_audit(state):
        captured.append(state)

    stub_llm = make_mock_llm([_FREEFLOW_STUB])
    prev_enabled, prev_categories = config.PSYCHOED_PATHWAYS_ENABLED, config.PSYCHOED_CATEGORIES
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("sage_poc.graph.intent_route_node", side_effect=_mock_intent_route))
        stack.enter_context(patch("sage_poc.nodes.output_gate.write_session_audit", new=_capture_audit))
        stack.enter_context(patch("sage_poc.graph.write_session_audit", new=_capture_audit))
        stack.enter_context(patch("sage_poc.nodes.freeflow_respond.get_responder", return_value=stub_llm))
        stack.enter_context(patch("sage_poc.nodes.freeflow_respond.get_fallback_responder", return_value=stub_llm))
        config.PSYCHOED_PATHWAYS_ENABLED = flag_on
        config.PSYCHOED_CATEGORIES = frozenset({"3c"}) if flag_on else frozenset()
        try:
            graph = build_graph()
            result = await graph.ainvoke(_carry_psychoed(prev, message))
            await asyncio.sleep(0)
        finally:
            config.PSYCHOED_PATHWAYS_ENABLED = prev_enabled
            config.PSYCHOED_CATEGORIES = prev_categories
    return {"result": result, "audit_rows": [_build_session_audit_row(s) for s in captured]}


# ───────── 5b. The other in-edge to Node 4: the EMR rehand is never a transit turn ─────────

def test_executor_rehand_into_skill_select_is_not_a_transit_turn(monkeypatch):
    """`skill_select` has a second in-edge: `skill_executor` -> `skill_select` (EMR surface-1
    `exit_with_rehand`). A turn arriving that way reached Node 4 on its own; it must run the
    full node body and the normal post-select ladder, never the transit null-case return --
    whatever its intent label happens to be. Guarded on the executor's path stamp."""
    from sage_poc.graph import _route_after_skill_select, psychoed_transit_destination

    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    rehand = {"primary_intent": "general_chat", "intent_confidence": 0.9,
              "path": ["safety_check", "intent_route", "skill_executor", "skill_select"],
              "active_skill_id": "box_breathing", "emotional_intensity": 5}
    assert psychoed_transit_destination(rehand) is None
    assert _route_after_skill_select(rehand) == "skill_executor", (
        "the rehand turn must reach the executor with the newly selected skill, not fall "
        "through the transit branch to freeflow"
    )

    from_intent_route = {**rehand, "path": ["safety_check", "intent_route"], "active_skill_id": None}
    assert psychoed_transit_destination(from_intent_route) == "freeflow"


# ───────── 6. The taxonomy's own 51 intercepted rows, re-driven under their labels ─────────
#
# The CI-tier analogue of the DoD's live acceptance test. The fixture set is not re-authored
# here: it is READ from the committed taxonomy (docs/2026-08-06-f1-wiring-flip-divergence-
# taxonomy.md), which classified every one of the 52 flip-tier misses per-row against the
# run's own console log. Each intercepted row is driven with the label the LIVE classifier
# actually assigned it, and must now produce the serve the F1 corpus expects. The parse is
# count-guarded (48 + 3, no silent narrowing): if the taxonomy is edited or the corpus row
# ids drift, collection fails loudly rather than quietly gating fewer rows.
#
# The 52nd miss (F1-s2c-t5-01, cross_category_collision) is deliberately NOT here: it is
# Ticket B, a resolver-side collision, and the resolver DID run for it.

_TAXONOMY = pathlib.Path(__file__).parent.parent / "docs" / "2026-08-06-f1-wiring-flip-divergence-taxonomy.md"
_F1_CORPUS = pathlib.Path(__file__).parent / "fixtures" / "psychoed" / "f1_wiring.jsonl"
_TAXONOMY_ROW = re.compile(
    r"^\|\s*(F1-\S+)\s*\|\s*(general_chat|scope_refusal)\s*\|.*\|\s*intent_interception_(?:general_chat|scope_refusal)\s*\|$"
)
_EXPECTED_INTERCEPTIONS = {"general_chat": 48, "scope_refusal": 3}


def _intercepted_rows() -> list[tuple[str, str, dict]]:
    """(fixture_id, live label, corpus row) for every intent-interception row of the taxonomy."""
    labels: dict[str, str] = {}
    for line in _TAXONOMY.read_text(encoding="utf-8").splitlines():
        m = _TAXONOMY_ROW.match(line.strip())
        if m:
            labels[m.group(1)] = m.group(2)
    counts = {lbl: sum(1 for v in labels.values() if v == lbl) for lbl in _EXPECTED_INTERCEPTIONS}
    assert counts == _EXPECTED_INTERCEPTIONS, (
        f"taxonomy parse drifted: expected {_EXPECTED_INTERCEPTIONS}, parsed {counts} from {_TAXONOMY}"
    )
    corpus = {}
    for line in _F1_CORPUS.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("//"):
            row = json.loads(line)
            corpus[row["fixture_id"]] = row
    missing = sorted(set(labels) - set(corpus))
    assert not missing, f"taxonomy rows absent from the F1 corpus: {missing}"
    return [(fid, labels[fid], corpus[fid]) for fid in sorted(labels)]


@pytest.mark.parametrize(
    "fixture_id,label,row", _intercepted_rows(), ids=[f"{fid}-{lbl}" for fid, lbl, _ in _intercepted_rows()]
)
def test_taxonomy_intercepted_row_reaches_the_resolver(fixture_id, label, row):
    """Every row the live classifier intercepted must now serve under that same label."""
    assert len(row["turns"]) == 1, f"{fixture_id}: F1 wiring rows are single-turn by construction"
    out = asyncio.run(_run_turn(row["turns"][0]["utterance"], label, flag_on=True,
                                categories=(row["category"],)))
    result = out["result"]
    assert result.get("psychoed_matched_row_id") == row["expect"]["audit"]["psychoed_matched_row_id"], (
        f"{fixture_id}: still unreachable under primary_intent={label!r}"
    )
    assert result.get("psychoed_active_category") == row["expect"]["state"]["psychoed_active_category"]


# ───────────── 5. Ruled scope boundary: jailbreak / exit_skill NOT widened ─────────────

@pytest.mark.parametrize("intent", ["jailbreak", "exit_skill"])
def test_labels_outside_the_ruled_scope_are_not_widened(intent):
    """Ruled 2026-08-11: widen `general_chat` + `scope_refusal` only. The flip-tier taxonomy
    observed ZERO interceptions under `jailbreak` or `exit_skill`, so there is no evidence
    of need; `jailbreak` additionally carries a persona-reassertion decision that a
    deterministic content serve must not pre-empt without its own clinical ruling. If this
    test starts failing, the scope was widened -- re-open
    docs/2026-08-12-reachability-jailbreak-exit-skill-assessment.md, do not just re-pin."""
    out = asyncio.run(_run_turn(TRIGGER_3C, intent, flag_on=True))
    assert "skill_select" not in out["result"]["path"]
    assert not out["result"].get("psychoed_serve")
