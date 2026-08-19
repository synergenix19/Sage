#!/usr/bin/env python3
"""Mechanical register-coverage check: the register surface is DERIVED from what the serving
process actually reads, never hand-maintained.

Why (2026-07-30): the completeness gate in tests/test_prod_flags_register.py enumerated only
SAGE_*-prefixed reads in config.py. SKILL_ROUTING_V2 / SKILL_RERANK_ENABLED / SKILL_RERANK_PRECISION
(read in skill_select.py, no SAGE_ prefix) therefore sat outside the register, the watchdog, the
readback AND the conformance runner's parity check for 22 days after their sanctioned 2026-07-08
flip — the K3/K4 local-vs-prod divergence hid in exactly that blind spot. Hand-maintained scope
lists rot; this scan is the fix.

Contract (CI-enforced by tests/test_env_register_coverage.py):
  * every env NAME the serving source reads (src/ + server.py; os.getenv / os.environ.get /
    os.environ["..."]) is EITHER a `flags:` row OR an `infra_allowlist:` entry with a reason;
  * never both (the dichotomy is exclusive);
  * no stale allowlist entries (a name nothing reads anymore must leave the file).
Exclusions are as governed as rows: adding an allowlist entry is a PR-reviewable decision.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER_PATH = os.path.join(REPO, "config", "prod_flags.yaml")

# One pattern per read idiom; a literal-name read is the unit of coverage. Dynamic reads
# (variable names) cannot be enumerated and must not be introduced for behavior flags.
# The _strict_flag(...) pattern covers config.py's single strict-parse helper (K2.1): its
# own internal os.getenv(env_name) call is a DYNAMIC read (env_name is a parameter, not a
# literal) and would otherwise be invisible to the first three patterns, silently dropping
# every migrated flag out of coverage. KEYWORD-ORDER-FRAGILE (name-only here, so this
# pattern doesn't depend on default_on's position, but the other four SAGE_-scoped
# scanners do — see the convention comment above _strict_flag in config.py).
_READ_PATTERNS = (
    re.compile(r'os\.getenv\(\s*["\']([A-Z][A-Z0-9_]+)["\']'),
    re.compile(r'os\.environ\.get\(\s*["\']([A-Z][A-Z0-9_]+)["\']'),
    re.compile(r'os\.environ\[\s*["\']([A-Z][A-Z0-9_]+)["\']'),
    re.compile(r'_strict_flag\(\s*["\']([A-Z][A-Z0-9_]+)["\']'),
)

_SOURCE_ROOTS = ("src", "server.py")


def served_env_reads(repo: str = REPO) -> set[str]:
    """Every literal env name read anywhere in the serving source tree."""
    names: set[str] = set()
    paths: list[str] = []
    for root in _SOURCE_ROOTS:
        full = os.path.join(repo, root)
        if os.path.isfile(full):
            paths.append(full)
        else:
            for dirpath, _dirs, files in os.walk(full):
                paths.extend(os.path.join(dirpath, f) for f in files if f.endswith(".py"))
    for path in paths:
        with open(path, encoding="utf-8") as f:
            src = f.read()
        for pat in _READ_PATTERNS:
            names.update(m.group(1) for m in pat.finditer(src))
    return names


def load_register(path: str = REGISTER_PATH) -> dict:
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def coverage_violations(reg: dict, reads: set[str]) -> list[str]:
    """Empty list = the register surface exactly covers the serving read surface."""
    rows = set((reg.get("flags") or {}).keys())
    allow = reg.get("infra_allowlist") or {}
    allow_names = set(allow.keys())
    out: list[str] = []
    for name in sorted(reads - rows - allow_names):
        out.append(f"UNCOVERED: {name} is read by serving source but is neither a register row "
                   f"nor an infra_allowlist entry (classify at birth)")
    for name in sorted(rows & allow_names):
        out.append(f"BOTH: {name} is a register row AND allowlisted — the dichotomy is exclusive")
    for name in sorted(allow_names - reads):
        out.append(f"STALE ALLOWLIST: {name} is allowlisted but nothing in serving source reads it")
    for name, reason in allow.items():
        if not (isinstance(reason, str) and reason.strip()):
            out.append(f"NO REASON: allowlist entry {name} must carry a non-empty reason string")
    return out


def main() -> int:
    reads = served_env_reads()
    reg = load_register()
    violations = coverage_violations(reg, reads)
    if violations:
        print(f"register coverage FAIL ({len(violations)}):")
        for v in violations:
            print(f"  {v}")
        return 1
    rows = len(reg.get("flags") or {})
    allow = len(reg.get("infra_allowlist") or {})
    print(f"register coverage OK: {len(reads)} served env reads = {rows} rows + {allow} allowlisted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
