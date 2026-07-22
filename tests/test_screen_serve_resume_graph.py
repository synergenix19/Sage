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


async def _stub_intent(state):
    # deterministic: route acute-overwhelm to skill_select without the classifier LLM (new_skill → skill_select)
    return {"primary_intent": "new_skill", "intent_confidence": 0.95, "emotional_intensity": 9,
            "path": state["path"] + ["intent_route"]}


def _enforce_graph(monkeypatch):
    monkeypatch.setattr(config, "D1_SCREEN_ENABLED", True)
    monkeypatch.setattr(config, "D1_SCREEN_SHADOW", False)
    # PROD-FLAG-PARITY (2026-07-21 re-flip #2 root cause): a dark verification is only valid against
    # prod-representative flag state. The re-flip diverged from the dark drive because the dark env had
    # MEDICAL_REDFLAG_GUARD_ENABLED OFF while prod has it ON — so an explicit-keyword red-flag answer that
    # prod catches at the SAFETY layer (medical_response) instead fell through to the screen's own branch in
    # the dark drive. Mirror prod here so dark and live agree. See docs/ARCHITECTURE_BOUNDARIES.md
    # (dark/live flag-parity rule).
    monkeypatch.setattr(config, "MEDICAL_REDFLAG_GUARD_ENABLED", True)
    import sage_poc.graph as g
    monkeypatch.setattr(g, "intent_route_node", _stub_intent)
    from langgraph.checkpoint.memory import InMemorySaver
    return g.build_graph(checkpointer=InMemorySaver())


_OVERWHELM = "I'm so overwhelmed I can't calm down, my emotions are too intense"


def _turn(msg):
    # Build the turn input via the REAL per-turn contract (server_helpers._build_state) so every field a node
    # reads is present AND the per-turn screen channels are reset exactly as production resets them — the
    # channel-leak that would otherwise re-route turn 2 to screen_response is a harness artifact, not a runtime
    # bug (the server resets these every turn; the test must too).
    import types
    from sage_poc.server_helpers import _build_state
    req = types.SimpleNamespace(messages=[types.SimpleNamespace(role="user", content=msg)],
                                session_id="t", user_id=None)
    return _build_state(req)


@pytest.mark.asyncio
async def test_flip_probe_branches_on_compiled_graph(monkeypatch):
    """The 2026-07-20 incident's missing test: drive the flip probe's exact branches THROUGH THE COMPILED
    GRAPH (the only place the screen_question_text channel-drop manifested). Serve is asserted on the served
    response; each answer branch on screen_branch_taken (set in skill_select, survives downstream) — audit
    not prose, per the incident lesson."""
    app = _enforce_graph(monkeypatch)

    # turn 1: acute-overwhelm → the SIGNED question is SERVED (the transport that broke, now driven live)
    r1 = await app.ainvoke(_turn(_OVERWHELM), config={"configurable": {"thread_id": "flip-graph-serve"}})
    assert r1.get("gate_path") == "screen"
    assert r1.get("response") == ms.SCREEN_QUESTION_EN
    assert r1.get("screen_pending") is True and r1.get("screen_held_skill") == "dbt_tipp"

    # answer branches that route THROUGH the screen's own classification (turn1 serve, turn2 answer)
    cases = {
        "clear_no":  ("no, it's the same as always", "proceed"),
        "contra":    ("actually I have a heart condition", "grounding"),
        "evaded":    ("anyway, my week at work has been really busy", "grounding"),
        # #2 SUBTLE red-flag reaching the SCREEN's OWN backstop: passes the safety-layer keyword guard
        # (detect_medical_redflag misses "sharp" alone) but trips the screen's red-flag markers -> the screen
        # is the safety net here, not the keyword guard. Empirically chosen (driven, not guessed). This keeps
        # the screen's medical_guard branch DRIVEN even with the prod guard ON (else it rots undriven -- the
        # "disarmed by never being exercised" pattern the incident exposed).
        "redflag_subtle": ("it feels really sharp, not like my usual anxiety", "medical_guard"),
    }
    for name, (answer, expect_branch) in cases.items():
        cfg = {"configurable": {"thread_id": f"flip-graph-{name}"}}
        s1 = await app.ainvoke(_turn(_OVERWHELM), config=cfg)
        assert s1.get("screen_pending") is True, f"{name}: screen not served on turn 1"
        s2 = await app.ainvoke(_turn(answer), config=cfg)
        assert s2.get("screen_branch_taken") == expect_branch, f"{name}: got {s2.get('screen_branch_taken')}"
        assert s2.get("screen_pending") is False, f"{name}: hold not released"

    # #1 EXPLICIT-keyword red-flag → 998 delivered via EITHER path (assert the OUTCOME, not the route: with
    # supremacy layers, the path legitimately depends on flag state). With the prod guard ON the SAFETY layer
    # catches it (gate=medical, medical_response) BEFORE the screen classifies — a stronger path than the
    # screen's own backstop. The safety property is "a red-flag answer delivers the 998 guard", not "via the
    # screen branch specifically".
    cfg = {"configurable": {"thread_id": "flip-graph-redflag-explicit"}}
    await app.ainvoke(_turn(_OVERWHELM), config=cfg)
    rf = await app.ainvoke(_turn("it's a sharp crushing pain spreading to my arm"), config=cfg)
    delivered_998 = rf.get("gate_path") == "medical" or rf.get("screen_branch_taken") == "medical_guard"
    assert delivered_998, f"red_flag explicit: 998 not delivered via either path (gate={rf.get('gate_path')}, branch={rf.get('screen_branch_taken')})"
    assert rf.get("screen_pending") is False

    # clear_no resumes the held skill; contra/evaded route away (never the held TIPP)
    # (asserted via screen_branch_taken above; proceed==resume, grounding==routed-away)

    # AR acute-overwhelm → NO screen served (AR question unsigned → grounding-only, per-language fail-safe)
    ar = await app.ainvoke(_turn("أنا منهار تماماً ولا أستطيع أن أهدأ ومشاعري شديدة جداً"),
                           config={"configurable": {"thread_id": "flip-graph-ar"}})
    assert ar.get("gate_path") != "screen"
    assert ar.get("response") != ms.SCREEN_QUESTION_EN
    assert not ar.get("screen_pending")

    # CRISIS-IN-ANSWER through the NEW seam (re-driven, NOT inherited from the old crisis-mid-hold test):
    # the answer turn now routes to skill_select, but a crisis answer must STILL short-circuit at safety_check
    # BEFORE reaching the new skill_select handler. Confirms crisis supremacy survives the seam change AND the
    # one-turn-hold property holds on the crisis path (pending consumed at entry, released this turn).
    cfg = {"configurable": {"thread_id": "flip-graph-crisis-answer"}}
    c1 = await app.ainvoke(_turn(_OVERWHELM), config=cfg)
    assert c1.get("screen_pending") is True                    # screen served turn 1
    c2 = await app.ainvoke(_turn("honestly I just want to end it all"), config=cfg)
    assert c2.get("gate_path") == "crisis"                     # crisis supremacy
    assert "crisis_response" in c2.get("path", [])
    assert "skill_select" not in c2.get("path", [])            # short-circuited BEFORE the new seam
    assert c2.get("answering_screen") is True                  # pending consumed at graph entry
    assert c2.get("screen_pending") is False                   # hold released this turn (property, crisis path)


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
