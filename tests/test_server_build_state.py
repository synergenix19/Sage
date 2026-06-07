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


def test_SF5_completed_skill_id_resets_per_turn():
    """SF-5: completed_skill_id must be present in _build_state() output and reset to
    None on every turn.

    Bleed scenario: skill completes on turn N (executor sets completed_skill_id=skill_id),
    turn N+1 is a freeflow turn that never enters the executor. Without this reset,
    LangGraph's checkpoint preserves the turn-N value and the turn-N+1 audit row gets
    stamped with a skill that was not active — a false attribution in the clinical trail.

    This test verifies that _build_state()'s None is present as the ainvoke input for
    every turn, which overrides the checkpoint value (overwrite reducer). The executor
    can then set it only on the turns where skill_complete=True.
    """
    req = _Req([_Msg("user", "hello")])
    state = _build_state(req)

    assert "completed_skill_id" in state, (
        "completed_skill_id must be in _build_state() output — "
        "its absence means the checkpoint value is never cleared on freeflow turns"
    )
    assert state["completed_skill_id"] is None, (
        "completed_skill_id must reset to None each turn via _build_state()"
    )


def test_M4_knowledge_fields_reset_each_turn():
    """M4 fix: knowledge_abstain, knowledge_passages, and knowledge_source must reset
    each turn so that an info_request turn's retrieval state does not bleed into the
    next turn's prompt composition (e.g. skill_continuation).
    """
    req = _Req([_Msg("user", "what is CBT?")])
    state = _build_state(req)

    assert state.get("knowledge_abstain") is False, (
        "knowledge_abstain must reset to False so stale abstain block is not injected"
    )
    assert state.get("knowledge_passages") == [], (
        "knowledge_passages must reset to [] so prior-turn passages are not reused"
    )
    assert state.get("knowledge_source") == "", (
        "knowledge_source must reset to '' so audit log shows correct source"
    )
