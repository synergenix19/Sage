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
