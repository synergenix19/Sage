"""B0 — deterministic Node-1 safety-route precedence (BOT BEHAVIOUR §4.5).

The resolver establishes ONE evaluation order for the safety routes that today
resolve implicitly and scattered across _route_after_safety / _route_after_intent
(crisis at safety_check, HR/psychotic mid-chain in intent_route, medical/IPV not yet
built). Order `crisis > medical > HR > IPV` is the clinical decision deferred to the
§4.5 sign-off line; this suite pins the *mechanism* (highest-wins + all-fired-preserved),
which is order-agnostic. Routes plug into the slots in Phase B (E3/E4/E7).
"""
import sage_poc.config as config
from sage_poc.audit import _build_session_audit_row
from sage_poc.nodes.safety_precedence import apply_precedence, resolve_safety_precedence


def _state(*, crisis=False, medical=False, hr=False, ipv=False):
    clinical = []
    if hr:
        clinical.append("psychotic_disclosure")
    if ipv:
        clinical.append("domestic_situation")
    return {
        "is_safe": not crisis,
        "medical_flags": ["cardiac_stroke"] if medical else [],
        "clinical_flags": clinical,
    }


def test_multi_hit_resolves_to_highest_precedence_and_preserves_all_fired():
    # All four safety routes fire on one message ("my chest is crushing and I don't
    # want to be here anymore" class). Highest-precedence wins the turn, but every
    # fired route is still recorded — never dropped (§4.5: all flags to state + audit).
    winner, fired = resolve_safety_precedence(
        _state(crisis=True, medical=True, hr=True, ipv=True)
    )
    assert winner == "crisis"
    assert set(fired) == {"crisis", "medical", "hr", "ipv"}


# --- ratification-sensitive order (locks the §4.5 proposed order: crisis>medical>hr>ipv) ---
# These characterize the CURRENT proposed order so a post-ratification reorder must be a
# conscious edit that updates these expectations, not a silent tuple change.

def test_medical_wins_when_no_crisis():
    winner, fired = resolve_safety_precedence(_state(medical=True, hr=True, ipv=True))
    assert winner == "medical"
    assert set(fired) == {"medical", "hr", "ipv"}


def test_hr_beats_ipv_when_no_crisis_or_medical():
    winner, fired = resolve_safety_precedence(_state(hr=True, ipv=True))
    assert winner == "hr"
    assert set(fired) == {"hr", "ipv"}


def test_ipv_alone_wins_and_is_recorded():
    winner, fired = resolve_safety_precedence(_state(ipv=True))
    assert winner == "ipv"
    assert fired == ["ipv"]


def test_no_safety_route_returns_none_and_empty():
    # The common case: nothing fired -> resolver is inert, caller falls through to
    # tier/category routing unchanged.
    winner, fired = resolve_safety_precedence(_state())
    assert winner is None
    assert fired == []


# --- apply_precedence: the flag-gated seam safety_check_node merges into its return ---

def test_apply_precedence_off_returns_empty_dict(monkeypatch):
    # Flag OFF (default) -> emits NO precedence keys, so the node return + audit row stay
    # byte-identical to v7/master.
    monkeypatch.setattr(config, "ROUTE_PRECEDENCE_ENABLED", False)
    assert apply_precedence(_state(crisis=True, medical=True, hr=True, ipv=True)) == {}


def test_apply_precedence_on_canonical_multihit_preserves_suppressed_route(monkeypatch):
    # Record's canonical example: "my chest is crushing and I don't want to be here anymore"
    # trips BOTH crisis and the medical red-flag. Crisis wins the turn; the medical route it
    # suppressed is still recorded (§4.5: never dropped).
    monkeypatch.setattr(config, "ROUTE_PRECEDENCE_ENABLED", True)
    out = apply_precedence(_state(crisis=True, medical=True))
    assert out["precedence_winner"] == "crisis"
    assert set(out["fired_safety_routes"]) == {"crisis", "medical"}


# --- audit row: the "never dropped" clause is a persistence obligation, not a comment ---

def test_audit_row_records_all_fired_routes_even_when_precedence_suppressed():
    row = _build_session_audit_row(
        {"fired_safety_routes": ["crisis", "medical"], "precedence_winner": "crisis"}
    )
    assert row["precedence_winner"] == "crisis"
    assert set(row["fired_safety_routes"]) == {"crisis", "medical"}


def test_audit_row_omits_precedence_fields_when_flag_off():
    # No precedence keys in state (flag OFF path) -> row carries no precedence columns,
    # byte-identical to master; migration becomes a flag-flip deploy gate, not a merge gate.
    row = _build_session_audit_row({})
    assert "precedence_winner" not in row
    assert "fired_safety_routes" not in row
