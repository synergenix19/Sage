"""Per-turn state builder — extracted for testability.
Must not import FastAPI or any module that opens DB connections at import time.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

# Skill context (active_skill_id/active_step_id) is in-session workflow position.
# It should not survive a multi-hour gap — 4h covers long pauses, resets overnight.
_SKILL_STALE_HOURS = 4


def _stale_skill_overrides(checkpoint_values: dict) -> dict:
    """Return state overrides to park a stale skill on session resume.

    Reads last_turn_at and active_skill_id from the checkpoint snapshot.
    If the gap exceeds _SKILL_STALE_HOURS, returns overrides that:
      - clear active_skill_id / active_step_id (stop silent skill continuation)
      - set stale_skill_id (let the composer inject a re-entry prompt)

    Clinical flags are intentionally NOT cleared — they are true longitudinal
    signals (v7 §6.3), not in-session workflow position.

    crisis_state IS cleared: it is a state machine position, not a longitudinal
    flag. After a 4h+ gap, preserving crisis_state='monitoring' causes silent
    re-enrollment into post_crisis_check_in on session resume (CSM-3).
    """
    last_turn_at = checkpoint_values.get("last_turn_at")
    active_skill_id = checkpoint_values.get("active_skill_id")
    if not last_turn_at or not active_skill_id:
        return {}
    try:
        last = datetime.fromisoformat(last_turn_at)
        gap_hours = (datetime.now(timezone.utc) - last).total_seconds() / 3600
        # crisis_state="monitoring" is a state machine position, not a longitudinal flag.
        # After a 4h+ gap, silently resuming a monitoring session causes unintended re-enrollment.
        # We reset it to "none" here alongside the skill clear. clinical_flags are NOT cleared —
        # those are the true longitudinal signals (v7 §6.3).
        if gap_hours >= _SKILL_STALE_HOURS:
            return {
                "active_skill_id":  None,
                "active_step_id":   None,
                "stale_skill_id":   active_skill_id,
                "crisis_state":     "none",
            }
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
        "code_switching":     False,
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
        "knowledge_source":        "",
        "knowledge_abstain":       False,
        "knowledge_passages":      [],
        # Set from request — needed by tools and summary persistence
        "session_id": req.session_id,
        "user_id":    req.user_id,
    }
