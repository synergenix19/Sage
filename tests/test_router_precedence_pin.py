"""Precedence-pin test (task-2-brief.md Step 3).

Pins the full ordered name list of each router's precedence table, verbatim.
This is the point of Task 2: the ladder that used to be readable only from a
guard-clause diff is now directly assertable.

REORDERING A ROW HERE REQUIRES THE SAME CLINICAL REVIEW A ROUTING CHANGE
GETS. A row's POSITION encodes a signed precedence ruling (e.g. crisis >
medical > hr > derealization in ROUTE_AFTER_SAFETY; the three crisis-branch
overrides > D1/weave/EMR screen redirects > scope_refusal/jailbreak >
monitoring > the S2-10/HR-1 psychotic referral > R1 offer-accept > F6 venting
> Routing-SF-2 > the Node-2 prepass hint > the EMR modality-request redirect
> the confidence gate in ROUTE_AFTER_INTENT -- see the row-level provenance
comments in src/sage_poc/graph.py for the citations). A failure here means
someone changed WHICH rung wins on a multi-hit turn, not just how the ladder
is spelled -- treat it exactly like a diff to the old nested `if`/`elif`
chain would have been treated: it needs the same sign-off the precedence
order itself carries, not a routine code-review pass.
"""
import pytest

pytestmark = pytest.mark.safety_gate

from sage_poc.graph import (
    ROUTE_AFTER_SAFETY,
    ROUTE_AFTER_INTENT,
    ROUTE_AFTER_SKILL_SELECT,
    ROUTE_AFTER_SKILL_EXECUTOR,
)


def test_route_after_safety_precedence_order():
    assert [r.name for r in ROUTE_AFTER_SAFETY] == [
        "monitoring_reescalate",
        "monitoring_stable",
        "crisis_tiering_t1",
        "not_safe",
        "medical_redflag",
        "high_risk_disclosure",
        "high_risk_reentry",
        "derealization_disclosure",
        "default_safe",
    ]


def test_route_after_intent_precedence_order():
    assert [r.name for r in ROUTE_AFTER_INTENT] == [
        "panic_grounding_override",
        "grief_presence_override",
        "selfworth_presence_override",
        "crisis_intent_default",
        "d1_answering_screen",
        "psychoed_weave_pending",
        "emr_modality_screen_pending",
        "scope_refusal",
        "jailbreak",
        "monitoring_priority",
        "hr_disclosure_redirect",
        "r1_offer_accept",
        "f6_venting_suppression",
        "routing_sf2_acute_intensity",
        "node2_prepass_hint",
        "emr_modality_request_redirect",
        "low_confidence_gate",
        "exit_skill",
        "new_skill",
        "info_request",
        "skill_continuation",
        "default_freeflow",
    ]


def test_route_after_skill_select_precedence_order():
    assert [r.name for r in ROUTE_AFTER_SKILL_SELECT] == [
        "psychoed_weave_escalation",
        "containment_directive",
        "psychoed_serve",
        "d1_screen_served",
        "v2_abstain",
        "info_request_consult_cards",
        "info_request_consult_no_cards",
        "info_request_plain",
        "active_skill_resume",
        "default_freeflow",
    ]


def test_route_after_skill_executor_precedence_order():
    assert [r.name for r in ROUTE_AFTER_SKILL_EXECUTOR] == [
        "reescalation_within_monitoring",
        "emr_rehand",
        "default_freeflow",
    ]


def test_every_table_ends_in_an_unconditional_default_row():
    """Structural invariant the evaluator relies on: _evaluate_route never falls off the
    end of a table. Each table's last row must be enabled=True, predicate=always-True."""
    for table in (
        ROUTE_AFTER_SAFETY, ROUTE_AFTER_INTENT, ROUTE_AFTER_SKILL_SELECT, ROUTE_AFTER_SKILL_EXECUTOR,
    ):
        last = table[-1]
        assert last.enabled_fn(), f"{last.name} (last row) must be unconditionally enabled"
        assert last.predicate({}), f"{last.name} (last row) must unconditionally match"
