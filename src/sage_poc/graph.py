import asyncio
import json
import logging
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from sage_poc.state import SageState
from sage_poc.nodes.safety_check import safety_check_node
from sage_poc.nodes.intent_route import intent_route_node
from sage_poc.nodes.low_confidence_respond import low_confidence_respond_node
from sage_poc.nodes.skill_select import skill_select_node
from sage_poc.nodes.skill_executor import skill_executor_node
from sage_poc.nodes.freeflow_respond import freeflow_respond_node
from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node
from sage_poc.config import CRISIS_LINE_UAE
from sage_poc.nodes.output_gate import output_gate_node
from sage_poc.config import AUDIT_LOG_ENABLED
from sage_poc.audit import write_session_audit

_log = logging.getLogger(__name__)


def _get_crisis_review_pool():
    """Lazy accessor for asyncpg pool in _crisis_response_node."""
    try:
        from server import app  # noqa: PLC0415
        return getattr(app.state, "_db_pool", None)
    except Exception:
        return None


async def _crisis_response_node(state: SageState) -> dict:
    from sage_poc.rules import engine as rules_engine

    prior_crisis_state = state.get("crisis_state", "none")
    is_reescalation = prior_crisis_state == "monitoring"

    lang = state.get("detected_language", "en")

    crisis_result = rules_engine.evaluate("crisis_content", {
        "language": lang,
        "crisis_level": "acute",
    })

    if crisis_result.fired:
        response_text = crisis_result.fired[0].action["response_text"]
    else:
        # Hard fallback: should never fire if JSON files are present
        response_text = (
            f"Please reach out for support now. UAE: MoHAP Counselling Line {CRISIS_LINE_UAE} (free, 24/7) or emergency: 999."
            if lang != "ar"
            else f"أرجوك تواصل مع خط وزارة الصحة {CRISIS_LINE_UAE} أو الطوارئ 999 الآن."
        )

    path = state["path"] + ["crisis_response"]

    _audit_task = asyncio.create_task(write_session_audit({
        **state,
        "path": path,
        "gate_path": "crisis",
        "crisis_state": "monitoring",
        "re_escalation_within_monitoring": is_reescalation,
    }))
    _audit_task.add_done_callback(
        lambda t: _log.warning("[crisis_response] session audit error: %s", t.exception())
        if not t.cancelled() and t.exception() else None
    )

    async def _notify_crisis_review() -> None:
        try:
            from sage_poc.memory.notification import PostgresNotifier  # noqa: PLC0415
            pool = _get_crisis_review_pool()
            if not pool:
                return
            notifier = PostgresNotifier(pool)
            await notifier.notify_review_required(
                user_id=state.get("user_id") or "",
                session_id=state.get("session_id") or "",
                reason=f"crisis flags: {', '.join(state.get('crisis_flags', []))}",
                source="layer1_safety",
                payload={"flags": state.get("crisis_flags", []) + state.get("clinical_flags", [])},
                severity="high",
            )
        except Exception as exc:
            _log.warning("[crisis_response] clinician_review_queue write failed: %s", exc)

    _notify_task = asyncio.create_task(_notify_crisis_review())
    _notify_task.add_done_callback(
        lambda t: _log.warning("[crisis_response] notify_crisis_review error: %s", t.exception())
        if not t.cancelled() and t.exception() else None
    )

    if AUDIT_LOG_ENABLED:
        audit = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "CRISIS_RESPONSE",
            "turn": state.get("turn_count"),
            "detected_language": lang,
            "crisis_flags": state.get("crisis_flags", []),
            "clinical_flags": state.get("clinical_flags", []),
            "active_skill_cleared": state.get("active_skill_id"),
            "crisis_content_rule": crisis_result.fired[0].rule_id if crisis_result.fired else "fallback",
            "re_escalation_within_monitoring": is_reescalation,
        }
        _log.info("[graph] AUDIT:CRISIS %s", json.dumps(audit))

    history = state.get("conversation_history", []) + [
        {"role": "user", "content": state.get("message_en", state.get("raw_message", ""))},
        {"role": "assistant", "content": response_text},
    ]

    return {
        "is_safe": False,
        "active_skill_id": None,
        "active_step_id": None,
        "gate_path": "crisis",
        "response": response_text,
        "response_en": response_text,
        "path": path,
        "conversation_history": history,
        "turn_count": state.get("turn_count", 0) + 1,
        "crisis_state": "monitoring",
        "s7_result": None,
        "s7_method": None,
        "re_escalation_within_monitoring": is_reescalation,
        # output_gate is bypassed for crisis responses (routes to END directly).
        # Without this, the stale-check gap is measured from the pre-crisis turn,
        # potentially under-counting by the duration of the crisis turn itself.
        "last_turn_at": datetime.now(timezone.utc).isoformat(),
    }


def _route_after_safety(state: SageState) -> str:
    if state.get("crisis_state") == "monitoring":
        # In monitoring: only re-escalate if S1-S6 fired directly or S7 classified a new crisis
        if not state["is_safe"] or state.get("s7_result") == "NEW_CRISIS":
            return "crisis"
        return "safe"
    return "safe" if state["is_safe"] else "crisis"


def _route_after_intent(state: SageState) -> str:
    intent = state.get("primary_intent", "general_chat")
    confidence = state.get("intent_confidence", 1.0)

    if intent == "crisis":
        return "crisis"
    if intent == "scope_refusal":
        return "gate"
    if intent == "jailbreak":
        # NOTE: jailbreak in monitoring state: persona reassertion takes priority.
        # crisis_state remains 'monitoring' — S7 will re-evaluate on the next turn.
        return "gate"
    # Post-crisis monitoring takes priority over confidence gating — short or fragmented
    # messages are expected after a crisis; route to skill_select regardless of confidence.
    if state.get("crisis_state") == "monitoring":
        return "skill_select"
    if confidence < 0.6:
        return "low_confidence"
    if intent == "exit_skill":
        return "skill_executor" if state.get("active_skill_id") else "freeflow"
    if intent == "new_skill":
        # If a skill is already active, don't re-run selection — skill_select would
        # either pick a different skill (hijack) or find no match and write
        # active_skill_id=None, clearing the checkpoint for the next turn.
        if state.get("active_skill_id"):
            return "skill_executor"
        return "skill_select"
    if intent == "info_request":
        return "skill_select"
    if intent == "skill_continuation" and state.get("active_skill_id"):
        return "skill_executor"
    return "freeflow"


def _route_after_skill_select(state: SageState) -> str:
    # info_request routes to knowledge_retrieve regardless of active skill — the
    # skill_select node preserves active_skill_id, so the skill survives this turn.
    if state.get("primary_intent") == "info_request":
        return "knowledge_retrieve"
    if state.get("active_skill_id"):
        return "skill_executor"
    return "freeflow"


def _route_after_skill_executor(state: SageState) -> str:
    if state.get("re_escalation_within_monitoring"):
        return "crisis"
    return "freeflow"


def _route_after_output_gate(state: SageState) -> str:
    # Cardinal Rule 4: crisis output is deterministic and never subject to stylistic retry.
    if state.get("crisis_state") not in (None, "none"):
        return END
    if state.get("banned_opener_correction") and state.get("banned_opener_retry_count", 0) <= 1:
        return "freeflow_respond"
    return END


def build_graph(checkpointer=None) -> CompiledStateGraph:
    graph = StateGraph(SageState)

    graph.add_node("safety_check", safety_check_node)
    graph.add_node("intent_route", intent_route_node)
    graph.add_node("low_confidence_respond", low_confidence_respond_node)
    graph.add_node("skill_select", skill_select_node)
    graph.add_node("knowledge_retrieve", knowledge_retrieve_node)
    graph.add_node("skill_executor", skill_executor_node)
    graph.add_node("freeflow_respond", freeflow_respond_node)
    graph.add_node("output_gate", output_gate_node)
    graph.add_node("crisis_response", _crisis_response_node)

    graph.set_entry_point("safety_check")

    graph.add_conditional_edges("safety_check", _route_after_safety, {
        "safe": "intent_route",
        "crisis": "crisis_response",
    })
    graph.add_edge("crisis_response", END)

    graph.add_conditional_edges("intent_route", _route_after_intent, {
        "skill_select": "skill_select",
        "skill_executor": "skill_executor",
        "freeflow": "freeflow_respond",
        "crisis": "crisis_response",
        "low_confidence": "low_confidence_respond",
        "gate": "output_gate",
    })
    graph.add_edge("low_confidence_respond", "output_gate")

    graph.add_conditional_edges("skill_select", _route_after_skill_select, {
        "skill_executor": "skill_executor",
        "knowledge_retrieve": "knowledge_retrieve",
        "freeflow": "freeflow_respond",
    })
    graph.add_edge("knowledge_retrieve", "freeflow_respond")

    graph.add_conditional_edges("skill_executor", _route_after_skill_executor, {
        "crisis": "crisis_response",
        "freeflow": "freeflow_respond",
    })
    graph.add_edge("freeflow_respond", "output_gate")
    graph.add_conditional_edges("output_gate", _route_after_output_gate, {
        "freeflow_respond": "freeflow_respond",
        END: END,
    })

    return graph.compile(checkpointer=checkpointer)
