from sage_poc.nodes.venting_detect import detect_venting
from sage_poc.graph import _route_after_intent
from sage_poc import config as _cfg


def test_dontfix_signals_detected():
    for m in ("please just listen, I can't handle this anymore",
              "I'm so overwhelmed I just need to get this out, don't try to fix it",
              "I just need to vent", "I don't want advice, just talk"):
        assert detect_venting(m, m, "en") is True, m


def test_non_venting_distress_not_detected():
    # Acute distress WITHOUT a don't-fix signal must NOT be suppressed — the user may want help.
    for m in ("I'm panicking, help me calm down", "my heart is racing, what do I do"):
        assert detect_venting(m, m, "en") is False, m


def _route(**st):
    base = {
        "primary_intent": "general_chat", "emotional_intensity": 8, "intent_confidence": 0.9,
        "crisis_state": "none", "active_skill_id": None, "venting_detected": False,
        "gate_path": None, "offer_response": None, "prepass_matched": [],
    }
    return _route_after_intent({**base, **st})


def test_venting_suppresses_sf2_to_freeflow(monkeypatch):
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", True)
    assert _route(venting_detected=True, emotional_intensity=8) == "freeflow"


def test_non_venting_high_intensity_still_reaches_skill_select(monkeypatch):
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", True)
    assert _route(venting_detected=False, emotional_intensity=8) == "skill_select"


def test_flag_off_venting_unchanged(monkeypatch):
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", False)
    assert _route(venting_detected=True, emotional_intensity=8) == "skill_select"


def test_crisis_still_wins_over_venting(monkeypatch):
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", True)
    assert _route(primary_intent="crisis", venting_detected=True) == "crisis"


def test_new_skill_venting_still_reaches_skill_select(monkeypatch):
    # Over-suppression guard: an explicit skill/help request must NOT be suppressed even if a
    # don't-fix keyword is present. Only general_chat venting is suppressed. (Uses the file's
    # existing _route(...) helper.)
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", True)
    assert _route(primary_intent="new_skill", venting_detected=True, emotional_intensity=8) == "skill_select"
