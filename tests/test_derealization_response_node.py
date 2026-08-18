"""§1c Part A derealization_response terminal node — audit-record correctness.

Mirrors medical_response / screen_response / high_risk_response: response_en must record THIS
turn's rendered text unconditionally, matching medical_response.py:47 / screen_response.py:43 /
high_risk_response.py:124. On an AR-language turn the terminal previously returned the PRIOR
turn's response_en (state.get("response_en")) instead of this turn's text — the served `response`
field was always correct; only the clinical-record field (audit row + history EN text) was wrong.
"""
import asyncio

from sage_poc.nodes.derealization_response import derealization_response_node
from sage_poc.safety.derealization_copy import derealization_referral_text


def _ar_state_with_stale_response_en():
    return {
        "detected_language": "ar",
        "path": ["safety_check"],
        "turn_started_at": None,
        "session_id": "s1",
        # stale value left over from a PRIOR turn in the conversation history — must NOT leak
        # into this turn's recorded response_en.
        "response_en": "some prior turn's english text",
    }


def test_response_en_records_this_turns_text_on_ar_turn():
    out = asyncio.run(derealization_response_node(_ar_state_with_stale_response_en()))
    expected = derealization_referral_text("ar")
    assert out["response"] == expected                       # served text unchanged
    assert out["response_en"] == expected                     # was: the stale prior-turn value
    assert out["response_en"] != "some prior turn's english text"


def test_response_en_matches_response_on_en_turn():
    out = asyncio.run(derealization_response_node({
        "detected_language": "en",
        "path": ["safety_check"],
        "turn_started_at": None,
        "session_id": "s1",
    }))
    assert out["response_en"] == out["response"]
