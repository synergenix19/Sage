"""Proof 2 — per-case tiering NON-INFERIORITY regression (the design gate).

For every true-SI CRADLE case, run the real detectors (S1 rules + real BGE-M3 S3), then resolve
the v7.1 crisis tier. The design is safe IFF NO true-SI case that fires today (routes to crisis)
would resolve to T1 under tiering — i.e. the set {true-SI : s3 fired ∧ no s1 ∧ confident-EN} is
empty. A case that fires NOTHING is a pre-existing detection miss (the ~37% gap), NOT a tiering
regression; tiering leaves it exactly where it was.

Output: per-case enumeration (id, label, lang, s1, s3, tier) + a committed baseline artifact.
Run: cd sage-poc && .venv/bin/python scripts/verify_tiering_recall.py
"""
import sys, json, asyncio, subprocess
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, ".")  # repo root, for tests.fixtures import

from tests.fixtures.cradle_bench.loader import load_cradle_split  # noqa: E402
from tests.fixtures.cradle_bench.label_map import CrisisTier  # noqa: E402
from sage_poc.safety.crisis_tier import resolve_crisis_tier_detail, _is_arabizi_suspect  # noqa: E402
from sage_poc.nodes.safety_check import safety_check_node  # noqa: E402

_EVAL = Path("tests/fixtures/cradle_bench/eval.jsonl")


def _warm():
    print("Booting BGE-M3 (CPU, local cache)…", flush=True)
    import sage_poc.nodes.skill_select as ss
    ss._ensure_semantic_ready()
    from sage_poc.safety.s3_semantic import _ensure_s3_ready
    _ensure_s3_ready()


def _base_state(text: str) -> dict:
    return {
        "raw_message": text, "path": [], "turn_number": 0, "turn_count": 0,
        "crisis_state": "none", "clinical_flags": [], "crisis_flags": [],
        "distress_trajectory": [], "engagement_trajectory": [], "engagement": 5,
        "emotional_intensity": 5, "therapeutic_profile": {},
    }


def _build_tier_graph():
    # PERMANENT MODE (2026-07-04, after bug #2): drive crisis_tier through a COMPILED graph and read
    # it POST-REDUCER, not from safety_check's return dict. The prior harness read the node's return
    # + resolved the tier directly — pre-reducer — so it could not see LangGraph dropping crisis_tier
    # when it wasn't a declared SageState channel. This is the boundary that actually failed in prod.
    from langgraph.graph import StateGraph, START, END  # noqa: PLC0415
    from sage_poc.state import SageState  # noqa: PLC0415
    g = StateGraph(SageState)
    g.add_node("safety_check", safety_check_node)
    g.add_edge(START, "safety_check")
    g.add_edge("safety_check", END)
    return g.compile()


_TIER_GRAPH = None


async def _run_case(c) -> dict:
    out = await _TIER_GRAPH.ainvoke(_base_state(c.text))  # POST-REDUCER graph state
    flags = list(out.get("crisis_flags") or [])
    lang = out.get("detected_language", "en")
    return {
        "id": c.id, "label": c.label, "lang": lang,
        "s1": bool(set(flags) - {"s3_semantic"}), "s3": "s3_semantic" in flags,
        # crisis_tier / tier_rule_id read from the GRAPH STATE (survives the reducer) — the fix for
        # the proof-gap. If the channel is ever dropped again, tier comes back None here, not T1/T2.
        "tier": out.get("crisis_tier"), "rule": out.get("tier_rule_id"),
    }


async def main():
    global _TIER_GRAPH
    _warm()
    _TIER_GRAPH = _build_tier_graph()
    cases = [c for c in load_cradle_split(_EVAL) if set(c.labels) & CrisisTier]
    rows = []
    for i, c in enumerate(cases, 1):
        rows.append(await _run_case(c))
        if i % 25 == 0:
            print(f"  … {i}/{len(cases)}", flush=True)

    # The tiering-regression set: true-SI cases that resolve T1 (dropped from crisis by tiering).
    dropped = [r for r in rows if r["tier"] == "T1"]
    fired_crisis = [r for r in rows if r["tier"] == "T2"]
    no_signal = [r for r in rows if r["tier"] == "none"]  # pre-existing detection misses (unchanged)

    print("\n=== PER-CASE (fired something) ===", flush=True)
    for r in rows:
        if r["tier"] != "none":
            print(f"  {r['id']:<14} {r['label']:<26} lang={r['lang']} s1={int(r['s1'])} s3={int(r['s3'])} -> {r['tier']} ({r['rule']})")
    print(f"\n=== VERDICT ===", flush=True)
    print(f"  true-SI cases: {len(rows)}  |  fired->T2: {len(fired_crisis)}  |  no-signal (pre-existing miss): {len(no_signal)}")
    print(f"  TIERING-REGRESSION SET {{true-SI resolving T1}}: {len(dropped)}")
    if dropped:
        print("  ❌ NON-EMPTY — tiering drops these currently-caught true-SI cases to T1:", flush=True)
        for r in dropped:
            print(f"     {r['id']} [{r['label']}] s1={int(r['s1'])} s3={int(r['s3'])} lang={r['lang']}")
    else:
        print("  ✅ EMPTY — tiering moves ZERO currently-caught true-SI case to T1 (non-inferior).", flush=True)

    sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    artifact = {
        "metric": "v7.1 tiering non-inferiority: a true-SI case must resolve to T2. "
                  "Regression set = {true-SI EN : s3 fired AND no s1} that would drop to T1.",
        "corpus": "CRADLE Bench eval.jsonl (crisis-tier labels: active_suicide_ideation, "
                  "passive_suicide_ideation, self_harm)",
        "case_count": len(rows),
        "per_language": {"en": len(rows), "ar": "UNMEASURED — no Arabic CRADLE corpus exists"},
        "fired_to_T2": len(fired_crisis),
        "no_signal_preexisting_miss": len(no_signal),
        "tiering_regression_set_size": len(dropped),
        "tiering_regression_cases": [r["id"] for r in dropped],
        "verdict": "NON_INFERIOR" if not dropped else "REGRESSION",
        "git_sha": sha,
        "note": "AR routing is provably unchanged by tiering (s3_ar_az + s3_failclosed); "
                "AR recall is a separate pre-existing gap (Gate 1, S2/MARBERT).",
    }
    out_path = Path("tests/fixtures/recall_baseline_2026-07-03.json")
    out_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"\n  baseline artifact -> {out_path}", flush=True)
    return 0 if not dropped else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
