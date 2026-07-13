from sage_poc.safety.medical_redflag import detect_medical_redflag
from sage_poc.graph import _route_after_safety
from sage_poc import config as _cfg
import typing
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
