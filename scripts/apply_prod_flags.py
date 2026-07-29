#!/usr/bin/env python3
"""Idempotent config-as-code apply for prod SAGE_* flags (config/prod_flags.yaml).

THE ONLY SANCTIONED FLAG-CHANGE PATH:  edit config/prod_flags.yaml -> PR -> merge ->
`python scripts/apply_prod_flags.py --apply`.  Direct `railway variables` edits are
drift by definition (scripts/flag_watchdog.py alerts on them).

Why this shape (owner-imposed): all three real SAGE_INFO_REQUEST_CONSULT reversions
(2026-07-28..29, two SERVED) were VARIABLE-ONLY changes — no build was ever triggered,
so a #258-style build-side gate never saw them. Enforcement therefore lives on the
COMMITTED FILE (signed-value check, CI: tests/test_prod_flags_register.py) and on this
idempotent apply, which:

  * reads the committed register, railway DESIRED (`railway variables --kv`) and the
    prod SERVING readback (/health/version *_raw_env), and prints a THREE-WAY diff;
  * is --dry-run by DEFAULT; `--apply` converges railway desired to the committed file
    (variable sets/deletes only, batched into a single railway invocation);
  * REFUSES to apply while the committed file fails its own signed-value check
    (a signed flag off its signed_value without a ratified override block);
  * never touches a variable the register does not list (secrets, SAGE_BUILD_SHA,
    SAGE_TEST_USER_IDS are excluded from the register by design + CI).

DEPLOY/RESTART SEMANTICS (documented, deliberate): this script performs VARIABLE
OPERATIONS ONLY. It never builds, never deploys a tree, never runs deploy_prod.sh.
Railway itself redeploys/restarts the service when its variables change — that is
railway's own restart semantics, not an action this script takes; all changed
variables are batched into ONE railway invocation so at most one restart results.
Deletes use `railway variable delete` (one call per variable — the CLI has no batch
delete; each may restart per railway's semantics, so deletes are rare by design).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER_PATH = os.path.join(REPO, "config", "prod_flags.yaml")
DEFAULT_BASE_URL = "https://sage-api-production-3328.up.railway.app"
DEFAULT_SERVICE = "sage-api"


class RegisterViolation(Exception):
    """The committed register fails its own signed-value/shape check; apply must refuse."""


def load_register(path: str = REGISTER_PATH) -> dict:
    import yaml  # local import so the module stays importable without pyyaml for pure helpers
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _norm(value):
    """Normalize a register value to raw-env string form (defensive against bare YAML scalars)."""
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def register_violations(reg: dict) -> list[str]:
    """Internal-consistency check of the committed file. Empty list = clean.

    Rules (CI-enforced by tests/test_prod_flags_register.py):
      - every row carries class safety|feature;
      - signed_value requires signature_ref;
      - value != signed_value requires an override block with BOTH a rationale and a
        ratification_ref (an override without ratification_ref is itself a violation).
    """
    out: list[str] = []
    for name, row in (reg.get("flags") or {}).items():
        row = row or {}
        if row.get("class") not in ("safety", "feature"):
            out.append(f"{name}: missing/invalid class (must be safety|feature)")
        override = row.get("override")
        if override is not None:
            if not (isinstance(override, dict) and override.get("rationale")):
                out.append(f"{name}: override block without a rationale")
            if not (isinstance(override, dict) and override.get("ratification_ref")):
                out.append(f"{name}: override block without a ratification_ref")
        if "signed_value" in row:
            if not row.get("signature_ref"):
                out.append(f"{name}: signed_value without a signature_ref")
            if _norm(row.get("value")) != _norm(row.get("signed_value")) and override is None:
                out.append(
                    f"{name}: value {row.get('value')!r} != signed_value "
                    f"{row.get('signed_value')!r} with NO override block — unratified breach "
                    f"of a signed flag state"
                )
    return out


def committed_values(reg: dict) -> dict:
    """{SAGE_VAR: raw-string-or-None} — None means 'not set in railway' (config default applies)."""
    return {name: _norm((row or {}).get("value")) for name, row in (reg.get("flags") or {}).items()}


# ---------------------------------------------------------------------------------
# Sources: railway DESIRED + prod SERVING readback
# ---------------------------------------------------------------------------------

def fetch_desired(service: str = DEFAULT_SERVICE):
    """Railway's DESIRED variable set via `railway variables --kv`. None if unreachable."""
    for cmd in (["railway", "variables", "--kv", "-s", service], ["railway", "variables", "--kv"]):
        try:
            raw = subprocess.check_output(cmd, text=True, timeout=45, stderr=subprocess.DEVNULL)
        except Exception:
            continue
        out = {}
        for line in raw.splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                out[k.strip()] = v
        return out
    return None


def fetch_serving(base_url: str = DEFAULT_BASE_URL, api_key: str | None = None):
    """SERVING flag state via /health/version *_raw_env readback (authed GET; read-only).
    Returns {SAGE_VAR: raw-string-or-None} for the vars the deployed build EXPOSES, or None
    if the endpoint is unreachable. Vars absent from the map are readback coverage gaps
    (the deployed build predates the readback widening), not divergences."""
    key = api_key if api_key is not None else os.environ.get("SAGE_API_KEY", "")
    try:
        import ssl
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            ctx = ssl.create_default_context()
        req = urllib.request.Request(
            base_url.rstrip("/") + "/health/version", headers={"X-Sage-Api-Key": key})
        health = json.loads(urllib.request.urlopen(req, timeout=15, context=ctx).read())
    except Exception:
        return None
    return {
        "SAGE_" + k[: -len("_raw_env")].upper(): v
        for k, v in health.items() if k.endswith("_raw_env")
    }


# ---------------------------------------------------------------------------------
# Diff + plan
# ---------------------------------------------------------------------------------

def three_way_diff(committed: dict, desired, serving) -> list[dict]:
    """One row per registered flag: committed vs railway-desired vs serving readback."""
    rows = []
    for name in sorted(committed):
        want = committed[name]
        des = desired.get(name) if desired is not None else "(unreachable)"
        if serving is None:
            srv = "(unreachable)"
        elif name in serving:
            srv = serving[name]
        else:
            srv = "(no readback)"
        rows.append({
            "flag": name, "committed": want, "desired": des, "serving": srv,
            "desired_drift": desired is not None and (desired.get(name) or None) != want,
            "serving_drift": serving is not None and name in serving
                             and (serving[name] or None) != want,
        })
    return rows


def plan_apply(reg: dict, desired: dict) -> tuple[dict, list]:
    """Converge railway DESIRED to the committed register. Returns (sets, deletes).

    Refuses (RegisterViolation) while the register fails its own signed-value check —
    a breach of a signed flag state cannot be propagated by tooling.
    Only variables the register LISTS are ever touched; anything else in railway
    (secrets, provenance pins, unrelated vars) is out of scope by construction.
    Idempotent: a desired set already matching the file yields an empty plan.
    """
    violations = register_violations(reg)
    if violations:
        raise RegisterViolation("; ".join(violations))
    committed = committed_values(reg)
    sets, deletes = {}, []
    for name, want in committed.items():
        have = desired.get(name)
        if want is None:
            if name in desired:
                deletes.append(name)          # committed says UNSET; railway has it set
        elif have != want:
            sets[name] = want
    return sets, sorted(deletes)


def _apply(sets: dict, deletes: list, service: str) -> int:
    rc = 0
    if sets:
        cmd = ["railway", "variables", "-s", service]
        for k, v in sorted(sets.items()):
            cmd += ["--set", f"{k}={v}"]
        print(f"[apply] batching {len(sets)} variable set(s) into one railway invocation "
              f"(railway applies them with its own service restart semantics)")
        rc |= subprocess.call(cmd)
    for k in deletes:
        print(f"[apply] deleting {k} (railway restart semantics apply)")
        rc |= subprocess.call(["railway", "variable", "delete", k, "-s", service])
    return rc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True,
                      help="print the three-way diff and the would-be plan (DEFAULT)")
    mode.add_argument("--apply", action="store_true",
                      help="converge railway desired to the committed file (variable ops only)")
    ap.add_argument("--register", default=REGISTER_PATH)
    ap.add_argument("--base-url", default=os.environ.get("SAGE_SMOKE_BASE_URL", DEFAULT_BASE_URL))
    ap.add_argument("--service", default=DEFAULT_SERVICE)
    args = ap.parse_args(argv)

    reg = load_register(args.register)
    violations = register_violations(reg)
    committed = committed_values(reg)
    desired = fetch_desired(args.service)
    serving = fetch_serving(args.base_url)

    print(f"register: {args.register} ({len(committed)} flags)")
    if violations:
        print("REGISTER VIOLATIONS (apply is REFUSED until the file is fixed):")
        for v in violations:
            print(f"  !! {v}")

    rows = three_way_diff(committed, desired, serving)
    drifted = [r for r in rows if r["desired_drift"] or r["serving_drift"]]
    print(f"\n{'flag':<38} {'committed':<22} {'desired':<22} serving")
    for r in rows:
        mark = " <-- DRIFT" if r in drifted else ""
        print(f"{r['flag']:<38} {str(r['committed']):<22} {str(r['desired']):<22} "
              f"{r['serving']}{mark}")

    if not args.apply:
        if desired is not None:
            try:
                sets, deletes = plan_apply(reg, desired)
                print(f"\n[dry-run] plan: {len(sets)} set(s), {len(deletes)} delete(s): "
                      f"{sets or '{}'} {deletes or '[]'}")
            except RegisterViolation as exc:
                print(f"\n[dry-run] apply would REFUSE: {exc}")
        return 1 if (violations or drifted) else 0

    if desired is None:
        print("FATAL: railway desired unreachable — cannot apply")
        return 3
    try:
        sets, deletes = plan_apply(reg, desired)
    except RegisterViolation as exc:
        print(f"REFUSED: committed file fails the signed-value check: {exc}")
        return 2
    if not sets and not deletes:
        print("\n[apply] already converged — nothing to do (idempotent)")
        return 0
    return _apply(sets, deletes, args.service)


if __name__ == "__main__":
    sys.exit(main())
