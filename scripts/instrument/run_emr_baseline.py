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

# BOT BEHAVIOUR §1a Tier-1 first-line pair (spec offer table). The spec-conformance
# column counts ONLY these; the offer-rate/first-line delta is itself the DF-1
# ordering evidence (semantic rank serving psychoed/worry_time/PMR, never the pair).
FIRST_LINE_PAIR = frozenset({"box_breathing", "grounding_5_4_3_2_1"})

# Path marker skill_select emits when a pending offer is genuinely promoted to the
# active skill (skill_select.py: path + ["skill_select", "offer_promoted"],
# skill_match_method "offer_accept"). Activation WITHOUT this marker (psychoed
# absorption via skill_executor, info_request_skill_consult, auto-selects) is not
# offer-derived and never spec-conformant here.
OFFER_PROMOTED_MARKER = "offer_promoted"


def _offered(rec: dict) -> bool:
    """Did the turn end with a skill offered/active/completed? (completion markers
    included — the measure_layer1_fullgraph instrument correction: in-turn-completing
    skills clear active_skill_id by END.)"""
    return bool(rec.get("offered_skill_ids")) or bool(rec.get("active_skill_id")) \
        or bool(rec.get("completed_skill_id"))


def _first_line_offered(rec: dict) -> bool:
    """Spec-conformance test for the final/request turn: the §1a Tier-1 pair was
    OFFERED (offered_skill_ids intersects the pair), or a pair skill was ACTIVATED
    through a genuinely offer-derived path (offer_promoted marker). Psychoed
    absorption, semantic offers of other skills, and knowledge-path responses all
    count 0 even when offer-rate counts them."""
    if FIRST_LINE_PAIR & set(rec.get("offered_skill_ids") or []):
        return True
    if OFFER_PROMOTED_MARKER in (rec.get("path") or []):
        activated = rec.get("active_skill_id") or rec.get("completed_skill_id")
        return activated in FIRST_LINE_PAIR
    return False


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
    first_line_rate = sum(_first_line_offered(r) for r in finals) / n if n else 0.0
    return {
        "n": n,
        "offer_rate": offer_rate,
        "first_line_offer_rate": first_line_rate,
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
# Quiescence attestation (baseline pre-authorization, BINDING)
# ---------------------------------------------------------------------------
# The full baseline may not run against a prod whose quiescence is merely assumed.
# Attestation = (1) two CLEAN desired+serving readback checks of the signed-flag
# set (minimum SAGE_INFO_REQUEST_CONSULT) that SPAN at least one deploy cycle
# (deployment id changed between checks, or a deployment timestamp is bracketed
# by them), AND (2) a NAMED CAUSE from the binding enum below. The clock alone
# NEVER satisfies it: an elapsed-time-only state refuses explicitly. Refusals are
# RECORDED (timestamp + failed condition) in the state file and surface in the
# eventual artifact's header as the refusal log — never silently retried.

QUIESCENCE_CAUSES = {
    "item1-condition-a",      # parallel writer confirmed stopped
    "item1-condition-b",      # activity feed clean over a deploy cycle
    "supersession-ratified",  # the diverging desired state was ratified as superseding
}
SIGNED_FLAG_MINIMUM = ("SAGE_INFO_REQUEST_CONSULT",)
DEFAULT_QUIESCENCE_STATE = os.path.join(
    REPO, "docs/superpowers/governance/2026-07-29-emr-phase0-quiescence.json")


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_quiescence_state(path: str) -> dict:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = {}
    state.setdefault("checks", [])
    state.setdefault("refusals", [])
    return state


def save_quiescence_state(path: str, state: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _ts(value: str):
    from datetime import datetime
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def evaluate_quiescence(state: dict, cause) -> dict:
    """Pure evaluation of the attestation over recorded checks. Returns
    {"ok": bool, "condition_failed": str|None, "detail": str}."""
    if cause not in QUIESCENCE_CAUSES:
        return {"ok": False, "condition_failed": "missing-or-invalid-cause",
                "detail": ("quiescence requires a NAMED CAUSE via --quiescence-cause, "
                           f"got {cause!r}; allowed: " + ", ".join(sorted(QUIESCENCE_CAUSES)))}
    clean = [c for c in state.get("checks", [])
             if c.get("clean")
             and all(f in c.get("flags_checked", []) for f in SIGNED_FLAG_MINIMUM)]
    if len(clean) < 2:
        return {"ok": False, "condition_failed": "insufficient-clean-checks",
                "detail": (f"{len(clean)} clean check(s) covering the signed-flag set "
                           f"(min {', '.join(SIGNED_FLAG_MINIMUM)}) recorded; need two "
                           "clean desired+serving checks spanning a deploy cycle")}
    events = [_ts(c.get("deployment_created_at")) for c in state.get("checks", [])]
    events = [e for e in events if e is not None]
    for i, a in enumerate(clean):
        for b in clean[i + 1:]:
            ida, idb = a.get("deployment_id"), b.get("deployment_id")
            if ida and idb and ida != idb:
                return {"ok": True, "condition_failed": None,
                        "detail": (f"deploy cycle spanned: deployment id changed "
                                   f"{ida} -> {idb} between clean checks "
                                   f"{a['ts']} / {b['ts']}")}
            ta, tb = _ts(a.get("ts")), _ts(b.get("ts"))
            if ta and tb:
                lo, hi = min(ta, tb), max(ta, tb)
                for ev in events:
                    if lo < ev < hi:
                        return {"ok": True, "condition_failed": None,
                                "detail": (f"deploy cycle spanned: deployment at "
                                           f"{ev.isoformat()} bracketed by clean checks "
                                           f"{lo.isoformat()} / {hi.isoformat()}")}
    return {"ok": False, "condition_failed": "no-deploy-cycle-spanned",
            "detail": ("two clean checks exist but no deploy cycle is spanned "
                       "(deployment id unchanged and no deployment timestamp bracketed) "
                       "— the clock alone NEVER satisfies quiescence; elapsed time is "
                       "not evidence of a completed deploy cycle")}


def record_refusal(state: dict, result: dict) -> dict:
    entry = {"ts": _now_iso(), "condition_failed": result["condition_failed"],
             "detail": result["detail"]}
    state.setdefault("refusals", []).append(entry)
    return entry


def attach_quiescence_to_header(header: dict, cause, result: dict, state: dict) -> None:
    """Standing rule 2: the artifact carries the attestation AND every recorded
    refusal, inline, so a strong-armed baseline is distinguishable at read time."""
    header["quiescence_attestation"] = {
        "cause": cause,
        "detail": result["detail"],
        "clean_checks": [c for c in state.get("checks", []) if c.get("clean")],
        "refusal_log": list(state.get("refusals", [])),
    }
    notes = header.setdefault("parity_notes", [])
    notes.append(f"quiescence attestation: cause={cause}; {result['detail']}")
    if state.get("refusals"):
        for r in state["refusals"]:
            notes.append(f"quiescence refusal log: {r['ts']} "
                         f"condition={r['condition_failed']} — {r['detail']}")
    else:
        notes.append("quiescence refusal log: empty (no refusals recorded)")


def _fetch_deployment_info(service: str = "sage-api") -> dict:
    """Best-effort deployment id + created-at via railway status (None fields when
    unavailable — absence is recorded, never fabricated)."""
    import subprocess
    rw_env = {**os.environ, "RAILWAY_CALLER": "instrument:run_emr_baseline"}
    for cmd in (["railway", "status", "--json"],):
        try:
            raw = subprocess.check_output(cmd, text=True, timeout=45, env=rw_env,
                                          stderr=subprocess.DEVNULL)
            data = json.loads(raw)
        except Exception:  # noqa: BLE001
            continue
        found = {}

        def _walk(node):
            if isinstance(node, dict):
                keys = {k.lower(): k for k in node}
                if "id" in keys and ("status" in keys or "createdat" in keys) \
                        and not found:
                    found["deployment_id"] = node.get(keys["id"])
                    found["deployment_created_at"] = node.get(keys.get("createdat", ""))
                for k, v in node.items():
                    if "deployment" in k.lower() or isinstance(v, (dict, list)):
                        _walk(v)
            elif isinstance(node, list):
                for v in node:
                    _walk(v)

        _walk(data)
        return {"deployment_id": found.get("deployment_id"),
                "deployment_created_at": found.get("deployment_created_at")}
    return {"deployment_id": None, "deployment_created_at": None}


def record_quiescence_check(state_path: str, base_url: str, service: str) -> dict:
    """One desired+serving readback comparison of the signed-flag set, recorded into
    the quiescence state file. Two clean checks spanning a deploy cycle satisfy
    attestation condition (1)."""
    readback = ge.fetch_readback(base_url)
    desired = ge.fetch_railway_desired(service)
    serving = ge.map_readback_to_sage(readback)
    mapping = ge.config_sage_vars()
    mismatches, flags_checked = [], []
    if desired is None:
        clean = False
        detail = "railway (desired) unavailable — a one-sided check is never clean"
    else:
        for var in sorted(mapping):
            if var not in serving:
                continue
            flags_checked.append(var)
            srv = serving[var] if serving[var] is not None else mapping[var]
            des = desired.get(var) if desired.get(var) is not None else mapping[var]
            if srv != des:
                mismatches.append({"var": var, "serving": srv, "desired": des})
        clean = not mismatches
        detail = "serving == desired on all readback-covered vars" if clean else \
            f"{len(mismatches)} serving/desired mismatch(es)"
    check = {"ts": _now_iso(), "clean": clean, "detail": detail,
             "build_sha": readback.get("build_sha"),
             "flags_checked": flags_checked, "mismatches": mismatches,
             **_fetch_deployment_info(service)}
    state = load_quiescence_state(state_path)
    state["checks"].append(check)
    save_quiescence_state(state_path, state)
    return check


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
        "Offer-rate = fraction of samples whose FINAL (request) turn ends with ANY skill "
        "offered/active/completed. First-line rate = spec-conformance column: the BOT "
        "BEHAVIOUR §1a Tier-1 pair {box_breathing, grounding_5_4_3_2_1} offered, or a "
        "pair skill activated via the offer_promoted path; psychoed absorption, other-skill "
        "semantic offers, and knowledge-path responses count 0 here even when offer-rate "
        "counts them — the offer-rate/first-line DELTA is the DF-1 ordering evidence. "
        "Flip-rate = fraction of samples off the modal outcome (mechanism = final-turn "
        "intent+path signature; trajectory = full session).", "",
        "| case | surface | n | offer-rate | first-line rate | mech flip-rate | traj flip-rate | degraded turns | modal mechanism |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for cid, agg in per_case.items():
        modal = next(iter(agg["mechanism_counts"]), "-")
        lines.append(
            f"| {cid} | {agg.get('surface', '?')} | {agg['n']} | {_fmt_rate(agg['offer_rate'])} "
            f"| {_fmt_rate(agg['first_line_offer_rate'])} "
            f"| {_fmt_rate(agg['mechanism_flip_rate'])} | {_fmt_rate(agg['trajectory_flip_rate'])} "
            f"| {agg['degraded_turn_count']} | `{modal}` |")
    lines.append("")
    for cid, agg in per_case.items():
        lines += [f"### {cid}", ""]
        exp = (agg.get("spec_expectation") or {}).get("expected")
        if exp:
            lines += [f"- **spec_expectation:** {exp}", ""]
        lines += [f"- offer-rate: **{_fmt_rate(agg['offer_rate'])}** | first-line offer-rate "
                  f"(§1a Tier-1 pair, spec-conformant): **{_fmt_rate(agg['first_line_offer_rate'])}** "
                  f"over n={agg['n']}",
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
    # ---- Quiescence attestation gate (full baseline only; smokes are already
    # stamped non-baseline). Evaluated BEFORE any prod read beyond what the checks
    # themselves recorded, and BEFORE any LLM spend. Refusals are RECORDED in the
    # state file — never silently retried.
    qstate = load_quiescence_state(args.quiescence_state)
    qresult = None
    if not args.smoke:
        qresult = evaluate_quiescence(qstate, args.quiescence_cause)
        if not qresult["ok"]:
            entry = record_refusal(qstate, qresult)
            save_quiescence_state(args.quiescence_state, qstate)
            print("REFUSING (quiescence attestation NOT satisfied): "
                  f"[{qresult['condition_failed']}] {qresult['detail']}\n"
                  f"Refusal RECORDED at {entry['ts']} in {args.quiescence_state} "
                  "(will appear in the eventual artifact's refusal log).",
                  file=sys.stderr, flush=True)
            return 2

    overrides = {}
    for spec in (args.override_flag or []):
        var, _, val = spec.partition("=")
        if not var.startswith("SAGE_") or not val:
            print(f"FATAL: --override-flag expects SAGE_VAR=value, got {spec!r}",
                  file=sys.stderr)
            return 2
        overrides[var] = val
    derived, readback = ge.prepare_evidence_env(args.base_url, args.railway_service,
                                                args.allow_deploy_window,
                                                flag_overrides=overrides or None)
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
    # DB parity (2026-07-30 close-read ruling): serving always has the KB pool; a
    # direct-graph run has it only via attach_db_pool(). A DB-absent FULL run is the
    # shakedown class — refuse rather than produce a plausible-looking non-baseline.
    db_pool = await ge.attach_db_pool()
    if db_pool is None and not (args.smoke or args.allow_db_absent):
        print("REFUSING: DB pool unavailable — knowledge_retrieve would abstain on every "
              "KB-path turn, a different graph than prod serves. Set DATABASE_URL (or fix "
              "the connection) and re-run. (--allow-db-absent exists for pipeline SMOKES "
              "only and stamps the artifact loudly.)", file=sys.stderr, flush=True)
        return 2
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
              f"{agg['offer_rate']:.2f} first-line={agg['first_line_offer_rate']:.2f} "
              f"mech-flip={agg['mechanism_flip_rate']:.2f}", flush=True)

    header = ge.header_block(derived, readback, n_per_fixture=args.n,
                             degraded_turn_count=degraded_total,
                             fingerprints=all_fingerprints, base_url=args.base_url,
                             db_pool_available=db_pool is not None)
    if db_pool is not None:
        await db_pool.close()
    if qresult is not None and qresult["ok"]:
        attach_quiescence_to_header(header, args.quiescence_cause, qresult, qstate)
    notes = []
    if prov_note:
        notes.append(prov_note)
    if args.smoke:
        notes.append("PIPELINE SMOKE ONLY (N=%d, %d case(s)) — NOT the Phase-0 baseline; "
                     "quiescence attestation NOT evaluated (binding for the full "
                     "baseline only)." % (args.n, len(cases)))
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
    ap.add_argument("--override-flag", action="append", default=None,
                    metavar="SAGE_VAR=value",
                    help="FIX-ARM MEASUREMENT ONLY: apply a deliberate flag delta after "
                         "serving-parity export (repeatable). Every override is stamped "
                         "into the resolved set (coverage 'deliberate_override') with a "
                         "loud parity note; the artifact is a counterfactual arm, never "
                         "a serving-parity baseline")
    ap.add_argument("--allow-db-absent", action="store_true",
                    help="SMOKES ONLY: proceed although the KB DB pool is unavailable "
                         "(knowledge_retrieve abstains on every KB-path turn); the header "
                         "records db_pool_available=false and the artifact is not citable "
                         "as a baseline-of-record")
    ap.add_argument("--quiescence-cause", default=None,
                    help="BINDING named cause for the quiescence attestation; one of: "
                         + ", ".join(sorted(QUIESCENCE_CAUSES)))
    ap.add_argument("--quiescence-state", default=DEFAULT_QUIESCENCE_STATE,
                    help="quiescence state file (recorded checks + refusal log)")
    ap.add_argument("--record-quiescence-check", action="store_true",
                    help="record ONE desired+serving readback check of the signed-flag "
                         "set into the state file and exit (no graph, no LLM); two clean "
                         "checks spanning a deploy cycle satisfy attestation condition 1")
    ap.add_argument("--base-url", default=os.getenv("SAGE_PROD_HEALTH_URL", ge.DEFAULT_BASE_URL))
    ap.add_argument("--railway-service", default="sage-api")
    args = ap.parse_args(argv)
    if args.record_quiescence_check:
        try:
            check = record_quiescence_check(args.quiescence_state, args.base_url,
                                            args.railway_service)
        except ge.ParityRefusal as e:
            print(str(e), file=sys.stderr, flush=True)
            return 2
        print(json.dumps(check, indent=2, ensure_ascii=False))
        print(f"quiescence check recorded ({'CLEAN' if check['clean'] else 'NOT clean'}) "
              f"-> {args.quiescence_state}")
        return 0
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
