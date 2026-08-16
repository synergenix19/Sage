"""OR-3 / OR-4 — conformance guards.

Both requirements are ALREADY conformant in product code (not test-only), per BOT
BEHAVIOUR verification. These are regression locks: they fail if a future edit silently
drops the one-question-at-a-time discipline or raises the offer cap above two.
  OR-3: L0 persona authors "ask at most one question per turn".
  OR-4: default_offer caps offered skills at max_offered == 2 (enforced by truncation
        in skill_select; the doc's Offer-First/Offer-Second structure implies <=2).
"""
import json
from pathlib import Path

import sage_poc

_PKG = Path(sage_poc.__file__).parent


def test_or3_one_question_at_a_time_authored_in_l0_persona():
    text = (_PKG / "prompts" / "templates" / "L0_persona.json").read_text().lower()
    assert "at most one question per turn" in text, (
        "OR-3: the CONVERSATION DISCIPLINE one-question-per-turn clause must remain in L0 persona"
    )


def test_or4_default_offer_caps_at_two():
    rules = json.loads(
        (_PKG / "rules" / "data" / "skill_matching" / "skill_matching_rules.json").read_text()
    )["rules"]
    default_offer = next(r for r in rules if r["rule_id"] == "default_offer")
    assert default_offer["action"]["max_offered"] == 2, (
        "OR-4: default_offer must cap at 2 options (plus keep-talking)"
    )
