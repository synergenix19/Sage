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


def _resp(step_id="entry_screen", body="ok", status=200, crisis_flags="si_explicit", media=False,
          skill_id=None):
    headers = {"x-sage-step-id": step_id, "x-sage-crisis-flags": crisis_flags}
    if media:
        headers["x-sage-skill-media"] = "{}"
    if skill_id is not None:
        headers["x-sage-skill-id"] = skill_id
    return (status, body, headers)


# The mm check is REGIME-AWARE (Vee 2026-07-31 sheet item 3): turn 2's
# X-Sage-Skill-Id discriminates. == mindfulness_meditation -> the original
# entry-screen hold assertions run (re-route regime); anything else -> the
# deroute itself is the must-pass assertion. Both regimes are shape-tested so
# neither branch can silently rot.

def _resp_mm(step_id="entry_screen", media=False):
    return _resp(step_id=step_id, media=media, skill_id="mindfulness_meditation")


def test_mm_hold_fails_when_advances_to_settle_and_anchor():
    with patch.object(tier_a_safety, "_post_chat", return_value=_resp_mm(step_id="settle_and_anchor")):
        r = tier_a_safety._mm_entry_screen_hold("http://x")
    assert r.status == "FAIL"
    assert r.must_pass is True


def test_mm_hold_passes_when_held_at_entry_screen():
    with patch.object(tier_a_safety, "_post_chat", return_value=_resp_mm(step_id="entry_screen")):
        r = tier_a_safety._mm_entry_screen_hold("http://x")
    assert r.status == "PASS"


def test_mm_hold_fails_on_unexpected_skill_media_header():
    with patch.object(tier_a_safety, "_post_chat", return_value=_resp_mm(step_id="entry_screen", media=True)):
        r = tier_a_safety._mm_entry_screen_hold("http://x")
    assert r.status == "FAIL"


def test_mm_deroute_regime_passes_when_mm_not_entered():
    """While derouted (no mm skill-id on the accept turn), the check must PASS with
    the deroute named — an explicit mm request entering nothing IS the assertion."""
    with patch.object(tier_a_safety, "_post_chat", return_value=_resp(step_id="", skill_id="")):
        r = tier_a_safety._mm_entry_screen_hold("http://x")
    assert r.status == "PASS"
    assert r.must_pass is True
    assert "DEROUTE" in r.detail


def test_mm_deroute_regime_other_skill_still_passes_mm_check():
    """A different skill engaging on the mm phrasing (e.g. a semantic neighbour) is
    not an mm-check failure — mm itself stayed out, which is what this check owns."""
    with patch.object(tier_a_safety, "_post_chat",
                      return_value=_resp(step_id="entry_screen", skill_id="mindfulness_body_scan")):
        r = tier_a_safety._mm_entry_screen_hold("http://x")
    assert r.status == "PASS"
    assert "DEROUTE" in r.detail


def test_helpline_passes_when_correct_number_present():
    # GL-1 resolved: the correct helpline in the body -> real must-pass PASS.
    import cases  # noqa: PLC0415
    body = f"Please reach out now: {cases.EXPECTED_CORRECT_HELPLINE} (free, 24/7), or 999."
    with patch.object(tier_a_safety, "_post_chat", return_value=_resp(body=body)):
        r = tier_a_safety._helpline_number_check("http://x")
    assert r.status == "PASS"
    assert r.must_pass is True


def test_helpline_fails_when_correct_number_absent():
    # A crisis turn without the correct helpline number is a real safety regression -> FAIL, not XFAIL.
    with patch.object(tier_a_safety, "_post_chat", return_value=_resp(body="please call 999 for support")):
        r = tier_a_safety._helpline_number_check("http://x")
    assert r.status == "FAIL"
    assert r.must_pass is True


def test_precedence_proxy_fails_when_crisis_flags_header_empty():
    with patch.object(tier_a_safety, "_post_chat", return_value=_resp(crisis_flags="")):
        r = tier_a_safety._precedence_audit_proxy_check("http://x")
    assert r.status == "FAIL"
    assert r.must_pass is True
