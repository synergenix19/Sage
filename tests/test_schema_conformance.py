"""Tests for the schema field conformance registry."""
import pytest
from sage_poc.skills.conformance import SCHEMA_CONFORMANCE, get_conformance_report
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """TestClient for testing endpoints."""
    from server import app
    with TestClient(app) as c:
        yield c


VALID_STATUSES = {"USED", "STORED_ONLY", "PARTIAL"}
EXPECTED_FIELDS = {
    "step.goal",
    "step.technique",
    "step.technique_description",
    "step.tone",
    "step.examples",
    "step.contraindications",
    "step.completion_criteria",
    "skill.cultural_overrides",
    "skill.criteria_hold_budget",
    "skill.hold_ceiling",
    "skill.escalation_matrix.L1",
    "skill.escalation_matrix.L2",
    "skill.escalation_matrix.L3",
    "skill.escalation_matrix.L4",
    "skill.evidence_base",
    "skill.skill_type",
    "skill.self_evolution",
}


def test_all_expected_fields_present():
    assert EXPECTED_FIELDS <= set(SCHEMA_CONFORMANCE.keys()), (
        f"Missing: {EXPECTED_FIELDS - set(SCHEMA_CONFORMANCE.keys())}"
    )


def test_every_field_has_valid_status():
    for field, info in SCHEMA_CONFORMANCE.items():
        assert info["status"] in VALID_STATUSES, f"{field} has invalid status {info['status']!r}"


def test_every_field_has_note():
    for field, info in SCHEMA_CONFORMANCE.items():
        assert isinstance(info.get("note"), str) and info["note"], f"{field} missing note"


def test_cultural_overrides_is_used():
    """After Task 1, cultural_overrides must be USED."""
    assert SCHEMA_CONFORMANCE["skill.cultural_overrides"]["status"] == "USED"


def test_criteria_hold_budget_is_used():
    assert SCHEMA_CONFORMANCE["skill.criteria_hold_budget"]["status"] == "USED"


def test_hold_ceiling_is_used():
    assert SCHEMA_CONFORMANCE["skill.hold_ceiling"]["status"] == "USED"


def test_escalation_matrix_l1_is_used():
    assert SCHEMA_CONFORMANCE["skill.escalation_matrix.L1"]["status"] == "USED"


def test_stored_only_fields_have_no_injected_by():
    for field, info in SCHEMA_CONFORMANCE.items():
        if info["status"] == "STORED_ONLY":
            assert info.get("injected_by") is None, (
                f"{field} is STORED_ONLY but has injected_by: {info['injected_by']!r}"
            )


def test_get_conformance_report_structure():
    report = get_conformance_report()
    assert "summary" in report
    assert "fields" in report
    s = report["summary"]
    assert set(s.keys()) >= {"used", "partial", "stored_only", "total"}
    assert s["total"] == len(SCHEMA_CONFORMANCE)
    assert s["used"] + s["partial"] + s["stored_only"] == s["total"]


def test_get_conformance_report_is_json_serializable():
    import json
    report = get_conformance_report()
    serialized = json.dumps(report)
    assert len(serialized) > 0


def test_total_field_count_is_17():
    assert len(SCHEMA_CONFORMANCE) == 17, (
        f"Got {len(SCHEMA_CONFORMANCE)} fields — update this count when adding new schema fields"
    )


def test_used_and_partial_fields_have_injected_by():
    for field, info in SCHEMA_CONFORMANCE.items():
        if info["status"] in ("USED", "PARTIAL"):
            assert info.get("injected_by") is not None, (
                f"{field} has status {info['status']!r} but injected_by is None"
            )


# ---- endpoint tests ----

def test_schema_conformance_endpoint_returns_200(client):
    response = client.get("/health/schema-conformance")
    assert response.status_code == 200


def test_schema_conformance_endpoint_returns_expected_shape(client):
    data = client.get("/health/schema-conformance").json()
    assert "summary" in data
    assert "fields" in data
    assert data["summary"]["total"] == 17


def test_schema_conformance_endpoint_cultural_overrides_is_used(client):
    data = client.get("/health/schema-conformance").json()
    assert data["fields"]["skill.cultural_overrides"]["status"] == "USED"


# ---- escalation_matrix truth-in-code pins (every skill JSON) ----------------
#
# These pins encode the VERIFIED runtime reality of the escalation_matrix so the
# corpus cannot silently re-grow a capability the code does not enforce:
#   L1  -> the ONLY level read at runtime (skill_executor reads escalation_matrix["L1"]).
#   L2  -> STORED_ONLY; the real behaviour is the clinical-flag machinery
#          (output_gate._log_clinical_review -> clinician_review_queue), not this string.
#   L3  -> STORED_ONLY; the real behaviour is the safety graph
#          (_route_after_safety -> _crisis_response_node), not this string.
#   L4  -> NOT_IMPLEMENTED; no enforcer exists anywhere (human-handoff automation deferred).
# If someone re-adds an imperative L2/L3/L4 string that implies these fire, these
# tests fail and force the change back through the conformance registry.

import json
import pathlib

_SKILLS_DIR = pathlib.Path(__file__).parent.parent / "src" / "sage_poc" / "skills"
_ALL_SKILL_JSON = sorted(_SKILLS_DIR.glob("*.json"))
_STORED_ONLY_MARKER = "[STORED_ONLY"
_NOT_IMPLEMENTED_MARKER = "[NOT_IMPLEMENTED"


def _em(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))["escalation_matrix"]


def test_skill_json_corpus_is_nonempty():
    # Guards against a broken glob silently making every parametrised pin vacuous.
    assert len(_ALL_SKILL_JSON) >= 20, f"only found {len(_ALL_SKILL_JSON)} skill JSONs"


@pytest.mark.parametrize("path", _ALL_SKILL_JSON, ids=lambda p: p.stem)
def test_escalation_l1_present_and_not_annotated(path):
    """L1 is the only runtime-read level: it must be present, non-empty, and must
    NOT carry a STORED_ONLY / NOT_IMPLEMENTED annotation (that would neuter a live path)."""
    em = _em(path)
    l1 = em.get("L1", "")
    assert l1.strip(), f"{path.stem}: L1 missing/empty — L1 is runtime-read (skill_executor)"
    assert not l1.startswith(_STORED_ONLY_MARKER), f"{path.stem}: L1 is runtime-read, must not be STORED_ONLY-annotated"
    assert not l1.startswith(_NOT_IMPLEMENTED_MARKER), f"{path.stem}: L1 is runtime-read, must not be NOT_IMPLEMENTED-annotated"


@pytest.mark.parametrize("path", _ALL_SKILL_JSON, ids=lambda p: p.stem)
def test_escalation_l2_annotated_to_clinical_flag_enforcer(path):
    """L2 must be STORED_ONLY-annotated and name its real enforcer (clinical-flag machinery)."""
    l2 = _em(path)["L2"]
    assert l2.startswith(_STORED_ONLY_MARKER), f"{path.stem}: L2 must be STORED_ONLY-annotated, got {l2[:40]!r}"
    assert "output_gate._log_clinical_review" in l2, f"{path.stem}: L2 annotation must name output_gate._log_clinical_review"
    assert "clinician_review_queue" in l2, f"{path.stem}: L2 annotation must name clinician_review_queue"


@pytest.mark.parametrize("path", _ALL_SKILL_JSON, ids=lambda p: p.stem)
def test_escalation_l3_annotated_to_safety_graph(path):
    """L3 must be STORED_ONLY-annotated and name its real enforcer (the safety graph)."""
    l3 = _em(path)["L3"]
    assert l3.startswith(_STORED_ONLY_MARKER), f"{path.stem}: L3 must be STORED_ONLY-annotated, got {l3[:40]!r}"
    assert "_route_after_safety" in l3, f"{path.stem}: L3 annotation must name _route_after_safety"
    assert "_crisis_response_node" in l3, f"{path.stem}: L3 annotation must name _crisis_response_node"


@pytest.mark.parametrize("path", _ALL_SKILL_JSON, ids=lambda p: p.stem)
def test_escalation_l4_marked_not_implemented(path):
    """L4 has NO enforcer anywhere — it must be explicitly marked NOT_IMPLEMENTED."""
    l4 = _em(path)["L4"]
    assert l4.startswith(_NOT_IMPLEMENTED_MARKER), f"{path.stem}: L4 must be NOT_IMPLEMENTED-annotated, got {l4[:40]!r}"
    assert "human-handoff" in l4, f"{path.stem}: L4 annotation must reference the deferred human-handoff automation"


def test_only_l1_is_read_at_runtime():
    """No production module may read escalation_matrix L2/L3/L4 by key; at least one reads L1.

    This is the code-side twin of the JSON pins: it keeps the runtime honest even if
    the annotations above are edited. Scans src/sage_poc only (not tests)."""
    src_root = pathlib.Path(__file__).parent.parent / "src" / "sage_poc"
    forbidden = []
    l1_readers = 0
    for py in src_root.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for lvl in ("L2", "L3", "L4"):
            for pat in (f'escalation_matrix["{lvl}"]', f"escalation_matrix['{lvl}']",
                        f'escalation_matrix.get("{lvl}"', f"escalation_matrix.get('{lvl}'"):
                if pat in text:
                    forbidden.append(f"{py.relative_to(src_root)}: {pat}")
        if 'escalation_matrix.get("L1"' in text or 'escalation_matrix["L1"]' in text:
            l1_readers += 1
    assert not forbidden, f"escalation_matrix L2/L3/L4 read at runtime (STORED_ONLY/NOT_IMPLEMENTED): {forbidden}"
    assert l1_readers >= 1, "expected at least one runtime read of escalation_matrix L1"


def test_conformance_registry_matches_pins():
    """The registry must still classify L1 USED and L2/L3/L4 STORED_ONLY."""
    assert SCHEMA_CONFORMANCE["skill.escalation_matrix.L1"]["status"] == "USED"
    for lvl in ("L2", "L3", "L4"):
        assert SCHEMA_CONFORMANCE[f"skill.escalation_matrix.{lvl}"]["status"] == "STORED_ONLY"
