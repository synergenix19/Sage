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

INTENT_SWEEP = ("general_chat", "info_request", "skill_request", "emotional_support")
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


def load_family(family: str) -> list[dict]:
    """Read and schema-validate every tests/fixtures/psychoed/f<N>_*.jsonl row for a family."""
    files = sorted(FIXTURES_DIR.glob(f"{family.lower()}_*.jsonl"))
    if not files:
        raise FileNotFoundError(
            f"no corpus files for family {family!r} under {FIXTURES_DIR} "
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


def assert_expectations(row: dict, out: dict) -> None:
    expect = row["expect"]
    ctx = row["fixture_id"]
    result = out["result"]

    disposition = expect.get("disposition")
    if disposition is not None:
        got = _observed(result)
        assert got == disposition, (
            f"{ctx}: disposition: expected {disposition!r}, observed {got!r} "
            f"(gate_path={result.get('gate_path')!r}, "
            f"skill_match_method={result.get('skill_match_method')!r})"
        )

    audit_expect = expect.get("audit")
    if audit_expect:
        assert out["audit_rows"], f"{ctx}: audit expectations given but no audit rows captured"
        _subset_match(audit_expect, out["audit_rows"][-1], f"{ctx} audit (last row)")

    state_expect = expect.get("state")
    if state_expect:
        _subset_match(state_expect, result, f"{ctx} state")


# ---------------------------------------------------------------------------
# Parametrization: discover families from the corpus directory
# ---------------------------------------------------------------------------

def _discovered_families() -> list[str]:
    fams = set()
    for path in FIXTURES_DIR.glob("f*_*.jsonl"):
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
    assert_expectations(row, out)


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
