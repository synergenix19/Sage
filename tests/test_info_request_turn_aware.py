"""Turn-aware info_request close (D4 amendment, clinical ruling 2026-07-07).

- FIRST single-intent info_request -> one open clarifying QUESTION (Abby-style triage).
- CONSECUTIVE info_request (prev_primary_intent == info_request) -> statement bridge (repeat variant).
- D4 amendment: directive_posture no longer fires on info_request, so the question survives output_gate.

Pairs with test_info_request_bridge_survives_gate.py (the strip-scope pin, which still holds
because the strip remains for genuinely-directive turns of OTHER intents).
"""
from sage_poc.nodes.directive_detect import detect_directive_request
from sage_poc.prompts import composer


def _state(**kw):
    base = {
        "message_en": "what is anxiety", "detected_language": "en",
        "primary_intent": "info_request", "secondary_intent": None,
        "intent_confidence": 1.0, "emotional_intensity": 3, "engagement": 5,
        "clinical_flags": [], "crisis_state": "none", "conversation_history": [],
        "active_skill_id": None, "step_instruction": None,
        "knowledge_passages": [{"text": "Anxiety is the body's response to threat.", "citation": "kb"}],
        "prev_primary_intent": None, "path": [],
    }
    base.update(kw)
    return base


# ---- D4 amendment: directive_posture must NOT fire on info_request anymore ----
def test_directive_posture_no_longer_fires_on_info_request():
    assert detect_directive_request(_state(), primary_intent="info_request") is False


def test_directive_posture_still_fires_on_genuine_delegation():
    # the answer-first strip must still work for real "just tell me what to do" turns
    st = _state(message_en="just tell me what to do", primary_intent="general_chat")
    assert detect_directive_request(st, primary_intent="general_chat") is True


# ---- Composer selects question-base first, statement-repeat on consecutive ----
def test_first_info_request_uses_question_close_base():
    _, user, _ = composer.compose_prompt(_state(prev_primary_intent=None))
    low = user.lower()
    assert "one open, warm clarifying question" in low
    assert "for themselves or in general" in low


def test_consecutive_info_request_uses_statement_repeat_variant():
    _, user, _ = composer.compose_prompt(_state(prev_primary_intent="info_request"))
    low = user.lower()
    assert "consecutive information request" in low  # repeat variant's distinctive phrase
    assert "do not re-ask a clarifying question" in low
    assert "statement and never a question" in low


def test_intervening_intent_resets_to_question_close():
    # prev turn was general_chat -> not consecutive -> base (question), i.e. re-triage after a switch
    _, user, _ = composer.compose_prompt(_state(prev_primary_intent="general_chat"))
    assert "one open, warm clarifying question" in user.lower()
