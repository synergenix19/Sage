"""Psychoed Phase 3 Task 1: CI families driver + corpus schema validator.

Every fixture family (F1-F10) runs through this driver. Corpus lives in
tests/fixtures/psychoed/f*_*.jsonl (see the README there for the row schema).

Execution model (mirrors tests/test_psychoed_graph.py exactly):
- the graph is built INSIDE the patch context (add_node captures a direct reference to
  sage_poc.graph.intent_route_node at call time, so patching after build_graph() is a no-op);
- intent routing is pinned deterministically per turn (mocked intent_route_node) so the
  psychoed mechanism, not LLM variance, is what's under test;
- BOTH write_session_audit call sites are captured (sage_poc.nodes.output_gate for normal
  turn-close, sage_poc.graph for the crisis short-circuit) and each captured raw state is
  run through audit._build_session_audit_row to get the actual audit row;
- turn-to-turn state threading uses tests/test_graph.py's carry_state plus the psychoed
  channels it doesn't know about (_PSYCHOED_CARRY, imported from test_psychoed_graph);
- freeflow's LLM is stubbed (conftest.make_mock_llm) so gate-family sweep intents that fall
  through the intent ladder to freeflow (skill_request, emotional_support, general_chat on a
  non-psychoed turn) never make a live LLM call;
- psychoed flags are applied via monkeypatch only (config.PSYCHOED_PATHWAYS_ENABLED + the
  row's category in config.PSYCHOED_CATEGORIES), never env-persisted.

Gate families (F4/F6/F8) are intent-SWEPT: a row with any turn marked intent_sweep=true
runs once per intent in INTENT_SWEEP, every swept turn pinned to that intent. Non-gate
families run once with the row's default intent.

INTENT_SWEEP [AMENDED 2026-07-30, human-ruled] is the FULL intent_route label vocabulary
(src/sage_poc/nodes/intent_route.py:25) plus one "__nonexistent_label__" sentinel that pins
the intent ladder's fall-through default branch (the de facto ninth classification). A sync
test below fails if the classifier's vocabulary and this sweep diverge, so future
vocabulary changes fail CI instead of silently narrowing the gate.

Assertions are split by label class (same ruling): EVERY label asserts the never-proceed
invariant (a weave-pending reply produces no psychoed serve and no menu; crisis disposition
where the row expects escalation). The escalation MECHANISM assertions (escalation audit
row: psychoed_weave_state="escalated" + matched_row_id; and the Task-8 pathway clear in
final state) apply ONLY on labels whose graph path reaches the weave evaluator -- under the
"crisis" label, _route_after_intent's crisis branch returns before the weave-pending
branch, so escalation arrives via crisis_response directly: psychoed_weave_escalation is
never set, hence neither the "escalated" audit patch nor the escalation-scoped pathway
clear runs (graph.py _crisis_response_node: both are gated on _weave_escalation). A blanket
assertion there would fail for the wrong reason.

Task 6 adds a THIRD label-class split for `"clear_no": true` rows (F4's clear-no family):
crisis-intent SUPREMACY forces `escalate_crisis` on the "crisis" label regardless of the reply's
actual clear-no content (a structural graph property, not a weave outcome), while every other
label asserts the mechanism-witness menu-after-weave shape instead. See the "Task 6 driver
extensions" section below for the full reasoning.

baseline_only rows (Task 3: f1_naturalistic.jsonl, the blind-authored F1 naturalistic set)
are collected and schema-validated like every other row, but never hard-required: they are
excluded from _all_params()'s sweep and instead run through test_psychoed_baseline_only,
which is xfail(strict=False) so neither a miss nor a hit can fail CI. See that test's
section below for the full mechanism and the README's "F1 naturalistic" section for the
fixture-level rationale.

Task 4 driver extensions (F2 collisions + F9 backstop/quarantine):
- `_arm_psychoed` now also accepts a row-level `categories` (list) field, arming MULTIPLE
  categories at once via monkeypatch. F2's cross-category collision paths (default_winner /
  context_winner / interim_default_winner / subsumption_winner) are only reachable when
  BOTH colliding categories are enabled simultaneously (resolver.py's `_flat_collision_winner`
  / `_subsumption_winner` both filter on `enabled_categories` first) -- a single `category`
  string can never exercise a genuine collision. `categories` wins over `category` when both
  are present; falls back to the existing single-`category` behavior otherwise. Schema-neutral
  (unknown keys aren't rejected).
- `_carry` (turn-to-turn state threading) now also carries `offered_skill_ids` forward, via
  `_EXTRA_CARRY` below. This is a REAL, checkpoint-persisted SageState channel (state.py:76)
  that `tests/test_graph.py`'s own `_CARRY_FIELDS` happens not to include (that suite's
  fixtures never needed it turn-to-turn) -- completing the gap here, not inventing new state.
  F2's grief-context multi-turn row needs it: `skill_select._psychoed_grief_context` reads
  `offered_skill_ids` to detect "grief_loss was recently offered" as the collision table's
  `context_winner` signal (spec §5.1/§5.2), so a prior turn's real keyword-matched skill offer
  must survive into the next turn's state exactly as it would in a live session.
- `run_fixture` now accepts two more optional, additive row/turn-level inputs:
    1. `turns[0]["state_overrides"]`: a dict merged into the FIRST turn's `make_e2e_state(...)`
       call (e.g. `active_skill_id`, `detected_language`). This is the same "construct the
       entry state directly" pattern every other test in this suite uses to represent
       "a skill was already active" or "this is an Arabic-language turn" -- not a mechanism
       bypass, just supplying real SageState fields the mechanism itself reads. Task 6
       generalizes this to ANY turn's `state_overrides` (not just the first): F4's AR rows need
       `detected_language`/`message_en` overrides on the REPLY turn specifically, since psychoed
       pathway ENTRY is EN-only gated but PSY-WEAVE-1 evaluation is language-ungated (a live AR
       reply to an already-pending weave must still evaluate) -- see the "Task 6 driver
       extensions" section below. Backward-compatible: no pre-Task-6 row sets state_overrides on
       a non-first turn.
    2. `row["rag_top"]`: F9's retrieval-faking hook (see `_fake_knowledge_result` below and
       the README's F9 section). When present, `run_fixture` patches
       `sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository` and `._get_pool` so
       `knowledge_retrieve_node`'s DB round trip returns a CONTROLLED `KnowledgeResult` built
       from `rag_top`, instead of touching a real database. This fakes ONLY the retrieval
       boundary -- every downstream decision (semantic-backstop gating, Classifier A,
       mid-skill suppression, EN-only entry, L4 quarantine) still runs as real, unmocked
       `knowledge_retrieve_node` code reading the faked result exactly as it would read a real
       one. Because retrieval is faked at the DB boundary rather than measured against a live
       corpus, F9 is CI-TIER ONLY: the flip-tier runner (Task 9) drives real intent_route AND
       real retrieval, so F9 rows are not meaningfully flip-driveable without a live seeded
       corpus row per case. Task 9's runner must SKIP `family == "F9"` rows with a LOGGED COUNT
       (spec §7.2 no-silent-caps) rather than attempt to run them -- noted here for that task,
       not implemented by this driver.

Task 6 driver extensions (F4 weave family, 100% hard gate):
- A THIRD label-class split, alongside the escalation-row split documented above. A row opts in
  via the row-level `"clear_no": true` marker (schema-neutral, same additive pattern as
  `flag_pair_check`/`baseline_only`): a weave-pending reply that IS a clear negative, so it does
  NOT expect `escalate_crisis` as its uniform disposition (unlike F4-001 and the other crisis
  rows) -- but it still needs a label-dependent split, for a reason specific to this row type:
    - `intent_for_sweep == "crisis"`: crisis-intent SUPREMACY, a structural graph property
      independent of message content. `_route_after_safety`/the intent router send ANY turn whose
      (here, mocked) `primary_intent` is `"crisis"` straight to `crisis_response` BEFORE
      `skill_select` -- and therefore before PSY-WEAVE-1 or the resolver -- ever run, regardless
      of what the reply text actually says. So even a genuinely clear-no reply escalates under
      this one label, exactly like every other row in the family; `assert_expectations` asserts
      `escalate_crisis` here for `clear_no` rows too, sourced from the same universal graph
      property the escalation-row split already encodes, not from the row's own `expect`.
    - every other label (`WEAVE_EVALUATOR_LABELS`, or `intent_for_sweep is None`): the MECHANISM
      WITNESS property -- the weave evaluator ran and cleared, and the outcome is the
      menu-after-weave continuation (`skill_match_method == "psychoed_menu_after_weave"`,
      `psychoed_menu_offered` True, `psychoed_weave_pending` False) -- never a bare resolver
      serve (`skill_match_method == "psychoed_resolver"`) and never a skipped evaluation. This is
      what `expect.audit`/`expect.state` on `clear_no` rows encode; `expect.disposition` stays
      `null` on these rows deliberately (`_observed()` has no dedicated
      `"psychoed_menu_after_weave"` branch and falls through to `"presence_only"`, an artifact of
      `_observed`'s fallthrough order rather than a meaningful named disposition for this shape --
      the brief's own instruction is to assert the shape via mechanism-derived fields, not
      disposition).
      **`psychoed_weave_state == "fired"` alone is NOT the discriminator** (reviewer finding,
      2026-07-30 adjudication fix round 1): the audit's derived `psychoed_weave_state` reads
      `"fired"` whenever `psychoed_weave_fired` is `True` and no weave is currently pending --
      which is ALSO true on a turn where the weave cleared correctly and a *different*
      mechanism (the resolver's active-category menu-label match) then hijacks the turn with an
      unrelated block serve (the exact class the F4-002 ticket, `docs/superpowers/tickets/
      2026-07-30-menu-label-short-token-substring-collision.md`, documents: `psychoed_weave_fired`
      was already `True` from the original serve, so `psychoed_weave_state` reads `"fired"` in
      BOTH the correct menu-after-weave case and the resolver-hijack phantom-serve case). The
      companions `psychoed_matched_row_id` (stays the ORIGINAL trigger row_id, e.g. `"3c-t3"`, on
      a genuine menu-after-weave continuation; becomes `"menu_pick"` on a resolver hijack) and
      `skill_match_method` (`"psychoed_menu_after_weave"` vs `"psychoed_resolver"`) are
      LOAD-BEARING for telling "evaluated, then proceeded" apart from "evaluated, then a
      DIFFERENT mechanism hijacked the turn" -- do not drop them from a `clear_no` row's
      `expect.state`/`expect.audit` in a future edit, and do not treat `psychoed_weave_state`
      alone as sufficient evidence the mechanism-witness property holds.
  F4-002 (bare "no") is authored to this SPEC-INTENDED shape and is a KNOWN, PASTED first-run
  FAIL on 8/9 swept intents: a same-category, unrelated resolver substring-match gap (see the
  row's own `source` field) makes master re-serve a specific block instead of reaching the
  menu-after-weave branch. Per the standing rule, this is authored to spec-intended and NOT
  re-pinned to match the unsanctioned observed behavior -- a BLOCKED finding, not a fixture bug.
- AR rows (`"lang": "ar"`, `"status": "draft-pending-validator"` -- the optional `status` field
  is new in Task 6, schema-neutral, `None`/absent everywhere else): F4's AR counterparts exist
  only as UNVALIDATED author translations pending the AR faithfulness-graded validator chain (no
  AR PSY-WEAVE-1 allowlist data file is ratified yet). `_all_params()` excludes them from the
  hard-required sweep entirely (same shape as the `baseline_only`/`flag_pair_check` exclusions
  above); a dedicated `@pytest.mark.skip` parametrized test
  (`test_psychoed_ar_draft_pending_validator`) registers each one individually so pytest's own
  `-rs`/summary output carries a per-row, VISIBLE skip reason and an aggregate skipped count
  (spec §7.2 no-silent-caps) -- nothing AR-labeled is quotable as coverage. A companion always-
  running test (`test_f4_ar_rows_present_and_flagged_draft`) asserts the AR rows are neither
  missing nor mislabeled and PRINTS the count, so an accidentally-empty AR set fails loudly
  rather than silently reading as "AR coverage: zero, nobody noticed."

Task 8 driver extensions (F6 precedence, 100% hard gate):
- `row["label_dispositions"]` (optional dict, row-level): a FOURTH label-class split (see
  `assert_expectations`'s own docstring for the full mechanism), schema-neutral like
  `clear_no`/`flag_pair_check`/`categories`. Maps an intent-sweep label to its expected
  `_observed()` disposition; `"_default"` is the fallback for any label without its own entry;
  a missing/`null` lookup means "assert no particular disposition for this label" (the row
  still asserts the universal never-proceed + non-leak properties on that label, just not a
  pinned disposition). This exists because F6's mid-menu precedence rows discovered, by
  running the full sweep before authoring (never assumed), that "which non-psychoed route
  wins" genuinely VARIES by sweep label for reasons that are ORTHOGONAL to psychoed and
  predate this family -- e.g. `skill_select_node`'s own `primary_intent == "info_request"`
  early-return (skill_select.py ~L786) runs BEFORE the psychotic-disclosure block
  (~L858) and so starves an HR referral on that one label; `_route_after_intent` sends
  `scope_refusal`/`jailbreak` to the `"gate"` node (graph.py ~L289-294) before its own HR
  redirect (~L316) ever runs. Both are pre-existing baseline routing, not something this task
  built or should adjudicate -- `label_dispositions` lets the fixture assert the REAL,
  verified-full-graph-before-authoring shape instead of a false uniform claim that would
  fail CI for a reason unrelated to F6's own precedence property. The property F6 actually
  gates on -- psychoed never wins the turn, and the winning route's response carries no
  psychoed copy fragment (design doc §6.3, #359 pattern) -- is asserted UNCONDITIONALLY on
  every label inside this branch, regardless of which specific route won or whether a
  disposition was pinned for that label at all. Crisis-mid-menu and medical-mid-menu use
  this same mechanism (via a single `"_default"` entry) rather than the pre-existing
  `expects_escalation` never-proceed block below, because that block's
  `assert not psychoed_menu_offered` assumes a weave-style escalation that clears the
  pathway the SAME turn (true for F4); an ordinary safety-exit mid a genuinely-offered menu
  leaves `psychoed_menu_offered` truthfully `True` as a stale carry-over (delta 8), which
  is not itself evidence of a leak.
- The post-crisis weave re-evaluation NAMED CASE (`f6_precedence.jsonl`'s row citing this
  comment) needs NO driver extension at all: verified full-graph before authoring, its
  disposition is uniformly `escalate_crisis` across every sweep label (an ordinary
  Node-1-driven crisis intercept on the `"crisis"` label; the residual `psychoed_weave_pending`
  re-firing PSY-WEAVE-1 -- fail-closed -- and escalating via `psychoed_weave_escalation` on
  every other label), so the PRE-EXISTING escalation-row shape and its WEAVE_EVALUATOR_LABELS
  mechanism-assertion split (already built for F4) apply unmodified.
"""
import asyncio
import contextlib
import json
import pathlib
import re
import unicodedata
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sage_poc.config as config
from sage_poc.audit import _build_session_audit_row
from sage_poc.graph import build_graph
from tests.conftest import make_mock_llm
from tests.test_graph import make_e2e_state, carry_state
from tests.test_psychoed_graph import _PSYCHOED_CARRY

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures" / "psychoed"

# Maintained-by-hand copy of intent_route's label vocabulary (src/sage_poc/nodes/
# intent_route.py:25, the INTENT_SYSTEM "primary_intent: one of ..." line -- there is no
# importable constant). test_intent_sweep_matches_intent_route_vocabulary() below is the
# sync check: vocabulary drift fails CI rather than silently narrowing the gate.
INTENT_ROUTE_VOCABULARY = (
    "skill_continuation", "new_skill", "general_chat", "crisis",
    "info_request", "exit_skill", "scope_refusal", "jailbreak",
)
# Pins _route_after_intent's fall-through default branch (the de facto ninth classification).
FALLTHROUGH_SENTINEL = "__nonexistent_label__"
INTENT_SWEEP = INTENT_ROUTE_VOCABULARY + (FALLTHROUGH_SENTINEL,)

# Labels whose graph path reaches the PSY-WEAVE-1 evaluator on a weave-pending turn.
# Derived from graph.py _route_after_intent's branch order: (1) intent == "crisis" returns
# "crisis" FIRST (crisis supremacy -- deliberate, see the HIGH-1 comment in graph.py);
# (2) answering_screen (never set here); (3) the weave-pending branch returns
# "skill_select" for EVERY other label, including scope_refusal/jailbreak (their "gate"
# branches sit BELOW it) and the sentinel (which would otherwise fall through to freeflow).
# So exactly one label bypasses the evaluator: "crisis".
WEAVE_EVALUATOR_LABELS = frozenset(INTENT_SWEEP) - {"crisis"}

GATE_FAMILIES = frozenset({"F4", "F6", "F8"})
# Default pinned intent for non-swept turns with no explicit turn/row intent: info_request
# reaches skill_select, where the psychoed resolver runs (mirrors test_psychoed_graph.py's
# pinned serve-turn intent).
DEFAULT_INTENT = "info_request"

_REQUIRED_KEYS = ("fixture_id", "family", "set", "turns", "expect", "lang")
_VALID_SETS = frozenset({"wiring", "authored", "seed"})
_VALID_FAMILY_RE = re.compile(r"^F([1-9]|10)$")
_EM_DASH = "—"

# Neutral stub for any turn that falls through to the LLM freeflow path. Must not begin
# with a banned opener (output_gate._BANNED_OPENER_RE) or the gate would retry via a real
# LLM rewrite call.
_FREEFLOW_STUB = (
    "You mentioned things feel heavy right now. What part of it is weighing on you most?"
)


# ---------------------------------------------------------------------------
# Schema validation + corpus loading
# ---------------------------------------------------------------------------

class FixtureSchemaError(AssertionError):
    """A corpus row violates the psychoed fixture schema (see fixtures/psychoed/README.md)."""


def _require(condition: bool, where: str, message: str) -> None:
    if not condition:
        raise FixtureSchemaError(f"{where}: {message}")


def _validate_row(row: dict, where: str) -> None:
    _require(isinstance(row, dict), where, "row must be a JSON object")
    for key in _REQUIRED_KEYS:
        _require(key in row, where, f"missing required key {key!r}")
    where = f"{where}:{row['fixture_id']}"
    _require(
        isinstance(row["fixture_id"], str) and bool(row["fixture_id"].strip()),
        where, "fixture_id must be a non-empty string",
    )
    _require(
        isinstance(row["family"], str) and bool(_VALID_FAMILY_RE.match(row["family"])),
        where, f"family must match F1..F10, got {row['family']!r}",
    )
    _require(
        row["set"] in _VALID_SETS,
        where, f"set must be one of {sorted(_VALID_SETS)}, got {row['set']!r}",
    )
    _require(
        isinstance(row["lang"], str) and bool(row["lang"].strip()),
        where, "lang must be a non-empty string",
    )
    turns = row["turns"]
    _require(isinstance(turns, list) and len(turns) > 0, where, "turns must be a non-empty list")
    for i, turn in enumerate(turns):
        t_where = f"{where}:turns[{i}]"
        _require(isinstance(turn, dict), t_where, "turn must be a JSON object")
        _require(
            isinstance(turn.get("utterance"), str) and bool(turn["utterance"].strip()),
            t_where, "utterance must be a non-empty string",
        )
        _require(
            isinstance(turn.get("intent_sweep"), bool),
            t_where, "intent_sweep must be a bool (required on every turn)",
        )
        # Clinician-editable content class: no em dashes in authored utterance text
        # (mirrors feedback_em_dash_rule_content: authored copy mirrors into LLM output).
        _require(
            _EM_DASH not in turn["utterance"],
            t_where, "em dash in utterance text (clinician-editable content class forbids it)",
        )
        _require(
            not turn["intent_sweep"] or row["family"] in GATE_FAMILIES,
            t_where,
            f"intent_sweep=true is only legal in gate families {sorted(GATE_FAMILIES)}; "
            f"{row['family']} is not a gate family",
        )
    _require(isinstance(row["expect"], dict), where, "expect must be a JSON object")
    for section in ("audit", "state"):
        section_val = row["expect"].get(section)
        _require(
            section_val is None or isinstance(section_val, dict),
            where, f"expect.{section} must be an object or null",
        )
    # F1 is the naturalistic family: provenance is mandatory, not decorative.
    if row["family"] == "F1":
        _require(
            isinstance(row.get("source"), str) and bool(row["source"].strip()),
            where, "F1 (naturalistic) rows must carry a non-empty source (authoring provenance)",
        )
    # rag_top (Task 4, F9 retrieval-faking hook): optional on every family, schema-neutral by
    # convention (see the flag_pair_check / baseline_only markers above), but shape-validated
    # when present so a malformed row fails at collection time, not with a confusing runtime
    # TypeError deep inside knowledge_retrieve_node.
    rag_top = row.get("rag_top")
    if rag_top is not None:
        _require(isinstance(rag_top, dict), where, "rag_top must be an object or null")
        passages = rag_top.get("passages")
        _require(
            isinstance(passages, list) and all(isinstance(p, str) and p for p in passages),
            where, "rag_top.passages must be a list of non-empty source_id strings",
        )
        abstain = rag_top.get("abstain", False)
        _require(isinstance(abstain, bool), where, "rag_top.abstain must be a bool when present")

    # status (Task 6, F4 AR rows): optional on every family, schema-neutral by the same additive
    # convention as rag_top/flag_pair_check/baseline_only above, but shape-validated when present.
    # Currently the only sanctioned value is "draft-pending-validator" (F4's AR rows -- see
    # _is_ar_draft and the module docstring's "Task 6 driver extensions" section); a future
    # validator-graded AR chain would introduce a new value here, not repurpose this one.
    status = row.get("status")
    if status is not None:
        _require(
            status == "draft-pending-validator",
            where, f"status must be 'draft-pending-validator' (or absent), got {status!r}",
        )


def load_family(family: str, fixtures_dir: pathlib.Path = FIXTURES_DIR) -> list[dict]:
    """Read and schema-validate every f<N>_*.jsonl row for a family.

    Enforces WITHIN-family fixture_id uniqueness; the corpus-WIDE guarantee the README
    states is enforced by load_corpus() (standing test: test_corpus_fixture_ids_globally_unique).
    """
    files = sorted(fixtures_dir.glob(f"{family.lower()}_*.jsonl"))
    if not files:
        raise FileNotFoundError(
            f"no corpus files for family {family!r} under {fixtures_dir} "
            f"(expected {family.lower()}_*.jsonl)"
        )
    rows: list[dict] = []
    for path in files:
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            where = f"{path.name}:{line_no}"
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise FixtureSchemaError(f"{where}: invalid JSON ({exc})") from exc
            _validate_row(row, where)
            _require(
                row["family"] == family,
                where, f"family {row['family']!r} does not match file prefix for {family!r}",
            )
            rows.append(row)
    ids = [r["fixture_id"] for r in rows]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise FixtureSchemaError(f"{family}: duplicate fixture_id(s): {dupes}")
    return rows


def load_corpus(fixtures_dir: pathlib.Path = FIXTURES_DIR) -> dict[str, list[dict]]:
    """Load EVERY family's corpus and enforce corpus-WIDE fixture_id uniqueness.

    load_family() can only see one family at a time, so it enforces within-family
    uniqueness; this is where the README's "unique across the whole corpus" claim is
    made true. Returns {family: rows}. Raises FixtureSchemaError listing each duplicated
    fixture_id with every family it appears in.
    """
    corpus = {
        family: load_family(family, fixtures_dir=fixtures_dir)
        for family in _discovered_families(fixtures_dir)
    }
    seen: dict[str, list[str]] = {}
    for family, rows in corpus.items():
        for row in rows:
            seen.setdefault(row["fixture_id"], []).append(family)
    cross_dupes = {fid: fams for fid, fams in seen.items() if len(fams) > 1}
    if cross_dupes:
        detail = "; ".join(
            f"{fid!r} in families {sorted(fams)}" for fid, fams in sorted(cross_dupes.items())
        )
        raise FixtureSchemaError(f"corpus-wide duplicate fixture_id(s): {detail}")
    return corpus


# ---------------------------------------------------------------------------
# Disposition semantics
# ---------------------------------------------------------------------------

# CANONICAL import (Task 9): scripts/bot_behaviour_audit/measure_psychoed_families.py::observed
# is now the single source of truth for this oracle (the layer1 observed(), extended with the
# psychoed markers) -- Task 1's local copy is retired in favor of this import so the CI-tier
# driver and the flip-tier runner can never drift apart into two different disposition
# oracles. Aliased to `_observed` (the name every call site in this file already uses) so the
# import is the ONLY line that changed; behavior is byte-identical to the retired copy (same
# function body, moved verbatim -- see that module's own docstring for the psychoed-extension
# placement rationale: below crisis/medical for crisis supremacy, above the skill markers).
from scripts.bot_behaviour_audit.measure_psychoed_families import observed as _observed


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

# Extra state channels carried turn-to-turn by this driver, beyond test_graph.py's
# _CARRY_FIELDS + _PSYCHOED_CARRY (Task 4: F2's grief-context multi-turn row). See the
# module docstring's "Task 4 driver extensions" section for why offered_skill_ids belongs
# here (a real, checkpoint-persisted SageState channel test_graph.py's own carry helper
# happens not to include).
_EXTRA_CARRY = ("offered_skill_ids",)


def _carry(prev: dict, raw_message: str, **overrides) -> dict:
    """carry_state() plus the psychoed channels it doesn't know about (_PSYCHOED_CARRY),
    plus _EXTRA_CARRY (Task 4)."""
    carried = {k: prev.get(k) for k in (*_PSYCHOED_CARRY, *_EXTRA_CARRY) if k in prev}
    return carry_state(prev, raw_message, **{**carried, **overrides})


def _fake_knowledge_result(rag_top: dict):
    """Task 4 (F9): build a controlled KnowledgeResult from a row's `rag_top` field.

    `rag_top` shape: {"passages": [<source_id>, ...], "abstain": <bool, default false>}.
    `passages` is rank-ordered (index 0 = top / rank 1). Each source_id becomes a minimal,
    deterministic KnowledgePassage: text=f"fixture passage {source_id}", citation="fixture",
    relevance_score descending from 0.9 by 0.1 per rank, source_url/title/video_url empty --
    the CONTENT of these fields is never clinically meaningful (no real KB text is faked;
    only the routing-relevant source_id and rank matter to the psychoed backstop/quarantine
    logic under test), so a fixture asserting exact `knowledge_passages` equality is pinning
    this documented, deterministic shape, not an arbitrary literal.
    `abstain: true` models a retrieval that judged its own match too weak (knowledge_retrieve
    node's outcome-2 gate checks `not result.abstain` before consulting passages at all).
    """
    from sage_poc.knowledge.models import KnowledgePassage, KnowledgeResult  # noqa: PLC0415

    passages = [
        KnowledgePassage(
            text=f"fixture passage {source_id}", source_id=source_id, citation="fixture",
            relevance_score=round(0.9 - 0.1 * i, 2),
        )
        for i, source_id in enumerate(rag_top.get("passages") or [])
    ]
    return KnowledgeResult(passages=passages, abstain=bool(rag_top.get("abstain", False)))


async def run_fixture(row: dict, intent_for_sweep: str | None = None) -> dict:
    """Drive one corpus row full-graph inside the established patch context.

    Returns {"result": final_state, "audit_rows": [...]} where audit_rows are built via
    audit._build_session_audit_row from every raw state captured at EITHER
    write_session_audit call site, in chronological call order.

    Task 4 additions (see module docstring): turns[0]["state_overrides"] is merged into the
    first turn's make_e2e_state(...) call; row["rag_top"], when present, activates the F9
    retrieval-faking patch (knowledge_retrieve's DB boundary only -- see
    _fake_knowledge_result above).
    """
    if intent_for_sweep is None and any(t["intent_sweep"] for t in row["turns"]):
        raise ValueError(
            f"{row['fixture_id']}: row has intent-swept turns but no intent_for_sweep given "
            "(gate-family rows are never single-pinned)"
        )

    # The pinned intent is set per turn just before ainvoke; the mocked node reads the cell.
    pinned = {"intent": DEFAULT_INTENT}

    def _mock_intent_route(state):
        return {
            "primary_intent": pinned["intent"],
            "secondary_intent": None,
            "intent_confidence": 0.9,
            "emotional_intensity": state.get("emotional_intensity", 5),
            "engagement": state.get("engagement", 7),
            "path": state["path"] + ["intent_route"],
        }

    captured: list[dict] = []

    async def _capture_audit(state):
        captured.append(state)

    stub_llm = make_mock_llm([_FREEFLOW_STUB])

    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("sage_poc.graph.intent_route_node", side_effect=_mock_intent_route))
        stack.enter_context(patch("sage_poc.nodes.output_gate.write_session_audit", new=_capture_audit))
        stack.enter_context(patch("sage_poc.graph.write_session_audit", new=_capture_audit))
        stack.enter_context(patch("sage_poc.nodes.freeflow_respond.get_responder", return_value=stub_llm))
        stack.enter_context(patch("sage_poc.nodes.freeflow_respond.get_fallback_responder", return_value=stub_llm))
        rag_top = row.get("rag_top")
        if rag_top is not None:
            # F9 retrieval-faking (Task 4): ONLY the DB boundary is replaced. knowledge_retrieve_node
            # still runs unmocked -- _get_pool() must return a non-None sentinel (real code returns
            # abstain-everything when the pool is None) and PostgresKnowledgeRepository(pool) must
            # return an object whose .retrieve(...) resolves to the row's controlled KnowledgeResult;
            # every gating check downstream (mid-skill suppression, Classifier A, EN-only entry, L4
            # quarantine) is real, unpatched sage_poc code reading that result.
            fake_repo = MagicMock()
            fake_repo.retrieve = AsyncMock(return_value=_fake_knowledge_result(rag_top))
            stack.enter_context(
                patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=fake_repo)
            )
            stack.enter_context(patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=object()))
        # build_graph() must run INSIDE the patch context: add_node("intent_route", ...)
        # captures a direct reference to sage_poc.graph.intent_route_node at call time.
        graph = build_graph()
        result: dict | None = None
        for turn in row["turns"]:
            pinned["intent"] = (
                intent_for_sweep if turn["intent_sweep"]
                else turn.get("intent") or row.get("default_intent") or DEFAULT_INTENT
            )
            if result is None:
                state_in = make_e2e_state(turn["utterance"], **(turn.get("state_overrides") or {}))
            else:
                # Task 6: state_overrides now applies on ANY turn, not just the first. F4's
                # draft-pending-validator AR rows need it on the REPLY turn (turn index 1):
                # entry into a psychoed pathway is EN-only gated (skill_select.py order item 2),
                # so an AR row's turn 1 stays EN to establish the weave, and only the reply turn
                # carries detected_language:"ar" + a message_en gloss -- mirroring how a live AR
                # reply to an already-pending weave would arrive (PSY-WEAVE-1 evaluation is
                # correctly language-UNgated; only fresh psychoed ENTRY is EN-gated). Backward-
                # compatible: no pre-Task-6 row sets state_overrides on a non-first turn, so this
                # is additive only.
                state_in = _carry(result, turn["utterance"], **(turn.get("state_overrides") or {}))
            result = await graph.ainvoke(state_in)
            # let asyncio.create_task(write_session_audit(...)) run (both call sites)
            await asyncio.sleep(0)

    return {"result": result, "audit_rows": [_build_session_audit_row(s) for s in captured]}


def _subset_match(expected: dict, actual: dict, ctx: str) -> None:
    """Subset match with null-absence semantics.

    expected value None  -> the key must be ABSENT from actual, None, or falsy
    expected value else  -> exact equality
    """
    for key, want in expected.items():
        got = actual.get(key)
        if want is None:
            assert not got, f"{ctx}: expected {key!r} absent/None/falsy, got {got!r}"
        else:
            assert got == want, f"{ctx}: {key!r}: expected {want!r}, got {got!r}"


def _resolve_content_ref(ref: dict) -> str:
    """Task 8 (F10 diagnosis split): resolve a content reference to its ratified string,
    NEVER a literal copy pasted into a fixture (assert on behavior/markers, never copy
    strings -- the standing convention this suite already follows for block content /
    manifest fields elsewhere). One of three shapes:
      {"category": <cat>, "field": "framing_statement"|"menu_offer"|"check_in"}
      {"script": <shared_script_name>}
      {"block_id": <block_id>}
    """
    from sage_poc.psychoed import store as psy_store  # noqa: PLC0415
    if "category" in ref:
        return psy_store.manifest(ref["category"])[ref["field"]]
    if "script" in ref:
        return psy_store.shared_script(ref["script"])
    if "block_id" in ref:
        return psy_store.get_block(ref["block_id"])["content"]
    raise ValueError(f"unrecognized content ref shape: {ref!r}")


def _assert_content(row: dict, result: dict, ctx: str) -> None:
    """Task 8 (F10 diagnosis split): optional row-level `assert_content` field, schema-
    neutral like every other additive marker in this driver. `{"contains": [...], "excludes":
    [...]}`, each entry a content ref resolved by `_resolve_content_ref` above and checked
    for presence/absence as a substring of the final turn's response. Applied unconditionally
    at the top of `assert_expectations` (before any label-class branching) so it holds
    regardless of which disposition-assertion shape a row otherwise uses -- harmless no-op
    for the overwhelming majority of rows that don't set it.
    """
    spec = row.get("assert_content")
    if not spec:
        return
    response = result.get("response") or ""
    for ref in spec.get("contains") or []:
        copy = _resolve_content_ref(ref)
        assert copy in response, f"{ctx}: assert_content.contains violated: {ref!r} not found in response"
    for ref in spec.get("excludes") or []:
        copy = _resolve_content_ref(ref)
        assert copy not in response, f"{ctx}: assert_content.excludes violated: {ref!r} found in response"


def assert_expectations(row: dict, out: dict, intent_for_sweep: str | None = None) -> None:
    """Label-class assertion split (plan amendment 09d8ff59, human-ruled):

    - EVERY label: disposition (if the row asserts one) + the never-proceed invariant for
      gate rows expecting escalation (a weave-pending reply produces no psychoed serve and
      no menu, under any classification whatsoever).
    - Escalation MECHANISM assertions (expect.audit escalation row, expect.state Task-8
      pathway clear): ONLY on labels in WEAVE_EVALUATOR_LABELS. Under the "crisis" label
      escalation arrives via the intent-route crisis path (crisis_response without
      psychoed_weave_escalation), so neither the "escalated" audit patch nor the
      escalation-scoped pathway clear fires -- both mechanism assertion sets would fail
      there for the wrong reason. Rows not expecting escalation (e.g. F8 absence rows)
      keep their audit/state expectations on every label.

    Task 6 adds a THIRD split for `row["clear_no"] == True` (F4's clear-no family; see the
    module docstring's "Task 6 driver extensions" section for the full reasoning): these rows
    do NOT expect escalate_crisis as a uniform disposition (they're clear negatives), but the
    "crisis" label still forces escalate_crisis via crisis-intent supremacy -- a structural
    graph property independent of the reply's actual content -- while every other label expects
    the menu-after-weave mechanism-witness shape. Handled as an early, self-contained branch
    below (returns before the escalation-row logic, which does not apply to these rows).

    Task 8 adds a FOURTH split, `row["label_dispositions"]` (F6 precedence; see "Task 8 driver
    extensions" in the module docstring): a per-label disposition map for rows whose winning
    route genuinely varies by sweep label for reasons ORTHOGONAL to psychoed (baseline graph
    precedence/routing quirks that predate this family), while the property F6 actually gates
    on -- psychoed never wins the turn -- holds uniformly across every label regardless. Also
    self-contained; returns before the escalation-row logic below.
    """
    expect = row["expect"]
    ctx = row["fixture_id"] if intent_for_sweep is None else f"{row['fixture_id']}[{intent_for_sweep}]"
    result = out["result"]

    _assert_content(row, result, ctx)

    if row.get("label_dispositions"):
        label_map = row["label_dispositions"]
        expected = label_map.get(intent_for_sweep, label_map.get("_default"))
        if expected is not None:
            got = _observed(result)
            assert got == expected, (
                f"{ctx}: label_dispositions[{intent_for_sweep!r}]: expected {expected!r}, "
                f"observed {got!r} (gate_path={result.get('gate_path')!r}, "
                f"skill_match_method={result.get('skill_match_method')!r})"
            )
        # The universal F6 property, independent of WHICH non-psychoed route wins on a given
        # label: psychoed never wins a precedence conflict. Holds under every sweep label
        # without exception (100% hard gate) -- unlike expects_escalation's never-proceed
        # block below, this deliberately does NOT check psychoed_menu_offered, since an
        # ordinary (non-weave) safety-exit does not clear the pathway on the SAME turn (handoff
        # notes delta 8: "_psychoed_pathway_clear" only runs from the weave-escalation exit and
        # skill_select's own non-psychoed-skill/HR/offer-accept exits) -- a mid-menu turn's
        # STALE `psychoed_menu_offered: true`, carried over from the turn that genuinely
        # offered it, is not evidence psychoed won THIS turn.
        assert not result.get("psychoed_serve"), (
            f"{ctx}: never-proceed violated: psychoed serve payload present when a "
            f"higher-precedence route should have won"
        )
        assert result.get("skill_match_method") not in (
            "psychoed_resolver", "psychoed_menu_after_weave"
        ), f"{ctx}: never-proceed violated: {result.get('skill_match_method')!r}"
        # Non-leak (design doc §6.3, #359 pattern): whichever non-psychoed route won, the
        # emitted response must carry no psychoed copy fragment from the row's own armed
        # category -- assert on behavior (the manifest's own ratified strings), never a
        # hand-copied literal pasted into the fixture. Single-category rows only (the
        # overwhelming majority); a future multi-category label_dispositions row would need
        # its own per-category loop, not implemented here since none exists yet.
        _category = row.get("category")
        if _category:
            from sage_poc.psychoed import store as psy_store  # noqa: PLC0415
            _manifest = psy_store.manifest(_category)
            _response = result.get("response") or ""
            for _field in ("framing_statement", "menu_offer", "check_in"):
                _copy = _manifest.get(_field)
                if _copy:
                    assert _copy not in _response, (
                        f"{ctx}: non-leak violated: category {_category!r}'s {_field!r} "
                        f"psychoed copy fragment found in the winning route's response"
                    )
        audit_expect = expect.get("audit")
        if audit_expect:
            assert out["audit_rows"], f"{ctx}: audit expectations given but no audit rows captured"
            _subset_match(audit_expect, out["audit_rows"][-1], f"{ctx} audit (last row)")
        state_expect = expect.get("state")
        if state_expect:
            _subset_match(state_expect, result, f"{ctx} state")
        return

    if row.get("clear_no"):
        if intent_for_sweep == "crisis":
            got = _observed(result)
            assert got == "escalate_crisis", (
                f"{ctx}: crisis-intent supremacy violated: a weave-pending reply classified "
                f"'crisis' by intent_route must escalate regardless of the reply's own clear-no "
                f"content (structural graph property, not a weave outcome) -- observed {got!r} "
                f"(gate_path={result.get('gate_path')!r}, "
                f"skill_match_method={result.get('skill_match_method')!r})"
            )
            assert not result.get("psychoed_menu_offered"), (
                f"{ctx}: crisis-intent supremacy violated: menu offered despite crisis-label "
                f"routing"
            )
            return
        # Every other label: the weave evaluator ran (mechanism witness) and the outcome is
        # the deferred menu-after-weave continuation -- never a bare resolver serve, never a
        # skipped evaluation. expect.disposition is deliberately null on clear_no rows (see the
        # module docstring); expect.audit/expect.state carry the mechanism-derived fields.
        assert not result.get("psychoed_weave_escalation"), (
            f"{ctx}: clear-no reply unexpectedly escalated to crisis"
        )
        audit_expect = expect.get("audit")
        if audit_expect:
            assert out["audit_rows"], f"{ctx}: audit expectations given but no audit rows captured"
            _subset_match(audit_expect, out["audit_rows"][-1], f"{ctx} audit (last row)")
        state_expect = expect.get("state")
        if state_expect:
            _subset_match(state_expect, result, f"{ctx} state")
        return

    disposition = expect.get("disposition")
    expects_escalation = disposition == "escalate_crisis"

    if disposition is not None:
        got = _observed(result)
        assert got == disposition, (
            f"{ctx}: disposition: expected {disposition!r}, observed {got!r} "
            f"(gate_path={result.get('gate_path')!r}, "
            f"skill_match_method={result.get('skill_match_method')!r})"
            + (
                "\nA weave-pending reply PROCEEDING unevaluated (serve/menu/freeflow "
                "instead of escalation) is a BLOCKED finding for adjudication, not a "
                "fixture bug -- do not weaken the fixture."
                if expects_escalation else ""
            )
        )

    if row["family"] in GATE_FAMILIES and expects_escalation:
        # Never-proceed invariant: holds under EVERY label, sentinel included.
        assert not result.get("psychoed_serve"), (
            f"{ctx}: never-proceed violated: psychoed serve payload present on a "
            f"weave-pending reply turn"
        )
        assert not result.get("psychoed_menu_offered"), (
            f"{ctx}: never-proceed violated: menu offered on a weave-pending reply turn"
        )
        assert result.get("skill_match_method") not in (
            "psychoed_resolver", "psychoed_menu_after_weave"
        ), f"{ctx}: never-proceed violated: {result.get('skill_match_method')!r}"

    mechanism_applies = (
        not expects_escalation
        or intent_for_sweep is None
        or intent_for_sweep in WEAVE_EVALUATOR_LABELS
    )

    audit_expect = expect.get("audit")
    if audit_expect and mechanism_applies:
        assert out["audit_rows"], f"{ctx}: audit expectations given but no audit rows captured"
        _subset_match(audit_expect, out["audit_rows"][-1], f"{ctx} audit (last row)")

    state_expect = expect.get("state")
    if state_expect and mechanism_applies:
        _subset_match(state_expect, result, f"{ctx} state")


# ---------------------------------------------------------------------------
# Parametrization: discover families from the corpus directory
# ---------------------------------------------------------------------------

def _discovered_families(fixtures_dir: pathlib.Path = FIXTURES_DIR) -> list[str]:
    fams = set()
    for path in fixtures_dir.glob("f*_*.jsonl"):
        m = re.match(r"^(f\d+)_", path.name)
        if m:
            fams.add(m.group(1).upper())
    return sorted(fams)


def _is_ar_draft(row: dict) -> bool:
    """Task 6: AR rows that are draft-pending-validator (F4's AR counterparts, at minimum) --
    schema-neutral opt-out, same additive pattern as flag_pair_check/baseline_only. Requires
    BOTH lang=="ar" AND the explicit status marker, not lang alone, so a future validator-graded
    AR row (status left null/absent once the chain lands) is NOT silently excluded here -- the
    opt-out is deliberate-and-labeled, not lang-triggered."""
    return row.get("lang") == "ar" and row.get("status") == "draft-pending-validator"


_XFAIL_TICKET = "docs/superpowers/tickets/2026-07-30-menu-label-short-token-substring-collision.md"


def _xfail_marks_for(row: dict, intent: str) -> list:
    """Adjudication fix round 1 (2026-07-30, human-ruled): F4-002 (bare "no" clear-no reply)
    stays authored to the spec-intended clinician contract -- the mechanism is NOT touched and
    the fixture is NOT weakened -- but its 8 known-failing sweep cases (every WEAVE_EVALUATOR_
    LABELS member; the "crisis" case is unaffected and keeps failing/passing on its own terms)
    are disposed as STRICT xfail, citing the divergence ticket (`_XFAIL_TICKET`), instead of a
    bare CI-red FAIL. `strict=True` is load-bearing, not decorative: when the mechanism fix
    lands (word-boundary/min-length guard on resolver.py's _match_menu_label, per the ticket),
    these cases will start passing, and a strict xfail that unexpectedly passes is ITSELF
    reported as a failure (XPASS(strict) -> test failure) -- which is exactly the "loud xpass
    forces a re-pin" property the ticket's definition-of-done requires, not a mechanism to let
    the fix land unnoticed.

    A row opts in via the optional row-level `xfail_intents` field (list of intent-sweep labels;
    schema-neutral, same additive pattern as `clear_no`/`flag_pair_check`/`baseline_only`) --
    general-purpose, not hardcoded to F4-002, so any future adjudicated-and-ticketed gate-family
    gap can use the same disposition without a new driver mechanism. Returns `[]` (no marks) for
    every row/intent pair that doesn't opt in, which is the overwhelming majority -- ordinary
    rows are completely unaffected.
    """
    xfail_intents = row.get("xfail_intents")
    if not xfail_intents or intent not in xfail_intents:
        return []
    return [pytest.mark.xfail(
        reason=(
            f"{row['fixture_id']}[{intent}]: adjudicated 2026-07-30 (fix round 1) -- known "
            f"mechanism gap, NOT a fixture bug. See {_XFAIL_TICKET} for the full trace "
            f"(short-token substring collision in resolver.py's _match_menu_label tier-1 "
            f"containment check). strict=True: when the fix lands this turns XPASS, which "
            f"fails CI loudly and forces the definition-of-done re-pin."
        ),
        strict=True,
    )]


def _row_xfail_marks(row: dict) -> list:
    """Task 8 fix round 1 (2026-07-31, human-ruled adjudication): the per-ROW equivalent of
    `_xfail_marks_for` above, for families with no intent sweep (F10 has none -- every F10
    row runs once, `intent_for_sweep=None`), so the intent-keyed `xfail_intents` mechanism
    doesn't apply. A row opts in via the optional row-level `xfail` field:
    `{"reason": <str>, "ticket": <path>}` (schema-neutral, same additive pattern as
    `xfail_intents`). `strict=True` for the same reason as `_xfail_marks_for`: an unexpected
    XPASS (the fix landing) fails CI loudly and forces the row's re-pin, rather than letting
    a landed fix go uncelebrated. Minimal, general-purpose (not hardcoded to F10-004) --
    returns `[]` for every row that doesn't opt in.
    """
    spec = row.get("xfail")
    if not spec:
        return []
    return [pytest.mark.xfail(
        reason=f"{row['fixture_id']}: {spec['reason']} (ticket: {spec['ticket']})",
        strict=True,
    )]


def _all_params() -> list:
    params = []
    for family in _discovered_families():
        for row in load_family(family):
            if row.get("flag_pair_check"):
                # Handled by test_psychoed_f8_flag_conformance_neutral's paired ON/OFF
                # execution below, not by the single-arm expect-matching path here.
                continue
            if row.get("baseline_only"):
                # Handled by test_psychoed_baseline_only's non-gating path below, not by
                # the hard-required expect-matching path here. See that test's section
                # (search "baseline_only: non-gating registration") for the mechanism.
                continue
            if _is_ar_draft(row):
                # Task 6: F4's AR rows are draft-pending-validator -- handled by
                # test_psychoed_ar_draft_pending_validator's skipped-with-count registration
                # below (search "AR draft-pending-validator"), never by the hard-required
                # expect-matching path here.
                continue
            swept = any(t.get("intent_sweep") for t in row["turns"])
            if family in GATE_FAMILIES and swept:
                for intent in INTENT_SWEEP:
                    params.append(
                        pytest.param(
                            row, intent, id=f"{row['fixture_id']}-{intent}",
                            marks=_xfail_marks_for(row, intent),
                        )
                    )
            else:
                params.append(
                    pytest.param(row, None, id=row["fixture_id"], marks=_row_xfail_marks(row))
                )
    return params


# Task 8 (F6 precedence): the ONLY config attrs a row's optional `flags` dict may monkeypatch,
# beyond PSYCHOED_PATHWAYS_ENABLED/PSYCHOED_CATEGORIES which _arm_psychoed already owns.
# Allowlisted (not an arbitrary setattr) so a typo'd or malicious key fails loudly at fixture-
# run time instead of silently patching an unrelated config surface. F6's medical-mid-menu row
# needs MEDICAL_REDFLAG_GUARD_ENABLED (default OFF, env-gated -- see config.py) armed in the
# SAME patch-context-only, never-env-persisted discipline as every other flag in this driver.
_ALLOWED_ROW_FLAGS = frozenset({"MEDICAL_REDFLAG_GUARD_ENABLED"})


def _arm_psychoed(monkeypatch, row: dict) -> None:
    """SAGE_PSYCHOED_PATHWAYS=true semantics + the fixture's category(ies), monkeypatch-only.

    Task 4: a row may carry `categories` (list) instead of the single `category` string --
    needed for F2's genuine cross-category collisions, which resolver.py only resolves when
    BOTH colliding categories are simultaneously enabled (see module docstring). `categories`
    wins when present; falls back to the pre-existing single-`category` behavior otherwise.

    Task 8: a row may also carry `flags` (dict of config attr name -> value), monkeypatched
    the same way -- patch-context only, never env-persisted (this task's own "flags patch-
    context only" rule). Restricted to `_ALLOWED_ROW_FLAGS` above.
    """
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    if row.get("categories"):
        cats = frozenset(row["categories"])
    elif row.get("category"):
        cats = frozenset({row["category"]})
    else:
        cats = frozenset()
    monkeypatch.setattr(config, "PSYCHOED_CATEGORIES", cats)
    for _flag, _value in (row.get("flags") or {}).items():
        assert _flag in _ALLOWED_ROW_FLAGS, (
            f"{row['fixture_id']}: row['flags'] key {_flag!r} is not in _ALLOWED_ROW_FLAGS "
            f"{sorted(_ALLOWED_ROW_FLAGS)} -- add it there deliberately, don't widen silently"
        )
        monkeypatch.setattr(config, _flag, _value)


def _disarm_psychoed(monkeypatch) -> None:
    """Flag-OFF counterpart to _arm_psychoed (Task 2 driver extension): full disarm, for
    the paired conformance-neutrality check below. Monkeypatch-only, never env-persisted."""
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", False)
    monkeypatch.setattr(config, "PSYCHOED_CATEGORIES", frozenset())


@pytest.mark.parametrize("row,intent", _all_params())
async def test_psychoed_fixture(row, intent, monkeypatch):
    _arm_psychoed(monkeypatch, row)
    out = await run_fixture(row, intent_for_sweep=intent)
    assert_expectations(row, out, intent_for_sweep=intent)


# ---------------------------------------------------------------------------
# F8 matrix-rows-unmoved: paired flag ON/OFF conformance-neutrality (Task 2 driver
# extension). Minimal addition: a row opts in via the top-level "flag_pair_check": true
# marker (schema-neutral -- _validate_row does not reject unknown keys), is excluded from
# the single-arm _all_params() sweep above, and instead runs its turns TWICE here: once
# with the psychoed pathway armed for the row's category, once fully disarmed. The
# assertion is EQUALITY of the observed disposition between the two runs, not a pinned
# disposition value -- this is what makes it "mechanical": the property under test is
# "the flag never moves this row's disposition", regardless of what that disposition is.
# ---------------------------------------------------------------------------

def _matrix_pair_params() -> list:
    params = []
    for row in load_family("F8"):
        if row.get("flag_pair_check"):
            params.append(pytest.param(row, id=row["fixture_id"]))
    return params


@pytest.mark.parametrize("row", _matrix_pair_params())
async def test_psychoed_f8_flag_conformance_neutral(row, monkeypatch):
    """matrix-rows-unmoved (Task 2): rows reusing spec_ids from
    tests/fixtures/bot_behaviour_audit/layer1_trigger_corpus.jsonl for the 6 psychoed-
    adjacent categories. Runs the row with the psychoed pathway armed for its category,
    then again fully disarmed, and asserts the OBSERVED disposition is identical both
    ways -- the flag must be conformance-neutral for pre-existing Layer-1 matrix rows
    outside its own trigger tables. A row whose disposition MOVES between arm settings
    is a BLOCKED finding for adjudication (the flag is additive-only over the pre-
    psychoed graph, never disposition-moving elsewhere), not a fixture to bend.
    """
    _arm_psychoed(monkeypatch, row)
    out_on = await run_fixture(row)
    disposition_on = _observed(out_on["result"])

    _disarm_psychoed(monkeypatch)
    out_off = await run_fixture(row)
    disposition_off = _observed(out_off["result"])

    assert disposition_on == disposition_off, (
        f"{row['fixture_id']}: conformance-neutrality violated: flag ON -> {disposition_on!r}, "
        f"flag OFF -> {disposition_off!r}. BLOCKED finding for adjudication, not a fixture bug."
    )


# ---------------------------------------------------------------------------
# baseline_only: non-gating registration (Task 3). A row opts in via the top-level
# "baseline_only": true marker -- schema-neutral (_validate_row does not reject unknown
# keys, same additive pattern as F8's "flag_pair_check"). This is how f1_naturalistic.jsonl
# (the blind-authored F1 naturalistic set) shares family "F1" -- and therefore the f1_*.jsonl
# glob in load_family/load_corpus -- with the green-required f1_wiring.jsonl without ever
# entering the hard-required sweep: _all_params() excludes baseline_only rows outright (see
# above), and they run ONLY through test_psychoed_baseline_only below.
#
# What "baseline-only" means mechanically:
#   - COLLECTED + SCHEMA-VALIDATED: load_family()/load_corpus() run _validate_row on every
#     baseline_only row exactly like any other row (including the corpus-wide fixture_id
#     uniqueness check) -- a malformed row still fails CI at collection time.
#   - FIXTURE-OUTCOME NEVER GATING: the row is driven full-graph and its expectations are
#     checked via assert_expectations, but the test is marked xfail(strict=False) (same
#     idiom as this codebase's other known-gap suites, e.g. test_safety_detection.py's
#     test_safety_known_gap) -- a mismatch reports XFAIL, a match reports XPASS, and EITHER
#     outcome is a normal, green pytest run. Nothing here can fail CI except a genuine
#     schema violation or a hard crash building/loading the corpus.
# Baseline MEASUREMENT (recall-by-category, the number for the clinician bar) is Task 10's
# job, not this driver's -- this only keeps the set runnable and visible in `-rxX` pytest
# output so a future measurement pass has something to point at.
# ---------------------------------------------------------------------------

def _baseline_only_params() -> list:
    params = []
    for family in _discovered_families():
        for row in load_family(family):
            if row.get("baseline_only"):
                params.append(pytest.param(row, id=row["fixture_id"]))
    return params


@pytest.mark.xfail(
    reason="baseline_only: F1 naturalistic (blind-authored) recall is a TRACKED BASELINE, "
           "never a hard gate (spec §7.1 / plan Global Constraints). XFAIL = row missed "
           "psychoed_serve/category this run; XPASS = row hit. Neither fails CI. Task 10 "
           "measures recall-by-category from this same set; do not chase individual rows here.",
    strict=False,
)
@pytest.mark.parametrize("row", _baseline_only_params())
async def test_psychoed_baseline_only(row, monkeypatch):
    _arm_psychoed(monkeypatch, row)
    out = await run_fixture(row)
    assert_expectations(row, out)


# ---------------------------------------------------------------------------
# AR draft-pending-validator: skipped-with-count registration (Task 6). F4's AR rows
# (lang=="ar", status=="draft-pending-validator") are collected and schema-validated like any
# other row (load_family/load_corpus run _validate_row on them, corpus-wide fixture_id
# uniqueness included -- a malformed AR row still fails CI at collection time), but are excluded
# from _all_params()'s hard-required sweep (see _is_ar_draft above) and NEVER executed against
# the mechanism here: no AR PSY-WEAVE-1 allowlist data exists yet, so there is nothing validated
# to assert against, and per spec 3.7 / the AR-gating design, nothing AR-labeled is quotable as
# coverage until the faithfulness-graded validator chain lands.
#
# Each row is registered as its own pytest.mark.skip parametrized case (not silently omitted)
# so pytest's own summary output (`-rs`, or the default short summary line) carries a VISIBLE,
# per-row skip reason plus an aggregate "N skipped" count -- spec §7.2 no-silent-caps. This
# mirrors baseline_only's "collected + schema-validated, never hard-gating" shape above, but
# skip (not xfail) is the right primitive here: these rows have no `expect` to compare against
# at all (deliberately null), so there is no pass/fail outcome to record, only "not yet
# executable."
# ---------------------------------------------------------------------------

def _ar_draft_params() -> list:
    params = []
    for family in _discovered_families():
        for row in load_family(family):
            if _is_ar_draft(row):
                params.append(pytest.param(row, id=row["fixture_id"]))
    return params


@pytest.mark.skip(
    reason="AR rows are draft-pending-validator (Task 6): unvalidated author translations, no "
           "AR PSY-WEAVE-1 allowlist data file is ratified yet, nothing AR-labeled is quotable "
           "as coverage until the faithfulness-graded AR validator chain exists. Collected + "
           "schema-validated (see test_f4_ar_rows_present_and_flagged_draft); never executed."
)
@pytest.mark.parametrize("row", _ar_draft_params())
async def test_psychoed_ar_draft_pending_validator(row):
    raise AssertionError("unreachable: this test is unconditionally skipped (see reason above)")


def test_f4_ar_rows_present_and_flagged_draft():
    """Always-running companion to the skip registration above: a genuinely empty or
    mislabeled AR set must fail loudly, not silently read as "AR coverage: zero, nobody
    noticed" (no-silent-caps in the negative direction too). Prints the visible count."""
    ar_rows = [r for r in load_family("F4") if r.get("lang") == "ar"]
    assert ar_rows, (
        "F4 AR rows are missing entirely -- no-silent-caps: this must never be silently zero "
        "(see task-6-brief.md: clear-no/clear-yes/ambiguous AR counterparts are required)"
    )
    mislabeled = [r["fixture_id"] for r in ar_rows if r.get("status") != "draft-pending-validator"]
    assert not mislabeled, (
        f"F4 AR rows must all carry status=='draft-pending-validator' until the AR "
        f"faithfulness-graded validator chain exists: {mislabeled}"
    )
    print(
        f"\n[F4 AR] {len(ar_rows)} lang='ar' row(s) present, all status='draft-pending-validator', "
        f"skipped from the hard gate (see test_psychoed_ar_draft_pending_validator)."
    )


def test_f4_002_xfail_intents_are_counted_and_cite_ticket():
    """Adjudication fix round 1 (2026-07-30): F4-002's mechanism gap is disposed as strict xfail,
    not a fixture bug and not silently absorbed. Independent of pytest's own -rxX summary count,
    this always-running test makes the xfail set itself visible + counted (no-silent-caps, same
    posture as the AR skip count above) and pins that the row's disposition is exactly the
    adjudicated shape: every WEAVE_EVALUATOR_LABELS member xfails, "crisis" is untouched, and the
    row's source field cites the ticket."""
    f4_by_id = {r["fixture_id"]: r for r in load_family("F4")}
    row = f4_by_id["F4-002"]
    xfail_intents = set(row.get("xfail_intents") or [])
    assert xfail_intents, (
        "F4-002 must carry xfail_intents -- adjudicated 2026-07-30 strict-xfail disposition, "
        "see docs/superpowers/tickets/2026-07-30-menu-label-short-token-substring-collision.md"
    )
    assert xfail_intents == WEAVE_EVALUATOR_LABELS, (
        f"F4-002's xfail_intents must be EXACTLY WEAVE_EVALUATOR_LABELS (the 'crisis' label is "
        f"unaffected by the collision -- crisis-intent supremacy bypasses skill_select entirely "
        f"-- and must keep running/passing normally, not xfail): got {sorted(xfail_intents)}, "
        f"expected {sorted(WEAVE_EVALUATOR_LABELS)}"
    )
    assert _XFAIL_TICKET in (row.get("source") or ""), (
        f"F4-002's source field must cite the divergence ticket ({_XFAIL_TICKET})"
    )
    print(
        f"\n[F4-002 xfail] {len(xfail_intents)} sweep intent(s) marked strict-xfail "
        f"(ticket: {_XFAIL_TICKET}); 'crisis' sweep case runs normally (not xfailed)."
    )


# ---------------------------------------------------------------------------
# F10 (Task 8) push-further companion: TRACE what the as-built continuation actually
# composes for f10_diagnosis.jsonl's F10-003 scenario. run_fixture's generic driver doesn't
# capture the LLM prompt (its stub_llm is a fixed-reply mock, not a capturing one -- mirrors
# test_psychoed_f5_flow.py's own reason for needing a dedicated capturing helper), so this is
# a standalone procedural test, not a corpus row, reusing F10-003's exact turns.
# ---------------------------------------------------------------------------

def test_f10_push_further_stage2_not_deterministically_composed():
    """F10-003's own `source` field states the trace conclusion; this test performs it.
    diagnosis_guard_stage1 primed the exchange, then a push-further reply that matches no
    resolver trigger reaches freeflow_respond via the generic psychoed_continuation L2
    override (delta 15) -- captures the ACTUAL messages list passed to the LLM and confirms
    diagnosis_guard_stage2's own text is absent, i.e. genuinely not deterministically
    reachable, not merely unasserted."""
    from sage_poc.psychoed import store as psy_store  # noqa: PLC0415

    pinned = {"intent": "info_request"}

    def _mock_intent_route(state):
        return {
            "primary_intent": pinned["intent"], "secondary_intent": None,
            "intent_confidence": 0.9, "emotional_intensity": state.get("emotional_intensity", 5),
            "engagement": state.get("engagement", 7), "path": state["path"] + ["intent_route"],
        }

    calls: list = []

    def _capturing_llm(text: str):
        mock = MagicMock()
        mock.model_name = "mock-model"
        mock.openai_api_base = ""
        mock.bind_tools = MagicMock(return_value=mock)

        async def _ainvoke(*args, **kwargs):
            calls.append(args[0] if args else kwargs.get("input"))
            msg = MagicMock()
            msg.content = text
            msg.tool_calls = []
            return msg

        mock.ainvoke = AsyncMock(side_effect=_ainvoke)
        return mock

    stub_llm = _capturing_llm(_FREEFLOW_STUB)

    async def _drive():
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch("sage_poc.graph.intent_route_node", side_effect=_mock_intent_route))
            stack.enter_context(patch("sage_poc.nodes.freeflow_respond.get_responder", return_value=stub_llm))
            stack.enter_context(patch("sage_poc.nodes.freeflow_respond.get_fallback_responder", return_value=stub_llm))
            with patch.object(config, "PSYCHOED_PATHWAYS_ENABLED", True), \
                 patch.object(config, "PSYCHOED_CATEGORIES", frozenset({"1f"})):
                graph = build_graph()
                t1 = await graph.ainvoke(make_e2e_state("do I have GAD"))
                t2 = await graph.ainvoke(_carry(t1, "please just tell me, I really need to know"))
        return t1, t2

    t1, t2 = asyncio.run(_drive())

    assert t1["psychoed_matched_row_id"] == "1f-t3"  # sanity: the stage-1 trigger genuinely hit
    assert t2["skill_match_method"] is None
    assert not t2.get("psychoed_serve")
    assert t2["psychoed_active_category"] == "1f", "pathway persists, un-hijacked"

    assert calls, "freeflow LLM must have been invoked for the push-further turn"
    user_prompt = next(m["content"] for m in calls[-1] if m["role"] == "user")
    stage2_script = psy_store.shared_script("diagnosis_guard_stage2")
    assert stage2_script not in user_prompt, (
        "TRACE conclusion (reworded per review LOW 4a, 2026-07-31): diagnosis_guard_stage2 has "
        "NO ENGINEERED MECHANISM AT ANY TIER -- zero references anywhere in src/sage_poc/ (grep-"
        "confirmed), not 'rides the LLM with some steering.' The composed prompt carries no "
        "diagnosis-specific signal whatsoever; a future flip-tier run (Task 9, real LLM) may "
        "OBSERVE the model rendering something resembling stage-2's substance on its own "
        "initiative given the conversation history, but that would be unengineered LLM behavior, "
        "not a mechanism this codebase built or steers toward -- nothing here should be read as "
        "'stage-2 rides the LLM continuation' in the sense of a designed handoff."
    )
    continuation_marker = "conversational glue only"
    assert continuation_marker in user_prompt, (
        "the generic psychoed_continuation glue renders instead -- confirms which mechanism "
        "actually handles this turn"
    )


def test_f10_formal_diagnosis_guard_question_clipped_by_one_question_cap():
    """Companion mechanical proof for the finding documented in f10_diagnosis.jsonl's F10-002
    `source` field: 1f's own framing_statement ends in a question, so output_gate.py's
    PRE-EXISTING, unrelated `_limit_to_one_question` discipline (Node 8, ~L836-841) strips
    diagnosis_guard_stage1's own trailing consent question ('Want me to walk through that?')
    every time formal_diagnosis fires on this category -- confirmed here via the real,
    declared marker the discipline itself adds to `path` when it actually modifies the
    turn, not via a hand-typed copy excerpt."""
    pinned = {"intent": "info_request"}

    def _mock_intent_route(state):
        return {
            "primary_intent": pinned["intent"], "secondary_intent": None,
            "intent_confidence": 0.9, "emotional_intensity": state.get("emotional_intensity", 5),
            "engagement": state.get("engagement", 7), "path": state["path"] + ["intent_route"],
        }

    stub_llm = make_mock_llm([_FREEFLOW_STUB])

    async def _drive():
        with patch("sage_poc.graph.intent_route_node", side_effect=_mock_intent_route), \
             patch("sage_poc.nodes.freeflow_respond.get_responder", return_value=stub_llm), \
             patch("sage_poc.nodes.freeflow_respond.get_fallback_responder", return_value=stub_llm), \
             patch.object(config, "PSYCHOED_PATHWAYS_ENABLED", True), \
             patch.object(config, "PSYCHOED_CATEGORIES", frozenset({"1f"})):
            graph = build_graph()
            return await graph.ainvoke(make_e2e_state("do I have GAD"))

    result = asyncio.run(_drive())

    assert result["psychoed_matched_row_id"] == "1f-t3"  # sanity: the formal_diagnosis trigger hit
    assert "question_discipline_applied" in result["path"], (
        "the one-question-cap discipline must have fired this turn (proving it, not just "
        "asserting the reshaped text's absence)"
    )
    from sage_poc.psychoed import store as psy_store  # noqa: PLC0415
    stage1_script = psy_store.shared_script("diagnosis_guard_stage1")
    assert stage1_script not in result["response"], (
        "sanity: the FULL script (including its trailing consent question) is genuinely "
        "absent, not merely unasserted -- this is what makes the finding real"
    )


def test_f10_flip_tier_only_rows_present_and_counted():
    """spec 7.2 no-silent-caps, same posture as the AR-skip-count (F4) and F9's CI-tier-only
    marking: F10's `flip_tier_only` rows are collected + schema-validated like any other row
    and DO run their CI-tier `expect` block (they are not excluded from _all_params() -- only
    the CONTENT question they flag is deferred), but the marker itself must be visible and
    counted so it is never silently invisible that a row's fuller claim rides on a future
    tier. Fails loudly (rather than reading as zero-coverage-nobody-noticed) if the set is
    ever empty.

    Reworded per review LOW 4a (2026-07-31): 'flip-tier-only' does NOT mean 'this claim is
    checkable at flip tier' -- diagnosis_guard_stage2 has no engineered mechanism at any tier
    (zero src/ references). Flip tier only ever gets to OBSERVE, never assert against a
    designed behavior."""
    f10_rows = load_family("F10")
    flip_tier_rows = [r for r in f10_rows if r.get("flip_tier_only")]
    assert flip_tier_rows, (
        "no F10 rows carry flip_tier_only -- no-silent-caps: if F10-003's push-further "
        "stage-2-content deferral is ever removed, this must fail loudly, not silently read "
        "as zero flip-tier-only rows"
    )
    print(
        f"\n[F10 flip-tier-only] {len(flip_tier_rows)} row(s) carry flip_tier_only: "
        f"{[(r['fixture_id'], r['flip_tier_only']) for r in flip_tier_rows]} -- NONE of the "
        f"claim(s) named there have any engineered mechanism at ANY tier (zero src/sage_poc/ "
        f"references for diagnosis_guard_stage2). A future Task 9 flip-tier run (real "
        f"intent_route + a real LLM call) may OBSERVE the live LLM rendering something "
        f"resembling this content unprompted, given conversation history -- that is unengineered "
        f"model behavior, never an assertion this or any future driver can make against a "
        f"designed mechanism."
    )


_F10_004_XFAIL_TICKET = "docs/superpowers/tickets/2026-07-31-diagnosis-guard-consent-to-serve-unbuilt.md"


def test_f10_004_xfail_and_cites_ticket():
    """Adjudication fix round 1 (2026-07-31): F10-004's finding (the diagnosis-guard
    consent-to-serve mechanism, design doc 5.5's yes-branch, is unimplemented) is disposed as
    strict xfail via the row-level `xfail` marker (`_row_xfail_marks`), not silently absorbed.
    Independent of pytest's own -rxX summary, this always-running test makes the disposition
    itself visible + counted (no-silent-caps, same posture as F4-002's own xfail-citation
    test) and pins that the row cites the right ticket in both `xfail` and `source`."""
    f10_by_id = {r["fixture_id"]: r for r in load_family("F10")}
    row = f10_by_id["F10-004"]
    xfail_spec = row.get("xfail")
    assert xfail_spec, (
        "F10-004 must carry an `xfail` marker -- adjudicated 2026-07-31 fix round 1, disposed "
        "as spec-sanctioned-behavior-UNBUILT, see " + _F10_004_XFAIL_TICKET
    )
    assert xfail_spec.get("ticket") == _F10_004_XFAIL_TICKET, (
        f"F10-004's xfail.ticket must be exactly {_F10_004_XFAIL_TICKET!r}, "
        f"got {xfail_spec.get('ticket')!r}"
    )
    assert _F10_004_XFAIL_TICKET in (row.get("source") or ""), (
        f"F10-004's source field must also cite the ticket ({_F10_004_XFAIL_TICKET})"
    )
    print(f"\n[F10-004 xfail] strict-xfail, ticket: {_F10_004_XFAIL_TICKET}")


# ---------------------------------------------------------------------------
# F10-004b (Task 8 fix round 1, adjudicated): companion GREEN, GATING regression floor for
# F10-004's finding. Reuses run_fixture's own `rag_top` retrieval-faking hook (Task 4, F9's
# mechanism -- generic to any row/family, not F9-specific) to construct a scenario where block
# content IS plausibly retrievable (a psychoed block ranks alongside a real KB passage) on the
# consented-yes continuation turn, and confirms the interim floor holds: L4 quarantine strips
# the psychoed passage before it ever reaches the composed prompt, and no psychoed_serve
# fires. Deliberately NOT the "psychoed block ranks FIRST, not abstained" shape (F9-001's own
# scenario) -- that shape legitimately fires knowledge_retrieve's outcome-2 backstop and SERVES
# the block (verified directly before choosing this row's rag_top shape: a rank-1, non-abstained
# psychoed passage produces a genuine psychoed_serve with psychoed_gate_action=="pass", which
# would conflate "the backstop legitimately served content" with "quarantine failed to protect
# an unconsented turn" -- two different properties). The rank-2 shape (F9-003's own mechanism)
# is the one that isolates "retrieval considered this content, quarantine must still strip it."
# ---------------------------------------------------------------------------

def test_f10_004b_consented_yes_no_block_leak_llm_prompt_capture():
    """Node-level companion to F10-004b's corpus row (which asserts knowledge_passages via
    expect.state, run through the generic driver): this test additionally captures the ACTUAL
    messages list passed to the freeflow LLM for the identical scenario and confirms the
    quarantined block's content is absent from what the model literally saw -- per this fix
    round's explicit instruction to VERIFY the floor, not assume it from the final response
    alone (a stub LLM's reply is fixed regardless of what's in the prompt, so asserting only
    against `response` would prove nothing)."""
    pinned = {"intent": "info_request"}

    def _mock_intent_route(state):
        return {
            "primary_intent": pinned["intent"], "secondary_intent": None,
            "intent_confidence": 0.9, "emotional_intensity": state.get("emotional_intensity", 5),
            "engagement": state.get("engagement", 7), "path": state["path"] + ["intent_route"],
        }

    calls: list = []

    def _capturing_llm(text: str):
        mock = MagicMock()
        mock.model_name = "mock-model"
        mock.openai_api_base = ""
        mock.bind_tools = MagicMock(return_value=mock)

        async def _ainvoke(*args, **kwargs):
            calls.append(args[0] if args else kwargs.get("input"))
            msg = MagicMock()
            msg.content = text
            msg.tool_calls = []
            return msg

        mock.ainvoke = AsyncMock(side_effect=_ainvoke)
        return mock

    stub_llm = _capturing_llm(_FREEFLOW_STUB)

    async def _drive():
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch("sage_poc.graph.intent_route_node", side_effect=_mock_intent_route))
            stack.enter_context(patch("sage_poc.nodes.freeflow_respond.get_responder", return_value=stub_llm))
            stack.enter_context(patch("sage_poc.nodes.freeflow_respond.get_fallback_responder", return_value=stub_llm))
            fake_repo = MagicMock()
            fake_repo.retrieve = AsyncMock(
                return_value=_fake_knowledge_result({"passages": ["cbt-001-en", "1f-b1"], "abstain": False})
            )
            stack.enter_context(
                patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=fake_repo)
            )
            stack.enter_context(patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=object()))
            with patch.object(config, "PSYCHOED_PATHWAYS_ENABLED", True), \
                 patch.object(config, "PSYCHOED_CATEGORIES", frozenset({"1f"})):
                graph = build_graph()
                t1 = await graph.ainvoke(make_e2e_state("do I have GAD"))
                t2 = await graph.ainvoke(_carry(t1, "yes"))
        return t1, t2

    t1, t2 = asyncio.run(_drive())

    assert t1["psychoed_matched_row_id"] == "1f-t3"  # sanity: stage-1 trigger genuinely hit
    assert not t2.get("psychoed_serve"), "no serve must fire on the consented-yes turn (F10-004's finding)"
    assert t2["knowledge_passages"] == [
        {"text": "fixture passage cbt-001-en", "source_id": "cbt-001-en", "citation": "fixture",
         "relevance_score": 0.9, "source_url": "", "title": "", "video_url": ""}
    ], "L4 quarantine must strip the rank-2 psychoed passage; the rank-1 non-psychoed passage survives"

    assert calls, "freeflow LLM must have been invoked for the consented-yes turn"
    user_prompt = next(m["content"] for m in calls[-1] if m["role"] == "user")
    from sage_poc.psychoed import store as psy_store  # noqa: PLC0415
    block_content = psy_store.get_block("1f-b1")["content"]
    assert block_content not in user_prompt, (
        "VERIFIED, not assumed: the quarantined block's content is absent from what the model "
        "actually saw, not merely absent from the (stub-fixed) final response"
    )


# ---------------------------------------------------------------------------
# F1 naturalistic no-trigger-phrase-reuse: standing fixture-independence guard (Task 3
# fix round 1, reviewer-required). f1_naturalistic.jsonl (blind-authored) and
# data/psychoed/trigger_tables/en/*.json are BOTH committed, so the isolation property
# the controller verified once by hand at authoring time -- the naturalistic set never
# reuses a real trigger phrase -- is mechanically checkable forever. This converts that
# one-time attestation into CI, same pattern as test_f1_wiring_matches_generator's
# table-sync check and test_intent_sweep_matches_intent_route_vocabulary's vocabulary-
# sync check: a future corpus edit (or trigger-table edit) that reintroduces overlap
# fails the build instead of silently rotting the provenance claim.
#
# This covers ONLY utterance-vs-trigger-tables (both sides committed, both sides live in
# this repo). It does NOT re-check the sealed brief against the trigger tables -- the
# brief is workspace scratch (.superpowers/sdd/.../f1-clinical-intent-brief.md), not part
# of the corpus, so that half of the seal remains a recorded one-time verification (see
# the README's provenance section for what was found there and why it's sanctioned).
#
# Two properties, both checked on NORMALIZED text (lowercased, punctuation stripped,
# whitespace collapsed, word-boundary-safe substring test):
#   1. no naturalistic utterance is an EXACT match of any multi-word (>=2 token) trigger
#      phrase;
#   2. no naturalistic utterance EMBEDS, as a contiguous substring, the FULL text of any
#      3+-token trigger phrase. This is deliberately NOT a sliding-3-gram scan over
#      arbitrary word co-occurrence -- generic connective fragments ("why do i", "i want
#      to") are expected to recur across any naturalistic corpus discussing the same
#      topics and are not reuse (see the README provenance section for the mechanical
#      check that established this, done at authoring time). This test checks whether a
#      REAL trigger phrase, whole, turns up inside a longer utterance.
# ---------------------------------------------------------------------------

# Unicode apostrophe/quote variants mapped to the straight ASCII apostrophe BEFORE the
# alnum-strip below (Task 3 fix round 2, reviewer-required): without this, a curly
# apostrophe ("can’t") is stripped to a space by the regex ([^a-z0-9\s'] does not
# include U+2019), silently splitting "can't" into "can t" -- so a trigger phrase reused
# verbatim except for straight-vs-curly quoting would sail past both the exact-match and
# embedded-substring checks below. 31/133 committed trigger phrases contain an
# apostrophe, so this is a live hole, not a theoretical one. NFKC first so composed/
# decomposed variants of the same character collapse before the literal quote-map runs.
_QUOTE_VARIANTS = str.maketrans({
    "‘": "'",  # LEFT SINGLE QUOTATION MARK
    "’": "'",  # RIGHT SINGLE QUOTATION MARK (the common "smart apostrophe")
    "‛": "'",  # SINGLE HIGH-REVERSED-9 QUOTATION MARK
    "ʼ": "'",  # MODIFIER LETTER APOSTROPHE
    "ʻ": "'",  # MODIFIER LETTER TURNED COMMA
    "´": "'",  # ACUTE ACCENT (used as apostrophe substitute in some inputs)
    "`": "'",  # GRAVE ACCENT (ditto)
})


def _normalize_phrase(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).translate(_QUOTE_VARIANTS)
    return " ".join(re.sub(r"[^a-z0-9\s']", " ", s.lower()).split())


def _find_trigger_reuse(
    utterance: str, trigger_phrases: list[tuple[str, str]]
) -> list[tuple[str, str, str]]:
    """[(kind, row_id, phrase), ...] hits for ONE utterance against a list of
    (row_id, phrase) trigger pairs -- "exact" or "embedded" per the module docstring
    above. Factored out so the corpus-wide standing test and its own regression cases
    below exercise IDENTICAL matching logic (no drift between what's asserted on the
    real corpus and what's proven in the regression tests)."""
    utt_norm = _normalize_phrase(utterance)
    hits: list[tuple[str, str, str]] = []
    for row_id, phrase in trigger_phrases:
        phrase_norm = _normalize_phrase(phrase)
        tokens = phrase_norm.split()
        if len(tokens) < 2:
            continue  # single-word trigger phrases aren't meaningfully "reusable"
        if utt_norm == phrase_norm:
            hits.append(("exact", row_id, phrase))
        elif len(tokens) >= 3 and f" {phrase_norm} " in f" {utt_norm} ":
            hits.append(("embedded", row_id, phrase))
    return hits


def test_f1_naturalistic_no_trigger_phrase_reuse():
    from tests.fixtures.psychoed.regen_wiring import generate_rows  # noqa: PLC0415

    naturalistic_rows = [r for r in load_family("F1") if r.get("baseline_only")]
    assert naturalistic_rows, (
        "no baseline_only F1 rows found -- f1_naturalistic.jsonl missing or its marker "
        "was removed; this guard has nothing to check"
    )
    # Fresh from the tables (same generator f1_wiring.jsonl's own sync test re-runs), so
    # this guard tracks trigger-table edits too, not just a stale snapshot.
    trigger_phrases = [
        (row["expect"]["audit"]["psychoed_matched_row_id"], row["turns"][0]["utterance"])
        for row in generate_rows()
    ]

    violations = [
        (row["fixture_id"], kind, row_id, phrase)
        for row in naturalistic_rows
        for kind, row_id, phrase in _find_trigger_reuse(row["turns"][0]["utterance"], trigger_phrases)
    ]

    assert not violations, (
        "f1_naturalistic.jsonl reuses trigger-table phrase(s) -- fixture-independence "
        f"violated (fixture_id, kind, trigger row_id, phrase): {violations}"
    )


# --- Regression cases (Task 3 fix round 2): a re-reviewer demonstrated that the ORIGINAL
# _normalize_phrase only preserved the straight ASCII apostrophe (regex [^a-z0-9\s'] does
# not include U+2019), so a curly/smart apostrophe -- the default on iOS/macOS/Word/
# Docs, and common in LLM output -- silently split contractions and let a verbatim-except-
# for-quote-style trigger phrase sail past both checks above. 31/133 committed trigger
# phrases contain an apostrophe, so this was a live hole, not a theoretical one. These
# cases pin the fix and prove it doesn't make the guard over-eager on clean phrasing.

def test_normalize_phrase_collapses_unicode_apostrophe_variants():
    straight = "why can't I just snap out of it"
    curly = "why can’t I just snap out of it"  # the re-reviewer's exact demonstration
    assert straight != curly, "sanity: these must be different raw strings to be a real test"
    assert _normalize_phrase(straight) == _normalize_phrase(curly) == (
        "why can't i just snap out of it"
    )


def test_f1_naturalistic_no_trigger_phrase_reuse_catches_curly_apostrophe_variant():
    """Regression for the re-reviewer's exact demonstration pair: 3c-t3's trigger phrase
    embedded in a longer utterance was already caught with a straight apostrophe before
    this fix; the identical utterance spelled with a curly apostrophe was MISSED. Both
    must be caught now, with the same violation shape."""
    trigger_phrases = [("3c-t3", "Why can't I just snap out of it?")]
    straight_utt = "yeah so why can't I just snap out of it, like actually"
    curly_utt = "yeah so why can’t I just snap out of it, like actually"

    for utt in (straight_utt, curly_utt):
        hits = _find_trigger_reuse(utt, trigger_phrases)
        assert hits == [("embedded", "3c-t3", "Why can't I just snap out of it?")], (
            f"expected embedded-reuse hit for {utt!r}, got {hits!r}"
        )


def test_f1_naturalistic_no_trigger_phrase_reuse_clean_utterance_stays_clean():
    """Companion sanity check: a real, independently-phrased F1N utterance (no
    apostrophe at all) must NOT trip the guard against an apostrophe-bearing trigger
    phrase -- the fix must not make the check over-eager."""
    trigger_phrases = [("3c-t3", "Why can't I just snap out of it?")]
    clean_utt = "why does my heart race and my hands shake when nothing bad is even happening"
    assert _find_trigger_reuse(clean_utt, trigger_phrases) == []


# ---------------------------------------------------------------------------
# F1 wiring: table-sync check (Task 2). f1_wiring.jsonl is GENERATED from
# data/psychoed/trigger_tables/en/*.json by tests/fixtures/psychoed/regen_wiring.py; this
# test re-generates from the tables on every CI run and fails if the committed file has
# drifted, so a trigger-table edit without a regeneration (or a hand-edit of the
# committed JSONL) fails CI instead of silently rotting.
# ---------------------------------------------------------------------------

def test_f1_wiring_matches_generator():
    from tests.fixtures.psychoed.regen_wiring import generate_rows, OUTPUT_PATH

    fresh_rows = generate_rows()
    committed_rows = [
        json.loads(line)
        for line in OUTPUT_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert committed_rows == fresh_rows, (
        "tests/fixtures/psychoed/f1_wiring.jsonl has drifted from "
        "data/psychoed/trigger_tables/en/*.json -- regenerate via "
        "`uv run python -m tests.fixtures.psychoed.regen_wiring` and commit the result."
    )


def test_intent_sweep_matches_intent_route_vocabulary():
    """Sync check (plan amendment 09d8ff59): INTENT_SWEEP = intent_route's ACTUAL label
    vocabulary + the fall-through sentinel. intent_route.py has no importable label
    constant -- the vocabulary lives in the INTENT_SYSTEM prompt's "primary_intent: one
    of ..." line -- so this parses that line (same pattern as a table-sync check). If the
    classifier's vocabulary changes, this fails CI instead of the sweep silently
    narrowing the gate."""
    intent_route_src = (
        pathlib.Path(__file__).parents[1] / "src" / "sage_poc" / "nodes" / "intent_route.py"
    )
    label_lines = [
        line for line in intent_route_src.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("- primary_intent: one of")
    ]
    assert len(label_lines) == 1, (
        f"expected exactly one 'primary_intent: one of' vocabulary line in "
        f"{intent_route_src}, found {len(label_lines)} -- re-derive INTENT_ROUTE_VOCABULARY"
    )
    source_vocabulary = tuple(re.findall(r'"([a-z_]+)"', label_lines[0]))
    assert source_vocabulary == INTENT_ROUTE_VOCABULARY, (
        "intent_route's label vocabulary and the driver's INTENT_ROUTE_VOCABULARY have "
        f"diverged.\n  source: {source_vocabulary}\n  driver: {INTENT_ROUTE_VOCABULARY}\n"
        "Update INTENT_ROUTE_VOCABULARY (and re-derive WEAVE_EVALUATOR_LABELS from "
        "_route_after_intent's branch order) so the sweep never silently narrows."
    )
    assert INTENT_SWEEP == INTENT_ROUTE_VOCABULARY + (FALLTHROUGH_SENTINEL,)
    assert FALLTHROUGH_SENTINEL not in source_vocabulary
    assert WEAVE_EVALUATOR_LABELS == frozenset(INTENT_SWEEP) - {"crisis"}


# ---------------------------------------------------------------------------
# Schema validator self-tests (the driver validates itself)
# ---------------------------------------------------------------------------

def _seed_row(**overrides) -> dict:
    base = {
        "fixture_id": "F4-900", "family": "F4", "set": "authored", "category": "3c",
        "turns": [{"utterance": "Why do I feel numb?", "intent_sweep": False}],
        "expect": {"disposition": None, "audit": None, "state": None},
        "delta_cite": None, "repin_on": None, "lang": "en", "source": "unit test row",
    }
    return {**base, **overrides}


def test_validator_accepts_well_formed_row():
    _validate_row(_seed_row(), "unit")


def test_validator_rejects_missing_required_key():
    row = _seed_row()
    del row["expect"]
    with pytest.raises(FixtureSchemaError, match="expect"):
        _validate_row(row, "unit")


def test_validator_rejects_unknown_set():
    with pytest.raises(FixtureSchemaError, match="set"):
        _validate_row(_seed_row(set="adhoc"), "unit")


def test_validator_rejects_em_dash_in_utterance():
    row = _seed_row(turns=[{"utterance": "I feel numb — all the time", "intent_sweep": False}])
    with pytest.raises(FixtureSchemaError, match="em dash"):
        _validate_row(row, "unit")


def test_validator_rejects_f1_naturalistic_row_without_source():
    row = _seed_row(fixture_id="F1-900", family="F1", source=None)
    with pytest.raises(FixtureSchemaError, match="source"):
        _validate_row(row, "unit")


def test_validator_rejects_intent_sweep_in_non_gate_family():
    row = _seed_row(
        fixture_id="F2-900", family="F2",
        turns=[{"utterance": "hello", "intent_sweep": True}],
    )
    with pytest.raises(FixtureSchemaError, match="gate famil"):
        _validate_row(row, "unit")


def test_load_family_reads_and_validates_seed_corpus():
    """Task 1 bring-up seeds are still present and still set:"seed" -- unmoved by Task 2's F8
    extension and Task 6's F4 extension (both add new fixture_ids alongside the seed row, so
    this no longer asserts the FULL family listing, only that the original seed row survives
    unchanged)."""
    f4 = load_family("F4")
    f8 = load_family("F8")
    f4_by_id = {r["fixture_id"]: r for r in f4}
    assert "F4-001" in f4_by_id
    assert f4_by_id["F4-001"]["set"] == "seed"
    f8_by_id = {r["fixture_id"]: r for r in f8}
    assert "F8-001" in f8_by_id
    assert f8_by_id["F8-001"]["set"] == "seed"


# ---------------------------------------------------------------------------
# fixture_id uniqueness: corpus-wide standing check + both rejection paths
# ---------------------------------------------------------------------------

def _write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_corpus_fixture_ids_globally_unique():
    """Standing check on the REAL corpus: the README's 'unique across the whole corpus'
    claim, enforced. Fails if any two f*_*.jsonl rows anywhere share a fixture_id."""
    corpus = load_corpus()
    assert set(corpus) >= {"F4", "F8"}  # seed families present; more join as tasks land


def test_load_family_rejects_within_family_duplicate(tmp_path):
    _write_jsonl(tmp_path / "f4_weave.jsonl", [
        _seed_row(fixture_id="F4-DUP"),
        _seed_row(fixture_id="F4-DUP"),
    ])
    with pytest.raises(FixtureSchemaError, match=r"duplicate fixture_id.*F4-DUP"):
        load_family("F4", fixtures_dir=tmp_path)


def test_load_corpus_rejects_cross_family_duplicate(tmp_path):
    """Cross-family collision: invisible to load_family (each family alone is clean),
    caught only by load_corpus's corpus-wide check."""
    _write_jsonl(tmp_path / "f4_weave.jsonl", [_seed_row(fixture_id="SHARED-001")])
    _write_jsonl(tmp_path / "f8_regression.jsonl", [
        _seed_row(fixture_id="SHARED-001", family="F8"),
    ])
    # sanity: each family alone passes the per-family check
    assert len(load_family("F4", fixtures_dir=tmp_path)) == 1
    assert len(load_family("F8", fixtures_dir=tmp_path)) == 1
    with pytest.raises(FixtureSchemaError, match=r"corpus-wide duplicate.*SHARED-001.*F4.*F8"):
        load_corpus(fixtures_dir=tmp_path)
