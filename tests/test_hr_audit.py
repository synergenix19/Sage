"""HR-1 Stage 2 Task 5: audit-columns flip blocker for the high_risk_response terminal.

Mirrors the B1 medical red-flag guard's Gate 4 pattern (tests/test_medical_redflag_guard.py,
"Gate 4: audit-columns flip blocker"): high_risk_response.py's _deliver_branch already sets
hr_branch/hr_distress_score on the state update it hands to write_session_audit, but until
_build_session_audit_row carries a matching conditional block, those fields are
written-then-dropped before ever reaching the persisted row (migration 013 is the deploy
gate for SAGE_HIGH_RISK_TERMINAL, same discipline as migration 012 for
SAGE_MEDICAL_REDFLAG_GUARD). These tests pin the row builder directly, not
write_session_audit's input state.

Conditional inclusion (crisis_tier / precedence / medical_flags convention): the hr_* columns
are included ONLY when a distress branch actually resolved this turn (hr_branch set), so a
flag-OFF / non-HR / mid-protocol (reask, no branch yet) row stays byte-identical to master
(Check B).
"""


def _audit_state(**kwargs) -> dict:
    defaults = {
        "session_id": "test-session-hr-audit-gate5",
        "turn_number": 2,
        "path": ["safety_check", "high_risk_response"],
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "intent_confidence": 0.9,
        "active_skill_id": None,
        "active_step_id": None,
        "skill_match_method": None,
        "knowledge_passages": [],
        "knowledge_abstain": False,
        "knowledge_source": "",
        "crisis_state": "none",
        "crisis_flags": [],
        "clinical_flags": [],
        "engagement": 7,
        "emotional_intensity": 4,
        "model_version": "claude-sonnet-4-6",
        "latency_ms": None,
        "user_id": None,
    }
    return {**defaults, **kwargs}


def test_build_session_audit_row_records_hr_branch_and_distress_score():
    from sage_poc.audit import _build_session_audit_row

    state = _audit_state(hr_branch="higher", hr_distress_score=8, gate_path="high_risk")

    row = _build_session_audit_row(state)

    assert row["hr_branch"] == "higher"
    assert row["hr_distress_score"] == 8


def test_build_session_audit_row_omits_hr_columns_when_no_branch_resolved():
    from sage_poc.audit import _build_session_audit_row

    # No hr_branch: either a non-HR turn, or the mid-protocol reask turn (T1 entry / T2
    # reask), which has not yet resolved a branch.
    state = _audit_state()

    row = _build_session_audit_row(state)

    assert "hr_branch" not in row
    assert "hr_distress_score" not in row


def test_build_session_audit_row_byte_identical_to_baseline_when_hr_absent():
    """Same discipline as the crisis_tier/precedence/medical_flags conditional blocks:
    a row built from a state with no hr_branch must be identical to a row built from a
    state that also has no hr_* keys at all -- the conditional block introduces zero
    drift for flag-OFF / non-HR turns."""
    from sage_poc.audit import _build_session_audit_row

    baseline = _build_session_audit_row(_audit_state())
    no_hr_keys_at_all = _build_session_audit_row(_audit_state())

    assert baseline == no_hr_keys_at_all
