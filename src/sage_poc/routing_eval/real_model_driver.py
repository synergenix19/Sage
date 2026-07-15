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

# MODE is pinned from the env BEFORE importing skill_select, because skill_select reads the
# module constant SKILL_ROUTING_V2 at import time to decide the Tier-2 anchor surface
# (include_exemplars) — a V2 run MUST embed target_presentations as exemplars, so the env has to
# be set at process start (a flags-off-built index must never be reused for a V2 run; run each
# mode as its own process). Increment 1 = flags-OFF/V1; Increment 2 = flags-ON/V2.
#   V1: SKILL_ROUTING_V2=0 SKILL_RERANK_ENABLED=0
#   V2: SKILL_ROUTING_V2=1 SKILL_RERANK_ENABLED=1 SKILL_RERANK_PRECISION=fp32
os.environ.setdefault("SKILL_ROUTING_V2", "0")
os.environ.setdefault("SKILL_RERANK_ENABLED", "0")
_V2 = os.environ["SKILL_ROUTING_V2"] == "1"
_RERANK = os.environ["SKILL_RERANK_ENABLED"] == "1"
MODE = "V2" if _V2 else "V1"
if _V2 != _RERANK:
    raise SystemExit(
        "V1 needs BOTH flags off; V2 needs BOTH on (routing-V2 exemplar set + reranker selector). "
        f"Got SKILL_ROUTING_V2={os.environ['SKILL_ROUTING_V2']!r} "
        f"SKILL_RERANK_ENABLED={os.environ['SKILL_RERANK_ENABLED']!r}."
    )
if _V2:
    # fp32 ONLY. int8 is SAFETY-DISQUALIFIED (over-routes 6/6 id_oos clinician-territory cases
    # fp32 ABSTAINS — skill_rerank_model.py docstring). Refuse to produce a V2 number under int8.
    _prec = os.environ.setdefault("SKILL_RERANK_PRECISION", "fp32").lower()
    if _prec != "fp32":
        raise SystemExit(
            f"V2 gate is fp32 only; int8 is safety-disqualified. Got SKILL_RERANK_PRECISION={_prec!r}."
        )

from sage_poc.routing_eval.gate_runner import RoutingMetrics, compute_metrics_by_stratum
from sage_poc.routing_eval.schema import ABSTAIN, EvalRecord
from sage_poc.skills.keyword_matcher import match_skill_keywords
from sage_poc.nodes.ocd_compulsion import is_ocd_compulsion as ss_is_ocd_compulsion
from sage_poc.nodes.harm_intrusive import is_harm_intrusive as ss_is_harm_intrusive
import sage_poc.nodes.skill_select as ss

# WRONG-TREE GUARD. This package is installed editable (`_editable_impl_sage_poc.pth` appends the
# MAIN checkout's src/ to sys.path), so `.venv/bin/python` run from ANY worktree silently imports
# the main checkout's sage_poc unless PYTHONPATH overrides it — a verification run can then produce
# a green result against the wrong code. When SAGE_EXPECT_SRC is set (to the src/ of the tree under
# test), fail loudly at import if the resolved package is not under it. Opt-in: unset = no-op.
_expect_src = os.environ.get("SAGE_EXPECT_SRC")
if _expect_src:
    import sage_poc as _sp
    _resolved = str(Path(_sp.__file__).resolve())
    if not _resolved.startswith(str(Path(_expect_src).resolve())):
        raise SystemExit(
            f"SAGE_EXPECT_SRC guard: routing_eval imported sage_poc from {_resolved!r}, "
            f"not under the intended tree {_expect_src!r}. A stale editable-install .pth is "
            f"shadowing the worktree — set PYTHONPATH={_expect_src} (before site-packages)."
        )

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
    """Load the live anchor index FOR THE CURRENT MODE, then remove `exclude_skills` from the
    Tier-2 candidate surface by filtering the module-level anchor arrays in place. Under V1 the
    index is description+anchors (include_exemplars=False); under V2 it also embeds
    target_presentations as exemplars and excludes the referral pathways (build_anchor_pairs reads
    the module constant SKILL_ROUTING_V2, which is True here because the env was set at process
    start). This is the §3 exclusion applied at CANDIDATE CONSTRUCTION only — registration files
    are untouched. max-over-anchors is per-skill, so dropping one skill's anchors leaves every
    other skill's score bit-identical; it only removes the excluded skill as a candidate.
    Idempotent."""
    ss._ensure_semantic_ready()  # builds for the current mode (include_exemplars=SKILL_ROUTING_V2)
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

        # Harm-intrusive iatrogenic veto (skill_select.py, arm-independent, before both tiers).
        # A postpartum/parental ego-dystonic disclosure of intrusive images/thoughts of harming a
        # baby or child ABSTAINS (never routes to a self-help skill). Deterministic, runs identically
        # in V1 and V2. Mirrors the live node's is_harm_intrusive(message_en) check.
        if ss_is_harm_intrusive(utterance):
            return ABSTAIN

        # OCD-compulsion iatrogenic veto (skill_select.py, arm-independent, before both tiers).
        # A disclosed compulsion/ritual ABSTAINS (never routes to a self-help skill). Deterministic,
        # runs identically in V1 and V2. Mirrors the live node's is_ocd_compulsion(message_en) check.
        if ss_is_ocd_compulsion(utterance):
            return ABSTAIN

        # Tier 1 — live keyword tier (skill_select.py:728-767).
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
            # V2: keyword routes are also gated by the reranker's ABSTAIN floor
            # (skill_select.py:761 -> _keyword_rerank_veto). A keyword false-match on
            # clinician-territory must not bypass the reranker. Flag-off: never runs (byte-identical V1).
            if ss._rerank_enabled() and ss._keyword_rerank_veto(candidates, utterance, "en"):
                return ABSTAIN
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


# Frozen V1 baseline (accepted 2026-07-07 @ fixtures 5e6b86e; committed corpus 192/64/32,
# mm-excluded, mi_readiness_ruler-cases dropped). V2 acceptance = beats-per-stratum vs THIS.
V1_BASELINE = {
    "en/in_scope": {"metric": "recall", "num": 109, "denom": 192, "pct": 56.8},
    "en/id_oos":   {"metric": "abstain", "num": 23,  "denom": 64,  "pct": 35.9},
    "en/far_oos":  {"metric": "abstain", "num": 32,  "denom": 32,  "pct": 100.0},
}


def positive_control() -> dict | None:
    """CRITICAL pre-trust check for V2: the fp32 cross-encoder head must be loaded (logit
    separation > 3). A headless CrossEncoder load yields ~0 logits = confident-wrong routing with
    NO error. Returns None in V1 (reranker unused). In V2, returns {ok, separation}."""
    if MODE != "V2":
        return None
    from sage_poc.nodes import skill_rerank_model as rr
    rel, off = rr.score_pairs([
        ("I want to write down and challenge my negative thoughts",
         "Guided practice for writing down an automatic negative thought and examining the evidence."),
        ("what time does the grocery store close today",
         "Guided practice for writing down an automatic negative thought and examining the evidence."),
    ])
    return {"ok": rr.head_loaded_ok(), "separation": round(rel - off, 4),
            "precision": rr.active_precision(), "tau_en": ss._rerank_tau("en")}


def run_gate(
    exclude_skills: frozenset[str] = DEFAULT_EXCLUDE_SKILLS,
    exclude_expected: frozenset[str] = DEFAULT_EXCLUDE_EXPECTED,
) -> dict:
    pc = positive_control()
    if MODE == "V2" and not (pc and pc["ok"]):
        raise SystemExit(
            f"POSITIVE CONTROL FAILED — reranker head not loaded (separation={pc and pc['separation']}). "
            "A headless CrossEncoder yields ~0 logits = confident-wrong routing. Refusing to report V2 numbers."
        )

    records, dropped = load_en_bulk_records(exclude_expected=exclude_expected)
    routed_of = make_routed_of(exclude_skills)
    by_stratum = compute_metrics_by_stratum(records, routed_of=routed_of)  # THE scorer
    denoms = _cell_denoms(records)

    report: dict = {
        "mode": MODE,
        "positive_control": pc,
        "exclude_skills": sorted(exclude_skills),
        "exclude_expected": sorted(exclude_expected),
        "dropped_cases_by_stratum": dropped,
        "flags": {"SKILL_ROUTING_V2": os.environ["SKILL_ROUTING_V2"],
                  "SKILL_RERANK_ENABLED": os.environ["SKILL_RERANK_ENABLED"],
                  "SKILL_RERANK_PRECISION": os.environ.get("SKILL_RERANK_PRECISION", "fp32")},
        "cells": {},
        "v1_baseline": V1_BASELINE,
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
        cell = f"{key[0]}/{key[1]}"
        entry = {
            "metric": kind, "num": num, "denom": denom,
            "pct": round(100 * rate, 1), "cell_n": m.n,
            "misroute_rate": round(m.misroute_rate, 4),
        }
        base = V1_BASELINE.get(cell)
        if base is not None:
            delta = round(entry["pct"] - base["pct"], 1)
            entry["vs_v1"] = "BEATS" if delta > 0 else ("TIES" if delta == 0 else "BELOW")
            entry["delta_pct"] = delta
        report["cells"][cell] = entry
    return report


def _print_report(report: dict) -> None:
    print("=" * 84)
    print(f"REAL-MODEL ROUTING DRIVER — {report['mode']} run")
    print("=" * 84)
    print(f"flags: {report['flags']}")
    if report.get("positive_control") is not None:
        print(f"positive_control (reranker head): {report['positive_control']}")
    print(f"exclude_skills (spec §3): {report['exclude_skills']}")
    print(f"exclude_expected (eval-set case drop): {report['exclude_expected']}")
    print(f"dropped cases by stratum: {report['dropped_cases_by_stratum']}")
    print(f"fixtures: {report['fixture_files']}")
    print("-" * 84)
    print(f"{'cell':<15}{'metric':<9}{'V1 (frozen)':<15}{report['mode']+' (this)':<15}{'delta':<9}{'vs V1'}")
    base = report["v1_baseline"]
    for cell, c in report["cells"].items():
        b = base.get(cell, {})
        v1 = "{}/{} {}%".format(b.get("num", "?"), b.get("denom", "?"), b.get("pct", "?"))
        v2 = "{}/{} {}%".format(c["num"], c["denom"], c["pct"])
        delta = c.get("delta_pct", "")
        verdict = c.get("vs_v1", "")
        print(f"{cell:<15}{c['metric']:<9}{v1:<15}{v2:<15}{str(delta):<9}{verdict}")
    print("-" * 84)


def main(argv: list[str] | None = None) -> int:
    report = run_gate()
    _print_report(report)
    if "--json" in (argv if argv is not None else sys.argv[1:]):
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
