# tests/test_embedding_timeout_channel.py
#
# F4 (code_review.md 2026-08-17): skill_select_node's embedding-timeout handler
# returns {"embedding_timeout": True}, but the key was not a declared SageState
# channel — LangGraph silently DROPS undeclared keys in the state merge (the
# state.py-documented bug class, 3rd+ recurrence: crisis_tier #2,
# monitoring_clear_turns, precedence_winner). Only the log line survived; any
# consumer reading state.get("embedding_timeout") — the natural audit /
# degradation-gate wiring — got None even during an active timeout incident.
#
# State-channel-seam checklist (declared channel + reset + static gate + graph
# test): the graph-survival test below is the behavioral backstop; the
# write-only-node-return rule added to scripts/check_state_channels.py is the
# class closure (a node emitting an undeclared key now fails CI even before
# any reader exists).

from langgraph.graph import StateGraph, START, END

from sage_poc.state import SageState


def test_embedding_timeout_is_a_declared_channel():
    assert "embedding_timeout" in SageState.__annotations__


def test_embedding_timeout_survives_the_node_to_node_seam():
    # Same pattern as test_state_channel_survival: a writer->reader graph over
    # the REAL SageState schema; reading into a declared field proves the
    # downstream node observed the value after the merge, exactly where an
    # audit writer or degradation gate would read it.
    def writer(state):
        return {"embedding_timeout": True}

    def reader(state):
        return {"gate_path": "timeout" if state.get("embedding_timeout") else "none"}

    g = StateGraph(SageState)
    g.add_node("writer", writer)
    g.add_node("reader", reader)
    g.add_edge(START, "writer")
    g.add_edge("writer", "reader")
    g.add_edge("reader", END)
    out = g.compile().invoke({})

    assert out.get("gate_path") == "timeout", (
        "embedding_timeout was DROPPED between nodes — declare it in SageState "
        "(LangGraph drops undeclared keys; see scripts/check_state_channels.py)"
    )


def test_embedding_timeout_reset_per_turn_in_build_state():
    # Per-turn signal (like skill_select_abstained): a timeout on turn N must
    # not read as a timeout on turn N+1 when the writer is skipped.
    from sage_poc.server_helpers import _build_state, _RequestLike, _MessageLike

    req = _RequestLike(messages=[_MessageLike(role="user", content="hi")], session_id="s1")
    state = _build_state(req)
    assert "embedding_timeout" in state
    assert state["embedding_timeout"] is None
