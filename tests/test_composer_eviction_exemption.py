"""Task 3: on a self_reference recall turn, the overflow shrink must not evict the disclosure
the user is asking about, and must surface (not silently ship) an unavoidable over-budget prompt."""
from sage_poc.prompts.composer import compose_prompt


def _state(**kw):
    base = dict(
        message_en="...", raw_message="...", detected_language="en", self_reference=True,
        conversation_summary=None, active_skill_id=None, executed_step_id=None, step_instruction=None,
        primary_intent="general_chat", secondary_intent=None, emotional_intensity=5, engagement=5,
        clinical_flags=[], crisis_state="none", crisis_flags=[], therapeutic_profile=None,
        knowledge_passages=[], knowledge_abstain=False, path=[], directive_posture=False,
        stall_detected=False, declined_skills=[],
    )
    base.update(kw)
    return base


_PAD = [{"role": "user", "content": "word " * 500}, {"role": "assistant", "content": "reply " * 500}] * 2


def test_recall_keeps_keyword_anchored_disclosure_under_overflow():
    disclosure = "things at home with my husband have gotten scary"
    state = _state(message_en="what did I just say about my husband?",
                   conversation_history=[{"role": "user", "content": disclosure},
                                         {"role": "assistant", "content": "thank you."}] + _PAD)
    _, user, _ = compose_prompt(state)
    assert disclosure in user            # anchored disclosure survives overflow eviction


def test_recall_keeps_arabic_anchored_disclosure_under_overflow():
    # Arabic parity: anchor must be computed from raw_message/Arabic history, not message_en.
    disclosure = "الوضع في البيت مع زوجي صار مخيف"
    state = _state(message_en="(ar)", raw_message="ماذا قلت لك عن زوجي؟", detected_language="ar",
                   message_en_unused=None,
                   conversation_history=[{"role": "user", "content": disclosure},
                                         {"role": "assistant", "content": "شكرا لمشاركتك."}] + _PAD)
    _, user, _ = compose_prompt(state)
    assert "زوجي" in user                # Arabic disclosure survives via raw_message anchor


def test_non_recall_turn_is_unchanged_under_overflow():
    # pin_turn is None when self_reference is False -> original eviction behaviour preserved.
    disclosure = "things at home with my husband have gotten scary"
    state = _state(self_reference=False, message_en="ok",
                   conversation_history=[{"role": "user", "content": disclosure},
                                         {"role": "assistant", "content": "thank you."}] + _PAD)
    _, user, _ = compose_prompt(state)
    assert disclosure not in user        # without self_reference, the old turn still evicts (unchanged)


def test_over_budget_recall_surfaces_status_not_silent():
    disclosure = "my husband has been violent toward me again last night " * 12  # ~120 words
    big = disclosure * 6                                                          # forces over-budget even when pinned
    state = _state(message_en="what did I just say about my husband?",
                   conversation_history=[{"role": "user", "content": big},
                                         {"role": "assistant", "content": "ok."}])
    _, user, layers = compose_prompt(state)
    assert "my husband has been violent" in user        # disclosure never dropped on a recall turn
    assert "status:prompt_over_budget" in layers         # observable, status-prefixed, not a content layer
