"""scripts/lib/prod_probe.py — pure-function tests only. No live HTTP/psql/railway calls.

Covers the three things the K3.1 brief calls out: session-id shape, column-list
rendering, and an argv-purity proof that the constructed psql argv carries neither the
DB credential (password) nor the raw DATABASE_URL — those live only in the env dict this
module builds, matching the "credential via PGPASSWORD/env, never argv" fix. A second
proof covers the session-id-binding fix: the SQL text psql receives never contains the
raw session_id value (it's bound via `-v` + `:'sid'`, not f-string-spliced in).
"""
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.lib import prod_probe  # noqa: E402

FAKE_DSN = "postgresql://probe_user:s3cr3t-pw@db.example.internal:5432/sage_prod?sslmode=require"
INJECTION_SID = "prodsuite-x'; DROP TABLE session_audit; --"


# ─────────────────────────────────────────────────────────────────────────────
# new_session_id() — shape
# ─────────────────────────────────────────────────────────────────────────────

def test_new_session_id_default_shape():
    sid = prod_probe.new_session_id("prodsuite-run-med-ar")
    prefix, _, suffix = sid.rpartition("-")
    assert prefix == "prodsuite-run-med-ar"
    assert len(suffix) == 8
    int(suffix, 16)  # hex


def test_new_session_id_custom_suffix_length():
    sid = prod_probe.new_session_id("sf1p0-fixture-3", n=6)
    prefix, _, suffix = sid.rpartition("-")
    assert prefix == "sf1p0-fixture-3"
    assert len(suffix) == 6
    int(suffix, 16)


def test_new_session_id_two_calls_differ():
    a = prod_probe.new_session_id("dup-tag")
    b = prod_probe.new_session_id("dup-tag")
    assert a != b


def test_new_session_id_n_zero_is_deterministic_passthrough():
    # measure_layer1_prod_http.py's scheme: run_tag + row index, no randomness.
    sid = prod_probe.new_session_id("prodconf-1755600000-42", n=0)
    assert sid == "prodconf-1755600000-42"


# ─────────────────────────────────────────────────────────────────────────────
# audit() column-list rendering
# ─────────────────────────────────────────────────────────────────────────────

def test_audit_query_renders_caller_supplied_columns_verbatim():
    cols = "COALESCE(active_skill_id,'<none>'), skill_match_method, node_path, gate_path"
    sql = prod_probe._audit_query(cols)
    assert sql.startswith(f"SELECT {cols} FROM session_audit")
    assert "ORDER BY turn_number DESC LIMIT 1" in sql


def test_audit_query_renders_concatenated_column_expression():
    # measure_layer1_prod_http.py's style: one || concatenated pseudo-column, not a list.
    cols = "COALESCE(active_skill_id,'')||'|'||COALESCE(skill_match_method,'')"
    sql = prod_probe._audit_query(cols)
    assert sql.startswith(f"SELECT {cols} FROM session_audit")


def test_audit_query_order_by_and_limit_are_configurable():
    sql = prod_probe._audit_query("x", order_by="created_at ASC", limit=3)
    assert "ORDER BY created_at ASC LIMIT 3" in sql


def test_audit_query_binds_session_id_never_interpolates_it():
    sql = prod_probe._audit_query("x")
    assert ":'sid'" in sql
    assert "session_id = :'sid'" in sql
    # no f-string splice point for a literal value at all
    assert "session_id='" not in sql


def test_audit_argv_sql_never_contains_the_raw_session_id():
    """The injection-shaped fix: whatever session_id the caller passes, it must never
    appear inside the SQL text itself — only as the `-v` variable value, which psql
    quotes safely when substituted via `:'sid'`."""
    argv = prod_probe._audit_argv(INJECTION_SID, "col_a, col_b")
    sql_token = argv[argv.index("-tAc") + 1]
    assert INJECTION_SID not in sql_token
    assert ":'sid'" in sql_token


def test_audit_argv_carries_session_id_only_via_dash_v():
    argv = prod_probe._audit_argv("prodsuite-hr1-psy-abcd1234", "x")
    assert "-v" in argv
    v_index = argv.index("-v")
    assert argv[v_index + 1] == "sid=prodsuite-hr1-psy-abcd1234"


# ─────────────────────────────────────────────────────────────────────────────
# argv-purity: psql argv carries no credential; the DSN never appears there either
# ─────────────────────────────────────────────────────────────────────────────

def test_pg_env_extracts_password_and_other_components():
    env = prod_probe._pg_env(FAKE_DSN, base_env={})
    assert env["PGPASSWORD"] == "s3cr3t-pw"
    assert env["PGUSER"] == "probe_user"
    assert env["PGHOST"] == "db.example.internal"
    assert env["PGPORT"] == "5432"
    assert env["PGDATABASE"] == "sage_prod"
    assert env["PGSSLMODE"] == "require"


def test_audit_argv_contains_no_credential_and_no_dsn():
    argv = prod_probe._audit_argv("prodsuite-run-med-ar-abcd1234", "col_a, col_b")
    for token in argv:
        assert "s3cr3t-pw" not in token
        assert "postgresql://" not in token
        assert "postgres://" not in token
        assert "DATABASE_URL" not in token
    # no positional conninfo token at all — the only DB-shaped thing here is the SQL text.
    assert argv[0] == "psql"
    assert argv[1] == "-v"


def test_audit_uses_pg_env_not_argv_for_credentials(monkeypatch):
    """Full audit() call, subprocess.run stubbed so we can inspect exactly what it
    would have been invoked with — argv and env are asserted separately."""
    captured = {}

    def fake_run(argv, capture_output, text, env):
        captured["argv"] = argv
        captured["env"] = env

        class _R:
            stdout = "ok"
        return _R()

    monkeypatch.setattr(prod_probe.subprocess, "run", fake_run)
    prod_probe.audit("prodsuite-x-abcd1234", "col_a", database_url=FAKE_DSN)

    assert captured["env"]["PGPASSWORD"] == "s3cr3t-pw"
    for token in captured["argv"]:
        assert "s3cr3t-pw" not in token
        assert FAKE_DSN not in token


# ─────────────────────────────────────────────────────────────────────────────
# resolve_creds() — pure branch (env present, no subprocess call)
# ─────────────────────────────────────────────────────────────────────────────

def test_resolve_creds_prefers_env_over_railway(monkeypatch):
    monkeypatch.setenv("SAGE_API_KEY", "env-key")
    monkeypatch.setenv("DATABASE_URL", FAKE_DSN)
    monkeypatch.setenv("SAGE_TEST_USER_IDS", "u1,u2")

    def fail_if_called(*a, **k):
        raise AssertionError("railway should not be invoked when env vars are set")

    monkeypatch.setattr(prod_probe.subprocess, "check_output", fail_if_called)

    creds = prod_probe.resolve_creds()
    assert creds.api_key == "env-key"
    assert creds.database_url == FAKE_DSN
    assert creds.test_user_ids == "u1,u2"


# ─────────────────────────────────────────────────────────────────────────────
# resolve_creds() — fail-closed: missing env, railway fallback gating, fail-fast
# ─────────────────────────────────────────────────────────────────────────────

def test_resolve_creds_no_gate_var_raises_runtime_error_without_calling_railway(monkeypatch):
    """Env vars absent, SAGE_ALLOW_RAILWAY_FALLBACK unset: this must raise RuntimeError
    and must NOT shell out to `railway variables --json` — the incident this closes is
    exactly that silent fallback pulling live prod credentials into a session transcript."""
    monkeypatch.delenv("SAGE_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SAGE_ALLOW_RAILWAY_FALLBACK", raising=False)

    def fail_if_called(*a, **k):
        raise AssertionError("railway must not be invoked when the fallback gate var is unset")

    monkeypatch.setattr(prod_probe.subprocess, "check_output", fail_if_called)

    try:
        prod_probe.resolve_creds()
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        msg = str(e)
        assert "SAGE_API_KEY" in msg
        assert "DATABASE_URL" in msg
        assert "SAGE_ALLOW_RAILWAY_FALLBACK" in msg


def test_resolve_creds_missing_var_in_railway_output_raises(monkeypatch):
    """Gate var set, env vars absent, but the railway payload lacks DATABASE_URL: must
    raise immediately naming the missing variable, never fall back to an empty string
    (matching the original scripts' dict-indexing fail-fast)."""
    monkeypatch.delenv("SAGE_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("SAGE_ALLOW_RAILWAY_FALLBACK", "1")

    def fake_check_output(argv, text, env):
        return json.dumps({"SAGE_API_KEY": "railway-key"})  # DATABASE_URL missing

    monkeypatch.setattr(prod_probe.subprocess, "check_output", fake_check_output)

    try:
        prod_probe.resolve_creds()
        assert False, "expected RuntimeError naming the missing variable"
    except RuntimeError as e:
        assert "DATABASE_URL" in str(e)


def test_resolve_creds_gate_set_fallback_works(monkeypatch):
    """With the gate var set and env vars absent, a complete railway payload resolves
    normally (mocked subprocess.check_output — no live call)."""
    monkeypatch.delenv("SAGE_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("SAGE_ALLOW_RAILWAY_FALLBACK", "1")

    payload = {
        "SAGE_API_KEY": "railway-key",
        "DATABASE_URL": FAKE_DSN,
        "SAGE_TEST_USER_IDS": "u1,u2",
    }

    def fake_check_output(argv, text, env):
        assert argv == ["railway", "variables", "--json"]
        return json.dumps(payload)

    monkeypatch.setattr(prod_probe.subprocess, "check_output", fake_check_output)

    creds = prod_probe.resolve_creds()
    assert creds.api_key == "railway-key"
    assert creds.database_url == FAKE_DSN
    assert creds.test_user_ids == "u1,u2"


# ─────────────────────────────────────────────────────────────────────────────
# chat() — ChatResult.status (review Critical: 4xx/5xx must be visible to callers,
# not silently absorbed into headers/text as if it were a 2xx)
# ─────────────────────────────────────────────────────────────────────────────

def _fake_curl_run(stdout, returncode=0, stderr=""):
    def fake_run(argv, capture_output, text):
        class _R:
            pass
        r = _R()
        r.stdout = stdout
        r.returncode = returncode
        r.stderr = stderr
        return r
    return fake_run


def test_chat_status_200(monkeypatch):
    monkeypatch.setattr(
        prod_probe.subprocess, "run",
        _fake_curl_run("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n"
                       '{"message": "hi"}'))
    result = prod_probe.chat("sid-1", "hello", base_url="https://x", api_key="k")
    assert result.status == 200
    assert result.message == "hi"


def test_chat_status_500(monkeypatch):
    monkeypatch.setattr(
        prod_probe.subprocess, "run",
        _fake_curl_run("HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\n"
                       "upstream error"))
    result = prod_probe.chat("sid-2", "hello", base_url="https://x", api_key="k")
    assert result.status == 500


def test_chat_status_takes_last_block_on_redirect(monkeypatch):
    """curl -i on a redirected/relayed request emits one header block per hop, all
    concatenated ahead of the body. status must reflect the FINAL response actually
    delivered, not an intermediate 3xx/100-continue block."""
    raw = ("HTTP/1.1 301 Moved Permanently\r\nLocation: https://x/chat/\r\n\r\n"
           "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n"
           '{"message": "hi"}')
    monkeypatch.setattr(prod_probe.subprocess, "run", _fake_curl_run(raw))
    result = prod_probe.chat("sid-3", "hello", base_url="https://x", api_key="k")
    assert result.status == 200
    # the final block's headers, not the 301's, populate .headers
    assert result.headers.get("content-type") == "application/json"


def test_chat_status_zero_on_malformed_response(monkeypatch):
    """No parsable HTTP status line at all (e.g. a transport-level failure that still
    put something on stdout) -> status=0, never a false 2xx."""
    monkeypatch.setattr(prod_probe.subprocess, "run", _fake_curl_run("not an http response"))
    result = prod_probe.chat("sid-4", "hello", base_url="https://x", api_key="k")
    assert result.status == 0


def test_chat_status_zero_on_empty_stdout(monkeypatch):
    monkeypatch.setattr(prod_probe.subprocess, "run", _fake_curl_run(""))
    result = prod_probe.chat("sid-5", "hello", base_url="https://x", api_key="k")
    assert result.status == 0
