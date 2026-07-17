"""D1 serve/resume — END-TO-END through the REAL compiled graph (#338). The constraint-1 property driven
live through the graph, not just the mechanism: the served question emits at the screen_response terminal,
and the hold releases in exactly one turn even when turn N+1 is a crisis (the bypass path safety_check's
consume_pending_screen guards). Deterministic terminals only (screen_response, crisis_response) — no LLM.
"""
import pytest
from sage_poc import config
from sage_poc.safety import medical_screen as ms


def test_router_sends_served_question_to_screen_terminal():
    """The graph edge, deterministically (no LLM): a skill_select result carrying screen_question_text
    (set by apply_screen_at_route on ask_screen) routes to the screen_response terminal. Below containment,
    above skill routing. Unreachable with the enforce flag off (screen_question_text never set)."""
    from sage_poc.graph import _route_after_skill_select
    assert _route_after_skill_select({"screen_question_text": ms.SCREEN_QUESTION_EN}) == "screen_response"
    # containment still wins (supremacy above screen)
    assert _route_after_skill_select(
        {"screen_question_text": ms.SCREEN_QUESTION_EN, "containment_directive": {"family": "x"}}
    ) == "knowledge_retrieve"
    # no served question → not the screen terminal (byte-identical to master routing)
    assert _route_after_skill_select({"active_skill_id": "dbt_tipp"}) == "skill_executor"
    assert _route_after_skill_select({}) == "freeflow"


@pytest.mark.asyncio
async def test_crisis_mid_hold_releases_in_one_turn(monkeypatch):
    """PROPERTY through the crisis-bypass path: a crisis on the pending turn routes to crisis (supremacy)
    AND the hold is released the same turn — screen_pending False — because safety_check consumes it at
    graph entry, before the crisis short-circuit. The hold can never outlive one turn."""
    monkeypatch.setattr(config, "D1_SCREEN_ENABLED", True)
    monkeypatch.setattr(config, "D1_SCREEN_SHADOW", False)
    from langgraph.checkpoint.memory import InMemorySaver
    from sage_poc.graph import build_graph
    app = build_graph(checkpointer=InMemorySaver())
    cfg = {"configurable": {"thread_id": "d1-graph-crisis-mid-hold"}}

    # turn 1: overwhelm → screen served, hold set
    r1 = await app.ainvoke({"raw_message": "I'm so overwhelmed I can't calm down", "path": []}, config=cfg)
    assert r1.get("screen_pending") is True

    # turn 2: crisis on the pending turn
    r2 = await app.ainvoke({"raw_message": "I want to end it all", "path": []}, config=cfg)
    assert r2.get("gate_path") == "crisis"                 # crisis supremacy
    assert r2.get("is_safe") is False
    assert r2.get("screen_pending") is False               # PROPERTY: hold released this turn
    assert r2.get("answering_screen") is True              # consumed at entry
