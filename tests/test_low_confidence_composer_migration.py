"""RED-first tests for the low_confidence -> compose_prompt migration.

The low_confidence path historically used a hardcoded _SYSTEM prompt and
bypassed compose_prompt entirely — a v7 §5.6.3 violation (L0 never composed
on this surface). These tests pin the migration:

  1. L0 persona must be COMPOSED on the low_confidence path.
  2. The frozen behavioural constraint (one gentle clarifying question, at
     most two sentences) must SURVIVE the migration, now carried by the
     low_confidence L2 template rather than a hardcoded string.

This PR is mechanism-only: no engagement/content redesign travels with it.
The real content rewrite of the low_confidence template is a separate,
clinically-reviewed batch item.
"""
import pytest
from unittest.mock import MagicMock

from sage_poc.nodes.low_confidence_respond import low_confidence_respond_node


def _make_state(**kw):
    defaults = {
        "raw_message": "I don't know... maybe",
        "message_en": "I don't know... maybe",
        "detected_language": "en",
        "primary_intent": "general_chat",   # low_confidence is a routing outcome, not an intent
        "secondary_intent": None,
        "intent_confidence": 0.4,           # < 0.6 => routed to low_confidence
        "emotional_intensity": 5,
        "engagement": 5,
        "clinical_flags": [],
        "crisis_state": "none",
        "conversation_history": [],
        "path": [],
    }
    return {**defaults, **kw}


async def _run_and_capture(state) -> list:
    """Invoke the node with a stub streaming LLM; return the composed messages."""
    captured: dict = {}

    async def _fake_astream(messages):
        captured["messages"] = messages
        yield MagicMock(content="Could you say a little more about what's on your mind?")

    mock_llm = MagicMock()
    mock_llm.astream = _fake_astream
    await low_confidence_respond_node(state, llm=mock_llm)
    return captured["messages"]


@pytest.mark.asyncio
async def test_low_confidence_composes_l0_persona():
    """L0 persona must be composed on the low_confidence path (was bypassed).

    'SAFETY BEFORE ADVICE' is an L0-distinctive header that never appeared in
    the old hardcoded _SYSTEM prompt; its presence proves compose_prompt now
    feeds this surface.
    """
    messages = await _run_and_capture(_make_state())
    system = messages[0]["content"]
    assert "SAFETY BEFORE ADVICE" in system, (
        "L0 persona is not composed on the low_confidence path — the node is "
        "still bypassing compose_prompt"
    )


@pytest.mark.asyncio
async def test_low_confidence_preserves_clarifying_and_brevity_constraint():
    """Behaviour-frozen: the one-question + max-two-sentences constraint must
    survive the migration, now carried by the low_confidence L2 template in the
    user role (not a hardcoded system string)."""
    messages = await _run_and_capture(_make_state())
    user = messages[1]["content"].lower()
    assert "clarifying question" in user, "lost the single-clarifying-question constraint"
    assert "two sentences" in user, "lost the max-two-sentences brevity cap"


@pytest.mark.asyncio
async def test_low_confidence_does_not_inject_freeflow_shape():
    """low_confidence is NOT a freeflow turn: the freeflow-only MID_FREEFLOW_SHAPE
    (three-or-four sentences / 40-80 words, fires at intensity 4-6) must not be
    composed here — it would directly contradict the max-two-sentences clarifying
    contract. Guards against the compose_prompt migration silently changing the
    low_confidence response shape."""
    messages = await _run_and_capture(_make_state(emotional_intensity=5))
    full = " ".join(m["content"] for m in messages).lower()
    assert "three or four sentences" not in full, "freeflow MID shape leaked into low_confidence"
    assert "forty to eighty words" not in full, "freeflow MID shape leaked into low_confidence"
