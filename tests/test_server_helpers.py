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
    """A stale non-crisis skill must clear active_skill_id and set crisis_state=none."""
    snap = _checkpoint(
        active_skill_id="box_breathing",
        crisis_state="none",
        hours_ago=5,
    )
    overrides = _stale_skill_overrides(snap)
    assert overrides["active_skill_id"] is None
    assert overrides["crisis_state"] == "none"


def test_no_active_skill_returns_empty():
    """No active_skill_id in checkpoint → no overrides regardless of gap."""
    snap = _checkpoint(active_skill_id=None, crisis_state="monitoring", hours_ago=10)
    overrides = _stale_skill_overrides(snap)
    assert overrides == {}
