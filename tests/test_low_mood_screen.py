"""§3a low-mood validate-first + woven-safety flow.

Task 1: flag + cross-turn state fields (SAGE_LOW_MOOD_SCREEN, screen_stage,
safety_probe_asked). The two state fields are CROSS-TURN — they must NOT be
reset per-turn in server_helpers._build_state, or the SI probe would clear
before the answer turn reads it.

Task 2: skill_select §3a interception (EN-gated). When the flag is ON, the
message is English, no screen is already in progress, and the offerable set
would include behavioral_activation, a deterministic §3a low-mood disclosure
defers that offer (screen_stage="validated") instead of emitting it, so a
later flow (built in other tasks) can validate -> screen -> ask the woven SI
question. This task does NOT build that later flow, only the interception.
"""
import inspect

import pytest

from sage_poc import config
from sage_poc.state import SageState
from sage_poc.nodes.skill_select import skill_select_node
from tests.test_skill_select import _ss_state


def test_flag_defaults_off():
    # Default OFF => byte-identical to today's §3a offer path.
    assert config.LOW_MOOD_SCREEN_ENABLED is False


def test_state_declares_screen_fields():
    assert "screen_stage" in SageState.__annotations__
    assert "safety_probe_asked" in SageState.__annotations__


def test_screen_fields_not_in_per_turn_reset():
    # CROSS-TURN invariant: neither field may appear in _build_state's per-turn
    # reset block, or the probe clears before safety_check reads the answer.
    import sage_poc.server_helpers as sh

    src = inspect.getsource(sh._build_state)
    assert "screen_stage" not in src
    assert "safety_probe_asked" not in src


# ---------------------------------------------------------------------------
# Task 2: is_low_mood_disclosure detection module
# ---------------------------------------------------------------------------


def test_is_low_mood_disclosure_importable():
    from sage_poc.nodes.low_mood_detect import is_low_mood_disclosure

    assert callable(is_low_mood_disclosure)


def test_is_low_mood_disclosure_none_and_empty_are_false():
    from sage_poc.nodes.low_mood_detect import is_low_mood_disclosure

    assert is_low_mood_disclosure(None) is False
    assert is_low_mood_disclosure("") is False


# ---------------------------------------------------------------------------
# AC1 — precision / false-positive set as a first-class deliverable.
# ---------------------------------------------------------------------------

_LOW_MOOD_POSITIVES = [
    "I've lost interest in everything and I can't get myself to do anything anymore",
    "nothing feels enjoyable and I don't have the energy to do anything",
    "I don't want to see anyone, I just want to stay in bed",
]

_LOW_MOOD_NEGATIVES = [
    "meh, bit of a flat day today",
    "I lost interest in the movie halfway through",
    "I'm tired after a long week",
    "bored, what should I do tonight",
]


@pytest.mark.parametrize("phrase", _LOW_MOOD_POSITIVES)
def test_is_low_mood_disclosure_fires_on_positives(phrase):
    from sage_poc.nodes.low_mood_detect import is_low_mood_disclosure

    assert is_low_mood_disclosure(phrase) is True, (
        f"§3a positive not detected: {phrase!r}"
    )


@pytest.mark.parametrize("phrase", _LOW_MOOD_NEGATIVES)
def test_is_low_mood_disclosure_does_not_fire_on_negatives(phrase):
    from sage_poc.nodes.low_mood_detect import is_low_mood_disclosure

    assert is_low_mood_disclosure(phrase) is False, (
        f"False positive: {phrase!r} must NOT be detected as a §3a low-mood disclosure"
    )


def test_low_mood_false_positive_rate_on_negative_set_is_zero():
    """AC1: false-positive rate on the named negative set is its own metric, asserted zero.

    A matcher that over-fires manufactures an SI question for benign users and
    routes them toward a crisis card — false positives are a safety cost here,
    not just noise. Do not weaken _LOW_MOOD_NEGATIVES to make this pass.
    """
    from sage_poc.nodes.low_mood_detect import is_low_mood_disclosure

    false_positives = [p for p in _LOW_MOOD_NEGATIVES if is_low_mood_disclosure(p)]
    fp_rate = len(false_positives) / len(_LOW_MOOD_NEGATIVES)
    assert fp_rate == 0.0, (
        f"§3a low-mood false-positive rate on the negative set is {fp_rate:.2%} "
        f"(non-zero): {false_positives!r}"
    )


# ---------------------------------------------------------------------------
# AC3 — flag OFF is byte-identical to today; flag ON defers the offer.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flag_off_is_unchanged(monkeypatch):
    monkeypatch.setattr("sage_poc.config.LOW_MOOD_SCREEN_ENABLED", False)
    out = await skill_select_node(_ss_state(
        message_en="I've lost interest in everything and I can't get myself to do anything anymore",
        offerable=["behavioral_activation"],
    ))
    assert out["offered_skill_ids"] == ["behavioral_activation"]


@pytest.mark.asyncio
async def test_intercept_defers_offer(monkeypatch):
    monkeypatch.setattr("sage_poc.config.LOW_MOOD_SCREEN_ENABLED", True)
    out = await skill_select_node(_ss_state(
        message_en="I've lost interest in everything and I can't get myself to do anything anymore",
        offerable=["behavioral_activation"],
    ))
    assert out["offered_skill_ids"] is None
    assert out["screen_stage"] == "validated"


# ---------------------------------------------------------------------------
# AC2 — lang == "en" gate on the interception itself, as a tested invariant.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_arabic_falls_through_no_screen(monkeypatch):
    # Invariant: an AR §3a disclosure falls through to today's behaviour, and the screen is
    # never entered. Today's AR behaviour in skill_select is DIRECT-ENTRY, not the offer path:
    # the Arabic-exclusion gate (skill_select.py, arabic_offer_excluded, signed 2026-06-13)
    # returns active_skill_id directly with offered_skill_ids=None for any AR keyword match,
    # BEFORE the EN-gated §3a interception can run. So we prove "falls through to today's
    # behaviour" by asserting the interception is a NO-OP for AR: the flag-ON and flag-OFF
    # outputs are EQUAL (rather than hardcoding what the AR path emits, which would couple this
    # test to the exclusion gate's internals). The two screen invariants below confirm the
    # screen is never entered and the SI probe is never posed in an AR session.
    def _ar_state():
        return _ss_state(
            message_en="I've lost interest in everything and I can't get myself to do anything anymore",
            detected_language="ar",
            offerable=["behavioral_activation"],
        )

    monkeypatch.setattr("sage_poc.config.LOW_MOOD_SCREEN_ENABLED", True)
    out_on = await skill_select_node(_ar_state())
    monkeypatch.setattr("sage_poc.config.LOW_MOOD_SCREEN_ENABLED", False)
    out_off = await skill_select_node(_ar_state())

    assert out_on == out_off, (
        "§3a interception must be a NO-OP for AR: flag-ON and flag-OFF outputs must be "
        "identical (AR falls through to today's arabic_offer_excluded direct-entry path)."
    )
    assert out_on.get("screen_stage") is None
    assert out_on.get("safety_probe_asked") is not True
