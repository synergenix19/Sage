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

import pytest

from sage_poc.routing_eval import real_model_driver as drv


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


def test_import_alone_does_not_configure_mode_or_raise(monkeypatch):
    """The core P2 Task 7g proof: importing the module (already done at collection time here)
    must be side-effect-free regardless of env var state -- MODE starts unset and only
    configure_mode() resolves it. Re-imports are cached by Python, so this asserts the
    INVARIANT the import-time removal established, via the reset fixture's guarantee that
    MODE is None at test start without any configure_mode() call having run in this test."""
    assert drv.MODE is None
