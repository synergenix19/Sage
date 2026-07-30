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
"""
import asyncio
import json
import pathlib
import re
from unittest.mock import patch

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

# LOCAL COPY of scripts/bot_behaviour_audit/measure_layer1_fullgraph.py::observed
# (lines 165-181), EXTENDED with psychoed markers. Task 9 replaces this with a canonical
# import from the runner; until then this copy is the driver's disposition oracle.
# Psychoed extension placement: below crisis/medical (crisis supremacy: an escalated
# psychoed turn must report escalate_crisis, never psychoed_serve), above the skill
# markers (a serve turn may still carry a preserved active_skill_id).
def _observed(res: dict) -> str:
    gp = res.get("gate_path")
    if gp == "crisis":
        return "escalate_crisis"
    if gp == "medical":
        return "medical_referral"
    # Psychoed extension (Task 1): a resolver serve this turn -> psychoed_serve.
    if res.get("skill_match_method") == "psychoed_resolver" or res.get("psychoed_serve"):
        return "psychoed_serve"
    # HR terminal + post-crisis complete in-turn -> active_skill_id cleared; check completion markers.
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
# Driver
# ---------------------------------------------------------------------------

def _carry(prev: dict, raw_message: str, **overrides) -> dict:
    """carry_state() plus the psychoed channels it doesn't know about (_PSYCHOED_CARRY)."""
    carried = {k: prev.get(k) for k in _PSYCHOED_CARRY if k in prev}
    return carry_state(prev, raw_message, **{**carried, **overrides})


async def run_fixture(row: dict, intent_for_sweep: str | None = None) -> dict:
    """Drive one corpus row full-graph inside the established patch context.

    Returns {"result": final_state, "audit_rows": [...]} where audit_rows are built via
    audit._build_session_audit_row from every raw state captured at EITHER
    write_session_audit call site, in chronological call order.
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

    with patch("sage_poc.graph.intent_route_node", side_effect=_mock_intent_route), \
         patch("sage_poc.nodes.output_gate.write_session_audit", new=_capture_audit), \
         patch("sage_poc.graph.write_session_audit", new=_capture_audit), \
         patch("sage_poc.nodes.freeflow_respond.get_responder", return_value=stub_llm), \
         patch("sage_poc.nodes.freeflow_respond.get_fallback_responder", return_value=stub_llm):
        # build_graph() must run INSIDE the patch context: add_node("intent_route", ...)
        # captures a direct reference to sage_poc.graph.intent_route_node at call time.
        graph = build_graph()
        result: dict | None = None
        for turn in row["turns"]:
            pinned["intent"] = (
                intent_for_sweep if turn["intent_sweep"]
                else turn.get("intent") or row.get("default_intent") or DEFAULT_INTENT
            )
            state_in = (
                make_e2e_state(turn["utterance"]) if result is None
                else _carry(result, turn["utterance"])
            )
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
    """
    expect = row["expect"]
    ctx = row["fixture_id"] if intent_for_sweep is None else f"{row['fixture_id']}[{intent_for_sweep}]"
    result = out["result"]

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


def _all_params() -> list:
    params = []
    for family in _discovered_families():
        for row in load_family(family):
            swept = any(t.get("intent_sweep") for t in row["turns"])
            if family in GATE_FAMILIES and swept:
                for intent in INTENT_SWEEP:
                    params.append(
                        pytest.param(row, intent, id=f"{row['fixture_id']}-{intent}")
                    )
            else:
                params.append(pytest.param(row, None, id=row["fixture_id"]))
    return params


def _arm_psychoed(monkeypatch, row: dict) -> None:
    """SAGE_PSYCHOED_PATHWAYS=true semantics + the fixture's category, monkeypatch-only."""
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    cats = frozenset({row["category"]}) if row.get("category") else frozenset()
    monkeypatch.setattr(config, "PSYCHOED_CATEGORIES", cats)


@pytest.mark.parametrize("row,intent", _all_params())
async def test_psychoed_fixture(row, intent, monkeypatch):
    _arm_psychoed(monkeypatch, row)
    out = await run_fixture(row, intent_for_sweep=intent)
    assert_expectations(row, out, intent_for_sweep=intent)


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
    f4 = load_family("F4")
    f8 = load_family("F8")
    assert [r["fixture_id"] for r in f4] == ["F4-001"]
    assert [r["fixture_id"] for r in f8] == ["F8-001"]
    assert all(r["set"] == "seed" for r in f4 + f8)


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
