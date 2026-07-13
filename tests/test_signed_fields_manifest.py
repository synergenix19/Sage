"""Signed-clinical-fields manifest gate (scripts/check_signed_fields.py).

This is the forcing function born from the 2026-07-10 trim-shipped-unconfirmed miss: a clinician-
signed field (skill semantic_description, served referral copy, crisis helpline) cannot change and
merge without the manifest being updated with a new hash + sign-off reference in the same PR. When a
signed field changes, THIS TEST goes red until the manifest is reconciled or the change reverted.
"""
import importlib.util
import pathlib

_SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "check_signed_fields.py"
_spec = importlib.util.spec_from_file_location("check_signed_fields", _SCRIPT)
csf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(csf)


def test_all_signed_fields_match_their_signed_hashes():
    # rc 0 means every signed field's current value still matches the hash it was signed at.
    # If this fails, a signed clinical field changed — reconcile signed_clinical_fields.json
    # (new hash + sign-off) in this PR, or revert the field change.
    assert csf.verify() == 0


def test_forcing_function_catches_a_drifted_field(monkeypatch):
    # prove the mechanism: a field whose current value no longer matches its pinned hash FAILS.
    real = csf._load_manifest()[0]
    drifted = {**real, "sha256": "0" * 64}  # deliberately wrong hash
    monkeypatch.setattr(csf, "_load_manifest", lambda: [drifted])
    assert csf.verify() == 1, "a drifted signed field must fail the check"


def test_missing_field_selector_fails_not_silently_passes():
    bad = {"id": "x", "selector": "json:does/not/exist.json:field", "sha256": "0" * 64}
    import unittest.mock as m
    with m.patch.object(csf, "_load_manifest", lambda: [bad]):
        assert csf.verify() == 1, "an unextractable field must fail, never silently pass"
