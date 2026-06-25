"""The sentinel injection lives in freeflow's empty-prior-context branch. Assert via prompt_layers
with a stubbed LLM (no network): fires on absent recall, not on present-history."""
import pytest
from sage_poc.nodes import freeflow_respond as ff


class _Stub:
    def bind_tools(self, tools): return self
    async def ainvoke(self, messages):
        class _M:
            content = "ok"
            tool_calls = None
        return _M()


def _state(hist):
    return {"self_reference": True, "message_en": "what did I just tell you about my husband?",
            "raw_message": "...", "detected_language": "en", "conversation_history": hist,
            "user_id": None, "session_id": None, "primary_intent": "general_chat", "active_skill_id": None,
            "emotional_intensity": 5, "engagement": 5, "clinical_flags": [], "crisis_state": "none", "path": [],
            "directive_posture": False, "stall_detected": False, "declined_skills": [],
            "conversation_summary": None, "knowledge_passages": [], "knowledge_abstain": False}


@pytest.mark.asyncio
async def test_sentinel_layer_on_absent_recall():
    out = await ff.freeflow_respond_node(_state([]), llm=_Stub())
    assert "memory_absent_sentinel" in out["prompt_layers"]


@pytest.mark.asyncio
async def test_no_sentinel_layer_when_disclosure_present():
    out = await ff.freeflow_respond_node(_state(
        [{"role": "user", "content": "things at home with my husband have gotten scary"},
         {"role": "assistant", "content": "thanks"}]), llm=_Stub())
    assert "memory_absent_sentinel" not in out["prompt_layers"]
