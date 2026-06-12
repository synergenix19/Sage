"""Content guards for the 2026-06-12 engagement-layer changes (R1 + R3).

Pins template content, blurb coverage, and composer offer selection so future
edits that silently regress engagement behavior fail CI instead of shipping.
"""
import json
from pathlib import Path

from sage_poc.prompts.loader import get_intent_template, reload_all

_PROMPTS_DIR = Path(__import__("sage_poc.prompts", fromlist=["__file__"]).__file__).parent


class TestR3GeneralChatEngageThenBridge:
    def test_deflection_clause_removed(self):
        reload_all()
        tmpl = get_intent_template("general_chat")
        assert "rather than engaging with the topic itself" not in tmpl.content, (
            "R3 regression: the scope-wall deflection clause is back in L2_general_chat"
        )

    def test_engage_then_bridge_present_and_version_bumped(self):
        reload_all()
        tmpl = get_intent_template("general_chat")
        assert "engage with the topic itself briefly" in tmpl.content
        assert "Never deflect" in tmpl.content
        assert tmpl.version == "1.3.0"

    def test_no_em_dash_in_content(self):
        reload_all()
        tmpl = get_intent_template("general_chat")
        assert "—" not in tmpl.content, "em dashes mirror into LLM output; use commas"
