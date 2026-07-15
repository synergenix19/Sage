"""HR-1 Stage 1.5: crisis co-check + full-graph precedence test.

Analogue of the crisis>medical precedence verification in
tests/test_medical_redflag_guard.py (test_crisis_wins_over_medical), extended to the
HR (mania/dissociation/psychosis) referral path added by Tasks 1-3. Ratified routing
order is crisis > medical > hr (BOT BEHAVIOUR / v7.1 precedence table): SI is checked
FIRST in _route_after_safety (graph.py), structurally before the HR redirect (which
only exists in _route_after_intent, a node the crisis short-circuit never reaches).

This file drives the REAL compiled graph end-to-end via app.ainvoke, exactly like
test_medical_redflag_guard.py's test_end_to_end_cardiac_no_longer_reaches_a_skill:
- CF-007 (mania_disclosure)/CF-008 (dissociation_disclosure)/CF-009 (psychosis-variant
  expansion) ship active=false pending clinician ratification (see
  tests/test_rules_safety_hr.py), so they are force-activated here the same way, by
  monkeypatching sage_poc.rules.engine.get_rules to append them to the real,
  disk-loaded safety rule set. This is orthogonal to HIGH_RISK_DETECTION_ENABLED,
  which gates ROUTING once a flag is detected, not whether the rule fires.
- The dissociation-only case reaches skill_select -> skill_executor -> freeflow_respond
  -> output_gate, so the classifier (intent_route) and responder (freeflow_respond)
  LLMs are stubbed with tests/conftest.py's make_mock_llm, matching the pattern in
  tests/test_session_audit_integration.py. No network / OPENROUTER_API_KEY needed.
- The SI+dissociation case never reaches intent_route at all (crisis short-circuits at
  Node 1 -> crisis_response -> END), so no LLM stub is needed there.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import sage_poc.config as config
from sage_poc.rules.schemas import SafetyRule

_RULES_PATH = (
    Path(__file__).parent.parent
    / "src" / "sage_poc" / "rules" / "data" / "safety" / "clinical_flag_patterns.json"
)
_FORCE_ACTIVE_IDS = {"CF-007", "CF-008", "CF-009"}


def _force_activate_hr_rules(monkeypatch) -> None:
    """Make CF-007/008/009 fire for this test only, without touching the on-disk
    active=false gate (see tests/test_rules_safety_hr.py, which does the same thing
    for direct _eval_safety calls). Here the patch point is one layer up:
    sage_poc.rules.engine.get_rules, the name safety_check_node's rules_engine.evaluate
    actually calls, so the force-activation is exercised through the real node, not a
    hand-copied duplicate of its logic.
    """
    from sage_poc.rules import engine as rules_engine
    from sage_poc.rules.loader import get_rules as _real_get_rules

    raw = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    forced = []
    for rule_data in raw["rules"]:
        if rule_data["rule_id"] in _FORCE_ACTIVE_IDS:
            rule_data = dict(rule_data)
            rule_data["active"] = True
            forced.append(SafetyRule.model_validate(rule_data))
    assert {r.rule_id for r in forced} == _FORCE_ACTIVE_IDS, forced

    def _patched_get_rules(category):
        if category == "safety":
            return _real_get_rules("safety") + forced
        return _real_get_rules(category)

    monkeypatch.setattr(rules_engine, "get_rules", _patched_get_rules)


def _stub_intent_and_responder_llms(monkeypatch) -> None:
    """Stub the two LLM entry points the dissociation-only turn reaches
    (intent_route's classifier, freeflow_respond's responder) so the full graph
    completes offline. Mirrors tests/test_session_audit_integration.py."""
    from tests.conftest import make_mock_llm, _INTENT_JSON_GENERAL_CHAT

    intent_llm = make_mock_llm([_INTENT_JSON_GENERAL_CHAT])
    responder_llm = make_mock_llm(["Thank you for sharing that with me."])

    monkeypatch.setattr("sage_poc.nodes.intent_route.get_classifier", lambda: intent_llm)
    monkeypatch.setattr("sage_poc.nodes.intent_route.get_fallback_classifier", lambda: intent_llm)
    monkeypatch.setattr("sage_poc.nodes.freeflow_respond.get_responder", lambda: responder_llm)
    monkeypatch.setattr("sage_poc.nodes.freeflow_respond.get_fallback_responder", lambda: responder_llm)


@pytest.mark.asyncio
async def test_si_plus_dissociation_routes_crisis_not_referral(monkeypatch):
    """A turn carrying BOTH suicidal ideation and dissociation language must route to
    crisis, never to the HR/psychotic referral -- SI wins. This is structural, not a
    tie-break: _route_after_safety returns "crisis" at Node 1 (is_safe False) before
    intent_route (Node 2, where the HR redirect lives) ever runs, so the referral path
    is unreachable this turn regardless of how many HR flags also fired.
    """
    _force_activate_hr_rules(monkeypatch)
    monkeypatch.setattr(config, "HIGH_RISK_DETECTION_ENABLED", True)

    from sage_poc.graph import build_graph
    app = build_graph()
    result = await app.ainvoke(
        {"raw_message": "nothing feels real and I want to end it all", "path": []},
        config={"configurable": {"thread_id": "hr15-si-plus-dissociation"}},
    )

    # Both signals actually fired this turn -- otherwise "SI wins" would be untested.
    assert result.get("is_safe") is False
    assert result.get("clinical_flags") and "dissociation_disclosure" in result["clinical_flags"]

    assert result.get("gate_path") == "crisis"
    assert "crisis_response" in result.get("path", [])
    assert "intent_route" not in result.get("path", [])
    assert result.get("active_skill_id") is None
    assert result.get("skill_match_method") != "psychotic_disclosure_auto_select"


@pytest.mark.asyncio
async def test_dissociation_only_reaches_psychotic_referral(monkeypatch):
    """Same dissociation language, no SI: with no crisis signal to short-circuit at
    Node 1, the turn proceeds to intent_route and the HR redirect there sends it to
    the deterministic psychotic_referral auto-select -- a referral, not a skill offer.

    psychotic_referral is a one-step skill (step_policy=[]) that always completes in
    the same turn it is selected (see skill_executor's NOTE on psychotic_referral_delivered),
    so by the time the full graph reaches END, active_skill_id has already been cleared
    back to None -- that is the skill's normal completed state, not a failure to route.
    completed_skill_id / skill_match_method / psychotic_referral_delivered are the
    correct markers that the referral actually fired this turn.
    """
    _force_activate_hr_rules(monkeypatch)
    monkeypatch.setattr(config, "HIGH_RISK_DETECTION_ENABLED", True)
    _stub_intent_and_responder_llms(monkeypatch)

    from sage_poc.graph import build_graph
    app = build_graph()
    result = await app.ainvoke(
        {"raw_message": "nothing feels real", "path": []},
        config={"configurable": {"thread_id": "hr15-dissociation-only"}},
    )

    assert result.get("is_safe") is True
    assert result.get("gate_path") != "crisis"
    assert result.get("skill_match_method") == "psychotic_disclosure_auto_select"
    assert result.get("completed_skill_id") == "psychotic_referral"
    assert result.get("psychotic_referral_delivered") is True
