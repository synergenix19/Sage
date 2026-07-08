import logging
import os
import httpx
from sage_poc.state import SageState

logger = logging.getLogger(__name__)

_URL = os.environ.get("SUPABASE_URL")
_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
_HEADERS = {
    "apikey": _KEY or "",
    "Authorization": f"Bearer {_KEY or ''}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

# Shared connection pool — eliminates the per-call TCP handshake that previously
# opened 2 separate connections per audit write (auth pre-check + write POST).
_audit_client: httpx.AsyncClient | None = None

# De-dup state for the auth pre-check warning: under a sustained auth-API outage,
# _user_exists_in_auth fails on every write and would otherwise log a WARNING per
# write (spam). Set True on the first failure, suppressed until a pre-check
# succeeds again — which resets it. Fail-open (returns True) is unaffected; only
# the logging is de-duped.
_PRECHECK_DEGRADED = False


def _get_audit_client() -> httpx.AsyncClient:
    global _audit_client
    if _audit_client is None:
        _audit_client = httpx.AsyncClient()
    return _audit_client


async def _user_exists_in_auth(user_id: str) -> bool:
    """Return True if user_id is present in auth.users.

    Fails open (True) on any network or timeout error so the write is still
    attempted — if that write then fails, it surfaces as a CRITICAL log.
    """
    global _PRECHECK_DEGRADED
    try:
        r = await _get_audit_client().get(
            f"{_URL}/auth/v1/admin/users/{user_id}",
            headers={"apikey": _KEY or "", "Authorization": f"Bearer {_KEY or ''}"},
            timeout=3.0,
        )
        _PRECHECK_DEGRADED = False
        return r.status_code == 200
    except Exception as exc:
        if not _PRECHECK_DEGRADED:
            logger.warning(
                "audit pre-check could not verify user %s: %s — attempting write anyway "
                "(further pre-check warnings suppressed until a check succeeds)",
                user_id, exc,
            )
            _PRECHECK_DEGRADED = True
        return True


async def write_identity_substitution_audit(
    session_id: str,
    turn_number: int,
    rule_id: str,
    original_response_hash: str,
    original_response_text: str,
    substitute_with: str,
    user_id: str | None,
) -> None:
    """Write the full original response to a RESTRICTED audit table.

    This table is separate from session_audit and must have row-level security
    permitting access only to the DPO role and authorized clinicians.
    It exists to satisfy PDPL Art. 6 right-to-challenge: if a user asks
    'why did you say that?', the original automated-decision output is
    recoverable without relying on sha256 reversal.

    Table: identity_substitution_audit
    Required columns: session_id, turn_number, rule_id, original_response_hash,
                      original_response_text, substitute_with, user_id, created_at
    RLS policy: SELECT restricted to dpo_role and clinician_admin_role only.
    """
    if not _URL or not _KEY:
        return
    row = {
        "session_id":             session_id,
        "turn_number":            turn_number,
        "rule_id":                rule_id,
        "original_response_hash": original_response_hash,
        "original_response_text": original_response_text,
        "substitute_with":        substitute_with,
        "user_id":                user_id,
    }
    try:
        r = await _get_audit_client().post(
            f"{_URL}/rest/v1/identity_substitution_audit",
            headers=_HEADERS,
            json=row,
            timeout=5.0,
        )
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        # A lost identity_substitution row is a PDPL Art. 6 right-to-challenge loss —
        # same "AUDIT FAILURE" token as the session_audit write-drop path so a
        # log-match alert catches both.
        logger.critical(
            "AUDIT FAILURE — identity_substitution_audit dropped (session %s turn %s "
            "user %s rule %s): %s — body: %s",
            session_id, turn_number, user_id, rule_id, exc, exc.response.text,
        )
    except Exception as exc:
        # Classified by consequence (an audit row was lost), not by exception type —
        # a ConnectError/timeout/JSON drop here is as much a lost PDPL Art. 6 record
        # as an FK/HTTPStatusError drop above.
        logger.critical(
            "AUDIT FAILURE — identity_substitution_audit dropped (session %s turn %s "
            "user %s rule %s): %s",
            session_id, turn_number, user_id, rule_id, exc,
        )


async def _supabase_insert(table: str, row: dict) -> None:
    """Minimal reusable POST to a Supabase REST table. Raises on failure — callers
    that need fail-open behaviour (e.g. shadow_eval) must catch around this call.

    Mirrors the base URL / service key / headers used by
    write_identity_substitution_audit and _write_session_audit_row, but is not
    tied to a specific table's row shape.
    """
    if not _URL or not _KEY:
        raise RuntimeError("Supabase URL/service key not configured")
    r = await _get_audit_client().post(
        f"{_URL}/rest/v1/{table}",
        headers=_HEADERS,
        json=row,
        timeout=5.0,
    )
    r.raise_for_status()


def _build_session_audit_row(state: SageState) -> dict:
    row = {
        "session_id":             state.get("session_id", ""),
        "turn_number":            state.get("turn_number", 0),
        "node_path":              state.get("path") or [],
        "primary_intent":         state.get("primary_intent"),
        "secondary_intent":       state.get("secondary_intent"),
        "intent_confidence":      state.get("intent_confidence"),
        "active_skill_id":        state.get("active_skill_id") or state.get("completed_skill_id") or None,
        "active_step_id":         state.get("active_step_id") or None,
        "skill_match_method":     state.get("skill_match_method") or None,
        "knowledge_source":       state.get("knowledge_source") or None,
        "knowledge_passage_ids":  [p.get("source_id", "") for p in state.get("knowledge_passages") or []],
        "knowledge_abstain":      bool(state.get("knowledge_abstain", False)),
        "knowledge_query_raw":      state.get("knowledge_query_raw") or None,
        "knowledge_query_searched": state.get("knowledge_query_searched") or None,
        "knowledge_top_similarity": state.get("knowledge_top_similarity"),
        "crisis_state":           state.get("crisis_state"),
        "crisis_flags":           state.get("crisis_flags") or [],
        "s3_score":               state.get("s3_score"),  # advisory; see CRADLE sweep 2026-06-05
        "clinical_flags":         state.get("clinical_flags") or [],
        "engagement":             state.get("engagement"),
        "emotional_intensity":    state.get("emotional_intensity"),
        "model_version":          state.get("model_version"),
        "latency_ms":             state.get("latency_ms"),
        "freeflow_gen_ms":        state.get("freeflow_gen_ms"),
        "translate_out_ms":       state.get("translate_out_ms"),
        "user_id":                state.get("user_id") or None,
        "re_escalation_within_monitoring": state.get("re_escalation_within_monitoring"),
    }
    # v7.1 tiering (F / schema-delta): the tier classification is auditable ONLY when the flag
    # is ON (safety_check omits crisis_tier when OFF). Including it conditionally keeps a flag-OFF
    # audit row byte-identical to master (Check B) and means migration 006 (crisis_tier/tier_rule_id
    # columns) is required only before the flag is flipped ON — a deploy gate, not a merge gate.
    if state.get("crisis_tier") is not None:
        row["crisis_tier"] = state.get("crisis_tier")
        row["tier_rule_id"] = state.get("tier_rule_id")
    # B0 §4.5 precedence (flag-gated, same discipline as tiering above): included ONLY when a
    # safety route actually fired this turn (apply_precedence emits nothing when the flag is OFF,
    # and an empty fired-list is dropped here). Keeps a flag-OFF / no-safety row byte-identical to
    # master; the precedence columns' migration is a flag-flip deploy gate, not a merge gate.
    # The full fired list is written even when precedence suppressed the lower routes (never dropped).
    if state.get("fired_safety_routes"):
        row["fired_safety_routes"] = state.get("fired_safety_routes")
        row["precedence_winner"] = state.get("precedence_winner")
    return row


async def _write_session_audit_row(row: dict, prefer: str, label: str) -> None:
    """Pre-check user existence, then write. Loud on any post-check failure."""
    user_id = row.get("user_id")

    if user_id and not await _user_exists_in_auth(user_id):
        logger.info(
            "%s skipped: user_id %s not found in auth.users "
            "(session %s turn %s) — likely eval/test traffic",
            label, user_id, row.get("session_id"), row.get("turn_number"),
        )
        return

    try:
        r = await _get_audit_client().post(
            f"{_URL}/rest/v1/session_audit",
            headers={**_HEADERS, "Prefer": prefer},
            json=row,
            timeout=5.0,
        )
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        # Pre-check passed but write failed — this must not be silent.
        logger.critical(
            "AUDIT FAILURE — %s dropped (session %s turn %s user %s): %s — body: %s",
            label, row.get("session_id"), row.get("turn_number"), user_id,
            exc, exc.response.text,
        )
    except Exception as exc:
        # Classified by consequence (an audit row was lost), not by exception type —
        # a ConnectError/timeout/JSON drop is as much a lost audit row as an FK
        # failure, so this must use the same CRITICAL level and "AUDIT FAILURE"
        # token as the HTTPStatusError branch above (a log-match alert must catch
        # both).
        logger.critical(
            "AUDIT FAILURE — %s dropped (session %s turn %s user %s): %s",
            label, row.get("session_id"), row.get("turn_number"), user_id, exc,
        )


async def write_session_audit(state: SageState) -> None:
    """Write or update a session audit row (merge-duplicates — last write wins).

    Use for the final state of a completed output_gate pass, where the complete
    node_path (including all intermediate markers) should be the authoritative record.
    """
    if not _URL or not _KEY:
        return
    await _write_session_audit_row(
        _build_session_audit_row(state),
        prefer="resolution=merge-duplicates",
        label="session_audit",
    )

