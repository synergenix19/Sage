"""Tier A shape tests — no network. Stub _post_chat and assert the safety-check
status logic: MM-hold FAILs on settle_and_anchor / PASSes on entry_screen, and
the helpline check is XFAIL (not FAIL, not PASS) while prod shows the wrong number.
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_PROD_SMOKE_DIR = Path(__file__).resolve().parent.parent
if str(_PROD_SMOKE_DIR) not in sys.path:
    sys.path.insert(0, str(_PROD_SMOKE_DIR))

import tier_a_safety  # noqa: E402


def _resp(step_id="entry_screen", body="ok", status=200, crisis_flags="si_explicit", media=False):
    headers = {"x-sage-step-id": step_id, "x-sage-crisis-flags": crisis_flags}
    if media:
        headers["x-sage-skill-media"] = "{}"
    return (status, body, headers)


def test_mm_hold_fails_when_advances_to_settle_and_anchor():
    with patch.object(tier_a_safety, "_post_chat", return_value=_resp(step_id="settle_and_anchor")):
        r = tier_a_safety._mm_entry_screen_hold("http://x")
    assert r.status == "FAIL"
    assert r.must_pass is True


def test_mm_hold_passes_when_held_at_entry_screen():
    with patch.object(tier_a_safety, "_post_chat", return_value=_resp(step_id="entry_screen")):
        r = tier_a_safety._mm_entry_screen_hold("http://x")
    assert r.status == "PASS"


def test_mm_hold_fails_on_unexpected_skill_media_header():
    with patch.object(tier_a_safety, "_post_chat", return_value=_resp(step_id="entry_screen", media=True)):
        r = tier_a_safety._mm_entry_screen_hold("http://x")
    assert r.status == "FAIL"


def test_helpline_is_xfail_while_correct_number_absent():
    # EXPECTED_CORRECT_HELPLINE is a placeholder not present in the body -> XFAIL,
    # never FAIL (GL-1 deferred) and never PASS (fix not live).
    with patch.object(tier_a_safety, "_post_chat", return_value=_resp(body="please call 999 for support")):
        r = tier_a_safety._helpline_number_check("http://x")
    assert r.status == "XFAIL"


def test_precedence_proxy_fails_when_crisis_flags_header_empty():
    with patch.object(tier_a_safety, "_post_chat", return_value=_resp(crisis_flags="")):
        r = tier_a_safety._precedence_audit_proxy_check("http://x")
    assert r.status == "FAIL"
    assert r.must_pass is True
