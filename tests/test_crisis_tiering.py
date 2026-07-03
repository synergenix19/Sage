"""W1-core: crisis tiering (v7.1 amendment to §5.1 OR-fusion).

This file has two layers:
  1. RESOLVER unit tests (this commit) — pure, fast, no model: the signal-set + language →
     tier mapping, sourced entirely from rules/data/tier_routing/tier_routing.json (no hardcoded
     boundary in code). Covers audit checklist C and the tier semantics of E.
  2. BEHAVIORAL + S7 invariant tests (next commit, gate plumbing) — assert real routing through
     safety_check/graph with the flag ON: the two prod FP strings resolve T1, the Arabic
     command-hallucination resolves T2, and the three S7 Cardinal-Rule-4 invariants. Those are
     marked below with an explicit skip so this file never claims coverage it does not yet have.
"""
import asyncio
import pytest

from sage_poc.safety.crisis_tier import resolve_crisis_tier


# ── Layer 1: resolver unit tests (the 3 signed rules) ────────────────────────

def test_s1_keyword_any_language_is_T2():
    # Any S1 keyword flag → acute, regardless of language or an accompanying S3 hit.
    assert resolve_crisis_tier({"si_explicit"}, "en") == "T2"
    assert resolve_crisis_tier({"si_passive"}, "ar") == "T2"
    assert resolve_crisis_tier({"si_explicit", "s3_semantic"}, "en") == "T2"


def test_s3_solo_english_is_T1():
    # Semantic-only (no keyword corroboration) in English → warm concern, NOT the RED card.
    # This is the exact production incident: "i am feeling hopeless" fired s3_semantic alone.
    assert resolve_crisis_tier({"s3_semantic"}, "en") == "T1"


def test_s3_solo_arabic_and_arabizi_is_T2():
    # AR/AZ keyword coverage is weak, so a semantic-only hit there stays acute (preserves the
    # Arabic command-hallucination catch found in prod).
    assert resolve_crisis_tier({"s3_semantic"}, "ar") == "T2"
    assert resolve_crisis_tier({"s3_semantic"}, "az") == "T2"


def test_no_signal_is_none():
    assert resolve_crisis_tier(set(), "en") == "none"
    assert resolve_crisis_tier(set(), "ar") == "none"


# ── Conservative language gate (closes the S5-misclassification hole) ─────────
# The T1 (warm) route is only safe on CONFIDENT English. Language ID is weakest exactly
# for Arabizi / code-switch, and a true-SI message misread as "en" would drop to T1.
# Fail-closed: anything not confidently English resolves as AR/AZ -> T2.

def test_s3_solo_en_but_code_switched_is_T2():
    assert resolve_crisis_tier({"s3_semantic"}, "en", code_switching=True) == "T2"


def test_s3_solo_en_but_arabizi_suspect_is_T2():
    assert resolve_crisis_tier({"s3_semantic"}, "en", arabizi_suspect=True) == "T2"


def test_s3_solo_confident_en_is_still_T1():
    # the benefit is preserved for genuinely-confident English
    assert resolve_crisis_tier({"s3_semantic"}, "en",
                               code_switching=False, arabizi_suspect=False) == "T1"


def test_s3_unknown_language_fails_closed_to_T2():
    # a semantic crisis signal in a language no rule maps (e.g. mis-ID'd "fr") must NOT
    # fall through to "none" — any fired signal that is not confidently-EN routes T2.
    assert resolve_crisis_tier({"s3_semantic"}, "fr") == "T2"


def test_arabizi_suspect_helper_flags_digit_letters():
    from sage_poc.safety.crisis_tier import _is_arabizi_suspect
    assert _is_arabizi_suspect("ana ta3ban w m5taneg mn 7yati")  # 3/5/7 as letters
    assert not _is_arabizi_suspect("i am feeling hopeless")
    assert not _is_arabizi_suspect("i have 3 kids and 2 jobs")   # digits as numbers, not letters


def test_resolver_fails_closed_when_rules_file_unloadable(monkeypatch):
    # A missing/malformed tier_routing.json at runtime must resolve any fired signal to T2
    # (never T0/T1, never an exception dropping the turn); no signal -> none.
    import sage_poc.safety.crisis_tier as ct

    def _boom():
        raise FileNotFoundError("tier_routing.json missing")

    monkeypatch.setattr(ct, "_load_tier_rules", _boom)
    assert ct.resolve_crisis_tier({"s3_semantic"}, "en") == "T2"   # fired -> fail-closed acute
    assert ct.resolve_crisis_tier({"si_explicit"}, "ar") == "T2"
    assert ct.resolve_crisis_tier(set(), "en") == "none"           # nothing fired -> none


def test_tier_routing_is_a_validated_rules_service_category():
    # Not a loose config file: it loads + schema-validates through the rules engine like any
    # other category, so a malformed rule fails the build (CI guard).
    from sage_poc.rules.loader import load_rules
    import json as _json
    from sage_poc.safety.crisis_tier import _RULES_PATH
    rules = load_rules("tier_routing")
    assert [r.id for r in rules] == ["s1_any", "s3_solo_en", "s3_ar_az", "s3_failclosed"]
    assert _json.loads(_RULES_PATH.read_text())["version"]  # file carries a version


def test_resolver_reads_json_not_hardcoded_constants():
    # Audit C: the boundary lives in tier_routing.json, exactly 3 rules, no phrase lists.
    from sage_poc.safety.crisis_tier import _load_tier_rules
    rules = _load_tier_rules()
    # 3 signed rules + the authorized fail-closed catch-all (language-gate closure 2026-07-03).
    assert [r["id"] for r in rules] == ["s1_any", "s3_solo_en", "s3_ar_az", "s3_failclosed"]
    for r in rules:
        assert "phrases" not in r and "keywords" not in r, "tier rules must carry no phrase lists (§K)"


# ── Layer 2: routing authority + S7 Cardinal-Rule-4 invariants (real, not stubbed) ──
# These drive the actual graph router _route_after_safety with the flag toggled. is_safe stays
# the truthful detector aggregate; routing authority is crisis_tier under the flag.
import sage_poc.config as _cfg
from sage_poc.graph import _route_after_safety


def _st(**kw):
    base = {"crisis_state": "none", "is_safe": True, "crisis_tier": "none", "s7_result": None}
    return {**base, **kw}


def test_flag_on_T1_routes_safe_not_crisis(monkeypatch):
    # The whole point: a T1 turn (is_safe False because s3 fired) routes to the normal graph.
    monkeypatch.setattr(_cfg, "CRISIS_TIERING_ENABLED", True)
    assert _route_after_safety(_st(is_safe=False, crisis_tier="T1")) == "safe"


def test_flag_on_T2_routes_crisis(monkeypatch):
    monkeypatch.setattr(_cfg, "CRISIS_TIERING_ENABLED", True)
    assert _route_after_safety(_st(is_safe=False, crisis_tier="T2")) == "crisis"


def test_flag_off_ignores_crisis_tier_and_routes_on_is_safe(monkeypatch):
    # Check B: with the flag OFF, a T1-tier state still routes on is_safe exactly like master.
    monkeypatch.setattr(_cfg, "CRISIS_TIERING_ENABLED", False)
    assert _route_after_safety(_st(is_safe=False, crisis_tier="T1")) == "crisis"
    assert _route_after_safety(_st(is_safe=True, crisis_tier="none")) == "safe"


def test_monitoring_reescalates_regardless_of_tier(monkeypatch):
    # Disposition: tiering does NOT apply in monitoring; any fired signal re-escalates.
    monkeypatch.setattr(_cfg, "CRISIS_TIERING_ENABLED", True)
    assert _route_after_safety(_st(crisis_state="monitoring", is_safe=False, crisis_tier="T1")) == "crisis"


def test_s7_timeout_cannot_suppress_same_turn_s1_fire(monkeypatch):
    # S7 Cardinal-Rule-4: an S1 keyword fire resolves T2 and routes crisis even when S7
    # produced nothing (timeout -> s7_result None). S7 failure never downgrades a deterministic fire.
    monkeypatch.setattr(_cfg, "CRISIS_TIERING_ENABLED", True)
    tier = resolve_crisis_tier({"si_explicit", "s3_semantic"}, "en")  # S1 fired
    assert tier == "T2"
    assert _route_after_safety(_st(is_safe=False, crisis_tier=tier, s7_result=None)) == "crisis"


# Behavioral prod-FP ("i am feeling hopeless"/"burden...so low" -> T1) and the Arabic/Arabizi
# command-hallucination -> T2 cases require real BGE-M3 S3 scoring; they are exercised end-to-end
# by the per-case fail-closed recall regression (scripts/), not here, to keep this file model-free.


@pytest.mark.xfail(
    strict=True,
    reason="Gate-1 S1-az coverage gap (NOT a tiering regression) — see "
           "governance/2026-07-03-arabizi-si-detection-finding.md. Flips to a hard pass "
           "(strict xfail -> XPASS failure) the moment clinician-approved az keywords land.",
)
@pytest.mark.asyncio
async def test_arabizi_explicit_si_fires_s1_XFAIL_gate1():
    # Surfaced by the tiering D/E pass: this Arabizi explicit-SI phrase fires NOTHING (S1-az
    # keyword gap + S3 blind to Arabizi) -> missed identically flag-OFF/ON. Non-inferiority holds;
    # this asserts the DETECTION fix, tracked upstream, not the tiering routing.
    from sage_poc.nodes.safety_check import safety_check_node
    out = await safety_check_node({
        "raw_message": "ana 3ayez amot ma3ish 3ayiz a3ish", "path": [], "turn_number": 0,
        "turn_count": 0, "crisis_state": "none", "clinical_flags": [], "crisis_flags": [],
        "distress_trajectory": [], "engagement_trajectory": [], "engagement": 5,
        "emotional_intensity": 5, "therapeutic_profile": {},
    })
    assert out["crisis_flags"], "Arabizi explicit SI must fire S1 (currently missed — S1-az gap)"


# ── output_gate disposition (the flood-risk edit) — negative assertions ──────
from unittest.mock import AsyncMock, patch
from sage_poc.nodes.output_gate import output_gate_node


def _og_state(**kw):
    base = {
        "gate_path": None, "path": [], "detected_language": "en", "message_en": "Same",
        "response_en": "I hear you, that sounds heavy.", "is_safe": False,
        "crisis_state": "none", "crisis_flags": ["s3_semantic"], "clinical_flags": [],
        "conversation_history": [], "turn_count": 0, "conversation_summary": None,
        "session_id": "s1", "user_id": "u1", "active_skill_id": None, "active_step_id": None,
        "emotional_intensity": 5, "engagement": 5, "banned_opener_retry_count": 0,
        "crisis_tier": "T1", "supportive_posture": True,
    }
    return {**base, **kw}


async def _run_og_capturing_reviews(state, monkeypatch):
    monkeypatch.setattr(_cfg, "CRISIS_TIERING_ENABLED", True)
    calls = []

    async def _capture(session_id, user_id, crisis_flags, clinical_flags, *,
                       severity_override=None, reason_override=None):
        calls.append({"crisis_flags": list(crisis_flags), "severity_override": severity_override})

    with patch("sage_poc.nodes.output_gate._log_clinical_review", new=_capture):
        await output_gate_node(state)
        await asyncio.sleep(0.05)  # let fire-and-forget review tasks (create_task) run
    return calls


@pytest.mark.asyncio
async def test_t1_turn_files_no_high_severity_crisis_review(monkeypatch):
    calls = await _run_og_capturing_reviews(_og_state(t1_count=1), monkeypatch)
    # T1 excluded from crisis review: no call carries crisis flags, and none is high-severity.
    assert all(not c["crisis_flags"] for c in calls)
    assert all(c["severity_override"] != "high" for c in calls)


@pytest.mark.asyncio
async def test_supportive_posture_injected_into_freeflow_system_prompt(monkeypatch):
    # G2: a T1 turn (supportive_posture=True) injects the warm-posture frame into the system
    # prompt and marks the prompt_layer. supportive_posture is only set under the flag, so this
    # is byte-identical when OFF.
    import sage_poc.nodes.freeflow_respond as ff
    captured = {}

    async def _fake_tool_loop(llm, messages, tools, **kw):
        captured["system"] = messages[0]["content"]
        return "warm reply"

    monkeypatch.setattr(ff, "_invoke_with_tool_loop", _fake_tool_loop)
    monkeypatch.setattr(ff, "_get_prior_context", AsyncMock(return_value=""))
    out = await ff.freeflow_respond_node(_og_state(supportive_posture=True, response_en=""))
    assert "SUPPORTIVE POSTURE" in captured["system"]
    assert "supportive_posture" in out["prompt_layers"]
    assert 30 <= len(ff._SUPPORTIVE_POSTURE_INSTRUCTION.split()) <= 55


@pytest.mark.asyncio
async def test_g1b_exactly_one_low_flag_on_second_t1(monkeypatch):
    first = await _run_og_capturing_reviews(_og_state(t1_count=1), monkeypatch)
    second = await _run_og_capturing_reviews(_og_state(t1_count=2), monkeypatch)
    third = await _run_og_capturing_reviews(_og_state(t1_count=3), monkeypatch)
    low = lambda cs: [c for c in cs if c["severity_override"] == "low"]
    assert len(low(first)) == 0, "no G1b flag on the 1st T1"
    assert len(low(second)) == 1, "exactly one low-severity G1b flag on the 2nd T1"
    assert len(low(third)) == 0, "no G1b flag on the 3rd T1"
