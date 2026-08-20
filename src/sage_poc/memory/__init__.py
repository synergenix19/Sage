"""sage_poc.memory package.

Hosts get_repository(), the single accessor that consolidates the
"pool-dance" pattern repeated at several call sites: a deferred import of
`server.app` (to dodge the server <-> sage_poc.graph circular import), a
lookup of the ambient asyncpg pool on `app.state._db_pool`, and construction
of a `PostgresMemoryRepository` around it.
"""

_UNSET = object()


def get_repository(pool=_UNSET):
    """Return a PostgresMemoryRepository, or None if no pool is available.

    Two modes, selected by whether `pool` is passed at all:

    - No argument (the common case): fetches the ambient pool from
      `server.app.state._db_pool` via a deferred import (avoids the
      circular import — server imports sage_poc.graph). Returns None if
      the app/pool lookup fails or the pool is unset.
    - `pool` passed explicitly (including explicitly as None): used as-is,
      the ambient app.state pool is never consulted. This is for callers
      that already resolved their own pool upstream (e.g.
      record_observation.make_record_tool, which receives `pool` as a
      constructor argument) — an explicit None there means "no pool was
      available to the caller", and must short-circuit the same way,
      without a redundant/misleading app.state lookup.

    Never raises. Each call site keeps its own degrade-gracefully handling
    (return "", return early, try/except-and-log) around the None result --
    this helper only centralizes the lookup + construction, not the
    per-site error-handling contract.
    """
    if pool is _UNSET:
        try:
            from server import app  # noqa: PLC0415 — deferred, avoids circular import (server imports sage_poc.graph)
            pool = getattr(app.state, "_db_pool", None)
        except Exception:
            return None

    if pool is None:
        return None

    from sage_poc.memory.postgres_repository import PostgresMemoryRepository  # noqa: PLC0415
    return PostgresMemoryRepository(pool)
