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
