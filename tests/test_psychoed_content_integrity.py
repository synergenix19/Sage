from pathlib import Path
import json, pytest
from scripts.psychoed_ingest import schemas

def _blocks():
    return sorted(Path("data/psychoed/blocks/en").rglob("*.json"))

def test_at_least_one_block_exists():
    assert _blocks(), "no psychoed blocks found"

@pytest.mark.parametrize("path", _blocks() or [Path("MISSING")])
def test_block_schema_valid(path):
    errs = schemas.validate_block(path)
    assert errs == [], f"{path}: {errs}"

@pytest.mark.parametrize("path", _blocks() or [Path("MISSING")])
def test_block_no_em_dashes(path):
    text = json.loads(path.read_text())["content"]
    for ch in schemas.EM_DASHES:
        assert ch not in text, f"{path}: em/en dash in served copy"

@pytest.mark.parametrize("path", _blocks() or [Path("MISSING")])
def test_block_source_citation(path):
    d = json.loads(path.read_text())
    assert d["psychoed"]["source_citation"]["file"] == schemas.SOURCE_FILE


COVERAGE = {
    "1f": ["1f-b1", "1f-b2", "1f-b3", "1f-b4", "1f-b5"],
    "3c": ["3c-b1", "3c-b2", "3c-b3", "3c-b4", "3c-b5", "3c-b6", "3c-b7"],
    "4b": ["4b-b1", "4b-b2", "4b-b3", "4b-b4", "4b-b5", "4b-b6", "4b-b7"],
    "6d": ["6d-b1", "6d-b2", "6d-b3", "6d-b4", "6d-b5", "6d-b6"],
    "7c": ["7c-b1", "7c-b2", "7c-b3", "7c-b4", "7c-b5", "7c-b6", "7c-b7"],
}


def test_manifests_valid():
    paths = schemas.iter_psychoed_files("manifest")
    assert paths, "no manifests"
    for p in paths:
        assert schemas.validate_manifest(p) == [], p


def test_trigger_tables_valid():
    paths = schemas.iter_psychoed_files("trigger_table")
    assert paths, "no trigger tables"
    for p in paths:
        assert schemas.validate_trigger_table(p) == [], p


def test_trigger_table_rows_carry_valid_provenance():
    paths = schemas.iter_psychoed_files("trigger_table")
    assert paths, "no trigger tables"
    for p in paths:
        d = json.loads(p.read_text())
        for r in d.get("rows", []):
            assert r.get("row_provenance") in schemas.ROW_PROVENANCES, (p, r.get("row_id"))


def test_1f_trigger_rows_are_all_inferred():
    p = Path("data/psychoed/trigger_tables/en/1f.json")
    d = json.loads(p.read_text())
    assert d["rows"], "1f trigger table has no rows"
    for r in d["rows"]:
        assert r["row_provenance"] == "inferred", r["row_id"]


def test_coverage_registry_matches_disk():
    on_disk = {p.stem for p in schemas.iter_psychoed_files("block")}
    declared = {b for blocks in COVERAGE.values() for b in blocks}
    assert declared <= on_disk, f"declared but missing: {declared - on_disk}"


def _write_manifest(tmp_path, **overrides):
    base = {
        "category": "1f",
        "delivery_shape": "menu_first",
        "safety_weave": False,
        "framing_statement": "Framing.",
        "menu_offer": "Menu.",
        "check_in": "Check in.",
        "blocks": ["1f-b1"],
        "bridge_map": [{"block_id": "1f-b1", "skill_id": "box_breathing", "offer": "optional"}],
        "source_citation": {"file": schemas.SOURCE_FILE, "section": "1f"},
    }
    base.update(overrides)
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(base))
    return p


def test_bridge_map_skill_id_must_be_in_registry(tmp_path):
    p = _write_manifest(
        tmp_path,
        bridge_map=[{"block_id": "1f-b1", "skill_id": "worry_tree", "offer": "optional"}],
    )
    errs = schemas.validate_manifest(p)
    assert any("registry" in e for e in errs), errs


def test_bridge_map_null_skill_id_requires_doc_target_and_status(tmp_path):
    p = _write_manifest(
        tmp_path,
        bridge_map=[{"block_id": "1f-b4", "skill_id": None, "offer": "optional"}],
    )
    errs = schemas.validate_manifest(p)
    assert any("doc_target" in e or "status" in e for e in errs), errs

    p_ok = _write_manifest(
        tmp_path,
        bridge_map=[
            {
                "block_id": "1f-b4",
                "skill_id": None,
                "doc_target": "Worry Tree",
                "offer": "optional",
                "status": "pending_clinician_no_registry_skill",
            }
        ],
    )
    assert schemas.validate_manifest(p_ok) == []


def test_bridge_map_null_block_id_requires_condition(tmp_path):
    p = _write_manifest(
        tmp_path,
        bridge_map=[
            {"block_id": None, "skill_id": "assertive_communication", "offer": "optional"}
        ],
    )
    errs = schemas.validate_manifest(p)
    assert any("condition" in e for e in errs), errs

    p_ok = _write_manifest(
        tmp_path,
        bridge_map=[
            {
                "block_id": None,
                "skill_id": "assertive_communication",
                "offer": "optional",
                "condition": "specific_person_or_message",
            }
        ],
    )
    assert schemas.validate_manifest(p_ok) == []
