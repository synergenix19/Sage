"""PI-SI-001 v2.0.0: blended intent renders the v7 §5.6.1 ORDERED contract.

Guards the mechanism-gap fix. When a secondary intent is present, the composed
prompt must carry the ordered validate-then-inform framing (primary FIRST),
grounding/ABSTAIN-aware when the secondary need is information — not the old
generic symmetric "both are valid" DBT frame. Single-intent turns
(secondary=null) must not fire the injection at all.
"""
import pytest

from sage_poc.prompts import composer


def _state(**kw):
    base = {
        "message_en": "my chest is tight all the time, what is anxiety anyway",
        "detected_language": "en",
        "primary_intent": "general_chat",   # emotional primary (POC has no emotional_support intent)
        "secondary_intent": "info_request",  # blended: distress + factual question
        "intent_confidence": 0.9,
        "emotional_intensity": 6,
        "engagement": 5,
        "clinical_flags": [],
        "crisis_state": "none",
        "conversation_history": [],
        "active_skill_id": None,
        "step_instruction": None,
        "knowledge_passages": [],
        "path": [],
    }
    base.update(kw)
    return base


def test_secondary_intent_renders_ordered_contract():
    _, user, _ = composer.compose_prompt(_state())
    low = user.lower()
    # Ordered: validate the primary need first, then the secondary — not symmetric.
    assert "respond in order" in low, "PI-SI-001 v2.0.0 ordered framing not injected"
    assert "validate or answer the primary need first" in low
    assert "do not lead with the secondary" in low
    # Grounding / ABSTAIN awareness for the info secondary.
    assert "ground it in the knowledge passages" in low
    assert "say so honestly rather than guessing" in low
    # The superseded v1.0.0 symmetric frame must be gone.
    assert "two things can be true at once" not in low


def test_no_secondary_intent_no_injection():
    _, user, _ = composer.compose_prompt(_state(secondary_intent=None))
    assert "respond in order" not in user.lower(), (
        "PI-SI-001 must fire only when a secondary intent is present"
    )
