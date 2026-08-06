"""Disposition-ownership registry — the THIRD refusal-property (un-reconciled safety overlap can't merge).

Locks in that (a) the check catches overlapping match-sets that route to different dispositions, (b) the
2026-07-28 derealization conflict stays tracked, and (c) the registry's declared mechanisms are real.
"""
import json
import os
import importlib.util

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(REPO, "docs/superpowers/governance/disposition_ownership.json")
_spec = importlib.util.spec_from_file_location(
    "check_disposition_ownership", os.path.join(REPO, "scripts/check_disposition_ownership.py"))
chk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(chk)


def test_check_passes_all_overlaps_declared():
    assert chk.main() == 0, "an undeclared cross-disposition overlap exists — reconcile + declare it"


def test_overlap_detector_catches_substring_witness():
    # the exact bug: 'unreal' (panic) is a substring of 'everything feels unreal' (CF-010)
    assert chk._overlap(["everything feels unreal"], ["unreal", "dizzy"]) == ["unreal"]
    assert chk._overlap(["nothing here"], ["totally unrelated"]) == []


def test_derealization_vs_panic_conflict_is_tracked():
    reg = json.load(open(REG, encoding="utf-8"))
    pairs = {frozenset((e["a"], e["b"])) for e in reg["pending_conflicts"]}
    assert frozenset(("derealization", "panic_ground")) in pairs, \
        "the derealization<->panic disposition conflict must stay declared until Vee reconciles"


def test_every_mechanism_source_is_readable():
    reg = json.load(open(REG, encoding="utf-8"))
    for m in reg["mechanisms"]:
        pats = chk._patterns_from_source(m["source"])
        assert pats, f"mechanism {m['id']} ({m['source']}) yielded no patterns — stale source?"
