"""H4 structure — CRISIS_RESOURCES + select_crisis_resources lead-logic (BOT BEHAVIOUR L2146).

Value-preserving: CRISIS_CONFIG stays byte-identical (derived from the primary/emergency entries),
so the ~7 consumers + byte-identical/conformance tests are unchanged. The lead-logic + hours-
awareness is exercised against INJECTED doc-like data (national 8am-8pm + a 24/7 alternative), so
the out-of-hours branch is tested WITHOUT changing the live, clinician-gated composition.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from sage_poc.config import CRISIS_CONFIG, CRISIS_RESOURCES, select_crisis_resources

_DUBAI = ZoneInfo("Asia/Dubai")
_DOC_LIKE = [
    {"name": "Emergency", "number": "999", "hours": "24/7", "scope": "emergency"},
    {"name": "National Mental Support Line", "number": "800-4673", "hours": "8am-8pm", "scope": "national"},
    {"name": "SAKINA", "number": "800-725462", "hours": "24/7", "scope": "regional"},
]


def test_immediate_danger_leads_with_emergency():
    out = select_crisis_resources(_DOC_LIKE, immediate_danger=True,
                                  now=datetime(2026, 7, 10, 14, 0, tzinfo=_DUBAI))
    assert out[0]["scope"] == "emergency"


def test_in_hours_leads_with_national():
    out = select_crisis_resources(_DOC_LIKE, now=datetime(2026, 7, 10, 14, 0, tzinfo=_DUBAI))  # 2pm
    assert out[0]["scope"] == "national"


def test_out_of_hours_leads_with_24_7_not_closed_national():
    out = select_crisis_resources(_DOC_LIKE, now=datetime(2026, 7, 10, 2, 0, tzinfo=_DUBAI))  # 2am
    assert out[0]["scope"] != "national", "must not lead with the closed 8am-8pm national line at 2am"
    assert "24/7" in out[0]["hours"], "out-of-hours lead must be a 24/7 line"


def test_always_includes_a_24_7_option():
    for hour in (2, 14):
        out = select_crisis_resources(_DOC_LIKE, now=datetime(2026, 7, 10, hour, 0, tzinfo=_DUBAI))
        assert any("24/7" in r["hours"] for r in out), f"no 24/7 option present at hour {hour}"


def test_crisis_config_shim_is_value_preserving():
    # The refactor must NOT change live values (GL-1 verified-final set); composition is gated.
    assert CRISIS_CONFIG == {
        "number": "800 46342", "label": "MoHAP Counselling Line", "hours": "24/7", "emergency": "999",
    }
    assert {r["scope"] for r in CRISIS_RESOURCES} == {"national", "emergency"}
