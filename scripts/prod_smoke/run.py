#!/usr/bin/env python3
"""Prod smoke suite runner — post-deploy health gate for SageAI.

Runs one or more "tiers" of read-only checks against a live deployment and
prints a one-screen summary. Exits 1 if any must-pass check FAILed; exits 0
otherwise — report-only (must_pass=False) FAILs and any XFAIL never flip the
exit code.

Usage:
    SAGE_API_KEY=... python scripts/prod_smoke/run.py [--tier a|b|c|all] [--base-url URL]

Tiers:
    a  — safety invariants: crisis resources (EN/AR), GL-1 helpline XFAIL,
         MM entry-screen derealization hold, precedence audit proxy (Task 2)
    b  — Playwright feature card-render checks (report-only; needs SAGE_SMOKE_STORAGE_STATE
         auth; validated live vs prod 2026-07-07). See docs/runbooks/prod-smoke.md.
    c  — flag readback + response-header regression (Task 1 slice, wired)
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tier_a_safety
import tier_b_features
import tier_c_regression
from result import CheckResult

DEFAULT_BASE_URL = "https://sage-api-production-3328.up.railway.app"

# Every tier function has the same signature: (base_url: str) -> list[CheckResult].
# Referenced by name (not captured into a local) so tests can monkeypatch this
# dict to stub tiers without touching the network.
TIER_FUNCS = {
    "a": tier_a_safety.run,
    "b": tier_b_features.run_all,
    "c": tier_c_regression.flag_readback,
}

WIDTH = 78


def _resolve_base_url(cli_value):
    if cli_value:
        return cli_value
    return os.environ.get("SAGE_SMOKE_BASE_URL", DEFAULT_BASE_URL)


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="SageAI prod smoke suite")
    parser.add_argument("--tier", choices=["a", "b", "c", "all"], default="all")
    parser.add_argument(
        "--base-url", default=None,
        help="Overrides SAGE_SMOKE_BASE_URL / the built-in production default",
    )
    return parser.parse_args(argv)


def run(tiers, base_url) -> list:
    results: list[CheckResult] = []
    for tier in tiers:
        results.extend(TIER_FUNCS[tier](base_url))
    return results


def _print_summary(results, base_url) -> None:
    print(f"\n{'=' * WIDTH}")
    print("  SageAI Prod Smoke Suite")
    print(f"  URL: {base_url}")
    print(f"{'=' * WIDTH}")
    for r in results:
        must = "must-pass" if r.must_pass else "report-only"
        print(f"  {r.status:<5}  [{r.tier}]  {r.name:<45}  ({must})  {r.detail}")

    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    xfailed = sum(1 for r in results if r.status == "XFAIL")
    print(f"{'-' * WIDTH}")
    print(f"  {len(results)} checks — pass={passed} fail={failed} xfail={xfailed}")
    print(f"{'=' * WIDTH}\n")


def main(argv=None) -> None:
    args = _parse_args(argv)
    base_url = _resolve_base_url(args.base_url)
    tiers = ["a", "b", "c"] if args.tier == "all" else [args.tier]

    results = run(tiers, base_url)
    _print_summary(results, base_url)

    must_pass_failed = any(r.status == "FAIL" and r.must_pass for r in results)
    sys.exit(1 if must_pass_failed else 0)


if __name__ == "__main__":
    main()
