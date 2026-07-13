"""Availability-consistency guard — no crisis-copy string may assert 24/7 / "24 hours" /
"متاح كل وقت" adjacent to the NATIONAL line number.

Root cause this guards (H4): the National Mental Support Line (800-HOPE / 800-4673) is 8am-8pm
daily, NOT 24/7. Before this fix, four crisis-copy sites carried a false "available 24 hours a day"
/ AR "متاح كل وقت" / "24 ساعة" claim right next to that number (psychotic_referral examples,
clinical_flag_adaptations, plus the "MoHAP 24/7" framing). Presenting the 8am-8pm National line as a
24/7 number can strand a user at night. The PO ruling: never present the National line as a lone or
"24/7" number; 999 (emergency, 24/7) is the immediate-danger lead.

This is a TRUTHFULNESS invariant, complementary to:
  * assert_crisis_copy_resolves (no raw placeholder ships), and
  * the always-24/7-in-top-set property (select_crisis_resources never strands a user).

It is intentionally NARROW: it only fires when a false-availability token sits WITHIN _WINDOW
characters of the National line number in the SAME resolved string. A legitimately 24/7 resource
(999, SAKINA, DHA) may still say "24/7" — just not glued to the National number. The National marker
and the resource numbers are derived from CRISIS_RESOURCES, so the guard follows a value change.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from sage_poc.config import CRISIS_CONFIG, CRISIS_RESOURCES
from sage_poc.crisis_copy import crisis_copy_source_files, resolve_crisis_placeholders_deep

# How close (chars) a false-availability token must sit to the National number to count as "adjacent"
# (i.e. asserting that availability ABOUT the National line). Wide enough to catch "800-4673, free
# and available 24 hours a day"; narrow enough that a separate 24/7 resource listed elsewhere in the
# same multi-line string does not false-positive.
_WINDOW = 40

# Availability claims that are FALSE for the 8am-8pm National line. Matched case-insensitively.
_FORBIDDEN_AVAILABILITY = (
    # English
    "24/7", "24-7", "24 hours", "24 hour", "24hrs", "24hr",
    "around the clock", "any time of day", "day or night",
    "any time", "anytime", "all hours", "open 24", "available 24",
    "always available", "available always",
    # Arabic
    "24 ساعة", "على مدار الساعة", "على مدار اليوم",
    "متاح كل وقت", "متاح في أي وقت", "في أي وقت", "أي وقت", "طوال الوقت",
    "دايم", "دائم", "دعم دايم", "دعم دائم",
)


def _digit_runs(s: str) -> set[str]:
    return set(re.findall(r"\d{3,}", s))


def _national_markers() -> set[str]:
    """Digit-run(s) that uniquely identify the National line number (not shared with any other
    resource number). For the current directory this is {"4673"}."""
    national = CRISIS_CONFIG["number"]
    other_runs: set[str] = set()
    for r in CRISIS_RESOURCES:
        num = r.get("number", "")
        if num != national:
            other_runs |= _digit_runs(num)
    markers = _digit_runs(national) - other_runs
    assert markers, (
        f"National number {national!r} shares all its digit-runs with other resources; the "
        "availability guard needs a unique marker to locate it — revisit this test."
    )
    return markers


def _find_violation(text: str) -> str | None:
    """Return the first false-availability token found within _WINDOW chars of a National-line
    number occurrence in *text*, or None. Case-insensitive."""
    markers = _national_markers()
    low = text.lower()
    forbidden_low = [(tok, tok.lower()) for tok in _FORBIDDEN_AVAILABILITY]
    for marker in markers:
        start = 0
        while True:
            i = low.find(marker.lower(), start)
            if i == -1:
                break
            lo = max(0, i - _WINDOW)
            hi = min(len(low), i + len(marker) + _WINDOW)
            window = low[lo:hi]
            for tok, tok_low in forbidden_low:
                if tok_low in window:
                    return tok
            start = i + len(marker)
    return None


def _iter_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_strings(item)
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from _iter_strings(value)


@pytest.mark.parametrize("path", crisis_copy_source_files(), ids=lambda p: p.name)
def test_no_false_247_adjacent_to_national_number(path: Path):
    """Every resolved crisis-copy string: no 24/7 / "24 hours" / "متاح كل وقت" claim adjacent to
    the 8am-8pm National line number."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pytest.skip(f"{path} not JSON-parseable")
        return
    resolved = resolve_crisis_placeholders_deep(data)
    offenders = []
    for s in _iter_strings(resolved):
        tok = _find_violation(s)
        if tok is not None:
            offenders.append((tok, s[:160]))
    assert not offenders, (
        f"{path.name}: false availability claim(s) adjacent to the National line number "
        f"({CRISIS_CONFIG['number']}, {CRISIS_CONFIG['hours']}): {offenders}. The National line is "
        "NOT 24/7 — state its real hours, or point urgency to emergency services (999). Never present "
        "the 8am-8pm National line as a lone or 24/7 number."
    )


def test_guard_flags_a_false_247_next_to_national():
    # Positive control: the exact bug class this guard exists to catch (EN + AR).
    assert _find_violation("call 800-HOPE (800-4673), free and available 24 hours a day") is not None
    assert _find_violation("خط الدعم النفسي الوطني 800-4673 متاح كل وقت") is not None
    assert _find_violation("800-4673 (24/7)") is not None
    assert _find_violation("800-4673 متاح في أي وقت") is not None


def test_guard_allows_true_hours_and_a_distant_24_7_line():
    # Negative control: National line stated with true hours, and a genuinely-24/7 emergency line
    # far enough away, must NOT trip the guard.
    ok = (
        "National Mental Support Line 800-HOPE (800-4673) (free, 8am–8pm daily), or emergency "
        "services 999. Emergency services are available 24 hours a day."
    )
    assert _find_violation(ok) is None
    ok_ar = "خط الدعم النفسي الوطني 800-4673 (مجاني، 8am–8pm daily)، وللحالات العاجلة اتصل بخدمات الطوارئ 999"
    assert _find_violation(ok_ar) is None
