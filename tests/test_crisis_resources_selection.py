"""H4 — CRISIS_RESOURCES + select_crisis_resources lead-logic (BOT BEHAVIOUR L2146).

The doc's verified 6-entry directory is now LIVE (all gates cleared 2026-07-10). CRISIS_CONFIG is
DERIVED from the primary national + emergency entries. The lead-logic + hours-awareness is exercised
both against INJECTED doc-like data (below) and, in the safety property test, against the LIVE
CRISIS_RESOURCES across all 24 hours ("no stranded 02:00 user").
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


def test_crisis_config_shim_reflects_adopted_composition():
    # H4 value adoption (all gates cleared 2026-07-10): CRISIS_CONFIG is DERIVED from the doc's
    # verified 6-entry directory. The primary national line leads the derived single-number shim;
    # the emergency number is 999. If any value changes, change CRISIS_RESOURCES (the one source).
    assert CRISIS_CONFIG == {
        "number": "800-HOPE (800-4673)",
        "label": "National Mental Support Line",
        "hours": "8am–8pm daily",
        "emergency": "999",
    }
    # The full dial-test-confirmed directory: national + emergency + regional (SAKINA, DHA) + youth.
    assert {r["scope"] for r in CRISIS_RESOURCES} == {"national", "emergency", "regional", "youth"}
    assert len(CRISIS_RESOURCES) == 6
    numbers = [r["number"] for r in CRISIS_RESOURCES]
    assert "800-SAKINA (800-725462)" in numbers  # Abu Dhabi 24/7
    assert "800 111" in numbers                   # DHA 24/7
    assert "800 51115" in numbers                 # Sharjah youth


def test_a_dialable_24_7_line_is_always_in_the_top_set_every_hour():
    """SAFETY PROPERTY — "no stranded 02:00 user".

    The primary national line is 8am-8pm; adopting it as the derived single number means the card
    must NEVER present a top set whose only options are closed lines. For EVERY hour of the day
    (Asia/Dubai) AND both immediate-danger states, the top set (first 3) served from the LIVE
    CRISIS_RESOURCES must contain at least one dialable 24/7 resource (999 is always 24/7; SAKINA
    800-725462 and DHA 800 111 are 24/7). Property-style over all 24 hours, not spot checks.
    """
    for hour in range(24):
        now = datetime(2026, 7, 13, hour, 0, tzinfo=_DUBAI)
        for immediate_danger in (True, False):
            out = select_crisis_resources(immediate_danger=immediate_danger, now=now)
            top = out[:3]
            has_24_7 = [r for r in top if "24/7" in r.get("hours", "") and r.get("number")]
            assert has_24_7, (
                f"hour={hour} immediate_danger={immediate_danger}: top set {[r['number'] for r in top]} "
                "has no dialable 24/7 line — a user in crisis at this hour could be stranded with only "
                "a closed helpline."
            )
