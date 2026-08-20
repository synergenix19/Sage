"""Unit tests for sage_poc.memory.get_repository() (P2 Task 7e).

get_repository() consolidates the pool-dance pattern (deferred `from server
import app` + app.state._db_pool lookup + PostgresMemoryRepository(pool)
construction) that used to be copy-pasted at four call sites. These tests
pin its two contracts:

  1. It never raises -- it returns None when no pool is available, in both
     the "fetch from app.state" and "explicit pool override" shapes.
  2. It returns a PostgresMemoryRepository wrapping the correct pool when
     one is available, again in both shapes.

Because `from server import app` is a deferred import (inside the function
body, to dodge the server <-> sage_poc.graph circular import), we patch it
via sys.modules injection -- the same strategy already used by
tests/test_output_gate_session_summary.py for the sites this helper
replaces.
"""
import sys
from unittest.mock import MagicMock, patch

from sage_poc.memory import get_repository
from sage_poc.memory.postgres_repository import PostgresMemoryRepository


def _patched_server(mock_app):
    fake_server_module = MagicMock()
    fake_server_module.app = mock_app
    return patch.dict(sys.modules, {"server": fake_server_module})


def test_no_arg_returns_none_when_app_state_pool_is_none():
    """get_repository() with no argument, app.state._db_pool is None -> None."""
    mock_app = MagicMock()
    mock_app.state._db_pool = None

    with _patched_server(mock_app):
        assert get_repository() is None


def test_no_arg_returns_none_when_app_state_has_no_pool_attr():
    """get_repository() with no argument, app.state lacks _db_pool entirely -> None.

    Mirrors the getattr(app.state, "_db_pool", None) pattern used at the
    output_gate.py call sites (as opposed to freeflow_respond.py's bare
    attribute access, which relied on the outer try/except instead).
    """
    mock_app = MagicMock()
    del mock_app.state._db_pool  # MagicMock supports attribute deletion

    with _patched_server(mock_app):
        assert get_repository() is None


def test_no_arg_returns_none_when_server_import_fails():
    """get_repository() with no argument, `from server import app` raising -> None, not a raise."""
    with patch.dict(sys.modules, {"server": None}):
        assert get_repository() is None


def test_explicit_none_pool_returns_none_without_touching_app_state():
    """get_repository(pool=None) short-circuits -- never consults app.state.

    This is record_observation.py's shape: the caller already resolved its
    own pool (possibly to None) upstream, so an explicit None must not
    trigger a fallback lookup against a (possibly different, possibly
    available) ambient pool.
    """
    mock_app = MagicMock()
    mock_app.state._db_pool = MagicMock()  # would be a REAL pool if consulted

    with _patched_server(mock_app):
        assert get_repository(pool=None) is None


def test_no_arg_returns_repository_wrapping_app_state_pool():
    """get_repository() with no argument, a pool present -> repo wraps that pool."""
    mock_pool = MagicMock()
    mock_app = MagicMock()
    mock_app.state._db_pool = mock_pool

    with _patched_server(mock_app):
        repo = get_repository()

    assert isinstance(repo, PostgresMemoryRepository)
    assert repo._pool is mock_pool


def test_explicit_pool_returns_repository_wrapping_that_pool():
    """get_repository(pool=explicit) -> repo wraps the explicit pool, app.state ignored."""
    explicit_pool = MagicMock()
    ambient_pool = MagicMock()
    mock_app = MagicMock()
    mock_app.state._db_pool = ambient_pool  # must NOT be the one used

    with _patched_server(mock_app):
        repo = get_repository(pool=explicit_pool)

    assert isinstance(repo, PostgresMemoryRepository)
    assert repo._pool is explicit_pool
    assert repo._pool is not ambient_pool
