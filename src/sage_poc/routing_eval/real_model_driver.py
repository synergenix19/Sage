"""Real-model routing driver (Track A, Increment 1) — the acceptance-gate instrument.

Spec: docs/superpowers/specs/2026-07-07-routing-eval-driver-spec.md.

WHAT THIS IS
------------
A faithful `routed_of(record) -> skill_id | ABSTAIN` that runs the LIVE tier pipeline
(Tier-1 keyword match -> Tier-2 bi-encoder max-over-anchors -> live `_route_decision`)
over each fixture utterance, and feeds it to the EXISTING scorer
`gate_runner.compute_metrics_by_stratum`. Flags-OFF (SKILL_ROUTING_V2=0,
SKILL_RERANK_ENABLED=0) == V1.

ONE SCORING SOURCE OF TRUTH (this module does NOT score)
--------------------------------------------------------
Every scoring rule stays in `sage_poc/routing_eval/gate_runner.py` — cited, never
reimplemented here:
  * routing-quality row filter ....... gate_runner.py:48-49
      (held_out and not flag_bearing and case_kind not in _PATH_ASSERTION_KINDS)
  * blended/comorbid correctness ..... gate_runner.py:52-55  (acceptable_routes else expected_route)
  * recall / abstain denominators .... gate_runner.py:57-59  (non-blended single-answer cases)
  * per-stratum grouping ............. gate_runner.py:82-94  (grouped by (lang, stratum))
  * harm gate ........................ gate_runner.py:107-120
The driver only supplies `routed_of`; the recall/abstain %s come out of
`compute_metrics_by_stratum`. The denominators printed for readability are recomputed
from the SAME cell filter (held_out and not flag_bearing) for display only; the rates
are the scorer's.

FAITHFUL `routed_of` — mirrors nodes/skill_select.py exactly (flags-off branch)
------------------------------------------------------------------------------
  1. Tier 1: `match_skill_keywords(utterance, "", "en")` (skill_select.py:728) then the
     C1 dbt_tipp/grounding tiebreak (skill_select.py:751-756). A keyword match routes to
     the primary candidate. (Comparator note: "Tier-1 keyword caught 0" on these fixtures.)
  2. Pre-Tier-2 exclusion guard: `_SEMANTIC_EXCLUSION_RE` (skill_select.py:774) -> ABSTAIN.
  3. Tier 2: live `_semantic_match_sync` (skill_select.py:413) — max-over-anchors +
     live `_route_decision` (skill_select.py:302). None -> ABSTAIN, else the skill_id.
The routing DECISION functions are reused, never re-derived.

SURFACE CONFOUND — #139 (spec §3, DECIDED)
------------------------------------------
The frozen 66/35/100 comparator was measured BEFORE `mindfulness_meditation` was
registered; this tree registers it. The gate run excludes it from the ROUTABLE
CANDIDATE SET via the `exclude_skills` run-config only — by dropping its anchors from
the (already-built) live anchor arrays (Tier-2 candidate surface) and dropping it from
the keyword-match dict (Tier-1 candidate surface). skill_ids.py / clinical_clusters.py /
mindfulness_meditation.json are NOT touched (clinician + governance territory).

SCOPE: local flags-off mode + acceptance gate + report ONLY. No flags-on (V2) mode, no
--target prod. Fixtures only, never live data (PDPL).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Callable, Iterable

# Flags-OFF is a hard precondition. skill_select reads the module constant SKILL_ROUTING_V2
# at import time to decide the anchor surface (include_exemplars), so pin the env BEFORE the
# import below. A caller that set them to "1" wants V2 — out of scope for this increment.
_V2 = os.environ.get("SKILL_ROUTING_V2", "0")
_RERANK = os.environ.get("SKILL_RERANK_ENABLED", "0")
if _V2 == "1" or _RERANK == "1":
    raise SystemExit(
        "real_model_driver is Increment 1 (flags-OFF/V1) only. "
        f"Got SKILL_ROUTING_V2={_V2!r} SKILL_RERANK_ENABLED={_RERANK!r}. "
        "Run with both = 0."
    )
os.environ.setdefault("SKILL_ROUTING_V2", "0")
os.environ.setdefault("SKILL_RERANK_ENABLED", "0")

from sage_poc.routing_eval.gate_runner import RoutingMetrics, compute_metrics_by_stratum
from sage_poc.routing_eval.schema import ABSTAIN, EvalRecord
from sage_poc.skills.keyword_matcher import match_skill_keywords
import sage_poc.nodes.skill_select as ss

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FIXTURE_DIR = _REPO_ROOT / "tests" / "fixtures" / "routing_eval"

# The EN bulk fixtures named by the acceptance gate. Strata come from each record's
# `stratum` field (bulk_oos_en.jsonl mixes id_oos + far_oos), NOT the filename.
_EN_BULK_FILES = ("bulk_in_scope.jsonl", "bulk_id_oos_en_v2.jsonl", "bulk_oos_en.jsonl")

DEFAULT_EXCLUDE_SKILLS = frozenset({"mindfulness_meditation"})  # spec §3


# --------------------------------------------------------------------------- loading
def _load_jsonl(path: Path) -> list[EvalRecord]:
    keep = set(EvalRecord.__dataclass_fields__)
    out: list[EvalRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        # tuple-valued fields must be tuples for the frozen record (JSON gives lists)
        for k in ("scored_candidates", "acceptable_routes"):
            if isinstance(d.get(k), list):
                d[k] = tuple(tuple(x) if isinstance(x, list) else x for x in d[k])
        out.append(EvalRecord(**{k: v for k, v in d.items() if k in keep}))
    return out


# Eval-set case exclusion (run-config, re-anchor 2026-07-07). Records whose expected_route
# is a deprecation-requested skill absent from SKILL_REGISTRY are structural NON-TESTS: no
# router on this tree can ever produce that route, so scoring them as recall misses measures
# registry drift, not routing quality. Dropping the CASES is NOT a registry edit and NOT a
# fixture edit — the fixtures on disk are untouched. mi_readiness_ruler is deprecation-requested
# (docs/superpowers/governance/2026-07-07-mi-readiness-ruler-deprecation-request.md).
DEFAULT_EXCLUDE_EXPECTED = frozenset({"mi_readiness_ruler"})


def load_en_bulk_records(
    files: Iterable[str] = _EN_BULK_FILES,
    exclude_expected: frozenset[str] = DEFAULT_EXCLUDE_EXPECTED,
) -> tuple[list[EvalRecord], dict[str, int]]:
    """Return (EN held-in records, dropped-count by stratum). `exclude_expected` drops whole
    cases whose expected_route is not a routable skill on this tree (structural non-tests)."""
    recs: list[EvalRecord] = []
    for f in files:
        recs.extend(_load_jsonl(_FIXTURE_DIR / f))
    en = [r for r in recs if r.lang == "en"]
    dropped: dict[str, int] = {}
    if exclude_expected:
        kept: list[EvalRecord] = []
        for r in en:
            if r.expected_route in exclude_expected:
                dropped[r.stratum] = dropped.get(r.stratum, 0) + 1
            else:
                kept.append(r)
        en = kept
    return en, dropped


# ------------------------------------------------------------------- candidate surface
def _prepare_candidate_surface(exclude_skills: frozenset[str]) -> None:
    """Load the live V1 anchor index, then remove `exclude_skills` from the Tier-2
    candidate surface by filtering the module-level anchor arrays in place. This is the
    §3 exclusion applied at CANDIDATE CONSTRUCTION only — registration files are untouched.
    max-over-anchors is per-skill, so dropping one skill's anchors leaves every other
    skill's score bit-identical; it only removes the excluded skill as a candidate.
    Idempotent."""
    ss._ensure_semantic_ready()  # V1 surface: build_anchor_pairs(include_exemplars=False)
    if not exclude_skills:
        return
    keep_idx = [i for i, sid in enumerate(ss._anchor_skill_ids) if sid not in exclude_skills]
    if len(keep_idx) == len(ss._anchor_skill_ids):
        return  # already filtered / nothing to drop
    ss._anchor_skill_ids = [ss._anchor_skill_ids[i] for i in keep_idx]
    ss._anchor_embeddings = ss._anchor_embeddings[keep_idx]


def make_routed_of(exclude_skills: frozenset[str] = DEFAULT_EXCLUDE_SKILLS) -> Callable[[EvalRecord], str]:
    """Return a faithful flags-off `routed_of` over EN utterances, with `exclude_skills`
    removed from BOTH candidate surfaces (Tier-1 keyword dict + Tier-2 anchors)."""
    _prepare_candidate_surface(exclude_skills)

    def routed_of(r: EvalRecord) -> str:
        utterance = r.utterance

        # Tier 1 — live keyword tier (skill_select.py:728-767), flags-off branch.
        kw = match_skill_keywords(utterance, "", "en")
        kw = {sid: n for sid, n in kw.items() if sid not in exclude_skills}
        if kw:
            ranked_kw = sorted(kw.items(), key=lambda x: x[1], reverse=True)
            candidates = [sid for sid, _ in ranked_kw]
            # C1 acute-overlap tiebreak (skill_select.py:751-756).
            if (
                candidates and candidates[0] == "dbt_tipp"
                and {"grounding_5_4_3_2_1", "dbt_tipp"} <= kw.keys()
            ):
                candidates.remove("grounding_5_4_3_2_1")
                candidates.insert(0, "grounding_5_4_3_2_1")
            return candidates[0]  # primary keyword route (enter/offer is consent-flow, not routing)

        # Pre-Tier-2 exclusion guard (skill_select.py:774).
        if ss._SEMANTIC_EXCLUSION_RE.search(utterance.lower()):
            return ABSTAIN

        # Tier 2 — live bi-encoder + live _route_decision (skill_select.py:800 -> :413 -> :302).
        best, _score = ss._semantic_match_sync(utterance)
        return best if best is not None else ABSTAIN

    return routed_of


# ------------------------------------------------------------------------------ report
def _cell_denoms(records: list[EvalRecord]) -> dict[tuple[str, str], tuple[int, int, str]]:
    """(skill_expected_n, abstain_expected_n, kind) per cell — DISPLAY ONLY, replicating
    the scorer's cell filter (gate_runner.py:91) + denominator split (gate_runner.py:57-59)
    so the printed numerator/denominator match what compute_metrics_by_stratum divided."""
    from sage_poc.routing_eval.gate_runner import _PATH_ASSERTION_KINDS
    out: dict[tuple[str, str], tuple[int, int, str]] = {}
    groups: dict[tuple[str, str], list[EvalRecord]] = {}
    for r in records:
        if not (r.held_out and not r.flag_bearing):
            continue
        groups.setdefault((r.lang, r.stratum), []).append(r)
    for key, rows in groups.items():
        rows = [r for r in rows if r.case_kind not in _PATH_ASSERTION_KINDS]
        skill_exp = sum(1 for r in rows if r.expected_route != ABSTAIN and not r.acceptable_routes)
        abstain_exp = sum(1 for r in rows if r.expected_route == ABSTAIN and not r.acceptable_routes)
        kind = "recall" if skill_exp >= abstain_exp else "abstain"
        out[key] = (skill_exp, abstain_exp, kind)
    return out


def run_gate(
    exclude_skills: frozenset[str] = DEFAULT_EXCLUDE_SKILLS,
    exclude_expected: frozenset[str] = DEFAULT_EXCLUDE_EXPECTED,
) -> dict:
    records, dropped = load_en_bulk_records(exclude_expected=exclude_expected)
    routed_of = make_routed_of(exclude_skills)
    by_stratum = compute_metrics_by_stratum(records, routed_of=routed_of)  # THE scorer
    denoms = _cell_denoms(records)

    report: dict = {
        "exclude_skills": sorted(exclude_skills),
        "exclude_expected": sorted(exclude_expected),
        "dropped_cases_by_stratum": dropped,
        "flags": {"SKILL_ROUTING_V2": os.environ["SKILL_ROUTING_V2"],
                  "SKILL_RERANK_ENABLED": os.environ["SKILL_RERANK_ENABLED"]},
        "cells": {},
        "prior_comparator": {"in_scope": "144/217", "id_oos": "25/71", "far_oos": "36/36"},
        "fixture_files": list(_EN_BULK_FILES),
    }
    order = [("en", "in_scope"), ("en", "id_oos"), ("en", "far_oos")]
    keys = order + [k for k in by_stratum if k not in order]
    for key in keys:
        m: RoutingMetrics | None = by_stratum.get(key)
        if m is None:
            continue
        skill_exp, abstain_exp, kind = denoms.get(key, (0, 0, "recall"))
        if kind == "recall":
            denom, rate = skill_exp, m.recall
        else:
            denom, rate = abstain_exp, m.abstain_correctness
        num = round(rate * denom)
        report["cells"][f"{key[0]}/{key[1]}"] = {
            "metric": kind, "num": num, "denom": denom,
            "pct": round(100 * rate, 1), "cell_n": m.n,
            "misroute_rate": round(m.misroute_rate, 4),
        }
    return report


def _print_report(report: dict) -> None:
    print("=" * 74)
    print("REAL-MODEL ROUTING DRIVER — acceptance gate (flags-OFF / V1)")
    print("=" * 74)
    print(f"flags: {report['flags']}")
    print(f"exclude_skills (spec §3): {report['exclude_skills']}")
    print(f"exclude_expected (eval-set case drop): {report['exclude_expected']}")
    print(f"dropped cases by stratum: {report['dropped_cases_by_stratum']}")
    print(f"fixtures: {report['fixture_files']}")
    print("-" * 74)
    print(f"{'cell':<16}{'metric':<10}{'got':<14}{'pct':<9}{'prior 6/24'}")
    tgt = report["prior_comparator"]
    for cell, c in report["cells"].items():
        stratum = cell.split("/")[-1]
        t = tgt.get(stratum, "")
        got = "{}/{}".format(c["num"], c["denom"])
        pct = "{}%".format(c["pct"])
        print(f"{cell:<16}{c['metric']:<10}{got:<14}{pct:<9}{t}")
    print("-" * 74)


def main(argv: list[str] | None = None) -> int:
    report = run_gate()
    _print_report(report)
    if "--json" in (argv if argv is not None else sys.argv[1:]):
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
