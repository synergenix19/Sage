"""P2 Task 7g fix round 1: real_model_driver's explicit configure_mode() gate.

Before P2 Task 7g, the env-mutation/validation that resolves MODE ran at IMPORT time, so
`MODE` could never be unset by the time `positive_control()` / `run_gate()` ran -- the
acceptance gate was unskippable by construction. Making `configure_mode()` an explicit,
opt-in call (instead of an import-time side effect) turned "forgot to call configure_mode()"
into a silent-fallback-to-V1 hole: `MODE is None` fell through `if MODE != "V2"` /
`if MODE == "V2" and ...` as if it meant V1, quietly skipping the positive-control check and
reporting `"mode": None`. These tests pin the restored guard: both functions must hard-fail
with SystemExit when MODE is unset, not silently behave like V1.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from sage_poc.routing_eval import real_model_driver as drv

_WORKTREE_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _reset_mode():
    """Every test starts and ends with MODE reset to None, so no test's configure_mode()
    call (or forgotten reset) leaks into another test in this module or elsewhere."""
    prior = drv.MODE
    drv.MODE = None
    yield
    drv.MODE = prior


def test_positive_control_raises_systemexit_when_mode_is_none():
    with pytest.raises(SystemExit, match="configure_mode"):
        drv.positive_control()


def test_run_gate_raises_systemexit_when_mode_is_none():
    with pytest.raises(SystemExit, match="configure_mode"):
        drv.run_gate()


def test_configure_mode_v1_sets_mode_and_returns_it(monkeypatch):
    monkeypatch.setenv("SKILL_ROUTING_V2", "0")
    monkeypatch.setenv("SKILL_RERANK_ENABLED", "0")
    result = drv.configure_mode()
    assert result == "V1"
    assert drv.MODE == "V1"


def test_configure_mode_then_positive_control_v1_returns_none(monkeypatch):
    """V1 mode: positive_control() must return None (reranker unused), not raise -- the
    guard added in this fix round only fires when MODE is unset, never for a valid V1/V2."""
    monkeypatch.setenv("SKILL_ROUTING_V2", "0")
    monkeypatch.setenv("SKILL_RERANK_ENABLED", "0")
    drv.configure_mode()
    assert drv.positive_control() is None


def test_configure_mode_mismatched_flags_raises_systemexit(monkeypatch):
    monkeypatch.setenv("SKILL_ROUTING_V2", "1")
    monkeypatch.setenv("SKILL_RERANK_ENABLED", "0")
    with pytest.raises(SystemExit, match="V1 needs BOTH flags off"):
        drv.configure_mode()
    # A failed configure_mode() call must not silently leave a stale MODE from a prior test
    # or partial mutation -- it should still read as unset (the module-level default).
    assert drv.MODE is None


def test_import_alone_does_not_configure_mode_or_raise():
    """The core P2 Task 7g proof, de-tautologized (fix round 2, item 563-a).

    A prior version of this test asserted only `drv.MODE is None` in-process. That is
    TAUTOLOGICAL: the autouse `_reset_mode` fixture above sets `drv.MODE = None` before
    EVERY test runs, so the assertion passes regardless of what import actually did --
    proven unfalsifiable by the RED-verification note below (a module that set MODE at
    import time still passes this shape of assertion once the fixture has already reset it).

    This drives a TRUE fresh import with NO fixtures involved: a subprocess, with
    PYTHONPATH pinned to THIS worktree's own src (not the shared venv's editable-installed
    checkout -- see the P2 Task 7g PR body's documented footgun), and a DELIBERATELY
    MISMATCHED flag combo in the environment (SKILL_ROUTING_V2=1, SKILL_RERANK_ENABLED=0).
    If configure_mode()'s validation ran at import time (the pre-P2-Task-7g bug, or a
    regression back to it), the subprocess would raise SystemExit before ever reaching the
    `print("OK")` line -- a non-zero exit code and missing "OK" in stdout, not just a
    `MODE is None` check a reset fixture could paper over.

    RED-verified (fix round 2): temporarily added `MODE = "V1"` as a module-level statement
    directly after `MODE: str | None = None` in real_model_driver.py (an uncommitted,
    unstaged mutation), re-ran this exact test, confirmed it failed (subprocess printed the
    assertion failure `MODE was 'V1' after import alone`), then reverted via Edit (never
    `git checkout`, no history lost) and re-ran to confirm green again.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{_WORKTREE_ROOT / 'src'}{os.pathsep}{_WORKTREE_ROOT}"
    env["SAGE_ALLOW_UNSET_ABSTAIN_THRESHOLD"] = "1"
    env["SKILL_ROUTING_V2"] = "1"
    env["SKILL_RERANK_ENABLED"] = "0"  # deliberately mismatched -- see docstring

    result = subprocess.run(
        [
            sys.executable, "-c",
            "from sage_poc.routing_eval import real_model_driver as drv\n"
            "assert drv.MODE is None, f'MODE was {drv.MODE!r} after import alone'\n"
            "print('OK')\n",
        ],
        env=env, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0 and "OK" in result.stdout, (
        f"import alone must be side-effect-free even under a mismatched flag combo -- "
        f"returncode={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
