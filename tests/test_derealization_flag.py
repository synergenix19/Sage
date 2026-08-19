"""§1c Part A — CF-010 derealization flag + anxiety-track referral terminal.

Both-direction fixtures (Vee 1a-1d, 2026-07-21): the flag FIRES on present-tense active
derealization (-> anxiety-track referral) and must NOT fire on the string-separable controls
(past-tense recount -> §1c grounding; grief-shock -> presence; pure panic -> §1c grounding). Routing
is inert until DEREALIZATION_DETECTION_ENABLED is flipped; precedence keeps crisis/medical/hr senior.
"""
from __future__ import annotations
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.safety_gate

from sage_poc.rules.engine import _eval_safety
from sage_poc.rules.schemas import SafetyRule

_RULES_PATH = (Path(__file__).parent.parent / "src" / "sage_poc" / "rules" / "data" / "safety"
               / "clinical_flag_patterns.json")


def _cf010() -> dict:
    raw = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    return next(r for r in raw["rules"] if r["rule_id"] == "CF-010")


_RULE = SafetyRule.model_validate(_cf010())


def _flags(text_en: str = "", text_ar: str = "") -> list[str]:
    lang = "ar" if text_ar else "en"
    result = _eval_safety([_RULE], {"text_en": text_en, "text_ar": text_ar, "language": lang})
    return [a["flag_id"] for a in result.actions if a.get("type") == "clinical_flag"]


# ── the rule ships active + signed (Vee ratified the 1d strings) ─────────────────────────────
def test_cf010_active_and_signed_on_disk():
    r = _cf010()
    assert r["active"] is True
    assert r["approved_by"] == "clinical_lead"
    assert r["action"]["flag_id"] == "derealization"


# ── FIRES: present-tense active derealization (Vee 1d strings + the #2 corpus row) ───────────
@pytest.mark.parametrize("text", [
    "everything feels unreal",
    "everything feels unreal and i can't take this",   # §1c corpus row #2 (was over-escalating to crisis)
    "i feel disconnected from my body",
])
def test_derealization_fires_on_active_derealization(text):
    assert "derealization" in _flags(text_en=text)


# ── DOES NOT FIRE: the string-separable controls (the whole point of 1d) ─────────────────────
@pytest.mark.parametrize("text", [
    "everything felt unreal during the panic attack",  # past/situational recount -> §1c grounding, NOT referral
    "someone close to me just died and it doesn't feel real",  # grief-shock -> presence (S2a), NOT derealization
    "i can't breathe",                                 # pure panic, no derealization -> §1c grounding
    "i feel completely out of control",                # §1c-B under-fire, NOT derealization (out of Part A scope)
])
def test_derealization_does_not_fire_on_controls(text):
    assert "derealization" not in _flags(text_en=text)


# ── the psychosis register is CF-008/CF-009's, not CF-010's (separation preserved) ──────────
@pytest.mark.parametrize("text", ["nothing feels real", "i feel detached from reality"])
def test_cf010_does_not_claim_the_psychosis_dissociation_strings(text):
    # These are CF-008/CF-009 -> HR. CF-010 must not also match them (precedence would pick hr anyway,
    # but keeping the string sets disjoint is the design).
    assert "derealization" not in _flags(text_en=text)


# ── AR parity: the interim-draft Khaleeji string fires on the raw AR path ────────────────────
def test_derealization_fires_on_arabic_draft_string():
    assert "derealization" in _flags(text_ar="كل شي يبين لي مو حقيقي")


# ── routing: inert when OFF, routes at safety altitude when ON, one-shot guard ───────────────
def _state(**kw):
    base = {"is_safe": True, "clinical_flags": ["derealization"]}
    base.update(kw)
    return base


def test_routing_inert_when_flag_off(monkeypatch):
    from sage_poc import config, graph
    monkeypatch.setattr(config, "DEREALIZATION_DETECTION_ENABLED", False)
    assert graph._route_after_safety(_state()) == "safe"  # flag present but routes nowhere


def test_routes_to_derealization_when_flag_on(monkeypatch):
    from sage_poc import config, graph
    monkeypatch.setattr(config, "DEREALIZATION_DETECTION_ENABLED", True)
    assert graph._route_after_safety(_state()) == "derealization"


def test_one_shot_guard_stops_reentry(monkeypatch):
    from sage_poc import config, graph
    monkeypatch.setattr(config, "DEREALIZATION_DETECTION_ENABLED", True)
    assert graph._route_after_safety(_state(derealization_referral_delivered=True)) == "safe"


def test_crisis_and_medical_stay_senior_to_derealization(monkeypatch):
    from sage_poc import config, graph
    monkeypatch.setattr(config, "DEREALIZATION_DETECTION_ENABLED", True)
    # crisis (is_safe False) wins even with the derealization flag also set
    assert graph._route_after_safety(_state(is_safe=False)) == "crisis"


# ── precedence: hr > derealization (a psychosis-context overlap resolves to hr) ──────────────
def test_precedence_hr_beats_derealization(monkeypatch):
    from sage_poc import config
    from sage_poc.nodes.safety_precedence import resolve_safety_precedence, SAFETY_ROUTE_ORDER
    monkeypatch.setattr(config, "DEREALIZATION_DETECTION_ENABLED", True)
    monkeypatch.setattr(config, "HIGH_RISK_DETECTION_ENABLED", True)
    assert SAFETY_ROUTE_ORDER.index("hr") < SAFETY_ROUTE_ORDER.index("derealization")
    winner, fired = resolve_safety_precedence(
        {"is_safe": True, "clinical_flags": ["derealization", "psychotic_disclosure"]})
    assert winner == "hr"
    assert "derealization" in fired  # never silently dropped (§4.5)


# ── the terminal copy: account-framed, refers, single-sourced helpline, both languages ───────
@pytest.mark.parametrize("lang", ["en", "ar"])
def test_referral_copy_renders_and_is_account_framed(lang):
    from sage_poc.safety.derealization_copy import derealization_referral_text
    t = derealization_referral_text(lang)
    assert "{{" not in t                       # placeholders resolved
    assert "4673" in t and "725462" in t       # helpline single-sourced (HOPE by day + SAKINA 24/7)
    frame = "what you're describing" if lang == "en" else "اللي تصفه"
    assert frame in t.lower()
