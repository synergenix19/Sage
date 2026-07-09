"""Per-turn state builder — extracted for testability.
Must not import FastAPI or any module that opens DB connections at import time.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

_log = logging.getLogger(__name__)

# Skill context (active_skill_id/active_step_id) is in-session workflow position.
# It should not survive a multi-hour gap — 4h covers long pauses, resets overnight.
_SKILL_STALE_HOURS = 4


async def _void_unseen_offer(graph, session_id: str) -> None:
    """Best-effort compensating cleanup after an errored offer-creating turn (S1-1b).

    Invariant: user-visible offer ⇔ promotable state. When graph.ainvoke times out
    or errors, the client receives [[SERVER_ERROR]] but the graph's checkpoint may
    have already persisted an offer created on that same turn. The user never saw
    the offer options, so the next turn must not promote it. The discriminator for
    "created this turn" is "skill_offer_made" in the persisted path channel —
    path is per-turn (reset by _build_state), so the checkpoint's path describes
    the turn that just errored. A pending offer from an earlier turn (path without
    the marker) was already seen by the user and is left untouched.

    Never raises: cleanup must not mask the original error response. Failures are
    logged at WARNING and swallowed.
    """
    try:
        checkpointer = getattr(graph, "checkpointer", None)
        if checkpointer is None:
            return
        config = {"configurable": {"thread_id": session_id}}
        snap = await checkpointer.aget(config)
        if not snap:
            return
        values = snap.get("channel_values") or {}
        if values.get("offered_skill_ids") and "skill_offer_made" in (values.get("path") or []):
            await graph.aupdate_state(config, {"offered_skill_ids": None, "offer_count": 0})
            _log.info(
                "[sage/chat] offer voided after errored turn (session %s, offer %s)",
                session_id, values.get("offered_skill_ids"),
            )
    except Exception as exc:
        _log.warning(
            "[sage/chat] offer-void cleanup failed for session %s: %s",
            session_id, exc,
        )


def _stale_skill_overrides(checkpoint_values: dict) -> dict:
    """Return state overrides to park a stale skill on session resume.

    Reads last_turn_at, active_skill_id, and crisis_state from the checkpoint.
    If the gap exceeds _SKILL_STALE_HOURS, returns overrides that:
      - clear active_skill_id / active_step_id (stop silent skill continuation)
      - set stale_skill_id (let the composer inject a re-entry prompt)
      - reset crisis_state to "none" (state machine position, not longitudinal signal)

    The early-return gate allows through any checkpoint where crisis_state is
    "monitoring" or "active", even if active_skill_id is None. This covers the
    canonical CSM-3 gap: _crisis_response_node sets active_skill_id=None, so a
    user who hit crisis and disappeared for 4h+ had their monitoring state survive
    the old early-return guard. The gate ALSO allows through any checkpoint where
    offered_skill_ids is non-null or declined_skills is non-empty, so a 4h+ gap
    clears those session-scoped fields even when no active skill or crisis state
    is present.

    When active_skill_id is None (crisis-only stale session), only crisis_state
    is reset — there is no skill to clear, so active_skill_id / active_step_id /
    stale_skill_id are not included in overrides.

    Clinical flags are intentionally NOT cleared — they are true longitudinal
    signals (v7 §6.3), not in-session workflow position.

    Offer and declined-skills clearing: offered_skill_ids and declined_skills
    follow the skill_matching rules' "declined_scope: session" contract — they
    are scoped to the current session, not the user's longitudinal history. A 4h+
    gap constitutes a session boundary, so any pending offer (offered_skill_ids)
    and the session-scoped decline list (declined_skills) are cleared alongside
    the stale skill. This prevents stale offers from surfacing after a long pause
    and allows re-offer of previously declined skills in a fresh session.
    """
    last_turn_at = checkpoint_values.get("last_turn_at")
    active_skill_id = checkpoint_values.get("active_skill_id")
    crisis_state = checkpoint_values.get("crisis_state", "none")
    is_stale_crisis = crisis_state in ("monitoring", "active")
    offered_pending = bool(checkpoint_values.get("offered_skill_ids"))
    declined_pending = bool(checkpoint_values.get("declined_skills"))
    if not last_turn_at or (
        not active_skill_id and not is_stale_crisis
        and not offered_pending and not declined_pending
    ):
        return {}
    try:
        last = datetime.fromisoformat(last_turn_at)
        gap_hours = (datetime.now(timezone.utc) - last).total_seconds() / 3600
        # crisis_state="monitoring"/"active" is a state machine position, not a longitudinal flag.
        # After a 4h+ gap, silently resuming a monitoring session causes unintended re-enrollment.
        # We reset it to "none" here. clinical_flags are NOT cleared —
        # those are the true longitudinal signals (v7 §6.3).
        if gap_hours >= _SKILL_STALE_HOURS:
            overrides: dict = {"crisis_state": "none"}
            if active_skill_id:
                overrides["active_skill_id"] = None
                overrides["active_step_id"] = None
                overrides["stale_skill_id"] = active_skill_id
            if offered_pending:
                overrides["offered_skill_ids"] = None
                overrides["offer_count"] = 0
            if declined_pending:
                overrides["declined_skills"] = []
            return overrides
    except (ValueError, TypeError):
        pass
    return {}


@dataclass
class _MessageLike:
    role: str
    content: str


@dataclass
class _RequestLike:
    messages: list[_MessageLike]
    session_id: str
    user_id: Optional[str] = None


def _build_state(req: _RequestLike) -> dict:
    """Build the per-turn slice of SageState passed to graph.ainvoke.

    Persistent fields intentionally absent (they come from LangGraph checkpoint):
      conversation_history, crisis_state, active_skill_id, active_step_id,
      clinical_flags, distress_trajectory, engagement_trajectory,
      conversation_summary, turn_count, therapeutic_profile.

    Nodes that accumulate state (safety_check for trajectories, output_gate for
    history) already use read-then-overwrite, so LangGraph's default overwrite
    reducer is correct — no Annotated reducers required.
    """
    current = req.messages[-1]
    return {
        "raw_message":        current.content,
        "detected_language":  "en",       # safety_check_node overwrites
        "message_en":         current.content,
        "is_safe":            True,
        "crisis_flags":       [],
        "third_party_crisis": False,
        "primary_intent":     None,
        "secondary_intent":   None,
        "intent_confidence":  0.0,
        "emotional_intensity": 5,
        "engagement":          7,
        "executed_step_id":   None,
        "step_instruction":   None,
        "rule_fired":         None,
        "escalation_triggered": None,
        "gate_path":          None,
        "response_en":        None,
        "response":           None,
        "path":               [],
        "skill_select_abstained": False,   # per-turn reset (like path) — no cross-turn abstain leak
        "abstain_referral": None,   # #218 per-turn reset (like skill_select_abstained)
        "code_switching":     False,
        "directive_posture":  False,
        "self_reference":     False,
        "s7_result":          None,
        "s7_method":          None,
        "skill_match_method": None,
        "semantic_score":     None,
        "prompt_layers":      [],
        "token_usage":        {},
        "cultural_output_violations": [],
        # Turn-level fields reset each turn (Category B/C signals)
        "new_clinical_flags_turn": [],
        "rule_fired":              None,
        "resistance_score":        None,
        "completed_skill_id":      None,
        "knowledge_source":        "",
        "knowledge_abstain":       False,
        "knowledge_passages":      [],
        "offer_response":          None,
        "offer_choice_skill_id":   None,
        "stall_detected":          None,   # per-turn; set in intent_route
        # Set from request — needed by tools and summary persistence
        "session_id": req.session_id,
        "user_id":    req.user_id,
        "banned_opener_retry_count": 0,
        "banned_opener_correction": None,
        "banned_opener_fallback_used": False,
    }
