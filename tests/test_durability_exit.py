"""Pins the durability="exit" behaviour introduced by the 2026-06-24 latency RCA.

durability="exit" (vs LangGraph's default "async") persists ONE checkpoint at graph
exit instead of one per super-step. Headline latency fix: prod measured ~7.5 checkpoint
+ ~105 checkpoint_writes rows/turn, each a cross-region INSERT.

Two properties pinned here, both verified empirically (the second corrects an initial
hypothesis):

1. WRITE COLLAPSE (the latency win). A successful multi-node turn writes one checkpoint
   and zero pending-writes under exit, vs many under async.

2. FLAG RETENTION ON A CRASHED TURN (the safety property). A channel value (modelling a
   clinical_flag) set at node 1 of a turn that then CRASHES before the terminal node is
   RETAINED under BOTH async and exit. Under exit, LangGraph still records the completed
   node's *pending write*, so the value survives in the persisted state that the next
   turn's safety_check reads as carry-forward. The originally-feared "exit silently drops
   a flag detected on a crashed turn" does NOT occur for in-process failures — this test
   guards against a regression that would make it occur.

Sage's clinical_flags ride exactly this mechanism: safety_check (node 1) writes
clinical_flags as a union of this-turn detection + checkpoint carry-forward + durable
profile. The value asserted below is what the next turn reads as carry-forward.
"""
import asyncio
from typing import TypedDict

import pytest
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver


class _S(TypedDict, total=False):
    flags: list
    detect: bool
    boom: bool
    x: int


def _node1_detect_and_carry(state):
    # Mirrors safety_check: union of this-turn detection + checkpoint carry-forward.
    flags = list(state.get("flags") or [])
    if state.get("detect"):
        flags = sorted(set(flags + ["substance_use"]))
    return {"flags": flags}


def _node2_maybe_crash(state):
    if state.get("boom"):
        raise RuntimeError("simulated mid-graph crash after node 1")
    return {"x": 1}


def _node3(state):
    return {"x": 2}


class _CountingSaver(InMemorySaver):
    def __init__(self):
        super().__init__()
        self.n_checkpoints = 0
        self.n_writes = 0

    async def aput(self, *a, **k):
        self.n_checkpoints += 1
        return await super().aput(*a, **k)

    async def aput_writes(self, *a, **k):
        self.n_writes += 1
        return await super().aput_writes(*a, **k)


def _build(saver):
    g = StateGraph(_S)
    g.add_node("n1", _node1_detect_and_carry)
    g.add_node("n2", _node2_maybe_crash)
    g.add_node("n3", _node3)
    g.add_edge(START, "n1")
    g.add_edge("n1", "n2")
    g.add_edge("n2", "n3")
    g.add_edge("n3", END)
    return g.compile(checkpointer=saver)


def test_exit_collapses_checkpoint_writes_vs_async():
    """The latency mechanism: a 3-node turn writes 1 checkpoint / 0 pending-writes under
    exit, but many under async."""
    cfg = {"configurable": {"thread_id": "t"}}

    sv_async = _CountingSaver()
    asyncio.run(_build(sv_async).ainvoke(
        {"flags": [], "detect": True, "boom": False}, config=cfg, durability="async"))

    sv_exit = _CountingSaver()
    asyncio.run(_build(sv_exit).ainvoke(
        {"flags": [], "detect": True, "boom": False}, config=cfg, durability="exit"))

    assert sv_exit.n_checkpoints == 1
    assert sv_exit.n_writes == 0
    assert sv_async.n_checkpoints > sv_exit.n_checkpoints  # many vs one


@pytest.mark.parametrize("durability", ["async", "exit"])
def test_flag_retained_on_crashed_turn(durability):
    """Safety property: a flag set at node 1 of a turn that crashes before the terminal
    node is retained under BOTH modes. Under exit this works via the recorded pending
    write — guards against a regression that would silently drop it."""
    graph = _build(_CountingSaver())
    cfg = {"configurable": {"thread_id": "t"}}

    with pytest.raises(RuntimeError):
        asyncio.run(graph.ainvoke(
            {"flags": [], "detect": True, "boom": True}, config=cfg, durability=durability))

    snap = graph.get_state(cfg)
    assert snap.values.get("flags") == ["substance_use"]


def test_exit_preserves_flag_after_successful_turn():
    """Cross-turn memory on a SUCCESSFUL turn is preserved under exit (the product
    property the latency fix must not break)."""
    graph = _build(_CountingSaver())
    cfg = {"configurable": {"thread_id": "t"}}

    asyncio.run(graph.ainvoke(
        {"flags": [], "detect": True, "boom": False}, config=cfg, durability="exit"))
    snap = graph.get_state(cfg)
    assert snap.values.get("flags") == ["substance_use"]
