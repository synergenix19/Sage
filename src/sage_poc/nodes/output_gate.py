import asyncio
import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from sage_poc.state import SageState
from sage_poc.language import async_translate_to_arabic
from sage_poc.config import AUDIT_LOG_ENABLED
from sage_poc.rules import engine as rules_engine
from sage_poc.prompts.summarizer import summarise_history
from sage_poc.audit import write_session_audit, write_session_audit_initial, write_identity_substitution_audit

_log = logging.getLogger(__name__)

_FLAG_CONFIG_PATH = Path(__file__).parent.parent / "rules" / "data" / "flag_lifecycle_config.json"
with _FLAG_CONFIG_PATH.open() as _f:
    _FLAG_LIFECYCLE_CONFIG: dict = json.load(_f)
_CROSS_SESSION_FLAGS: dict[str, bool] = _FLAG_LIFECYCLE_CONFIG.get("cross_session_persistence", {})

SCOPE_REFUSAL_RESPONSE = (
    "That's a question better answered by a medical professional or licensed therapist. "
    "I want to make sure you get accurate information. I can help you think through "
    "how you're feeling about it, or find some general information. Would either of those help?"
)

_FORMAT_VIOLATIONS = re.compile(
    r"—"                            # em dash
    r"|\*\*"                        # bold markdown
    r"|["
    r"\U0001F300-\U0001F9FF"        # misc symbols, emoticons, transport, flags
    r"\U00002600-\U000027BF"        # misc symbols (weather, chess, etc.)
    r"\U0001FA00-\U0001FAFF"        # extended symbols and pictographs
    r"]"
)

_BANNED_OPENER_PATTERNS: list[str] = [
    r"it sounds like\b",
    r"that sounds (really |very |incredibly |quite )?(tough|hard|difficult|painful|overwhelming|exhausting|challenging|frustrating|lonely|scary|frightening)\b",
    r"it seems like\b",
    r"i can hear (that|how|the)\b",
    r"i can see (that|how)\b",
    r"it looks like\b",
]
_BANNED_OPENER_RE = re.compile(
    r"(?i)^(" + "|".join(_BANNED_OPENER_PATTERNS) + r")"
)
_HAS_ARABIC_RE = re.compile(r"[؀-ۿ]")
_BANNED_OPENER_CORRECTION = (
    "Your previous response began with a banned opener. "
    "Respond again without beginning with 'It sounds like', 'That sounds', or any "
    "reflective paraphrase. Name the specific thing the user said and ask one direct question."
)

# PLACEHOLDER — pending clinical review before Gitex.
# Constraints: (1) must NOT begin with a banned or near-banned opener (regex or structural),
# (2) Khaleeji wellness-companion register — warm, open-ended, never "I cannot respond to that",
# (3) safe to emit on any turn including after heavy disclosure (not dismissive),
# (4) must work in EN and AR turns (translation pipeline still runs on this string),
# (5) treat as user-facing copy with measurable frequency, not a rare error message.
# Review doc: docs/superpowers/reviews/FALLBACK_RESPONSE_REVIEW.md
_VETTED_FALLBACK_RESPONSE = "I'm here with you. What would feel most helpful to share right now?"

JAILBREAK_RESPONSE = (
    "I'm Sage, a wellness companion here to offer emotional support and evidence-based coping "
    "techniques. That's my role. What's been on your mind today?"
)


async def _log_clinical_review(
    session_id: str,
    user_id: str,
    crisis_flags: list[str],
    clinical_flags: list[str],
) -> None:
    """Deterministic clinician review log: fires when Layer 1 safety rules detected flags.
    source='layer1_safety' distinguishes this from the LLM tool path.
    severity='high' for crisis, 'medium' for clinical-only (DB constraint: low/medium/high).
    """
    try:
        from server import app  # noqa: PLC0415
        from sage_poc.memory.notification import PostgresNotifier  # noqa: PLC0415
        pool = getattr(app.state, "_db_pool", None)
        if not pool:
            return
        severity = "high" if crisis_flags else "medium"
        reason_parts = []
        if crisis_flags:
            reason_parts.append(f"crisis flags: {', '.join(crisis_flags)}")
        if clinical_flags:
            reason_parts.append(f"clinical flags: {', '.join(clinical_flags)}")
        notifier = PostgresNotifier(pool)
        await notifier.notify_review_required(
            user_id=user_id,
            session_id=session_id,
            reason="; ".join(reason_parts),
            source="layer1_safety",
            payload={"flags": crisis_flags + clinical_flags},
            severity=severity,
        )
    except Exception as exc:
        _log.warning("[output_gate] _log_clinical_review failed: %s", exc)


async def _write_persisted_clinical_flags(
    user_id: str,
    clinical_flags: list[str],
) -> None:
    """Write cross-session-eligible flags to user_therapeutic_profiles.
    Gated by flag_lifecycle_config.json cross_session_persistence values.
    Non-fatal — errors are logged only.
    """
    flags_to_persist = [f for f in clinical_flags if _CROSS_SESSION_FLAGS.get(f, False)]
    try:
        from server import app  # noqa: PLC0415
        from sage_poc.memory.postgres_repository import PostgresMemoryRepository  # noqa: PLC0415
        pool = getattr(app.state, "_db_pool", None)
        if pool is None:
            return
        repo = PostgresMemoryRepository(pool)
        await repo.write_persisted_clinical_flags(user_id, flags_to_persist)
    except Exception as exc:
        _log.warning("[output_gate] write_persisted_clinical_flags failed: %s", exc)


async def _persist_session_summary(
    session_id: str,
    user_id: str,
    summary_text: str,
    crisis_flags: list[str],
    clinical_flags: list[str],
    skills_used: list[str] | None = None,
    mood_score: float | None = None,
) -> None:
    """Persist session summary to database. Non-fatal — errors are logged only."""
    try:
        from server import app  # noqa: PLC0415
        from sage_poc.memory.postgres_repository import PostgresMemoryRepository  # noqa: PLC0415
        from sage_poc.memory.embedding import get_embedding_async  # noqa: PLC0415
        pool = getattr(app.state, "_db_pool", None)
        if pool is None:
            return
        embedding = await get_embedding_async(summary_text)
        safety_level = (
            "crisis" if crisis_flags
            else "clinical" if clinical_flags
            else "normal"
        )
        repo = PostgresMemoryRepository(pool)
        await repo.save_session_summary(
            session_id, user_id, summary_text, embedding, safety_level,
            skills_used=skills_used,
            mood_score=mood_score,
        )
    except Exception:
        _log.warning("Failed to persist session summary for session %s", session_id)
    # Flag persistence is intentionally decoupled from session summary persistence.
    # A summary write failure must not block flag persistence: persisted_clinical_flags
    # feeds safety_check at the start of the next session (Cardinal Rule 4 path) and
    # must be written regardless of whether the summary write succeeded.
    try:
        await _write_persisted_clinical_flags(user_id, clinical_flags)
    except Exception as exc:
        _log.warning("[output_gate] write_persisted_clinical_flags failed: %s", exc)


async def output_gate_node(state: SageState) -> dict:
    gate_path = state.get("gate_path")
    lang = state["detected_language"]
    path = (state.get("path") or []) + ["output_gate"]
    session_id = state.get("session_id")
    user_id = state.get("user_id")

    if gate_path == "scope_refusal":
        response_en = SCOPE_REFUSAL_RESPONSE
    elif gate_path == "jailbreak":
        response_en = JAILBREAK_RESPONSE
    else:
        response_en = state["response_en"] or ""

    _arabic_chars = len(_HAS_ARABIC_RE.findall(response_en))
    _total_chars = len(response_en.strip())
    _response_en_is_arabic = (
        lang == "ar"
        and gate_path not in ("scope_refusal", "jailbreak")
        and _total_chars > 0
        and (_arabic_chars / _total_chars) > 0.4
    )
    if _response_en_is_arabic:
        _log.warning(
            "[output_gate] response_en is predominantly Arabic "
            "(ratio=%.2f, session=%s, gate=%s) -- "
            "skipping EN validators and translation; audit for CU-DM-001 regression",
            _arabic_chars / _total_chars, session_id, gate_path,
        )

    if gate_path not in ("scope_refusal", "jailbreak") and not _response_en_is_arabic:
        cultural_violations = rules_engine.evaluate("cultural_output", {
            "response_text": response_en,
            "message_en": state.get("message_en", ""),
            "clinical_flags": state.get("clinical_flags", []),
        })
        _identity_sub_rule_id: str | None = None
        _original_response_hash: str | None = None
        _original_response_text: str | None = None
        for rule in cultural_violations.fired:
            _log.warning(
                "[output_gate] cultural violation %s v%s: %s",
                rule.rule_id, rule.version,
                rule.action.get('message', rule.action.get('type', '')),
            )
            if rule.action.get("type") == "substitute" and _identity_sub_rule_id is None:
                _original_response_text = response_en
                _original_response_hash = hashlib.sha256(response_en.encode()).hexdigest()[:16]
                _identity_sub_rule_id = rule.rule_id
                response_en = rule.action["substitute_with"]
                _log.warning(
                    "[output_gate] Rule %s substituted response (hash: %s)",
                    rule.rule_id, _original_response_hash,
                )
                # Write full original text to restricted PDPL audit table (non-fatal).
                # The main audit log records only the hash; the original text lives here
                # under RLS policies permitting DPO and clinician_admin access only.
                if session_id:
                    asyncio.create_task(
                        write_identity_substitution_audit(
                            session_id=session_id,
                            turn_number=state.get("turn_number", 0),
                            rule_id=rule.rule_id,
                            original_response_hash=_original_response_hash,
                            original_response_text=_original_response_text,
                            substitute_with=rule.action["substitute_with"],
                            user_id=user_id,
                        )
                    )
        cultural_output_violations = [r.rule_id for r in cultural_violations.fired]
    else:
        _identity_sub_rule_id = None
        _original_response_hash = None
        _original_response_text = None
        cultural_output_violations = []

    banned_opener_violation = False
    banned_opener_fallback_used = False
    # Substitute fallback on empty retry response — the second LLM call can return "" due to
    # rate limiting, token-budget overflow, or other transient failures. Empty is not valid
    # wellness-companion copy; treat it the same as an exhausted-retry banned opener.
    _retry_count = state.get("banned_opener_retry_count", 0)
    if (
        not response_en
        and _retry_count >= 1
        and gate_path not in ("scope_refusal", "jailbreak")
    ):
        response_en = _VETTED_FALLBACK_RESPONSE
        banned_opener_fallback_used = True
        path = path + ["output_gate_fallback_substituted"]
        _log.warning("[output_gate] empty response on retry — substituting vetted fallback")
        if session_id:
            _empty_audit = asyncio.create_task(
                write_session_audit({**state, "path": path, "gate_path": gate_path or "standard"})
            )
            _empty_audit.add_done_callback(
                lambda t: _log.warning("[output_gate] empty-retry audit error: %s", t.exception())
                if not t.cancelled() and t.exception() else None
            )
    if gate_path not in ("scope_refusal", "jailbreak") and response_en and not _response_en_is_arabic:
        banned_match = _BANNED_OPENER_RE.match(response_en.lstrip())
        if banned_match:
            retry_count = _retry_count
            if retry_count < 1:
                _log.warning(
                    "[output_gate] banned opener detected (%r) — routing back to freeflow_respond for retry",
                    banned_match.group(0),
                )
                retry_path = path + ["output_gate_banned_opener_retry"]
                if session_id:
                    _retry_audit = asyncio.create_task(
                        write_session_audit_initial({**state, "path": retry_path, "gate_path": gate_path or "standard"})
                    )
                    _retry_audit.add_done_callback(
                        lambda t: _log.warning("[output_gate] retry audit error: %s", t.exception())
                        if not t.cancelled() and t.exception() else None
                    )
                return {
                    "banned_opener_retry_count": retry_count + 1,
                    "banned_opener_correction": _BANNED_OPENER_CORRECTION,
                    "path": retry_path,
                    # Preserve expected state keys so downstream tests and LangGraph
                    # state merges don't encounter missing fields on this early exit.
                    "cultural_output_violations": cultural_output_violations,
                    "identity_substitution_rule_id": None,
                    "original_response_hash": None,
                    "original_response_text": None,
                    "banned_opener_violation": False,
                }
            else:
                # Retry exhausted — substitute vetted fallback rather than passing the
                # violating response to the user. Append marker to path so it surfaces in
                # X-Sage-Node-Path and audit rows; reviewers can distinguish "fallback
                # substituted" from "violation passed through."
                response_en = _VETTED_FALLBACK_RESPONSE
                banned_opener_violation = True
                banned_opener_fallback_used = True
                path = path + ["output_gate_fallback_substituted"]
                _log.warning(
                    "[output_gate] banned opener persists after retry — substituting vetted fallback"
                )
                if session_id:
                    _fallback_audit = asyncio.create_task(
                        write_session_audit({**state, "path": path, "gate_path": gate_path or "standard"})
                    )
                    _fallback_audit.add_done_callback(
                        lambda t: _log.warning("[output_gate] fallback audit error: %s", t.exception())
                        if not t.cancelled() and t.exception() else None
                    )

    violations = _FORMAT_VIOLATIONS.findall(response_en)
    if violations:
        _log.warning("[output_gate] format violations: %s", violations)

    if lang == "ar" and not _response_en_is_arabic:
        final_response = await async_translate_to_arabic(response_en)
    else:
        final_response = response_en

    if AUDIT_LOG_ENABLED:
        audit = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "turn": state.get("turn_count", 0),
            "path": path,
            "gate_path": gate_path or "standard",
            "detected_language": lang,
            "primary_intent": state.get("primary_intent"),
            "active_skill": state.get("active_skill_id") or state.get("completed_skill_id"),
            "skill_match_method": state.get("skill_match_method"),
            "semantic_score": state.get("semantic_score"),
            "executed_step": state.get("executed_step_id"),
            "next_step": state.get("active_step_id"),
            "emotional_intensity": state.get("emotional_intensity"),
            "engagement": state.get("engagement"),
            "is_safe": state.get("is_safe"),
            "crisis_state": state.get("crisis_state", "none"),
            "s7_result": state.get("s7_result"),
            "s7_method": state.get("s7_method"),
            "clinical_flags": state.get("clinical_flags", []),
            "third_party_crisis": state.get("third_party_crisis", False),
            "escalation": state.get("escalation_triggered"),
            "knowledge_source": state.get("knowledge_source", ""),
            "knowledge_passage_ids": [
                p.get("source_id") for p in (state.get("knowledge_passages") or [])
            ],
            "knowledge_abstain": state.get("knowledge_abstain", False),
            "identity_substitution": (
                {"rule_id": _identity_sub_rule_id, "original_response_hash": _original_response_hash}
                if _identity_sub_rule_id else None
            ),
            "banned_opener_violation": banned_opener_violation,
        }
        _log.info("[output_gate] AUDIT %s", json.dumps(audit))

        if state.get("clinical_flags"):
            _log.info("[output_gate] clinical flags: %s", ', '.join(state['clinical_flags']))
        if state.get("escalation_triggered"):
            esc = state["escalation_triggered"]
            _log.warning("[output_gate] escalation L%s: %s", esc['level'], esc['reason'])

    new_history = state.get("conversation_history", []) + [
        {"role": "user", "content": state["message_en"]},
        {"role": "assistant", "content": response_en},
    ]

    next_turn = state.get("turn_count", 0) + 1
    new_summary = state.get("conversation_summary")
    if next_turn % 10 == 0:
        try:
            new_summary = await summarise_history(new_history)
            _log.info("Conversation summary generated at turn %d", next_turn)
        except Exception:
            _log.warning("Summarisation failed at turn %d; keeping prior summary", next_turn)
        if new_summary and session_id and user_id:
            _task = asyncio.create_task(
                _persist_session_summary(
                    session_id, user_id, new_summary,
                    state.get("crisis_flags", []),
                    state.get("clinical_flags", []),
                    skills_used=(
                        [state["active_skill_id"]] if state.get("active_skill_id")
                        else [state["completed_skill_id"]] if state.get("completed_skill_id")
                        else []
                    ),
                    mood_score=float(state.get("emotional_intensity", 5)),
                )
            )
            _task.add_done_callback(
                lambda t: _log.warning("[output_gate] summary persist error: %s", t.exception())
                if not t.cancelled() and t.exception() else None
            )

    _crisis_flags = state.get("crisis_flags") or []
    _clinical_flags = state.get("clinical_flags") or []
    if (_crisis_flags or _clinical_flags) and session_id and user_id:
        _review_task = asyncio.create_task(
            _log_clinical_review(session_id, user_id, _crisis_flags, _clinical_flags)
        )
        _review_task.add_done_callback(
            lambda t: _log.warning("[output_gate] clinical review error: %s", t.exception())
            if not t.cancelled() and t.exception() else None
        )

    _audit_task = asyncio.create_task(write_session_audit({**state, "path": path, "gate_path": gate_path or "standard"}))
    _audit_task.add_done_callback(
        lambda t: _log.warning("[output_gate] session audit error: %s", t.exception())
        if not t.cancelled() and t.exception() else None
    )

    return {
        "response": final_response,
        "gate_path": gate_path or "standard",
        "path": path,
        "turn_count": next_turn,
        "conversation_history": new_history,
        "conversation_summary": new_summary,
        "cultural_output_violations": cultural_output_violations,
        "identity_substitution_rule_id": _identity_sub_rule_id,
        "original_response_hash": _original_response_hash,
        "original_response_text": _original_response_text,
        "last_turn_at": datetime.now(timezone.utc).isoformat(),
        "banned_opener_retry_count": 0,
        "banned_opener_correction": None,
        "banned_opener_violation": banned_opener_violation,
        "banned_opener_fallback_used": banned_opener_fallback_used,
    }
