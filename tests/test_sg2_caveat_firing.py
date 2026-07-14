"""SG-2 firing fix — the mandatory contraindication caveat is delivered DETERMINISTICALLY by the
gate, bypassing LLM discretion (Cardinal Rule: the LLM renders language, it does NOT decide whether
safety copy fires). Content-in-JSON is NECESSARY BUT NOT SUFFICIENT — the driven transcript
(2026-07-10, prod) showed the LLM dropping the caveat and suggesting cold water without the screen.
This fix + these tests guarantee firing, and the firing test asserts the caveat leads (before any
temperature/exercise content). Generalizes to any step carrying `mandatory_caveat` (the class fix).
"""
from sage_poc.nodes.output_gate import _pin_contraindication_caveat
from sage_poc.skills.schema import load_skill


def test_gate_prepends_caveat_ahead_of_technique_content():
    caveat = ("Please check before trying this: the temperature step can slow the heart rate; "
              "if you have a heart condition or you're pregnant, skip those two steps.")
    llm_reply = "Let's get cold water on your wrists for 30 seconds, tell me when you've done it."
    out = _pin_contraindication_caveat(llm_reply, caveat)
    assert out.startswith(caveat), "caveat must lead — ahead of any temperature/exercise instruction"
    assert "cold water" in out, "technique content preserved after the caveat"


def test_gate_noop_when_step_has_no_caveat():
    assert _pin_contraindication_caveat("hello", "") == "hello"
    assert _pin_contraindication_caveat("hello", None) == "hello"


def test_gate_idempotent_if_caveat_already_surfaced():
    caveat = "Please check before trying this: skip the temperature and exercise steps if pregnant."
    already = caveat + " Now, when you're ready, breathe slowly."
    assert _pin_contraindication_caveat(already, caveat) == already, "must not double the caveat"


def test_dbt_tipp_entry_screen_carries_mandatory_caveat():
    entry = next(s for s in load_skill("dbt_tipp").steps if s.step_id == "entry_screen")
    cav = entry.mandatory_caveat
    assert "heart condition" in cav and "pregnant" in cav and "skip those two steps" in cav, (
        "the TIPP entry screen must carry the verbatim cardiac/pregnancy caveat as mandatory copy"
    )
