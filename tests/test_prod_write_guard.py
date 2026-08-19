"""The prod-write source-ref guard (2026-08-19 incident, fourth of its class).

The incident: a repair run from a checkout parked on a stale feature branch wrote
pre-refresh corpus content into prod, reverting two approved citation upgrades. These
tests assert the guard's BEHAVIOUR — refuse on divergence, pass on identity, and refuse
loudly rather than silently when it cannot compare — using real throwaway git repos, so
nothing here depends on the state of the checkout the suite happens to run in.
"""
from __future__ import annotations

import subprocess

import pytest

pytestmark = pytest.mark.safety_gate

from scripts.prod_write_guard import (
    ESCAPE_ENV,
    SourceRefMismatch,
    assert_source_ref,
    diverging_paths,
)


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=str(repo), check=True,
                   capture_output=True, text=True)


@pytest.fixture()
def repo(tmp_path):
    """A repo with a 'reviewed' ref and a feature branch that edits the guarded path."""
    r = tmp_path / "repo"
    (r / "data" / "knowledge_corpus" / "ar").mkdir(parents=True)
    _git(r.parent, "init", "-q", "repo")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    art = r / "data" / "knowledge_corpus" / "ar" / "anxiety-001.json"
    art.write_text('{"citation": "approved-2026-08"}')
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "reviewed state")
    _git(r, "branch", "reviewed")
    return r


def test_passes_when_content_matches_the_reviewed_ref(repo):
    assert_source_ref(["data/knowledge_corpus"], ref="reviewed", root=repo)


def test_refuses_when_the_checkout_carries_stale_content(repo):
    """The exact incident shape: a feature branch holding a superseded citation."""
    _git(repo, "checkout", "-qb", "feat/stale")
    (repo / "data" / "knowledge_corpus" / "ar" / "anxiety-001.json").write_text(
        '{"citation": "superseded-pre-refresh"}')
    _git(repo, "commit", "-qam", "stale citation")
    with pytest.raises(SourceRefMismatch) as exc:
        assert_source_ref(["data/knowledge_corpus"], ref="reviewed", root=repo)
    assert "anxiety-001.json" in str(exc.value)
    assert "feat/stale" in str(exc.value), "must name the checkout the operator is standing in"


def test_refuses_on_uncommitted_working_tree_edits(repo):
    """A branch name proves nothing; the guard is content-based by design."""
    (repo / "data" / "knowledge_corpus" / "ar" / "anxiety-001.json").write_text('{"citation": "hand-edited"}')
    with pytest.raises(SourceRefMismatch):
        assert_source_ref(["data/knowledge_corpus"], ref="reviewed", root=repo)


def test_ignores_divergence_outside_the_guarded_paths(repo):
    _git(repo, "checkout", "-qb", "feat/unrelated")
    (repo / "README.md").write_text("unrelated change")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "unrelated")
    assert_source_ref(["data/knowledge_corpus"], ref="reviewed", root=repo)


def test_refuses_when_the_ref_is_unknown_rather_than_passing_silently(repo):
    with pytest.raises(SourceRefMismatch, match="cannot compare"):
        diverging_paths(["data/knowledge_corpus"], ref="origin/does-not-exist", root=repo)


def test_escape_hatch_bypasses_but_is_explicit(repo, monkeypatch):
    _git(repo, "checkout", "-qb", "feat/stale")
    (repo / "data" / "knowledge_corpus" / "ar" / "anxiety-001.json").write_text('{"citation": "superseded"}')
    _git(repo, "commit", "-qam", "stale")
    monkeypatch.setenv(ESCAPE_ENV, "1")
    assert_source_ref(["data/knowledge_corpus"], ref="reviewed", root=repo)  # does not raise
