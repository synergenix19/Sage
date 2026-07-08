"""Fail-closed crisis-copy boot guard tests.

assert_crisis_copy_resolves() is called from server.py lifespan startup. It loads every crisis-copy
source in RESOLVED form and raises RuntimeError if ANY unresolved '{{crisis_*}}' placeholder remains,
so the app refuses to boot rather than serve a raw placeholder in a crisis message.
"""
from pathlib import Path

import pytest

from sage_poc.crisis_copy import (
    assert_crisis_copy_resolves,
    crisis_copy_source_files,
    resolve_crisis_placeholders,
)


def test_real_crisis_sources_all_resolve_clean():
    # The shipped tree must boot: every real crisis-copy source resolves with no leftover placeholder.
    assert_crisis_copy_resolves()  # must not raise


def test_source_inventory_is_nonempty():
    # Guard against the glob silently matching nothing (which would make the guard vacuously pass).
    assert len(crisis_copy_source_files()) > 0


def test_unresolved_variable_raises_runtime_error(tmp_path: Path):
    # A clinician typo / an unknown crisis variable must fail the boot.
    bad = tmp_path / "bad_crisis.json"
    bad.write_text('{"response": "call {{crisis_numbr}} now"}', encoding="utf-8")  # typo'd variable
    with pytest.raises(RuntimeError, match="BOOT GUARD FAILED"):
        assert_crisis_copy_resolves([bad])


def test_known_variables_do_not_raise(tmp_path: Path):
    good = tmp_path / "good_crisis.json"
    good.write_text(
        '{"r": "{{crisis_label}} {{crisis_number}} ({{crisis_hours}}) or {{crisis_emergency}}"}',
        encoding="utf-8",
    )
    assert_crisis_copy_resolves([good])  # must not raise
    # and it actually resolved to real values, no marker left
    assert "{{crisis_" not in resolve_crisis_placeholders(good.read_text(encoding="utf-8"))


def test_missed_resolution_point_would_be_caught(tmp_path: Path):
    # Simulates the "missed load point" failure: a raw placeholder file reaches the guard.
    missed = tmp_path / "missed.json"
    missed.write_text('{"x": "{{crisis_number}} and {{crisis_unknown_field}}"}', encoding="utf-8")
    with pytest.raises(RuntimeError):
        assert_crisis_copy_resolves([missed])
