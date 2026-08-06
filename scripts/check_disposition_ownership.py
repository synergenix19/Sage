#!/usr/bin/env python3
"""THIRD refusal-property: sign-off prep refuses un-reconciled disposition overlap.

Two parallel sessions (2026-07-28) built CF-010 (derealization->referral) and panic_override
(derealization->ground) against the same doc section, each clinician-signed, neither aware of the other —
a live safety conflict caught only at the flip line. This check makes that class impossible to merge
unremarked: it extracts each safety mechanism's REAL match patterns and fails if any two mechanisms whose
dispositions DIFFER share an overlapping pattern (one is a substring of the other -> some utterance matches
both) that is not declared in docs/superpowers/governance/disposition_ownership.json (resolved_overlaps or
pending_conflicts). Same shape as check_state_channels / the conformance flag-parity guard.

Exit 0 = every cross-disposition overlap is declared. Exit 1 = an UNDECLARED overlap (reconcile + declare).
"""
import json
import os
import sys
import itertools

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(REPO, "docs/superpowers/governance/disposition_ownership.json")
_SAFETY_DIR = os.path.join(REPO, "src/sage_poc/rules/data/safety")


def _patterns_from_source(source: str) -> list[str]:
    """Extract the real match patterns for a mechanism's declared source."""
    if source.startswith("nodes/") or source.endswith(".py") or ".py:" in source:
        mod_path, sym = source.split(":")
        modname = "sage_poc." + mod_path[len("src/sage_poc/"):].replace("/", ".").removesuffix(".py") \
            if mod_path.startswith("src/") else "sage_poc.nodes." + os.path.basename(mod_path).removesuffix(".py")
        modname = modname.replace("nodes.nodes.", "nodes.")
        mod = __import__(modname, fromlist=[sym])
        return [str(x).lower() for x in getattr(mod, sym)]
    # a clinical-flag JSON, optionally filtered by flag_id
    fname, _, filt = source.partition(":")
    path = os.path.join(_SAFETY_DIR, os.path.basename(fname))
    data = json.load(open(path, encoding="utf-8"))
    rules = data.get("rules", data if isinstance(data, list) else [])
    want_flag = filt.split("=", 1)[1] if filt.startswith("flag_id=") else None
    out = []
    for r in rules:
        if not r.get("patterns"):
            continue
        if want_flag and (r.get("action") or {}).get("flag_id") != want_flag:
            continue
        out.extend(p.lower() for p in r["patterns"])
    return out


def _overlap(pats_a: list[str], pats_b: list[str]) -> list[str]:
    """Shared match witnesses: a pattern of one is a substring of a pattern of the other (so an utterance
    matching the longer also matches the shorter). Returns the shorter (the shared trigger)."""
    shared = set()
    for a in pats_a:
        for b in pats_b:
            if a and b and (a in b or b in a):
                shared.add(a if len(a) <= len(b) else b)
    return sorted(shared)


def _declared_pairs(reg: dict) -> set[frozenset]:
    pairs = set()
    for entry in reg.get("resolved_overlaps", []) + reg.get("pending_conflicts", []):
        pairs.add(frozenset((entry["a"], entry["b"])))
    return pairs


def main() -> int:
    reg = json.load(open(REGISTRY, encoding="utf-8"))
    mechs = reg["mechanisms"]
    declared = _declared_pairs(reg)
    pats = {}
    for m in mechs:
        try:
            pats[m["id"]] = _patterns_from_source(m["source"])
        except Exception as e:
            print(f"❌ disposition-ownership: cannot read patterns for '{m['id']}' ({m['source']}): {e}")
            return 1
    disp = {m["id"]: m["disposition"] for m in mechs}

    undeclared, pending = [], []
    for a, b in itertools.combinations(sorted(pats), 2):
        if disp[a] == disp[b]:
            continue  # same disposition -> no conflict
        shared = _overlap(pats[a], pats[b])
        if not shared:
            continue
        if frozenset((a, b)) not in declared:
            undeclared.append((a, b, disp[a], disp[b], shared))
        elif any(frozenset((a, b)) == frozenset((e["a"], e["b"])) for e in reg.get("pending_conflicts", [])):
            pending.append((a, b, shared))

    for a, b, sh in pending:
        print(f"⚠️  disposition overlap DECLARED-PENDING: {a} vs {b} share {sh} — tracked in pending_conflicts (reconcile).")
    if undeclared:
        print("❌ UNDECLARED cross-disposition overlap(s) — a colliding safety mechanism must be reconciled + "
              "declared in disposition_ownership.json before merge:")
        for a, b, da, db, sh in undeclared:
            print(f"    {a} ({da})  ⨯  {b} ({db})  share: {sh}")
        return 1
    print(f"✅ disposition-ownership: {len(pats)} mechanisms, all cross-disposition overlaps declared "
          f"({len(pending)} pending, {len(reg.get('resolved_overlaps', []))} resolved).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
