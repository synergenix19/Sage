#!/usr/bin/env python3
# scripts/coverage_matrix.py
"""Wrong-skill routing coverage matrix.

Runs all 125 colloquial phrases from tests/fixtures/wrong_skill/cases.py through
the production skill_select_node and prints a per-skill coverage table.

Usage (from sage-poc repo root):
    python scripts/coverage_matrix.py

Output columns:
  T1     — Tier 1 (keyword) match, correct skill
  T2-OK  — Tier 2 (semantic) match, correct skill
  T2-ERR — Tier 2 match, WRONG skill (semantic bleed)
  MISS   — No match at all (active_skill_id is None)
  TOTAL  — always 5 per skill
  *      — within-cluster psychoed mismatch (not counted as T2-ERR)

Interpreting results:
  High T1 / 0 T2-OK  → skill has no semantic coverage; fragile if new phrasing misses keywords
  High T2-ERR        → semantic bleed to another skill; fix with Tier 1 keyword expansion
  High MISS          → phrases have neither keyword nor semantic match; priority for expansion
  psychoed cluster   → within-cluster mismatches expected; fix with per-skill Tier 1 keywords
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sage_poc.nodes.skill_select import skill_select_node
from tests.fixtures.wrong_skill.cases import WRONG_SKILL_CASES, PSYCHOED_CLUSTER


def _make_state(phrase: str) -> dict:
    return {
        "raw_message": phrase,
        "detected_language": "en",
        "message_en": phrase,
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "primary_intent": "new_skill",
        "secondary_intent": None,
        "intent_confidence": 1.0,
        "emotional_intensity": 5,
        "engagement": 7,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
        "skill_match_method": None,
        "semantic_score": None,
        "distress_trajectory": [],
        "code_switching": False,
    }


async def run_all() -> list[dict]:
    results = []
    total = len(WRONG_SKILL_CASES)
    for i, (expected_skill, phrase) in enumerate(WRONG_SKILL_CASES, 1):
        print(f"\r  Running {i}/{total}...", end="", flush=True)
        state = _make_state(phrase)
        result = await skill_select_node(state)
        actual = result.get("active_skill_id")
        method = result.get("skill_match_method")
        score = result.get("semantic_score")

        # Categorise
        within_cluster = (
            expected_skill in PSYCHOED_CLUSTER
            and actual in PSYCHOED_CLUSTER
            and actual != expected_skill
        )

        if actual == expected_skill and method == "keyword":
            category = "T1"
        elif actual == expected_skill and method == "semantic":
            category = "T2-OK"
        elif within_cluster:
            category = "CLUSTER"  # psychoed within-cluster — not a hard error
        elif actual is not None and actual != expected_skill:
            category = "T2-ERR"
        else:
            category = "MISS"

        results.append({
            "expected": expected_skill,
            "actual": actual,
            "method": method,
            "score": score,
            "phrase": phrase,
            "category": category,
        })
    print()
    return results


def print_matrix(results: list[dict]) -> None:
    from collections import defaultdict
    by_skill: dict[str, dict[str, int]] = defaultdict(
        lambda: {"T1": 0, "T2-OK": 0, "T2-ERR": 0, "CLUSTER": 0, "MISS": 0}
    )
    for r in results:
        by_skill[r["expected"]][r["category"]] += 1

    col_w = 38
    print()
    print(
        f"{'Skill':<{col_w}} {'T1':>5} {'T2-OK':>6} "
        f"{'T2-ERR':>7} {'CLUST*':>7} {'MISS':>6} {'TOTAL':>6}"
    )
    print("-" * (col_w + 45))

    t1_t = t2ok_t = t2err_t = clust_t = miss_t = 0
    for skill in sorted(by_skill):
        c = by_skill[skill]
        t1, t2ok, t2err, clust, miss = c["T1"], c["T2-OK"], c["T2-ERR"], c["CLUSTER"], c["MISS"]
        total_row = t1 + t2ok + t2err + clust + miss
        flag = ""
        if t2err > 0 or miss > 0:
            flag = " ⚠"
        elif clust > 0:
            flag = " *"
        print(
            f"{skill:<{col_w}} {t1:>5} {t2ok:>6} "
            f"{t2err:>7} {clust:>7} {miss:>6} {total_row:>6}{flag}"
        )
        t1_t += t1; t2ok_t += t2ok; t2err_t += t2err; clust_t += clust; miss_t += miss

    print("-" * (col_w + 45))
    grand = t1_t + t2ok_t + t2err_t + clust_t + miss_t
    print(
        f"{'TOTAL':<{col_w}} {t1_t:>5} {t2ok_t:>6} "
        f"{t2err_t:>7} {clust_t:>7} {miss_t:>6} {grand:>6}"
    )
    print()
    print("T1=keyword correct, T2-OK=semantic correct, T2-ERR=wrong skill, CLUST*=within-psychoed, MISS=no match")
    hard_gaps = t2err_t + miss_t
    print(f"Hard gaps (⚠): {t2err_t} T2-ERR + {miss_t} MISS = {hard_gaps} phrases need keyword expansion")
    if clust_t:
        print(f"Soft gaps (*): {clust_t} within-psychoed-cluster (acceptable — fix with Tier 1 keywords)")


def print_failures(results: list[dict]) -> None:
    failures = [r for r in results if r["category"] in ("T2-ERR", "MISS")]
    if not failures:
        print("\nNo hard routing failures — all 125 phrases routed correctly (ignoring psychoed cluster).")
        return

    print(f"\n{'─' * 72}")
    print(f"HARD ROUTING FAILURES ({len(failures)} phrases):")
    print(f"{'─' * 72}")
    for r in sorted(failures, key=lambda x: (x["expected"], x["category"])):
        print(f"\n  [{r['category']}] Expected : {r['expected']}")
        print(f"          Got      : {r['actual']!r}  (score={r['score']})")
        print(f"          Phrase   : {r['phrase']!r}")

    cluster_misses = [r for r in results if r["category"] == "CLUSTER"]
    if cluster_misses:
        print(f"\n{'─' * 72}")
        print(f"WITHIN-CLUSTER (psychoed, not hard failures) — {len(cluster_misses)} phrases:")
        print(f"{'─' * 72}")
        for r in sorted(cluster_misses, key=lambda x: (x["expected"], x["actual"])):
            print(f"\n  [CLUSTER] Expected : {r['expected']}")
            print(f"            Got      : {r['actual']!r}  (score={r['score']})")
            print(f"            Phrase   : {r['phrase']!r}")


if __name__ == "__main__":
    print("Loading BGE-M3 and running 125 phrases through skill_select_node...")
    print("(First run takes ~30s for model warmup; subsequent runs are faster)\n")
    results = asyncio.run(run_all())
    print_matrix(results)
    print_failures(results)
