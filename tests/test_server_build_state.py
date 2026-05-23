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

def test_build_state_excludes_conversation_history():
    req = _Req([_Msg("user", "hello")])
    state = _build_state(req)
    assert "conversation_history" not in state

def test_build_state_excludes_active_skill_id():
    req = _Req([_Msg("user", "hi")])
    state = _build_state(req)
    assert "active_skill_id" not in state

def test_build_state_excludes_crisis_state():
    req = _Req([_Msg("user", "hi")])
    state = _build_state(req)
    assert "crisis_state" not in state

def test_build_state_includes_per_turn_resets():
    req = _Req([_Msg("user", "hello")], session_id="test-1", user_id="u-1")
    state = _build_state(req)
    assert state["raw_message"] == "hello"
    assert state["path"] == []
    assert state["is_safe"] is True
    assert state["session_id"] == "test-1"
    assert state["user_id"] == "u-1"
