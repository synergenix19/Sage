#!/usr/bin/env python3
"""Alert-first flag watchdog — one-shot committed-vs-desired-vs-serving divergence check.

Interim compensating control for the signed-flag gate (2026-07-29 ledger): three
variable-only reversions of a signed flag in 24h, two of them served, the third with an
ACTIVE contending writer. Per the command session's stand-down decision this watchdog
NEVER auto-reverts — an automated restore against an active contending writer starts a
flip-war on production. It observes, names the flag and the side that diverged, and
exits nonzero so a schedule/CI wrapper can page a human.

Usage:
    SAGE_API_KEY=... python scripts/flag_watchdog.py [--base-url URL] [--service NAME]

Exit codes:
    0  committed file, railway desired and serving readback all agree
    2  DIVERGENCE (named-flag report printed) and/or the committed file itself fails
       its signed-value check
    3  neither railway nor the serving readback was reachable — cannot check
"""
import argparse
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "apply_prod_flags", os.path.join(_HERE, "apply_prod_flags.py"))
_apply = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_apply)


def divergences(reg: dict, desired, serving) -> list[dict]:
    """Named-flag divergence rows, one per (flag, side). A flag ABSENT from the serving
    readback map is a readback coverage gap (see readback_gaps), never a divergence —
    the deployed build may simply predate the readback widening."""
    committed = _apply.committed_values(reg)
    rows = []
    for name in sorted(committed):
        want = committed[name]
        if desired is not None and (desired.get(name) or None) != want:
            rows.append({"flag": name, "side": "desired",
                         "committed": want, "observed": desired.get(name)})
        if serving is not None and name in serving and (serving[name] or None) != want:
            rows.append({"flag": name, "side": "serving",
                         "committed": want, "observed": serving[name]})
    return rows


def readback_gaps(reg: dict, serving) -> list[str]:
    """Registered flags the serving build's /health/version readback does not expose."""
    if serving is None:
        return []
    return sorted(n for n in _apply.committed_values(reg) if n not in serving)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="one-shot flag divergence watchdog (no auto-revert)")
    ap.add_argument("--register", default=_apply.REGISTER_PATH)
    ap.add_argument("--base-url",
                    default=os.environ.get("SAGE_SMOKE_BASE_URL", _apply.DEFAULT_BASE_URL))
    ap.add_argument("--service", default=_apply.DEFAULT_SERVICE)
    args = ap.parse_args(argv)

    reg = _apply.load_register(args.register)
    violations = _apply.register_violations(reg)
    desired = _apply.fetch_desired(args.service)
    serving = _apply.fetch_serving(args.base_url)

    if desired is None and serving is None:
        print("FLAG WATCHDOG: UNCHECKABLE — railway and the serving readback are both "
              "unreachable. This is not a pass.")
        return 3

    rows = divergences(reg, desired, serving)
    gaps = readback_gaps(reg, serving)
    signed = {n for n, r in (reg.get("flags") or {}).items() if "signed_value" in (r or {})}

    if violations:
        print("COMMITTED-FILE VIOLATIONS (the register itself breaches the signed state):")
        for v in violations:
            print(f"  !! {v}")
    if rows:
        print("FLAG DIVERGENCE DETECTED — the committed register is the source of truth; "
              "someone changed variables outside the sanctioned path:")
        for r in rows:
            tag = "  [SIGNED FLAG]" if r["flag"] in signed else ""
            print(f"  !! {r['flag']}: {r['side']} = {r['observed']!r}, committed = "
                  f"{r['committed']!r}{tag}")
        print("NO AUTO-REVERT (stand-down 2026-07-29): coordinate with the deploy owner / "
              "parallel-stream owner; a ratified change goes file -> PR -> merge -> apply.")
    if gaps:
        print(f"readback coverage gaps (serving build does not expose {len(gaps)} "
              f"registered flag(s) — desired-only check for these): {', '.join(gaps)}")
    if desired is None:
        print("note: railway desired unreachable — serving-only check this run.")
    if serving is None:
        print("note: serving readback unreachable — desired-only check this run.")

    if rows or violations:
        return 2
    print(f"flag watchdog: clean ({len(_apply.committed_values(reg))} flags checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
