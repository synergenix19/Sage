"""Tests for _stale_skill_overrides in server_helpers.py."""
import pytest
from datetime import datetime, timezone, timedelta
from sage_poc.server_helpers import _stale_skill_overrides


def _checkpoint(active_skill_id=None, crisis_state="none", hours_ago=0):
    last_turn_at = (
        datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    ).isoformat()
    return {
        "last_turn_at":    last_turn_at,
        "active_skill_id": active_skill_id,
        "crisis_state":    crisis_state,
    }


def test_stale_skill_clears_crisis_state_monitoring():
    """A stale skill with crisis_state=monitoring must reset crisis_state to none."""
    snap = _checkpoint(
        active_skill_id="post_crisis_check_in",
        crisis_state="monitoring",
        hours_ago=5,
    )
    overrides = _stale_skill_overrides(snap)
    assert overrides["active_skill_id"] is None
    assert overrides["crisis_state"] == "none", (
        "Stale skill with monitoring crisis_state must clear it to avoid silent re-enrollment"
    )


def test_no_stale_skill_does_not_touch_crisis_state():
    """No stale skill (gap < 4h) must not modify crisis_state."""
    snap = _checkpoint(
        active_skill_id="box_breathing",
        crisis_state="monitoring",
        hours_ago=1,
    )
    overrides = _stale_skill_overrides(snap)
    assert overrides == {}, "Under-threshold gap must return empty overrides"


def test_stale_non_crisis_skill_preserves_none_crisis_state():
    """A stale non-crisis skill must include crisis_state=none in overrides."""
    snap = _checkpoint(
        active_skill_id="box_breathing",
        crisis_state="none",
        hours_ago=5,
    )
    overrides = _stale_skill_overrides(snap)
    assert overrides["active_skill_id"] is None
    assert "crisis_state" in overrides, (
        "crisis_state must always be in overrides for stale skills, regardless of incoming value"
    )
    assert overrides["crisis_state"] == "none"


def test_stale_skill_clears_active_crisis_state():
    """A stale skill with crisis_state=active must also reset to none."""
    snap = _checkpoint(
        active_skill_id="grounding_exercise",
        crisis_state="active",
        hours_ago=5,
    )
    overrides = _stale_skill_overrides(snap)
    assert overrides["crisis_state"] == "none"


def test_no_active_skill_no_crisis_returns_empty():
    """No active_skill_id and no crisis state → no overrides regardless of gap."""
    snap = _checkpoint(active_skill_id=None, crisis_state="none", hours_ago=10)
    overrides = _stale_skill_overrides(snap)
    assert overrides == {}


def test_stale_crisis_only_no_active_skill_resets_crisis_state():
    """Crisis state persists after _crisis_response_node sets active_skill_id=None.

    The canonical CSM-3 gap: user hit crisis (monitoring, no active skill),
    disappeared for 4h. Stale check must still reset crisis_state.
    """
    snap = _checkpoint(
        active_skill_id=None,
        crisis_state="monitoring",
        hours_ago=5,
    )
    overrides = _stale_skill_overrides(snap)
    assert overrides.get("crisis_state") == "none", (
        "Stale monitoring state with no active skill must still reset crisis_state"
    )
    # No skill to clear — these keys should not appear in overrides
    assert "active_skill_id" not in overrides
    assert "stale_skill_id" not in overrides


def test_stale_crisis_active_state_also_resets():
    """crisis_state='active' should also be reset on stale gap."""
    snap = _checkpoint(
        active_skill_id=None,
        crisis_state="active",
        hours_ago=5,
    )
    overrides = _stale_skill_overrides(snap)
    assert overrides.get("crisis_state") == "none"
