"""Clinician-ruled additive safety cases (Item 2 of the sign-off sheet).

The genuine addition the clinician insisted on: a MATCHED perinatal-harm contrast pair, so the
router is tested in both directions and can't learn the wrong rule "baby + harm -> always
abstain":
  - harm-OCD (ego-dystonic intrusive images, avoidance/reassurance) -> ABSTAIN (over-escalation
    is iatrogenic + punitive), and
  - postpartum psychosis (ego-syntonic, command/delusion-driven) -> ESCALATE (psychiatric
    emergency).
Plus active-restriction ED: ABSTAIN on diagnosis BUT carries a safety_net flag (firmer than
body-image) so it can't be absorbed by a self-help skill.
"""
import json
from pathlib import Path

from sage_poc.routing_eval.gate_runner import harm_gate
from sage_poc.routing_eval.schema import ABSTAIN, ESCALATE, EvalRecord

_PATH = Path(__file__).parents[1] / "fixtures" / "routing_eval" / "additive_safety_cases.jsonl"


def _rows():
    return [json.loads(ln) for ln in _PATH.read_text().splitlines() if ln.strip()]


def _as_record(d: dict) -> EvalRecord:
    keep = {f for f in EvalRecord.__dataclass_fields__}
    return EvalRecord(**{k: v for k, v in d.items() if k in keep})


def _by_tag(tag):
    return [r for r in _rows() if r.get("tag") == tag]


def test_harm_ocd_and_psychosis_form_a_two_direction_contrast():
    ocd = _by_tag("harm_ocd")
    psy = _by_tag("postpartum_psychosis")
    assert ocd and psy, "need both halves of the contrast pair"
    for r in ocd:
        assert r["expected_route"] == ABSTAIN          # ego-dystonic OCD -> ABSTAIN
        assert r["harm_severity"] == "iatrogenic"
    for r in psy:
        assert r["expected_route"] == ESCALATE         # ego-syntonic emergency -> ESCALATE
        assert r["case_kind"] == "crisis_invariance"
        assert r["harm_severity"] == "critical"


def test_psychosis_absorbed_by_a_skill_fails_the_harm_gate():
    psy = [_as_record(r) for r in _by_tag("postpartum_psychosis")]
    assert harm_gate(psy, routed_of=lambda r: ESCALATE).passed is True
    assert harm_gate(psy, routed_of=lambda r: "self_compassion").passed is False


def test_active_ed_is_abstain_but_safety_net_protected():
    ed = _by_tag("active_ed")
    assert ed, "need the active-restriction ED case"
    for r in ed:
        assert r["expected_route"] == ABSTAIN
        assert r["harm_severity"] == "safety_net"
    recs = [_as_record(r) for r in ed]
    assert harm_gate(recs, routed_of=lambda r: ABSTAIN).passed is True
    assert harm_gate(recs, routed_of=lambda r: "behavioral_activation").passed is False
