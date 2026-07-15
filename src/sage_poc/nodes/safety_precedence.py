"""B0 — deterministic Node-1 safety-route precedence (BOT BEHAVIOUR §4.5).

One resolver that establishes a single evaluation order for the deterministic safety
routes. On a multi-hit turn the highest-precedence route wins, but EVERY fired route is
returned so callers can write them all to SageState + the audit trail — a lower route is
never silently dropped just because a higher one won.

Generalises v7's existing structural precedence (safety_check -> crisis_response runs
before intent_route) and the rules engine's first-match-by-ascending-priority. The routes
themselves (E3 medical, E4 HR, E7 IPV) land in Phase B behind this wiring.
"""
from __future__ import annotations

from sage_poc.safety.hr_disclosure import hr_disclosure_present

# §4.5 order — RATIFIED (clinical lead Rohan Sarda, 2026-07-04, relay via PO; see
# docs/superpowers/governance/2026-07-04-review-cycle-package.md §E + §A-REV).
# crisis-first is spec-mandated (BOT BEHAVIOUR §C/§F: crisis "overrides everything" /
# "Severity-tier logic never supersedes the crisis guard"); medical > HR > IPV is the
# eng-proposed sub-order the clinician approved as part of the package (A1). This tuple IS
# that clinical decision — do not reorder without a record edit.
# NOTE: this ratification unlocks the BUILD. The SAGE_ROUTE_PRECEDENCE flag flip is a SEPARATE
# governed step (audit-column migration + a route actually consuming the winner); today no route
# consults it, so flipping it is inert-plus-risk. Route flags (SAGE_IPV_PREEMPTION, etc.) flip
# only when that route's ≥95% recall gate is MET — approval does not waive the gate.
SAFETY_ROUTE_ORDER: tuple[str, ...] = ("crisis", "medical", "hr", "ipv")


def _crisis_fired(state) -> bool:
    # Mirrors _route_after_safety: crisis == the detector said unsafe this turn.
    return not state.get("is_safe", True)


def _medical_fired(state) -> bool:
    # E3 channel; empty until B1 (medical red-flag screen) populates it.
    return bool(state.get("medical_flags"))


def _hr_fired(state) -> bool:
    # E4 §HR. HR-1 Stage 1 Task 3: psychotic_disclosure always fires; mania_disclosure
    # and dissociation_disclosure are gated behind HIGH_RISK_DETECTION_ENABLED (call-time
    # read, matching apply_precedence's kill-switch honouring below).
    from sage_poc import config  # noqa: PLC0415

    return hr_disclosure_present(
        state.get("clinical_flags") or [], flag_enabled=config.HIGH_RISK_DETECTION_ENABLED
    )


def _ipv_fired(state) -> bool:
    # E7 §6a. domestic_situation exists as a passive flag today; B3 upgrades it to an
    # active pre-emption route.
    return "domestic_situation" in (state.get("clinical_flags") or [])


def fired_safety_routes(state) -> list[str]:
    """Every deterministic safety route that matched this turn, unordered."""
    checks = (
        ("crisis", _crisis_fired),
        ("medical", _medical_fired),
        ("hr", _hr_fired),
        ("ipv", _ipv_fired),
    )
    return [name for name, fired in checks if fired(state)]


def resolve_safety_precedence(state) -> tuple[str | None, list[str]]:
    """Return (winning_route, all_fired_routes).

    winning_route is the highest-precedence fired route per SAFETY_ROUTE_ORDER, or None
    when no safety route fired. all_fired_routes preserves every hit for the audit trail.
    """
    fired = fired_safety_routes(state)
    winner = next((route for route in SAFETY_ROUTE_ORDER if route in fired), None)
    return winner, fired


def apply_precedence(state) -> dict:
    """Flag-gated state delta for safety_check_node to merge into its return.

    Flag OFF (default) -> {} : the node return and audit row stay byte-identical to v7/master.
    Flag ON -> {precedence_winner, fired_safety_routes} : winner drives routing, the full fired
    list rides state so every audit consumer records the suppressed routes too (§4.5 never-dropped).
    Reads config at call time so the kill-switch is honoured live (and monkeypatchable in tests).
    """
    from sage_poc import config  # noqa: PLC0415 — call-time read of the kill-switch

    if not config.ROUTE_PRECEDENCE_ENABLED:
        return {}
    winner, fired = resolve_safety_precedence(state)
    return {"precedence_winner": winner, "fired_safety_routes": fired}
