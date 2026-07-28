# scripts/psychoed_ingest/audit_collisions.py
"""Cross-category trigger collision audit (spec §5.2): exact + subsumption. CI fails on undeclared collisions."""
import json, re
from pathlib import Path
from scripts.psychoed_ingest import schemas

COLLISION_TABLE = Path("data/psychoed/collisions/collision_table.json")

def _norm(p: str) -> str:
    return re.sub(r"[^\w\s']", "", p.lower()).strip()

def _all_phrase_categories() -> dict[str, set[str]]:
    seen: dict[str, set[str]] = {}
    for t in schemas.iter_psychoed_files("trigger_table"):
        d = json.loads(t.read_text())
        for row in d["rows"]:
            for ph in row["phrases"]:
                seen.setdefault(_norm(ph), set()).add(d["category"])
    return seen

def subsumption_pairs() -> list[dict]:
    """Cross-category subsumption: normalized phrase A (shorter) is a substring of normalized
    phrase B (longer), and A/B's category sets differ. Keyed detail, contained-phrase-first."""
    seen = _all_phrase_categories()
    phrases = sorted(seen.keys(), key=len)
    pairs = []
    for i, short in enumerate(phrases):
        for long_ in phrases[i + 1:]:
            if short != long_ and short in long_ and len(seen[short] | seen[long_]) > 1:
                pairs.append({
                    "short_phrase": short,
                    "short_categories": sorted(seen[short]),
                    "long_phrase": long_,
                    "long_categories": sorted(seen[long_]),
                })
    return pairs

def compute_collisions() -> dict[str, list[str]]:
    seen = _all_phrase_categories()
    collisions: dict[str, set[str]] = {p: set(c) for p, c in seen.items() if len(c) > 1}
    for pair in subsumption_pairs():
        collisions.setdefault(pair["short_phrase"], set()).update(pair["short_categories"])
        collisions[pair["short_phrase"]].update(pair["long_categories"])
    return {p: sorted(c) for p, c in collisions.items()}

def undeclared_collisions() -> list[str]:
    declared: set[str] = set()
    if COLLISION_TABLE.exists():
        table = json.loads(COLLISION_TABLE.read_text())
        declared = {_norm(e["phrase"]) for e in table.get("collisions", [])}
        declared |= {_norm(e["short_phrase"]) for e in table.get("subsumption_collisions", [])}
    return sorted(p for p in compute_collisions() if p not in declared)
