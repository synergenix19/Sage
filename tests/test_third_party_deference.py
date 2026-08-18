# tests/test_third_party_deference.py
#
# R4 (Vee ruling 2026-08-18, packet 2): third-party crisis turns get a DISTINCT
# helper-support path instead of the first-person crisis script. Flag-gated
# (SAGE_THIRD_PARTY_DEFERENCE, default OFF, register row at birth); content is
# a crisis_content rule (Rules Service JSON, DRAFT until Vee signs).
#
# The two HARD boundaries from the ruling, as tests:
#   1. the first-person crisis script never serves the clean third-party case
#      when the flag is ON (and always serves when OFF - byte-identical);
#   2. deference applies ONLY on Layer-1-clean turns - co-occurring
#      first-person SI fires deterministically (F1), so the compound case gets
#      the first-person script in BOTH flag states, always.
#
# Assertions are behavior-to-behavior (node response vs the rules engine's own
# resolved text) - no clinical prose is copied into this file.

import pytest

from sage_poc.graph import _crisis_response_node
from sage_poc.rules import engine as rules_engine
from sage_poc.config import CRISIS_CONFIG


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


@pytest.mark.asyncio
async def test_flag_off_clean_third_party_serves_first_person(monkeypatch):
    monkeypatch.setattr("sage_poc.config.THIRD_PARTY_DEFERENCE_ENABLED", False)
    out = await _crisis_response_node(_state())
    assert out["response"] == _content("en", "acute"), (
        "flag OFF must be byte-identical: the acute first-person script serves"
    )


@pytest.mark.asyncio
async def test_flag_on_clean_third_party_serves_helper_content(monkeypatch):
    monkeypatch.setattr("sage_poc.config.THIRD_PARTY_DEFERENCE_ENABLED", True)
    out = await _crisis_response_node(_state())
    helper = _content("en", "third_party")
    assert out["response"] == helper
    assert out["response"] != _content("en", "acute"), (
        "hard boundary 1: the first-person crisis script never serves the "
        "clean third-party case under the flag"
    )
    assert CRISIS_CONFIG["number"] in out["response"], (
        "the helpline (single-source config value) must be present, framed as "
        "a resource for the friend"
    )


@pytest.mark.asyncio
async def test_flag_on_compound_never_defers(monkeypatch):
    # Hard boundary 2 (both-directions per regression-by-improvement): a
    # co-occurring first-person flag means the deterministic layer fired (F1);
    # the helper path must NEVER serve this case.
    monkeypatch.setattr("sage_poc.config.THIRD_PARTY_DEFERENCE_ENABLED", True)
    out = await _crisis_response_node(_state(crisis_flags=["si_passive"], is_safe=False))
    assert out["response"] == _content("en", "acute")


@pytest.mark.asyncio
async def test_flag_on_ar_without_content_falls_back_toward_crisis(monkeypatch):
    # No signed AR third-party content row yet: fail-toward-crisis means the
    # AR acute script serves, never a missing-content hole.
    monkeypatch.setattr("sage_poc.config.THIRD_PARTY_DEFERENCE_ENABLED", True)
    out = await _crisis_response_node(_state(detected_language="ar"))
    assert out["response"] == _content("ar", "acute")


@pytest.mark.asyncio
async def test_deference_keeps_crisis_mechanics_unchanged(monkeypatch):
    # Stage 1 is DELIVERY-CONTENT-ONLY: monitoring entry and the crisis gate
    # path are identical to the first-person case (whether a helper turn should
    # enter monitoring is a flagged clinical question in the decision request).
    monkeypatch.setattr("sage_poc.config.THIRD_PARTY_DEFERENCE_ENABLED", True)
    out = await _crisis_response_node(_state())
    assert out["crisis_state"] == "monitoring"
    assert out["gate_path"] == "crisis"


def test_third_party_content_rule_exists_en():
    # Engine-level: the DRAFT rule resolves for en; its text carries the
    # resolved single-source helpline (load-time {{crisis_*}} templating).
    text = _content("en", "third_party")
    assert CRISIS_CONFIG["number"] in text
    assert "{{" not in text, "unresolved {{crisis_*}} placeholder"
