"""E7 — §6a coercive-control / relationship-safety pre-emption (BOT BEHAVIOUR §6a).

Step 1: flag-gated detection expansion. The 19 §6a-guard phrases fire domestic_situation ONLY
when SAGE_IPV_PREEMPTION is ON; OFF is byte-identical (only the approved CF-005 lexicon fires).
Expansion phrases are VERBATIM from the fixture (source of truth — no re-derivation); the sync
test guards against drift. Recall/precision are measured against the same ipv_e7_recall fixture
the harness uses, so the gate and these tests read the same ground truth.
"""
import json
from pathlib import Path

import sage_poc.config as config
from sage_poc.nodes.ipv_preempt import EXPANSION_PHRASES, apply_ipv_preempt

_FIXTURE = Path("tests/fixtures/bot_behaviour/ipv_e7_recall.json")


def _fixture_6a_phrases() -> set[str]:
    data = json.loads(_FIXTURE.read_text())
    return {p["phrase"] for p in data["positive"]["phrases"] if p["src"] == "6a"}


def _people_pleasing_negatives() -> list[str]:
    data = json.loads(_FIXTURE.read_text())
    return data["negative"]["ordinary_people_pleasing"]["phrases"]


def test_expansion_phrases_match_fixture_verbatim():
    # The fixture is the single source of truth for the expansion set. Production data must equal
    # it exactly, so the 19 phrases can never silently drift or be re-derived by hand.
    assert set(EXPANSION_PHRASES) == _fixture_6a_phrases()


def test_off_is_byte_identical(monkeypatch):
    # Flag OFF (default) -> emits nothing; safety_check return + audit stay v7-identical.
    monkeypatch.setattr(config, "IPV_PREEMPTION_ENABLED", False)
    out = apply_ipv_preempt(
        {"message_en": "They get really angry if I say no", "clinical_flags": []}
    )
    assert out == {}


def test_all_19_expansion_phrases_fire_domestic_situation_when_on(monkeypatch):
    monkeypatch.setattr(config, "IPV_PREEMPTION_ENABLED", True)
    missed = [
        p for p in _fixture_6a_phrases()
        if "domestic_situation"
        not in apply_ipv_preempt({"message_en": p, "clinical_flags": []}).get("clinical_flags", [])
    ]
    assert missed == [], f"expansion phrases not detected: {missed}"


def test_people_pleasing_negatives_do_not_fire(monkeypatch):
    # Precision / the punish-disclosure guard's mirror: ordinary people-pleasing must route to
    # assertiveness coaching, NOT IPV pre-emption. Over-firing E7 is clinically harmful too.
    monkeypatch.setattr(config, "IPV_PREEMPTION_ENABLED", True)
    fired = [
        n for n in _people_pleasing_negatives()
        if "domestic_situation"
        in apply_ipv_preempt({"message_en": n, "clinical_flags": []}).get("clinical_flags", [])
    ]
    assert fired == [], f"negatives wrongly fired IPV: {fired}"
