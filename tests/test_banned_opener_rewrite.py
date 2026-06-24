"""#58 — opener-rewrite helper (register-preserving fix). New behaviour; the legacy
regen/retry contract in test_output_gate_banned_opener.py is migrated in Tasks 2-3."""
import asyncio
import pytest
from unittest.mock import patch
from sage_poc.nodes import output_gate


@pytest.mark.asyncio
async def test_rewrite_opener_passes_context_and_returns_text():
    captured = {}

    class _Msg:
        content = "You're carrying a lot with these deadlines. The lack of sleep makes it heavier."

    class _FakeClassifier:
        async def ainvoke(self, messages, *a, **k):
            captured["messages"] = messages
            return _Msg()

    with patch.object(output_gate, "get_classifier", lambda: _FakeClassifier()):
        out = await output_gate._rewrite_opener(
            response_en="It sounds like things are hard right now. The lack of sleep makes it heavier.",
            opener="It sounds like",
            user_message_en="deadlines keep piling up and I can't sleep",
        )
    joined = " ".join(m["content"] for m in captured["messages"])
    assert "It sounds like" in joined and "deadlines keep piling up" in joined
    assert out.startswith("You're carrying")
    assert "it sounds like" not in out.lower()


@pytest.mark.asyncio
async def test_rewrite_opener_times_out_to_empty(monkeypatch):
    class _Slow:
        async def ainvoke(self, *a, **k):
            await asyncio.sleep(10)
            return "never"

    monkeypatch.setattr(output_gate, "get_classifier", lambda: _Slow())
    monkeypatch.setattr(output_gate, "_OPENER_REWRITE_TIMEOUT", 0.2)
    out = await output_gate._rewrite_opener(
        "It sounds like things are hard.", "It sounds like", "msg"
    )
    assert out == ""


@pytest.mark.asyncio
async def test_rewrite_opener_empty_input_returns_empty():
    assert await output_gate._rewrite_opener("", "It sounds like", "msg") == ""


# ---- defense-in-depth: the rewrite must never touch scripted/crisis copy --------------
from unittest.mock import AsyncMock, MagicMock


def _base_state(**overrides) -> dict:
    base = {
        "raw_message": "I am exhausted by everything",
        "message_en": "I am exhausted by everything",
        "detected_language": "en",
        "response_en": "It sounds like you're really overwhelmed. What's been hardest?",
        "gate_path": None, "primary_intent": "general_chat", "secondary_intent": None,
        "emotional_intensity": 8, "engagement": 4, "active_skill_id": None,
        "executed_step_id": None, "step_instruction": None, "rule_fired": None,
        "escalation_triggered": None, "clinical_flags": [], "crisis_flags": [],
        "crisis_state": "none", "third_party_crisis": False, "code_switching": False,
        "s7_result": None, "conversation_history": [], "conversation_summary": None,
        "therapeutic_profile": None, "knowledge_passages": [], "knowledge_abstain": False,
        "stale_skill_id": None, "cultural_output_violations": [],
        "path": ["safety_check", "intent_route", "freeflow_respond"],
        "turn_count": 1, "turn_number": 1, "session_id": None, "user_id": None,
        "knowledge_source": "", "identity_substitution_rule_id": None,
        "original_response_hash": None, "original_response_text": None,
        "prompt_layers": ["persona", "intent"], "token_usage": {}, "resistance_score": None,
        "resistance_history": [], "semantic_score": None, "skill_match_method": None,
        "new_clinical_flags_turn": [], "active_step_id": None, "prev_step_id": None,
        "re_escalation_within_monitoring": None, "engagement_trajectory": [],
        "distress_trajectory": [], "banned_opener_retry_count": 0,
    }
    base.update(overrides)
    return base


async def _run_gate(monkeypatch, response_en, gate_path=None, crisis_flags=None):
    calls = []

    async def _spy_rewrite(response_en, opener, user_message_en):
        calls.append(opener)
        return "REWRITTEN should-not-be-used"

    monkeypatch.setattr(output_gate, "_rewrite_opener", _spy_rewrite)
    monkeypatch.setattr(output_gate.rules_engine, "evaluate", lambda *a, **k: MagicMock(fired=[]))
    monkeypatch.setattr(output_gate, "async_translate_to_arabic", AsyncMock(return_value="..."))
    monkeypatch.setattr(output_gate, "write_session_audit", AsyncMock())
    state = _base_state(response_en=response_en, gate_path=gate_path)
    if crisis_flags is not None:
        state["crisis_flags"] = crisis_flags
    res = await output_gate.output_gate_node(state)
    res["_rewrite_calls"] = calls
    return res


@pytest.mark.asyncio
async def test_scripted_safety_paths_are_never_rewritten(monkeypatch):
    """scope_refusal / jailbreak copy must never reach the opener rewriter (allowlist)."""
    for gp in ("scope_refusal", "jailbreak"):
        res = await _run_gate(monkeypatch,
            response_en="It sounds like you want a diagnosis, which I can't give.", gate_path=gp)
        assert res["_rewrite_calls"] == []
        assert "output_gate_opener_rewritten" not in res.get("path", [])


@pytest.mark.asyncio
async def test_crisis_state_is_never_rewritten(monkeypatch):
    """Highest-stakes: a crisis-flagged turn (even at gate_path=None) never reaches the rewriter.
    Defense-in-depth — does not rely on the upstream routing invariant alone."""
    res = await _run_gate(monkeypatch,
        response_en="It sounds like you're in real danger right now. Please call 999.",
        gate_path=None, crisis_flags=["si_explicit"])
    assert res["_rewrite_calls"] == []
    assert "output_gate_opener_rewritten" not in res.get("path", [])


# ---- #58 x #60 recompose: the rewrite and #60's question-discipline / directive_posture ---------
# logic edit the SAME node and have never run together. These prove the merge is semantically clean.

def _mock_node(monkeypatch):
    monkeypatch.setattr(output_gate.rules_engine, "evaluate", lambda *a, **k: MagicMock(fired=[]))
    monkeypatch.setattr(output_gate, "async_translate_to_arabic", AsyncMock(return_value="..."))
    monkeypatch.setattr(output_gate, "write_session_audit", AsyncMock())


@pytest.mark.asyncio
async def test_rewrite_composes_with_question_discipline(monkeypatch):
    """Rewrite runs BEFORE question-discipline, so a rewritten opener that still leaves two questions
    is limited to one by #60's discipline (discipline sees the rewrite, not the pre-rewrite text)."""
    async def _fake_rewrite(response_en, opener, user_message_en):
        return "You're carrying a lot right now. What's been hardest? How are you sleeping?"
    monkeypatch.setattr(output_gate, "_rewrite_opener", _fake_rewrite)
    _mock_node(monkeypatch)

    state = _base_state(
        response_en="It sounds like you're overwhelmed. What's been hardest? How are you sleeping?")
    res = await output_gate.output_gate_node(state)
    resp = res["response"]

    assert "output_gate_opener_rewritten" in res.get("path", [])
    assert not output_gate._BANNED_OPENER_RE.match(resp.lstrip())     # opener fixed
    assert resp.count("?") == 1, f"discipline must cap the rewritten reply at one question: {resp!r}"
    assert "question_discipline_applied" in res.get("path", [])


@pytest.mark.asyncio
async def test_passthrough_flows_through_directive_posture(monkeypatch):
    """When the rewrite fails and the original passes through, that original still flows through #60's
    directive_posture trailing-question strip — the pass-through path is NOT short-circuited."""
    async def _fail_rewrite(response_en, opener, user_message_en):
        return ""  # pass-through
    monkeypatch.setattr(output_gate, "_rewrite_opener", _fail_rewrite)
    _mock_node(monkeypatch)

    state = _base_state(
        response_en="It sounds like you want steps. Try box breathing tonight. Does that help?",
        directive_posture=True, offered_skill_ids=None)
    res = await output_gate.output_gate_node(state)
    resp = res["response"]

    assert "output_gate_opener_passthrough" in res.get("path", [])
    assert "Does that help?" not in resp, "directive_posture must strip the trailing question on pass-through"
    assert "question_discipline_applied" in res.get("path", [])
