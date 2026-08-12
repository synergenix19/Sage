"""EMR Phase 2 surface 2 — info_request early-return consumer.

The defect this surface closes: an explicit modality request the classifier labels
info_request fell into the KB short-circuit (abstain -> freeflow, request dropped).
Behavior-anchored; every guard asserts the POSITIVE alternative path (C3), never
silence.
"""
import pytest

from sage_poc import config
from sage_poc.matching import SCREEN_LEAD_IN, empty_presentation_context
from sage_poc.nodes.skill_select import skill_select_node


def _state(msg="are there any exercises i can do", *, emr=None, ctx=None, declined=None,
           active=None, intent="info_request"):
    return {
        "message_en": msg, "raw_message": msg, "detected_language": "en",
        "primary_intent": intent, "path": ["safety_check", "intent_route"],
        "active_skill_id": active, "active_step_id": None,
        "offered_skill_ids": [], "declined_skills": declined or [],
        "clinical_flags": [], "crisis_flags": [], "conversation_history": [],
        "turn_count": 3,
        "explicit_modality_request": emr,
        "recent_presentation": ctx,
    }


def _cleared_ctx(**over):
    ctx = empty_presentation_context()
    ctx.update({"duration_class": "acute", "onset_supplied": True, "cleared": True})
    ctx.update(over)
    return ctx


@pytest.fixture(autouse=True)
def _flag_on(monkeypatch):
    monkeypatch.setattr(config, "MODALITY_REQUEST_ROUTING_ENABLED", True)


@pytest.mark.asyncio
async def test_cleared_request_offers_first_line_pair_not_kb():
    out = await skill_select_node(_state(
        emr={"requested": True, "modality_hint": None}, ctx=_cleared_ctx()))
    assert out["offered_skill_ids"] == ["box_breathing", "grounding_5_4_3_2_1"]
    assert out["skill_match_method"] == "modality_request_offer"
    assert "modality_request_routed:info_request" in out["path"]
    assert "skill_offer_made" in out["path"]
    assert out["active_skill_id"] is None            # offer, never activation (R1 consent)


@pytest.mark.asyncio
async def test_modality_hint_narrows_the_offer():
    out = await skill_select_node(_state(
        emr={"requested": True, "modality_hint": "breathing"}, ctx=_cleared_ctx()))
    assert out["offered_skill_ids"] == ["box_breathing"]


@pytest.mark.asyncio
async def test_chronic_cleared_offers_with_referral_context_marker():
    """The signed 'alongside' reading: chronic still gets the offer, plus the referral
    context marker the delivery layer renders alongside, never instead."""
    out = await skill_select_node(_state(
        emr={"requested": True, "modality_hint": None},
        ctx=_cleared_ctx(duration_class="chronic", referral_alongside=True)))
    assert out["offered_skill_ids"] == ["box_breathing", "grounding_5_4_3_2_1"]
    assert "modality_request_referral_context" in out["path"]


@pytest.mark.asyncio
async def test_declined_filtering_preserved_and_partial_offer():
    out = await skill_select_node(_state(
        emr={"requested": True, "modality_hint": None}, ctx=_cleared_ctx(),
        declined=["box_breathing"]))
    assert out["offered_skill_ids"] == ["grounding_5_4_3_2_1"]


@pytest.mark.asyncio
async def test_all_candidates_declined_falls_through_to_kb():
    """R1 declined semantics outrank the request: both first-line skills declined this
    session -> the request falls to the KB path (positive: the KB-bound shape, not a
    re-offer of a declined skill)."""
    out = await skill_select_node(_state(
        emr={"requested": True, "modality_hint": None}, ctx=_cleared_ctx(),
        declined=["box_breathing", "grounding_5_4_3_2_1"]))
    assert not out.get("offered_skill_ids")
    assert out["skill_match_method"] is None          # KB-bound result, unchanged shape
    assert "modality_request_routed:info_request" not in out["path"]


@pytest.mark.asyncio
async def test_unscreened_request_serves_signed_screen_question_verbatim():
    """Not cleared -> the signed screen question goes out through the D1 verbatim
    terminal (screen_question_text set, duration first), the asked key is recorded in
    the channel, and no offer is made."""
    out = await skill_select_node(_state(
        emr={"requested": True, "modality_hint": None}, ctx=None))
    assert out["screen_question_text"].startswith(SCREEN_LEAD_IN)
    assert "How long has this been going on for" in out["screen_question_text"]
    assert "modality_request_screen_pending" in out["path"]
    assert out["recent_presentation"]["screen_asked"] == ["duration"]
    assert not out.get("offered_skill_ids")


@pytest.mark.asyncio
async def test_red_flag_context_yields_to_medical_surface_kb_path_unchanged():
    """Red-flag language: the screen goes silent and the request is NOT offered — the
    positive path is the unchanged KB-bound result this turn (the medical guard owns
    red-flag adjudication upstream/downstream, not this surface)."""
    ctx = empty_presentation_context()
    ctx["red_flag_language"] = True
    out = await skill_select_node(_state(
        emr={"requested": True, "modality_hint": None}, ctx=ctx))
    assert "screen_question_text" not in out
    assert not out.get("offered_skill_ids")
    assert out["skill_match_method"] is None


@pytest.mark.asyncio
async def test_genuine_info_ask_reaches_kb_exactly_as_today():
    """C3 guard, the surface's reason-to-exist inverted: requested=False (a real info
    ask) -> the KB-bound result, byte-identical shape, no screen, no offer."""
    out = await skill_select_node(_state(
        "what is the crisis helpline number?",
        emr={"requested": False, "modality_hint": None}, ctx=_cleared_ctx()))
    assert out["skill_match_method"] is None
    assert "screen_question_text" not in out
    assert not out.get("offered_skill_ids")


@pytest.mark.asyncio
async def test_flag_off_is_byte_identical_even_with_request_channel_set(monkeypatch):
    monkeypatch.setattr(config, "MODALITY_REQUEST_ROUTING_ENABLED", False)
    out = await skill_select_node(_state(
        emr={"requested": True, "modality_hint": None}, ctx=_cleared_ctx()))
    assert out["skill_match_method"] is None
    assert "screen_question_text" not in out
    assert not out.get("offered_skill_ids")
    assert "modality_request_routed:info_request" not in out["path"]


@pytest.mark.asyncio
async def test_mid_skill_info_request_untouched_surface1_territory():
    """An info_request arriving with an ACTIVE skill is surface-1 (executor) territory;
    surface 2 must not fire (positive: the existing preserve-active shape returns)."""
    out = await skill_select_node(_state(
        emr={"requested": True, "modality_hint": None}, ctx=_cleared_ctx(),
        active="psychoed_anxiety"))
    assert "active_skill_id" not in out or out.get("active_skill_id") != "box_breathing"
    assert not out.get("offered_skill_ids")
    assert "modality_request_routed:info_request" not in out["path"]


# ---------------------------------------------------------------------------
# Screen resumption (2026-08-12; the loop-closure the extension family caught)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_screen_serve_holds_request_and_does_not_arm_d1():
    """The screen turn writes modality_screen_pending (the request survives) and must
    NOT set D1's screen_pending — the crossed-wires defect: D1's answer machinery
    processed the duration answer through the contraindication classifier."""
    out = await skill_select_node(_state(
        emr={"requested": True, "modality_hint": "breathing"}, ctx=None))
    assert out["modality_screen_pending"] == {"modality_hint": "breathing"}
    assert "screen_pending" not in out
    from sage_poc.nodes.screen_response import screen_response_node
    served = await screen_response_node({**_state(emr=None), **out, "path": out["path"],
                                         "turn_started_at": None})
    assert served["screen_pending"] is False


@pytest.mark.asyncio
async def test_answer_turn_delivers_held_request_with_hint():
    """The resumption itself: requested=False on the answer turn, but the hold + a now-
    cleared context deliver the hinted offer and release the hold."""
    out = await skill_select_node({
        **_state("it started this afternoon after a rough call with my boss",
                 emr={"requested": False, "modality_hint": None},
                 ctx=_cleared_ctx(), intent="general_chat"),
        "modality_screen_pending": {"modality_hint": "breathing"},
    })
    assert out["offered_skill_ids"] == ["box_breathing"]
    assert out["modality_screen_pending"] is None
    assert "skill_offer_made" in out["path"]


@pytest.mark.asyncio
async def test_answer_turn_not_yet_cleared_asks_next_question_keeps_hold():
    ctx = empty_presentation_context()
    ctx["duration_class"] = "acute"          # duration supplied, onset still missing
    out = await skill_select_node({
        **_state("a few hours i guess", emr={"requested": False, "modality_hint": None},
                 ctx=ctx, intent="general_chat"),
        "modality_screen_pending": {"modality_hint": None},
    })
    assert "screen_question_text" in out
    assert out["modality_screen_pending"] == {"modality_hint": None}


@pytest.mark.asyncio
async def test_exhausted_screen_abandons_hold_honestly():
    """All mandatory questions asked, still not cleared (off-topic answers): the hold
    clears with its own marker and the turn falls to presence — never a silent
    forever-hold, never an unscreened offer."""
    ctx = empty_presentation_context()
    ctx["screen_asked"] = ["duration", "onset"]
    out = await skill_select_node({
        **_state("anyway did you watch the match last night",
                 emr={"requested": False, "modality_hint": None},
                 ctx=ctx, intent="general_chat"),
        "modality_screen_pending": {"modality_hint": None},
    })
    assert out["modality_screen_pending"] is None
    assert "modality_request_screen_abandoned" in out["path"]
    assert not out.get("offered_skill_ids")


def test_router_redirects_pending_answer_turn_to_skill_select(monkeypatch):
    from sage_poc.graph import _route_after_intent
    monkeypatch.setattr(config, "MODALITY_REQUEST_ROUTING_ENABLED", True)
    state = {
        "primary_intent": "general_chat", "intent_confidence": 0.9,
        "active_skill_id": None, "clinical_flags": [], "crisis_flags": [],
        "modality_screen_pending": {"modality_hint": None},
        "explicit_modality_request": {"requested": False, "modality_hint": None},
    }
    assert _route_after_intent(state) == "skill_select"
