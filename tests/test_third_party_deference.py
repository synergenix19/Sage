# tests/test_third_party_deference.py
#
# R4 (Vee ruling 2026-08-18, packet 2; owner Scoping 1): third-party crisis
# turns get a DISTINCT helper-support path at RESPONSE-CONTENT SELECTION, never
# at routing. Flag-gated (SAGE_THIRD_PARTY_DEFERENCE, default OFF, register row
# at birth). Content rule CC-EN-TP-001 ships INACTIVE: the crisis locale parity
# boot guard forbids any crisis level active in one locale only, and the ar_uae
# twin must be NATIVELY authored (Khaleeji lane) — so activation is part of the
# signing, and the mechanism is tested here via a synthetic ACTIVE injection of
# the draft row's own resolved content (behavior-to-behavior; no clinical prose
# copied into this file).
#
# The two HARD boundaries from the ruling, as content assertions:
#   1. the first-person script never serves the clean third-party case when the
#      flag is ON and content exists (and flag OFF ignores available content);
#   2. deference applies ONLY on Layer-1-clean turns — a co-occurring
#      first-person flag serves the first-person script even with the flag ON
#      and content available, no exceptions.

import json
from pathlib import Path

import pytest

from sage_poc.graph import _crisis_response_node
from sage_poc.rules import engine as rules_engine
from sage_poc.rules.loader import get_rules as _real_get_rules
from sage_poc.rules.schemas import CrisisContentRule
from sage_poc.crisis_copy import resolve_crisis_placeholders
from sage_poc.config import CRISIS_CONFIG

_REPO = Path(__file__).resolve().parents[1]
_EN_FILE = _REPO / "src/sage_poc/rules/data/crisis_content/en_uae.json"


def _draft_row() -> dict:
    raw = json.loads(_EN_FILE.read_text())
    return next(r for r in raw["rules"] if r["rule_id"] == "CC-EN-TP-001")


def _inject_active_third_party(monkeypatch) -> str:
    """Append an ACTIVE, placeholder-resolved copy of the draft row to the engine's
    crisis_content rules; return its resolved response_text."""
    row = json.loads(resolve_crisis_placeholders(json.dumps(_draft_row())))
    row["active"] = True
    synthetic = CrisisContentRule(**{k: v for k, v in row.items()
                                     if k in CrisisContentRule.model_fields})

    def wrapped(category):
        rules = list(_real_get_rules(category))
        if category == "crisis_content":
            rules.append(synthetic)
        return rules

    monkeypatch.setattr("sage_poc.rules.engine.get_rules", wrapped)
    return synthetic.action["response_text"]


def _content(lang: str, level: str) -> str:
    r = rules_engine.evaluate("crisis_content", {"language": lang, "crisis_level": level})
    assert r.fired, f"no crisis_content rule for {lang}/{level}"
    return r.fired[0].action["response_text"]


def _state(**over):
    base = {
        "raw_message": "my sister is suicidal and I don't know how to support her",
        "detected_language": "en",
        "message_en": "my sister is suicidal and I don't know how to support her",
        "is_safe": True,
        "crisis_flags": [],
        "third_party_crisis": True,
        "clinical_flags": [],
        "crisis_state": "none",
        "path": ["safety_check", "intent_route"],
        "turn_count": 1,
        "conversation_history": [],
        "session_id": "t-tpd",
        "user_id": "",  # empty -> clinician_review_queue write is skipped (logged)
    }
    base.update(over)
    return base


# ── Dark-state pin: shipped data serves NOTHING new, even flag-ON ────────────

@pytest.mark.asyncio
async def test_shipped_dark_state_flag_on_serves_acute(monkeypatch):
    # CC-EN-TP-001 ships inactive (locale-parity boot guard): with REAL rules,
    # flag-ON falls back toward crisis (acute script). This is the serving
    # truth until Vee signs EN + a native AR twin activates the level.
    monkeypatch.setattr("sage_poc.config.THIRD_PARTY_DEFERENCE_ENABLED", True)
    out = await _crisis_response_node(_state())
    assert out["response"] == _content("en", "acute")


# ── Mechanism under synthetic activation of the draft's own content ──────────

@pytest.mark.asyncio
async def test_flag_off_ignores_available_third_party_content(monkeypatch):
    helper = _inject_active_third_party(monkeypatch)
    monkeypatch.setattr("sage_poc.config.THIRD_PARTY_DEFERENCE_ENABLED", False)
    out = await _crisis_response_node(_state())
    assert out["response"] == _content("en", "acute")
    assert out["response"] != helper, "flag OFF must be byte-identical"


@pytest.mark.asyncio
async def test_flag_on_clean_third_party_serves_helper_content(monkeypatch):
    helper = _inject_active_third_party(monkeypatch)
    monkeypatch.setattr("sage_poc.config.THIRD_PARTY_DEFERENCE_ENABLED", True)
    out = await _crisis_response_node(_state())
    assert out["response"] == helper
    assert out["response"] != _content("en", "acute"), (
        "hard boundary 1: the first-person crisis script never serves the "
        "clean third-party case under the flag"
    )
    assert CRISIS_CONFIG["number"] in out["response"], (
        "helpline (single-source config value) present, framed for the friend"
    )


@pytest.mark.asyncio
async def test_flag_on_compound_never_defers(monkeypatch):
    # Hard boundary 2, both-directions: even with the flag ON and helper
    # content AVAILABLE, a co-occurring first-person flag (F1's deterministic
    # layer fired) serves the first-person script. No exceptions.
    helper = _inject_active_third_party(monkeypatch)
    monkeypatch.setattr("sage_poc.config.THIRD_PARTY_DEFERENCE_ENABLED", True)
    out = await _crisis_response_node(_state(crisis_flags=["si_passive"], is_safe=False))
    assert out["response"] == _content("en", "acute")
    assert out["response"] != helper


@pytest.mark.asyncio
async def test_flag_on_ar_without_native_content_falls_back_toward_crisis(monkeypatch):
    # EN-only injection: an AR session finds no ar_uae third_party rule and
    # serves the AR acute script — fail-toward-crisis, never a content hole
    # (and never machine translation: the boot guard forbids activating the
    # level until a NATIVE ar_uae twin exists).
    _inject_active_third_party(monkeypatch)
    monkeypatch.setattr("sage_poc.config.THIRD_PARTY_DEFERENCE_ENABLED", True)
    out = await _crisis_response_node(_state(detected_language="ar"))
    assert out["response"] == _content("ar", "acute")


@pytest.mark.asyncio
async def test_deference_keeps_crisis_mechanics_unchanged(monkeypatch):
    # Delivery-content-only: monitoring entry and the crisis gate path are
    # identical to the first-person case (helper-turn monitoring semantics =
    # flagged clinical question in the decision request).
    _inject_active_third_party(monkeypatch)
    monkeypatch.setattr("sage_poc.config.THIRD_PARTY_DEFERENCE_ENABLED", True)
    out = await _crisis_response_node(_state())
    assert out["crisis_state"] == "monitoring"
    assert out["gate_path"] == "crisis"


# ── Draft-row invariants (the artifact Vee signs) ────────────────────────────

def test_draft_row_is_inactive_and_templated():
    row = _draft_row()
    assert row["active"] is False, (
        "CC-EN-TP-001 must ship inactive: the crisis locale parity boot guard "
        "forbids a level active in en_uae without a natively-authored ar_uae "
        "twin; activation is part of the signing"
    )
    text = row["action"]["response_text"]
    assert "{{crisis_" in text, "single-source templating required, never a literal"
    resolved = resolve_crisis_placeholders(text)
    assert "{{" not in resolved and CRISIS_CONFIG["number"] in resolved


def test_inactive_draft_is_not_loaded_by_the_engine():
    r = rules_engine.evaluate("crisis_content", {"language": "en", "crisis_level": "third_party"})
    assert not r.fired, "inactive draft must not load (locale-parity guard depends on it)"
