"""Integration tests for PostgresMemoryRepository against a live Postgres instance.

These tests exercise the real SQL for the four repository methods that have no
unit-test coverage: get_persisted_clinical_flags, write_persisted_clinical_flags,
save_session_summary, and search_session_summaries.

Why integration tests here:
- search_session_summaries uses the pgvector `<=>` operator — only verifiable against
  a real Postgres instance with the pgvector extension loaded.
- save_session_summary uses DELETE + INSERT for the UNIQUE session_id constraint —
  mock tests cannot detect an accidental INSERT-only regression.
- The NOT ALL(...) filter in search_session_summaries has no Python equivalent to mock;
  a wrong cast or operator silently returns all rows.
- PDPL auditability requires confidence that persisted_clinical_flags round-trip
  faithfully through JSONB serialisation on the write path and back on the read path.

Required: DATABASE_URL in environment pointing to a Postgres instance with the full
SageAI schema (pgvector extension, public.user_therapeutic_profiles,
public.session_summaries).

Run with:
    uv run pytest tests/ -m integration -k postgres_repository_integration
"""

import os
import uuid

import pytest

asyncpg = pytest.importorskip("asyncpg", reason="asyncpg not installed")

pytestmark = pytest.mark.integration

_DATABASE_URL = os.environ.get("DATABASE_URL")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def pg_pool():
    if not _DATABASE_URL:
        pytest.skip("DATABASE_URL required for repository integration tests")
    pool = await asyncpg.create_pool(_DATABASE_URL, min_size=1, max_size=2)
    yield pool
    await pool.close()


@pytest.fixture
def repo(pg_pool):
    from sage_poc.memory.postgres_repository import PostgresMemoryRepository
    return PostgresMemoryRepository(pg_pool)


def _new_user_id() -> str:
    """UUID-backed user_id unique per test to prevent cross-test row collisions."""
    return str(uuid.uuid4())


def _unit_vector_1024() -> list[float]:
    """1024-dimensional unit vector along axis 0.

    Cosine similarity with itself = 1.0. Used as a deterministic stand-in for
    BGE-M3 embeddings so these tests run without the model loaded.
    """
    v = [0.0] * 1024
    v[0] = 1.0
    return v


def _orthogonal_vector_1024() -> list[float]:
    """Unit vector orthogonal to _unit_vector_1024 (axis 1).

    Cosine similarity with _unit_vector_1024 = 0.0. Used to confirm similarity
    ordering puts the matching summary above an unrelated one.
    """
    v = [0.0] * 1024
    v[1] = 1.0
    return v


# ---------------------------------------------------------------------------
# persisted_clinical_flags
# ---------------------------------------------------------------------------


class TestPersistedClinicalFlagsRepository:

    async def test_returns_empty_list_for_unknown_user(self, repo):
        """Non-existent user returns [] without raising."""
        result = await repo.get_persisted_clinical_flags(str(uuid.uuid4()))
        assert result == []

    async def test_write_then_read_roundtrip(self, repo):
        """Flags written are returned faithfully by get_persisted_clinical_flags.

        Validates JSONB round-trip: the json.dumps / json.loads path in
        postgres_repository must not corrupt flag names or list structure.
        """
        user_id = _new_user_id()
        flags = ["substance_use", "trauma_indicator"]
        await repo.write_persisted_clinical_flags(user_id, flags)
        try:
            result = await repo.get_persisted_clinical_flags(user_id)
            assert set(result) == set(flags), (
                "JSONB round-trip must preserve all flag names without corruption"
            )
        finally:
            async with repo._pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM public.user_therapeutic_profiles WHERE user_id = $1",
                    user_id,
                )

    async def test_second_write_upserts_not_appends(self, repo):
        """ON CONFLICT DO UPDATE replaces flags; it must not append to the prior list.

        If the upsert accidentally appended, a flag removed by clinical governance
        decision would silently persist across calls.
        """
        user_id = _new_user_id()
        await repo.write_persisted_clinical_flags(user_id, ["substance_use"])
        await repo.write_persisted_clinical_flags(user_id, ["trauma_indicator"])
        try:
            result = await repo.get_persisted_clinical_flags(user_id)
            assert result == ["trauma_indicator"], (
                "Second write must overwrite, not append — ON CONFLICT DO UPDATE semantics"
            )
            assert "substance_use" not in result
        finally:
            async with repo._pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM public.user_therapeutic_profiles WHERE user_id = $1",
                    user_id,
                )

    async def test_write_empty_list_clears_flags(self, repo):
        """Writing [] removes all persisted flags — does not leave the prior list."""
        user_id = _new_user_id()
        await repo.write_persisted_clinical_flags(user_id, ["substance_use"])
        await repo.write_persisted_clinical_flags(user_id, [])
        try:
            result = await repo.get_persisted_clinical_flags(user_id)
            assert result == [], "Writing [] must clear the stored flag list"
        finally:
            async with repo._pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM public.user_therapeutic_profiles WHERE user_id = $1",
                    user_id,
                )


# ---------------------------------------------------------------------------
# session_summaries
# ---------------------------------------------------------------------------


class TestSessionSummaryRepository:

    async def test_save_inserts_row_with_correct_fields(self, repo):
        """save_session_summary inserts a row with correct text, safety_level, and mood_score."""
        session_id = str(uuid.uuid4())
        user_id = _new_user_id()

        await repo.save_session_summary(
            session_id, user_id,
            "User discussed work stress and difficulty sleeping.",
            _unit_vector_1024(), "normal",
            skills_used=["sleep_hygiene"], mood_score=3.5,
        )
        try:
            async with repo._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """SELECT summary_text, safety_level, mood_score, skills_used
                       FROM public.session_summaries WHERE session_id = $1""",
                    session_id,
                )
            assert row is not None
            assert row["summary_text"] == "User discussed work stress and difficulty sleeping."
            assert row["safety_level"] == "normal"
            assert abs(float(row["mood_score"]) - 3.5) < 0.001
        finally:
            async with repo._pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM public.session_summaries WHERE session_id = $1",
                    session_id,
                )

    async def test_second_save_replaces_first_for_same_session(self, repo):
        """DELETE + INSERT must leave exactly one row per session_id.

        Sessions generate summaries at turns 10, 20, 30 — each successive write
        must fully replace the prior one, not accumulate duplicates.
        """
        session_id = str(uuid.uuid4())
        user_id = _new_user_id()
        embedding = _unit_vector_1024()

        await repo.save_session_summary(
            session_id, user_id, "First summary.", embedding, "normal"
        )
        await repo.save_session_summary(
            session_id, user_id, "Updated summary.", embedding, "clinical"
        )
        try:
            async with repo._pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT summary_text, safety_level FROM public.session_summaries WHERE session_id = $1",
                    session_id,
                )
            assert len(rows) == 1, (
                "DELETE+INSERT must leave exactly one row per session_id — "
                "a missing DELETE would violate the UNIQUE constraint or leave stale rows"
            )
            assert rows[0]["summary_text"] == "Updated summary."
            assert rows[0]["safety_level"] == "clinical"
        finally:
            async with repo._pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM public.session_summaries WHERE session_id = $1",
                    session_id,
                )

    async def test_search_returns_matching_summary_above_threshold(self, repo):
        """search_session_summaries returns a result with similarity > 0.99 for an identical vector.

        Verifies the `1 - (embedding <=> $2::vector)` cosine similarity expression is
        correctly formed — a typo (`+` instead of `-`, or wrong cast) would return 0.0.
        """
        session_id = str(uuid.uuid4())
        user_id = _new_user_id()
        embedding = _unit_vector_1024()

        await repo.save_session_summary(
            session_id, user_id, "User discussed anxiety and work pressure.",
            embedding, "normal",
        )
        try:
            results = await repo.search_session_summaries(
                user_id=user_id,
                query_embedding=embedding,
                top_k=3,
            )
            assert len(results) == 1
            assert results[0]["summary_text"] == "User discussed anxiety and work pressure."
            assert results[0]["similarity"] > 0.99, (
                "Identical-vector cosine similarity must be > 0.99 — "
                "a value near 0 indicates a broken `1 - (embedding <=> ...)` expression"
            )
        finally:
            async with repo._pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM public.session_summaries WHERE session_id = $1",
                    session_id,
                )

    async def test_search_excludes_crisis_summaries(self, repo):
        """NOT ALL(...) filter must exclude crisis-tagged sessions from retrieval.

        Crisis sessions must never surface into freeflow context without a safety
        re-check. A broken filter (wrong cast, missing NULL handling, wrong operator)
        would silently return crisis content.
        """
        normal_session = str(uuid.uuid4())
        crisis_session = str(uuid.uuid4())
        user_id = _new_user_id()
        embedding = _unit_vector_1024()

        await repo.save_session_summary(
            normal_session, user_id, "Normal session — user practiced breathing.",
            embedding, "normal",
        )
        await repo.save_session_summary(
            crisis_session, user_id, "Crisis session — suicidal ideation detected.",
            embedding, "crisis",
        )
        try:
            results = await repo.search_session_summaries(
                user_id=user_id,
                query_embedding=embedding,
                top_k=10,
                exclude_safety_levels=["crisis"],
            )
            returned_texts = [r["summary_text"] for r in results]
            assert "Crisis session — suicidal ideation detected." not in returned_texts, (
                "crisis-tagged sessions must be excluded by the NOT ALL(...) filter"
            )
            assert "Normal session — user practiced breathing." in returned_texts
        finally:
            async with repo._pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM public.session_summaries WHERE session_id = ANY($1::uuid[])",
                    [normal_session, crisis_session],
                )

    async def test_search_top_k_limits_results(self, repo):
        """LIMIT $4 in the SQL must be respected — top_k=2 must return at most 2 rows."""
        user_id = _new_user_id()
        session_ids = [str(uuid.uuid4()) for _ in range(4)]
        embedding = _unit_vector_1024()

        for i, sid in enumerate(session_ids):
            await repo.save_session_summary(
                sid, user_id, f"Session {i}.",
                embedding, "normal",
            )
        try:
            results = await repo.search_session_summaries(
                user_id=user_id,
                query_embedding=embedding,
                top_k=2,
            )
            assert len(results) <= 2
        finally:
            async with repo._pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM public.session_summaries WHERE session_id = ANY($1::uuid[])",
                    session_ids,
                )

    async def test_search_orders_by_similarity_descending(self, repo):
        """Results are returned most-similar first (ORDER BY embedding <=> $2::vector ASC).

        Inserts one identical-vector session and one orthogonal-vector session;
        verifies the identical-vector session ranks first.
        """
        matching_session = str(uuid.uuid4())
        unrelated_session = str(uuid.uuid4())
        user_id = _new_user_id()
        query = _unit_vector_1024()

        await repo.save_session_summary(
            matching_session, user_id, "Highly relevant session.",
            _unit_vector_1024(), "normal",
        )
        await repo.save_session_summary(
            unrelated_session, user_id, "Unrelated session.",
            _orthogonal_vector_1024(), "normal",
        )
        try:
            results = await repo.search_session_summaries(
                user_id=user_id,
                query_embedding=query,
                top_k=10,
            )
            assert len(results) == 2
            assert results[0]["summary_text"] == "Highly relevant session.", (
                "Most-similar session must rank first"
            )
        finally:
            async with repo._pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM public.session_summaries WHERE session_id = ANY($1::uuid[])",
                    [matching_session, unrelated_session],
                )
