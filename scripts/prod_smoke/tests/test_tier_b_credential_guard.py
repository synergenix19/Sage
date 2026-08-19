"""Tier B storage-state credential guard — no network.

The Playwright storage-state file is CREDENTIAL-CLASS (a signed-in staff session:
cookies + localStorage). It must live OUTSIDE version control with deploy-secrets
handling (docs/runbooks/tier-b-storage-state.md). This guard is a MUST-PASS refusal
check in the smoke suite: if any storage-state file is committed/tracked in git —
the *storage*state*.json glob, or the SAGE_SMOKE_STORAGE_STATE path when it points
inside the repo — the run FAILS. It runs BEFORE (and regardless of) Tier B auth, so
a missing storage state still gets the credential hygiene check.
"""
import sys
from pathlib import Path
import pytest

pytestmark = pytest.mark.safety_gate

_PROD_SMOKE_DIR = Path(__file__).resolve().parent.parent
if str(_PROD_SMOKE_DIR) not in sys.path:
    sys.path.insert(0, str(_PROD_SMOKE_DIR))

import tier_b_features  # noqa: E402


# ---------------------------------------------------------------------------
# Pure logic (injectable tracked-file list; no git subprocess in unit tests)
# ---------------------------------------------------------------------------

def test_clean_tree_passes():
    r = tier_b_features._credential_guard_result(
        tracked=["server.py", "scripts/prod_smoke/run.py"], env_path="", repo_root="/repo")
    assert r.status == "PASS"
    assert r.must_pass is True


def test_tracked_storage_state_glob_fails_the_run():
    r = tier_b_features._credential_guard_result(
        tracked=["scripts/prod_smoke/smoke_storage_state.json"], env_path="", repo_root="/repo")
    assert r.status == "FAIL"
    assert r.must_pass is True
    assert "smoke_storage_state.json" in r.detail


def test_glob_matches_variants_case_insensitively():
    for name in ("StorageState.json", "auth-storage-state.json", "my_storage.state.json"):
        r = tier_b_features._credential_guard_result(
            tracked=[f"e2e/{name}"], env_path="", repo_root="/repo")
        assert r.status == "FAIL", name


def test_env_path_inside_repo_and_tracked_fails():
    r = tier_b_features._credential_guard_result(
        tracked=["secrets/session.json"],
        env_path="/repo/secrets/session.json", repo_root="/repo")
    assert r.status == "FAIL"
    assert "SAGE_SMOKE_STORAGE_STATE" in r.detail


def test_env_path_outside_repo_is_fine():
    r = tier_b_features._credential_guard_result(
        tracked=["server.py"], env_path="/home/ops/.sage/session.json", repo_root="/repo")
    assert r.status == "PASS"


def test_env_path_inside_repo_but_untracked_passes_with_warning_detail():
    """Spec: the FAIL condition is committed/TRACKED. Inside-repo-but-untracked is not a
    failure, but the detail must warn (one `git add -A` away from a leak)."""
    r = tier_b_features._credential_guard_result(
        tracked=["server.py"], env_path="/repo/tmp/session.json", repo_root="/repo")
    assert r.status == "PASS"
    assert "inside the repo" in r.detail


# ---------------------------------------------------------------------------
# Wiring: the guard is part of Tier B, first, must-pass, and runs without auth
# ---------------------------------------------------------------------------

def test_run_all_emits_the_guard_first_and_must_pass(monkeypatch):
    monkeypatch.delenv("SAGE_SMOKE_STORAGE_STATE", raising=False)
    results = tier_b_features.run_all("http://unused")
    assert results, "tier B returned nothing"
    guard = results[0]
    assert guard.name == "storage_state_not_in_vcs"
    assert guard.must_pass is True
    # and the auth-skip result still follows (report-only), unchanged behavior
    assert any(r.name == "tier_b_auth" for r in results[1:])


def test_repo_is_currently_clean():
    """The real check against THIS repo's git index: no storage-state artifact is tracked."""
    r = tier_b_features._credential_guard()
    assert r.status == "PASS", r.detail
