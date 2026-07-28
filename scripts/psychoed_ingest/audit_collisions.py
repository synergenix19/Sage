# scripts/psychoed_ingest/audit_collisions.py
"""Cross-category trigger collision audit (spec §5.2). CI fails on undeclared collisions."""
import json, re
from pathlib import Path
from scripts.psychoed_ingest import schemas

COLLISION_TABLE = Path("data/psychoed/collisions/collision_table.json")

def _norm(p: str) -> str:
    return re.sub(r"[^\w\s']", "", p.lower()).strip()

def compute_collisions() -> dict[str, list[str]]:
    seen: dict[str, set[str]] = {}
    for t in schemas.iter_psychoed_files("trigger_table"):
        d = json.loads(t.read_text())
        for row in d["rows"]:
            for ph in row["phrases"]:
                seen.setdefault(_norm(ph), set()).add(d["category"])
    return {p: sorted(c) for p, c in seen.items() if len(c) > 1}

def undeclared_collisions() -> list[str]:
    declared = set()
    if COLLISION_TABLE.exists():
        declared = {_norm(e["phrase"]) for e in json.loads(COLLISION_TABLE.read_text())["collisions"]}
    return sorted(p for p in compute_collisions() if p not in declared)
