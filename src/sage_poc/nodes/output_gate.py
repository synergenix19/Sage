import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from sage_poc.state import SageState
from sage_poc.language import async_translate_to_arabic
from sage_poc.config import AUDIT_LOG_ENABLED
from sage_poc.rules import engine as rules_engine
from sage_poc.prompts.summarizer import summarise_history

_log = logging.getLogger(__name__)

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

JAILBREAK_RESPONSE = (
    "I'm Sage, a wellness companion here to offer emotional support and evidence-based coping "
    "techniques. That's my role. What's been on your mind today?"
)


async def _log_clinical_review(
    user_id: str,
    session_id: str,
    flags: list[str],
    turn_count: int,
) -> None:
    """Deterministic clinician review log: fires when Layer 1 safety rules detected flags.
    source='layer1_safety' distinguishes this from the LLM tool path.
    """
    try:
        from server import app  # noqa: PLC0415
        from sage_poc.memory.notification import PostgresNotifier  # noqa: PLC0415
        pool = getattr(app.state, "_db_pool", None)
        if not pool:
            return
        notifier = PostgresNotifier(pool)
        await notifier.notify_review_required(
            user_id=user_id,
            session_id=session_id,
            reason=f"clinical flags detected: {', '.join(flags)}",
            source="layer1_safety",
            payload={"flags": flags, "turn_count": turn_count},
        )
    except Exception as exc:
        _log.warning("[output_gate] _log_clinical_review failed: %s", exc)


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
        pool = app.state._db_pool
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

    if gate_path not in ("scope_refusal", "jailbreak"):
        cultural_violations = rules_engine.evaluate("cultural_output", {
            "response_text": response_en,
            "message_en": state.get("message_en", ""),
            "clinical_flags": state.get("clinical_flags", []),
        })
        for rule in cultural_violations.fired:
            print(
                f"\n[CULTURAL OUTPUT VIOLATION] {rule.rule_id} v{rule.version}: "
                f"{rule.action.get('message', rule.action.get('type', ''))}"
            )
        cultural_output_violations = [r.rule_id for r in cultural_violations.fired]
    else:
        cultural_output_violations = []

    violations = _FORMAT_VIOLATIONS.findall(response_en)
    if violations:
        print(f"\n[FORMAT VIOLATION] Disallowed formatting detected: {violations}")

    if lang == "ar":
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
            "active_skill": state.get("active_skill_id"),
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
        }
        print(f"\n[AUDIT] {json.dumps(audit, indent=2)}")

        if state.get("clinical_flags"):
            print(f"\n[CLINICAL FLAGS] {', '.join(state['clinical_flags'])}")
        if state.get("escalation_triggered"):
            esc = state["escalation_triggered"]
            print(f"\n[ESCALATION {esc['level']}] {esc['reason']}")

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
            asyncio.create_task(
                _persist_session_summary(
                    session_id, user_id, new_summary,
                    state.get("crisis_flags", []),
                    state.get("clinical_flags", []),
                    skills_used=[state["active_skill_id"]] if state.get("active_skill_id") else [],
                    mood_score=float(state.get("emotional_intensity", 5)),
                )
            )

    all_flags = (state.get("clinical_flags") or []) + (state.get("crisis_flags") or [])
    if all_flags and session_id and user_id:
        asyncio.create_task(
            _log_clinical_review(
                user_id=user_id,
                session_id=session_id,
                flags=all_flags,
                turn_count=state.get("turn_count", 0),
            )
        )

    return {
        "response": final_response,
        "gate_path": gate_path or "standard",
        "path": path,
        "turn_count": next_turn,
        "conversation_history": new_history,
        "conversation_summary": new_summary,
        "cultural_output_violations": cultural_output_violations,
    }
