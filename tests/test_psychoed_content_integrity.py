from pathlib import Path
import json, pytest

pytestmark = pytest.mark.safety_gate
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
    "s2c": ["s2c-b1", "s2c-b2", "s2c-b3", "s2c-b4", "s2c-b5", "s2c-b6", "s2c-b7", "s2c-b8"],
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


def test_block_guard_only_on_s2c_b8():
    guarded = [p.stem for p in schemas.iter_psychoed_files("block")
               if "block_guard" in json.loads(p.read_text())["psychoed"]]
    assert guarded == ["s2c-b8"]


def test_shared_scripts_present_and_single_sourced():
    d = json.loads(Path("data/psychoed/shared/shared_scripts.en.json").read_text())
    assert set(d["scripts"].keys()) == {"diagnosis_guard_stage1", "diagnosis_guard_stage2",
                                        "safety_weave_script", "human_referral_close"}
    # Single-source: no shared-script sentence may appear inside any block/manifest (#321 class).
    corpus = " ".join(p.read_text() for p in schemas.iter_psychoed_files("block"))
    corpus += " ".join(p.read_text() for p in schemas.iter_psychoed_files("manifest"))
    for name, text in d["scripts"].items():
        probe = text[:60]
        assert probe not in corpus, f"{name} duplicated into content ({probe!r})"


def test_no_undeclared_collisions():
    from scripts.psychoed_ingest import audit_collisions
    assert audit_collisions.undeclared_collisions() == []


def _write_fixture_trigger_tables(tmp_path):
    t1 = tmp_path / "zx.json"
    t1.write_text(json.dumps({
        "category": "zx",
        "rows": [{"row_id": "zx-t1", "phrases": ["I feel bad."]}],
    }))
    t2 = tmp_path / "zy.json"
    t2.write_text(json.dumps({
        "category": "zy",
        "rows": [{"row_id": "zy-t1", "phrases": ["I feel bad today."]}],
    }))
    return [t1, t2]


def test_subsumption_collision_caught_when_undeclared(tmp_path, monkeypatch):
    from scripts.psychoed_ingest import audit_collisions

    fixtures = _write_fixture_trigger_tables(tmp_path)
    monkeypatch.setattr(schemas, "iter_psychoed_files", lambda kind: fixtures)
    monkeypatch.setattr(audit_collisions, "COLLISION_TABLE", tmp_path / "collision_table.json")

    assert audit_collisions.subsumption_pairs() == [{
        "short_phrase": "i feel bad",
        "short_categories": ["zx"],
        "long_phrase": "i feel bad today",
        "long_categories": ["zy"],
    }]
    assert audit_collisions.undeclared_collisions() == ["i feel bad"]


def test_subsumption_collision_passes_when_declared(tmp_path, monkeypatch):
    from scripts.psychoed_ingest import audit_collisions

    fixtures = _write_fixture_trigger_tables(tmp_path)
    collision_table = tmp_path / "collision_table.json"
    collision_table.write_text(json.dumps({
        "note": "test fixture",
        "subsumption_rule": "test rule",
        "collisions": [],
        "subsumption_collisions": [
            {
                "short_phrase": "I feel bad.",
                "long_phrase": "I feel bad today.",
                "categories": ["zx", "zy"],
                "resolution": {"winner": "zy", "loser": "zx"},
            }
        ],
    }))

    monkeypatch.setattr(schemas, "iter_psychoed_files", lambda kind: fixtures)
    monkeypatch.setattr(audit_collisions, "COLLISION_TABLE", collision_table)

    assert audit_collisions.undeclared_collisions() == []


def test_weave_data_shape_and_fail_closed_examples():
    d = json.loads(Path("data/psychoed/weave/psy_weave_1.en.json").read_text())
    assert d["status"] == "draft-pending-clinician"
    assert d["clear_negative_patterns"] and d["contradiction_markers"]
    assert d["evaluation_semantics"]["default"] == "fail_closed_to_crisis"
    import re
    def is_clear_negative(reply: str) -> bool:
        norm = re.sub(r"[^\w\s']", "", reply.lower()).strip()
        if any(m in norm for m in d["contradiction_markers"]):
            return False
        return any(re.fullmatch(p, norm) for p in d["clear_negative_patterns"])
    # natural clear negatives MUST pass (spec §6.1 false-crisis cost)
    for ok in ["No", "no, nothing like that", "No, alhamdulillah", "no I haven't, why?",
               "no thank god"]:
        assert is_clear_negative(ok), ok
    # everything else fails closed
    for bad in ["kind of", "sometimes", "not really but...", "no, but sometimes",
                "actually, what is anxiety?"]:
        assert not is_clear_negative(bad), bad


FULL_MAP = {
    "1f": 5, "3c": 7, "4b": 7, "6d": 6, "7c": 7, "s2c": 8,
}

def test_full_coverage_by_name():
    for cat, n in FULL_MAP.items():
        blocks = COVERAGE.get(cat, [])
        assert len(blocks) == n, f"{cat}: {len(blocks)}/{n} blocks declared"
        expected = [f"{cat}-b{i}" for i in range(1, n + 1)]
        assert blocks == expected, f"{cat}: IDs must be {expected}"
    manifests = {p.stem for p in schemas.iter_psychoed_files("manifest")}
    tables = {p.stem for p in schemas.iter_psychoed_files("trigger_table")}
    assert manifests == set(FULL_MAP), f"manifests: {manifests}"
    assert tables == set(FULL_MAP), f"trigger tables: {tables}"

def test_manifest_scripts_complete():
    for p in schemas.iter_psychoed_files("manifest"):
        d = json.loads(p.read_text())
        for f in ("framing_statement", "menu_offer", "check_in"):
            assert d[f].strip() and "<VERBATIM" not in d[f], f"{p.stem}.{f} untranscribed"


def test_source_file_hash_matches_pinned_sha():
    import hashlib
    actual = hashlib.sha256(Path(schemas.SOURCE_FILE).read_bytes()).hexdigest()
    assert actual == schemas.SOURCE_SHA, (
        f"{schemas.SOURCE_FILE} hash changed since SOURCE_SHA was pinned "
        f"({actual} != {schemas.SOURCE_SHA}) — ratified source moved underneath "
        f"already-signed artifacts, STOP and reconcile, do not silently re-transcribe"
    )
