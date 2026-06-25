#!/usr/bin/env python3
"""Latency baseline harness for the latency campaign (WARMUP → EMBED-CACHE → ...).

Captures the BEFORE-optimization numbers the campaign is evaluated against. Two test shapes,
because they measure different things:

  * single-user (cold/warm × EN/AR) — per-turn stage costs; cheap half.
  * concurrency  — the ONLY shape where ① (checkpointer pool max_size) shows. A thin/sequential
    run scores the pool fix as a no-op. This driver fires N concurrent turns with DISTINCT
    sessions to contend the checkpointer pool past its old cap of 4 — set --concurrency well
    above 4 and run it against the PROD-SHAPED pool settings (6543 transaction URL, replica
    count, SAGE_*_POOL_MAX_SIZE) or the numbers won't transfer.

TRUSTWORTHY RUN PRECONDITION (operator): point at the prod-shaped deployment with
CHECKPOINT_DATABASE_URL=6543, AINVOKE_TIMEOUT_SECONDS=55, and the real replica count set. A
dev run (5432 / 30s) will mislead. COLD is only meaningful on the FIRST call after a restart.

Every session_id is `latbase-<run>-<scenario>-<i>`; grep the server logs for that run tag to
join the per-stage `{"event":"stage_latency",...}` lines to these end-to-end numbers, and to
slice cold/warm/EN/AR by scenario.

Usage:
  SAGE_API_URL=https://sage-api-staging.up.railway.app SAGE_API_KEY=... \
      uv run python scripts/latency_baseline.py --concurrency 16 --warm-iters 8
"""
from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import time
import uuid

import httpx

EN_MSG = "I've been feeling really overwhelmed at work lately and I can't switch off at night."
# Non-crisis Arabic general_chat — exercises translate-in + translate-out + freeflow (the
# expensive path), not the crisis short-circuit.
AR_MSG = "أشعر بضغط كبير في العمل هذه الأيام ولا أستطيع التوقف عن التفكير في الليل."


async def _one_call(
    client: httpx.AsyncClient, base_url: str, api_key: str | None,
    session_id: str, user_id: str | None, message: str,
) -> dict:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-Sage-Api-Key"] = api_key
    body = {
        "messages": [{"role": "user", "content": message}],
        "session_id": session_id,
    }
    if user_id:
        body["user_id"] = user_id
    start = time.monotonic()
    try:
        # Read the full body so latency reflects whole-turn wall-clock (the backend buffers
        # the graph before the body flushes — see the streaming analysis).
        resp = await client.post(f"{base_url}/chat", json=body, headers=headers)
        text = resp.text
        elapsed = time.monotonic() - start
        return {
            "session_id": session_id, "ok": resp.status_code == 200,
            "status": resp.status_code, "latency_s": elapsed,
            "node_path": resp.headers.get("X-Sage-Node-Path", ""),
            "n_chars": len(text),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "session_id": session_id, "ok": False, "status": None,
            "latency_s": time.monotonic() - start, "error": repr(exc), "n_chars": 0,
        }


def _pct(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    idx = min(len(s) - 1, int(round((p / 100) * (len(s) - 1))))
    return s[idx]


def _summarize(name: str, results: list[dict]) -> None:
    lat = [r["latency_s"] for r in results if r.get("ok")]
    errs = [r for r in results if not r.get("ok")]
    print(f"\n## {name}  (n={len(results)}, ok={len(lat)}, err={len(errs)})")
    if lat:
        print(
            f"   p50={_pct(lat,50):.2f}s  p95={_pct(lat,95):.2f}s  "
            f"max={max(lat):.2f}s  min={min(lat):.2f}s  mean={statistics.mean(lat):.2f}s"
        )
    if errs:
        shown = errs[0].get("error") or f"HTTP {errs[0].get('status')}"
        print(f"   ERRORS: {len(errs)} (first: {shown})")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.environ.get("SAGE_API_URL", "http://localhost:8000"))
    ap.add_argument("--api-key", default=os.environ.get("SAGE_API_KEY"))
    ap.add_argument("--user-id", default=os.environ.get("SAGE_BASELINE_USER_ID"),
                    help="optional; enables profile load + write-tool path")
    ap.add_argument("--warm-iters", type=int, default=8, help="sequential single-user samples per lang")
    ap.add_argument("--concurrency", type=int, default=16, help="must exceed old pool cap (4) to contend ①")
    ap.add_argument("--timeout", type=float, default=90.0)
    args = ap.parse_args()

    run = uuid.uuid4().hex[:8]
    base = args.base_url.rstrip("/")
    print(f"# latency baseline  run={run}  base={base}  concurrency={args.concurrency}  warm-iters={args.warm_iters}")
    print(f"# JOIN: grep server logs for 'latbase-{run}-' to attach per-stage stage_latency lines.")
    if args.concurrency <= 4:
        print("# WARNING: --concurrency <= 4 will NOT contend the checkpointer pool; ① will score as a no-op.")

    limits = httpx.Limits(max_connections=args.concurrency + 4)
    async with httpx.AsyncClient(timeout=args.timeout, limits=limits) as client:
        # 0) warm the server (BGE-M3 + TCP) so 'warm' scenarios aren't polluted by first-call cost.
        await _one_call(client, base, args.api_key, f"latbase-{run}-warmup-0", args.user_id, EN_MSG)

        # 1) COLD — only meaningful immediately after a server restart. One sample, labelled.
        cold = [await _one_call(client, base, args.api_key, f"latbase-{run}-cold-0", args.user_id, EN_MSG)]
        _summarize("single-user COLD EN (valid only if first call post-restart)", cold)

        # 2) WARM single-user EN — sequential, distinct sessions (isolate per-turn cost).
        warm_en = []
        for i in range(args.warm_iters):
            warm_en.append(await _one_call(client, base, args.api_key, f"latbase-{run}-warmEN-{i}", args.user_id, EN_MSG))
        _summarize("single-user WARM EN", warm_en)

        # 3) WARM single-user AR — pays translate-in + translate-out + gate translate.
        warm_ar = []
        for i in range(args.warm_iters):
            warm_ar.append(await _one_call(client, base, args.api_key, f"latbase-{run}-warmAR-{i}", args.user_id, AR_MSG))
        _summarize("single-user WARM AR", warm_ar)

        # 4) CONCURRENCY — the ① evidence. Fire C turns at once, distinct sessions, to contend
        #    the checkpointer pool. Run against prod-shaped pool settings for a real result.
        conc = await asyncio.gather(*[
            _one_call(client, base, args.api_key, f"latbase-{run}-conc-{i}", args.user_id, EN_MSG)
            for i in range(args.concurrency)
        ])
        _summarize(f"CONCURRENCY EN x{args.concurrency} (contends checkpointer pool)", list(conc))

    print(f"\n# done. run={run}")


if __name__ == "__main__":
    asyncio.run(main())
