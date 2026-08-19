"""Tests for idempotent corpus sync (auto-ingestion change detection).

Pure-logic tests only: hashing, recursive discovery, and the sync plan.
The DB-integration wrapper (sync_corpus) is exercised against a live pool,
not mocked here — these tests fix the change-detection contract.
"""
import json
import pathlib

import pytest


# ── content_hash ────────────────────────────────────────────────────────────

def test_content_hash_is_deterministic():
    from sage_poc.knowledge.sync import content_hash
    art = {
        "article_id": "cbt-001", "language": "en", "title": "What is CBT?",
        "source_url": "https://x", "citation": "Beck (1979)",
        "content": "CBT is structured.", "is_crisis_content": False,
    }
    assert content_hash(art) == content_hash(dict(art))


def test_content_hash_changes_when_content_changes():
    from sage_poc.knowledge.sync import content_hash
    base = {
        "article_id": "cbt-001", "language": "en", "title": "What is CBT?",
        "source_url": "https://x", "citation": "Beck (1979)",
        "content": "CBT is structured.", "is_crisis_content": False,
    }
    edited = dict(base, content="CBT is a structured, evidence-based therapy.")
    assert content_hash(base) != content_hash(edited)


def test_content_hash_changes_when_title_or_source_changes():
    from sage_poc.knowledge.sync import content_hash
    base = {
        "article_id": "cbt-001", "language": "en", "title": "What is CBT?",
        "source_url": "https://x", "citation": "Beck (1979)",
        "content": "CBT is structured.", "is_crisis_content": False,
    }
    assert content_hash(base) != content_hash(dict(base, title="CBT Overview"))
    assert content_hash(base) != content_hash(dict(base, source_url="https://y"))


# ── discover_corpus (recursive en/ar) ───────────────────────────────────────

def _write(tmp: pathlib.Path, rel: str, art: dict):
    p = tmp / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(art))


def _art(aid, lang, content="some clinical content here."):
    return {
        "article_id": aid, "language": lang, "title": f"{aid} title",
        "source_url": "https://x", "citation": "cite",
        "content": content, "is_crisis_content": False,
    }


def test_discover_corpus_recurses_into_language_subdirs(tmp_path):
    from sage_poc.knowledge.sync import discover_corpus
    _write(tmp_path, "en/cbt-001.json", _art("cbt-001", "en"))
    _write(tmp_path, "ar/cbt-001.json", _art("cbt-001", "ar"))
    _write(tmp_path, "en/anxiety-001.json", _art("anxiety-001", "en"))
    found = discover_corpus(tmp_path)
    ids = sorted((a["article_id"], a["language"]) for a in found)
    assert ids == [("anxiety-001", "en"), ("cbt-001", "ar"), ("cbt-001", "en")]


def test_discover_corpus_validates_schema(tmp_path):
    from sage_poc.knowledge.sync import discover_corpus
    bad = {"article_id": "x", "language": "en"}  # missing required fields
    _write(tmp_path, "en/bad.json", bad)
    with pytest.raises(ValueError):
        discover_corpus(tmp_path)


def test_discover_corpus_empty_dir_returns_empty(tmp_path):
    from sage_poc.knowledge.sync import discover_corpus
    assert discover_corpus(tmp_path) == []


# ── compute_sync_plan (the change-detection contract) ───────────────────────

def test_plan_new_articles_are_ingested():
    from sage_poc.knowledge.sync import compute_sync_plan, content_hash
    arts = [_art("cbt-001", "en"), _art("cbt-001", "ar")]
    plan = compute_sync_plan(arts, existing_hashes={}, prune=False)
    assert {(a["article_id"], a["language"]) for a in plan.to_ingest} == {
        ("cbt-001", "en"), ("cbt-001", "ar")}
    assert plan.to_skip == []
    assert plan.to_prune == []


def test_plan_unchanged_articles_are_skipped():
    from sage_poc.knowledge.sync import compute_sync_plan, content_hash
    a = _art("cbt-001", "en")
    existing = {"cbt-001-en": content_hash(a)}
    plan = compute_sync_plan([a], existing_hashes=existing, prune=False)
    assert plan.to_ingest == []
    assert plan.to_skip == ["cbt-001-en"]


def test_plan_changed_article_is_reingested():
    from sage_poc.knowledge.sync import compute_sync_plan
    a = _art("cbt-001", "en", content="OLD")
    existing = {"cbt-001-en": "stalehash"}
    plan = compute_sync_plan([a], existing_hashes=existing, prune=False)
    assert [(x["article_id"], x["language"]) for x in plan.to_ingest] == [("cbt-001", "en")]
    assert plan.to_skip == []


def test_plan_prune_removes_db_only_articles_when_enabled():
    from sage_poc.knowledge.sync import compute_sync_plan, content_hash
    a = _art("cbt-001", "en")
    existing = {"cbt-001-en": content_hash(a), "removed-001-en": "abc"}
    plan = compute_sync_plan([a], existing_hashes=existing, prune=True)
    assert plan.to_prune == ["removed-001-en"]
    assert plan.to_skip == ["cbt-001-en"]


def test_plan_prune_disabled_keeps_db_only_articles():
    from sage_poc.knowledge.sync import compute_sync_plan, content_hash
    a = _art("cbt-001", "en")
    existing = {"cbt-001-en": content_hash(a), "removed-001-en": "abc"}
    plan = compute_sync_plan([a], existing_hashes=existing, prune=False)
    assert plan.to_prune == []


# ---------------------------------------------------------------------------
# Abstain-gate fail-closed default (2026-08-19). The gate must not run open just
# because nobody set the variable.
# ---------------------------------------------------------------------------

def test_abstain_threshold_raises_when_unset_outside_test_context(monkeypatch):
    from sage_poc.config import _abstain_threshold
    monkeypatch.delenv("SAGE_COSINE_ABSTAIN_THRESHOLD", raising=False)
    monkeypatch.delenv("SAGE_ALLOW_UNSET_ABSTAIN_THRESHOLD", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setitem(__import__("sys").modules, "pytest", None)
    monkeypatch.delitem(__import__("sys").modules, "pytest")
    with pytest.raises(RuntimeError, match="SAGE_COSINE_ABSTAIN_THRESHOLD"):
        _abstain_threshold()


def test_abstain_threshold_explicit_zero_is_honoured_as_deliberate_rollback(monkeypatch):
    from sage_poc.config import _abstain_threshold
    monkeypatch.setenv("SAGE_COSINE_ABSTAIN_THRESHOLD", "0.0")
    assert _abstain_threshold() == 0.0


def test_abstain_threshold_reads_the_configured_value(monkeypatch):
    from sage_poc.config import _abstain_threshold
    monkeypatch.setenv("SAGE_COSINE_ABSTAIN_THRESHOLD", "0.58")
    assert _abstain_threshold() == 0.58


# ---------------------------------------------------------------------------
# Post-sync integrity assertion (2026-08-19). Regression cover for the tear that
# left anxiety-001-ar absent and wellbeing-001-ar truncated to 1 of 4 chunks in
# prod: the sync deletes a prefix, commits, then re-inserts on a separate pooled
# connection, so a failure in between is silent. These assert on the DETECTION
# behaviour — counts vs corpus files — not on any log string.
# ---------------------------------------------------------------------------

class _FakeConn:
    """Minimal asyncpg-shaped stub: fetch() returns the stored article_id rows."""

    def __init__(self, article_ids):
        self._rows = [{"article_id": a} for a in article_ids]

    async def fetch(self, *_args, **_kwargs):
        return self._rows


@pytest.mark.asyncio
async def test_integrity_check_passes_when_stored_matches_corpus():
    from sage_poc.knowledge.ingestion import chunk_text
    from sage_poc.knowledge.sync import verify_corpus_integrity
    art = _art("cbt-001", "en")
    n = len(chunk_text(art["content"], is_crisis_content=False))
    ids = [f"cbt-001-en-{i:03d}" for i in range(n)] if n > 1 else ["cbt-001-en"]
    assert await verify_corpus_integrity(_FakeConn(ids), [art]) == []


@pytest.mark.asyncio
async def test_integrity_check_flags_article_missing_entirely():
    from sage_poc.knowledge.sync import verify_corpus_integrity
    art = _art("anxiety-001", "ar")
    mismatches = await verify_corpus_integrity(_FakeConn([]), [art])
    assert len(mismatches) == 1
    prefix, expected, stored = mismatches[0]
    assert prefix == "anxiety-001-ar"
    assert stored == 0 and expected >= 1


@pytest.mark.asyncio
async def test_integrity_check_flags_truncated_article():
    """The wellbeing-001-ar shape: present, hash-consistent, but short of chunks.

    Content-hash readback cannot see this — the surviving rows carry a correct
    hash — which is exactly why the check counts instead.
    """
    from sage_poc.knowledge.ingestion import chunk_text
    from sage_poc.knowledge.sync import verify_corpus_integrity
    art = _art("wellbeing-001", "ar")
    art["content"] = "\n\n".join(f"Paragraph {i} with enough text to chunk." * 40 for i in range(6))
    n = len(chunk_text(art["content"], is_crisis_content=False))
    assert n > 1, "fixture must chunk into more than one piece to model a tear"
    mismatches = await verify_corpus_integrity(_FakeConn(["wellbeing-001-ar-000"]), [art])
    assert mismatches == [("wellbeing-001-ar", n, 1)]


@pytest.mark.asyncio
async def test_corpus_integrity_error_names_every_affected_article():
    from sage_poc.knowledge.sync import CorpusIntegrityError
    exc = CorpusIntegrityError([("anxiety-001-ar", 4, 0), ("wellbeing-001-ar", 4, 1)])
    assert "anxiety-001-ar" in str(exc) and "wellbeing-001-ar" in str(exc)
    assert len(exc.mismatches) == 2
