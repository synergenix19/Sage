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
