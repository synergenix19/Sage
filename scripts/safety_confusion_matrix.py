#!/usr/bin/env python3
# scripts/safety_confusion_matrix.py
"""S1 rules-engine safety detection confusion matrix.

Runs all safety test cases from tests/fixtures/safety/cases.py through
rules_engine.evaluate() directly — synchronous, no async, no LLM calls.

This measures the S1-only baseline because S1 is the only load-bearing detection
layer (S2 not built; S3 advisory, adds 0 recall on CRADLE passive-SI set at any
threshold 0.65–0.8059, per 2026-06-05 sweep).

Usage (from sage-poc repo root):
    python scripts/safety_confusion_matrix.py

Output:
  Per-category confusion matrix (TP / FN / FP / TN)
  Overall crisis recall and precision
  KPI check: crisis recall >= 95%
  Known-gap vs unexpected-gap breakdown

Terminology:
  TP — expected_is_crisis=True  AND system detected crisis
  FN — expected_is_crisis=True  AND system missed crisis
  TN — expected_is_crisis=False AND system correctly returned safe
  FP — expected_is_crisis=False AND system incorrectly flagged crisis
  known_fn — documented gap; expected to fail; do not fix until baseline measured
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sage_poc.rules.engine import evaluate
from tests.fixtures.safety.cases import SAFETY_CASES, SafetyCase


@dataclass
class CaseResult:
    case: SafetyCase
    actual_is_crisis: bool
    actual_crisis_flags: list[str]
    actual_clinical_flags: list[str]
    outcome: str  # TP | FN | TN | FP


def _run_case(case: SafetyCase) -> CaseResult:
    """Evaluate one SafetyCase through the S1 rules engine."""
    if case.language == "ar":
        ctx = {"text_en": "", "text_ar": case.phrase, "text_raw": case.phrase, "language": "ar"}
    elif case.language == "az":
        ctx = {"text_en": case.phrase, "text_ar": "", "text_raw": case.phrase, "language": "az"}
    else:
        ctx = {"text_en": case.phrase, "text_ar": "", "text_raw": case.phrase, "language": "en"}

    result = evaluate("safety", ctx)
    crisis_flags = [a["flag_id"] for a in result.actions if a.get("type") == "crisis_flag"]
    clinical_flags = [a["flag_id"] for a in result.actions if a.get("type") == "clinical_flag"]
    actual_is_crisis = len(crisis_flags) > 0

    if case.expected_is_crisis and actual_is_crisis:
        outcome = "TP"
    elif case.expected_is_crisis and not actual_is_crisis:
        outcome = "FN"
    elif not case.expected_is_crisis and not actual_is_crisis:
        outcome = "TN"
    else:
        outcome = "FP"

    return CaseResult(
        case=case,
        actual_is_crisis=actual_is_crisis,
        actual_crisis_flags=crisis_flags,
        actual_clinical_flags=clinical_flags,
        outcome=outcome,
    )


def _recall(tp: int, fn: int) -> str:
    total = tp + fn
    if total == 0:
        return "   n/a"
    return f"{100 * tp / total:5.1f}%"


def _precision(tp: int, fp: int) -> str:
    total = tp + fp
    if total == 0:
        return "   n/a"
    return f"{100 * tp / total:5.1f}%"


def run() -> None:
    results = [_run_case(c) for c in SAFETY_CASES]

    # ── Per-category aggregation ──────────────────────────────────────────────
    categories = ["tp_explicit", "tp_passive_si", "tp_cumulative", "tn_idiom", "tn_clinical_only"]
    cat_stats: dict[str, dict[str, int]] = {
        cat: {"TP": 0, "FN": 0, "FP": 0, "TN": 0, "total": 0} for cat in categories
    }

    for r in results:
        s = cat_stats[r.case.category]
        s["total"] += 1
        s[r.outcome] += 1

    # ── Print table ───────────────────────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║     Safety Detection Confusion Matrix — S1 Rules Engine Baseline (2026)     ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    print(f"{'Category':<22} {'Total':>5}  {'TP':>4} {'FN':>4} {'FP':>4} {'TN':>4}  {'Recall':>7}  {'Precision':>9}")
    print("─" * 78)

    overall_tp = overall_fn = overall_fp = overall_tn = 0

    for cat in categories:
        s = cat_stats[cat]
        tp, fn, fp, tn = s["TP"], s["FN"], s["FP"], s["TN"]
        overall_tp += tp; overall_fn += fn; overall_fp += fp; overall_tn += tn
        rec = _recall(tp, fn)
        pre = _precision(tp, fp)
        tp_str = f"{tp:4}" if tp else "   -"
        fn_str = f"{fn:4}" if fn else "   -"
        fp_str = f"{fp:4}" if fp else "   -"
        tn_str = f"{tn:4}" if tn else "   -"
        print(f"{cat:<22} {s['total']:>5}  {tp_str} {fn_str} {fp_str} {tn_str}  {rec}  {pre:>9}")

    print("─" * 78)
    overall_rec = _recall(overall_tp, overall_fn)
    overall_pre = _precision(overall_tp, overall_fp)
    print(
        f"{'OVERALL (crisis)':<22} {len(results):>5}  "
        f"{overall_tp:4} {overall_fn:4} {overall_fp:4} {overall_tn:4}  "
        f"{overall_rec}  {overall_pre:>9}"
    )
    print()

    # ── KPI ───────────────────────────────────────────────────────────────────
    crisis_total = overall_tp + overall_fn
    crisis_recall_pct = 100 * overall_tp / crisis_total if crisis_total else 0.0
    kpi_pass = crisis_recall_pct >= 95.0
    kpi_label = "PASS ✓" if kpi_pass else "FAIL ✗"
    print(f"KPI: Crisis recall ≥ 95%  →  {crisis_recall_pct:.1f}%  [{kpi_label}]")
    print()

    # ── FN breakdown ─────────────────────────────────────────────────────────
    fn_results = [r for r in results if r.outcome == "FN"]
    known_fn = [r for r in fn_results if r.case.known_fn]
    unexpected_fn = [r for r in fn_results if not r.case.known_fn]

    print(f"False Negatives: {len(fn_results)} total  ({len(known_fn)} documented gap  |  {len(unexpected_fn)} unexpected)")
    print()

    if unexpected_fn:
        print("  !! UNEXPECTED FNs — investigate immediately:")
        for r in unexpected_fn:
            print(f"     [{r.case.category}] [{r.case.rule_hint or '?'}]  {r.case.phrase[:80]!r}")
            print(f"       Note: {r.case.note}")
        print()

    if known_fn:
        print("  Documented gaps (known_fn=True) — do not fix until baseline is established:")
        mech_groups: dict[str, list[CaseResult]] = defaultdict(list)
        for r in known_fn:
            mech_groups[r.case.mechanism].append(r)
        for mech, group in sorted(mech_groups.items()):
            print(f"    [{mech}] — {len(group)} phrase(s)")
            for r in group:
                phrase_short = r.case.phrase[:72]
                print(f"      · {phrase_short!r}")
        print()

    # ── FP breakdown ─────────────────────────────────────────────────────────
    fp_results = [r for r in results if r.outcome == "FP"]
    if fp_results:
        print(f"False Positives: {len(fp_results)}")
        for r in fp_results:
            print(f"  [{r.case.category}] [{r.case.rule_hint or '?'}]  {r.case.phrase[:72]!r}")
            print(f"    Flags fired: {r.actual_crisis_flags}")
            print(f"    Note: {r.case.note}")
        print()

    # ── Clinical flag accuracy (tn_clinical_only) ─────────────────────────────
    clinical_cases = [r for r in results if r.case.category == "tn_clinical_only"]
    clinical_correct = sum(
        1 for r in clinical_cases
        if r.case.expected_flag in r.actual_clinical_flags
    )
    if clinical_cases:
        print(
            f"Clinical flag accuracy (tn_clinical_only): "
            f"{clinical_correct}/{len(clinical_cases)} cases have expected flag in clinical_flags"
        )
        for r in clinical_cases:
            ok = "✓" if r.case.expected_flag in r.actual_clinical_flags else "✗"
            print(f"  {ok} [{r.case.rule_hint}] {r.case.expected_flag!r}  ← {r.case.phrase[:60]!r}")
        print()

    print("Interpretation:")
    print("  TP / FN rows show coverage gaps in S1 lexicon.")
    print("  FP rows show false-trigger risk (suppression bugs or missing FPE rules).")
    print("  known_fn=True gaps need clinical specification before engineering fix.")
    print("  Re-run after any safety rule edit to track regression/progress.")
    print()


if __name__ == "__main__":
    run()
