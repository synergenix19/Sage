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

SIX-SITE AUDIT CAPTURE IS PARITY-SAFE, NOT AN INTENT MOCK. `write_session_audit` is imported
into SIX distinct module namespaces across src/sage_poc/ (`_AUDIT_PATCH_TARGETS`, below) --
the CI driver's own two (`sage_poc.graph`, the Node-1 crisis short-circuit;
`sage_poc.nodes.output_gate`, normal turn-close) plus FOUR terminal response nodes that bypass
output_gate entirely (`derealization_response.py`, `medical_response.py`,
`high_risk_response.py`, `screen_response.py`). An earlier version of this file patched only
the CI driver's two sites -- a review finding (task-9-review.md, "(c) Audit-write exposure")
caught that this runner drives the REAL, unpatched intent_route with a live LLM, so a
fixture's real-time classification can land on ANY of the six, and the other four would POST a
real `session_audit` row to prod Supabase whenever credentials are configured in-process
(which Task 10's live run necessarily has). `_assert_audit_patch_coverage_complete()` runs
before every row is driven and fails loudly if a future node addition introduces a SEVENTH
site this list doesn't cover -- the coverage claim is enforced, not merely asserted in prose.
Every site invokes `write_session_audit` via `asyncio.create_task(...)` (fire-and-forget)
strictly AFTER the graph has already computed `result`/`response`: the write is what a live
deployment sends to Postgres for later analytics, not an input to any node's decision.
Replacing it with a capturing coroutine that records the raw state and returns changes nothing
about what intent_route, skill_select, freeflow, or any terminal node computed or returned --
it only lets this run inspect the audit row a live deployment would have written, without
touching a real database. Contrast with the CI driver's OTHER patches (`intent_route_node`,
the freeflow LLM, `rag_top` retrieval-faking) -- all decision-node mocks, all deliberately
ABSENT here.

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

FULL expect.audit/expect.state assertion (Task 9 fix round 4, controller-observed live-run
finding): every row's `expect.audit`/`expect.state` subsets are checked via `_assert_subset`
(imports, does not reimplement, test_psychoed_fixtures_ci.py's own `_subset_match`) -- not
just `expect.disposition`. `_real_label`/`_mechanism_applies` capture what the REAL graph
actually decided this turn (Node-1's own deterministic crisis intercept, or the live
classifier's own `primary_intent`) and mirror the CI driver's `WEAVE_EVALUATOR_LABELS` split
against it, so a row's mechanism-witness assertions only apply on labels that actually reach
the code path they describe -- exactly as at CI tier, just keyed on the REAL label instead of
a pinned sweep label.

xfail reproduction (ruled): F4-002 and F10-004 are strict-xfail at CI tier (known,
adjudicated, ticketed gaps -- see f4_weave.jsonl's `xfail_intents` / f10_diagnosis.jsonl's
`xfail`). This runner drives them like any other row (no special-casing of the MECHANISM) and
reports whether the SAME divergence reproduces at prod parity with a live classifier, as an
explicit named count in the output -- never silently absorbed into the general miss tally. As
of fix round 4, this reproduction is MEANINGFUL (the actual audit/state divergence, not just
"n/a (no pinned disposition to compare)") now that expect.audit/expect.state are asserted.

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
pass/fail tally either way. RETRIEVAL HONESTY (Task 9 fix round 4): this smoke case can only
genuinely fire when retrieval is ACTIVE -- see `_bootstrap_retrieval_pool` below, which
bootstraps a real (read-only) DB pool when `DATABASE_URL` is present and stamps an honest
"UNAVAILABLE" provenance line when it is not, rather than silently driving every row with
retrieval structurally abstaining while the output claims "REAL retrieval."

Usage (mirrors measure_layer1_fullgraph.py's own usage block -- set flags to match the SERVING
env BEFORE running; config reads them at import). `--live` is REQUIRED for a real run --
without it, this refuses before touching the network or the graph (undefeatable-live-mode-gate,
see the module-level safety-snapshot comment near the top of this file):
  SAGE_PSYCHOED_PATHWAYS=true SAGE_PSYCHOED_CATEGORIES=1f,3c,4b,6d,7c,s2c \\
  OPENROUTER_API_KEY=... python scripts/bot_behaviour_audit/measure_psychoed_families.py \\
    --live --categories 1f,3c,4b,6d,7c,s2c --sha <serving-sha> --out <path.md> \\
    [--json <path.json>] [--include-procedural]

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
import uuid
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# SAFETY SNAPSHOT -- fixes a disclosed Task-9 incident (task-9-review.md, "(a) No-key
# refusal: STILL DEFEATABLE"). MUST stay the first executable statement after the stdlib
# imports above, BEFORE any import below that could transitively import sage_poc.config.
#
# The incident: sage_poc/config.py calls bare `load_dotenv()` at module import time.
# python-dotenv's default `find_dotenv()` walks UP parent directories looking for a `.env`;
# `override=False` only refuses to clobber a var ALREADY PRESENT in os.environ, so a var an
# operator explicitly unset (`env -u OPENROUTER_API_KEY ...`) is *absent*, not merely empty,
# and dotenv freely (re-)injects it from any discoverable parent `.env`. A key-presence check
# placed AFTER `sage_poc.config` has already been imported (as this file's first version did,
# and as measure_layer1_fullgraph.py's own guard still does) observes the RE-INJECTED value
# and is silently defeated -- reproduced live during Task 9's own verification AND
# independently by the reviewer (`env -u OPENROUTER_API_KEY python -c "import
# sage_poc.config"` shows the var reappear, with zero graph/LLM involvement).
#
# Fix (two independent layers, per the reviewer's "or both"): (1) live mode requires the
# explicit --live flag, checked in main() -- a .env file cannot forge a CLI argument, so an
# operator who did not deliberately type --live can never reach the live path regardless of
# what any .env anywhere up the tree contains; (2) this snapshot, taken here (before the
# import below that is THIS module's own trigger for sage_poc.config's load_dotenv()),
# reflects the process's OWN environment at interpreter start -- immune to dotenv injection,
# because dotenv has not run yet at this line. main() requires BOTH before ever calling
# asyncio.run(_main_async(...)).
_PRE_IMPORT_ENV_HAD_OPENROUTER_KEY = "OPENROUTER_API_KEY" in os.environ

REPO = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO / "tests" / "fixtures" / "psychoed"

# ---- inherited VERBATIM from the layer1 fullgraph runner (not re-typed) -- THIS is the
# import that transitively triggers sage_poc.config's load_dotenv() (measure_layer1_
# fullgraph.py's own top level does `from sage_poc import config as _c`) -- everything above
# this line must never import anything sage_poc-rooted. -------------------------------------
sys.path.insert(0, str(REPO)) if str(REPO) not in sys.path else None
from scripts.bot_behaviour_audit.measure_layer1_fullgraph import (  # noqa: E402
    _config_sage_vars,
    _fetch_prod_env,
    _fetch_serving_flags,
    _flag_parity,
    _git_sha,
    _resolve,
    normalize,
)

_PSYCHOED_VALID_CATEGORIES = frozenset({"1f", "3c", "4b", "6d", "7c", "s2c"})

# ---------------------------------------------------------------------------
# Psychoed arming = this run's DECLARED DELTA, not a parity violation (Task 9 fix round 2,
# controller-observed deadlock at Task 10's live checkpoint -- see task-9-report.md for the
# full incident). Prod currently serves the psychoed pathway OFF (pre-flip): the inherited,
# GENERIC _flag_parity() guard (measure_layer1_fullgraph.py, shared unmodified with the layer1
# conformance matrix, which has no declared-delta concept and must keep comparing every var
# unconditionally) would refuse on exactly SAGE_PSYCHOED_PATHWAYS/SAGE_PSYCHOED_CATEGORIES the
# moment this runner arms them ON -- deadlocking against this runner's OWN, independent
# PSYCHOED_PATHWAYS_ENABLED/PSYCHOED_CATEGORIES checks below, which demand the opposite. The
# ONLY built-in escape, --allow-flag-mismatch, is a GENERIC override that stamps the WHOLE run
# non-baseline and would silently tolerate a mismatch in any of the ~17 OTHER SAGE_ vars too --
# unacceptable for a §7.3 record run, which needs parity on everything EXCEPT the two vars this
# run exists to measure the un-flipped mechanism under.
#
# Fix: `_carve_out_declared_delta` (below) removes ONLY these two named vars from the diff set
# _flag_parity() already computed, then recomputes the verdict from what remains. PARITY-SAFE
# because the carve-out is a fixed, exactly-two-name set applied AFTER the full inherited scan
# has already run (it does not skip or narrow that scan) -- a mismatch on ANY other SAGE_ var
# still hard-refuses exactly as before the fix (see the safety-test file's
# `test_carve_out_is_exactly_two_vars_other_mismatches_still_refuse`). The two carved vars are
# instead validated by this runner's OWN explicit expectations immediately below (pathway ON;
# resolved PSYCHOED_CATEGORIES == --categories) -- so they are never left unchecked, only
# checked against a DIFFERENT, run-specific baseline (the declared delta) instead of prod's.
_PSYCHOED_DECLARED_DELTA_VARS = frozenset({"SAGE_PSYCHOED_PATHWAYS", "SAGE_PSYCHOED_CATEGORIES"})


def _carve_out_declared_delta(flag_diffs: list, unverified_vars: list):
    """Removes `_PSYCHOED_DECLARED_DELTA_VARS` from flag_diffs/unverified_vars and recomputes
    the parity verdict from what remains. Returns (verdict, filtered_diffs,
    filtered_unverified, carved_diffs) -- carved_diffs (the entries removed, each
    `(var, local, prod)`) feeds the output doc's honest delta stamp, so the record states
    plainly what prod actually serves vs what this run armed, never hides it."""
    carved = [d for d in flag_diffs if d[0] in _PSYCHOED_DECLARED_DELTA_VARS]
    filtered_diffs = [d for d in flag_diffs if d[0] not in _PSYCHOED_DECLARED_DELTA_VARS]
    filtered_unverified = [v for v in unverified_vars if v not in _PSYCHOED_DECLARED_DELTA_VARS]
    if filtered_diffs:
        verdict = "MISMATCH"
    elif filtered_unverified:
        verdict = "VERIFIED_PARTIAL"
    else:
        verdict = "VERIFIED"
    return verdict, filtered_diffs, filtered_unverified, carved


def _psychoed_delta_stamp(carved_diffs: list, resolved_flags: dict, armed: frozenset[str]) -> str:
    """The honest 'declared delta' line for the output doc (ruled: must be prominent). Reads
    what PROD actually serves for the two carved vars from `carved_diffs` when they diverged
    from local; when they did NOT diverge (local already equals prod -- e.g. a post-flip
    parity run, or a rare local coincidence), falls back to `resolved_flags` (which then holds
    the SAME value on both sides by construction of "no diff"), so the stamp is always present
    and always accurate, never conditional on a diff having fired."""
    prod_vals = {var: prod for var, _local, prod in carved_diffs}
    prod_pathways = prod_vals.get("SAGE_PSYCHOED_PATHWAYS", resolved_flags.get("SAGE_PSYCHOED_PATHWAYS"))
    prod_categories = prod_vals.get("SAGE_PSYCHOED_CATEGORIES", resolved_flags.get("SAGE_PSYCHOED_CATEGORIES"))
    prod_on = str(prod_pathways).strip().lower() == "true"
    armed_str = ",".join(sorted(armed))
    if prod_on and str(prod_categories or "") == armed_str:
        return (f"PROD SERVES: psychoed ON ({prod_categories}) -- THIS RUN ARMS THE SAME SET. "
                f"No declared delta this run; full parity including psychoed.")
    return (
        f"PROD SERVES: psychoed {'ON' if prod_on else 'OFF'}"
        f"{f' ({prod_categories})' if prod_on else ''}. THIS RUN ARMS: {armed_str} -- "
        f"flip-tier measurement of the UNFLIPPED mechanism at parity on all other flags "
        f"(declared delta, not a parity violation -- see _PSYCHOED_DECLARED_DELTA_VARS)."
    )


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
    """PSYCHOED_SERVE EXPLICIT RESET (Task 9 fix round 4, controller-observed live-run
    finding): `psychoed_serve` is documented in src/sage_poc/state.py + server_helpers.py's
    `_build_state` as PER-TURN -- prod's own `_build_state` explicitly resets it to `None` on
    EVERY incoming request ("psychoed_serve is PER-TURN, reset unconditionally... The other
    pathway-scoped channels... are DELIBERATELY ABSENT here... persistent fields are
    intentionally absent and come from the LangGraph checkpoint"). This runner's
    make_e2e_state/carry_state helpers predate the psychoed mechanism, so `psychoed_serve` is
    in neither their defaults nor `_PSYCHOED_CARRY` -- harmless for the CI driver (no
    checkpointer, an omitted key is simply absent, never stale), but a real gap now that this
    runner's graph is built WITH a real checkpointer + a stable per-row thread_id (fix round
    3): an omitted key means "don't touch this channel," so a genuine serve on an EARLIER
    turn of a multi-turn row leaked, unreset, into every LATER turn's final state --
    confirmed by an offline harness (task-9-report.md fix round 4): a real F6-002-shaped
    2-turn row showed turn 1's `psychoed_serve` dict still present in turn 2's result even
    when turn 2's OWN `skill_match_method` correctly showed HR routing
    (`psychotic_disclosure_auto_select`) had fired -- `observed()` checks `psychoed_serve`
    before the HR marker, so the stale leak silently overrode the correct disposition, and
    this runner's own `never_proceed` checks read it as a false leak. This is the exact class
    of bug the F6-001/F6-002/F6-003 MISSes in Task 10 live attempt 5 traced to."""
    carried = {k: prev.get(k) for k in (*_PSYCHOED_CARRY, *_EXTRA_CARRY) if k in prev}
    return carry_state(prev, raw_message, **{**carried, "psychoed_serve": None, **overrides})


# ---------------------------------------------------------------------------
# COMPLETE PER-TURN RESET MIRROR (Task 9 fix round 5, scoped-re-review finding).
#
# Fix round 4 mirrored exactly ONE of prod's per-turn resets (`psychoed_serve`, in `_carry`
# above) because that was the one channel a diagnosed live artifact pointed at. That fix was
# correct but INCOMPLETE: the underlying defect is a CLASS, not a single channel.
#
# The class: fix round 3 made this runner's checkpointer genuinely active (a real MemorySaver
# compiled into the graph by `graph_evidence.build_local_graph`, plus a STABLE per-row
# thread_id so one fixture row = one session). Under an active checkpointer, LangGraph merges
# a turn's input dict INTO the persisted channel values -- so a key OMITTED from the input
# does not mean "absent/default", it means "leave this channel exactly as the previous turn
# left it". `make_e2e_state`/`carry_state` (tests/test_graph.py) predate almost all of the
# psychoed/knowledge/screen/classifier channels and set only 30 keys; prod's own per-turn
# state constructor (src/sage_poc/server_helpers.py::_build_state) sets 62. Every one of the
# ~37 keys in the difference was leak-prone here: turn 1's value silently survived into turn
# 2+ with no reset, exactly as `psychoed_serve` did. At least one existing multi-turn fixture
# (F10-004b, tests/fixtures/psychoed/f10_diagnosis.jsonl) asserts on one of them
# (`knowledge_passages`), so flip-tier MISSes on that class would have been INSTRUMENT
# ARTIFACTS, not measurements -- the same verdict fix round 4 reached for F6-001/002/003.
#
# The fix is DERIVED FROM THE SOURCE, not hand-copied: `_prod_build_state` IS
# `server_helpers._build_state`, imported and called. There is no list of channel names in
# this file to drift out of sync -- if prod adds, removes, or renames a per-turn reset, this
# runner picks it up on the next run with no edit. `src/` is not touched: the import is
# read-only reuse of a pure function (server_helpers' own module docstring guarantees it
# imports neither FastAPI nor anything that opens a DB connection at import time, and it
# imports nothing sage_poc-rooted at all -- so this import cannot trigger config.py's
# `load_dotenv()` and is safe with respect to the SAFETY SNAPSHOT discipline at the top of
# this file). `test_measure_psychoed_families_safety.py` still carries a source-parsing SYNC
# GUARD (AST-derived from server_helpers.py, house style per
# test_psychoed_fixtures_ci.py::test_intent_sweep_matches_intent_route_vocabulary) that fails
# CI if `_build_state` ever stops being a single literal return dict, or if any reset channel
# it declares stops being present in a turn this runner constructs.
#
# RESET vs CARRIED -- the distinction is prod's own, mirrored structurally, not by a list:
#   * PRESENT as a key in `_build_state`'s returned dict  => per-turn reset. Prod rebuilds it
#     from scratch on EVERY request, so a stale value can never reach a node.
#   * ABSENT from that dict                               => persisted. Prod deliberately
#     leaves it to the LangGraph checkpoint (its own docstring: "Persistent fields
#     intentionally absent ... they come from LangGraph checkpoint" -- conversation_history,
#     crisis_state, active_skill_id/_step_id, clinical_flags, trajectories, turn_count,
#     therapeutic_profile), and its psychoed comment extends the same rule to the
#     pathway-scoped channels: "The other pathway-scoped channels (psychoed_active_category,
#     _delivery_shape, _blocks_served, _menu_offered, _weave_fired, _weave_pending,
#     _matched_row_id, _collision_path, _framing) and the session-scoped
#     psychoed_family_exposures are DELIBERATELY ABSENT here".
# That is EXACTLY this runner's carry set: `_PSYCHOED_CARRY` (10 keys) has ZERO intersection
# with `_build_state`'s keys -- verified mechanically, every run, by the sync guard -- so the
# reset overlay structurally CANNOT clobber a psychoed carry key. The overlay is applied
# UNDER the runner's own state (`{**overlay, **own}`), so it only ever FILLS IN a channel the
# runner does not already set: every carried value (`_CARRY_FIELDS`, `_PSYCHOED_CARRY`,
# `_EXTRA_CARRY`) and every fixture `state_overrides` value still wins, unchanged. This is
# additive reset coverage, never a value change to anything already threaded.
#
# TWO KEYS ARE EXCLUDED (`_PROD_REQUEST_DERIVED_KEYS`): `session_id`/`user_id` are not resets
# at all -- `_build_state`'s own trailing comment labels them "Set from request", they carry
# the caller's identity, and injecting a synthetic one here would hand real per-session/user
# persistence paths a fabricated identity. This runner drives fixtures, not sessions; leaving
# them absent (as every psychoed test at CI tier does) is the faithful choice.
#
# `raw_message`/`message_en`/`detected_language` ARE included (they are genuine per-turn
# rebuilds in prod), but the runner's own state sets all three, so the overlay never changes
# them -- `make_e2e_state`'s long-standing `message_en=""` / `is_safe=False` conventions are
# preserved byte-for-byte, and safety_check overwrites both on every turn regardless.
# ---------------------------------------------------------------------------

from sage_poc.server_helpers import (  # noqa: E402
    _MessageLike as _ProdMessageLike,
    _RequestLike as _ProdRequestLike,
    _build_state as _prod_build_state,
)

_PROD_REQUEST_DERIVED_KEYS = frozenset({"session_id", "user_id"})


def _prod_per_turn_reset(raw_message: str) -> dict:
    """The EXACT per-turn reset slice prod's server builds for every incoming request.

    Calls the REAL `server_helpers._build_state` (a pure function of the request) rather than
    reproducing any part of it, then drops the two request-identity keys (see
    `_PROD_REQUEST_DERIVED_KEYS` above). Every remaining key is a channel prod rebuilds from
    scratch each turn; supplying them here is what makes this runner's checkpointer-backed
    multi-turn path reset-equivalent to prod's stateless-per-turn construction."""
    prod_state = _prod_build_state(
        _ProdRequestLike(
            messages=[_ProdMessageLike(role="user", content=raw_message)],
            session_id="",
            user_id=None,
        )
    )
    return {k: v for k, v in prod_state.items() if k not in _PROD_REQUEST_DERIVED_KEYS}


def _turn_state(prev: dict | None, raw_message: str, **overrides) -> dict:
    """Build one turn's input state: prod's full per-turn reset UNDER this runner's own
    turn-state convention (first turn: `make_e2e_state`; continuation turns: `_carry`).

    Merge order is load-bearing and asserted by the sync guard: the reset overlay is the
    BASE, so it fills every channel the runner would otherwise omit (the leak class) while
    every carried field and every fixture `state_overrides` value still wins on top."""
    own = make_e2e_state(raw_message, **overrides) if prev is None else _carry(prev, raw_message, **overrides)
    return {**_prod_per_turn_reset(raw_message), **own}


# ---------------------------------------------------------------------------
# Audit-capture coverage (task-9-review.md finding "(c) Audit-write exposure" -- Important).
#
# `write_session_audit` is imported into SIX distinct module namespaces across src/sage_poc/
# (each `from sage_poc.audit import write_session_audit`, a REBOUND name -- patching
# `sage_poc.audit.write_session_audit` alone does NOT intercept a caller that already holds
# its own reference). Two are the CI driver's own patch targets (`sage_poc.graph`, the Node-1
# crisis short-circuit; `sage_poc.nodes.output_gate`, normal turn-close, two call sites one
# import); the other FOUR are terminal response nodes that bypass output_gate entirely
# (`derealization_response.py`, `medical_response.py`, `high_risk_response.py`,
# `screen_response.py`). This runner drives the REAL, unpatched intent_route with a live LLM
# by design -- a fixture's real-time classification can land on any of the six -- so missing
# even one means a live run (Task 10, which necessarily configures real Supabase credentials
# for the amendment-8 smoke case's genuine DB retrieval) POSTs a real session_audit row from
# that unpatched site. Enumerated explicitly (not just "the two the CI driver already
# patches") and statically verified complete before ANY row is driven -- see
# `_assert_audit_patch_coverage_complete` below.
# ---------------------------------------------------------------------------

_AUDIT_PATCH_TARGETS = (
    "sage_poc.graph.write_session_audit",
    "sage_poc.nodes.output_gate.write_session_audit",
    "sage_poc.nodes.derealization_response.write_session_audit",
    "sage_poc.nodes.medical_response.write_session_audit",
    "sage_poc.nodes.high_risk_response.write_session_audit",
    "sage_poc.nodes.screen_response.write_session_audit",
)


def _discover_write_session_audit_importers(src_root: Path | None = None) -> frozenset[str]:
    """Static source scan (same enforcement idiom as scripts/check_state_channels.py /
    tests/test_instrument_helper_only.py): every module under src/sage_poc/ whose source
    contains `from sage_poc.audit import ... write_session_audit ...`. Returns dotted
    `<module>.write_session_audit` names, the same shape `_AUDIT_PATCH_TARGETS` uses."""
    src_root = src_root or (REPO / "src" / "sage_poc")
    pattern = re.compile(r"from\s+sage_poc\.audit\s+import\s+[^\n]*\bwrite_session_audit\b")
    discovered = set()
    for path in src_root.rglob("*.py"):
        if path.name == "audit.py":
            continue  # the definition site, not an importer
        if pattern.search(path.read_text(encoding="utf-8")):
            rel = path.relative_to(src_root).with_suffix("")
            mod = "sage_poc." + ".".join(rel.parts)
            discovered.add(f"{mod}.write_session_audit")
    return frozenset(discovered)


def _assert_audit_patch_coverage_complete() -> None:
    """Fails LOUDLY (RuntimeError, not a silently-narrowed patch list) if a
    write_session_audit import site exists that `_AUDIT_PATCH_TARGETS` does not cover, so a
    FUTURE node addition (a fifth terminal response node, same shape as the current four)
    cannot silently reopen the live-DB-write hole this module closes. Also flags a STALE
    entry (a target that no longer corresponds to any real import site) so the list never
    drifts into false confidence in either direction. Called once, before driving any row."""
    discovered = _discover_write_session_audit_importers()
    patched = frozenset(_AUDIT_PATCH_TARGETS)
    missing = discovered - patched
    stale = patched - discovered
    if missing:
        raise RuntimeError(
            f"AUDIT-CAPTURE COVERAGE GAP: write_session_audit is imported by {sorted(missing)} "
            f"but _AUDIT_PATCH_TARGETS does not cover it -- a live run would POST real "
            f"session_audit rows from this site if a fixture's real-time routing reaches it. "
            f"Add it to _AUDIT_PATCH_TARGETS (measure_psychoed_families.py) before running live."
        )
    if stale:
        raise RuntimeError(
            f"_AUDIT_PATCH_TARGETS lists {sorted(stale)} but no matching write_session_audit "
            f"import site exists anymore -- prune the stale entry."
        )


# ---------------------------------------------------------------------------
# Driver: REAL intent_route, REAL freeflow LLM, REAL knowledge_retrieve. The ONLY patches are
# the six write_session_audit capture sites above -- see module docstring for why that is
# parity-safe (observes a side effect, never a decision).
# ---------------------------------------------------------------------------

async def run_fixture_real(row: dict) -> dict:
    """Instrument-parity standing rule (SIGNED 2026-07-28, docs/superpowers/governance/
    2026-07-28-instrument-parity-standing-rule.md): the graph is built and invoked only via
    scripts/instrument/graph_evidence.py's `build_local_graph`/`invoke_turn` helpers -- the
    ONLY sanctioned home for direct graph-construction/-invocation calls outside that file
    itself (test_instrument_helper_only.py enforces this by static scan; this module
    deliberately calls neither the graph constructor nor the graph's own invoke method by
    name). This runner owns state construction (make_e2e_state/carry_state/`_carry`) and the
    six-site audit-capture patch; the helper owns the actual invocation mechanics -- see
    graph_evidence.py's own `invoke_turn` docstring.

    THREAD_ID (Task 9 fix round 3, controller-observed live-checkpoint crash): `build_local_
    graph()` always compiles the graph WITH a checkpointer (MemorySaver), so `invoke_turn`
    REQUIRES a thread_id on every call (LangGraph raises ValueError otherwise -- see that
    function's own docstring for the full incident trace: a live run crashed on its very
    first invocation, the amendment-8 smoke case, before driving any of the 196 corpus rows).
    This function does NOT rely on the checkpointer for turn-to-turn continuity -- state is
    threaded manually via make_e2e_state/`_carry` exactly as the CI driver does, so the
    SPECIFIC thread_id value is not load-bearing for correctness -- but it must be STABLE
    across every turn of the SAME row (one fixture row = one session, mirroring how a real
    multi-turn conversation would look) and UNIQUE per row (so two rows, or two runs of the
    same fixture_id, never share checkpoint state)."""
    from sage_poc.audit import _build_session_audit_row  # noqa: PLC0415
    from scripts.instrument import graph_evidence as ge  # noqa: PLC0415

    _assert_audit_patch_coverage_complete()

    captured: list[dict] = []

    async def _capture_audit(state):
        captured.append(state)

    thread_id = f"psychoed-flip-{row.get('fixture_id', 'unknown')}-{uuid.uuid4().hex[:8]}"

    with contextlib.ExitStack() as stack:
        for target in _AUDIT_PATCH_TARGETS:
            stack.enter_context(patch(target, new=_capture_audit))
        # build_local_graph() INSIDE the patch context: add_node("output_gate", ...) style
        # callers capture a direct reference to the write_session_audit-calling function at
        # build time in this codebase's graph wiring (same rule the CI driver documents for
        # intent_route_node); doing this after the patches keeps that binding consistent.
        # warm=False: this runner warms BGE-M3 ONCE for the whole run (main()), not per row.
        app = ge.build_local_graph(warm=False)
        result: dict | None = None
        for turn in row["turns"]:
            overrides = turn.get("state_overrides") or {}
            # `_turn_state` = prod's COMPLETE per-turn reset (server_helpers._build_state,
            # imported and called, not re-typed) under this runner's own make_e2e_state/
            # `_carry` convention -- see that function and the reset-mirror block above.
            # Applied on the FIRST turn too, exactly as prod does: `_build_state` runs for
            # every incoming request, including a session's first.
            state_in = _turn_state(result, turn["utterance"], **overrides)
            result = await ge.invoke_turn(app, state_in, thread_id)
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
# exactly one label per turn, so the label-class splits become branches on the REAL OBSERVED
# label rather than on a pinned sweep label -- see `_real_label`/`_mechanism_applies` below.
#
# Task 9 fix round 4 (controller-observed live-run findings, Task 10 attempt 5):
#   (1) "Flip-tier assertion semantics are disposition-only" -- rows with no
#       expect.disposition (all F10, F3-001..004, all F8 matrix rows) reported
#       "observed-only n/a": their expect.audit/expect.state subsets were never asserted at
#       all. Fixed by `_assert_subset` below, which REUSES (imports, does not reimplement)
#       test_psychoed_fixtures_ci.py's own `_subset_match` -- the exact function the CI
#       driver asserts audit/state subsets with -- wrapped to convert its raising-assert
#       semantics into this runner's non-raising MISS-is-data semantics.
#   (2) "Label-class split by REAL observed intent" -- F6-001/F6-003 showed observed
#       disposition == expected yet MISS. Root-caused (see `_carry`'s own docstring) to a
#       DIFFERENT bug (`psychoed_serve` staleness from the newly-active checkpointer), not a
#       missing label split per se -- but `label_dispositions` rows WERE also missing the
#       real-label lookup entirely (only `_default` was ever consulted, so F6-002's row,
#       which has no `_default`, never had ITS per-label expected disposition checked at
#       all). `_real_label`/`_mechanism_applies` below now mirror the CI driver's
#       WEAVE_EVALUATOR_LABELS split using the REAL observed label instead of a pinned sweep
#       label.
# Returns (conform: bool | None, detail: str); conform=None means "no assertable expectation
# fired for this row" (never tallied as a pass or a fail, only reported as observed).
# ---------------------------------------------------------------------------

def _real_label(result: dict) -> str | None:
    """The flip-tier analog of the CI driver's swept `intent_for_sweep` label: what the REAL
    graph actually decided for this row's final turn. `"crisis"` when Node-1's own
    deterministic S1-S4 crisis detection intercepted (`gate_path == "crisis"`) BEFORE
    intent_route ever ran -- the flip-tier equivalent of the CI driver's crisis-label sweep
    case, a structural graph property independent of what the LLM classifier would have said.
    Otherwise the REAL `primary_intent` the live classifier produced this turn -- `None` if
    the turn never reached intent_route via some other early-gate path. `primary_intent` is a
    per-turn-reset SageState channel (both make_e2e_state's defaults and
    server_helpers.py::_build_state explicitly set it to `None` every turn), so it can never
    carry stale from an earlier turn the way `psychoed_serve` did before this fix round."""
    if result.get("gate_path") == "crisis":
        return "crisis"
    return result.get("primary_intent")


def _mechanism_applies(real_label: str | None) -> bool:
    """Mirrors the CI driver's `WEAVE_EVALUATOR_LABELS` split (test_psychoed_fixtures_ci.py):
    the psychoed mechanism-witness assertions (escalation audit patch, pathway-clear state)
    only apply on labels whose graph path actually reaches skill_select's PSY-WEAVE-1
    evaluator -- every real label EXCEPT `"crisis"` (crisis-intent supremacy bypasses
    skill_select entirely, at flip tier exactly as at CI tier)."""
    return real_label != "crisis"


def _assert_subset(expected: dict | None, actual: dict, ctx: str) -> tuple[bool | None, str]:
    """Wraps test_psychoed_fixtures_ci.py's own `_subset_match` (imported, NOT reimplemented,
    per the ruled instruction) to convert its raising-assert semantics into this runner's
    non-raising MISS-is-data semantics. Deferred (in-function) import: by the time THIS
    function is CALLED, both modules are already fully loaded regardless of import order, so
    this cannot resurrect the circular-import `observed()`'s own one-way top-level-import
    discipline exists to avoid (test_psychoed_fixtures_ci.py imports `observed` from this
    module at ITS top level; this module must not import anything back at ITS OWN top level)."""
    if not expected:
        return None, "(no expect block)"
    from tests.test_psychoed_fixtures_ci import _subset_match  # noqa: PLC0415
    try:
        _subset_match(expected, actual, ctx)
        return True, "OK"
    except AssertionError as e:
        return False, str(e)


def _conforms(row: dict, out: dict) -> tuple[bool | None, str]:
    result = out["result"]
    audit_rows = out["audit_rows"]
    last_audit = audit_rows[-1] if audit_rows else {}
    got = observed(result)
    real_label = _real_label(result)
    fid = row.get("fixture_id", "?")

    parts: list[tuple[str, bool | None, str]] = []  # (name, ok_or_None, detail)

    if row.get("clear_no"):
        # Single real path: crisis-intent supremacy applies only if the LIVE classifier
        # actually produced the crisis label this turn (gate_path=="crisis"); every other
        # observed path expects the menu-after-weave mechanism-witness shape (see the CI
        # driver's own `assert_expectations` docstring, "Task 6 driver extensions", for the
        # full reasoning this mirrors).
        if real_label == "crisis":
            ok = got == "escalate_crisis" and not result.get("psychoed_menu_offered")
            parts.append(("disposition", ok, f"clear_no/crisis-path observed={got!r}"))
        else:
            never_proceed = (
                not result.get("psychoed_weave_escalation")
                and result.get("skill_match_method") != "psychoed_resolver"
            )
            parts.append(("never_proceed", never_proceed,
                          f"clear_no/non-crisis skill_match_method={result.get('skill_match_method')!r}"))
            ok, d = _assert_subset(row["expect"].get("audit"), last_audit, f"{fid} audit")
            parts.append(("audit", ok, d))
            ok, d = _assert_subset(row["expect"].get("state"), result, f"{fid} state")
            parts.append(("state", ok, d))

    elif row.get("label_dispositions"):
        label_map = row["label_dispositions"]
        expected = label_map.get(real_label, label_map.get("_default"))
        never_proceed = (
            not result.get("psychoed_serve")
            and result.get("skill_match_method") not in ("psychoed_resolver", "psychoed_menu_after_weave")
        )
        parts.append(("never_proceed", never_proceed,
                      f"label_dispositions[{real_label!r}] never_proceed={never_proceed}"))
        if expected is not None:
            parts.append(("disposition", got == expected, f"observed={got!r} expected={expected!r}"))
        ok, d = _assert_subset(row["expect"].get("audit"), last_audit, f"{fid} audit")
        parts.append(("audit", ok, d))
        ok, d = _assert_subset(row["expect"].get("state"), result, f"{fid} state")
        parts.append(("state", ok, d))

    else:
        disposition = row["expect"].get("disposition")
        expects_escalation = disposition == "escalate_crisis"
        if disposition is not None:
            parts.append(("disposition", got == disposition, f"observed={got!r} expected={disposition!r}"))
        if row["family"] in ("F4", "F6", "F8") and expects_escalation:
            never_proceed = (
                not result.get("psychoed_serve")
                and not result.get("psychoed_menu_offered")
                and result.get("skill_match_method") not in ("psychoed_resolver", "psychoed_menu_after_weave")
            )
            parts.append(("never_proceed", never_proceed, f"never_proceed={never_proceed}"))
        # Mechanism-witness assertions (audit/state) apply unconditionally UNLESS this row
        # expects escalation, in which case they only apply on labels that actually reach the
        # weave evaluator (mirrors the CI driver's WEAVE_EVALUATOR_LABELS split, keyed here on
        # the REAL observed label instead of a pinned sweep label).
        gate_ok = (not expects_escalation) or _mechanism_applies(real_label)
        if gate_ok:
            ok, d = _assert_subset(row["expect"].get("audit"), last_audit, f"{fid} audit")
            parts.append(("audit", ok, d))
            ok, d = _assert_subset(row["expect"].get("state"), result, f"{fid} state")
            parts.append(("state", ok, d))
        else:
            parts.append(("audit/state", None,
                          f"real_label={real_label!r} does not reach the weave evaluator -- "
                          f"mechanism-witness assertions do not apply this turn"))

    assertable = [ok for _n, ok, _d in parts if ok is not None]
    overall = all(assertable) if assertable else None
    detail = "; ".join(
        f"{n}={'OK' if ok else 'MISS' if ok is False else 'n/a'}({d})" for n, ok, d in parts
    ) or "no assertable expectation"
    return overall, f"real_label={real_label!r} {detail}"


# ---------------------------------------------------------------------------
# Retrieval honesty + read-only bootstrap (Task 9 fix round 4, controller-observed live-run
# finding). knowledge_retrieve_node's own `_get_pool()` reads `server.app.state._db_pool` --
# normally built by server.py's startup lifespan hook (server.py:363-411), which never runs
# for this standalone script. Task 10 live attempt 5 drove EVERY row with retrieval
# permanently abstaining ('[knowledge_retrieve] DB pool unavailable, returning abstain' on
# every single turn), making the prior provenance line ("REAL retrieval") FALSE AS WRITTEN,
# and the amendment-8 smoke case STRUCTURALLY UNABLE to fire -- not merely "didn't fire this
# run, retrieval-dependent" (which implied a coin-flip that never had real odds).
# ---------------------------------------------------------------------------

async def _bootstrap_retrieval_pool():
    """When DATABASE_URL is present, bootstraps a genuinely READ-ONLY asyncpg pool
    (`server_settings={"default_transaction_read_only": "on"}` -- a session-level PostgreSQL
    GUC that makes the SERVER ITSELF reject any write statement issued through a connection
    from this pool; a DB-ENFORCED write guard, not merely an application-level promise) and
    injects it at the EXACT site `_get_pool()` reads (`server.app.state._db_pool`) -- the same
    attribute name server.py's own startup hook sets, so `knowledge_retrieve_node`'s
    unmodified code path finds it exactly as it would find prod's own pool.

    When DATABASE_URL is ABSENT, this does NOT refuse -- retrieval-dependent measurement is a
    known-honest degraded mode, not a hard failure; the run proceeds with retrieval abstaining
    everywhere (byte-identical to Task 10 attempt 5's actual behavior), but the provenance
    below states the truth instead of overclaiming "REAL retrieval".

    Returns (provenance_line: str, pool_or_None) -- caller is responsible for closing the pool."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        return (
            "UNAVAILABLE (no DATABASE_URL) -- all retrieval abstains this run; the "
            "amendment-8 smoke case cannot structurally fire"
        ), None
    import asyncpg  # noqa: PLC0415
    from server import app as _server_app  # noqa: PLC0415
    pool = await asyncpg.create_pool(
        db_url, min_size=1, max_size=2,
        server_settings={"default_transaction_read_only": "on"},
    )
    _server_app.state._db_pool = pool
    return (
        "ACTIVE (read-only pool: default_transaction_read_only=on -- writes rejected at the "
        "DB session level, not merely an application-level promise)"
    ), pool


# ---------------------------------------------------------------------------
# Register-amendment-8 rider (a): ONE best-effort, non-gating real-retrieval smoke case.
# ---------------------------------------------------------------------------

_AMENDMENT_8_SMOKE = {
    "category": "3c",
    "utterance": "Can you tell me a bit more about why I've been feeling so down and numb lately?",
}


async def _run_amendment_8_smoke(armed_categories: frozenset[str], retrieval_active: bool) -> dict:
    """Register amendment #8 rider (a) (ruled 2026-07-30): a paraphrase query, run through
    the REAL knowledge_retrieve node (no rag_top fake -- genuinely live DB retrieval when
    `retrieval_active`), that plausibly surfaces a psychoed block via spec 2.2's semantic
    backstop (the same mechanism F9-001 pins with a faked rag_top). NON-GATING regardless of
    outcome: this only ever produces a log entry, never a pass/fail contribution.

    `retrieval_active=False` (no DATABASE_URL) means this smoke case is STRUCTURALLY UNABLE
    to fire -- still runs (for the rest of its diagnostic value: intent routing, psychoed
    entry, etc.) but is reported honestly as "cannot structurally fire" rather than the
    misleading "did not fire this run (non-deterministic)" the pre-fix version always said."""
    if _AMENDMENT_8_SMOKE["category"] not in armed_categories:
        return {"ran": False, "note": f"target category {_AMENDMENT_8_SMOKE['category']!r} not armed this run"}
    row = {"turns": [{"utterance": _AMENDMENT_8_SMOKE["utterance"], "state_overrides": {}}]}
    out = await run_fixture_real(row)
    result = out["result"]
    fired = bool(result.get("psychoed_serve"))
    passages = result.get("knowledge_passages") or []
    return {
        "ran": True,
        "retrieval_active": retrieval_active,
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
    ap.add_argument("--live", action="store_true",
                     help="REQUIRED (with --dry-run absent) to actually drive fixtures against a "
                          "live LLM/graph. Explicit opt-in a .env file cannot forge -- see the "
                          "module-level safety-snapshot comment for why this exists.")
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
    # CARVE-OUT (see _PSYCHOED_DECLARED_DELTA_VARS docstring above): the two psychoed vars are
    # this run's declared delta, not a parity violation -- removed from the diff set BEFORE the
    # MISMATCH gate below, verdict recomputed from what remains. Every other var stays hard-parity.
    parity, flag_diffs, unverified_vars, _carved_delta = _carve_out_declared_delta(flag_diffs, unverified_vars)
    print(f"📌 DECLARED DELTA: {_psychoed_delta_stamp(_carved_delta, resolved_flags, armed)}", flush=True)

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
        # Defense-in-depth: main()'s pre-import snapshot check (undefeatable by a .env) is
        # the PRIMARY guard and already ran before this function was ever called; this catches
        # the (currently theoretical) case of something deleting the var between that snapshot
        # and here.
        print("❌ OPENROUTER_API_KEY is not set -- refusing (this runner requires a REAL "
              "live LLM; no node patches, see module docstring).", flush=True)
        return 8

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

    retrieval_provenance, retrieval_pool = await _bootstrap_retrieval_pool()
    print(f"[{time.time()-t0:.0f}s] retrieval: {retrieval_provenance}", flush=True)

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

    amendment8 = await _run_amendment_8_smoke(armed, retrieval_active=retrieval_pool is not None)

    procedural = _run_procedural() if args.include_procedural else None

    if retrieval_pool is not None:
        await retrieval_pool.close()

    faults = len(errors)
    result = {
        "provenance": {
            "sha": args.sha or _git_sha(),
            "instrument": "FULL-GRAPH app.ainvoke, REAL intent_route + REAL LLM (no node "
                           "patches); only write_session_audit is captured (parity-safe); "
                           "retrieval state below is the ACTUAL state, not assumed",
            "flag_parity": f"{parity} vs {parity_source} (psychoed vars carved out as the "
                           "declared delta -- see below; all other SAGE_ vars hard-parity)"
                           + (" (proceeded via --allow-flag-mismatch)" if parity == "MISMATCH" else ""),
            "categories_armed": sorted(armed),
            "declared_delta": _psychoed_delta_stamp(_carved_delta, resolved_flags, armed),
            "retrieval": retrieval_provenance,
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
        # PROMINENT declared-delta banner (ruled, task-9 fix round 2): this run intentionally
        # diverges from prod on exactly SAGE_PSYCHOED_PATHWAYS/SAGE_PSYCHOED_CATEGORIES -- the
        # record must state that plainly, up front, every time, not bury it in the provenance
        # table below.
        f.write(f"> **📌 DECLARED DELTA: {prov['declared_delta']}**\n\n")
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
        elif not a8.get("retrieval_active"):
            f.write(f"- did not fire -- retrieval UNAVAILABLE this run ({prov['retrieval']}); "
                    f"this smoke case could NOT structurally fire (honest, not a non-deterministic "
                    f"miss). passages surfaced: {a8.get('passage_source_ids')}\n")
        elif a8.get("fired"):
            f.write(f"- **FIRED**: backstop served (matched_row_id={a8.get('matched_row_id')!r}, "
                    f"collision_path={a8.get('collision_path')!r}, gate_action={a8.get('gate_action')!r})"
                    " -- confirms spec 2.2 fail-to-personal shape in situ.\n")
        else:
            f.write(f"- did not fire this run (retrieval was ACTIVE; genuinely retrieval-dependent, "
                    f"non-deterministic outcome); passages surfaced: {a8.get('passage_source_ids')}\n")

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
    # ---- UNDEFEATABLE live-mode gate (task-9-review.md finding (a)) -- checked here, before
    # ANY network/graph/asyncio work, so a missing opt-in fails as cheaply and as loudly as
    # possible. Both checks are required; neither alone is sufficient (see the module-level
    # safety-snapshot comment for the full incident trace).
    if not args.live:
        print("❌ live mode requires the explicit --live flag (a .env file cannot forge a CLI "
              "argument) -- refusing. Pass --dry-run to validate wiring, or --live to actually "
              "drive fixtures against a live LLM.", flush=True)
        return 6
    if not _PRE_IMPORT_ENV_HAD_OPENROUTER_KEY:
        print("❌ OPENROUTER_API_KEY was not present in this process's environment BEFORE any "
              "sage_poc import (checked pre-import -- immune to config.py's load_dotenv() "
              "re-injecting it from a parent .env). This is the disclosed Task-9 incident's exact "
              "mechanism; refusing.", flush=True)
        return 7
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    sys.exit(main())
