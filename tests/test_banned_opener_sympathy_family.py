"""SECONDARY regression test for the stock-opener RCA (2026-06-14).

The deterministic backstop (_BANNED_OPENER_PATTERNS in output_gate) previously caught
reflective fillers and praise openers but NOT the "I'm sorry to hear ..." sympathy family,
the most common distress-response default. These patterns are anchored at ^, so a mid-reply
apology ("I'm sorry, could you say more") must survive.

See docs/superpowers/audits/2026-06-14-stock-opener-rca.md.
"""

import pytest

from sage_poc.nodes.output_gate import _BANNED_OPENER_RE


@pytest.mark.parametrize("text", [
    "I'm sorry to hear you're not feeling too good today.",
    "I'm sorry you're feeling this way.",
    "I'm sorry that things have been so hard lately.",
    "I'm so sorry you're going through this.",
    "Sorry to hear that.",
])
def test_sympathy_openers_are_caught(text):
    assert _BANNED_OPENER_RE.match(text.lstrip()) is not None


@pytest.mark.parametrize("text", [
    "I'm here for you. What's on your mind right now?",
    "I'm sorry, could you say a bit more about that?",  # mid-flow apology, not a sympathy opener
    "Carrying all of that and still showing up. What do you need most right now?",
])
def test_legitimate_openers_are_not_over_matched(text):
    assert _BANNED_OPENER_RE.match(text.lstrip()) is None
