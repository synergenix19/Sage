"""Regeneration script for F1 wiring fixtures (Phase 3 Task 2).

F1 wiring rows are GENERATED from data/psychoed/trigger_tables/en/*.json: one row per
trigger phrase, `set:"wiring"`, expecting the resolver's mechanical routing (category +
row_id match via `psychoed_matched_row_id`). The generated JSONL is committed
(tests/fixtures/psychoed/f1_wiring.jsonl) so the corpus stays readable/diffable in review,
but the committed file is NOT the source of truth -- the trigger tables are.
`test_f1_wiring_matches_generator` in tests/test_psychoed_fixtures_ci.py re-generates from
the tables on every CI run and fails if the committed file has drifted, so hand-editing
f1_wiring.jsonl, or editing a trigger table without regenerating, both fail CI.

Regenerate after any trigger_tables/en/*.json edit:

    uv run python -m tests.fixtures.psychoed.regen_wiring

`set:"wiring"` rows assert MECHANICAL routing only (does the phrase resolve to the right
category/row_id and produce a serve), never clinical recall/accuracy evidence -- see the
corpus README's provenance section for why wiring rows must never be quoted as recall.
"""
from __future__ import annotations

import json
import pathlib

TABLES_DIR = pathlib.Path(__file__).resolve().parents[3] / "data" / "psychoed" / "trigger_tables" / "en"
OUTPUT_PATH = pathlib.Path(__file__).parent / "f1_wiring.jsonl"


def generate_rows(tables_dir: pathlib.Path = TABLES_DIR) -> list[dict]:
    """One fixture row per (row_id, phrase) pair across every en trigger table.

    Deterministic order: tables sorted by filename, rows in table order, phrases in
    table order -- so two runs over the same tables always produce byte-identical output
    (the sync test relies on this).
    """
    rows: list[dict] = []
    for table_path in sorted(tables_dir.glob("*.json")):
        table = json.loads(table_path.read_text(encoding="utf-8"))
        category = table["category"]
        lang = table.get("language", "en")
        for row in table["rows"]:
            row_id = row["row_id"]
            phrases = row["phrases"]
            for idx, phrase in enumerate(phrases, start=1):
                fixture_id = f"F1-{row_id}-{idx:02d}"
                rows.append({
                    "fixture_id": fixture_id,
                    "family": "F1",
                    "set": "wiring",
                    "category": category,
                    "turns": [
                        {"utterance": phrase, "intent_sweep": False, "intent": "info_request"},
                    ],
                    "expect": {
                        "disposition": "psychoed_serve",
                        "audit": {"psychoed_matched_row_id": row_id},
                        "state": {"psychoed_active_category": category},
                    },
                    "delta_cite": None,
                    "repin_on": None,
                    "lang": lang,
                    "source": (
                        f"generated: data/psychoed/trigger_tables/en/{table_path.name} "
                        f"row {row_id} ({row.get('type', '?')}) phrase {idx}/{len(phrases)}; "
                        "regenerate via `uv run python -m tests.fixtures.psychoed.regen_wiring`"
                    ),
                })
    return rows


def write_wiring_file(rows: list[dict], output_path: pathlib.Path = OUTPUT_PATH) -> None:
    text = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"
    output_path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    written = generate_rows()
    write_wiring_file(written)
    print(f"wrote {len(written)} rows to {OUTPUT_PATH}")
