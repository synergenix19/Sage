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


def test_stale_gap_clears_pending_offer_and_declined():
    from datetime import datetime, timedelta, timezone
    from sage_poc.server_helpers import _stale_skill_overrides
    old = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    overrides = _stale_skill_overrides({
        "last_turn_at": old,
        "active_skill_id": None,
        "crisis_state": "none",
        "offered_skill_ids": ["worry_time"],
        "declined_skills": ["box_breathing"],
    })
    assert overrides["offered_skill_ids"] is None
    assert overrides["declined_skills"] == []


def test_fresh_session_does_not_clear_offer_or_declined():
    from datetime import datetime, timedelta, timezone
    from sage_poc.server_helpers import _stale_skill_overrides
    recent = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    overrides = _stale_skill_overrides({
        "last_turn_at": recent,
        "active_skill_id": None,
        "crisis_state": "none",
        "offered_skill_ids": ["worry_time"],
        "declined_skills": ["box_breathing"],
    })
    assert overrides == {}


def test_build_state_resets_offer_response_fields():
    from sage_poc.server_helpers import _build_state, _RequestLike, _MessageLike
    req = _RequestLike(messages=[_MessageLike(role="user", content="hi")], session_id="s1")
    state = _build_state(req)
    assert state["offer_response"] is None
    assert state["offer_choice_skill_id"] is None
    assert "offered_skill_ids" not in state, "checkpoint-persisted, must not be reset per turn"
    assert "declined_skills" not in state, "checkpoint-persisted, must not be reset per turn"
