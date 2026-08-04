"""Regression tests for two Task-9 review findings (task-9-review.md, 2026-08-04) in
scripts/bot_behaviour_audit/measure_psychoed_families.py:

(a) "No-key refusal is still defeatable" -- a parent .env file (python-dotenv's default
    find_dotenv() walks up directories; sage_poc/config.py calls bare load_dotenv() at import)
    could re-inject OPENROUTER_API_KEY into os.environ after an operator explicitly unset it,
    silently defeating a refusal check placed after that import ran. Fixed by (1) requiring
    an explicit --live flag (a .env cannot forge a CLI argument) and (2) a pre-import
    os.environ snapshot taken before any sage_poc-triggering import in the runner module.
    Tests below spawn a REAL subprocess with a planted scratch .env to prove the exact
    incident mechanism is defeated -- this property cannot be verified in-process (by the
    time any pytest test function runs, sage_poc.config is already imported for the whole
    test session via conftest.py, so an in-process check would not observe a fresh process
    start).

(b) "Audit-write exposure" -- write_session_audit is imported into six distinct module
    namespaces; the runner's original patch covered only two, leaving four terminal response
    nodes (derealization/medical/high_risk/screen_response) able to POST a real session_audit
    row during a live run. Fixed by patching all six explicitly and adding a static coverage
    guard (_assert_audit_patch_coverage_complete) that fails loudly if a future node addition
    introduces an uncovered seventh site. Tests below exercise that guard directly (both the
    passing case on real source and synthetic missing/stale cases via monkeypatch).

Also (fix round 3, Task 10 live checkpoint): run_fixture_real omitted `config={'configurable':
{'thread_id': ...}}` on every graph invocation. build_local_graph() always compiles the graph
WITH a checkpointer (MemorySaver), and LangGraph raises ValueError on ANY invoke that lacks a
thread_id when a checkpointer is present -- a live run crashed on its very first invocation
(the amendment-8 smoke case, which runs before any of the 196 corpus rows), driving zero rows
and writing no output doc. Fixed by generating a thread_id per fixture row (stable across that
row's turns, unique per row) and threading it through graph_evidence.py's `invoke_turn`. Tested
below with a mocked ainvoke capturing the config -- NOT a live call.

No live LLM, no OPENROUTER_API_KEY, no network call anywhere in this file.
"""
import asyncio
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.bot_behaviour_audit import measure_psychoed_families as mpf

REPO = Path(__file__).resolve().parents[1]
_RUNNER = REPO / "scripts" / "bot_behaviour_audit" / "measure_psychoed_families.py"


# ---------------------------------------------------------------------------
# (a) Undefeatable live-mode opt-in
# ---------------------------------------------------------------------------

def _run_subprocess(tmp_path, args, env_overrides):
    """Spawn the runner as a genuinely fresh subprocess, cwd inside tmp_path (so any .env
    planted at tmp_path's parent is what python-dotenv's upward walk would discover), with
    a minimal, explicitly-controlled environment (not this pytest process's own, which may
    already carry a real key)."""
    import os
    env = {"PATH": os.environ.get("PATH", "")}
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, str(_RUNNER), *args],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=60, env=env,
    )


def test_live_mode_refuses_without_explicit_live_flag(tmp_path):
    proc = _run_subprocess(tmp_path, ["--categories", "1f", "--out", str(tmp_path / "out.md")],
                            env_overrides={})
    assert proc.returncode == 6, proc.stdout + proc.stderr
    assert "--live" in proc.stdout


def test_live_mode_defeats_the_disclosed_planted_env_incident(tmp_path):
    """Reproduces the EXACT incident: a parent .env carries a fake OPENROUTER_API_KEY, the
    operator explicitly unset the var for this process (mirrors `env -u OPENROUTER_API_KEY`),
    and --live IS passed (so the first gate does not mask the second). Before the fix, the
    runner's key check ran AFTER sage_poc.config's load_dotenv() had already re-injected the
    fake key, and proceeded. After the fix, the pre-import snapshot (taken before any
    sage_poc import) correctly reflects that the key was NOT present at process start, and
    the runner refuses -- exit 7, not a silent pass-through."""
    scratch_parent = tmp_path / "parent"
    scratch_cwd = scratch_parent / "cwd"
    scratch_cwd.mkdir(parents=True)
    (scratch_parent / ".env").write_text("OPENROUTER_API_KEY=fake-planted-key-from-scratch-env\n")

    # Sanity: prove the plant actually works via dotenv's own upward walk from this cwd,
    # independent of the runner -- if this assertion ever fails, the test's premise is
    # broken, not the fix.
    sanity = subprocess.run(
        [sys.executable, "-c",
         "import os, sys; sys.path.insert(0, %r); "
         "print('BEFORE', 'OPENROUTER_API_KEY' in os.environ); "
         "import sage_poc.config; "
         "print('AFTER', 'OPENROUTER_API_KEY' in os.environ)" % str(REPO / "src")],
        cwd=str(scratch_cwd), capture_output=True, text=True, timeout=30,
        env={"PATH": __import__("os").environ.get("PATH", "")},
    )
    assert "BEFORE False" in sanity.stdout and "AFTER True" in sanity.stdout, (
        f"planted-.env sanity check failed -- test premise broken: {sanity.stdout} {sanity.stderr}"
    )

    proc = _run_subprocess(
        scratch_cwd, ["--live", "--categories", "1f", "--out", str(tmp_path / "out.md")],
        env_overrides={},
    )
    assert proc.returncode == 7, (
        f"the disclosed incident's exact mechanism was NOT defeated -- expected exit 7 "
        f"(pre-import snapshot refusal), got {proc.returncode}: {proc.stdout} {proc.stderr}"
    )
    assert "BEFORE any sage_poc import" in proc.stdout


def test_live_mode_proceeds_past_the_gate_with_a_genuinely_pre_import_key(tmp_path):
    """Negative control: a key genuinely present at process start (not .env-forged) must NOT
    be falsely blocked by either new check -- the run should proceed to the NEXT real gate
    (SAGE_PSYCHOED_PATHWAYS off, exit 4), proving the fix doesn't over-block legitimate runs."""
    proc = _run_subprocess(
        tmp_path,
        ["--live", "--no-parity-check", "--categories", "1f", "--out", str(tmp_path / "out.md")],
        env_overrides={"OPENROUTER_API_KEY": "genuinely-set-by-operator",
                        "SAGE_PSYCHOED_PATHWAYS": "false"},
    )
    assert proc.returncode == 4, proc.stdout + proc.stderr
    assert "SAGE_PSYCHOED_PATHWAYS is not ON" in proc.stdout


# ---------------------------------------------------------------------------
# (a2) Psychoed-arming-as-declared-delta carve-out (Task 9 fix round 2, controller-observed
# deadlock at Task 10's live checkpoint -- see task-9-report.md). Attempts 2 and 3 there were
# jointly a deadlock: the inherited, generic flag-parity guard demanded SAGE_PSYCHOED_PATHWAYS/
# SAGE_PSYCHOED_CATEGORIES match prod (OFF, pre-flip), while this runner's own precondition
# demands them ON+armed -- the only built-in escape (--allow-flag-mismatch) is a GENERIC
# override that would also mask a mismatch in any of the ~17 OTHER SAGE_ vars, unacceptable for
# a record run. Fix: carve exactly these two vars out of the parity comparison and validate
# them against the run's OWN expectation instead. Tests below prove the carve-out (1) actually
# clears the exact deadlock scenario, (2) does NOT widen past the two named vars -- a mismatch
# in any other SAGE_ var still hard-refuses, (3) does not become a rubber stamp -- a locally-OFF
# pathway or a --categories/resolved-categories disagreement still refuses exactly as before.
# ---------------------------------------------------------------------------

def test_carve_out_is_exactly_two_vars_other_mismatches_still_refuse(monkeypatch):
    """Simulates the exact controller-observed deadlock: prod serves psychoed OFF/empty,
    local arms it ON with categories -- the RAW _flag_parity() verdict is MISMATCH (would
    deadlock against this runner's own PSYCHOED_PATHWAYS_ENABLED/CATEGORIES checks below),
    but the carve-out reduces it to VERIFIED once every OTHER var genuinely matches. Then
    perturbs exactly ONE other var and proves the carved verdict is MISMATCH again,
    containing ONLY that other var -- the carve-out never widens past the two named vars."""
    from scripts.bot_behaviour_audit.measure_layer1_fullgraph import _flag_parity, _config_sage_vars

    mapping = _config_sage_vars()
    serving, desired = {}, {}
    other_var = None
    for var, default in mapping.items():
        if var == "SAGE_PSYCHOED_PATHWAYS":
            serving[var] = "false"
            desired[var] = "false"
            monkeypatch.setenv(var, "true")
        elif var == "SAGE_PSYCHOED_CATEGORIES":
            serving[var] = ""
            desired[var] = ""
            monkeypatch.setenv(var, "1f,3c,4b,6d,7c,s2c")
        else:
            val = default or ""
            serving[var] = val
            desired[var] = val
            monkeypatch.setenv(var, val)
            if other_var is None:
                other_var = var

    # Attempt-3 shape: psychoed diverges, everything else matches -> carve-out must clear it.
    parity, _resolved, flag_diffs, unverified = _flag_parity(serving, desired)
    assert parity == "MISMATCH", "test premise: raw parity must show the deadlock first"
    carved_parity, filtered_diffs, _fu, carved = mpf._carve_out_declared_delta(flag_diffs, unverified)
    assert carved_parity == "VERIFIED", f"carve-out did not clear the declared delta: {filtered_diffs}"
    assert {d[0] for d in carved} == mpf._PSYCHOED_DECLARED_DELTA_VARS

    # Perturb exactly one OTHER var -- the carve-out must NOT hide it.
    monkeypatch.setenv(other_var, serving[other_var] + "XDIFFX")
    parity2, _resolved2, flag_diffs2, unverified2 = _flag_parity(serving, desired)
    carved_parity2, filtered_diffs2, _fu2, _carved2 = mpf._carve_out_declared_delta(flag_diffs2, unverified2)
    assert carved_parity2 == "MISMATCH", "a mismatch on a non-psychoed var must still refuse"
    assert [d[0] for d in filtered_diffs2] == [other_var], (
        f"carve-out leaked beyond the two named vars: {filtered_diffs2}"
    )


def test_pathway_off_locally_still_refuses_with_carve_out_in_place(tmp_path):
    """Even with the parity carve-out active, a locally-OFF pathway must still refuse -- the
    carve-out validates the two vars against THIS RUN's own declared-delta expectation
    (pathway ON, categories == --categories), never a rubber stamp that lets anything
    through. --no-parity-check isolates this from the network-touching parity fetch."""
    proc = _run_subprocess(
        tmp_path,
        ["--live", "--no-parity-check", "--categories", "1f", "--out", str(tmp_path / "out.md")],
        env_overrides={"OPENROUTER_API_KEY": "genuinely-set", "SAGE_PSYCHOED_PATHWAYS": "false"},
    )
    assert proc.returncode == 4, proc.stdout + proc.stderr
    assert "SAGE_PSYCHOED_PATHWAYS is not ON" in proc.stdout


def test_categories_disagreement_still_refuses_with_carve_out_in_place(tmp_path):
    """--categories declaring a different set than the REAL resolved SAGE_PSYCHOED_CATEGORIES
    must still refuse -- the carve-out validates the declared delta, it does not relax this
    declared-vs-resolved cross-check."""
    proc = _run_subprocess(
        tmp_path,
        ["--live", "--no-parity-check", "--categories", "1f,3c", "--out", str(tmp_path / "out.md")],
        env_overrides={"OPENROUTER_API_KEY": "genuinely-set", "SAGE_PSYCHOED_PATHWAYS": "true",
                        "SAGE_PSYCHOED_CATEGORIES": "1f"},
    )
    assert proc.returncode == 5, proc.stdout + proc.stderr
    assert "does not equal the REAL resolved" in proc.stdout


def test_declared_delta_stamp_matches_the_controller_observed_scenario():
    """The output-doc stamp text, built from the exact attempt-3 carved diffs, matches the
    ruled format ('PROD SERVES: ... THIS RUN ARMS: ... flip-tier measurement of the
    unflipped mechanism at parity on all other flags')."""
    carved = [
        ("SAGE_PSYCHOED_CATEGORIES", "1f,3c,4b,6d,7c,s2c", ""),
        ("SAGE_PSYCHOED_PATHWAYS", "true", "false"),
    ]
    stamp = mpf._psychoed_delta_stamp(carved, {}, frozenset({"1f", "3c", "4b", "6d", "7c", "s2c"}))
    assert "PROD SERVES: psychoed OFF" in stamp
    assert "THIS RUN ARMS: 1f,3c,4b,6d,7c,s2c" in stamp
    assert "unflipped mechanism" in stamp.lower()
    assert "at parity on all other flags" in stamp.lower()


# ---------------------------------------------------------------------------
# (b) Six-site audit-capture coverage guard
# ---------------------------------------------------------------------------

def test_discovered_write_session_audit_importers_equals_patch_targets():
    """The real source tree, scanned right now: exactly the six sites this module patches,
    no more, no fewer."""
    discovered = mpf._discover_write_session_audit_importers()
    assert discovered == frozenset(mpf._AUDIT_PATCH_TARGETS)
    assert len(discovered) == 6, sorted(discovered)


def test_assert_audit_patch_coverage_complete_passes_on_real_source():
    mpf._assert_audit_patch_coverage_complete()  # must not raise


def test_all_audit_patch_targets_actually_patchable():
    """Every dotted name in _AUDIT_PATCH_TARGETS must resolve -- a typo'd module path would
    silently patch nothing (unittest.mock.patch raises AttributeError on a bad target, but
    only when actually applied; this proves it up front)."""
    async def _dummy(state):
        return None

    for target in mpf._AUDIT_PATCH_TARGETS:
        with patch(target, new=_dummy):
            pass  # no exception == the target resolved


def test_coverage_guard_fails_loudly_on_a_missing_site(monkeypatch):
    """Simulates a future node addition: a seventh write_session_audit importer appears that
    _AUDIT_PATCH_TARGETS does not cover. The guard must raise, not silently pass."""
    monkeypatch.setattr(
        mpf, "_discover_write_session_audit_importers",
        lambda: frozenset(mpf._AUDIT_PATCH_TARGETS) | {"sage_poc.nodes.some_new_node.write_session_audit"},
    )
    with pytest.raises(RuntimeError, match="COVERAGE GAP"):
        mpf._assert_audit_patch_coverage_complete()


def test_coverage_guard_fails_loudly_on_a_stale_target(monkeypatch):
    """Simulates a removed/renamed node: _AUDIT_PATCH_TARGETS lists a site that no longer
    exists. The guard must raise (never silently pass a rotted list)."""
    monkeypatch.setattr(
        mpf, "_discover_write_session_audit_importers",
        lambda: frozenset(mpf._AUDIT_PATCH_TARGETS) - {"sage_poc.nodes.screen_response.write_session_audit"},
    )
    with pytest.raises(RuntimeError, match="stale"):
        mpf._assert_audit_patch_coverage_complete()


# ---------------------------------------------------------------------------
# Dead-import removal (minor review finding): _map_health_to_sage was imported but unused.
# ---------------------------------------------------------------------------

def test_map_health_to_sage_is_not_imported():
    assert not hasattr(mpf, "_map_health_to_sage"), (
        "dead import should have been removed (task-9-review.md minor finding)"
    )


# ---------------------------------------------------------------------------
# (c) thread_id on every live-invoke call (Task 9 fix round 3, controller-observed live crash)
# ---------------------------------------------------------------------------

def test_run_fixture_real_supplies_thread_id_on_every_invoke(monkeypatch):
    """The controller-observed incident, reproduced structurally: build_local_graph() always
    compiles the graph WITH a checkpointer (MemorySaver), so LangGraph requires
    config={'configurable': {'thread_id': ...}} on every ainvoke() call, or it raises
    ValueError before any node runs. An earlier version of run_fixture_real (via
    graph_evidence.invoke_turn) omitted config entirely -- a live run crashed on its very
    first invocation (the amendment-8 smoke case), driving zero fixture rows.

    Mocked ainvoke capturing the config (NOT a live call): build_local_graph is monkeypatched
    to return a fake app whose .ainvoke records every (state_in, config) pair. This exercises
    the REAL, unmocked run_fixture_real + graph_evidence.invoke_turn code paths -- only the
    graph construction itself is substituted, so this proves both (1) run_fixture_real
    generates and passes a thread_id, and (2) invoke_turn forwards it in the exact shape
    LangGraph requires."""
    import scripts.instrument.graph_evidence as ge_module

    calls = []

    class _FakeApp:
        async def ainvoke(self, state_in, config=None):
            calls.append((state_in, config))
            return {"path": [], "response": "stub"}

    monkeypatch.setattr(ge_module, "build_local_graph", lambda warm=True: _FakeApp())

    row = {"fixture_id": "THREAD-ID-REGRESSION-TEST", "turns": [
        {"utterance": "turn one", "state_overrides": {}},
        {"utterance": "turn two", "state_overrides": {}},
    ]}
    asyncio.run(mpf.run_fixture_real(row))

    assert len(calls) == 2, "both turns of the row must reach the (fake) graph invocation"
    thread_ids = set()
    for state_in, config in calls:
        assert config is not None, (
            "invoke call missing config entirely -- this is the EXACT incident "
            "(ValueError: Checkpointer requires ... thread_id)"
        )
        assert "configurable" in config, config
        assert "thread_id" in config["configurable"], config
        assert config["configurable"]["thread_id"], "thread_id must be non-empty"
        thread_ids.add(config["configurable"]["thread_id"])
    assert len(thread_ids) == 1, (
        f"thread_id must be STABLE across every turn of the SAME row (one fixture row = one "
        f"session, mirroring a real multi-turn conversation); got {thread_ids}"
    )


def test_run_fixture_real_thread_id_is_unique_per_row(monkeypatch):
    """Two different rows must get two different thread_ids -- otherwise one row's
    checkpoint state could bleed into another's (cross-row contamination)."""
    import scripts.instrument.graph_evidence as ge_module

    seen_thread_ids = []

    class _FakeApp:
        async def ainvoke(self, state_in, config=None):
            seen_thread_ids.append(config["configurable"]["thread_id"])
            return {"path": [], "response": "stub"}

    monkeypatch.setattr(ge_module, "build_local_graph", lambda warm=True: _FakeApp())

    row_a = {"fixture_id": "ROW-A", "turns": [{"utterance": "hi", "state_overrides": {}}]}
    row_b = {"fixture_id": "ROW-B", "turns": [{"utterance": "hi", "state_overrides": {}}]}
    asyncio.run(mpf.run_fixture_real(row_a))
    asyncio.run(mpf.run_fixture_real(row_b))

    assert len(seen_thread_ids) == 2
    assert seen_thread_ids[0] != seen_thread_ids[1], "rows must not share a thread_id"
