from sage_poc.server_helpers import _build_state

class _Msg:
    def __init__(self, role, content):
        self.role = role
        self.content = content

class _Req:
    def __init__(self, msgs, session_id="s1", user_id=None):
        self.messages = msgs
        self.session_id = session_id
        self.user_id = user_id

_CHECKPOINT_FIELDS = [
    "conversation_history",
    "active_skill_id",
    "active_step_id",
    "crisis_state",
    "turn_count",
    "clinical_flags",
    "distress_trajectory",
    "engagement_trajectory",
    "conversation_summary",
]


def test_build_state_excludes_all_checkpoint_fields():
    """_build_state must never inject checkpoint-managed fields.

    In LangGraph, any key present in the input dict overwrites the
    checkpoint value for that channel (overwrite reducer). Injecting
    defaults here would clobber turn_count, conversation_history, etc.
    on every turn, erasing cross-turn memory.
    """
    req = _Req([_Msg("user", "hello")])
    state = _build_state(req)
    for field in _CHECKPOINT_FIELDS:
        assert field not in state, (
            f"_build_state must NOT include '{field}' — "
            "it is managed by the LangGraph checkpoint"
        )

def test_build_state_includes_per_turn_resets():
    req = _Req([_Msg("user", "hello")], session_id="test-1", user_id="u-1")
    state = _build_state(req)
    assert state["raw_message"] == "hello"
    assert state["path"] == []
    assert state["is_safe"] is True
    assert state["session_id"] == "test-1"
    assert state["user_id"] == "u-1"


def test_T9_new_clinical_flags_turn_and_resistance_score_reset_each_turn():
    """T9: Turn-level Category C signals must be reset to a neutral value by
    _build_state() so they cannot bleed across turns via the LangGraph checkpoint.

    new_clinical_flags_turn must be [] (not inherited from prior turn).
    resistance_score must be None (recomputed per turn by skill_executor).
    """
    req = _Req([_Msg("user", "hello")])
    state = _build_state(req)

    assert "new_clinical_flags_turn" in state, (
        "new_clinical_flags_turn must be present in _build_state() output"
    )
    assert state["new_clinical_flags_turn"] == [], (
        "new_clinical_flags_turn must reset to [] each turn"
    )

    assert "resistance_score" in state, (
        "resistance_score must be present in _build_state() output"
    )
    assert state["resistance_score"] is None, (
        "resistance_score must reset to None each turn — it is computed by skill_executor"
    )
