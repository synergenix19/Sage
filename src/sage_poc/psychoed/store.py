"""In-process store for the Phase-1 psychoed content artifacts (data/psychoed/**).

The ONLY source of ratified psychoed copy at runtime (spec §3; Phase-2 handoff).
Loads once, lazily. Copy never appears as literals in code. The SOURCE_SHA CI
guard (tests/test_psychoed_content_integrity.py) pins these files to the doc.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path

_DATA = Path(__file__).resolve().parents[3] / "data" / "psychoed"

class PendingClinicianScript(RuntimeError):
    """Raised when a consuming path requests a shared script still awaiting clinical authorship."""

class _Store:
    def __init__(self) -> None:
        self._blocks: dict[str, dict] = {}
        for f in sorted((_DATA / "blocks" / "en").rglob("*.json")):
            d = json.loads(f.read_text())
            self._blocks[d["article_id"]] = d
        self._manifests = {
            f.stem: json.loads(f.read_text()) for f in sorted((_DATA / "manifests").glob("*.json"))
        }
        self._tables = [
            json.loads(f.read_text()) for f in sorted((_DATA / "trigger_tables" / "en").glob("*.json"))
        ]
        self._collisions = json.loads((_DATA / "collisions" / "collision_table.json").read_text())
        self._shared = json.loads((_DATA / "shared" / "shared_scripts.en.json").read_text())["scripts"]
        self._weave = json.loads((_DATA / "weave" / "psy_weave_1.en.json").read_text())

_instance: _Store | None = None

def _s() -> _Store:
    global _instance
    if _instance is None:
        _instance = _Store()
    return _instance

def reload_for_tests() -> None:
    global _instance
    _instance = None

def get_block(block_id: str) -> dict | None:
    return _s()._blocks.get(block_id)

def block_ids() -> frozenset[str]:
    return frozenset(_s()._blocks)

def manifest(category: str) -> dict:
    return _s()._manifests[category]

def category_of(block_id: str) -> str:
    return _s()._blocks[block_id]["psychoed"]["category"]

def family_of_kb_ref(kb_ref: str) -> str | None:
    blocks = _s()._blocks
    if kb_ref in blocks:
        return blocks[kb_ref]["psychoed"]["article_family"]
    families = {b["psychoed"]["article_family"] for b in blocks.values()}
    return kb_ref if kb_ref in families else None

def trigger_rows() -> list[dict]:
    rows: list[dict] = []
    for t in _s()._tables:
        for r in t["rows"]:
            rows.append({**r, "category": t["category"]})
    return rows

def collision_entries() -> dict:
    return _s()._collisions

def shared_script(name: str) -> str:
    v = _s()._shared[name]
    if v.startswith("PENDING-CLINICIAN"):
        raise PendingClinicianScript(name)
    return v

def weave_data() -> dict:
    return _s()._weave

def block_sha256(block_id: str) -> str:
    return hashlib.sha256(_s()._blocks[block_id]["content"].encode("utf-8")).hexdigest()
