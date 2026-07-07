"""Case-29 boundary dataset: red-flag somatic must escalate, recognized-recurrent must not.

The clinician's stratified call (C default + red-flag MEDICAL_REFERRAL) is only real if the
held-out set can PROVE the boundary fires in BOTH directions. A benign-only set (just the
original case 29) false-passes a router that has never seen a red-flag presentation. So this
fixture must carry:
  - the four named red-flag variants (radiation, dyspnea, exertional, syncope) → MEDICAL_REFERRAL
  - at least one already-cardiology-cleared recurrent panic case → stays on the support skill
and the harm gate must bite when a red-flag case is absorbed by a therapeutic skill.
"""
import json
from pathlib import Path

from sage_poc.routing_eval.gate_runner import harm_gate
from sage_poc.routing_eval.schema import MEDICAL_REFERRAL, EvalRecord

_PATH = Path(__file__).parents[1] / "fixtures" / "routing_eval" / "redflag_somatic.jsonl"


def _rows():
    return [json.loads(ln) for ln in _PATH.read_text().splitlines() if ln.strip()]


def _as_record(d: dict) -> EvalRecord:
    keep = {f for f in EvalRecord.__dataclass_fields__}
    return EvalRecord(**{k: v for k, v in d.items() if k in keep})


def test_redflag_cases_are_path_assertions_to_medical_referral():
    referrals = [r for r in _rows() if r["expected_route"] == MEDICAL_REFERRAL]
    assert referrals, "fixture must contain red-flag MEDICAL_REFERRAL cases"
    for r in referrals:
        assert r["case_kind"] == "medical_referral"
        assert r["harm_severity"] == "critical"
        assert r["stratum"] == "n/a"          # path-assertion, excluded from the AUGRC curve


def test_all_four_named_redflag_variants_present():
    tags = {r.get("redflag") for r in _rows() if r["expected_route"] == MEDICAL_REFERRAL}
    for variant in ("radiation", "dyspnea", "exertional", "syncope"):
        assert variant in tags, f"missing red-flag variant: {variant}"


def test_recognized_recurrent_case_stays_on_support_path():
    recurrent = [r for r in _rows()
                 if r["case_kind"] == "normal" and r["expected_route"] == "psychoed_anxiety"]
    assert recurrent, "fixture must include an already-cleared recurrent panic case (the other direction)"
    for r in recurrent:
        assert r["stratum"] == "in_scope"


def test_harm_gate_bites_in_both_directions_on_the_real_fixture():
    referrals = [_as_record(r) for r in _rows() if r["expected_route"] == MEDICAL_REFERRAL]
    # Correct: every red-flag case routes to the medical referral terminal → gate passes.
    assert harm_gate(referrals, routed_of=lambda r: MEDICAL_REFERRAL).passed is True
    # Wrong: absorbing ANY red-flag case into the anxiety skill → gate fails.
    assert harm_gate(referrals, routed_of=lambda r: "psychoed_anxiety").passed is False
