"""PS-2 / OR-5 — 'do I have X' diagnosis requests get the verbatim no-diagnose script
(BOT BEHAVIOUR.docx L694, condition-generic wording); other out-of-scope requests
(medication, prescription) keep the generic scope-refusal copy.

Verbatim source (L694), em-dash -> comma per the no-em-dash-in-output convention:
  "I'm here to help you understand what you're experiencing and offer tools that might
   help, but I'm not able to diagnose any mental health condition. A diagnosis needs a
   full picture from a qualified professional who can properly assess what's going on.
   If you're wondering whether something has a clinical name, that's worth bringing to
   a doctor or therapist directly."
"""
from sage_poc.nodes.output_gate import (
    _scope_refusal_response,
    DIAGNOSIS_DECLINE_RESPONSE,
    SCOPE_REFUSAL_RESPONSE,
)


def test_diagnosis_request_gets_no_diagnose_script():
    for msg in [
        "Do I have depression?",
        "do you think i have bipolar",
        "could I have OCD",
        "can you diagnose me",
    ]:
        assert _scope_refusal_response(msg) == DIAGNOSIS_DECLINE_RESPONSE, msg
    assert "not able to diagnose any mental health condition" in DIAGNOSIS_DECLINE_RESPONSE


def test_non_diagnosis_scope_refusal_keeps_generic():
    for msg in [
        "Can you prescribe me something?",
        "what dose of sertraline should I take",
    ]:
        assert _scope_refusal_response(msg) == SCOPE_REFUSAL_RESPONSE, msg


def test_no_em_dash_in_diagnosis_response():
    # house style + T6 output strip: no em dashes in mirrored output copy
    assert "—" not in DIAGNOSIS_DECLINE_RESPONSE
