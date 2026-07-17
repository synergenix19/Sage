"""D1 wiring (#338) — the injection decision, where subtle-wrongness hides while isolated tests stay green.

Pinned design (V + build notes 2026-07-17):
 (1) SESSION-PERSISTENT screen state. The screen fires when routing = a contraindicated-flagged skill
     (TIPP) AND no valid screen answer exists THIS SESSION. State is per-SESSION (persists across turns,
     not per-turn): answered-no once → never re-screened this session; answered-yes → never re-offered TIPP.
 (2) CRISIS SUPREMACY. A screen turn is still a turn — crisis content in the answer wins over the branch
     table; the classifier never files it. Defense-in-depth even though safety_check precedes skill_select.
 (3) AUDIT alert-or-fail (#160). A swallowed screen_asked write is a contraindication decision with no
     record — the PDPL exposure the D-item closes. Induced-failure must fail LOUD.
"""
import pytest
from sage_poc.safety import medical_screen as ms

CONTRA = "dbt_tipp"  # contraindicated-flagged acute skill


def _st(**kw):
    base = {"session_screen_answer": None, "screen_pending": False, "is_safe": True,
            "crisis_flags": [], "raw_message": ""}
    base.update(kw); return base


# ── (1) fresh routing to a contraindicated skill ──
def test_first_tipp_no_prior_answer_asks_screen():
    d = ms.decide_screen(CONTRA, _st())
    assert d["action"] == "ask_screen"

def test_reentry_after_clear_no_proceeds_without_reasking():
    d = ms.decide_screen(CONTRA, _st(session_screen_answer="clear_no"))
    assert d["action"] == "proceed" and d.get("re_asked") is not True

def test_reentry_after_yes_reroutes_grounding_without_reasking():
    d = ms.decide_screen(CONTRA, _st(session_screen_answer="yes"))
    assert d["action"] == "reroute_grounding" and d.get("re_asked") is not True

def test_reentry_after_redflag_never_reoffers_tipp():
    d = ms.decide_screen(CONTRA, _st(session_screen_answer="red_flag"))
    assert d["action"] in ("reroute_grounding", "to_medical_guard")

def test_non_contraindicated_skill_never_screens():
    d = ms.decide_screen("grounding_5_4_3_2_1", _st())
    assert d["action"] == "proceed"


# ── answering a pending screen ──
@pytest.mark.parametrize("answer,action,cls", [
    ("no, same as always", "proceed", "clear_no"),
    ("yeah it's spreading to my arm", "to_medical_guard", "red_flag"),
    ("kind of, maybe", "reroute_grounding", "yes"),
    ("it's kind of both", "reroute_grounding", "unclear"),
    ("anyway my week's been rough", "reroute_grounding", "no_answer"),
])
def test_answer_turn_routes_and_stores(answer, action, cls):
    d = ms.decide_screen(CONTRA, _st(screen_pending=True, raw_message=answer))
    assert d["action"] == action
    assert d["session_screen_answer"] == cls          # stored for the session
    assert d["audit"]["screen_answer_class"] == cls
    assert d["audit"]["screen_branch_taken"] == {"proceed": "proceed", "to_medical_guard": "medical_guard",
                                                 "reroute_grounding": "grounding"}[action]


# ── (2) crisis supremacy: crisis content in a screen answer abandons the screen ──
def test_crisis_in_screen_answer_abandons_screen():
    d = ms.decide_screen(CONTRA, _st(screen_pending=True, is_safe=False, crisis_flags=["si"],
                                     raw_message="does it matter? i don't want to be here anymore"))
    assert d["action"] == "abandon_crisis"
    assert d["audit"]["screen_branch_taken"] == "abandoned_crisis"   # abandonment recorded, not filed as unclear


# ── (3) audit alert-or-fail (#160): a swallowed screen_asked write must fail loud ──
def test_audit_write_failure_is_loud():
    def _broken_writer(row):  # simulates a swallowed/failed write
        raise RuntimeError("db down")
    with pytest.raises(ms.ScreenAuditError):
        ms.write_screen_audit({"screen_asked": True, "screen_answer_class": "red_flag",
                               "screen_branch_taken": "medical_guard"}, writer=_broken_writer)
