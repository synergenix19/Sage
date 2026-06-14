"""PRIMARY regression test for the stock-opener RCA (2026-06-14).

Root cause (see docs/superpowers/audits/2026-06-14-stock-opener-rca.md):
  prompt-layer conflict. L0 OPENERS says warmth comes from substance, "not from ... a
  paraphrase of what they just told you". L2 general_chat v1.4.0 said "reflect the feeling
  back before anything else", which is a paraphrase-first instruction. The responder obeys
  the turn-level L2 directive and opens with a stock sympathy/paraphrase line. Tuning L0
  alone could never fix this because L0 was the layer being overridden.

This locks the L2 content contract. The deterministic backstop (the "I'm sorry to hear"
blocklist family) is tested separately in test_banned_opener_sympathy_family.py.
"""

import json
from pathlib import Path

import sage_poc

_GENERAL_CHAT_JSON = (
    Path(sage_poc.__file__).parent
    / "prompts" / "templates" / "L2_intents" / "general_chat.json"
)


def _general_chat_content() -> str:
    return json.loads(_GENERAL_CHAT_JSON.read_text())["content"].lower()


def test_general_chat_does_not_command_reflecting_the_feeling_back():
    """L2 must not re-introduce the paraphrase-first directive that contradicts L0."""
    assert "reflect the feeling back" not in _general_chat_content()


def test_general_chat_directs_a_substance_first_opener():
    """L2 must positively steer the opener toward naming the specific thing said."""
    content = _general_chat_content()
    assert "name the specific thing" in content or "naming the specific thing" in content


def test_general_chat_preserves_validate_before_inform():
    """Guard: the opener rewrite must NOT drop the clinical validate-first invariant."""
    assert "validate before you inform" in _general_chat_content()
