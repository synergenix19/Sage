"""Readiness must not report healthy without a database (2026-08-19).

The shape being prevented, observed on staging 2026-07-30: POST /chat answering 200 OK,
every session_audit write failing, graph.checkpointer None, and /health/ready green
throughout — for three weeks. Serving clinical turns with no audit trail is not a state
this service should accept traffic in.

These assert on BEHAVIOUR (status codes, probe outcomes, cache effects), never on log
strings or detail wording.
"""
from __future__ import annotations

import asyncio

import pytest

pytestmark = pytest.mark.safety_gate

import server


class _FakeConn:
    def __init__(self, exc=None, delay=0.0, column_exists=True):
        self._exc, self._delay, self._column_exists = exc, delay, column_exists

    async def fetchval(self, query="", *_a, **_k):
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._exc:
            raise self._exc
        # _db_probe's "SELECT 1" and _opener_rewrite_column_probe's information_schema query
        # both run through this same fake connection; distinguish by query text so a single
        # _FakeConn can drive both probes independently in one health_ready() call.
        if "information_schema" in str(query):
            return self._column_exists
        return 1


class _FakeAcquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *_a):
        return False


class _FakePool:
    """asyncpg-shaped pool. delay simulates a hung/saturated pool."""

    def __init__(self, exc=None, delay=0.0, column_exists=True):
        self._conn = _FakeConn(exc, delay, column_exists)
        self.acquires = 0

    def acquire(self):
        self.acquires += 1
        return _FakeAcquire(self._conn)


class _FakeGraph:
    def __init__(self, checkpointer):
        self.checkpointer = checkpointer


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    """Every test starts warm, with a clean probe cache."""
    monkeypatch.setattr(server, "_bge_ready", True)
    monkeypatch.setattr(server, "_db_probe_cache", None)
    monkeypatch.setattr(server, "_opener_rewrite_column_cache", None)
    yield
    monkeypatch.setattr(server, "_db_probe_cache", None)
    monkeypatch.setattr(server, "_opener_rewrite_column_cache", None)


def _set_state(monkeypatch, pool, checkpointer="present"):
    monkeypatch.setattr(server.app.state, "_db_pool", pool, raising=False)
    monkeypatch.setattr(server.app.state, "_graph", _FakeGraph(checkpointer), raising=False)


# --------------------------------------------------------------------------- healthy

@pytest.mark.asyncio
async def test_ready_returns_200_when_database_reachable(monkeypatch):
    _set_state(monkeypatch, _FakePool())
    out = await server.health_ready()
    assert out["status"] == "ready"


@pytest.mark.asyncio
async def test_probe_reports_ok_on_a_live_pool(monkeypatch):
    _set_state(monkeypatch, _FakePool())
    ok, _ = await server._db_probe()
    assert ok is True


# --------------------------------------------------------------------------- db down

@pytest.mark.asyncio
async def test_ready_returns_503_when_pool_is_absent(monkeypatch):
    """The startup-failure shape: db connect failed, so _db_pool is None."""
    _set_state(monkeypatch, None)
    with pytest.raises(server.HTTPException) as exc:
        await server.health_ready()
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_ready_returns_503_when_query_raises(monkeypatch):
    _set_state(monkeypatch, _FakePool(exc=OSError("Name or service not known")))
    with pytest.raises(server.HTTPException) as exc:
        await server.health_ready()
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_probe_failure_does_not_propagate_the_exception(monkeypatch):
    """A probe reports, it does not explode — otherwise health returns 500 and the
    operator learns nothing about which condition failed."""
    _set_state(monkeypatch, _FakePool(exc=RuntimeError("boom")))
    ok, detail = await server._db_probe()
    assert ok is False and detail


# --------------------------------------------------------------------------- pool hung

@pytest.mark.asyncio
async def test_hung_pool_times_out_rather_than_hanging_the_endpoint(monkeypatch):
    """A hung pool must not turn a database problem into an unresponsive service."""
    monkeypatch.setattr(server, "_DB_PROBE_TIMEOUT_SECONDS", 0.05)
    _set_state(monkeypatch, _FakePool(delay=5.0))
    ok, _ = await asyncio.wait_for(server._db_probe(), timeout=2.0)
    assert ok is False


@pytest.mark.asyncio
async def test_ready_returns_503_on_a_hung_pool(monkeypatch):
    monkeypatch.setattr(server, "_DB_PROBE_TIMEOUT_SECONDS", 0.05)
    _set_state(monkeypatch, _FakePool(delay=5.0))
    with pytest.raises(server.HTTPException) as exc:
        await asyncio.wait_for(server.health_ready(), timeout=2.0)
    assert exc.value.status_code == 503


# --------------------------------------------------------------------------- checkpointer

@pytest.mark.asyncio
async def test_ready_returns_503_when_checkpointer_is_none(monkeypatch):
    """The exact staging shape: database reachable enough to answer, but the graph was
    built with checkpointer=None, so turns persist nothing."""
    _set_state(monkeypatch, _FakePool(), checkpointer=None)
    with pytest.raises(server.HTTPException) as exc:
        await server.health_ready()
    assert exc.value.status_code == 503


def test_checkpointer_present_is_false_when_graph_absent(monkeypatch):
    monkeypatch.setattr(server.app.state, "_graph", None, raising=False)
    assert server._checkpointer_present() is False


# ------------------------------------------------ opener_rewrite column (fix round 1, item 10)

@pytest.mark.asyncio
async def test_ready_returns_200_when_opener_rewrite_column_present(monkeypatch):
    _set_state(monkeypatch, _FakePool(column_exists=True))
    out = await server.health_ready()
    assert out["status"] == "ready"


@pytest.mark.asyncio
async def test_ready_returns_503_when_opener_rewrite_column_missing(monkeypatch):
    """The mechanical deploy-order gate: migration 020 not applied -> refuse traffic, exactly
    like the pre-existing DB-unreachable / checkpointer-absent cases above, not a silent
    audit-row loss discovered later at the first INSERT."""
    _set_state(monkeypatch, _FakePool(column_exists=False))
    with pytest.raises(server.HTTPException) as exc:
        await server.health_ready()
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_ready_error_names_the_missing_column_and_migration_file(monkeypatch):
    """Fail-closed wording must name the missing column and the migration file so the
    operator knows the fix in one read (owner ruling, design constraint b)."""
    _set_state(monkeypatch, _FakePool(column_exists=False))
    with pytest.raises(server.HTTPException) as exc:
        await server.health_ready()
    detail = str(exc.value.detail)
    assert "opener_rewrite" in detail
    assert "020_add_opener_rewrite_to_session_audit.sql" in detail


@pytest.mark.asyncio
async def test_opener_rewrite_column_probe_reports_true_when_present(monkeypatch):
    _set_state(monkeypatch, _FakePool(column_exists=True))
    assert await server._opener_rewrite_column_probe() is True


@pytest.mark.asyncio
async def test_opener_rewrite_column_probe_reports_false_when_absent(monkeypatch):
    _set_state(monkeypatch, _FakePool(column_exists=False))
    assert await server._opener_rewrite_column_probe() is False


@pytest.mark.asyncio
async def test_opener_rewrite_column_probe_fails_closed_when_pool_absent(monkeypatch):
    """No pool at all -> the probe must read as ABSENT, never as "unknown, assume present"."""
    _set_state(monkeypatch, None)
    assert await server._opener_rewrite_column_probe() is False


@pytest.mark.asyncio
async def test_opener_rewrite_column_probe_fails_closed_on_query_error(monkeypatch):
    _set_state(monkeypatch, _FakePool(exc=RuntimeError("boom")))
    assert await server._opener_rewrite_column_probe() is False


@pytest.mark.asyncio
async def test_opener_rewrite_column_probe_result_is_cached_within_its_ttl(monkeypatch):
    """Same anti-flap discipline as the DB reachability probe: repeated readiness hits must
    not re-query information_schema on every request."""
    pool = _FakePool(column_exists=True)
    _set_state(monkeypatch, pool)
    for _ in range(5):
        await server._opener_rewrite_column_probe()
    assert pool.acquires == 1


@pytest.mark.asyncio
async def test_opener_rewrite_column_probe_zero_behavior_change_when_present(monkeypatch):
    """Design constraint (d): the success response is byte-identical whether or not this new
    probe runs, when the column IS present -- no new field, no shape change to /health/ready's
    200 response."""
    _set_state(monkeypatch, _FakePool(column_exists=True))
    out = await server.health_ready()
    assert set(out.keys()) == {"status", "routing_mode", "reranker_head_control"}


# --------------------------------------------------------------------------- anti-flap

@pytest.mark.asyncio
async def test_probe_result_is_cached_within_its_ttl(monkeypatch):
    """Repeated readiness hits must not hammer the pool."""
    pool = _FakePool()
    _set_state(monkeypatch, pool)
    for _ in range(5):
        await server._db_probe()
    assert pool.acquires == 1


@pytest.mark.asyncio
async def test_cache_expires_so_recovery_is_observed(monkeypatch):
    """Anti-flap must not become anti-recovery: a stale failure cannot pin readiness down."""
    monkeypatch.setattr(server, "_DB_PROBE_TTL_SECONDS", 0.01)
    _set_state(monkeypatch, _FakePool(exc=OSError("down")))
    ok, _ = await server._db_probe()
    assert ok is False
    await asyncio.sleep(0.02)
    _set_state(monkeypatch, _FakePool())          # database comes back
    ok, _ = await server._db_probe()
    assert ok is True


# --------------------------------------------------------------------------- observability

def test_corpus_status_starts_not_run_not_ok():
    """'not_run' must be distinguishable from 'ran and passed' — the PR #519 gate was
    unobservable precisely because absence read as success."""
    assert server._corpus_status["state"] == "not_run"
    assert server._corpus_status["integrity"] == "unknown"
