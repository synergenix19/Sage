"""D1 shadow mode (#338) — SILENT shadow: observe the would-be screen decision, write it to the audit,
but NEVER alter the served route. The safety invariant, red-verified BOTH directions:

  SHADOW-MODE ROUTE-IDENTITY: with D1_SCREEN_SHADOW on (and enforce off), the served routing fields
  (active_skill_id / offered_skill_ids / active_step_id / screen_pending / screen_question_text) are
  BYTE-IDENTICAL to the flag-off output. Only screen_shadow_* observation keys are added.

Why silent (not serve-but-don't-enforce): a safety screen cannot be shadowed by letting the harm through.
Serving-without-enforcing would route a heart-condition discloser to TIPP ice-water during the window — the
exact harm D1 exists to prevent. So shadow measures FIRE-VOLUME only; the answer-class distribution
(RULING 3) is a POST-FLIP monitored-enforce gate, not a shadow gate. See the GATE 0 addendum.
"""
import pytest
from sage_poc import config
from sage_poc.safety import medical_screen as ms

_SHADOW_KEYS = ("screen_shadow_action", "screen_shadow_answer_class", "screen_shadow_branch")


def _base_result():
    return {"active_skill_id": "dbt_tipp", "active_step_id": "entry_screen",
            "skill_match_method": "keyword", "path": ["skill_select"]}


def _served(d):  # the fields that determine what the user gets, stripped of shadow observation
    return {k: v for k, v in d.items() if not k.startswith("screen_shadow")}


# ── ROUTE-IDENTITY: shadow observes but never moves the served route (byte-for-byte) ──
def test_shadow_route_identity_on_contraindicated(monkeypatch):
    monkeypatch.setattr(config, "D1_SCREEN_ENABLED", False)
    monkeypatch.setattr(config, "D1_SCREEN_SHADOW", True)
    r_in = _base_result()
    r_out = ms.apply_screen_at_route({"detected_language": "en"}, dict(r_in))
    assert _served(r_out) == r_in                          # served fields byte-identical to flag-off output
    assert r_out["active_skill_id"] == "dbt_tipp"          # TIPP still routed — route NOT altered
    assert "screen_pending" not in _served(r_out)          # never serves, never holds
    assert "screen_question_text" not in _served(r_out)


def test_shadow_records_would_be_action(monkeypatch):
    monkeypatch.setattr(config, "D1_SCREEN_ENABLED", False)
    monkeypatch.setattr(config, "D1_SCREEN_SHADOW", True)
    r_out = ms.apply_screen_at_route({"detected_language": "en"}, _base_result())
    # fresh contraindicated routing, no prior → the screen WOULD have fired (ask_screen)
    assert r_out["screen_shadow_action"] == "ask_screen"


def test_shadow_observation_matches_decide_screen(monkeypatch):
    monkeypatch.setattr(config, "D1_SCREEN_ENABLED", False)
    monkeypatch.setattr(config, "D1_SCREEN_SHADOW", True)
    # session prior = a disclosed contraindication → decide_screen would reroute to grounding
    state = {"detected_language": "en", "session_screen_answer": "contraindication_disclosed"}
    r_out = ms.apply_screen_at_route(state, _base_result())
    assert _served(r_out)["active_skill_id"] == "dbt_tipp"  # STILL not enforced — route identical
    assert r_out["screen_shadow_action"] == "reroute_grounding"  # but the would-be action is recorded


# ── PRECEDENCE: enforce wins over shadow (enforce is not route-identity) ──
def test_enforce_wins_over_shadow(monkeypatch):
    monkeypatch.setattr(config, "D1_SCREEN_ENABLED", True)
    monkeypatch.setattr(config, "D1_SCREEN_SHADOW", True)
    r_out = ms.apply_screen_at_route({"detected_language": "en"}, _base_result())
    assert r_out["active_skill_id"] != "dbt_tipp"          # enforced: route DID move
    assert not any(k in r_out for k in _SHADOW_KEYS)       # enforce path writes no shadow observation


# ── BOTH OFF: identity, and no shadow observation leaks ──
def test_both_off_is_identity_no_shadow_keys(monkeypatch):
    monkeypatch.setattr(config, "D1_SCREEN_ENABLED", False)
    monkeypatch.setattr(config, "D1_SCREEN_SHADOW", False)
    r_in = _base_result()
    r_out = ms.apply_screen_at_route({"detected_language": "en"}, dict(r_in))
    assert r_out == r_in
    assert not any(k in r_out for k in _SHADOW_KEYS)


# ── VETO in shadow: not a screen situation → route-identity AND no observation ──
def test_veto_in_shadow_no_observation(monkeypatch):
    monkeypatch.setattr(config, "D1_SCREEN_ENABLED", False)
    monkeypatch.setattr(config, "D1_SCREEN_SHADOW", True)
    veto = {"active_skill_id": None, "offered_skill_ids": None, "path": ["skill_select", "veto"]}
    r_out = ms.apply_screen_at_route({"detected_language": "ar", "raw_message": "x"}, dict(veto))
    assert r_out == veto                                    # untouched, no shadow keys
    assert not any(k in r_out for k in _SHADOW_KEYS)


# ── non-contraindicated skill in shadow: nothing to observe, identity ──
def test_noncontraindicated_in_shadow_is_identity(monkeypatch):
    monkeypatch.setattr(config, "D1_SCREEN_ENABLED", False)
    monkeypatch.setattr(config, "D1_SCREEN_SHADOW", True)
    r_in = {"active_skill_id": "box_breathing", "path": ["skill_select"]}
    r_out = ms.apply_screen_at_route({"detected_language": "en"}, dict(r_in))
    assert r_out == r_in
    assert not any(k in r_out for k in _SHADOW_KEYS)
