"""Guard: live safety-exit terminal copy must carry its urgency markers, BEFORE the
voice-pass renovates these strings. Warmth erodes urgency one synonym at a time (the
HR slot-3 pass caught 'as soon as you can' softening a 999 redirect). This pins the
property on the LIVE crisis and medical copy so a future edit that softens them fails
CI. Guards before renovation: when the voice-pass runs, its guardrail predates it.

Wired into the required 'Safety-surface unit tests' gate.
"""
import json
import pathlib

from sage_poc import config as _c

_NOW_MARKERS = ("now", "right away", "immediately", "don't wait", "dont wait", "straight to")


def test_medical_terminal_leads_with_998_and_carries_urgency():
    t = _c.MEDICAL_REFERRAL_TEXT.lower()
    assert "998" in t, "medical terminal must reference 998 (ambulance) -- see the 998-vs-999 split"
    assert any(m in t for m in _NOW_MARKERS), (
        f"medical terminal lacks a now-class urgency marker (warmth-erodes-urgency guard): {t!r}"
    )


def test_crisis_copy_carries_999_and_urgency():
    src = pathlib.Path("src/sage_poc/rules/data/crisis_content/en_uae.json")
    s = json.dumps(json.loads(src.read_text())).lower()
    assert "999" in s, "crisis copy must contain 999 (emergency escalation)"
    assert any(m in s for m in _NOW_MARKERS + ("emergency",)), (
        "crisis copy lacks now-class urgency framing (warmth-erodes-urgency guard)"
    )
