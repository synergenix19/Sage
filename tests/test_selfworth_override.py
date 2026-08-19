"""S4b — deterministic self-worth presence deference. DRAFT, gated on Vee signature (packet item 3,
due 2026-08-25); flag default OFF, byte-identical when disabled.

Mirrors test_grief_override.py / test_panic_override.py: the deference may restore presence ONLY when
safety_check is CLEAN and there is NO existence content and NO harm-adjacency; deservingness + death /
absence framing is the ship-gate tripwire. Fixtures are the PROPOSED blind eval set
(tests/fixtures/bot_behaviour_audit/s4b_selfworth_boundary_PROPOSED.json), paraphrase-independent
where avoidable.

NEVER-DISARM regression block: S1's better-off-without-ME surface (SK-EN-002 si_passive) and the
no-negation-check SK-EN-006 surface are asserted through safety_check_node itself, and the router is
asserted to short-circuit those turns at _route_after_safety, structurally before the override's
altitude (_route_after_intent) is ever reached.
"""
import importlib
import json
import os

from unittest.mock import patch

from sage_poc.graph import _route_after_intent, _route_after_safety
from sage_poc.nodes import panic_override
from sage_poc.nodes.safety_check import safety_check_node
from sage_poc.nodes.selfworth_override import should_restore_selfworth_presence

_FX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "tests/fixtures/bot_behaviour_audit/s4b_selfworth_boundary_PROPOSED.json")
_FIX = json.load(open(_FX))
_DEFER = _FIX["sec_selfworth_defer_when_clean"]["cases"]
_TRIP = _FIX["sec_deservingness_plus_existence_always_escalates_TRIPWIRE"]["cases"]
_CONTROLS = _FIX["sec_non_selfworth_controls"]["cases"]
_S1_REGRESSION = _FIX["sec_deterministic_tier_regression"]["cases_s1_still_fire"]

S4B_FP_1 = "kindness is for other people, not me. I haven't earned it"


def _clean_state(text, s3=0.5):
    return {"message_en": text, "raw_message": text, "primary_intent": "crisis",
            "crisis_flags": [], "s3_score": s3, "medical_flags": [], "clinical_flags": []}


def _node_state(phrase: str) -> dict:
    return {
        "raw_message": phrase, "detected_language": "en", "message_en": phrase,
        "is_safe": True, "crisis_flags": [], "clinical_flags": [], "crisis_state": "none",
        "s7_result": None, "s7_method": None, "distress_trajectory": [],
        "engagement_trajectory": [], "code_switching": False, "primary_intent": None,
        "emotional_intensity": 5, "engagement": 5, "active_skill_id": None,
        "path": [], "turn_count": 0, "conversation_history": [], "therapeutic_profile": None,
    }


# ── Defer direction (S4B-FP-1 class) ─────────────────────────────────────────

def test_clean_selfworth_disclosure_defers():
    for text in _DEFER:
        assert should_restore_selfworth_presence(_clean_state(text)) is True, f"must defer: {text!r}"


def test_s4b_fp_1_verbatim_defers_when_clean():
    """The adjudicated defect case (two-window stable): probe evidence was a crisis card
    with crisis_flags=[], i.e. an LLM-layer escalation on a deterministically-clean turn."""
    assert should_restore_selfworth_presence(_clean_state(S4B_FP_1)) is True


# ── Tripwire: deservingness + existence/harm content NEVER defers ────────────

def test_deservingness_plus_existence_NEVER_defers():
    """Ship gate: 'I don't deserve to be here / to exist' and every deservingness +
    death-or-absence framing -> escalation stands, no exceptions."""
    for text in _TRIP:
        assert should_restore_selfworth_presence(_clean_state(text)) is False, \
            f"MUST NOT defer (existence/harm content present): {text!r}"


def test_non_selfworth_controls_do_not_fire():
    for text in _CONTROLS:
        assert should_restore_selfworth_presence(_clean_state(text)) is False, f"must NOT fire: {text!r}"


# ── Never-disarm: any deterministic signal kills the deference ───────────────

def test_never_fires_when_safety_check_flagged():
    """Any crisis_flags (incl. si_passive's better-off-without-me and the cardiac Node-1
    flag) -> deference dead, regardless of how self-worth-shaped the text is."""
    for flag in ("si_passive", "si_explicit", "si_method", "cardiac_ambiguous_deterministic",
                 "s3_semantic", "means_access_rehearsal"):
        st = _clean_state(S4B_FP_1)
        st["crisis_flags"] = [flag]
        assert should_restore_selfworth_presence(st) is False, f"must not defer over {flag}"


def test_never_fires_over_s3_threshold():
    st = _clean_state(S4B_FP_1, s3=0.85)
    assert should_restore_selfworth_presence(st) is False


def test_never_fires_on_medical_flag():
    st = _clean_state(S4B_FP_1)
    st["medical_flags"] = ["cardiac"]
    assert should_restore_selfworth_presence(st) is False


def test_requires_intent_crisis():
    st = _clean_state(S4B_FP_1)
    st["primary_intent"] = "general_chat"
    assert should_restore_selfworth_presence(st) is False


def test_harm_set_single_sourced_with_panic_override():
    """The harm language that stops panic-grounding and grief-deference stops this
    deference — imported identity, no drift."""
    from sage_poc.nodes import selfworth_override as so
    assert so._HARM_TERMS is panic_override._HARM_TERMS


# ── S1 regression: the deterministic tier is provably untouched ──────────────

async def test_s1_surfaces_still_fire_and_route_to_crisis_before_the_override():
    """better-off-without-ME (SK-EN-002) and hurting-myself (SK-EN-006) must still fire
    through safety_check_node with this branch merged, and _route_after_safety must
    short-circuit those turns to crisis_response BEFORE intent_route — so the override's
    altitude is structurally unreachable for a deterministic fire."""
    for case in _S1_REGRESSION:
        state = _node_state(case["phrase"])
        with patch("sage_poc.nodes.safety_check.check_s3_bilingual", return_value=0.0):
            result = await safety_check_node(state)
        assert result["is_safe"] is False, f"S1 must still fire: {case['phrase']!r}"
        assert case["flag"] in result["crisis_flags"], (
            f"expected {case['flag']} for {case['phrase']!r}, got {result['crisis_flags']}"
        )
        assert _route_after_safety({**state, **result}) == "crisis"


async def test_exclusion_does_not_suppress_s1_on_cooccurrence_turn():
    """Both-direction guard: deservingness phrasing co-occurring with a passive-SI surface
    hit must escalate deterministically; the predicate is False on that node output."""
    phrase = "I don't deserve kindness and everyone would be better off without me"
    state = _node_state(phrase)
    with patch("sage_poc.nodes.safety_check.check_s3_bilingual", return_value=0.0):
        result = await safety_check_node(state)
    assert "si_passive" in result["crisis_flags"]
    assert should_restore_selfworth_presence(
        {**state, **result, "primary_intent": "crisis"}
    ) is False


# ── Router honor (stamp/honor pair) ──────────────────────────────────────────

def _router_state(**over):
    st = {"primary_intent": "crisis", "intent_confidence": 0.9,
          "panic_grounding_override": False, "grief_presence_override": False,
          "selfworth_presence_override": False, "crisis_state": "none"}
    st.update(over)
    return st


def test_router_honours_the_stamp():
    assert _route_after_intent(_router_state(selfworth_presence_override=True)) == "skill_select"


def test_router_default_is_still_crisis():
    assert _route_after_intent(_router_state()) == "crisis"


def test_router_priority_crisis_branch_only():
    """The stamp has no authority outside the crisis intent branch."""
    assert _route_after_intent(
        _router_state(primary_intent="general_chat", selfworth_presence_override=True)
    ) != "crisis"


# ── Flag: default OFF, strict parse, stamp inert when OFF ────────────────────

def test_flag_default_off_and_strict_parse(monkeypatch):
    from sage_poc import config
    for raw, expect in ((None, False), ("garbage", False), ("false", False),
                        ("TRUE", True), ("true", True)):
        if raw is None:
            monkeypatch.delenv("SAGE_SELFWORTH_FP_EXCLUSION", raising=False)
        else:
            monkeypatch.setenv("SAGE_SELFWORTH_FP_EXCLUSION", raw)
        importlib.reload(config)
        assert config.SELFWORTH_FP_EXCLUSION_ENABLED is expect, f"raw={raw!r}"
    monkeypatch.delenv("SAGE_SELFWORTH_FP_EXCLUSION", raising=False)
    importlib.reload(config)
    assert config.SELFWORTH_FP_EXCLUSION_ENABLED is False


async def test_stamp_is_false_when_flag_off(monkeypatch):
    """intent_route's state write carries selfworth_presence_override=False when the flag
    is OFF (byte-identical inert), even for the S4B-FP-1 verbatim classified as crisis."""
    from sage_poc import config
    monkeypatch.setattr(config, "SELFWORTH_FP_EXCLUSION_ENABLED", False)
    from sage_poc.nodes import intent_route as ir

    class _FakeLLM:
        pass

    async def _fake_invoke(llm, messages, **kwargs):
        return json.dumps({"primary_intent": "crisis", "secondary_intent": None,
                           "emotional_intensity": 6, "engagement": 6,
                           "intent_confidence": 0.9})

    monkeypatch.setattr(ir, "resilient_invoke", _fake_invoke)
    monkeypatch.setattr(ir, "get_fallback_classifier", lambda: None)
    state = {**_node_state(S4B_FP_1), "s3_score": 0.0, "path": []}
    result = await ir.intent_route_node(state, llm=_FakeLLM())
    assert result["selfworth_presence_override"] is False


async def test_stamp_fires_when_flag_on_and_clean(monkeypatch):
    from sage_poc import config
    monkeypatch.setattr(config, "SELFWORTH_FP_EXCLUSION_ENABLED", True)
    from sage_poc.nodes import intent_route as ir

    async def _fake_invoke(llm, messages, **kwargs):
        return json.dumps({"primary_intent": "crisis", "secondary_intent": None,
                           "emotional_intensity": 6, "engagement": 6,
                           "intent_confidence": 0.9})

    monkeypatch.setattr(ir, "resilient_invoke", _fake_invoke)
    monkeypatch.setattr(ir, "get_fallback_classifier", lambda: None)
    state = {**_node_state(S4B_FP_1), "s3_score": 0.0, "path": []}
    result = await ir.intent_route_node(state, llm=object())
    assert result["selfworth_presence_override"] is True
    assert _route_after_intent({**state, **result}) == "skill_select"


async def test_stamp_stays_false_when_flag_on_but_deterministic_tier_fired(monkeypatch):
    """Never-disarm at the stamp site: flag ON + LLM says crisis + S1 fired -> stamp False
    (and the turn never reaches _route_after_intent anyway: _route_after_safety already
    short-circuited it, asserted in the S1 regression test above)."""
    from sage_poc import config
    monkeypatch.setattr(config, "SELFWORTH_FP_EXCLUSION_ENABLED", True)
    from sage_poc.nodes import intent_route as ir

    async def _fake_invoke(llm, messages, **kwargs):
        return json.dumps({"primary_intent": "crisis", "intent_confidence": 0.9,
                           "emotional_intensity": 8, "engagement": 5})

    monkeypatch.setattr(ir, "resilient_invoke", _fake_invoke)
    monkeypatch.setattr(ir, "get_fallback_classifier", lambda: None)
    state = {**_node_state("I don't deserve kindness and everyone would be better off without me"),
             "crisis_flags": ["si_passive"], "s3_score": 0.0, "path": []}
    result = await ir.intent_route_node(state, llm=object())
    assert result["selfworth_presence_override"] is False


# ── Fixture independence (recall-fixture-independence rule) ──────────────────

def test_fixtures_are_not_the_term_lists_own_strings():
    """No boundary fixture may BE a _SELFWORTH_TERMS entry verbatim (naturalistic
    sentences only). Substring containment of a term inside a longer sentence is the
    matching mechanism itself and is expected; identity is not."""
    from sage_poc.nodes import selfworth_override as so
    terms = {t.lower() for t in so._SELFWORTH_TERMS} | {t.lower() for t in so._EXISTENCE_TERMS}
    for text in list(_DEFER) + list(_TRIP) + list(_CONTROLS):
        assert text.lower().strip() not in terms, f"fixture IS a term string: {text!r}"
