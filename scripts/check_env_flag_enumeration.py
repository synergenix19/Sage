#!/usr/bin/env python3
"""Static gate: every behavior-affecting env flag read OUTSIDE config.py must be enumerated.

Incident class (3rd recurrence, "V2-off locals false-passed": V2-live register 07-08, the
§1a characterization replay, the §3a eval harness — code_review.md F10/F12): a flag read
from os.environ at call time (SKILL_ROUTING_V2, SKILL_RERANK_ENABLED, ...) is invisible to
config-module-based parity stamps, so an instrument asserts "prod parity" while silently
measuring the flag-off arm. config.py flags are import-time os.getenv reads and already
enumerable from the module; THIS gate covers the other kind.

Rule: any SAGE_*/SKILL_* name read via os.environ.get / os.environ[...] / os.getenv in
src/sage_poc (config.py excluded) MUST appear in sage_poc.env_flags.ENUMERATED_ENV_FLAGS,
and every enumerated name must still be read somewhere (no stale enumeration). Parity
stamps call sage_poc.env_flags.effective_env_flags(), which delegates to the LIVE readers
(_v2_enabled() etc.) — effective values, never module constants.

Exit 1 (naming the gap) on any violation. Run in CI (unit-gate) and by hand.
"""
import ast
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
SRC = REPO / "src" / "sage_poc"
_PREFIX = re.compile(r"^(SAGE_|SKILL_)")
_EXCLUDE = {
    "config.py",     # import-time os.getenv config flags: enumerable from the module itself
    "env_flags.py",  # the enumerator itself — counting its own reads would defeat stale-detection
}


def scanned_env_names() -> dict[str, set[str]]:
    names: dict[str, set[str]] = {}

    def record(name: str, where: str) -> None:
        if _PREFIX.match(name):
            names.setdefault(name, set()).add(where)

    for f in sorted(SRC.rglob("*.py")):
        if f.name in _EXCLUDE:
            continue
        rel = str(f.relative_to(SRC))
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            # os.environ.get("NAME", ...) / os.environ.setdefault("NAME", ...)
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ("get", "setdefault")
                    and isinstance(node.func.value, ast.Attribute)
                    and node.func.value.attr == "environ"
                    and node.args and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                record(node.args[0].value, rel)
            # os.getenv("NAME", ...)
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "getenv"
                    and node.args and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                record(node.args[0].value, rel)
            # os.environ["NAME"]
            if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
                    and node.value.attr == "environ"
                    and isinstance(node.slice, ast.Constant)
                    and isinstance(node.slice.value, str)):
                record(node.slice.value, rel)
    return names


def main() -> int:
    found = scanned_env_names()
    try:
        sys.path.insert(0, str(REPO / "src"))
        from sage_poc.env_flags import ENUMERATED_ENV_FLAGS  # noqa: PLC0415
    except ImportError as exc:
        print(f"FAIL: sage_poc.env_flags is missing or broken ({exc}).")
        print("Every env flag read outside config.py must be enumerated there:")
        for name, where in sorted(found.items()):
            print(f"  - {name}: read in {sorted(where)}")
        return 1

    missing = sorted(n for n in found if n not in ENUMERATED_ENV_FLAGS)
    stale = sorted(n for n in ENUMERATED_ENV_FLAGS if n not in found)
    if missing:
        print("FAIL: env flags read in src/ but ABSENT from env_flags.ENUMERATED_ENV_FLAGS "
              "(a parity stamp cannot see these — the V2-off false-pass class):")
        for n in missing:
            print(f"  - {n}: read in {sorted(found[n])}")
    if stale:
        print("FAIL: enumerated env flags no longer read anywhere (stale enumeration — the "
              "stamp would report a dead flag as live):")
        for n in stale:
            print(f"  - {n}")
    if missing or stale:
        print("\nFix sage_poc/env_flags.py (delegating to the LIVE reader, never a copied "
              "expression or module constant).")
        return 1
    print(f"OK: all {len(found)} env-read flags outside config.py are enumerated, none stale.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
