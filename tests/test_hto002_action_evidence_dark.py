"""SK-EN-HTO-002 — action-evidence harm proximity (wall-punch class), merged DARK.

Signed disposition: class ESCALATES — 2026-08-19-vee-approval-record-signature-sheet.md
item 7 (PO relay). Cells: docs/superpowers/plans/2026-08-18-219-canary-plan.md sections
3 and 5 (must-NOT-fire wording signed via the same record). Mirrors
tests/test_harm_to_others_node1_backstop.py (the #219 precedent) with one addition:
because the rule ships active:false ahead of the canary T0 flip, the engine-level fire
direction is tested under FORCED ACTIVATION (rule re-validated with active=True and
injected into the loader cache), while the as-shipped dark state is asserted inert —
the engine never sees the rule and serves master behavior unchanged.

These tests assert:
1. rule structure (Node-1 crisis rule, regex, negation_check, correct flag_id, the
   signed approved_by value, active:false as shipped);
2. INERT AS SHIPPED — active:false means the loader excludes the rule and NO fixture
   (fire or must-not-fire direction) produces the new flag, so prod is unaffected
   until the deploy owner flips it at canary T0;
3. FIRE DIRECTION under forced activation — the canary plan's F-cells (L2-02 verbatim
   + paraphrases) plus a fixture-independence paraphrase set all fire;
4. MUST-NOT-FIRE under forced activation — venting-without-harm, media/game reference,
   idiom class INCLUDING Vee's held Group-B figurative phrases (2026-07-09 ruling,
   re-affirmed HELD in the 2026-08-19 record), negation/denial, no-person-proximity
   boundary paraphrases, and a third-party victim report (IPV/CF-005 territory, not
   harm-to-others) — the inverted FP asymmetry: a false positive here is a crisis card
   served to someone venting;
5. fixture-independence — no pattern string appears verbatim in any fire fixture
   (the E7 fixture=pattern tautology guard), and no held Group-B phrase appears in
   the pattern set.

The FULL gate (prod-HTTP cells, organic-fire review) runs at canary T0/+2h/+24h/+72h
per the plan; activation itself is the deploy owner's act.
"""
import json
import pathlib
from contextlib import contextmanager

import pytest

from sage_poc.rules import engine as rules_engine
from sage_poc.rules import loader
from sage_poc.rules.schemas import SafetyRule

_KW = pathlib.Path("src/sage_poc/rules/data/safety/crisis_keywords.json")
_FIXTURES = pathlib.Path("tests/fixtures/safety/harm_proximity_hto002.jsonl")

RULE_ID = "SK-EN-HTO-002"
FLAG_ID = "harm_to_others_action_evidence"
SIGNED_APPROVED_BY = (
    "Vee (clinical lead) 2026-08-19 — PO relay; "
    "record: 2026-08-19-vee-approval-record-signature-sheet.md"
)

# Vee's held Group-B figurative list (2026-07-09 ruling; NOT exercised in the
# 2026-08-19 relay — stays held). Must never appear in this rule's patterns.
GROUP_B_HELD = [
    "could kill him",
    "strangle",
    "could hurt him",
    "might do something i regret",
]


def _raw_rule() -> dict | None:
    d = json.loads(_KW.read_text())
    return next((r for r in d["rules"] if r["rule_id"] == RULE_ID), None)


def _cases() -> list[dict]:
    return [json.loads(line) for line in _FIXTURES.read_text().splitlines() if line.strip()]


_FIRE = [c for c in _cases() if c["expect_fire_when_active"]]
_NO_FIRE = [c for c in _cases() if not c["expect_fire_when_active"]]


def _crisis_flags(utt: str) -> list[str]:
    res = rules_engine.evaluate("safety", {
        "text_en": utt.lower(), "text_ar": None, "language": "en", "text_raw": utt.lower(),
    })
    return [a.get("flag_id") for a in res.actions if a.get("type") == "crisis_flag"]


@contextmanager
def _forced_active():
    """Inject SK-EN-HTO-002 re-validated with active=True into the loader cache.

    The loader excludes active:false rules at load time, so the dark rule never
    reaches the engine; this is the only seam that lets the fire direction be
    tested pre-activation without touching the shipped JSON."""
    loader.reload_all()
    base = loader.load_rules("safety")
    assert all(r.rule_id != RULE_ID for r in base), "dark rule must not load from disk"
    forced = SafetyRule.model_validate({**_raw_rule(), "active": True})
    loader._cache["safety"] = base + [forced]
    try:
        yield
    finally:
        loader.reload_all()


# ── 1. structure ─────────────────────────────────────────────────────────────

def test_rule_structure_dark_action_evidence():
    r = _raw_rule()
    assert r is not None, f"{RULE_ID} must exist"
    assert r["active"] is False, \
        "DARK until canary T0 — the active flip is the deploy owner's separate atomic commit"
    assert r["approved_by"] == SIGNED_APPROVED_BY, \
        "approved_by must carry the exact 2026-08-19 signature-sheet value"
    assert r["action"] == {"type": "crisis_flag", "flag_id": FLAG_ID}, \
        "must be a Node-1 crisis_flag -> s1 -> T2 via s1_any, same disposition path as HTO-001"
    assert "negation_check" in r["modifiers"], "must carry negation_check (HTO-001 parity)"
    assert r["language"] == "en"
    assert r["match_type"] == "regex"


def test_no_group_b_held_phrase_in_patterns():
    # The figurative list stays HELD per the 2026-07-09 ruling (re-affirmed 2026-08-19).
    pats = [p.lower() for p in _raw_rule()["patterns"]]
    for held in GROUP_B_HELD:
        assert not any(held in p for p in pats), \
            f"held Group-B phrase must NOT ship in HTO-002 patterns: {held!r}"


def test_no_stated_intent_patterns():
    # Group A (stated intent) belongs to SK-EN-HTO-001; HTO-002 is action-evidence only.
    pats = [p.lower() for p in _raw_rule()["patterns"]]
    for intent_marker in ["want to hurt", "going to hurt", "planning to hurt", "plan to hurt"]:
        assert not any(intent_marker in p for p in pats), \
            f"stated-intent wording belongs to SK-EN-HTO-001, not HTO-002: {intent_marker!r}"


def test_fixture_independence_no_pattern_verbatim_in_fire_fixtures():
    # E7 lesson (fixture=pattern tautology): patterns are compositional regexes, never
    # fixture strings. No pattern may appear verbatim inside any fire-direction fixture.
    pats = [p.lower() for p in _raw_rule()["patterns"]]
    for case in _FIRE:
        utt = case["utterance"].lower()
        for p in pats:
            assert p not in utt, \
                f"pattern string appears verbatim in fire fixture (tautology): {p!r}"


# ── 2. inert as shipped (dark) ───────────────────────────────────────────────

def test_dark_rule_is_excluded_by_loader():
    loader.reload_all()
    loaded = loader.load_rules("safety")
    assert all(r.rule_id != RULE_ID for r in loaded), \
        "active:false must keep the rule out of the evaluated set (inert as shipped)"


@pytest.mark.parametrize("case", _cases(), ids=lambda c: c["group"][:40])
def test_dark_state_serves_master_behavior(case):
    """As shipped (dark), the new flag fires on NOTHING — fire cells included.

    This is the byte-identical-to-master assertion at the deterministic tier: with
    active:false the loader excludes the rule, so the engine's evaluated rule set —
    and therefore every fixture's crisis_flags — is exactly what master serves."""
    loader.reload_all()
    assert FLAG_ID not in _crisis_flags(case["utterance"]), \
        f"dark rule must not fire pre-activation: {case['utterance']!r}"


# ── 3+4. both directions under forced activation ─────────────────────────────

@pytest.mark.parametrize("activated", [False, True], ids=["dark", "force_activated"])
@pytest.mark.parametrize("case", _FIRE, ids=lambda c: c["group"][:40])
def test_fire_direction(case, activated):
    ctx = _forced_active() if activated else _noop()
    with ctx:
        flags = _crisis_flags(case["utterance"])
    if activated:
        assert FLAG_ID in flags, \
            f"action-evidence harm proximity must reach crisis when active: {case['utterance']!r}"
    else:
        assert FLAG_ID not in flags, \
            f"dark rule must not fire: {case['utterance']!r}"


@pytest.mark.parametrize("activated", [False, True], ids=["dark", "force_activated"])
@pytest.mark.parametrize("case", _NO_FIRE, ids=lambda c: c["group"][:40])
def test_must_not_fire_direction(case, activated):
    # Inverted FP asymmetry: a false positive is a crisis card served to someone
    # venting — trust-damaging over-escalation (the 2026-07-09 ruling's ground).
    ctx = _forced_active() if activated else _noop()
    with ctx:
        flags = _crisis_flags(case["utterance"])
    assert FLAG_ID not in flags, \
        f"[{case['group']}] must NOT fire in any state: {case['utterance']!r}"


@pytest.mark.parametrize("case", _NO_FIRE, ids=lambda c: c["group"][:40])
def test_must_not_fire_holds_at_full_deterministic_tier(case):
    """No crisis_flag of ANY rule fires on the must-not-fire cells while HTO-002 is
    active — the canary plan's N-cell expectation at the deterministic tier
    (crisis_flags empty; an LLM-layer over-escalation would be a separate,
    pre-existing finding)."""
    with _forced_active():
        assert _crisis_flags(case["utterance"]) == [], \
            f"[{case['group']}] deterministic tier must stay silent: {case['utterance']!r}"


@contextmanager
def _noop():
    loader.reload_all()
    yield
