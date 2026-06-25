from sage_poc.prompts.composer import memory_absent_sentinel


def _s(**k):
    base = {"self_reference": True, "detected_language": "en",
            "message_en": "what did I just tell you about my husband?", "raw_message": "...",
            "conversation_history": []}
    base.update(k); return base


def test_sentinel_fires_when_recall_and_no_grounding():
    assert memory_absent_sentinel(_s(), prior_context_present=False) is not None


def test_no_sentinel_when_disclosure_present_in_history():
    s = _s(conversation_history=[{"role": "user", "content": "things at home with my husband have gotten scary"},
                                 {"role": "assistant", "content": "thank you"}])
    assert memory_absent_sentinel(s, prior_context_present=False) is None


def test_no_sentinel_when_history_exists_but_unrelated():
    # BACK-DOOR PROTECTION: history present, no keyword match to the recall. Must NOT fire,
    # else it asserts "I can't see that" over real history = false-denial reintroduced.
    s = _s(conversation_history=[{"role": "user", "content": "work has been really stressful this week"},
                                 {"role": "assistant", "content": "that sounds hard"}])
    assert memory_absent_sentinel(s, prior_context_present=False) is None


def test_no_sentinel_when_prior_context_exists():
    assert memory_absent_sentinel(_s(), prior_context_present=True) is None


def test_no_sentinel_when_not_a_recall():
    assert memory_absent_sentinel(_s(self_reference=False), prior_context_present=False) is None
