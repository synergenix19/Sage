"""
Latency benchmark: measures TTFB across all major turn types, English and Arabic.

TTFB = time from POST /chat to first byte of body (= total time post-ainvoke removal).

Usage:
    uv run python scripts/benchmark_latency.py [--runs N] [--url http://localhost:8765]

Default: 5 runs per scenario. Results written to docs/superpowers/audits/<date>-latency-benchmark.md
"""
from __future__ import annotations
import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8765"
TIMEOUT = 90.0
_RUN_ID = str(int(time.time()))[-6:]


# ── HTTP helpers ──────────────────────────────────────────────────────────────

async def chat(
    message: str,
    session_id: str,
    url: str = BASE_URL,
) -> tuple[float, str, dict]:
    """POST /chat. Returns (ttfb_seconds, body, response_headers)."""
    payload = {
        "messages": [{"role": "user", "content": message}],
        "session_id": session_id,
    }
    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        async with client.stream("POST", f"{url}/chat", json=payload) as resp:
            resp.raise_for_status()
            # First byte arrives when streaming starts — for ainvoke this = full graph time
            first_chunk = None
            chunks = []
            async for chunk in resp.aiter_bytes():
                if first_chunk is None:
                    first_chunk = time.monotonic() - t0
                chunks.append(chunk)
            body = b"".join(chunks).decode("utf-8", errors="replace")
            headers = dict(resp.headers)
    ttfb = first_chunk or (time.monotonic() - t0)
    return ttfb, body, headers


def h(headers: dict, key: str) -> str:
    return headers.get(key.lower(), "")


# ── Scenario definitions ──────────────────────────────────────────────────────

@dataclass
class Scenario:
    name: str
    label: str           # short label for table
    language: str        # "en" | "ar"
    turn_type: str       # conceptual category
    message: str
    context_setup: list[str] = field(default_factory=list)  # prior messages (same session)
    expected_path_contains: list[str] = field(default_factory=list)
    note: str = ""


SCENARIOS: list[Scenario] = [
    # ── English paths ─────────────────────────────────────────────────────────
    Scenario(
        name="EN — general_chat (freeflow, no skill)",
        label="EN general_chat",
        language="en",
        turn_type="freeflow",
        message="I've been feeling a bit off lately, not sure what's going on.",
        expected_path_contains=["safety_check", "intent_route", "freeflow_respond", "output_gate"],
        note="Expects general_chat intent → no skill activation → freeflow path",
    ),
    Scenario(
        name="EN — new_skill (skill select + execute)",
        label="EN new_skill",
        language="en",
        turn_type="skill_entry",
        message="I've been having panic attacks — my heart races and I can't breathe.",
        expected_path_contains=["safety_check", "intent_route", "skill_select", "skill_executor"],
        note="Specific somatic symptoms → new_skill → grounding or box_breathing likely",
    ),
    Scenario(
        name="EN — skill_continuation (warm turn, no skill_select)",
        label="EN skill_cont",
        language="en",
        turn_type="skill_continuation",
        message="I can feel my feet on the floor.",
        context_setup=["I've been having panic attacks, my heart is racing right now."],
        expected_path_contains=["skill_executor"],
        note="T2 in skill session — should bypass skill_select and go direct to executor",
    ),
    Scenario(
        name="EN — info_request (knowledge retrieve path)",
        label="EN info_request",
        language="en",
        turn_type="knowledge_retrieve",
        message="What is CBT and how does it work for anxiety?",
        expected_path_contains=["knowledge_retrieve", "freeflow_respond"],
        note="info_request → skill_select early-return → knowledge_retrieve → freeflow",
    ),
    Scenario(
        name="EN — crisis (safety_check → crisis_response, no LLM response)",
        label="EN crisis",
        language="en",
        turn_type="crisis",
        message="I don't want to live anymore. I've been thinking about ending my life.",
        expected_path_contains=["safety_check", "crisis_response"],
        note="Fastest path: rules-based crisis_response only, no LLM response generation",
    ),
    Scenario(
        name="EN — scope_refusal (output_gate, no LLM)",
        label="EN scope_refusal",
        language="en",
        turn_type="scope_refusal",
        message="Can you diagnose me with depression and prescribe antidepressants?",
        expected_path_contains=["output_gate"],
        note="scope_refusal → output_gate only, deterministic response",
    ),
    Scenario(
        name="EN — low_confidence (clarification request)",
        label="EN low_conf",
        language="en",
        turn_type="low_confidence",
        message="uhmm",
        expected_path_contains=["low_confidence_respond"],
        note="Single-word ambiguous input → low confidence → clarification",
    ),
    Scenario(
        name="EN — post_crisis monitoring turn (S7 fires)",
        label="EN post_crisis",
        language="en",
        turn_type="post_crisis",
        message="I feel a little better now, thank you.",
        context_setup=["I want to hurt myself. I can't take it anymore."],
        expected_path_contains=["safety_check", "skill_select", "skill_executor"],
        note="T2 after crisis: S7 fires in safety_check + post_crisis_check_in auto-select",
    ),
    # ── Arabic paths ──────────────────────────────────────────────────────────
    Scenario(
        name="AR — general_chat (freeflow + translate in + translate out)",
        label="AR general_chat",
        language="ar",
        turn_type="freeflow",
        message="أنا حاسس بضغط من الشغل",  # "I feel pressure from work"
        expected_path_contains=["safety_check", "intent_route", "freeflow_respond", "output_gate"],
        note="+1 LLM call vs EN: async_translate_to_english (in) + async_translate_to_arabic (out)",
    ),
    Scenario(
        name="AR — new_skill (translate + skill activate)",
        label="AR new_skill",
        language="ar",
        turn_type="skill_entry",
        message="قلبي يدق بسرعة وما أقدر أتنفس بشكل صحيح",  # "My heart is racing and I can't breathe right"
        expected_path_contains=["safety_check", "skill_select", "skill_executor"],
        note="Arabic somatic symptoms → skill activation → output translated to Khaleeji",
    ),
    Scenario(
        name="AR — crisis (translate in + rules-based response in AR)",
        label="AR crisis",
        language="ar",
        turn_type="crisis",
        message="أبي أموت، ما أقدر أكمل",  # "I want to die, I can't continue"
        expected_path_contains=["safety_check", "crisis_response"],
        note="Arabic crisis: translate in → S1/S3 detect → crisis_response in Arabic (CC-AR-001)",
    ),
    Scenario(
        name="AR — code-switching (EN+AR mixed)",
        label="AR code-switch",
        language="ar",
        turn_type="freeflow",
        message="I'm really تعبان these days, لا أعرف what to do",  # mixed EN/AR
        expected_path_contains=["safety_check"],
        note="Mixed EN+AR → code_switching=True → CU-CS-001 fires → mirror bilingual register",
    ),
]


# ── Per-scenario runner ───────────────────────────────────────────────────────

@dataclass
class RunResult:
    ttfb: float
    path: list[str]
    intent: str
    skill_id: str
    crisis_state: str
    is_crisis: bool
    error: str = ""


async def run_scenario(
    scenario: Scenario,
    run_index: int,
    url: str,
) -> RunResult:
    session_id = f"bench-{scenario.label[:12].replace(' ', '-')}-{_RUN_ID}-r{run_index}"

    # Set up context turns (not timed)
    for ctx_msg in scenario.context_setup:
        try:
            await chat(ctx_msg, session_id, url)
        except Exception:
            pass  # context failures don't invalidate timing turn

    try:
        ttfb, body, headers = await chat(scenario.message, session_id, url)
        path = json.loads(h(headers, "x-sage-node-path") or "[]")
        return RunResult(
            ttfb=ttfb,
            path=path,
            intent=h(headers, "x-sage-intent"),
            skill_id=h(headers, "x-sage-skill-id"),
            crisis_state=h(headers, "x-sage-crisis-state"),
            is_crisis="[[CRISIS" in body,
        )
    except Exception as exc:
        return RunResult(
            ttfb=0.0, path=[], intent="", skill_id="", crisis_state="", is_crisis=False,
            error=str(exc),
        )


# ── Stats ─────────────────────────────────────────────────────────────────────

def stats(values: list[float]) -> dict:
    if not values:
        return {}
    s = sorted(values)
    return {
        "mean":  round(statistics.mean(s), 2),
        "p50":   round(s[len(s) // 2], 2),
        "p95":   round(s[min(int(len(s) * 0.95), len(s) - 1)], 2),
        "min":   round(s[0], 2),
        "max":   round(s[-1], 2),
        "stdev": round(statistics.stdev(s), 2) if len(s) > 1 else 0.0,
    }


# ── Report writer ─────────────────────────────────────────────────────────────

def write_report(
    results: dict[str, list[RunResult]],
    n_runs: int,
    url: str,
    output_path: Path,
) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Latency Benchmark — SageAI POC",
        "",
        f"**Date:** {now}  ",
        f"**Server:** {url}  ",
        f"**Runs per scenario:** {n_runs}  ",
        f"**Measurement:** TTFB = time from POST to first response byte (= total ainvoke time)  ",
        "**Note:** Streaming is word-by-word drip removed in 2026-05-28; TTFB ≈ total response time.",
        "",
        "---",
        "",
        "## Summary Table",
        "",
        "| Scenario | Lang | Mean | p50 | p95 | Min | Max | Stdev | Errors |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    scenario_stats: dict[str, dict] = {}
    for scenario in SCENARIOS:
        name = scenario.name
        run_results = results.get(name, [])
        good = [r for r in run_results if not r.error and r.ttfb > 0]
        errors = len(run_results) - len(good)
        if not good:
            scenario_stats[name] = {}
            lines.append(f"| {scenario.label} | {scenario.language.upper()} | — | — | — | — | — | — | {errors}/{n_runs} |")
            continue
        s = stats([r.ttfb for r in good])
        scenario_stats[name] = s
        lines.append(
            f"| {scenario.label} | {scenario.language.upper()} "
            f"| {s['mean']}s | {s['p50']}s | {s['p95']}s "
            f"| {s['min']}s | {s['max']}s | {s['stdev']}s "
            f"| {errors}/{n_runs} |"
        )

    lines += [
        "",
        "---",
        "",
        "## English vs Arabic Overhead",
        "",
    ]

    en_ff = scenario_stats.get("EN — general_chat (freeflow, no skill)", {})
    ar_ff = scenario_stats.get("AR — general_chat (freeflow + translate in + translate out)", {})
    if en_ff and ar_ff:
        overhead_mean = round(ar_ff.get("mean", 0) - en_ff.get("mean", 0), 2)
        overhead_p95 = round(ar_ff.get("p95", 0) - en_ff.get("p95", 0), 2)
        lines += [
            f"Arabic adds two LLM translation calls (async_translate_to_english + async_translate_to_arabic).",
            f"",
            f"| | EN freeflow | AR freeflow | AR overhead |",
            f"|---|---|---|---|",
            f"| Mean | {en_ff.get('mean', '—')}s | {ar_ff.get('mean', '—')}s | +{overhead_mean}s |",
            f"| p95 | {en_ff.get('p95', '—')}s | {ar_ff.get('p95', '—')}s | +{overhead_p95}s |",
        ]

    lines += ["", "---", "", "## Per-scenario Detail", ""]

    for scenario in SCENARIOS:
        name = scenario.name
        run_results = results.get(name, [])
        lines.append(f"### {name}")
        lines.append(f"_{scenario.note}_")
        lines.append(f"- Message: `{scenario.message[:80]}`")
        if scenario.context_setup:
            lines.append(f"- Context setup turns: {len(scenario.context_setup)}")
        lines.append("")

        good = [r for r in run_results if not r.error]
        if not good:
            lines.append("**No valid results — all runs errored.**")
            for r in run_results:
                lines.append(f"- Error: {r.error}")
            lines.append("")
            continue

        s = scenario_stats.get(name, {})
        lines.append(f"**Stats:** mean={s.get('mean','—')}s p50={s.get('p50','—')}s p95={s.get('p95','—')}s min={s.get('min','—')}s max={s.get('max','—')}s")
        lines.append("")
        lines.append("| Run | TTFB | Path | Intent | Skill |")
        lines.append("|---|---|---|---|---|")
        for i, r in enumerate(run_results):
            if r.error:
                lines.append(f"| {i+1} | ERROR | — | — | {r.error[:40]} |")
            else:
                short_path = "→".join(p[:6] for p in r.path)
                lines.append(
                    f"| {i+1} | {r.ttfb:.2f}s "
                    f"| `{short_path}` "
                    f"| {r.intent} "
                    f"| {r.skill_id or '—'} |"
                )
        lines.append("")

    lines += [
        "---",
        "",
        "## Known Latency Drivers",
        "",
        "| Driver | Scope | Estimated cost |",
        "|---|---|---|",
        "| LLM response (intent_route) | Every turn | 400–800ms (gpt-4o-mini) |",
        "| LLM response (freeflow_respond) | Non-crisis turns | 1–3s (gpt-4o) |",
        "| S3 BGE-M3 semantic check | Every turn | 200–500ms (warm model) |",
        "| async_translate_to_english | Arabic input | ~800ms (gpt-4o-mini) |",
        "| async_translate_to_arabic | Arabic output | ~800ms (gpt-4o-mini) |",
        "| LangGraph AsyncPostgresSaver | Every turn (with DATABASE_URL) | 400–800ms |",
        "| Session summary (turn % 10) | Turn 10, 20, 30... | +500ms–1.5s |",
        "| LLM criteria eval (4 skills only) | Certain skill steps | +400ms |",
        "| LLM resistance scoring | Skill turns with resistance rules | +400ms |",
        "| Prior context pgvector retrieval | Every turn with user_id | ~100–300ms |",
        "",
        "**Option B (real streaming):** Replacing `graph.ainvoke()` with `graph.astream(stream_mode=['messages','values'])` ",
        "would surface first LLM tokens as generated, reducing TTFB to ~400ms (first intent_route token). ",
        "This is the only path to the v7 KPI of <3s p95. Deferred post-POC.",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written → {output_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main(n_runs: int, url: str) -> None:
    print(f"SageAI Latency Benchmark — {n_runs} run(s) per scenario")
    print(f"Server: {url}")
    print(f"Run ID: {_RUN_ID}")
    print()

    # Connectivity check
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{url}/health/schema-conformance")
            r.raise_for_status()
        print("Server reachable ✓\n")
    except Exception as exc:
        print(f"Server not reachable at {url}: {exc}")
        print("Start the server first: uv run python run.py")
        sys.exit(1)

    results: dict[str, list[RunResult]] = {}

    for scenario in SCENARIOS:
        print(f"{'─'*60}")
        print(f"{scenario.name}")
        run_results: list[RunResult] = []
        for i in range(n_runs):
            print(f"  Run {i+1}/{n_runs}...", end=" ", flush=True)
            r = await run_scenario(scenario, i, url)
            run_results.append(r)
            if r.error:
                print(f"ERROR: {r.error[:60]}")
            else:
                path_short = "→".join(r.path)
                print(f"{r.ttfb:.2f}s  [{path_short}]")
        results[scenario.name] = run_results

        good = [r.ttfb for r in run_results if not r.error]
        if good:
            s = stats(good)
            print(f"  → mean={s['mean']}s  p95={s['p95']}s  min={s['min']}s  max={s['max']}s")

    # Write report
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_path = (
        Path(__file__).parent.parent
        / "docs" / "superpowers" / "audits"
        / f"{date_str}-latency-benchmark.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_report(results, n_runs, url, output_path)

    # Print summary to stdout
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"{'Scenario':<35} {'Mean':>7} {'p95':>7} {'Min':>7} {'Max':>7}")
    print(f"{'─'*35} {'─'*7} {'─'*7} {'─'*7} {'─'*7}")
    for scenario in SCENARIOS:
        run_results = results.get(scenario.name, [])
        good = [r.ttfb for r in run_results if not r.error]
        if good:
            s = stats(good)
            print(
                f"{scenario.label:<35} "
                f"{s['mean']:>6.2f}s "
                f"{s['p95']:>6.2f}s "
                f"{s['min']:>6.2f}s "
                f"{s['max']:>6.2f}s"
            )
        else:
            print(f"{scenario.label:<35} {'ERROR':>7}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SageAI latency benchmark")
    parser.add_argument("--runs", type=int, default=5, help="Runs per scenario (default: 5)")
    parser.add_argument("--url", default=BASE_URL, help=f"Server URL (default: {BASE_URL})")
    args = parser.parse_args()
    asyncio.run(main(args.runs, args.url))
