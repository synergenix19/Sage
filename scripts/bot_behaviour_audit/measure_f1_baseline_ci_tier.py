"""Durable helper: F1-naturalistic recall-by-category, CI tier (patched-intent).

Recreated from the reproduction recipe disclosed in
docs/2026-08-05-psychoed-f1-baseline-145c4e43.md ("How this was measured"): that doc
committed the *aggregate* number (0/61) from an ad hoc pytest function that was run once
and then deleted -- not part of the permanent suite, not committed. Final-review Minor 5
flagged that this is a primary-record risk that is only defused today because every
category happens to be 0/61 (self-corroborating against the flip-tier record and the CI
xfail count); it stops being defused the moment the block-hints addendum (spec §10 entry
12) lands and these numbers go non-zero. This script IS that instrument, committed as a
durable, reproducible helper so the next F1-naturalistic re-measurement has a real
primary record instead of a one-off deleted script.

It produces the same table committed at docs/2026-08-05-psychoed-f1-baseline-145c4e43.md's
"Recall by category (CI tier)" section: for every `baseline_only` F1 row
(tests/fixtures/psychoed/f1_naturalistic.jsonl, blind-authored, Task 3), drive it
full-graph through the SAME driver functions the CI suite itself uses
(load_family/run_fixture/assert_expectations/_arm_psychoed, imported unmodified from
tests.test_psychoed_fixtures_ci -- same patched-intent context: mocked
intent_route_node, stubbed freeflow LLM, monkeypatch-only flag arming), catch
assert_expectations' AssertionError per row (miss) instead of letting it propagate to an
xfail marker the way test_psychoed_baseline_only does (hit = no AssertionError raised),
and collate hit/total by category.

Run with:
    .venv/bin/python -m pytest scripts/bot_behaviour_audit/measure_f1_baseline_ci_tier.py -q -s

Writes a per-row + per-category JSON breakdown next to this file
(measure_f1_baseline_ci_tier.output.json) and prints the recall-by-category table to
stdout. This is a measurement tool, not a gate -- it is deliberately NOT wired into
unit-gate.yml's CANDIDATES list, and asserts nothing about the aggregate recall number
(a real collection/driver failure above the measurement loop still raises normally, the
same as any other test).
"""
from __future__ import annotations

import json
import pathlib
from collections import defaultdict

import pytest

from tests.test_psychoed_fixtures_ci import (
    _arm_psychoed,
    assert_expectations,
    load_family,
    run_fixture,
)

_OUT = pathlib.Path(__file__).parent / "measure_f1_baseline_ci_tier.output.json"


async def test_f1_baseline_per_category_ci_tier():
    """The durable instrument itself. See module docstring for provenance and shape."""
    rows = [r for r in load_family("F1") if r.get("baseline_only")]
    assert rows, "no baseline_only F1 rows found -- f1_naturalistic.jsonl missing or its marker was removed"

    per_row: list[dict] = []
    by_category: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # [hits, total]

    for row in rows:
        with pytest.MonkeyPatch.context() as mp:
            _arm_psychoed(mp, row)
            out = await run_fixture(row)
        try:
            assert_expectations(row, out)
            hit = True
        except AssertionError:
            hit = False

        category = row["category"]
        by_category[category][1] += 1
        if hit:
            by_category[category][0] += 1

        result = out["result"]
        per_row.append({
            "fixture_id": row["fixture_id"],
            "category": category,
            "hit": hit,
            "psychoed_serve": result.get("psychoed_serve"),
            "psychoed_active_category": result.get("psychoed_active_category"),
        })

    summary = {
        cat: {"hit": h, "total": t, "recall": (h / t if t else 0.0)}
        for cat, (h, t) in sorted(by_category.items())
    }
    total_hit = sum(h for h, _t in by_category.values())
    total_n = sum(t for _h, t in by_category.values())
    summary["overall"] = {
        "hit": total_hit,
        "total": total_n,
        "recall": (total_hit / total_n if total_n else 0.0),
    }

    _OUT.write_text(json.dumps({"per_row": per_row, "by_category": summary}, indent=2))

    print("\n| category | hit/total | recall |")
    print("|---|---|---|")
    for cat, s in summary.items():
        if cat == "overall":
            continue
        print(f"| {cat} | {s['hit']}/{s['total']} | {s['recall'] * 100:.1f}% |")
    o = summary["overall"]
    print(f"| **overall** | **{o['hit']}/{o['total']}** | **{o['recall'] * 100:.1f}%** |")
