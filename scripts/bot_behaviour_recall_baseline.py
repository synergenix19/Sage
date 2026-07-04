"""Shared recall-measurement harness for the BOT BEHAVIOUR safety-route fixtures
(ingestion plan §3). ENGINEERING TEST INFRA — changes no production behaviour.

§3 CONSTRAINT (enforced by construction): the runner is CODE and the fixtures are
CONTENT. This file hardcodes NO clinical phrase — every phrase is loaded from the
JSON fixtures in tests/fixtures/bot_behaviour/. The runner only knows, per fixture,
which detector SIGNAL means "fired".

It reuses the real detector exactly as verify_tiering_recall.py does: a compiled
safety_check-only graph, run per phrase, read post-reducer. Reports PER-CLASS recall
(positives that fire) and precision (negatives that do NOT fire), and writes a
committed baseline artifact.

Run:  cd sage-poc-bb-fixtures-wt && uv run python scripts/bot_behaviour_recall_baseline.py
"""
import sys, json, asyncio
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, ".")

from langgraph.graph import StateGraph, START, END  # noqa: E402
from sage_poc.state import SageState  # noqa: E402
from sage_poc.nodes.safety_check import safety_check_node  # noqa: E402

FIX_DIR = Path("tests/fixtures/bot_behaviour")

# Per-fixture: which detector signal counts as "fired". Reads only the graph's
# output state — never the phrase text. A signal returning None means "no detector
# exists yet" (E3), reported as a 0% baseline with that fact stated.
def _crisis_fired(s):   # §C
    return (s.get("is_safe") is False) or bool(s.get("crisis_flags")) or (s.get("crisis_tier") in ("T1", "T2"))
def _medical_fired(s):  # E3 — no medical route exists yet
    return any("medical" in f or "red_flag" in f for f in (s.get("clinical_flags") or []))
def _hr_fired(s):       # E4
    return "psychotic_disclosure" in (s.get("clinical_flags") or [])
def _ipv_fired(s):      # E7
    return "domestic_situation" in (s.get("clinical_flags") or [])

FIXTURES = {
    "crisis_sc_recall.json":  {"gate": "§C / GL-0", "signal": _crisis_fired, "detector": "S1 rules + S3 BGE-M3 (live)"},
    "medical_e3_recall.json": {"gate": "E3 medical", "signal": _medical_fired, "detector": "NONE — E3 route unbuilt (baseline expected ~0)"},
    "hr_e4_recall.json":      {"gate": "E4 HR", "signal": _hr_fired, "detector": "psychotic_disclosure clinical flag (keyword-only, psychosis; CF-006 gated in prod)"},
    "ipv_e7_recall.json":     {"gate": "E7 IPV", "signal": _ipv_fired, "detector": "domestic_situation clinical flag (keyword-only lexicon)"},
}


def _iter_phrases(node, parent_key=None):
    """Yield (phrase, class) from any fixture shape, without knowing the schema.
    Handles: {class:[str]}, {class:{phrases:[str]}}, {phrases:[{phrase,class}]}."""
    if isinstance(node, list):
        for item in node:
            if isinstance(item, str):
                yield item, parent_key
            elif isinstance(item, dict) and "phrase" in item:
                yield item["phrase"], item.get("class", parent_key)
    elif isinstance(node, dict):
        for k, v in node.items():
            if k.startswith("_"):
                continue
            if k == "phrases":
                yield from _iter_phrases(v, parent_key)
            else:
                yield from _iter_phrases(v, k)


def _base_state(text):
    return {"raw_message": text, "path": [], "turn_number": 0, "turn_count": 0,
            "crisis_state": "none", "clinical_flags": [], "crisis_flags": [],
            "distress_trajectory": [], "engagement_trajectory": [], "engagement": 5,
            "emotional_intensity": 5, "therapeutic_profile": {}}


def _build_graph():
    g = StateGraph(SageState)
    g.add_node("safety_check", safety_check_node)
    g.add_edge(START, "safety_check")
    g.add_edge("safety_check", END)
    return g.compile()


async def _fire(graph, signal, text):
    s = await graph.ainvoke(_base_state(text))
    return bool(signal(s))


def _pct(n, d):
    return f"{100.0*n/d:5.1f}%" if d else "  n/a"


async def main():
    print("Booting BGE-M3 S3 (CPU, local cache)…", flush=True)
    import sage_poc.nodes.skill_select as ss; ss._ensure_semantic_ready()
    from sage_poc.safety.s3_semantic import _ensure_s3_ready; _ensure_s3_ready()
    graph = _build_graph()

    report = {"authored": "2026-07-04", "note": "current-detector baseline; runner=code, fixtures=content", "gates": {}}
    for fname, cfg in FIXTURES.items():
        data = json.loads((FIX_DIR / fname).read_text())
        print(f"\n=== {cfg['gate']}  ({fname}) — detector: {cfg['detector']} ===")
        gate = {"detector": cfg["detector"], "positive_recall": {}, "negative_precision": {}}
        # recall per positive class
        pos = {}
        for phrase, cls in _iter_phrases(data.get("positive", {})):
            pos.setdefault(cls, []).append(phrase)
        for cls, phrases in pos.items():
            fired = 0
            for p in phrases:
                if await _fire(graph, cfg["signal"], p):
                    fired += 1
            gate["positive_recall"][cls] = {"fired": fired, "total": len(phrases)}
            print(f"  recall  [{cls:28}] {fired:3}/{len(phrases):<3} = {_pct(fired, len(phrases))}")
        # precision per negative class (must NOT fire)
        neg = {}
        for phrase, cls in _iter_phrases(data.get("negative", {})):
            neg.setdefault(cls, []).append(phrase)
        for cls, phrases in neg.items():
            if not phrases:
                print(f"  precis  [{cls:28}]   0/0   = held (clinician-authored, not yet populated)")
                continue
            not_fired = 0
            for p in phrases:
                if not await _fire(graph, cfg["signal"], p):
                    not_fired += 1
            gate["negative_precision"][cls] = {"not_fired": not_fired, "total": len(phrases)}
            print(f"  precis  [{cls:28}] {not_fired:3}/{len(phrases):<3} = {_pct(not_fired, len(phrases))} did-not-fire")
        report["gates"][cfg["gate"]] = gate

    out = FIX_DIR / "recall_baseline_2026-07-04.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"\nBaseline artifact written: {out}")


if __name__ == "__main__":
    asyncio.run(main())
