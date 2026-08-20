"""Corpus sync must never leave an article absent (2026-08-19 incident, cure).

The incident: apply_sync deleted an article's rows, committed, then re-ingested on a
SEPARATE pooled connection. Pool exhaustion between the two left anxiety-001-ar absent
and wellbeing-001-ar truncated to 1 of 4 chunks in production, silently.

The cure is an inversion — upsert, then delete only the surplus — whose safety property
is asserted here directly: **a failure at any point leaves a SUPERSET of the correct rows
(stale-but-complete), never a subset.** Absence is eliminated; the residual failure mode
is staleness, which the next sync repairs and the integrity check can see.

These drive the real apply_sync against an in-memory fake that models the parts that
mattered in the incident: per-connection failure, and a bounded pool.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.safety_gate

from sage_poc.knowledge.ingestion import chunk_ids


def _art(aid: str, lang: str = "en", body: str | None = None, crisis: bool = False) -> dict:
    return {
        "article_id": aid, "language": lang, "title": "T",
        "source_url": "https://x", "citation": "C",
        "content": body if body is not None else "Para one. " * 40,
        "is_crisis_content": crisis,
    }


class _FakeDB:
    """The rows table, shared by every connection — like the real database."""

    def __init__(self):
        self.rows: dict[str, str] = {}          # article_id -> chunk text
        self.upserts = 0
        self.deletes = 0


class _FakeConn:
    def __init__(self, db: _FakeDB, fail_on_upsert_after: int | None = None):
        self.db, self._fail_after = db, fail_on_upsert_after

    async def fetchval(self, sql, *a):
        return True if "advisory_lock" in sql else None

    async def fetch(self, sql, *a):
        if "pg_indexes" in sql:
            return []
        return [{"article_id": k, "citation_metadata": None} for k in sorted(self.db.rows)]

    async def execute(self, sql, *a):
        s = " ".join(sql.split())
        if s.startswith("INSERT INTO public.knowledge_articles"):
            if self._fail_after is not None and self.db.upserts >= self._fail_after:
                raise ConnectionError("EMAXCONNSESSION: max clients reached in session mode")
            self.db.rows[a[0]] = a[2]
            self.db.upserts += 1
            return "INSERT 0 1"
        if s.startswith("DELETE FROM public.knowledge_articles"):
            prefix, keep = a[0], (a[1] if len(a) > 1 else None)
            victims = [k for k in self.db.rows
                       if (k == prefix or k.startswith(prefix + "-"))
                       and (keep is None or k not in keep)]
            for v in victims:
                del self.db.rows[v]
            self.db.deletes += len(victims)
            return f"DELETE {len(victims)}"
        return "OK"


class _FakePool:
    """Bounded pool. max_size=1 with the caller holding the only connection is the
    EMAXCONNSESSION shape: a second acquire cannot succeed."""

    def __init__(self, db: _FakeDB, max_size: int = 10, fail_on_upsert_after=None):
        self.db, self.max_size = db, max_size
        self._fail_after = fail_on_upsert_after
        self.in_use = 0
        self.peak = 0

    def acquire(self):
        pool = self

        class _Ctx:
            async def __aenter__(self):
                if pool.in_use >= pool.max_size:
                    raise ConnectionError(
                        "EMAXCONNSESSION: max clients reached in session mode "
                        f"- limited to pool_size: {pool.max_size}")
                pool.in_use += 1
                pool.peak = max(pool.peak, pool.in_use)
                return _FakeConn(pool.db, pool._fail_after)

            async def __aexit__(self, *_a):
                pool.in_use -= 1
                return False

        return _Ctx()


@pytest.fixture(autouse=True)
def _no_embeddings(monkeypatch):
    monkeypatch.setattr("sage_poc.memory.embedding.get_embedding",
                        lambda text: [0.0] * 1024)


async def _sync(pool, articles, tmp_path, monkeypatch, prune=False):
    import json as _json
    from sage_poc.knowledge import sync as sync_mod
    for a in articles:
        (tmp_path / f"{a['article_id']}-{a['language']}.json").write_text(_json.dumps(a))
    monkeypatch.setattr(sync_mod, "verify_corpus_integrity",
                        lambda *_a, **_k: _noop_list())
    return await sync_mod.sync_corpus(str(tmp_path), pool, prune=prune)


async def _noop_list():
    return []


# --------------------------------------------------------------- id derivation is shared

def test_chunk_ids_matches_single_chunk_bare_prefix():
    ids = chunk_ids(_art("crisis-001", body="short", crisis=True))
    assert ids == ["crisis-001-en"]


def test_chunk_ids_suffixes_multi_chunk_articles():
    ids = chunk_ids(_art("cbt-001"))
    assert len(ids) > 1 and ids[0] == "cbt-001-en-000"
    assert ids == sorted(ids), "ids must be ordered so index N is chunk N"


# --------------------------------------------------------------- the safety property

@pytest.mark.asyncio
async def test_failure_mid_upsert_leaves_a_superset_never_a_subset(tmp_path, monkeypatch):
    """THE incident property: a crash during the write leaves old content fully serveable.

    Deletes run only after every upsert succeeds, so a failure in the write phase cannot
    remove anything. Premise asserted explicitly — the edit must chunk into more than one
    piece, or there is no mid-write failure point to test.
    """
    db = _FakeDB()
    old = _art("anxiety-001", "ar", body="Para. " * 200)
    assert len(chunk_ids(old)) >= 3, "fixture premise: multi-chunk article"
    for i, cid in enumerate(chunk_ids(old)):
        db.rows[cid] = f"old-{i}"
    before = dict(db.rows)

    edited = dict(old, content="Rewritten para. " * 200)
    assert len(chunk_ids(edited)) >= 2, "fixture premise: edit has a mid-write failure point"

    pool = _FakePool(db, fail_on_upsert_after=1)          # dies after the first chunk
    with pytest.raises(Exception):
        await _sync(pool, [edited], tmp_path, monkeypatch)

    assert set(before) <= set(db.rows), "rows vanished — this is the tear we removed"
    assert db.deletes == 0, "a delete ran despite the write phase failing"


@pytest.mark.asyncio
async def test_no_delete_happens_before_the_upserts(tmp_path, monkeypatch):
    """If a delete ever precedes the writes again, absence becomes reachable again."""
    db = _FakeDB()
    art = _art("cbt-001")
    for cid in chunk_ids(art):
        db.rows[cid] = "old"
    pool = _FakePool(db, fail_on_upsert_after=0)          # fail on the very first upsert
    with pytest.raises(Exception):
        await _sync(pool, [dict(art, content="New. " * 50)], tmp_path, monkeypatch)
    assert db.deletes == 0, "a delete ran before any upsert succeeded"
    assert len(db.rows) == len(chunk_ids(art))


@pytest.mark.asyncio
async def test_surplus_rows_are_removed_when_an_edit_shrinks_the_article(tmp_path, monkeypatch):
    db = _FakeDB()
    long_art = _art("sleep-001", body="Para. " * 200)
    for cid in chunk_ids(long_art):
        db.rows[cid] = "old"
    assert len(db.rows) > 2

    short = dict(long_art, content="Tiny.")
    await _sync(_FakePool(db), [short], tmp_path, monkeypatch)
    assert sorted(db.rows) == sorted(chunk_ids(short)), "surplus tail not removed"


@pytest.mark.asyncio
async def test_surplus_delete_never_touches_another_article(tmp_path, monkeypatch):
    db = _FakeDB()
    keep = _art("cbt-002")
    for cid in chunk_ids(keep):
        db.rows[cid] = "other"
    target = _art("cbt-001")
    for cid in chunk_ids(target):
        db.rows[cid] = "old"

    await _sync(_FakePool(db), [dict(target, content="Short.")], tmp_path, monkeypatch)
    for cid in chunk_ids(keep):
        assert cid in db.rows, "surplus-delete escaped its article's id space"


@pytest.mark.asyncio
async def test_surplus_delete_refuses_an_empty_keep_set():
    """An empty keep set would delete the whole article — refuse instead of wiping."""
    from sage_poc.knowledge.sync import _delete_surplus
    with pytest.raises(ValueError, match="empty keep set"):
        await _delete_surplus(_FakeConn(_FakeDB()), "cbt-001-en", [])


# --------------------------------------------------------------- the incident, replayed

@pytest.mark.asyncio
async def test_constrained_pool_no_longer_reaches_the_absence_state(tmp_path, monkeypatch):
    """The 2026-08-19 shape as a regression test: the caller holds the only connection.

    Under the old code the ingest acquired a SECOND connection, hit the ceiling and died
    after the delete had committed. Reusing the held connection means the sync completes;
    the assertion that matters either way is that no row is ever absent.
    """
    db = _FakeDB()
    art = _art("anxiety-001", "ar", body="Para. " * 200)
    for cid in chunk_ids(art):
        db.rows[cid] = "old"
    before = set(db.rows)

    # An edit that does not SHRINK the article, so any row loss is a tear rather than a
    # legitimate surplus removal. (A shrink deletes old rows by design — after the writes.)
    edited = dict(art, content="Rewritten para. " * 240)
    assert set(chunk_ids(edited)) >= before, "fixture premise: edit must not shrink"

    pool = _FakePool(db, max_size=1)                      # one connection, total
    try:
        await _sync(pool, [edited], tmp_path, monkeypatch)
    except Exception:
        pass                                              # loud failure is acceptable
    assert before <= set(db.rows), "absence reachable under a constrained pool"


@pytest.mark.asyncio
async def test_sync_uses_one_connection_per_article_not_two(tmp_path, monkeypatch):
    """Peak concurrent connections is the EMAXCONNSESSION hypothesis, measured."""
    db = _FakeDB()
    pool = _FakePool(db, max_size=10)
    await _sync(pool, [_art("cbt-001"), _art("sleep-001")], tmp_path, monkeypatch)
    assert pool.peak == 1, f"sync held {pool.peak} concurrent connections, expected 1"
