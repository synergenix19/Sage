"""D1 shadow/enforce audit row (#338) — the shadow observation persists on the per-turn audit row, and a
non-screen turn stays byte-identical to master. Anonymised class+route only (PDPL-approved 2026-07-17)."""
from sage_poc.audit import _build_session_audit_row


def _base_state():
    return {"session_id": "s1", "turn_number": 1, "path": ["skill_select"], "active_skill_id": "dbt_tipp"}


def test_shadow_columns_present_when_shadow_fired():
    st = {**_base_state(), "screen_shadow_action": "ask_screen",
          "screen_shadow_answer_class": None, "screen_shadow_branch": None}
    row = _build_session_audit_row(st)
    assert row["screen_shadow_action"] == "ask_screen"
    assert "screen_shadow_branch" in row
    # anonymised: no message content field ever rides the row
    assert not any("message" in k or "raw" in k and "message" in k for k in row)


def test_shadow_reroute_records_class_and_branch():
    st = {**_base_state(), "screen_shadow_action": "reroute_grounding",
          "screen_shadow_answer_class": "contraindication_disclosed", "screen_shadow_branch": "grounding"}
    row = _build_session_audit_row(st)
    assert row["screen_shadow_answer_class"] == "contraindication_disclosed"
    assert row["screen_shadow_branch"] == "grounding"


def test_non_screen_turn_has_no_screen_columns():
    # byte-identical to master: a turn where neither shadow nor enforce fired carries no screen_* columns
    row = _build_session_audit_row(_base_state())
    assert not any(k.startswith("screen_") for k in row)


def test_enforce_columns_present_on_real_screen_turn():
    st = {**_base_state(), "screen_asked": True, "screen_answer_class": None, "screen_branch_taken": None}
    row = _build_session_audit_row(st)
    assert row["screen_asked"] is True and "screen_branch_taken" in row
