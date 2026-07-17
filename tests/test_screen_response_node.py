"""D1 screen_response terminal node (#338) — emits the signed question, holds, → END. Red-verified.

Mirrors medical_response: emits fixed signed text as the turn response, writes its OWN session audit
(bypasses output_gate), → END. UNLIKE medical_response it PRESERVES the per-session hold (screen_pending /
screen_held_skill) so the next turn is recognised as the answer.
"""
import asyncio
import pytest
from sage_poc.nodes.screen_response import screen_response_node
from sage_poc.safety import medical_screen as ms


def _held_state():
    return {"screen_question_text": ms.SCREEN_QUESTION_EN, "screen_pending": True,
            "screen_held_skill": "dbt_tipp", "path": ["safety_check", "skill_select"],
            "turn_started_at": None, "session_id": "s1"}


def test_emits_signed_question_verbatim():
    out = asyncio.run(screen_response_node(_held_state()))
    assert out["response"] == ms.SCREEN_QUESTION_EN          # served text IS the signed bytes
    assert out["response_en"] == ms.SCREEN_QUESTION_EN
    assert out["gate_path"] == "screen"


def test_preserves_hold_for_next_turn():
    out = asyncio.run(screen_response_node(_held_state()))
    # the hold must survive to the answer turn — NOT cleared here (unlike medical_response's active-skill clear)
    assert out.get("screen_pending") is True
    assert out.get("screen_held_skill") == "dbt_tipp"
    assert out.get("active_skill_id") is None               # no skill runs this turn; the question is the turn
    assert "screen_response" in out["path"]


def test_records_screen_asked_audit(monkeypatch):
    # the emit turn records screen_asked (audit surface for the PDPL contraindication-decision trail)
    out = asyncio.run(screen_response_node(_held_state()))
    assert out.get("screen_asked") is True
