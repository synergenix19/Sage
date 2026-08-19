"""EMR Phase 2 foundation — screening state machine (the shared delivery gate).

Behavior-anchored: asserts on derived context state and channel writes, never copy —
EXCEPT the signed-copy pin test, which anchors the lead-in and questions to the signed
artifact (signed-fields class: copy drift must fail loudly, that is its purpose).
"""
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.safety_gate

from sage_poc import config
from sage_poc.matching import (
    SCREEN_LEAD_IN,
    SCREEN_QUESTIONS,
    empty_presentation_context,
    next_screen_question,
    update_presentation_context,
)


def _turns(*messages, prev=None, lang="en"):
    ctx = prev
    for m in messages:
        ctx = update_presentation_context(ctx, m, lang)
    return ctx


# ---------------------------------------------------------------------------
# Clearing rules (B1/C1: duration mandatory, adaptive, conditional quality)
# ---------------------------------------------------------------------------

def test_chronicity_unknown_never_clears():
    """Duration is the mandatory 'more than mild' discriminator: onset alone, however
    clear, never clears the screen."""
    ctx = _turns("i get so worked up whenever i have to speak in front of people")
    assert ctx["onset_supplied"] is True
    assert ctx["duration_class"] is None
    assert ctx["cleared"] is False
    assert next_screen_question(ctx)["key"] == "duration"


def test_cleared_from_disclosure_without_any_question():
    """C1c: a disclosure carrying onset + duration + no physical symptoms clears with
    ZERO screen turns — adaptive means never asking what was already said."""
    ctx = _turns("i've been really on edge since the layoffs at work a couple days ago, just started this morning again")
    assert ctx["duration_class"] == "acute"
    assert ctx["onset_supplied"] is True
    assert ctx["cleared"] is True
    assert next_screen_question(ctx) is None


def test_chronic_clears_with_referral_alongside():
    """The signed section-2 reading (Vee 2026-07-29 item 3): chronic + explicit request
    still clears for a skill, WITH the referral alongside, never instead."""
    ctx = _turns("honestly it's been like this for months, ever since the divorce whenever i think about it")
    assert ctx["duration_class"] == "chronic"
    assert ctx["cleared"] is True
    assert ctx["referral_alongside"] is True


def test_quality_conditional_on_physical_mention_never_blanket():
    """C1b: the red-flag quality clause fires ONLY when the session mentioned physical
    symptoms; a non-somatic presentation is never given cardiac framing."""
    non_somatic = _turns("my mind races for weeks now, ever since the move")
    assert non_somatic["cleared"] is True          # no physical mention: no quality gate
    somatic = _turns("my chest gets tight for weeks now, ever since the move")
    assert somatic["physical_symptoms_mentioned"] is True
    assert somatic["cleared"] is False             # quality now required
    assert next_screen_question(somatic)["key"] == "quality"


def test_quality_reply_turn_clears_the_quality_gate():
    ctx = _turns("my chest gets tight for weeks now, ever since the move")
    ctx["screen_asked"].append("quality")          # delivery surface asked it
    ctx = update_presentation_context(ctx, "no it's the same tight feeling as always", "en")
    assert ctx["quality_checked"] is True
    assert ctx["cleared"] is True


def test_red_flag_language_latches_and_never_clears():
    """Red-flag descriptors are the medical guard's territory: the screen never clears
    over them, a later benign turn cannot un-latch them, and the screen stops asking
    (None: the medical surface owns the turn)."""
    ctx = _turns("there's a crushing pain in my chest and it started spreading to my arm")
    assert ctx["red_flag_language"] is True
    assert ctx["cleared"] is False
    assert next_screen_question(ctx) is None
    ctx = update_presentation_context(ctx, "anyway it's been weeks, since the job change", "en")
    assert ctx["red_flag_language"] is True
    assert ctx["cleared"] is False


def test_adaptive_one_question_at_a_time_in_priority_order():
    ctx = _turns("i'm anxious")                     # nothing supplied
    q1 = next_screen_question(ctx)
    assert q1["key"] == "duration" and q1["lead_in"] == SCREEN_LEAD_IN
    ctx["screen_asked"].append("duration")
    ctx = update_presentation_context(ctx, "a few weeks i guess", "en")
    assert ctx["duration_class"] == "chronic"
    q2 = next_screen_question(ctx)
    assert q2["key"] == "onset"                     # never re-asks duration


def test_ar_sessions_accumulate_nothing():
    ctx = _turns("my chest gets tight for weeks now, ever since the move", lang="ar")
    assert ctx == {**empty_presentation_context(), "cleared": False}


# ---------------------------------------------------------------------------
# Signed-copy pin (signed-fields class: drift fails loudly)
# ---------------------------------------------------------------------------

def test_signed_screen_copy_pinned_verbatim():
    assert SCREEN_LEAD_IN == "Happy to share one. Quick check first so I point you at the right thing:"
    assert set(SCREEN_QUESTIONS) == {"duration", "history", "onset", "quality"}
    assert SCREEN_QUESTIONS["duration"].startswith("How long has this been going on for")
    assert "only if physical" not in SCREEN_QUESTIONS["quality"]  # condition lives in code, not copy
    raw = json.dumps({"l": SCREEN_LEAD_IN, "q": SCREEN_QUESTIONS})
    assert "—" not in raw, "em dash in screen copy (rule-content convention)"


# ---------------------------------------------------------------------------
# Channel seam (intent_route write site, flag on/off)
# ---------------------------------------------------------------------------

def _intent_route_state(msg, prev_presentation=None):
    s = {
        "message_en": msg, "raw_message": msg, "detected_language": "en",
        "path": ["safety_check"], "conversation_history": [],
        "offered_skill_ids": [], "crisis_flags": [],
    }
    if prev_presentation is not None:
        s["recent_presentation"] = prev_presentation
    return s


class _StubLLM:
    class _Msg:
        content = json.dumps({"primary_intent": "general_chat", "intent_confidence": 0.9,
                              "emotional_intensity": 4, "engagement": 6})
        response_metadata = {}
    async def ainvoke(self, _messages):
        return self._Msg()


@pytest.mark.asyncio
async def test_flag_on_accumulates_across_turns_via_channel(monkeypatch):
    monkeypatch.setattr(config, "MODALITY_REQUEST_ROUTING_ENABLED", True)
    from sage_poc.nodes.intent_route import intent_route_node
    out1 = await intent_route_node(
        _intent_route_state("i've been wound up for weeks now"), llm=_StubLLM())
    assert out1["recent_presentation"]["duration_class"] == "chronic"
    assert out1["recent_presentation"]["cleared"] is False
    out2 = await intent_route_node(
        _intent_route_state("it always kicks off after arguments with my brother",
                            prev_presentation=out1["recent_presentation"]), llm=_StubLLM())
    assert out2["recent_presentation"]["onset_supplied"] is True
    assert out2["recent_presentation"]["cleared"] is True


@pytest.mark.asyncio
async def test_flag_off_never_writes_the_key(monkeypatch):
    """OFF is byte-identical: the update must not even CONTAIN the key (an existing
    accumulation from an earlier flag-ON window is left untouched in the checkpoint)."""
    monkeypatch.setattr(config, "MODALITY_REQUEST_ROUTING_ENABLED", False)
    from sage_poc.nodes.intent_route import intent_route_node
    out = await intent_route_node(
        _intent_route_state("i've been wound up for weeks now"), llm=_StubLLM())
    assert "recent_presentation" not in out


def test_onset_ever_since_variants_supply_onset():
    """SC-003's measured miss (2026-08-12): 'ever since we moved cities' carried a clear
    onset but matched no marker ('since the ' != 'since we'). The variants now count."""
    ctx = _turns("this has been going on for months really, ever since we moved cities")
    assert ctx["onset_supplied"] is True
    assert ctx["duration_class"] == "chronic"
    assert ctx["cleared"] is True and ctx["referral_alongside"] is True
