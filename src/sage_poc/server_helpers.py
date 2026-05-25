"""Per-turn state builder — extracted for testability.
Must not import FastAPI or any module that opens DB connections at import time.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


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
        # Set from request — needed by tools and summary persistence
        "session_id": req.session_id,
        "user_id":    req.user_id,
    }
