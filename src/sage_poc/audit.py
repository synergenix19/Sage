import logging
import os
import httpx
from sage_poc import config as _cfg
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
    try:
        r = await _get_audit_client().get(
            f"{_URL}/auth/v1/admin/users/{user_id}",
            headers={"apikey": _KEY or "", "Authorization": f"Bearer {_KEY or ''}"},
            timeout=3.0,
        )
        return r.status_code == 200
    except Exception as exc:
        logger.warning(
            "audit pre-check could not verify user %s: %s — attempting write anyway",
            user_id, exc,
        )
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
        logger.error(
            "identity_substitution_audit write failed: %s — body: %s", exc, exc.response.text
        )
    except Exception as exc:
        logger.error("identity_substitution_audit write failed: %s", exc)


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


def derive_psychoed_weave_state(state: SageState) -> str | None:
    """Node-8 audit derivation (Phase 2 Task 11, gap-2 escalation-turn fix). Single-sourced so
    output_gate.py's in-memory audit log and _build_session_audit_row below can never drift on
    the derivation:
      - an explicit "psychoed_weave_state" key in the incoming dict wins outright. Only the
        crisis node's escalation-turn audit patch sets this (graph.py's `_crisis_response_node`,
        value "escalated") -- a PSY-WEAVE-1 evaluation that resolved to crisis this turn, which
        never carries a live psychoed_serve payload of its own.
      - otherwise "pending" while a weave question is outstanding (psychoed_weave_pending),
      - "fired" once the pathway's weave has fired for this run (psychoed_weave_fired) and no
        question is currently outstanding,
      - else None (no psychoed weave activity this turn).
    """
    if "psychoed_weave_state" in state:
        return state.get("psychoed_weave_state")
    if state.get("psychoed_weave_pending"):
        return "pending"
    if state.get("psychoed_weave_fired"):
        return "fired"
    return None


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
    # C1 cards-only retrieval (flag-gated, same discipline as tiering/precedence/medical below):
    # keys included ONLY when the cards path actually ran (cards channels populated — impossible
    # with SAGE_CONSULT_SOURCES off, the node is unreachable), so a flag-OFF row stays
    # byte-identical to master and migration 018 (knowledge_retrieval_purpose) is a flag-flip
    # deploy gate, not a merge gate. PURPOSE DISCRIMINATOR (ruling condition 2): cards ids land
    # in knowledge_passage_ids (preserving sources ⊆ knowledge_passage_ids) but the row stamps
    # purpose='cards_only' so no auditor can read non-empty ids as evidence-grounded generation.
    # Evidence and cards are mutually exclusive per turn by construction (consult turns never
    # reach Node 6; KB turns never reach the cards node).
    _cards = state.get("cards_knowledge_passages") or []
    if _cards or state.get("cards_knowledge_abstain"):
        if not row["knowledge_passage_ids"]:
            row["knowledge_passage_ids"] = [p.get("source_id", "") for p in _cards]
        row["knowledge_retrieval_purpose"] = "cards_only"
        row["knowledge_top_similarity"] = (
            row["knowledge_top_similarity"]
            if row["knowledge_top_similarity"] is not None
            else state.get("cards_knowledge_top_similarity")
        )
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
    # B1 medical red-flag audit (flag-gated, same discipline as tiering/precedence above):
    # included ONLY when a medical turn fired, so a flag-OFF / non-medical row stays
    # byte-identical to master. Records WHICH phrase fired (recall measurement + post-hoc
    # referral review + the B1-full >=95% gate). Migration is a flag-flip deploy gate.
    if state.get("medical_flags"):
        row["gate_path"] = state.get("gate_path")
        row["medical_flags"] = state.get("medical_flags")
    # §1c derealization terminal audit (same conditional discipline): gate_path was ONLY persisted on
    # medical turns, so a served derealization referral audited with gate_path NULL and the prod-HTTP
    # conformance driver misclassified it presence_only (2026-07-30 increment-1 finding). Included ONLY
    # when the derealization terminal ran, so every other row stays byte-identical.
    if "derealization_response" in (row["node_path"] or []):
        row["gate_path"] = state.get("gate_path")
    # HR-1 Stage 2 high_risk_response audit (flag-gated, same discipline as tiering/
    # precedence/medical above): included ONLY when a distress branch actually resolved
    # this turn (hr_branch set by _deliver_branch), so a flag-OFF / non-HR / mid-protocol
    # (T1 entry, or the T2 reask before a branch resolves) row stays byte-identical to
    # master. Migration 013 is the flag-flip deploy gate for SAGE_HIGH_RISK_TERMINAL.
    if state.get("hr_branch"):
        row["hr_branch"] = state.get("hr_branch")
        row["hr_distress_score"] = state.get("hr_distress_score")
    # #338 D1 SILENT shadow observation (flag-gated, same discipline as tiering/precedence/medical/HR
    # above): included ONLY when the screen shadow-fired this turn (screen_shadow_action set), so a
    # flag-OFF / non-screen row stays byte-identical to master. PDPL-approved 2026-07-17: anonymised
    # class + route ONLY, never message content or free text — the writer takes exactly these fields.
    # Migration for the screen_shadow_* columns is the SAGE_D1_SCREEN_SHADOW flip deploy gate.
    if state.get("screen_shadow_action"):
        row["screen_shadow_action"] = state.get("screen_shadow_action")
        row["screen_shadow_answer_class"] = state.get("screen_shadow_answer_class")
        row["screen_shadow_branch"] = state.get("screen_shadow_branch")
    # #338 D1 ENFORCE audit fields — same flag-gated discipline; included only on a real screen turn.
    if state.get("screen_asked") or state.get("screen_branch_taken"):
        row["screen_asked"] = bool(state.get("screen_asked"))
        row["screen_answer_class"] = state.get("screen_answer_class")
        row["screen_branch_taken"] = state.get("screen_branch_taken")
    # Classifier provenance (flag-gated, same discipline as tiering/precedence/medical/HR/screen
    # above; Node-2 bistability finding 2026-07-28, consequence 3 — PDPL auditability): included
    # ONLY when SAGE_AUDIT_CLASSIFIER_PROVENANCE is ON, so a flag-OFF row stays byte-identical to
    # master. Records what is needed to RECONSTRUCT a classifier decision: the model + upstream
    # provider + seed actually in force, and the sha256 of the exact assembled classifier prompt
    # (which embeds stochastic temp-0.7 responder history — the identified bistability cause).
    # Migration 016 is the flag-flip deploy gate. Provider chain: intent_route's captured response
    # metadata (via the classifier_provider channel, already pin-fallback-resolved), else the pin,
    # else NULL. Columns may be NULL when the flag is ON but the turn bypassed intent_route
    # (e.g. crisis short-circuit) — a NULL hash on a non-classifier turn is correct provenance.
    if _cfg.AUDIT_CLASSIFIER_PROVENANCE_ENABLED:
        row["classifier_model"] = _cfg.CLASSIFIER_MODEL
        row["classifier_provider"] = (
            state.get("classifier_provider") or _cfg.OPENROUTER_PROVIDER_PIN or None
        )
        row["classifier_seed"] = _cfg.CLASSIFIER_SEED
        row["classifier_context_hash"] = state.get("classifier_context_hash")
        # Q-b: what came BACK, alongside the requested seed above — system_fingerprint
        # identifies the backend configuration that served the call (seed HONOR signal).
        # NULL when the provider exposes none; never fabricated.
        row["classifier_system_fingerprint"] = state.get("classifier_system_fingerprint")
    # Psychoed audit (flag-gated, Phase 2 Task 11; same discipline as tiering/precedence/medical/
    # HR/screen above): included ONLY when a psychoed signal fired this turn (a serve payload, a
    # matched trigger row, a collision/framing disposition, a weave in flight/fired, or the gate
    # having run), so a flag-OFF / non-psychoed row stays byte-identical to master (Check B).
    # Migration 016 is the deploy-gate for SAGE_PSYCHOED_PATHWAYS. This is also how the
    # escalation-turn row (gap-2, crisis node) picks up the marker: that call carries no live
    # psychoed_serve payload of its own, but DOES carry the explicit "psychoed_weave_state":
    # "escalated" patch, which alone trips the presence check below via derive_psychoed_weave_state.
    _psychoed_serve = state.get("psychoed_serve") or {}
    _psychoed_weave_state = derive_psychoed_weave_state(state)
    if (
        _psychoed_serve
        or state.get("psychoed_matched_row_id") is not None
        or state.get("psychoed_collision_path") is not None
        or state.get("psychoed_framing") is not None
        or _psychoed_weave_state is not None
        or state.get("psychoed_gate_action") is not None
    ):
        row["psychoed_block_ids"] = [_psychoed_serve["block_id"]] if _psychoed_serve.get("block_id") else []
        row["psychoed_matched_row_id"] = state.get("psychoed_matched_row_id")
        row["psychoed_collision_path"] = state.get("psychoed_collision_path")
        row["psychoed_framing"] = state.get("psychoed_framing")
        row["psychoed_weave_state"] = _psychoed_weave_state
        row["psychoed_template_version"] = _psychoed_serve.get("template_version")
        row["psychoed_gate_action"] = state.get("psychoed_gate_action")
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
        logger.error("%s write failed: %s", label, exc)


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

