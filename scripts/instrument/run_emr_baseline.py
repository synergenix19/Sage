"""EMR Phase-0 distributional baseline runner (explicit-modality-request handling).

Drives every case in tests/fixtures/conformance/emr_request_family.json at N per
fixture THROUGH the parity helper (scripts/instrument/graph_evidence.py — the only
supported invocation path for evidence, signed instrument-parity standing rule
2026-07-28) and writes the baseline artifact with the template header block plus
per-fixture outcome DISTRIBUTIONS:

  - offer-rate (fraction of samples whose FINAL turn — the request turn — ends
    with a skill offered, active, or completed),
  - per-surface mechanism counts keyed on intent+path signatures of the final turn,
  - flip-rate per fixture (fraction of samples off the modal outcome; reported for
    both the final-turn mechanism and the full per-turn trajectory),
  - per-trajectory frequencies (full-session intent+path signatures).

This is the fresh comparator the re-plan's Phase 0 requires (the v5 2/5 row is
invalid: mechanism change since v5 + single-run measurement). Distributional
stability of the fixtures themselves is part of the readout (Node-2 bistability
finding: single-run characterization is a coin flip recorded as a verdict).

Provenance gate: SAGE_AUDIT_CLASSIFIER_PROVENANCE must resolve true for a REAL
baseline (register ruling in the re-plan Phase 0 — an unrecorded-provenance
baseline fails the signed instrument-parity rule). --allow-unrecorded-provenance
exists for pipeline smokes only and stamps the artifact loudly.

Usage:
  # full baseline (coordinator-reviewed step; real LLM cost)
  uv run python scripts/instrument/run_emr_baseline.py

  # pipeline smoke: N=1, one case, artifact to a scratch path
  uv run python scripts/instrument/run_emr_baseline.py --smoke --case EMR-S1-000 \
      --out /tmp/emr-smoke.md --allow-unrecorded-provenance
"""
import argparse
import asyncio
import collections
import importlib.util
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(_HERE))

_spec = importlib.util.spec_from_file_location(
    "graph_evidence", os.path.join(_HERE, "graph_evidence.py"))
ge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ge)

DEFAULT_FAMILY = os.path.join(REPO, "tests/fixtures/conformance/emr_request_family.json")
DEFAULT_OUT = os.path.join(REPO, "docs/superpowers/governance/2026-07-29-emr-phase0-baseline.md")
DEFAULT_N = 10


# ---------------------------------------------------------------------------
# Aggregation (pure — unit-tested with synthetic records)
# ---------------------------------------------------------------------------

def _offered(rec: dict) -> bool:
    """Did the turn end with a skill offered/active/completed? (completion markers
    included — the measure_layer1_fullgraph instrument correction: in-turn-completing
    skills clear active_skill_id by END.)"""
    return bool(rec.get("offered_skill_ids")) or bool(rec.get("active_skill_id")) \
        or bool(rec.get("completed_skill_id"))


def mechanism_signature(rec: dict) -> str:
    """Outcome mechanism keyed on intent + node-path signature."""
    return f"{rec.get('primary_intent')}|{'>'.join(rec.get('path') or [])}"


def trajectory_signature(records: list) -> str:
    return " ;; ".join(f"t{r['turn']}:{mechanism_signature(r)}" for r in records)


def aggregate_case(fixture_result: dict) -> dict:
    samples = fixture_result["samples"]
    n = len(samples)
    finals = [s["records"][-1] for s in samples]
    mech = collections.Counter(mechanism_signature(r) for r in finals)
    traj = collections.Counter(trajectory_signature(s["records"]) for s in samples)
    offer_rate = sum(_offered(r) for r in finals) / n if n else 0.0
    return {
        "n": n,
        "offer_rate": offer_rate,
        "mechanism_counts": dict(mech.most_common()),
        "mechanism_flip_rate": (1 - mech.most_common(1)[0][1] / n) if n else 0.0,
        "trajectory_freqs": dict(traj.most_common()),
        "trajectory_flip_rate": (1 - traj.most_common(1)[0][1] / n) if n else 0.0,
        "degraded_turn_count": fixture_result.get("degraded_turn_count", 0),
        "final_turn_offered_detail": [
            {"sample": s["sample"],
             "offered_skill_ids": s["records"][-1].get("offered_skill_ids"),
             "active_skill_id": s["records"][-1].get("active_skill_id"),
             "skill_match_method": s["records"][-1].get("skill_match_method")}
            for s in samples],
    }


# ---------------------------------------------------------------------------
# Provenance gate
# ---------------------------------------------------------------------------

def enforce_recorded_provenance(effective: dict, allow_unrecorded: bool) -> str | None:
    on = (effective.get("SAGE_AUDIT_CLASSIFIER_PROVENANCE") or "false").lower() == "true"
    if on:
        return None
    if not allow_unrecorded:
        raise ge.ParityRefusal(
            "REFUSING: SAGE_AUDIT_CLASSIFIER_PROVENANCE resolves false in the derived "
            "(serving) flag set — an unrecorded-provenance baseline fails the signed "
            "instrument-parity rule (re-plan Phase 0 register ruling). The deploy owner "
            "must activate provenance in the evidence environment first. "
            "(--allow-unrecorded-provenance exists for pipeline SMOKES only.)")
    return ("LOUD: run proceeded with UNRECORDED classifier provenance "
            "(--allow-unrecorded-provenance) — NOT citable as the Phase-0 baseline; "
            "pipeline smoke only.")


# ---------------------------------------------------------------------------
# Artifact
# ---------------------------------------------------------------------------

def _fmt_rate(x: float) -> str:
    return f"{x:.2f}"


def render_body(per_case: dict) -> str:
    lines = [
        "## Per-fixture outcome distributions", "",
        "Offer-rate = fraction of samples whose FINAL (request) turn ends with a skill "
        "offered/active/completed. Flip-rate = fraction of samples off the modal outcome "
        "(mechanism = final-turn intent+path signature; trajectory = full session).", "",
        "| case | surface | n | offer-rate | mech flip-rate | traj flip-rate | degraded turns | modal mechanism |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for cid, agg in per_case.items():
        modal = next(iter(agg["mechanism_counts"]), "-")
        lines.append(
            f"| {cid} | {agg.get('surface', '?')} | {agg['n']} | {_fmt_rate(agg['offer_rate'])} "
            f"| {_fmt_rate(agg['mechanism_flip_rate'])} | {_fmt_rate(agg['trajectory_flip_rate'])} "
            f"| {agg['degraded_turn_count']} | `{modal}` |")
    lines.append("")
    for cid, agg in per_case.items():
        lines += [f"### {cid}", ""]
        exp = (agg.get("spec_expectation") or {}).get("expected")
        if exp:
            lines += [f"- **spec_expectation:** {exp}", ""]
        lines += [f"- offer-rate: **{_fmt_rate(agg['offer_rate'])}** over n={agg['n']}",
                  f"- mechanism flip-rate: {_fmt_rate(agg['mechanism_flip_rate'])} | "
                  f"trajectory flip-rate: {_fmt_rate(agg['trajectory_flip_rate'])}",
                  "", "Mechanism counts (final turn, intent+path signature):", ""]
        for sig, cnt in agg["mechanism_counts"].items():
            lines.append(f"- {cnt}/{agg['n']} `{sig}`")
        lines += ["", "Trajectory frequencies (full session):", ""]
        for sig, cnt in agg["trajectory_freqs"].items():
            lines.append(f"- {cnt}/{agg['n']} `{sig}`")
        lines.append("")
    return "\n".join(lines)


def write_baseline(out_path: str, header: dict, per_case: dict,
                   extra_notes: list | None = None) -> None:
    body = render_body(per_case)
    if extra_notes:
        body = "\n".join(f"> **{n}**" for n in extra_notes) + "\n\n" + body
    ge.write_artifact(out_path, header, body,
                      title="EMR Phase-0 baseline — explicit-modality-request handling "
                            "(distributional, pre-fix)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def _amain(args) -> int:
    derived, readback = ge.prepare_evidence_env(args.base_url, args.railway_service,
                                                args.allow_deploy_window)
    prov_note = enforce_recorded_provenance(derived["effective"],
                                            args.allow_unrecorded_provenance)
    if prov_note:
        print(prov_note, flush=True)

    family = json.load(open(args.family, encoding="utf-8"))
    cases = family["cases"]
    if args.case:
        cases = [c for c in cases if c["case_id"] in args.case]
        if not cases:
            print(f"no case matched {args.case}", file=sys.stderr)
            return 2
    if args.smoke:
        cases = cases[:1] if not args.case else cases

    if not os.getenv("OPENROUTER_API_KEY"):
        # This check runs BEFORE any sage_poc import (config.py's load_dotenv has not
        # run yet), so backfill from the repo .env the same way config.py would.
        env_key = ge._load_env_file(os.path.join(REPO, ".env")).get("OPENROUTER_API_KEY")
        if env_key:
            os.environ["OPENROUTER_API_KEY"] = env_key
    if not os.getenv("OPENROUTER_API_KEY"):
        # config.py may have imported without it; the graph's classifier cannot run.
        print("FATAL: OPENROUTER_API_KEY missing — the graph's intent classifier cannot "
              "run. STOP; do not fabricate readouts.", file=sys.stderr)
        return 2

    app = ge.build_local_graph()
    t0 = time.time()
    per_case, all_fingerprints, degraded_total, faults = {}, [], 0, []
    for c in cases:
        cid = c["case_id"]
        try:
            result = await ge.run_fixture(
                app, c["turns"], args.n,
                thread_prefix=f"emr-{readback.get('build_sha', 'x')[:7]}-{cid}")
        except Exception as e:  # noqa: BLE001
            faults.append({"case": cid, "err": repr(e)[:300]})
            print(f"[{time.time()-t0:.0f}s] {cid} FAULT {repr(e)[:120]}", flush=True)
            continue
        all_fingerprints += ge.collect_fingerprints(result)
        degraded_total += result["degraded_turn_count"]
        agg = aggregate_case(result)
        agg["surface"] = c.get("surface")
        agg["spec_expectation"] = c.get("spec_expectation")
        per_case[cid] = agg
        if args.json:
            per_case[cid]["_raw_samples"] = result["samples"]
        print(f"[{time.time()-t0:.0f}s] {cid} n={args.n} offer-rate="
              f"{agg['offer_rate']:.2f} mech-flip={agg['mechanism_flip_rate']:.2f}",
              flush=True)

    header = ge.header_block(derived, readback, n_per_fixture=args.n,
                             degraded_turn_count=degraded_total,
                             fingerprints=all_fingerprints, base_url=args.base_url)
    notes = []
    if prov_note:
        notes.append(prov_note)
    if args.smoke:
        notes.append("PIPELINE SMOKE ONLY (N=%d, %d case(s)) — NOT the Phase-0 baseline."
                     % (args.n, len(cases)))
    if faults:
        notes.append(f"RUN VOID: {len(faults)} instrument fault(s) — a partial baseline "
                     f"is not data. First: {faults[0]}")

    raw_dump = None
    if args.json:
        raw_dump = {cid: agg.pop("_raw_samples") for cid, agg in per_case.items()
                    if "_raw_samples" in agg}
    write_baseline(args.out, header, per_case, extra_notes=notes)
    print(f"baseline artifact written: {args.out}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"header": header, "per_case": per_case, "raw_samples": raw_dump,
                       "faults": faults}, f, indent=2, ensure_ascii=False, default=str)
        print(f"raw records written: {args.json}")
    return 1 if faults else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--family", default=DEFAULT_FAMILY)
    ap.add_argument("--n", type=int, default=DEFAULT_N)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--json", default=None, help="also dump raw per-sample records")
    ap.add_argument("--case", action="append", default=None,
                    help="restrict to case id(s); repeatable")
    ap.add_argument("--smoke", action="store_true",
                    help="pipeline smoke: forces N=1 and (unless --case) the first case only")
    ap.add_argument("--allow-unrecorded-provenance", action="store_true",
                    help="SMOKES ONLY: proceed although SAGE_AUDIT_CLASSIFIER_PROVENANCE "
                         "is off; artifact is loudly stamped non-baseline")
    ap.add_argument("--allow-deploy-window", action="store_true",
                    help="SMOKES ONLY (requires --smoke): proceed although serving != "
                         "desired; divergence is stamped loudly, output is not a baseline")
    ap.add_argument("--base-url", default=os.getenv("SAGE_PROD_HEALTH_URL", ge.DEFAULT_BASE_URL))
    ap.add_argument("--railway-service", default="sage-api")
    args = ap.parse_args(argv)
    if args.allow_deploy_window and not args.smoke:
        print("REFUSING: --allow-deploy-window is smoke-only — an evidence baseline is "
              "never taken against a mid-transition prod.", file=sys.stderr)
        return 2
    if args.smoke:
        args.n = 1
        if os.path.abspath(args.out) == os.path.abspath(DEFAULT_OUT):
            print("REFUSING: --smoke may not write the governance baseline path; "
                  "pass an explicit scratch --out.", file=sys.stderr)
            return 2
    try:
        return asyncio.run(_amain(args))
    except ge.ParityRefusal as e:
        print(str(e), file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
