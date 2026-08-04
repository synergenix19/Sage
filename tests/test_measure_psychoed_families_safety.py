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

No live LLM, no OPENROUTER_API_KEY, no network call anywhere in this file.
"""
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
