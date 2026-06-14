from sage_poc.nodes.directive_detect import detect_directive_request


def _state(message_en, history=None):
    return {"message_en": message_en, "conversation_history": history or []}


def test_explicit_delegation_phrases_detected():
    for phrase in [
        "just tell me what to do",
        "you tell me",
        "you decide",
        "you pick",
        "I want answers, not questions",
        "stop asking me questions",
        "you need to guide me, not ask me",
        "you're the one with the answers",
        "I don't need more questions",
    ]:
        assert detect_directive_request(_state(phrase)) is True, f"missed: {phrase!r}"


def test_frustration_repair_signal_after_a_question():
    history = [
        {"role": "user", "content": "my dad reacted badly"},
        {"role": "assistant", "content": "How does that usually affect you?"},
    ]
    assert detect_directive_request(_state("why do you keep questioning me", history)) is True


def test_repair_signal_requires_prior_question():
    history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "I'm here with you."},
    ]
    assert detect_directive_request(_state("why", history)) is False


def test_genuine_first_question_is_not_directive():
    for phrase in [
        "How do I deal with my father's response like this?",
        "what should I think about here",
        "I feel anxious",
        "can you help me understand why I feel this way",
    ]:
        assert detect_directive_request(_state(phrase)) is False, f"false positive: {phrase!r}"
