"""Schema-conformance guard for identity_substitution_audit (PDPL Art. 6 backing store).

The table existed in NO migration from writer inception (2026-05-27, ade88cb) until
migration 012 — a silent audit loss. This test is the "write succeeds against the
real schema" guard without a live DB: it parses migration 012's CREATE TABLE column
list and asserts it is exactly the set of keys write_identity_substitution_audit puts
in its row dict (excluding id/created_at, which the writer never sets). Any future
drift between the writer and the schema — a renamed field, a dropped column, a new
row key with no matching migration — fails this test.

This is deliberately separate from tests/test_identity_gate.py, which mocks the write
and tests the substitution RULE (CUO-ID-001 firing logic). That file must not be the
only test touching this path — it never touches the actual row shape or the schema.
"""
import re
from pathlib import Path
from unittest.mock import patch

import pytest

MIGRATION_PATH = (
    Path(__file__).parent.parent / "migrations" / "012_add_identity_substitution_audit.sql"
)

# Columns the writer (audit.py) never sets — the DB assigns these.
_WRITER_EXCLUDED_COLUMNS = {"id", "created_at"}


def _migration_columns() -> set[str]:
    """Parse the CREATE TABLE column names out of migration 012."""
    sql = MIGRATION_PATH.read_text()
    match = re.search(
        r"CREATE TABLE IF NOT EXISTS identity_substitution_audit\s*\((.*?)\);",
        sql,
        re.DOTALL,
    )
    assert match, "migration 012 must contain a CREATE TABLE identity_substitution_audit block"
    body = match.group(1)

    columns = set()
    for raw_line in body.splitlines():
        line = raw_line.strip().rstrip(",")
        if not line:
            continue
        # First whitespace-delimited token on each column line is the column name.
        col_name = line.split()[0]
        columns.add(col_name)
    return columns


async def _capture_posted_row() -> dict:
    """Call write_identity_substitution_audit with a mock client and return the
    exact JSON body it POSTs — the real row dict, not a re-implementation of it."""
    import importlib
    import sage_poc.audit as audit_mod
    importlib.reload(audit_mod)

    posted = {}

    class MockResponse:
        def raise_for_status(self):
            pass

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def post(self, url, headers, json, **kwargs):
            posted.update(json)
            return MockResponse()

    with patch("httpx.AsyncClient", return_value=MockClient()):
        await audit_mod.write_identity_substitution_audit(
            session_id="sess-conformance",
            turn_number=1,
            rule_id="CUO-ID-001",
            original_response_hash="abc123def456",
            original_response_text="I am a therapist and I'm here to help.",
            substitute_with="I'm a wellness companion.",
            user_id="user-conformance",
        )
    return posted


def test_migration_012_exists():
    assert MIGRATION_PATH.exists(), (
        "migrations/012_add_identity_substitution_audit.sql must exist — "
        "identity_substitution_audit is written by audit.py but had no backing table"
    )


def test_migration_012_enables_and_forces_rls():
    sql = MIGRATION_PATH.read_text()
    assert "ALTER TABLE identity_substitution_audit ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE identity_substitution_audit FORCE ROW LEVEL SECURITY" in sql
    assert "REVOKE ALL ON identity_substitution_audit FROM anon, authenticated" in sql


@pytest.mark.asyncio
async def test_writer_row_keys_match_migration_columns(monkeypatch):
    """The set of keys write_identity_substitution_audit POSTs must equal the set
    of migration-012 columns, minus id/created_at (DB-assigned, writer never sets)."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")

    posted_row = await _capture_posted_row()
    writer_keys = set(posted_row.keys())

    migration_columns = _migration_columns() - _WRITER_EXCLUDED_COLUMNS

    missing_in_migration = writer_keys - migration_columns
    missing_in_writer = migration_columns - writer_keys

    assert not missing_in_migration, (
        f"writer sets columns with no matching migration column: {missing_in_migration}"
    )
    assert not missing_in_writer, (
        f"migration declares columns the writer never sets: {missing_in_writer}"
    )
