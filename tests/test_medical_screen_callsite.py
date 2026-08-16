"""D1 call-site (#338) — the two precision points as red-verify, not assumption."""
import pytest
from sage_poc import config
from sage_poc.safety import medical_screen as ms


def _base_result():  # a typical skill_select return for a resolved acute skill
    return {"active_skill_id": "dbt_tipp", "active_step_id": "entry_screen",
            "skill_match_method": "keyword", "path": ["skill_select"]}


# ── (1) FLAG BOUNDARY: off == byte-identical, no decide_screen, no channel touch ──
def test_flag_off_is_byte_identical(monkeypatch):
    monkeypatch.setattr(config, "D1_SCREEN_ENABLED", False)
    called = {"n": 0}
    monkeypatch.setattr(ms, "decide_screen", lambda *a, **k: called.__setitem__("n", called["n"] + 1) or {})
    r_in = _base_result()
    r_out = ms.apply_screen_at_route({"detected_language": "en"}, dict(r_in))
    assert r_out == r_in                                  # unchanged
    assert called["n"] == 0                               # decide_screen NEVER invoked
    assert not any(k.startswith("screen_") for k in r_out)  # no channel touched

def test_flag_on_engages_on_contraindicated(monkeypatch):
    monkeypatch.setattr(config, "D1_SCREEN_ENABLED", True)
    r_out = ms.apply_screen_at_route({"detected_language": "en"}, _base_result())
    # unsigned question -> fail-safe grounding; either way TIPP is no longer the entered skill + screen state set
    assert r_out["active_skill_id"] != "dbt_tipp"
    assert "screen_asked" in r_out


# ── (2) VETO ORDER: a veto result is never a screen situation (even flag-on) ──
def test_veto_result_never_screens(monkeypatch):
    monkeypatch.setattr(config, "D1_SCREEN_ENABLED", True)
    called = {"n": 0}
    monkeypatch.setattr(ms, "decide_screen", lambda *a, **k: called.__setitem__("n", called["n"] + 1) or {})
    veto_result = {"active_skill_id": None, "offered_skill_ids": None,
                   "path": ["skill_select", "ocd_compulsion_veto"]}
    r_out = ms.apply_screen_at_route({"detected_language": "ar", "raw_message": "أغسل يدي وأنا متضايق"}, dict(veto_result))
    assert r_out == veto_result and called["n"] == 0      # veto wins; no screen, no state written
