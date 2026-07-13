#!/usr/bin/env python3
"""Signed-clinical-fields manifest check.

WHY: a clinical field (a skill semantic_description, a served referral line, the crisis helpline)
is a CLINICIAN-SIGNED artifact. The 2026-07-10 trim incident proved these can change and ship LIVE
with no forcing function to catch that the sign-off was never recorded. This makes a silent change
structurally impossible: every signed field's content hash is pinned in the manifest alongside its
sign-off reference. If a field's current value no longer matches its pinned hash, the field CHANGED
-> this check FAILS until the manifest is updated in the SAME PR with the new hash AND a sign-off
reference (or the change is reverted). It is a forcing function, not cryptographic proof: it cannot
verify a sign-off ref is real, but it makes "changed a signed clinical field" impossible to merge
without consciously citing who signed it.

Selectors:
  json:<path>:<dotpath>              e.g. json:src/sage_poc/skills/x.json:semantic_description
  pyconst:<module>:<NAME>[:<subkey>] e.g. pyconst:sage_poc.config:CRISIS_CONFIG:number

Usage:
  check_signed_fields.py            # verify tree against manifest; exit 1 on any mismatch/missing
  check_signed_fields.py --generate # print current hashes for every manifest entry (to reseed)
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_MANIFEST = _ROOT / "docs" / "superpowers" / "governance" / "signed_clinical_fields.json"


def _extract(selector: str) -> str:
    kind, rest = selector.split(":", 1)
    if kind == "json":
        path, dotpath = rest.split(":", 1)
        data = json.loads((_ROOT / path).read_text(encoding="utf-8"))
        for key in dotpath.split("."):
            data = data[int(key)] if isinstance(data, list) else data[key]
        return json.dumps(data, ensure_ascii=False, sort_keys=True)
    if kind == "pyconst":
        parts = rest.split(":")
        module, name = parts[0], parts[1]
        sys.path.insert(0, str(_ROOT / "src"))
        import importlib
        val = getattr(importlib.import_module(module), name)
        for sub in parts[2:]:
            val = val[sub]
        return json.dumps(val, ensure_ascii=False, sort_keys=True)
    raise ValueError(f"unknown selector kind: {kind!r}")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_manifest() -> list[dict]:
    return json.loads(_MANIFEST.read_text(encoding="utf-8"))["fields"]


def generate() -> int:
    for f in _load_manifest():
        try:
            print(f"{f['id']:40s} {_sha(_extract(f['selector']))}")
        except Exception as e:  # noqa: BLE001
            print(f"{f['id']:40s} ERROR: {e}")
    return 0


def verify() -> int:
    failures = []
    for f in _load_manifest():
        try:
            actual = _sha(_extract(f["selector"]))
        except Exception as e:  # noqa: BLE001
            failures.append(f"{f['id']}: extraction failed ({e}) — selector {f['selector']!r}")
            continue
        if actual != f["sha256"]:
            failures.append(
                f"{f['id']}: SIGNED FIELD CHANGED.\n"
                f"    selector : {f['selector']}\n"
                f"    signed   : {f.get('signed_by')} {f.get('signed_date')} ({f.get('signoff')})\n"
                f"    manifest sha256 : {f['sha256']}\n"
                f"    current  sha256 : {actual}\n"
                f"    -> record the new sign-off + hash in signed_clinical_fields.json (same PR), or revert."
            )
    if failures:
        print("❌ signed-clinical-fields check FAILED:\n", file=sys.stderr)
        for x in failures:
            print("  " + x + "\n", file=sys.stderr)
        return 1
    print(f"✅ signed-clinical-fields: all {len(_load_manifest())} fields match their signed hashes.")
    return 0


def files() -> int:
    # unique backing file paths (for the deploy clinical-surface diff). json:<path>:.. and
    # pyconst:<module>:.. -> resolve the module to its src path.
    out = set()
    for f in _load_manifest():
        kind, rest = f["selector"].split(":", 1)
        if kind == "json":
            out.add(rest.split(":", 1)[0])
        elif kind == "pyconst":
            out.add("src/" + rest.split(":", 1)[0].replace(".", "/") + ".py")
    for p in sorted(out):
        print(p)
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--generate" in args:
        sys.exit(generate())
    if "--files" in args:
        sys.exit(files())
    sys.exit(verify())
