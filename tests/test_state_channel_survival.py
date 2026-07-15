"""Graph-level tests for the node->node state-channel seam and the caveat emit-boundary.

Incident class (4th instance): #191 render seam, #205 affordance seam, SG-2's JSON->prompt
seam, and SG-2's node->node channel seam (2026-07-15). Every one: components individually
green, the seam silently broken, no node-isolation test failing. LangGraph merges only
DECLARED SageState channels between nodes, so a value written by one node under an undeclared
key is dropped and the downstream reader gets None.

These tests are the behavioral backstop to the static enforcement in
scripts/check_state_channels.py. They must run in the deterministic safety gate (no LLM):
node-isolation tests cannot catch this — the drop only happens in the compiled graph's merge.
"""
import pytest
from langgraph.graph import StateGraph, START, END

from sage_poc.state import SageState


def test_step_mandatory_caveat_survives_the_node_to_node_seam():
    """SG-2 root cause: skill_executor writes step_mandatory_caveat, output_gate reads it. If the
    key is not a declared SageState channel, LangGraph drops it in the state merge and the gate
    no-ops -> the caveat never fires for ANY skill (unit tests passed because they never drove the
    graph). Uses the REAL SageState schema; a minimal writer->reader graph reproduces the exact
    merge. Reading the value into a declared field (step_instruction) proves the DOWNSTREAM node
    observed it, not just that it appears in output."""
    sentinel = "SG2-CAVEAT-SENTINEL-9f3a2c"

    def writer(state):
        return {"step_mandatory_caveat": sentinel}

    def reader(state):
        # A downstream node reading the channel — this is output_gate's position.
        return {"step_instruction": state.get("step_mandatory_caveat")}

    g = StateGraph(SageState)
    g.add_node("writer", writer)
    g.add_node("reader", reader)
    g.add_edge(START, "writer")
    g.add_edge("writer", "reader")
    g.add_edge("reader", END)
    out = g.compile().invoke({})

    assert out.get("step_instruction") == sentinel, (
        "step_mandatory_caveat was DROPPED between nodes — it must be declared in the SageState "
        "TypedDict (LangGraph drops undeclared keys). This is the SG-2 firing bug's exact root "
        "cause; see scripts/check_state_channels.py for the static gate."
    )


def _graph_edges() -> set[tuple[str, str]]:
    from sage_poc.graph import build_graph
    drawable = build_graph(None).get_graph()
    return {(e.source, e.target) for e in drawable.edges}


def _reachable_from(start: str, edges: set[tuple[str, str]]) -> set[str]:
    seen, stack = set(), [start]
    while stack:
        n = stack.pop()
        for s, t in edges:
            if s == n and t not in seen:
                seen.add(t)
                stack.append(t)
    return seen


def test_acute_skill_turns_route_through_output_gate():
    """Caveats live on acute-skill steps and are delivered by output_gate
    (_pin_contraindication_caveat). The acute path is skill_executor -> freeflow_respond ->
    output_gate; assert output_gate is REACHABLE from skill_executor (robust to benign
    intermediates, still catches a real gate-bypass). Welds the SG-2 fix to the topology: a
    future change that routed caveat-bearing turns around the gate would fail here, not silently
    strip the safety copy."""
    edges = _graph_edges()
    reachable = _reachable_from("skill_executor", edges)
    assert "output_gate" in reachable, (
        f"output_gate is NOT reachable from skill_executor (reachable: {sorted(reachable)}) — "
        "acute-skill caveats would not fire."
    )


def test_crisis_turns_bypass_output_gate_per_emit_boundary_adr():
    """Emit-boundary ADR: crisis turns skip output_gate (crisis_response -> END). Pin the bypass
    as a deliberate, tested property so it can't drift — and confirm crisis never reaches the gate."""
    edges = _graph_edges()
    crisis_targets = {t for s, t in edges if s == "crisis_response"}
    assert crisis_targets, "crisis_response has no outgoing edge"
    assert "output_gate" not in crisis_targets, (
        f"crisis_response routes to output_gate ({crisis_targets}) — violates the emit-boundary ADR "
        "(crisis turns must bypass the gate)."
    )
    assert any(t in (END, "__end__") for t in crisis_targets), (
        f"crisis_response must terminate at END (bypassing the gate); targets were {crisis_targets}."
    )
