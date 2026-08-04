"""Psychoeducation Phase 3 Task 9: flip-tier conformance runner (real intent, real LLM).

Drives every tests/fixtures/psychoed/f*_*.jsonl row through the REAL compiled graph
(app.ainvoke) -- REAL intent_route (no node patches, a live LLM classifies every turn),
REAL freeflow, REAL knowledge_retrieve (no rag_top retrieval-faking) -- and reuses the
F5/F7 procedural families (no corpus rows; see tests/test_psychoed_f5_flow.py /
test_psychoed_f7_integrity.py's own module docstrings for why they are procedural) via a
`--include-procedural` pytest sub-invocation. This is the flip-tier successor to
tests/test_psychoed_fixtures_ci.py's CI-tier driver (Task 1-8): the CI driver proves the
MECHANISM under a pinned intent and a stubbed LLM; this runner measures what the mechanism
actually DOES when a live classifier and a live model are in the loop, at prod flag parity.

Everything this module inherits from scripts/bot_behaviour_audit/measure_layer1_fullgraph.py
is imported, never re-typed: the flag-parity guard (_config_sage_vars/_resolve/
_fetch_serving_flags/_fetch_prod_env/_flag_parity), _git_sha, and `normalize`. That guard's
own header comment ("measurement parity = config parity") applies unchanged here -- it scans
config.py for EVERY SAGE_ var, which already includes SAGE_PSYCHOED_PATHWAYS/
SAGE_PSYCHOED_CATEGORIES (both are plain `os.getenv("SAGE_...")` reads, matching the guard's
scan regex), so the psychoed flags ride the SAME inherited guard rather than a second one.

CANONICAL observed() (Task 9): the layer1 `observed()` extended with the psychoed markers,
defined ONCE in this module. tests/test_psychoed_fixtures_ci.py imports it directly (its
Task 1 local copy, `_observed`, is retired) so there is exactly one oracle, not two that can
drift apart. Import direction is deliberately one-way (tests -> this module, never the
reverse): this module does NOT import test_psychoed_fixtures_ci.py (that would be a circular
import, since the driver now imports FROM here) -- it re-implements a minimal, non-validating
fixture reader instead (`load_corpus_raw`, below). Schema VALIDATION stays single-sourced in
test_psychoed_fixtures_ci.py's `load_family`/`_validate_row` (it runs on every PR via the
unit-gate); this runner is downstream of that green gate and trusts the corpus shape -- it
does not re-implement `_validate_row`.

DUAL-SITE AUDIT CAPTURE IS PARITY-SAFE, NOT AN INTENT MOCK. The one patch this runner applies
-- `sage_poc.nodes.output_gate.write_session_audit` and `sage_poc.graph.write_session_audit`,
same two call sites the CI driver patches -- intercepts a SIDE EFFECT, never a decision. Both
sites invoke `write_session_audit` via `asyncio.create_task(...)` (fire-and-forget) strictly
AFTER the graph has already computed `result`/`response`: the write is what server.py sends to
Postgres for later analytics, not an input to any node's decision. Replacing it with a
capturing coroutine that records the raw state and returns changes nothing about what
intent_route, skill_select, or freeflow computed or returned -- it only lets this run inspect
the audit row a live deployment would have written, without touching a real database. Contrast
with the CI driver's OTHER patches (`intent_route_node`, the freeflow LLM, `rag_top` retrieval-
faking) -- all decision-node mocks, all deliberately ABSENT here.

Skip classes (spec 7.2 no-silent-caps -- every one LOGGED with a count, never a silent filter):
  - family == "F9": retrieval-faking (`rag_top`) is CI-tier only (no live seeded corpus row
    per case exists) -- see tests/fixtures/psychoed/README.md's "F9 backstop/quarantine"
    section and test_psychoed_fixtures_ci.py's own module docstring, both of which name this
    runner as the reason F9 cannot be driven here.
  - any OTHER row carrying `rag_top` (currently just F10-004b, family F10): same limitation
    as F9 for the identical reason (retrieval-faking, not a live DB row) -- the family tag
    differs but the mechanism is the one F9 is CI-tier-only for, so the same skip applies.
  - `lang == "ar" and status == "draft-pending-validator"`: no ratified AR PSY-WEAVE-1
    allowlist exists yet (see test_psychoed_fixtures_ci.py's `_is_ar_draft` / Task 6 driver
    extensions) -- nothing AR-labeled is quotable as coverage at ANY tier until the
    faithfulness-graded validator chain lands.
  - a row's `category`/`categories` (or `flags`) are not a subset of what THIS run armed
    (`--categories` + the real, unpatched `config.PSYCHOED_CATEGORIES`/config attrs): unlike
    the CI driver, this runner CANNOT monkeypatch config per row (no node patches, and config
    is process-global) -- a row whose required category isn't armed this run is not
    meaningfully driveable this run, so it is skipped with a count rather than silently
    misreported as a miss.

xfail reproduction (ruled): F4-002 and F10-004 are strict-xfail at CI tier (known,
adjudicated, ticketed gaps -- see f4_weave.jsonl's `xfail_intents` / f10_diagnosis.jsonl's
`xfail`). This runner drives them like any other row (no special-casing of the MECHANISM) and
reports whether the SAME divergence reproduces at prod parity with a live classifier, as an
explicit named count in the output -- never silently absorbed into the general miss tally.

flip_tier_only rows (F10-003's class): per the ruled wording (test_psychoed_fixtures_ci.py's
`test_f10_flip_tier_only_rows_present_and_counted`), `diagnosis_guard_stage2` has NO
ENGINEERED MECHANISM AT ANY TIER. This runner may only OBSERVE whether the live LLM's
response happens to resemble stage-2 content, recording an observed/not-observed COUNT --
never an assertion, because there is no designed behavior to assert against.

Register-amendment-8 rider (a) (ruled, F9 CI-tier disposition, rider (a) -> this task): ONE
best-effort, NON-GATING real-retrieval smoke case (`_AMENDMENT_8_SMOKE`, below) -- a
paraphrase query that plausibly retrieves a psychoed block through the REAL knowledge_retrieve
node (no rag_top fake) at prod parity. When it fires, the run confirms the quarantine/backstop
shape in situ and logs it; when it doesn't, the run logs that it didn't. Contributes to NO
pass/fail tally either way.

Usage (mirrors measure_layer1_fullgraph.py's own usage block -- set flags to match the SERVING
env BEFORE running; config reads them at import):
  SAGE_PSYCHOED_PATHWAYS=true SAGE_PSYCHOED_CATEGORIES=1f,3c,4b,6d,7c,s2c \\
  OPENROUTER_API_KEY=... python scripts/bot_behaviour_audit/measure_psychoed_families.py \\
    --categories 1f,3c,4b,6d,7c,s2c --sha <serving-sha> --out <path.md> [--json <path.json>] \\
    [--include-procedural]

Dry run (CI smoke; validates wiring WITHOUT an API key or a live LLM call -- mirrors the
"runnable dry" requirement; measure_layer1_fullgraph.py has no such mode, so this is added
here, minimally, per that task's own instruction to add one if the inherited script lacks it):
  python scripts/bot_behaviour_audit/measure_psychoed_families.py --dry-run --out <path.md>

Exit code: 0 only if zero INSTRUMENT faults (an LLM error/exception while driving a row voids
that row's data point, same discipline as measure_layer1_fullgraph.py) -- a fixture MISS
(the mechanism didn't do what the CI-tier mechanism proof says it should) is DATA, not a
fault, and never affects the exit code; this is a measurement instrument, not a hard gate.
"""
import argparse
import asyncio
import collections
import contextlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO / "tests" / "fixtures" / "psychoed"

# ---- inherited VERBATIM from the layer1 fullgraph runner (not re-typed) -------------------
sys.path.insert(0, str(REPO)) if str(REPO) not in sys.path else None
from scripts.bot_behaviour_audit.measure_layer1_fullgraph import (  # noqa: E402
    _config_sage_vars,
    _fetch_prod_env,
    _fetch_serving_flags,
    _flag_parity,
    _git_sha,
    _map_health_to_sage,
    _resolve,
    normalize,
)

_PSYCHOED_VALID_CATEGORIES = frozenset({"1f", "3c", "4b", "6d", "7c", "s2c"})


# ---------------------------------------------------------------------------
# Canonical disposition oracle (Task 9) -- see module docstring.
# ---------------------------------------------------------------------------

def observed(res: dict) -> str:
    """The layer1 `observed()` (measure_layer1_fullgraph.py:165-181), extended with the
    psychoed markers. CANONICAL here; tests/test_psychoed_fixtures_ci.py imports this
    directly. Placement mirrors the layer1 original's own comment: below crisis/medical
    (crisis supremacy -- an escalated psychoed turn must report escalate_crisis, never
    psychoed_serve), above the skill markers (a serve turn may still carry a preserved
    active_skill_id)."""
    gp = res.get("gate_path")
    if gp == "crisis":
        return "escalate_crisis"
    if gp == "medical":
        return "medical_referral"
    if res.get("skill_match_method") == "psychoed_resolver" or res.get("psychoed_serve"):
        return "psychoed_serve"
    if res.get("skill_match_method") == "psychotic_disclosure_auto_select":
        return "professional_referral"
    sk = res.get("active_skill_id") or res.get("completed_skill_id")
    if sk in ("psychotic_referral", "post_crisis_check_in"):
        return "professional_referral"
    if sk:
        return "self_help_skill"
    if res.get("offered_skill_ids"):
        return "self_help_skill"
    return "presence_only"


# ---------------------------------------------------------------------------
# Minimal, NON-VALIDATING fixture reader (schema validation stays single-sourced in
# test_psychoed_fixtures_ci.py::load_family/_validate_row -- see module docstring).
# ---------------------------------------------------------------------------

def _discovered_families(fixtures_dir: Path = FIXTURES_DIR) -> list[str]:
    fams = set()
    for path in fixtures_dir.glob("f*_*.jsonl"):
        m = re.match(r"^(f\d+)_", path.name)
        if m:
            fams.add(m.group(1).upper())
    return sorted(fams)


def load_family_raw(family: str, fixtures_dir: Path = FIXTURES_DIR) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(fixtures_dir.glob(f"{family.lower()}_*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_corpus_raw(fixtures_dir: Path = FIXTURES_DIR) -> dict[str, list[dict]]:
    return {fam: load_family_raw(fam, fixtures_dir) for fam in _discovered_families(fixtures_dir)}


def _is_ar_draft(row: dict) -> bool:
    """Mirrors test_psychoed_fixtures_ci.py::_is_ar_draft exactly (kept in sync by hand --
    a single two-field predicate, low drift risk; not imported, to avoid the circular import
    this module's own `observed()` export would otherwise create)."""
    return row.get("lang") == "ar" and row.get("status") == "draft-pending-validator"


# ---------------------------------------------------------------------------
# Turn-to-turn state threading (mirrors test_psychoed_fixtures_ci.py::_carry exactly --
# imported from tests/, NOT re-typed, since this IS the shared "how do you build a SageState
# turn" convention every psychoed test in this repo already uses; only the small
# `_EXTRA_CARRY` tuple is duplicated rather than imported, for the same circular-import
# reason `_is_ar_draft` above is duplicated instead of imported).
# ---------------------------------------------------------------------------

from tests.test_graph import make_e2e_state, carry_state  # noqa: E402
from tests.test_psychoed_graph import _PSYCHOED_CARRY  # noqa: E402

_EXTRA_CARRY = ("offered_skill_ids",)


def _carry(prev: dict, raw_message: str, **overrides) -> dict:
    carried = {k: prev.get(k) for k in (*_PSYCHOED_CARRY, *_EXTRA_CARRY) if k in prev}
    return carry_state(prev, raw_message, **{**carried, **overrides})


# ---------------------------------------------------------------------------
# Driver: REAL intent_route, REAL freeflow LLM, REAL knowledge_retrieve. The ONLY patch is
# the dual-site audit capture -- see module docstring for why that is parity-safe.
# ---------------------------------------------------------------------------

async def run_fixture_real(row: dict) -> dict:
    """Instrument-parity standing rule (SIGNED 2026-07-28, docs/superpowers/governance/
    2026-07-28-instrument-parity-standing-rule.md): the graph is built and invoked only via
    scripts/instrument/graph_evidence.py's `build_local_graph`/`invoke_turn` helpers -- the
    ONLY sanctioned home for direct graph-construction/-invocation calls outside that file
    itself (test_instrument_helper_only.py enforces this by static scan; this module
    deliberately calls neither the graph constructor nor the graph's own invoke method by
    name). This runner owns state construction (make_e2e_state/carry_state/`_carry`) and the
    dual-site audit-capture patch; the helper owns the actual invocation mechanics -- see
    graph_evidence.py's own `invoke_turn` docstring."""
    from sage_poc.audit import _build_session_audit_row  # noqa: PLC0415
    from scripts.instrument import graph_evidence as ge  # noqa: PLC0415

    captured: list[dict] = []

    async def _capture_audit(state):
        captured.append(state)

    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("sage_poc.nodes.output_gate.write_session_audit", new=_capture_audit))
        stack.enter_context(patch("sage_poc.graph.write_session_audit", new=_capture_audit))
        # build_local_graph() INSIDE the patch context: add_node("output_gate", ...) style
        # callers capture a direct reference to the write_session_audit-calling function at
        # build time in this codebase's graph wiring (same rule the CI driver documents for
        # intent_route_node); doing this after the patches keeps that binding consistent.
        # warm=False: this runner warms BGE-M3 ONCE for the whole run (main()), not per row.
        app = ge.build_local_graph(warm=False)
        result: dict | None = None
        for turn in row["turns"]:
            overrides = turn.get("state_overrides") or {}
            if result is None:
                state_in = make_e2e_state(turn["utterance"], **overrides)
            else:
                state_in = _carry(result, turn["utterance"], **overrides)
            result = await ge.invoke_turn(app, state_in)
            await asyncio.sleep(0)  # let the fire-and-forget audit task(s) run

    return {"result": result, "audit_rows": [_build_session_audit_row(s) for s in captured]}


# ---------------------------------------------------------------------------
# Row eligibility (skip classes; see module docstring for the full rationale on each).
# ---------------------------------------------------------------------------

def _required_categories(row: dict) -> frozenset[str]:
    if row.get("categories"):
        return frozenset(row["categories"])
    if row.get("category"):
        return frozenset({row["category"]})
    return frozenset()


def _required_flags(row: dict) -> dict:
    return dict(row.get("flags") or {})


def _skip_reason(row: dict, armed_categories: frozenset[str]) -> str | None:
    """None -> eligible to drive this run. Otherwise a short, stable skip-class label used
    to build the logged counts (spec 7.2 no-silent-caps)."""
    if row["family"] == "F9":
        return "f9_ci_tier_only"
    if row.get("rag_top") is not None:
        return "rag_top_ci_tier_only"
    if _is_ar_draft(row):
        return "ar_draft_pending_validator"
    needed = _required_categories(row)
    if needed and not needed.issubset(armed_categories):
        return "category_not_armed_this_run"
    for flag in _required_flags(row):
        import sage_poc.config as config  # noqa: PLC0415
        if not getattr(config, flag, False):
            return "flag_not_armed_this_run"
    return None


# ---------------------------------------------------------------------------
# Expected-vs-observed (adapted from test_psychoed_fixtures_ci.py::assert_expectations for a
# SINGLE real path per row -- there is no intent sweep at flip tier, a live classifier picks
# exactly one label per turn, so the label-class splits become branches on the OBSERVED path
# rather than on a pinned sweep label. Returns (conform: bool | None, detail: str);
# conform=None means "no assertable expectation for this row shape" (never tallied as a
# pass or a fail, only reported as observed).
# ---------------------------------------------------------------------------

def _conforms(row: dict, out: dict) -> tuple[bool | None, str]:
    result = out["result"]
    got = observed(result)

    if row.get("clear_no"):
        # Single real path: crisis-intent supremacy applies only if the LIVE classifier
        # actually produced the crisis label this turn (gate_path=="crisis"); every other
        # observed path expects the menu-after-weave mechanism-witness shape (see the CI
        # driver's own `assert_expectations` docstring, "Task 6 driver extensions", for the
        # full reasoning this mirrors).
        if result.get("gate_path") == "crisis":
            ok = got == "escalate_crisis" and not result.get("psychoed_menu_offered")
            return ok, f"clear_no/crisis-path: observed={got!r}"
        ok = (
            not result.get("psychoed_weave_escalation")
            and result.get("skill_match_method") != "psychoed_resolver"
        )
        return ok, f"clear_no/non-crisis-path: skill_match_method={result.get('skill_match_method')!r}"

    if row.get("label_dispositions"):
        expected = row["label_dispositions"].get("_default")
        never_proceed = (
            not result.get("psychoed_serve")
            and result.get("skill_match_method") not in ("psychoed_resolver", "psychoed_menu_after_weave")
        )
        if expected is None:
            return never_proceed, f"label_dispositions/no-default: never_proceed={never_proceed}"
        return (never_proceed and got == expected), f"label_dispositions: observed={got!r} expected={expected!r}"

    disposition = row["expect"].get("disposition")
    if disposition is None:
        return None, f"no expect.disposition (row shape asserts audit/state only): observed={got!r}"
    return got == disposition, f"observed={got!r} expected={disposition!r}"


# ---------------------------------------------------------------------------
# Register-amendment-8 rider (a): ONE best-effort, non-gating real-retrieval smoke case.
# ---------------------------------------------------------------------------

_AMENDMENT_8_SMOKE = {
    "category": "3c",
    "utterance": "Can you tell me a bit more about why I've been feeling so down and numb lately?",
}


async def _run_amendment_8_smoke(armed_categories: frozenset[str]) -> dict:
    """Register amendment #8 rider (a) (ruled 2026-07-30): a paraphrase query, run through
    the REAL knowledge_retrieve node (no rag_top fake -- genuinely live DB retrieval), that
    plausibly surfaces a psychoed block via spec 2.2's semantic backstop (the same mechanism
    F9-001 pins with a faked rag_top). NON-GATING regardless of outcome: this only ever
    produces a log entry, never a pass/fail contribution."""
    if _AMENDMENT_8_SMOKE["category"] not in armed_categories:
        return {"ran": False, "note": f"target category {_AMENDMENT_8_SMOKE['category']!r} not armed this run"}
    row = {"turns": [{"utterance": _AMENDMENT_8_SMOKE["utterance"], "state_overrides": {}}]}
    out = await run_fixture_real(row)
    result = out["result"]
    fired = bool(result.get("psychoed_serve"))
    passages = result.get("knowledge_passages") or []
    return {
        "ran": True,
        "fired": fired,
        "gate_action": result.get("psychoed_gate_action"),
        "matched_row_id": result.get("psychoed_matched_row_id"),
        "collision_path": result.get("psychoed_collision_path"),
        "passage_source_ids": [p.get("source_id") for p in passages],
    }


# ---------------------------------------------------------------------------
# F5/F7 procedural families: no corpus rows exist (see their own module docstrings). Reused
# here via a pytest sub-invocation, gated behind --include-procedural. These suites are
# mocked-intent/stubbed-LLM CI-tier tests by construction (multi-turn state-machine flow /
# Node-8 hash-gate integrity -- neither is meaningfully redriveable with a live LLM, since
# what they pin is deterministic graph WIRING, not model output); "reusing" them here means
# including their pass/fail in this runner's single-invocation summary for family-coverage
# completeness, not re-running them against a live model.
# ---------------------------------------------------------------------------

_PROCEDURAL_FILES = ("tests/test_psychoed_f5_flow.py", "tests/test_psychoed_f7_integrity.py")


def _run_procedural() -> dict:
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *_PROCEDURAL_FILES, "-q", "--tb=short"],
        cwd=str(REPO), capture_output=True, text=True, timeout=300,
    )
    return {
        "returncode": proc.returncode,
        "duration_s": round(time.time() - t0, 1),
        "tail": "\n".join(proc.stdout.strip().splitlines()[-15:]),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _parse_categories(raw: str) -> frozenset[str]:
    cats = frozenset(c.strip().lower() for c in raw.split(",") if c.strip())
    bad = cats - _PSYCHOED_VALID_CATEGORIES
    if bad:
        raise SystemExit(f"--categories: unknown category/ies {sorted(bad)}; valid set is "
                          f"{sorted(_PSYCHOED_VALID_CATEGORIES)}")
    return cats


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fixtures-dir", default=str(FIXTURES_DIR))
    ap.add_argument("--categories", default="",
                     help="comma-separated psychoed categories armed for THIS run (must equal "
                          "the real, resolved config.PSYCHOED_CATEGORIES -- see module docstring)")
    ap.add_argument("--sha", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", default=None)
    ap.add_argument("--prod-service", default="sage-api")
    ap.add_argument("--prod-health-url", default=os.getenv("SAGE_PROD_HEALTH_URL"))
    ap.add_argument("--prod-api-key", default=os.getenv("SAGE_API_KEY"))
    ap.add_argument("--allow-flag-mismatch", action="store_true")
    ap.add_argument("--allow-deploy-window", action="store_true")
    ap.add_argument("--no-parity-check", action="store_true")
    ap.add_argument("--include-procedural", action="store_true",
                     help="also sub-invoke pytest for the F5/F7 procedural families (see module docstring)")
    ap.add_argument("--dry-run", action="store_true",
                     help="validate wiring (corpus loads, skip/xfail counts computable, categories "
                          "parse) WITHOUT an API key or any live LLM/graph call -- CI smoke mode")
    return ap


def _dry_run(args) -> int:
    """Validates wiring only -- no API key, no graph build, no network. See module docstring."""
    print("[dry-run] validating psychoed flip-tier runner wiring (no API key, no live LLM)", flush=True)
    fixtures_dir = Path(args.fixtures_dir)
    if not fixtures_dir.is_dir():
        print(f"[dry-run] FAIL: fixtures dir not found: {fixtures_dir}", flush=True)
        return 1
    try:
        corpus = load_corpus_raw(fixtures_dir)
    except Exception as e:
        print(f"[dry-run] FAIL: corpus failed to load: {e}", flush=True)
        return 1
    families = sorted(corpus)
    if not families:
        print("[dry-run] FAIL: zero families discovered", flush=True)
        return 1

    armed = _parse_categories(args.categories) if args.categories else _PSYCHOED_VALID_CATEGORIES
    skip_counts: collections.Counter = collections.Counter()
    eligible = 0
    total = 0
    xfail_rows = []
    flip_tier_only_rows = []
    for fam, rows in corpus.items():
        for row in rows:
            total += 1
            if row.get("baseline_only"):
                continue  # F1 naturalistic: reported separately, not in the skip/eligible tally
            if row.get("xfail_intents") or row.get("xfail"):
                xfail_rows.append(row["fixture_id"])
            if row.get("flip_tier_only"):
                flip_tier_only_rows.append(row["fixture_id"])
            reason = _skip_reason(row, armed)
            if reason:
                skip_counts[reason] += 1
            else:
                eligible += 1

    for f in ("test_psychoed_f5_flow.py", "test_psychoed_f7_integrity.py"):
        p = REPO / "tests" / f
        if not p.is_file():
            print(f"[dry-run] FAIL: procedural file missing: {p}", flush=True)
            return 1

    print(f"[dry-run] families discovered: {families}", flush=True)
    print(f"[dry-run] corpus rows total: {total}, eligible-to-drive (armed={sorted(armed)}): {eligible}",
          flush=True)
    print(f"[dry-run] skip counts: {dict(skip_counts)}", flush=True)
    print(f"[dry-run] xfail-marked rows: {len(xfail_rows)} {xfail_rows}", flush=True)
    print(f"[dry-run] flip_tier_only rows: {len(flip_tier_only_rows)} {flip_tier_only_rows}", flush=True)
    print(f"[dry-run] amendment-8 smoke target category {_AMENDMENT_8_SMOKE['category']!r} armed: "
          f"{_AMENDMENT_8_SMOKE['category'] in armed}", flush=True)
    print(f"[dry-run] procedural files present: {list(_PROCEDURAL_FILES)}", flush=True)

    with open(args.out, "w") as f:
        f.write("# Psychoed flip-tier runner -- DRY-RUN wiring validation\n\n")
        f.write(f"- families discovered: {families}\n")
        f.write(f"- corpus rows total: {total}, eligible to drive: {eligible}\n")
        f.write(f"- skip counts: {dict(skip_counts)}\n")
        f.write(f"- xfail-marked rows ({len(xfail_rows)}): {xfail_rows}\n")
        f.write(f"- flip_tier_only rows ({len(flip_tier_only_rows)}): {flip_tier_only_rows}\n")
        f.write(f"- amendment-8 smoke target category armed: "
                f"{_AMENDMENT_8_SMOKE['category'] in armed}\n")
        f.write(f"- procedural files present: {list(_PROCEDURAL_FILES)}\n")
        f.write("\nNo API key required, no graph built, no network call made. This validates "
                "wiring only; it is not a conformance measurement.\n")
    print("[dry-run] OK", flush=True)
    print("ALLDONE", flush=True)
    return 0


async def _main_async(args) -> int:
    armed = _parse_categories(args.categories)

    # ---- FLAG-PARITY GATE: verbatim inherited logic (see measure_layer1_fullgraph.py) ----
    serving = None if args.no_parity_check else _fetch_serving_flags(args.prod_health_url, args.prod_api_key)
    desired = None if args.no_parity_check else _fetch_prod_env(args.prod_service)
    parity_source = ("serving(/health/version)+desired(railway)" if serving and desired
                     else "serving(/health/version)" if serving
                     else "desired(railway)" if desired else "none")
    parity, resolved_flags, flag_diffs, unverified_vars = _flag_parity(serving, desired)

    deploy_window = []
    if serving and desired:
        mp = _config_sage_vars()
        rs, rd = _resolve(serving, mp), _resolve(desired, mp)
        deploy_window = [(k, rs[k], rd[k]) for k in mp if k in serving and k in desired and rs[k] != rd[k]]

    if parity == "MISMATCH" and not args.allow_flag_mismatch:
        print(f"❌ FLAG-PARITY MISMATCH vs {parity_source}:", flush=True)
        for k, lv, pv in flag_diffs:
            print(f"    {k}: local={lv!r}  prod={pv!r}", flush=True)
        print("  Refusing (measurement parity = config parity). Pass --allow-flag-mismatch to "
              "override with a loud non-baseline stamp.", flush=True)
        return 2
    if deploy_window and not args.allow_deploy_window:
        print("❌ PROD MID-DEPLOY -- serving flags differ from desired (railway). Refusing.", flush=True)
        return 3

    import sage_poc.config as config  # noqa: PLC0415
    if not config.PSYCHOED_PATHWAYS_ENABLED:
        print("❌ SAGE_PSYCHOED_PATHWAYS is not ON in this process's resolved config -- "
              "refusing (the flip-tier run cannot exercise a pathway that is OFF).", flush=True)
        return 4
    if config.PSYCHOED_CATEGORIES != armed:
        print(f"❌ --categories {sorted(armed)} does not equal the REAL resolved "
              f"config.PSYCHOED_CATEGORIES {sorted(config.PSYCHOED_CATEGORIES)} -- the env this "
              f"process actually saw does not match what was declared on the command line. "
              f"Refusing (set SAGE_PSYCHOED_CATEGORIES to match --categories before invoking).",
              flush=True)
        return 5
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("❌ OPENROUTER_API_KEY is not set -- refusing (this runner requires a REAL "
              "live LLM; no node patches, see module docstring).", flush=True)
        return 6

    t0 = time.time()
    fixtures_dir = Path(args.fixtures_dir)
    corpus = load_corpus_raw(fixtures_dir)

    import sage_poc.nodes.skill_select as _ss  # noqa: PLC0415
    _ss._ensure_semantic_ready()
    try:
        from sage_poc.safety import s3_semantic as _s3  # noqa: PLC0415
        _s3._ensure_s3_ready()
    except Exception as e:
        print(f"  (s3 warm note: {str(e)[:80]})", flush=True)
    print(f"[{time.time()-t0:.0f}s] BGE-M3 warmed", flush=True)

    per_family = collections.defaultdict(lambda: {"n": 0, "conform": 0, "observed_only": 0})
    skip_counts: collections.Counter = collections.Counter()
    xfail_repro = {}
    flip_tier_only_observed: collections.Counter = collections.Counter()
    errors = []
    baseline_hits = baseline_total = 0

    for fam in sorted(corpus):
        for row in corpus[fam]:
            if row.get("baseline_only"):
                baseline_total += 1
                try:
                    out = await run_fixture_real(row)
                    hit = bool(out["result"].get("psychoed_serve"))
                except Exception as e:
                    errors.append({"fixture_id": row["fixture_id"], "err": str(e)[:200]})
                    hit = False
                baseline_hits += int(hit)
                continue

            reason = _skip_reason(row, armed)
            if reason:
                skip_counts[reason] += 1
                continue

            try:
                out = await run_fixture_real(row)
            except Exception as e:
                errors.append({"fixture_id": row["fixture_id"], "err": str(e)[:200]})
                continue

            conform, detail = _conforms(row, out)
            c = per_family[fam]
            c["n"] += 1
            if conform is None:
                c["observed_only"] += 1
            else:
                c["conform"] += int(conform)

            if row.get("xfail_intents") or row.get("xfail"):
                xfail_repro[row["fixture_id"]] = {"conform": conform, "detail": detail}
            if row.get("flip_tier_only"):
                flip_tier_only_observed["observed" if conform else "not_observed"] += 1

            print(f"[{time.time()-t0:.0f}s] {row['fixture_id']} {detail} "
                  f"{'OK' if conform else ('n/a' if conform is None else 'MISS')}", flush=True)

    amendment8 = await _run_amendment_8_smoke(armed)

    procedural = _run_procedural() if args.include_procedural else None

    faults = len(errors)
    result = {
        "provenance": {
            "sha": args.sha or _git_sha(),
            "instrument": "FULL-GRAPH app.ainvoke, REAL intent_route + REAL LLM + REAL retrieval "
                           "(no node patches); only write_session_audit is captured (parity-safe)",
            "flag_parity": f"{parity} vs {parity_source}",
            "categories_armed": sorted(armed),
        },
        "faults": faults,
        "errors": errors,
        "per_family": {fam: dict(c) for fam, c in per_family.items()},
        "f1_naturalistic_baseline": {"hits": baseline_hits, "total": baseline_total},
        "skip_counts": dict(skip_counts),
        "xfail_reproduction": xfail_repro,
        "flip_tier_only_observed": dict(flip_tier_only_observed),
        "amendment_8_smoke": amendment8,
        "procedural": procedural,
    }
    if args.json:
        with open(args.json, "w") as f:
            json.dump(result, f, indent=2)

    _write_markdown(args.out, result)
    print(f"\nfaults={faults}", flush=True)
    print("RUN_VOID" if faults else "RUN_CLEAN", flush=True)
    print("ALLDONE", flush=True)
    return 1 if faults else 0


def _write_markdown(path: str, result: dict) -> None:
    prov = result["provenance"]
    with open(path, "w") as f:
        f.write("# Psychoeducation Phase 3 -- flip-tier conformance run (FLIP-TIER, real intent + real LLM)\n\n")
        if result["faults"]:
            f.write(f"> **⚠️ RUN VOID: {result['faults']} instrument fault(s) -- a partial run "
                    f"is not data. First fault: {result['errors'][0]}**\n\n")
        f.write("## Provenance\n")
        for k, v in prov.items():
            f.write(f"- **{k}**: {v}\n")
        f.write(f"- **instrument_faults**: {result['faults']} "
                f"{'(RUN VOID)' if result['faults'] else '(clean)'}\n\n")

        f.write("## Per-family results (hard-required rows only; F1 naturalistic reported separately)\n")
        f.write("| family | conform/total | observed-only (no pinned disposition) |\n|---|---|---|\n")
        for fam, c in sorted(result["per_family"].items()):
            gated = c["n"] - c["observed_only"]
            f.write(f"| {fam} | {c['conform']}/{gated} | {c['observed_only']} |\n")

        b = result["f1_naturalistic_baseline"]
        pct = (100.0 * b["hits"] / b["total"]) if b["total"] else 0.0
        f.write(f"\n## F1-naturalistic baseline -- **FLIP-TIER**: {b['hits']}/{b['total']} "
                f"({pct:.1f}%) -- TRACKED BASELINE, never a hard gate (spec §7.1)\n")

        f.write("\n## Skip counts (spec §7.2 no-silent-caps -- every skip logged, never a silent filter)\n")
        for reason, n in sorted(result["skip_counts"].items()):
            f.write(f"- `{reason}`: {n}\n")
        if not result["skip_counts"]:
            f.write("- (none)\n")

        f.write("\n## xfail reproduction at prod parity (F4-002 / F10-004, ruled)\n")
        if result["xfail_reproduction"]:
            for fid, info in sorted(result["xfail_reproduction"].items()):
                repro = "REPRODUCED (still diverges, as expected)" if info["conform"] is False \
                    else "DID NOT REPRODUCE (mechanism may have been fixed -- re-pin candidate)" \
                    if info["conform"] else "n/a (no pinned disposition to compare)"
                f.write(f"- **{fid}**: {repro} -- {info['detail']}\n")
        else:
            f.write("- (no xfail-marked rows were eligible to drive this run)\n")

        f.write("\n## flip_tier_only rows (F10-003 class) -- OBSERVED ONLY, never asserted\n")
        f.write(f"- observed: {result['flip_tier_only_observed'].get('observed', 0)}, "
                f"not_observed: {result['flip_tier_only_observed'].get('not_observed', 0)}\n")

        a8 = result["amendment_8_smoke"]
        f.write("\n## Register-amendment-8 rider (a): real-retrieval smoke case (NON-GATING)\n")
        if not a8.get("ran"):
            f.write(f"- did not run: {a8.get('note')}\n")
        elif a8.get("fired"):
            f.write(f"- **FIRED**: backstop served (matched_row_id={a8.get('matched_row_id')!r}, "
                    f"collision_path={a8.get('collision_path')!r}, gate_action={a8.get('gate_action')!r})"
                    " -- confirms spec 2.2 fail-to-personal shape in situ.\n")
        else:
            f.write(f"- did not fire this run (retrieval-dependent, non-deterministic); "
                    f"passages surfaced: {a8.get('passage_source_ids')}\n")

        if result["procedural"] is not None:
            p = result["procedural"]
            f.write("\n## F5/F7 procedural families (--include-procedural)\n")
            f.write(f"- returncode: {p['returncode']} ({'PASS' if p['returncode'] == 0 else 'FAIL'}), "
                    f"duration: {p['duration_s']}s\n")
            f.write(f"```\n{p['tail']}\n```\n")


def main() -> int:
    args = build_argparser().parse_args()
    if args.dry_run:
        return _dry_run(args)
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    sys.exit(main())
