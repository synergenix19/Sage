from sage_poc.safety.medical_redflag import detect_medical_redflag
from sage_poc.graph import _route_after_safety
from sage_poc import config as _cfg
import typing
import os
import pytest

def test_state_declares_medical_channel():
    from sage_poc.state import SageState
    hints = typing.get_type_hints(SageState)
    assert "medical_flags" in hints, "medical_flags must be a declared channel (LangGraph drops undeclared keys)"

def test_gate_path_allows_medical():
    from sage_poc.state import SageState
    hints = typing.get_type_hints(SageState)
    assert "medical" in str(hints["gate_path"])

# The VERBATIM escalation trace. Do not adjust this string to fit the phrase list.
LIVE_TRACE = "crushing pain in my chest spreading to my jaw, my left arm's gone numb"
# The same presentation with the one clause that trivially matched removed. A textbook
# cardiac presentation phrased the way people actually phrase it — MUST still fire.
JAWLESS_VARIANT = "crushing pain in my chest, my left arm's gone numb"

def test_live_trace_fires():
    assert detect_medical_redflag(LIVE_TRACE) != []

def test_jawless_variant_fires():
    # If this fails, the phrase list is wrong — extend it (word-order/proximity
    # variants), never narrow this test.
    assert detect_medical_redflag(JAWLESS_VARIANT) != []

def test_crushing_variant_isolated_forces_word_order_entry():
    # No numbness/jaw clause — only the word-order variant can match. If crushing_variant
    # is deleted or broken, this fails (the other entries cannot cover it).
    ids = detect_medical_redflag("I have crushing pain in my chest")
    assert "crushing_variant" in ids, ids
    # And the verbatim §1 literal (different word order) still matches its own entry:
    assert "crushing" in detect_medical_redflag("this is crushing chest pain")

def test_must_not_fire_controls_stay_clear():
    # Panic negatives AND benign-numbness negatives. Benign limb-numbness (no
    # laterality) must NOT route to a medical emergency — §1's criterion is one-sided.
    for benign in ("racing heart", "tight chest", "shallow breath",
                   "my chest feels a little tight", "my heart is racing from the panic",
                   "my foot's gone numb from sitting",
                   "my hand went numb from sleeping on it",
                   "my leg's gone numb from sitting cross-legged"):
        assert detect_medical_redflag(benign) == [], benign


def _state(msg: str) -> dict:
    return {"raw_message": msg, "message_en": msg, "detected_language": "en",
            "path": [], "crisis_flags": [], "clinical_flags": [], "crisis_state": "none"}


@pytest.mark.asyncio
async def test_safety_check_sets_medical_flags_on_cardiac():
    from sage_poc.nodes.safety_check import safety_check_node
    out = await safety_check_node(_state("crushing chest pain spreading to my jaw"))
    assert out["medical_flags"], "cardiac red-flag must populate medical_flags"


@pytest.mark.asyncio
async def test_safety_check_no_medical_flag_on_benign():
    from sage_poc.nodes.safety_check import safety_check_node
    out = await safety_check_node(_state("my heart is racing from the panic"))
    assert out["medical_flags"] == []


@pytest.mark.asyncio
async def test_medical_response_returns_referral_and_gate_path():
    from sage_poc.nodes.medical_response import medical_response_node
    out = await medical_response_node(_state("x") | {"medical_flags": ["crushing"]})
    assert out["gate_path"] == "medical"
    assert out["response"] and "medical" in out["response"].lower()


@pytest.mark.asyncio
async def test_medical_response_writes_its_own_audit(monkeypatch):
    # Defect 3: this path bypasses output_gate, so it MUST write its own audit.
    import asyncio
    import sage_poc.nodes.medical_response as mr
    captured = {}
    async def _fake_audit(rec): captured.update(rec)
    monkeypatch.setattr(mr, "write_session_audit", _fake_audit)
    await mr.medical_response_node(_state("x") | {"medical_flags": ["crushing"]})
    await asyncio.sleep(0)  # let the fire-and-forget audit task run
    assert captured.get("gate_path") == "medical"
    assert captured.get("medical_flags") == ["crushing"]
    assert "latency_ms" in captured and "path" in captured


def _routed(**st) -> str:
    base = {"is_safe": True, "crisis_state": "none", "medical_flags": [], "crisis_tier": None}
    return _route_after_safety(base | st)


def test_cardiac_routes_medical_when_enabled(monkeypatch):
    monkeypatch.setattr(_cfg, "MEDICAL_REDFLAG_GUARD_ENABLED", True)
    assert _routed(is_safe=True, medical_flags=["crushing"]) == "medical"


def test_crisis_wins_over_medical(monkeypatch):
    monkeypatch.setattr(_cfg, "MEDICAL_REDFLAG_GUARD_ENABLED", True)
    # SI + cardiac in the same turn: crisis takes precedence, never medical.
    assert _routed(is_safe=False, medical_flags=["crushing"]) == "crisis"


def test_medical_route_off_by_default(monkeypatch):
    monkeypatch.setattr(_cfg, "MEDICAL_REDFLAG_GUARD_ENABLED", False)
    assert _routed(is_safe=True, medical_flags=["crushing"]) == "safe"


def test_benign_stays_safe(monkeypatch):
    monkeypatch.setattr(_cfg, "MEDICAL_REDFLAG_GUARD_ENABLED", True)
    assert _routed(is_safe=True, medical_flags=[]) == "safe"


# --- Task 6: end-to-end red->green trace + flip-control gate + honesty record ---

@pytest.mark.parametrize("trace,tid", [
    ("crushing pain in my chest spreading to my jaw, my left arm's gone numb", "b1-e2e-full"),
    ("crushing pain in my chest, my left arm's gone numb", "b1-e2e-jawless"),  # jaw clause removed
])
@pytest.mark.asyncio
async def test_end_to_end_cardiac_no_longer_reaches_a_skill(monkeypatch, trace, tid):
    # Cardiac input short-circuits at safety_check -> _route_after_safety -> "medical"
    # -> medical_response -> END. It never reaches intent_route (the only LLM step),
    # so this drives the real compiled graph without needing OPENROUTER_API_KEY.
    monkeypatch.setattr(_cfg, "MEDICAL_REDFLAG_GUARD_ENABLED", True)
    from sage_poc.graph import build_graph
    app = build_graph()
    result = await app.ainvoke(
        {"raw_message": trace, "path": []},
        config={"configurable": {"thread_id": tid}},
    )
    assert result.get("gate_path") == "medical"
    assert "medical_response" in result.get("path", [])
    assert result.get("active_skill_id") is None  # never absorbed into box_breathing/grounding


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="benign path reaches intent_route (LLM); needs OPENROUTER_API_KEY",
)
@pytest.mark.asyncio
async def test_flip_control_benign_panic_stays_on_support_path(monkeypatch):
    monkeypatch.setattr(_cfg, "MEDICAL_REDFLAG_GUARD_ENABLED", True)
    from sage_poc.graph import build_graph
    app = build_graph()
    result = await app.ainvoke(
        {"raw_message": "my heart is racing from the panic", "path": []},
        config={"configurable": {"thread_id": "b1-benign"}},
    )
    assert result.get("gate_path") != "medical"
    assert "medical_response" not in result.get("path", [])


@pytest.mark.asyncio
async def test_medical_response_clears_active_skill():
    # A user mid-skill who reports chest pain must not have the skill resume next turn.
    from sage_poc.nodes.medical_response import medical_response_node
    out = await medical_response_node(_state("crushing chest pain") | {
        "medical_flags": ["crushing"], "active_skill_id": "box_breathing",
        "active_step_id": "inhale_hold", "offered_skill_ids": ["box_breathing"],
    })
    assert out["active_skill_id"] is None
    assert out["active_step_id"] is None
    assert out["offered_skill_ids"] is None


def test_honesty_notes_ship_verbatim():
    import json
    from pathlib import Path
    import sage_poc.safety.medical_redflag as mr
    meta = json.loads(Path(mr._PHRASES_PATH).read_text())["_meta"]
    assert "Not coverage" in meta["status"]
    assert "ZERO native Arabic" in meta["arabic"]
    assert "Arabic" in mr.__doc__ and "ZERO native coverage" in mr.__doc__


def test_medical_referral_uses_998_not_999_lead():
    # UAE reality: 998 = ambulance, 999 = police. A medical/cardiac emergency MUST lead with
    # 998. Regression guard: the pre-fix default led with "999 in the UAE" — routing a heart
    # attack to the police. 999 may appear only as an explicit non-leading fallback.
    from sage_poc import config as _cfg
    txt = _cfg.MEDICAL_REFERRAL_TEXT
    assert "998" in txt, "medical referral must give the UAE ambulance number (998)"
    if "999" in txt:
        assert txt.index("998") < txt.index("999"), "998 (ambulance) must lead 999 in the medical terminal"


# --- Gate 4: audit-columns flip blocker ---
# medical_response already calls write_session_audit({**state, "gate_path":"medical",
# "medical_flags":[...], ...}), but _build_session_audit_row had no gate_path/medical_flags
# columns, so those fields were written-then-dropped before ever reaching the row that gets
# persisted. These tests pin the row builder directly (not write_session_audit's input state),
# mirroring the crisis_tier / precedence conditional-inclusion convention: the columns are
# included ONLY when a medical turn fired, so a flag-OFF / non-medical row stays
# byte-identical to master (Check B).

def _audit_state(**kwargs) -> dict:
    defaults = {
        "session_id": "test-session-b1-gate4",
        "turn_number": 1,
        "path": ["safety_check", "medical_response", "output_gate"],
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "intent_confidence": 0.9,
        "active_skill_id": None,
        "active_step_id": None,
        "skill_match_method": None,
        "knowledge_passages": [],
        "knowledge_abstain": False,
        "knowledge_source": "",
        "crisis_state": "none",
        "crisis_flags": [],
        "clinical_flags": [],
        "engagement": 7,
        "emotional_intensity": 4,
        "model_version": "claude-sonnet-4-6",
        "latency_ms": None,
        "user_id": None,
    }
    return {**defaults, **kwargs}


def test_build_session_audit_row_records_medical_flags_and_gate_path():
    from sage_poc.audit import _build_session_audit_row
    state = _audit_state(medical_flags=["crushing"], gate_path="medical")

    row = _build_session_audit_row(state)

    assert row["gate_path"] == "medical"
    assert row["medical_flags"] == ["crushing"]


def test_build_session_audit_row_omits_medical_columns_when_not_medical():
    from sage_poc.audit import _build_session_audit_row
    state = _audit_state()  # no medical_flags, no gate_path -> non-medical turn

    row = _build_session_audit_row(state)

    assert "gate_path" not in row
    assert "medical_flags" not in row
