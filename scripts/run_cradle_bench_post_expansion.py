"""CRADLE bench post-expansion run.

Measures S1+S3 combined crisis recall on the full eval.jsonl after
crisis_phrases.json was expanded from 54 → 73 phrases.

Usage:
    /Users/knowledgebase/Documents/Sage/sage-poc/.venv/bin/python \
        /Users/knowledgebase/Documents/Sage/sage-poc/.worktrees/crisis-phrases-expansion/scripts/run_cradle_bench_post_expansion.py

This is a read-only eval script. It does NOT commit or write memory.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# ── sys.path bootstrap ────────────────────────────────────────────────────────
# IMPORTANT: worktree src must be FIRST so the expanded crisis_phrases.json
# (73 phrases) is picked up via s3_semantic._PHRASES_PATH = Path(__file__).parent/...
# If main branch src is first, Python imports the 54-phrase version and the
# test does not measure what we think it does.
sys.path.insert(0, "/Users/knowledgebase/Documents/Sage/sage-poc/.worktrees/crisis-phrases-expansion/src")
sys.path.insert(1, "/Users/knowledgebase/Documents/Sage/sage-poc/src")
sys.path.insert(2, "/Users/knowledgebase/Documents/Sage/sage-poc")

# ── load .env before importing sage_poc modules ───────────────────────────────
_ENV_PATH = Path("/Users/knowledgebase/Documents/Sage/sage-poc/.env")
if _ENV_PATH.exists():
    for _line in _ENV_PATH.read_text().splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _, _v = _line.partition("=")
        os.environ.setdefault(_k.strip(), _v.strip())

# Disable BGE warmup at server startup (we warm manually below)
os.environ["SAGE_WARMUP_BGE"] = "0"

# ── imports ───────────────────────────────────────────────────────────────────
from sage_poc.nodes.safety_check import safety_check_node  # noqa: E402

# Use worktree fixture data — same eval.jsonl as main branch
_EVAL_PATH = Path(
    "/Users/knowledgebase/Documents/Sage/sage-poc/tests/fixtures/cradle_bench/eval.jsonl"
)
_LABEL_MAP_PATH = Path(
    "/Users/knowledgebase/Documents/Sage/sage-poc/tests/fixtures/cradle_bench"
)
sys.path.insert(0, str(_LABEL_MAP_PATH.parent.parent))  # tests/
from tests.fixtures.cradle_bench.label_map import LABEL_MAP, CrisisTier  # noqa: E402
from tests.fixtures.cradle_bench.loader import load_cradle_split  # noqa: E402


# ── state factory (matches task spec exactly) ─────────────────────────────────

def _make_state(text: str) -> dict:
    return {
        "raw_message": text,
        "message_en": text,
        "detected_language": "en",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "distress_trajectory": [],
        "engagement_trajectory": [],
        "conversation_summary": None,
        "code_switching": False,
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "skill_match_method": None,
        "semantic_score": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "turn_number": 1,
        "conversation_history": [],
        "knowledge_passages": [],
        "knowledge_abstain": False,
        "knowledge_source": "",
        "session_id": "cradle-bench-post-expansion",
        "user_id": None,
    }


# ── pre-warm BGE-M3 ───────────────────────────────────────────────────────────

def prewarm_bge_m3() -> None:
    """Load BGE-M3 on CPU, build skill embeddings, build S3 phrase index."""
    print("[prewarm] Loading BGE-M3 on CPU ...", flush=True)
    t0 = time.perf_counter()
    import sage_poc.nodes.skill_select as ss
    from sage_poc.nodes.skill_select import _BGE_M3_REVISION
    if ss._embed_model is None:
        from sentence_transformers import SentenceTransformer
        try:
            model = SentenceTransformer(
                "BAAI/bge-m3",
                local_files_only=True,
                revision=_BGE_M3_REVISION,
                device="cpu",
            )
        except (OSError, EnvironmentError):
            model = SentenceTransformer(
                "BAAI/bge-m3",
                revision=_BGE_M3_REVISION,
                device="cpu",
            )
        ss._embed_model = model
    # Build skill embedding matrix
    ss._ensure_semantic_ready()
    print(f"[prewarm] BGE-M3 + skill matrix ready in {time.perf_counter()-t0:.1f}s", flush=True)

    # Build S3 crisis phrase index (MUST use worktree's crisis_phrases.json)
    from sage_poc.safety import s3_semantic as s3
    # Verify we are using the expanded file
    phrases_path = s3._PHRASES_PATH
    phrases_data = json.loads(phrases_path.read_text())
    n_phrases = len(phrases_data["phrases"])
    print(f"[prewarm] crisis_phrases.json path: {phrases_path}", flush=True)
    print(f"[prewarm] Phrase count: {n_phrases} (expected 73)", flush=True)

    print("[prewarm] Building S3 phrase index ...", flush=True)
    t1 = time.perf_counter()
    ok = s3._ensure_s3_ready()
    print(f"[prewarm] S3 index {'OK' if ok else 'FAILED'} in {time.perf_counter()-t1:.1f}s", flush=True)
    if not ok:
        raise RuntimeError("S3 index build failed — cannot run benchmark")


# ── eval loop ─────────────────────────────────────────────────────────────────

async def run_eval() -> None:
    if not _EVAL_PATH.exists():
        print(f"ERROR: eval.jsonl not found at {_EVAL_PATH}", file=sys.stderr)
        sys.exit(1)

    cases = load_cradle_split(_EVAL_PATH)
    crisis_cases = [c for c in cases if LABEL_MAP[c.label]["tier"] == "crisis"]
    safe_cases = [c for c in cases if c.label == "safe"]

    print(f"\n[eval] Loaded {len(cases)} total cases", flush=True)
    print(f"[eval] Crisis cases: {len(crisis_cases)}", flush=True)
    print(f"[eval] Safe cases:   {len(safe_cases)}", flush=True)

    # ── crisis recall ─────────────────────────────────────────────────────────
    crisis_results: list[dict] = []
    print(f"\n[eval] Running crisis recall ({len(crisis_cases)} cases) ...", flush=True)
    t0 = time.perf_counter()

    for i, case in enumerate(crisis_cases):
        state = _make_state(case.text)
        result = await safety_check_node(state)
        detected = result.get("is_safe") is False
        s3_fired = "s3_semantic" in result.get("crisis_flags", [])
        s1_fired = any(
            f != "s3_semantic" for f in result.get("crisis_flags", [])
        )
        crisis_results.append({
            "id": case.id,
            "label": case.label,
            "detected": detected,
            "s1_fired": s1_fired,
            "s3_fired": s3_fired,
            "s3_only": s3_fired and not s1_fired,
            "crisis_flags": result.get("crisis_flags", []),
        })
        if (i + 1) % 25 == 0:
            print(f"  ... {i+1}/{len(crisis_cases)} done ({time.perf_counter()-t0:.0f}s elapsed)", flush=True)

    print(f"[eval] Crisis loop complete in {time.perf_counter()-t0:.1f}s", flush=True)

    # ── specificity (safe cases) ──────────────────────────────────────────────
    safe_results: list[dict] = []
    print(f"\n[eval] Running specificity ({len(safe_cases)} cases) ...", flush=True)
    t1 = time.perf_counter()

    for i, case in enumerate(safe_cases):
        state = _make_state(case.text)
        result = await safety_check_node(state)
        triggered = result.get("is_safe") is False
        safe_results.append({
            "id": case.id,
            "triggered": triggered,
            "crisis_flags": result.get("crisis_flags", []),
        })
        if (i + 1) % 25 == 0:
            print(f"  ... {i+1}/{len(safe_cases)} done ({time.perf_counter()-t1:.0f}s elapsed)", flush=True)

    print(f"[eval] Specificity loop complete in {time.perf_counter()-t1:.1f}s", flush=True)

    # ── compute metrics ───────────────────────────────────────────────────────
    total_crisis = len(crisis_results)
    total_detected = sum(1 for r in crisis_results if r["detected"])
    overall_recall = total_detected / total_crisis if total_crisis else 0.0

    def sub_recall(label: str) -> tuple[int, int, float]:
        sub = [r for r in crisis_results if r["label"] == label]
        if not sub:
            return 0, 0, 0.0
        tp = sum(1 for r in sub if r["detected"])
        return tp, len(sub), tp / len(sub)

    sh_tp, sh_n, sh_recall = sub_recall("self_harm")
    asi_tp, asi_n, asi_recall = sub_recall("active_suicide_ideation")
    psi_tp, psi_n, psi_recall = sub_recall("passive_suicide_ideation")

    total_safe = len(safe_results)
    fp_list = [r for r in safe_results if r["triggered"]]
    fp_count = len(fp_list)
    tn = total_safe - fp_count
    specificity = tn / total_safe if total_safe else 0.0

    # S3-only recoveries (cases caught by S3 but not S1)
    s3_only_recoveries = [r for r in crisis_results if r["detected"] and r["s3_only"]]

    # Misses by label
    misses = [r for r in crisis_results if not r["detected"]]
    sh_misses = [r for r in misses if r["label"] == "self_harm"]

    # ── baseline numbers (pre-expansion, from task spec) ──────────────────────
    BASELINE = {
        "overall_recall": (37.1, 86, 232),
        "self_harm_recall": (18.0, 17, 92),
        "active_si_recall": (52.0, 34, 65),
        "passive_si_recall": (47.0, 35, 75),
        "specificity": (95.7, 178, 186),
    }

    # ── print report ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("CRADLE BENCH — POST-EXPANSION RESULTS")
    print("crisis_phrases.json: 54 → 73 phrases (self-harm register added)")
    print("S3_THRESHOLD: 0.8059 (unchanged)")
    print("=" * 70)

    print(f"\n{'Metric':<30} {'Before':>10} {'After':>10} {'Delta':>10}")
    print("-" * 62)

    def fmt_row(label, before_pct, after_tp, after_n, before_tp=None, before_n=None):
        after_pct = (after_tp / after_n * 100) if after_n else 0.0
        delta = after_pct - before_pct
        sign = "+" if delta >= 0 else ""
        print(
            f"{label:<30} {before_pct:>9.1f}% {after_pct:>9.1f}% {sign}{delta:>+8.1f}pp"
        )
        return after_pct

    fmt_row("Overall crisis recall",
            BASELINE["overall_recall"][0],
            total_detected, total_crisis)
    fmt_row("Self-harm recall",
            BASELINE["self_harm_recall"][0],
            sh_tp, sh_n)
    fmt_row("Active SI recall",
            BASELINE["active_si_recall"][0],
            asi_tp, asi_n)
    fmt_row("Passive SI recall",
            BASELINE["passive_si_recall"][0],
            psi_tp, psi_n)
    fmt_row("Specificity",
            BASELINE["specificity"][0],
            tn, total_safe)

    print("\n" + "=" * 70)
    print("COUNTS")
    print("=" * 70)
    print(f"Overall crisis:    {total_detected}/{total_crisis}  (was {BASELINE['overall_recall'][1]}/{BASELINE['overall_recall'][2]})")
    print(f"Self-harm:         {sh_tp}/{sh_n}  (was {BASELINE['self_harm_recall'][1]}/{BASELINE['self_harm_recall'][2]})")
    print(f"Active SI:         {asi_tp}/{asi_n}  (was {BASELINE['active_si_recall'][1]}/{BASELINE['active_si_recall'][2]})")
    print(f"Passive SI:        {psi_tp}/{psi_n}  (was {BASELINE['passive_si_recall'][1]}/{BASELINE['passive_si_recall'][2]})")
    print(f"Specificity:       {tn}/{total_safe}  (was {BASELINE['specificity'][1]}/{BASELINE['specificity'][2]})")

    print("\n" + "=" * 70)
    print("RECOVERY ANALYSIS")
    print("=" * 70)
    baseline_sh_misses = BASELINE["self_harm_recall"][2] - BASELINE["self_harm_recall"][1]  # 92-17=75
    sh_recovered = sh_tp - BASELINE["self_harm_recall"][1]
    print(f"Self-harm misses (before): {baseline_sh_misses}")
    print(f"Self-harm detected (after): {sh_tp}")
    print(f"Self-harm recovered: {sh_recovered} of {baseline_sh_misses} prior misses")
    print(f"S3-only recoveries (all crisis): {len(s3_only_recoveries)}")

    print(f"\nNew false positives introduced: {max(0, fp_count - (BASELINE['specificity'][2] - BASELINE['specificity'][1]))}")
    print(f"  FP count before: {BASELINE['specificity'][2] - BASELINE['specificity'][1]}  (={BASELINE['specificity'][2]}-{BASELINE['specificity'][1]})")
    print(f"  FP count after:  {fp_count}")

    if fp_list:
        print("\nFalse positives (safe cases flagged):")
        for r in fp_list:
            print(f"  {r['id']}  flags={r['crisis_flags']}")

    print("\n" + "=" * 70)
    print("MARKDOWN TABLE (for report)")
    print("=" * 70)
    overall_after = total_detected / total_crisis * 100 if total_crisis else 0.0
    sh_after = sh_tp / sh_n * 100 if sh_n else 0.0
    asi_after = asi_tp / asi_n * 100 if asi_n else 0.0
    psi_after = psi_tp / psi_n * 100 if psi_n else 0.0
    spec_after = tn / total_safe * 100 if total_safe else 0.0

    def sign(x):
        return f"+{x:.1f}pp" if x >= 0 else f"{x:.1f}pp"

    print("| Metric | Before | After | Delta |")
    print("|---|---|---|---|")
    print(f"| Overall crisis recall | 37.1% ({BASELINE['overall_recall'][1]}/{BASELINE['overall_recall'][2]}) | {overall_after:.1f}% ({total_detected}/{total_crisis}) | {sign(overall_after-37.1)} |")
    print(f"| Self-harm recall | 18.0% ({BASELINE['self_harm_recall'][1]}/{BASELINE['self_harm_recall'][2]}) | {sh_after:.1f}% ({sh_tp}/{sh_n}) | {sign(sh_after-18.0)} |")
    print(f"| Active SI recall | 52.0% ({BASELINE['active_si_recall'][1]}/{BASELINE['active_si_recall'][2]}) | {asi_after:.1f}% ({asi_tp}/{asi_n}) | {sign(asi_after-52.0)} |")
    print(f"| Passive SI recall | 47.0% ({BASELINE['passive_si_recall'][1]}/{BASELINE['passive_si_recall'][2]}) | {psi_after:.1f}% ({psi_tp}/{psi_n}) | {sign(psi_after-47.0)} |")
    print(f"| Specificity | 95.7% ({BASELINE['specificity'][1]}/{BASELINE['specificity'][2]}) | {spec_after:.1f}% ({tn}/{total_safe}) | {sign(spec_after-95.7)} |")

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)


# ── entrypoint ────────────────────────────────────────────────────────────────

def main() -> None:
    # Pre-warm synchronously before entering the event loop
    prewarm_bge_m3()
    asyncio.run(run_eval())


if __name__ == "__main__":
    main()
