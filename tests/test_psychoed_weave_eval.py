# tests/test_psychoed_weave_eval.py
from sage_poc.psychoed import weave
import pytest

pytestmark = pytest.mark.safety_gate

OK = ["No", "no, nothing like that", "No, alhamdulillah", "no I haven't, why?", "no thank god"]
BAD = ["kind of", "sometimes", "not really but...", "no, but sometimes",
       "actually, what is anxiety?", "yes", "i don't know", ""]

def test_clear_negatives_proceed():
    for r in OK:
        assert weave.evaluate(r) == "proceed", r

def test_everything_else_fails_closed():
    for r in BAD:
        assert weave.evaluate(r) == "crisis", r

def test_driven_by_data_not_code():
    import inspect
    src = inspect.getsource(weave)
    assert "alhamdulillah" not in src  # patterns live in data, not code

def test_default_not_fail_closed_raises_not_silently_passes(monkeypatch):
    """The fail-closed invariant check must be a real, non-optimizable raise, not `assert`
    (which `python -O` strips entirely). Simulate the invariant being violated (a corrupted
    or mis-authored evaluation_semantics.default) and confirm is_clear_negative/evaluate
    raise loudly instead of silently returning a value -- PSY-WEAVE-1 is on the
    crisis-escalation path, so this must never be optimizable away or fail open."""
    real_data = weave.store.weave_data()
    tampered = {**real_data, "evaluation_semantics": {**real_data["evaluation_semantics"], "default": "fail_open"}}
    monkeypatch.setattr(weave.store, "weave_data", lambda: tampered)

    with pytest.raises(RuntimeError, match="fail_closed_to_crisis"):
        weave.is_clear_negative("no")
    with pytest.raises(RuntimeError, match="fail_closed_to_crisis"):
        weave.evaluate("no")
