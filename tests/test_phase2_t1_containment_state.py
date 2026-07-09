"""Phase 2 T1 — containment_directive state scaffolding (default-OFF / inert).

The field exists and resets per turn; NOTHING sets it yet (T2 contain-action + T3 edge come next).
So this is the inert scaffolding: a real deploy of T1 must be behavior-identical to master (the flip
is gated on T2-T4 + the safeguarding sign-offs, per the never-build-live-ahead-of-sign-off rule).
"""
from sage_poc.state import SageState


def test_field_declared_optional():
    # declared in the TypedDict so LangGraph's reducer carries it (the lesson from crisis_tier being dropped)
    assert "containment_directive" in SageState.__annotations__, \
        "containment_directive must be a declared channel or the reducer drops it"


def test_default_none_inert(server_state_builder=None):
    # a freshly built turn state has containment_directive None (inert) — nothing sets it in T1
    import inspect
    from sage_poc import server_helpers
    src = inspect.getsource(server_helpers)
    assert '"containment_directive": None' in src, "must reset to None per-turn (inert until T2-T4)"
