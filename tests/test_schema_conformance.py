"""Tests for the schema field conformance registry."""
import pytest
from sage_poc.skills.conformance import SCHEMA_CONFORMANCE, get_conformance_report


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


def test_total_field_count_is_15():
    assert len(SCHEMA_CONFORMANCE) == 15, (
        f"Got {len(SCHEMA_CONFORMANCE)} fields — update this count when adding new schema fields"
    )


def test_used_and_partial_fields_have_injected_by():
    for field, info in SCHEMA_CONFORMANCE.items():
        if info["status"] in ("USED", "PARTIAL"):
            assert info.get("injected_by") is not None, (
                f"{field} has status {info['status']!r} but injected_by is None"
            )
