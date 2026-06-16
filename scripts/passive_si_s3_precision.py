#!/usr/bin/env python3
"""#18 (LOCK-SF1-02) measurement harness — passive-SI recall + S3 precision/marginal-recall.

Read-only. Loads the eval set, runs the S1 rules engine and the S3 (BGE-M3) semantic
detector per case, and reports per-bucket:

  - S1 recall            (keyword detector — load-bearing, esp AR/AZ)
  - S3 fire-rate         (>= S3_THRESHOLD)
  - S3 MARGINAL recall   = expected-crisis cases S1 MISSES but S3 catches  ← the gate
  - S3 precision         = on distress_not_si, fraction S3 wrongly fires   ← the FP problem

GATE for the tactical FP exclusion (FPE-EN-002, "feel like a failure" family):
  it is certifiable-safe iff S3 marginal recall = 0 on the cooccurring + passive_si buckets
  (i.e. every true-crisis case S3 catches is ALSO caught by S1, so blanket-suppressing
  s3_semantic for that phrase family loses nothing). See
  docs/superpowers/governance/2026-06-14-crisis-precision-s3-signoff-package.md.

This harness does NOT change any production behaviour and ships nothing. Certification of
results requires clinician validation of the eval set (esp. Arabic) + the results sign-off.

Run: uv run python scripts/passive_si_s3_precision.py
"""
import json
from pathlib import Path
from collections import defaultdict

from sage_poc.rules import engine as rules_engine
from sage_poc.safety.s3_semantic import check_s3_bilingual, S3_THRESHOLD

EVAL = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "passive_si_eval" / "eval_en.jsonl"


def s1_fires(text_en: str, text_ar: str | None, lang: str) -> tuple[bool, list[str]]:
    """True + flag_ids if the S1 rules engine raises a (non-suppressed) crisis flag."""
    res = rules_engine.evaluate("safety", {
        "text_en": text_en,
        "text_ar": text_ar,
        "language": lang,
        "text_raw": text_en if lang != "ar" else (text_ar or text_en),
    })
    flags = [a["flag_id"] for a in res.actions if a.get("type") == "crisis_flag"]
    # third_party overrides (mirror safety_check)
    if any(a.get("type") == "third_party_crisis" for a in res.actions):
        flags = []
    return (len(flags) > 0, flags)


def main() -> None:
    cases = [json.loads(l) for l in EVAL.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"=== #18 S3-precision / passive-SI harness ===")
    print(f"eval set: {EVAL}  ({len(cases)} cases)   S3_THRESHOLD={S3_THRESHOLD}\n")

    by_bucket: dict[str, list[dict]] = defaultdict(list)
    rows = []
    for c in cases:
        en = c["text"] if c["lang"] != "ar" else ""
        ar = c["text"] if c["lang"] == "ar" else None
        s1, s1flags = s1_fires(en, ar, c["lang"])
        s3score = check_s3_bilingual(en or "", ar)
        s3 = s3score >= S3_THRESHOLD
        rec = {**c, "s1": s1, "s1flags": s1flags, "s3": s3, "s3score": round(s3score, 4)}
        rows.append(rec)
        by_bucket[c["bucket"]].append(rec)

    # Per-case table
    print(f"{'id':12} {'bucket':16} {'exp':4} {'S1':3} {'S3':3} {'s3score':8} text")
    for r in rows:
        print(f"{r['id']:12} {r['bucket']:16} {str(r['expected_crisis'])[0]:4} "
              f"{('Y' if r['s1'] else '.'):3} {('Y' if r['s3'] else '.'):3} {r['s3score']:<8} {r['text'][:60]}")

    print("\n=== per-bucket summary ===")
    for bucket, recs in by_bucket.items():
        n = len(recs)
        s1_rec = sum(r["s1"] for r in recs)
        s3_fire = sum(r["s3"] for r in recs)
        if recs[0]["expected_crisis"]:
            # recall buckets
            either = sum(r["s1"] or r["s3"] for r in recs)
            marginal = [r for r in recs if (not r["s1"]) and r["s3"]]   # S3 catches what S1 misses
            missed_both = [r for r in recs if not (r["s1"] or r["s3"])]
            print(f"\n[{bucket}] n={n}  (expected=CRISIS)")
            print(f"  S1 recall:           {s1_rec}/{n}")
            print(f"  S1-or-S3 recall:     {either}/{n}")
            print(f"  S3 MARGINAL recall:  {len(marginal)}/{n}  (S1 miss + S3 catch)  <- gate: must be 0")
            if marginal:
                for r in marginal:
                    print(f"      MARGINAL: {r['id']} {r['text']!r} (s3score={r['s3score']})")
            if missed_both:
                for r in missed_both:
                    print(f"      MISSED BY BOTH: {r['id']} {r['text']!r} (s3score={r['s3score']})  <- recall gap (#2)")
        else:
            # precision bucket (distress_not_si): S3 fire = false positive
            s3_fp = [r for r in recs if r["s3"]]
            s1_fp = [r for r in recs if r["s1"]]
            print(f"\n[{bucket}] n={n}  (expected=NOT crisis)")
            print(f"  S3 false positives:  {len(s3_fp)}/{n}  (FP rate {len(s3_fp)/n:.0%})  <- the precision problem")
            for r in s3_fp:
                print(f"      S3 FP: {r['id']} {r['text']!r} (s3score={r['s3score']})")
            print(f"  S1 false positives:  {len(s1_fp)}/{n}")
            for r in s1_fp:
                print(f"      S1 FP: {r['id']} {r['text']!r} flags={r['s1flags']}")

    # Gate verdict for FPE-EN-002 (failure family)
    crisis_recs = [r for r in rows if r["expected_crisis"]]
    marginal_all = [r for r in crisis_recs if (not r["s1"]) and r["s3"]]
    print("\n=== GATE VERDICT (English, first-pass set) ===")
    print(f"S3 marginal recall over S1 (all expected-crisis): {len(marginal_all)}/{len(crisis_recs)}")
    if not marginal_all:
        print("  -> S3 adds 0 marginal recall on this set: suppressing s3_semantic for the")
        print("     'feel like a failure' family loses no S1-uncaught crisis here. FPE-EN-002")
        print("     blast radius == empty ON THIS SET. (Certification still needs clinician-")
        print("     validated + Arabic-extended set + results sign-off.)")
    else:
        print("  -> S3 carries NON-ZERO marginal recall: FPE blast radius is NON-EMPTY.")
        print("     Do NOT ship the blanket exclusion as-is; narrow it or keep S3 as trigger.")


if __name__ == "__main__":
    main()
