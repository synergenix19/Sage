import logging
import os
import re
import httpx
from sage_poc.state import SageState

logger = logging.getLogger(__name__)

# Synthetic user IDs: sequential ints zero-padded to UUID form (e.g. eval harnesses, CRADLE bench).
# These are never present in auth.users, so audit writes legitimately fail the FK check.
_SYNTHETIC_UID_RE = re.compile(r"^0{8}-0{4}-0{4}-0{4}-", re.IGNORECASE)


def _is_synthetic_user_id(user_id: str | None) -> bool:
    return bool(user_id and _SYNTHETIC_UID_RE.match(user_id))

_URL = os.environ.get("SUPABASE_URL")
_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
_HEADERS = {
    "apikey": _KEY or "",
    "Authorization": f"Bearer {_KEY or ''}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}


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
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{_URL}/rest/v1/identity_substitution_audit",
                headers=_HEADERS,
                json=row,
            )
            r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "identity_substitution_audit write failed: %s — body: %s", exc, exc.response.text
        )
    except Exception as exc:
        logger.error("identity_substitution_audit write failed: %s", exc)


def _build_session_audit_row(state: SageState) -> dict:
    return {
        "session_id":             state.get("session_id", ""),
        "turn_number":            state.get("turn_number", 0),
        "node_path":              state.get("path") or [],
        "primary_intent":         state.get("primary_intent"),
        "secondary_intent":       state.get("secondary_intent"),
        "intent_confidence":      state.get("intent_confidence"),
        "active_skill_id":        state.get("active_skill_id") or None,
        "active_step_id":         state.get("active_step_id") or None,
        "skill_match_method":     state.get("skill_match_method") or None,
        "knowledge_source":       state.get("knowledge_source") or None,
        "knowledge_passage_ids":  [p.get("source_id", "") for p in state.get("knowledge_passages") or []],
        "knowledge_abstain":      bool(state.get("knowledge_abstain", False)),
        "crisis_state":           state.get("crisis_state"),
        "crisis_flags":           state.get("crisis_flags") or [],
        "clinical_flags":         state.get("clinical_flags") or [],
        "engagement":             state.get("engagement"),
        "emotional_intensity":    state.get("emotional_intensity"),
        "model_version":          state.get("model_version"),
        "latency_ms":             state.get("latency_ms"),
        "user_id":                state.get("user_id") or None,
        "re_escalation_within_monitoring": state.get("re_escalation_within_monitoring"),
    }


def _handle_audit_http_error(exc: httpx.HTTPStatusError, row: dict, label: str) -> None:
    body = exc.response.text
    # PostgreSQL FK violation (23503) on user_id — two cases:
    if '"23503"' in body and "user_id" in body:
        user_id = row.get("user_id")
        if _is_synthetic_user_id(user_id):
            # Known test/eval traffic — no real user, skip silently.
            logger.debug("%s skipped: synthetic user_id %s", label, user_id)
            return
        # Real user whose audit record was dropped — this must be visible.
        logger.critical(
            "AUDIT FAILURE — %s dropped for real user %s "
            "(session %s turn %s): FK violation. Body: %s",
            label, user_id, row.get("session_id"), row.get("turn_number"), body,
        )
        return
    logger.error("%s write failed: %s — body: %s", label, exc, body)


async def write_session_audit(state: SageState) -> None:
    """Write or update a session audit row (merge-duplicates — last write wins).

    Use for the final state of a completed output_gate pass, where the complete
    node_path (including all intermediate markers) should be the authoritative record.
    """
    if not _URL or not _KEY:
        return
    row = _build_session_audit_row(state)
    try:
        upsert_headers = {**_HEADERS, "Prefer": "resolution=merge-duplicates"}
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{_URL}/rest/v1/session_audit",
                headers=upsert_headers,
                json=row,
            )
            r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        _handle_audit_http_error(exc, row, "session_audit")
    except Exception as exc:
        logger.error("session_audit write failed: %s", exc)


async def write_session_audit_initial(state: SageState) -> None:
    """Write a session audit row only if the row does not already exist (ignore-duplicates).

    Use for intermediate writes (e.g. retry-detection early-return) so the final
    write_session_audit call always wins the race regardless of asyncio scheduling order.
    If the final write committed first, this call is silently dropped.
    If this call commits first, write_session_audit will overwrite it with the complete path.
    """
    if not _URL or not _KEY:
        return
    row = _build_session_audit_row(state)
    try:
        ignore_headers = {**_HEADERS, "Prefer": "resolution=ignore-duplicates"}
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{_URL}/rest/v1/session_audit",
                headers=ignore_headers,
                json=row,
            )
            r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        _handle_audit_http_error(exc, row, "session_audit_initial")
    except Exception as exc:
        logger.error("session_audit initial write failed: %s", exc)
