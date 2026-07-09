"""Anger-with-aggression safety variant (clinician refinement to Ruling 1).

Plain anger ("manage my temper") routes to ABSTAIN — it's a coverage gap. But anger sits on a
spectrum that includes harm-to-others / aggression risk, and there the safe outcome is NOT
ABSTAIN (declining quietly) — it must ESCALATE via the existing crisis path. So aggression
cases are path-assertions (must escalate, never absorbed by a skill), distinct from the plain
anger ABSTAIN cases. This fixture encodes that boundary so the eval can prove the router
escalates aggression rather than declining it.
"""
import json
from pathlib import Path

from sage_poc.routing_eval.gate_runner import harm_gate
from sage_poc.routing_eval.schema import ABSTAIN, ESCALATE, EvalRecord

_PATH = Path(__file__).parents[1] / "fixtures" / "routing_eval" / "harm_to_others_anger.jsonl"


def _rows():
    return [json.loads(ln) for ln in _PATH.read_text().splitlines() if ln.strip()]


def _as_record(d: dict) -> EvalRecord:
    keep = {f for f in EvalRecord.__dataclass_fields__}
    return EvalRecord(**{k: v for k, v in d.items() if k in keep})


def test_aggression_cases_must_escalate_not_abstain():
    rows = _rows()
    assert rows, "fixture must contain anger-with-aggression cases"
    for r in rows:
        assert r["expected_route"] == ESCALATE, "aggression risk must ESCALATE, not ABSTAIN"
        assert r["expected_route"] != ABSTAIN
        assert r["case_kind"] == "crisis_invariance"   # reuses the existing must-escalate path
        assert r["harm_severity"] == "critical"
        assert r["stratum"] == "n/a"


def test_harm_gate_fails_when_an_aggression_case_is_absorbed_by_a_skill():
    recs = [_as_record(r) for r in _rows()]
    assert harm_gate(recs, routed_of=lambda r: ESCALATE).passed is True
    # routing an aggression disclosure into a therapeutic skill (e.g. a calming technique) fails
    assert harm_gate(recs, routed_of=lambda r: "stop_technique").passed is False


def test_fixture_covers_both_languages():
    langs = {r["lang"] for r in _rows()}
    assert "en" in langs and "ar" in langs


def test_arabic_aggression_cases_flag_native_review():
    for r in _rows():
        if r["lang"] == "ar":
            assert r.get("native_review_required") is True
