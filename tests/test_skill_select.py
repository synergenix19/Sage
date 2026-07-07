# tests/test_skill_select.py
import pytest
from sage_poc.nodes.skill_select import skill_select_node, _SKILLS as _ALL_SKILLS


def _ss_state(**overrides):
    base = {
        "raw_message": "",
        "detected_language": "en",
        "message_en": "",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 1.0,
        "emotional_intensity": 5,
        "engagement": 7,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
        "skill_match_method": None,
        "semantic_score": None,
        "distress_trajectory": [],
        "code_switching": False,
    }
    base.update(overrides)
    return base


def _routed_skill(result: dict):
    """The primary skill a turn routes to, independent of the consent mechanism.

    Under R1 a keyword/semantic match at moderate intensity produces an OFFER
    (offered_skill_ids), while acute_direct_entry (intensity >= 8) and the
    Arabic-exclusion gate enter directly (active_skill_id). Routing-intent tests
    (which skill, per the clinical bucketing) should assert the destination
    regardless of whether it is offered or entered — that is what this returns.
    """
    return result.get("active_skill_id") or (result.get("offered_skill_ids") or [None])[0]


@pytest.mark.asyncio
async def test_monitoring_state_always_selects_post_crisis_check_in():
    """When crisis_state=='monitoring', skill_select bypasses keyword/semantic and returns post_crisis_check_in."""
    state = _ss_state(
        message_en="I feel a bit calmer now",
        crisis_state="monitoring",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "post_crisis_check_in"
    assert result["skill_match_method"] == "post_crisis_auto_select"
    assert result["active_step_id"] == "acknowledge_and_check"


@pytest.mark.asyncio
async def test_monitoring_state_continues_from_current_step_if_already_in_skill():
    """If post_crisis_check_in is already active on step 2, skill_select preserves that step."""
    state = _ss_state(
        message_en="I feel a bit calmer",
        crisis_state="monitoring",
        active_skill_id="post_crisis_check_in",
        active_step_id="bridge_or_close",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "post_crisis_check_in"
    assert result["active_step_id"] == "bridge_or_close"


@pytest.mark.asyncio
async def test_normal_state_not_affected_by_post_crisis_check_in_in_registry():
    """post_crisis_check_in's empty target_presentations must not match via keyword or semantic."""
    state = _ss_state(
        message_en="I keep thinking everything is my fault",
        crisis_state="none",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] != "post_crisis_check_in"


@pytest.mark.asyncio
async def test_resolved_state_falls_through_to_normal_skill_matching():
    """In resolved state, skill_select must use normal keyword/semantic matching, not auto-select."""
    state = _ss_state(
        message_en="I keep thinking everything is my fault",
        crisis_state="resolved",
    )
    result = await skill_select_node(state)
    # R1: keyword match produces a consent offer, not direct activation.
    assert result["active_skill_id"] is None
    assert result["offered_skill_ids"][0] == "cbt_thought_record"
    assert result["skill_match_method"] == "keyword_offer"


async def test_skill_executor_l1_exit_from_post_crisis_sets_resolved():
    """L1 exit phrase while post_crisis_check_in is active must set crisis_state='resolved'."""
    from sage_poc.nodes.skill_executor import skill_executor_node
    # "i'm done" is in L1_EXIT_PHRASES and unambiguously signals the user wants to stop
    state = _ss_state(
        message_en="i'm done",
        crisis_state="monitoring",
        active_skill_id="post_crisis_check_in",
        active_step_id="acknowledge_and_check",
        emotional_intensity=5,
        engagement=7,
    )
    result = await skill_executor_node(state)
    assert result["active_skill_id"] is None, (
        "active_skill_id must be cleared on L1 exit"
    )
    assert result.get("crisis_state") == "resolved", (
        "crisis_state must transition to 'resolved' on L1 exit from post_crisis_check_in"
    )
    assert result["escalation_triggered"]["level"] == "L1", (
        "escalation_triggered must carry the L1 escalation dict"
    )


async def test_skill_executor_sets_resolved_when_post_crisis_skill_completes():
    """skill_executor_node must write crisis_state='resolved' when post_crisis_check_in finishes."""
    from sage_poc.nodes.skill_executor import skill_executor_node
    state = _ss_state(
        message_en="I feel much steadier now and I think I am okay to continue with my day",
        crisis_state="monitoring",
        active_skill_id="post_crisis_check_in",
        active_step_id="bridge_or_close",
        emotional_intensity=3,
        engagement=8,
    )
    result = await skill_executor_node(state)
    assert result["active_skill_id"] is None, "Skill must be cleared when bridge_or_close completes"
    # skill_executor's _meets_completion_criteria requires > 10 words — this message has 17
    assert result.get("crisis_state") == "resolved", (
        "crisis_state must transition to 'resolved' when post_crisis_check_in finishes"
    )


@pytest.mark.asyncio
async def test_dbt_tipp_keyword_match():
    # R1 offer model: default intensity (5) is below acute_direct_entry (>=8), so a keyword
    # match yields an OFFER, not direct activation. Message updated 2026-06-14: the prior
    # compound ("...calm down fast, I'm overwhelmed and losing control") now routes to grounding
    # under the merged C1 tiebreak, so it no longer cleanly tests dbt_tipp — use an unambiguous
    # failed-first-line phrase (TIPP's retained indication). The test's purpose is preserved.
    state = _ss_state(message_en="my breathing isn't working and I need something stronger")
    result = await skill_select_node(state)
    assert result["active_skill_id"] is None
    assert result["offered_skill_ids"][0] == "dbt_tipp"
    assert result["skill_match_method"] == "keyword_offer"

@pytest.mark.asyncio
async def test_calm_down_fast_arabic_routes_to_grounding():
    # Merged 2026-06-14 (B.3 re-bucket + Arabic-exclusion gate):
    #  - C1 B.3 (signed): محتاج أهدى بسرعة ("need to calm down fast") re-bucketed dbt_tipp ->
    #    grounding (urgency is not extremity; no failed-first-line marker).
    #  - Arabic-exclusion gate (Option 1): Arabic-script sessions skip the R1 consent offer and
    #    enter the matched skill directly (pre-R1 behavior) until S2-2 ships a tested accept path.
    # Merged outcome: B.3 target (grounding) reached via direct entry, not an offer.
    # See docs/superpowers/governance/2026-06-13-overwhelm-routing-c1-conflict.md
    state = _ss_state(message_en="محتاج أهدى بسرعة", detected_language="ar")
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "grounding_5_4_3_2_1"
    assert not result.get("offered_skill_ids")


def test_semantic_threshold_is_calibrated():
    """Threshold must be in plausible range and calibration gap comment must reflect >= 13 skills."""
    import ast, pathlib
    src = pathlib.Path("src/sage_poc/nodes/skill_select.py").read_text()
    tree = ast.parse(src)
    threshold = None
    for node in ast.walk(tree):
        # Handle both plain assignment (x = ...) and annotated assignment (x: float = ...)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "SEMANTIC_THRESHOLD":
                    threshold = ast.literal_eval(node.value)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "SEMANTIC_THRESHOLD":
                if node.value is not None:
                    threshold = ast.literal_eval(node.value)
    assert threshold is not None, "SEMANTIC_THRESHOLD not found in skill_select.py"
    assert 0.45 <= threshold <= 0.65, f"Threshold {threshold} outside expected range 0.45–0.65"


# ---- Door 3: Semantic fallback proof ------------------------------------------------
# Each test uses a phrase that is keyword-clean for the target skill.
# _phrase_is_keyword_clean asserts this so the 'semantic' method assertion is meaningful.


def _phrase_is_keyword_clean(phrase: str, target_skill_id: str) -> bool:
    """Return True if no keyword in ANY skill is a substring of phrase.

    This is a stricter check than keyword-clean for the target skill only,
    because a phrase matching a DIFFERENT skill's keywords would route to that
    skill via keyword tier rather than the target skill via semantic tier.
    """
    phrase_lower = phrase.lower()
    for skill_id, skill in _ALL_SKILLS.items():
        for kw in skill.target_presentations:
            if kw.lower() in phrase_lower:
                return False
    return True


@pytest.mark.slow
@pytest.mark.asyncio
async def test_semantic_cbt_inherently_broken_phrase():
    """CBT semantic match: phrase describes self-critical schema without keyword overlap."""
    phrase = "I feel like there is something inherently broken in the way I am built"
    assert _phrase_is_keyword_clean(phrase, "cbt_thought_record"), (
        "Phrase accidentally matches a keyword — choose a different phrase for this test."
    )
    state = _ss_state(message_en=phrase)
    result = await skill_select_node(state)
    assert result["offered_skill_ids"][0] == "cbt_thought_record", (
        f"Expected cbt_thought_record offer, got: {result.get('offered_skill_ids')} "
        f"(score: {result.get('semantic_score')})"
    )
    assert result["skill_match_method"] == "semantic_offer"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_semantic_behavioral_activation_stuck_cycle_phrase():
    """Behavioral activation semantic match: withdrawal cycle described without keywords."""
    phrase = "If I could just schedule one small activity for tomorrow and actually do it that would help"
    assert _phrase_is_keyword_clean(phrase, "behavioral_activation"), (
        "Phrase accidentally matches a keyword — choose a different phrase."
    )
    state = _ss_state(message_en=phrase)
    result = await skill_select_node(state)
    assert result["offered_skill_ids"][0] == "behavioral_activation", (
        f"Expected behavioral_activation offer, got: {result.get('offered_skill_ids')} "
        f"(score: {result.get('semantic_score')})"
    )
    assert result["skill_match_method"] == "semantic_offer"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_semantic_worry_time_brain_cycling_phrase():
    """Worry time semantic match: ruminative cycling described without worry/overthink keywords."""
    phrase = "My brain just refuses to stop, the same scenarios cycle through all night"
    assert _phrase_is_keyword_clean(phrase, "worry_time"), (
        "Phrase accidentally matches a keyword — choose a different phrase."
    )
    state = _ss_state(message_en=phrase)
    result = await skill_select_node(state)
    assert result["offered_skill_ids"][0] == "worry_time", (
        f"Expected worry_time offer, got: {result.get('offered_skill_ids')} "
        f"(score: {result.get('semantic_score')})"
    )
    assert result["skill_match_method"] == "semantic_offer"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_semantic_dbt_tipp_internal_volcano_phrase():
    """DBT TIPP semantic match: acute emotional flooding described without TIPP keywords."""
    phrase = "I need something physical to slow my heart rate right now, maybe cold water or intense exercise"
    assert _phrase_is_keyword_clean(phrase, "dbt_tipp"), (
        "Phrase accidentally matches a keyword — choose a different phrase."
    )
    state = _ss_state(message_en=phrase)
    result = await skill_select_node(state)
    assert result["offered_skill_ids"][0] == "dbt_tipp", (
        f"Expected dbt_tipp offer, got: {result.get('offered_skill_ids')} "
        f"(score: {result.get('semantic_score')})"
    )
    assert result["skill_match_method"] == "semantic_offer"


# (test_semantic_mi_readiness_half_wanting_phrase removed — mi_readiness_ruler deprecated 2026-07-07,
#  spec-absent + routing-margin collision; JSON retained, deregistered from SKILL_REGISTRY.)


@pytest.mark.asyncio
async def test_semantic_timeout_falls_back_to_keyword_match():
    """When embedding times out, skill_select must return a keyword match if one exists.

    Timeout fallback must not raise — it must return the keyword match (or None
    if no keyword match), never an exception.
    """
    import asyncio
    from unittest.mock import patch

    async def slow_embedding(*args, **kwargs):
        await asyncio.sleep(100)  # Force timeout

    # "always my fault" matches cbt_thought_record via keyword
    state = _ss_state(message_en="always my fault")

    with patch("sage_poc.nodes.skill_select.asyncio.wait_for", side_effect=asyncio.TimeoutError):
        result = await skill_select_node(state)

    # Keyword match must still work even when semantic times out (R1: as an offer)
    assert result["offered_skill_ids"][0] == "cbt_thought_record", (
        "Keyword fallback failed when semantic timed out"
    )
    assert result["skill_match_method"] == "keyword_offer"
    assert result.get("semantic_score") is None


@pytest.mark.asyncio
async def test_info_request_bypasses_crisis_monitoring():
    """info_request intent routes to knowledge_retrieve even when crisis_state=monitoring.

    When a skill is active, skill_select omits active_skill_id from its return dict so the
    checkpoint preserves it — the skill resumes on the next turn after the knowledge lookup.
    """
    state = _ss_state(
        message_en="what is the number for the crisis line",
        crisis_state="monitoring",
        primary_intent="info_request",
        active_skill_id="post_crisis_check_in",
        active_step_id="acknowledge_and_check",
    )
    result = await skill_select_node(state)
    assert "active_skill_id" not in result, (
        "info_request with active skill must NOT write active_skill_id — "
        "omitting it preserves the checkpoint value so the skill resumes next turn"
    )
    assert "active_step_id" not in result
    assert result["skill_match_method"] is None


@pytest.mark.asyncio
async def test_semantic_timeout_returns_none_when_no_keyword_match():
    """When embedding times out and no keyword matches, active_skill_id must be None."""
    import asyncio
    from unittest.mock import patch

    # A factual question that matches no skill keyword
    state = _ss_state(message_en="what is the capital of France")

    with patch("sage_poc.nodes.skill_select.asyncio.wait_for", side_effect=asyncio.TimeoutError):
        result = await skill_select_node(state)

    assert result["active_skill_id"] is None
    assert result.get("semantic_score") is None


@pytest.mark.asyncio
async def test_arabic_keyword_routes_via_tier1():
    """Arabic-script keyword in target_presentations must match raw_message for Arabic sessions.

    Arabic-exclusion gate (Option 1, 2026-06-13): the match enters directly rather than
    offering (Arabic is excluded from the R1 consent flow). This test still proves the
    raw_message keyword pass fires; only the entry mechanism is direct, not offer.
    """
    state = _ss_state(
        raw_message="تنفس معي",
        message_en="breathe with me",
        detected_language="ar",
        primary_intent="new_skill",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "box_breathing", (
        f"Expected box_breathing direct entry, got active={result.get('active_skill_id')!r} "
        f"offered={result.get('offered_skill_ids')!r}. "
        "Arabic-script keyword تنفس معي must match via raw_message pass."
    )
    assert not result.get("offered_skill_ids"), "Arabic session must not offer"
    assert result["skill_match_method"] == "keyword"


@pytest.mark.asyncio
async def test_arabic_keyword_fires_when_translation_is_ambiguous():
    """When Arabic message_en translation is ambiguous, raw_message keyword pass must fire.

    Arabic-exclusion gate (Option 1, 2026-06-13): match enters directly, not via offer.
    """
    state = _ss_state(
        raw_message="أبي تمرين تنفس",
        message_en="I want some exercise",  # ambiguous — would miss keyword
        detected_language="ar",
        primary_intent="new_skill",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "box_breathing", (
        f"Expected box_breathing direct entry, got active={result.get('active_skill_id')!r} "
        f"offered={result.get('offered_skill_ids')!r}. "
        "Arabic keyword أبي تمرين تنفس must match via raw_message pass."
    )
    assert not result.get("offered_skill_ids"), "Arabic session must not offer"
    assert result["skill_match_method"] == "keyword"


@pytest.mark.asyncio
async def test_arabic_raw_message_only_path():
    """When message_en has NO keyword match, Arabic keyword in raw_message must fire for ar sessions.

    This is the definitive test for the raw_message branch: the English translation
    is semantically neutral so the only way box_breathing is reached is via raw_message.
    """
    state = _ss_state(
        raw_message="تنفس معي",
        message_en="okay let's go",  # no box_breathing keyword, low semantic signal
        detected_language="ar",
        primary_intent="new_skill",
    )
    result = await skill_select_node(state)
    # Arabic-exclusion gate (Option 1, 2026-06-13): match enters directly, not via offer.
    assert result["active_skill_id"] == "box_breathing", (
        f"Expected box_breathing direct entry via raw_message, got active={result.get('active_skill_id')!r} "
        f"offered={result.get('offered_skill_ids')!r}. "
        "When message_en has no keyword, raw_message Arabic keyword must be the match source."
    )
    assert not result.get("offered_skill_ids"), "Arabic session must not offer"
    assert result["skill_match_method"] == "keyword"


@pytest.mark.asyncio
async def test_english_session_ignores_arabic_raw_message():
    """An English session must NOT match via Arabic raw_message keywords.

    detected_language='en' must gate the raw_message branch completely.
    If box_breathing appears in the result for an en session with only an Arabic
    raw_message keyword match, the branch guard is broken.
    """
    state = _ss_state(
        raw_message="تنفس معي",           # Arabic box_breathing keyword
        message_en="okay let's go",       # no keyword match, no semantic signal
        detected_language="en",
        primary_intent="new_skill",
    )
    result = await skill_select_node(state)
    # Either no skill matched, OR if box_breathing matched semantically, it MUST NOT
    # have matched via keyword (which would mean Arabic raw_message leaked into en routing).
    # R1: keyword matches surface as offers, so check the offer list and method.
    if (result.get("offered_skill_ids") or [None])[0] == "box_breathing":
        assert result.get("skill_match_method") != "keyword_offer", (
            "box_breathing matched via keyword tier for an English session with only "
            "an Arabic raw_message keyword. The detected_language=='ar' guard is broken."
        )


# ---------------------------------------------------------------------------
# dbt_tipp interim fix: simpler-technique-failure register
#
# SF-2 means intent_route can classify acute distress as 'general_chat',
# bypassing skill_select entirely. These phrases use a "breathing has already
# failed" frame that intent_route classifies as 'new_skill', reaching the
# keyword tier. Confirms keyword tier routes them to dbt_tipp [12] without
# being shadowed by grounding [1] or stop_technique [9].
#
# asyncio.wait_for patch forces semantic tier to TimeoutError so the test
# proves routing is via keyword only. skill_match_method=="keyword" is the
# primary assertion; the patch documents intent and guards against incidental
# semantic routing masking a missing keyword.
# ---------------------------------------------------------------------------

_DBTIPP_EN_PHRASES = [
    "breathing isn't working",
    "breathing is not enough",
    "too intense to breathe through",
    "need something stronger than breathing",
    "breathing won't help right now",
    "need an intense physical reset",
]

_DBTIPP_AR_PHRASES = [
    "التنفس ما يساعد",
    "التنفس ما كافي",
    "أحتاج شيء أقوى من التنفس",
    # "مشاعري أقوى من قدرتي" re-bucketed to grounding by C1 decision B.2 (2026-06-13):
    # generic overwhelm, no failed-first-line/arousal marker. See the dedicated test below
    # and docs/superpowers/governance/2026-06-13-overwhelm-routing-c1-conflict.md.
]


@pytest.mark.asyncio
@pytest.mark.parametrize("phrase", _DBTIPP_EN_PHRASES)
async def test_dbtipp_interim_en_phrase_routes_via_keyword(phrase):
    """Each simpler-technique-failure phrase must route to dbt_tipp via keyword tier.

    Negative assertion: if active_skill_id were grounding_5_4_3_2_1 or
    stop_technique, the phrase is shadowed by a lower-index skill -- keyword
    collision check has a false negative.
    """
    import asyncio
    from unittest.mock import patch

    state = _ss_state(message_en=phrase, primary_intent="new_skill")
    with patch("sage_poc.nodes.skill_select.asyncio.wait_for", side_effect=asyncio.TimeoutError):
        result = await skill_select_node(state)

    assert result["offered_skill_ids"][0] == "dbt_tipp", (
        f"Expected dbt_tipp offer, got {result.get('offered_skill_ids')!r} for phrase {phrase!r}. "
        "Phrase missing from dbt_tipp target_presentations or shadowed by lower-index skill."
    )
    assert result["skill_match_method"] == "keyword_offer", (
        f"Expected keyword_offer match, got {result['skill_match_method']!r}."
    )
    assert result["offered_skill_ids"][0] not in ("grounding_5_4_3_2_1", "stop_technique"), (
        f"Phrase {phrase!r} routed to a shadowing skill instead of dbt_tipp."
    )


# ---------------------------------------------------------------------------
# Appetite-loss disclosure cluster — semantic false-positive guard
#
# "i don't eat much" / "I haven't been eating" style phrases reached
# skill_select as new_skill intent (appetite loss is a specific symptom) and
# produced a box_breathing false-positive at score 0.4665 (threshold 0.4593,
# margin +0.0072). Root cause: BGE-M3 proximity between eating/breathing as
# co-occurring physiological processes. No therapeutic skill in the registry
# addresses appetite loss — correct destination is freeflow exploration.
#
# Fix: raise SEMANTIC_THRESHOLD so this cluster scores below it.
# These tests are the gate: they fail if the threshold regresses.
# ---------------------------------------------------------------------------

_APPETITE_DISCLOSURE_PHRASES = [
    "i think it's lack of eating, i don't eat much",  # observed production FP
    "I haven't been eating",
    "I barely eat",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("phrase", _APPETITE_DISCLOSURE_PHRASES)
async def test_appetite_disclosure_does_not_trigger_skill(phrase):
    """Appetite-loss disclosures must fall through to freeflow; no skill match expected.

    Root cause: "i don't eat much" scored 0.4665 against box_breathing via BGE-M3
    physiological proximity (eating/breathing). Fixed by SEMANTIC_EXCLUSION_WORDS
    word-boundary guard in corpus_constants.py — fires before Tier 2 semantic scoring.
    If this test fails, _SEMANTIC_EXCLUSION_RE in skill_select.py is not matching the
    phrase — check that "eat", "eating", "appetite", or "food" is present as a whole word.
    """
    state = _ss_state(message_en=phrase, primary_intent="new_skill")
    result = await skill_select_node(state)
    assert result["active_skill_id"] is None, (
        f"Appetite-loss phrase {phrase!r} matched {result['active_skill_id']!r} "
        f"(score={result.get('semantic_score')}) — SEMANTIC_EXCLUSION_WORDS guard missing or bypassed."
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("phrase", _DBTIPP_AR_PHRASES)
async def test_dbtipp_interim_ar_phrase_routes_via_keyword(phrase):
    """Each Arabic simpler-technique-failure phrase must route to dbt_tipp via keyword tier.

    Arabic keywords route via raw_message path (detected_language=='ar').

    C1/#15 TARGET NOTE: these phrases match dbt_tipp ONLY (no grounding overlap), so they
    are NOT the "overwhelmed"+"spinning" longest-match case behind #15 and the narrow
    tiebreak fix leaves them unchanged. Whether this acute-Arabic vocabulary belongs to
    dbt_tipp (signed 25634a3) vs grounding (C1) is a clinical-bucketing question for the
    same clinical lead handling #15; revisit if that adjudication re-buckets acute vocab.
    See docs/superpowers/governance/2026-06-13-overwhelm-routing-c1-conflict.md
    """
    import asyncio
    from unittest.mock import patch

    state = _ss_state(
        raw_message=phrase,
        message_en=phrase,
        detected_language="ar",
        primary_intent="new_skill",
    )
    with patch("sage_poc.nodes.skill_select.asyncio.wait_for", side_effect=asyncio.TimeoutError):
        result = await skill_select_node(state)

    # Arabic-exclusion gate (Option 1, 2026-06-13): match enters directly, not via offer.
    # Routing target (dbt_tipp) and the anti-shadowing guarantee are unchanged.
    assert result["active_skill_id"] == "dbt_tipp", (
        f"Expected dbt_tipp direct entry, got active={result.get('active_skill_id')!r} "
        f"offered={result.get('offered_skill_ids')!r} for Arabic phrase {phrase!r}. "
        "Phrase missing from dbt_tipp target_presentations or shadowed."
    )
    assert not result.get("offered_skill_ids"), "Arabic session must not offer"
    assert result["skill_match_method"] == "keyword", (
        f"Expected keyword match, got {result['skill_match_method']!r}."
    )
    assert result["active_skill_id"] not in ("grounding_5_4_3_2_1", "stop_technique"), (
        f"Arabic phrase {phrase!r} routed to a shadowing skill instead of dbt_tipp."
    )


# ── C1 acute-routing adjudication (clinical sign-off 2026-06-13) ───────────────
# Decision A: when grounding_5_4_3_2_1 AND dbt_tipp both keyword-match, prefer grounding
# (contraindication-free, lower activation) for ambiguous overwhelm. Decision B.2: the
# Arabic phrase مشاعري أقوى من قدرتي ("feelings stronger than my ability") re-buckets from
# dbt_tipp to grounding (generic overwhelm, no failed-first-line/arousal marker).
# See docs/superpowers/governance/2026-06-13-overwhelm-routing-c1-conflict.md

@pytest.mark.asyncio
async def test_c1_tiebreak_grounding_wins_when_both_match():
    """A: 'overwhelmed' (dbt_tipp, 11) + 'spinning' (grounding, 8) — longest-match would pick
    dbt_tipp; the C1 tiebreak routes to grounding instead. This is the unit-level proof of the
    same behavior asserted end-to-end by test_selects_grounding_for_overwhelmed_phrasing."""
    # Under R1 this routes via a consent OFFER (grounding listed first) at moderate intensity;
    # the C1 intent — grounding, not dbt_tipp, for ambiguous overwhelm — is what we assert,
    # mechanism-agnostic. (At acute intensity >= 8 it would be direct entry of grounding.)
    state = _ss_state(message_en="i feel completely overwhelmed, my head is spinning",
                      primary_intent="new_skill")
    result = await skill_select_node(state)
    assert _routed_skill(result) == "grounding_5_4_3_2_1", (
        f"C1 tiebreak failed: expected grounding, got {_routed_skill(result)!r}."
    )


@pytest.mark.asyncio
async def test_c1_tiebreak_does_not_affect_dbt_tipp_only_match():
    """A guard: 'i can't calm down' matches dbt_tipp ONLY (grounding's variant removed by
    25634a3), so the tiebreak must NOT fire — acute flooding still routes to dbt_tipp."""
    state = _ss_state(message_en="i can't calm down", primary_intent="new_skill")
    result = await skill_select_node(state)
    assert _routed_skill(result) == "dbt_tipp", (
        f"Tiebreak over-reached: 'i can't calm down' should stay dbt_tipp, got "
        f"{_routed_skill(result)!r}."
    )


@pytest.mark.asyncio
async def test_c1_b2_feelings_stronger_than_ability_routes_to_grounding():
    """B.2: مشاعري أقوى من قدرتي re-bucketed dbt_tipp -> grounding. Generic overwhelm with no
    failed-first-line/arousal marker routes to the lower-risk default under autonomous delivery."""
    import asyncio
    from unittest.mock import patch
    state = _ss_state(
        raw_message="مشاعري أقوى من قدرتي",
        message_en="مشاعري أقوى من قدرتي",
        detected_language="ar",
        primary_intent="new_skill",
    )
    with patch("sage_poc.nodes.skill_select.asyncio.wait_for", side_effect=asyncio.TimeoutError):
        result = await skill_select_node(state)
    assert result["active_skill_id"] == "grounding_5_4_3_2_1", (
        f"B.2 re-bucket failed: expected grounding, got {result['active_skill_id']!r}."
    )
    assert result["skill_match_method"] == "keyword"


# ── Acute-cluster bucket lock (clinical sign-off 2026-06-13/14) ────────────────
# DECIDED phrases only. Each (phrase, lang, expected_skill) is a signed routing decision; a
# move requires a clinical sign-off + an edit here, so neighbors cannot drift unreviewed.
# This deliberately EXCLUDES the still-pending audit phrases (overwhelmed family,
# unbearable/can't-handle/emotions-too-much, control-loss) — those await the lead's
# per-phrase ruling and must NOT be locked to today's un-adjudicated bucket. See
# docs/superpowers/governance/2026-06-13-overwhelm-routing-c1-conflict.md (audit worklist).
_BUCKET_LOCK = [
    # grounding — C1 ambiguous-overwhelm / signed re-buckets (B.2, B.3, EN/AR twins)
    ("مشاعري أقوى من قدرتي", "ar", "grounding_5_4_3_2_1"),   # B.2
    ("محتاج أهدى بسرعة", "ar", "grounding_5_4_3_2_1"),        # B.3
    ("مشاعري أقوى مني", "ar", "grounding_5_4_3_2_1"),         # B.2 twin
    ("مشاعري فوق طاقتي", "ar", "grounding_5_4_3_2_1"),        # B.2 twin
    ("need to calm down fast", "en", "grounding_5_4_3_2_1"),  # B.3 EN twin
    ("I need to calm down", "en", "grounding_5_4_3_2_1"),     # B.3 EN twin
    # dbt_tipp — retained: failed-first-line / explicit extremity / acute inability (25634a3)
    ("breathing isn't working", "en", "dbt_tipp"),
    ("need something stronger than breathing", "en", "dbt_tipp"),
    ("urge to act out", "en", "dbt_tipp"),
    ("I'm about to explode", "en", "dbt_tipp"),
    ("can't calm down", "en", "dbt_tipp"),                    # inability, signed 25634a3
    ("التنفس ما يساعد", "ar", "dbt_tipp"),                    # breathing-failed
    ("أشعر إني سأنفجر", "ar", "dbt_tipp"),                    # about to explode
]


@pytest.mark.asyncio
@pytest.mark.parametrize("phrase,lang,expected", _BUCKET_LOCK)
async def test_acute_cluster_bucket_lock(phrase, lang, expected):
    import asyncio
    from unittest.mock import patch
    state = _ss_state(
        message_en=phrase,
        raw_message=phrase if lang == "ar" else "",
        detected_language=lang,
        primary_intent="new_skill",
    )
    with patch("sage_poc.nodes.skill_select.asyncio.wait_for", side_effect=asyncio.TimeoutError):
        result = await skill_select_node(state)
    # Mechanism-agnostic: EN matches route via R1 offer at moderate intensity; AR via the
    # Arabic-exclusion direct path. The lock asserts the DESTINATION skill either way.
    assert _routed_skill(result) == expected, (
        f"Bucket lock violated: {phrase!r} expected {expected!r}, got "
        f"{_routed_skill(result)!r}. A move requires clinical sign-off + a governance entry."
    )


# ── Task 7: Rerank interface tests ────────────────────────────────────────────

def test_rerank_returns_best_candidate_from_stub():
    from sage_poc.nodes.skill_rerank import rerank_candidates
    candidates = [
        ("grief_loss", 0.51),
        ("interpersonal_effectiveness", 0.49),
        ("behavioral_activation", 0.45),
    ]
    result_id, result_score = rerank_candidates("I lost someone", candidates)
    assert result_id == "grief_loss"
    assert abs(result_score - 0.51) < 1e-9


def test_rerank_handles_single_candidate():
    from sage_poc.nodes.skill_rerank import rerank_candidates
    candidates = [("grief_loss", 0.48)]
    result_id, result_score = rerank_candidates("I am grieving", candidates)
    assert result_id == "grief_loss"
    assert abs(result_score - 0.48) < 1e-9


def test_rerank_raises_on_empty_candidates():
    import pytest
    from sage_poc.nodes.skill_rerank import rerank_candidates
    with pytest.raises(ValueError, match="at least one candidate"):
        rerank_candidates("hello", [])


# ── Task 8: Margin guard test ─────────────────────────────────────────────────

def test_margin_guard_routes_to_reranker_on_close_scores(monkeypatch):
    """When top-2 scores are within _RERANK_MARGIN, rerank_candidates must be called."""
    from sage_poc.nodes import skill_select as ss
    import sage_poc.nodes.skill_rerank as rerank_mod

    calls = []
    original = rerank_mod.rerank_candidates

    def mock_rerank(msg, candidates):
        calls.append((msg, candidates))
        return original(msg, candidates)

    monkeypatch.setattr(rerank_mod, "rerank_candidates", mock_rerank)

    # Simulate: worry_time=0.500, cognitive_restructuring=0.498 (diff=0.002 < 0.05 margin)
    def mock_match_sync(message_en, profile_context=""):
        skill_scores = {
            "worry_time": 0.500,
            "cognitive_restructuring": 0.498,
            "grief_loss": 0.420,
        }
        ranked = sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)
        best_sid, best_score = ranked[0]
        above = [(sid, sc) for sid, sc in ranked if sc >= ss.SEMANTIC_THRESHOLD]
        if len(above) >= 2:
            if above[0][1] - above[1][1] < ss._RERANK_MARGIN:
                from sage_poc.nodes.skill_rerank import rerank_candidates
                return rerank_candidates(message_en, above[:ss._RERANK_TOP_K])
        if above:
            return above[0]
        return None, best_score

    monkeypatch.setattr(ss, "_semantic_match_sync", mock_match_sync)
    result = ss._semantic_match_sync("catastrophizing about something", "")
    assert len(calls) == 1, "rerank_candidates should have been called once for close scores"
    assert result[0] == "worry_time"


# ── SF-1 Best-Match Scoring Tests ─────────────────────────────────────────────
# The catastrophizing case is the committed xfail below (TASK-3 gate).
# These three are ungated: they must go green when Task 2 best-match lands,
# without any clinical content from Tasks 3 or 5.

def make_state(**kwargs) -> dict:
    defaults = {
        "raw_message": kwargs.get("message_en", ""),
        "message_en": kwargs.get("message_en", ""),
        "detected_language": "en",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "active_skill_id": None,
        "active_step_id": None,
        "primary_intent": "new_skill",
        "intent_confidence": 1.0,
        "path": [],
        "therapeutic_profile": None,
    }
    return {**defaults, **kwargs}


@pytest.mark.slow
@pytest.mark.parametrize("phrase,expected_skill", [
    # self_compassion_break must win over cbt_thought_record [0]:
    # scb has "self-criticism" (14 chars); cbt has "self-blame" (10 chars).
    # Under first-match: cbt_thought_record wins (position 0). Under best-match: scb wins.
    ("I am lost in self-criticism and self-blame", "self_compassion_break"),
    # PST must win over worry_time [7]:
    # pst has "dont know what to do" (20 chars); wt has "cant stop worrying" (18 chars).
    # Under first-match: worry_time wins (position 7). Under best-match: PST wins.
    ("I cant stop worrying but I dont know what to do about this real situation", "problem_solving_therapy"),
    # ACT must win over worry_time [7]:
    # act has "avoiding things i care about" (28 chars); wt has "stuck in my head" (16 chars).
    # Under first-match: worry_time wins (position 7). Under best-match: ACT wins.
    ("I've been stuck in my head and avoiding things I care about", "act_psychological_flexibility"),
])
async def test_sf1_best_match_overrides_first_match(phrase: str, expected_skill: str):
    """SF-1: best-match scoring must return the most-specific keyword match,
    not the first registry-order match. Failure = first-match-wins is still active."""
    state = make_state(message_en=phrase)
    result = await skill_select_node(state)
    offered = result.get("offered_skill_ids") or [None]
    assert offered[0] == expected_skill, (
        f"SF-1 FAILURE: '{phrase[:60]}'\n"
        f"  Expected: {expected_skill}\n"
        f"  Got:      {offered[0]!r}  (method={result.get('skill_match_method')!r})\n"
        f"  Dominant-shadower failure — first-match-wins still routing to lower-index skill."
    )


# ── Phase 2 governance holds — pre-committed before implementation starts ─────
# These tests are xfail(strict=True): they must stay red until the corresponding
# clinical sign-off lands. strict=True means an unexpected XPASS (someone adding
# the content without sign-off) is a CI failure, not a silent green.
# DO NOT remove these markers or author the missing content without sign-off.


import pytest as _pytest


@_pytest.mark.slow
async def test_sf1_catastrophizing_routes_to_cognitive_restructuring_gated():
    """Catastrophizing language must route to cognitive_restructuring, not worry_time [7].
    Gated: depends on Task 3 removing catastrophizing from worry_time and adding it to
    cognitive_restructuring. Will be xfail until Task 3 clinical sign-off."""
    from sage_poc.nodes.skill_select import skill_select_node
    state = {
        "raw_message": "I keep catastrophizing about this situation and I cannot stop the thought spiral",
        "message_en": "I keep catastrophizing about this situation and I cannot stop the thought spiral",
        "detected_language": "en",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "active_skill_id": None,
        "active_step_id": None,
        "primary_intent": "new_skill",
        "intent_confidence": 1.0,
        "path": [],
        "therapeutic_profile": None,
    }
    result = await skill_select_node(state)
    assert (result.get("offered_skill_ids") or [None])[0] == "cognitive_restructuring"


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    reason=(
        "RT-4 trip-wire (governance/2026-06-25-rt4-matcher-evidence-general-chat-gate-shield.md). "
        "Affective loneliness phrasing misroutes at the matcher: Tier-1 keyword collision on "
        "'dont know what to do' -> problem_solving_therapy; if that did not fire, Tier-2 -> "
        "worry_time at 0.4609 (threshold 0.4593). The clinically-correct skill "
        "(behavioral_activation / self_compassion_break) is not selectable. This is EXPECTED to "
        "fail today. When the matcher is fixed (BA 'lonely' coverage, PST collision, threshold "
        "calibration) it will XPASS, and strict=True turns that XPASS into a hard failure -- the "
        "loud signal that the general_chat gate is now a redundant shield and is safe to revisit. "
        "Asserted at the skill_select layer, NOT end-to-end: end-to-end the gate routes this to "
        "freeflow and would pass for the wrong reason, masking the matcher."
    ),
)
async def test_loneliness_routes_to_connection_skill_not_problem_solving():
    """Trip-wire for RT-4 matcher correctness on relational-loneliness disclosure.

    Forces the message past the production general_chat gate (primary_intent='new_skill')
    so the assertion tests the MATCHER, not the gate. Do not relax to xfail(strict=False):
    a silent XPASS is exactly the missed signal this test exists to prevent.
    """
    msg = "I just feel lonely, I don't know what to do or how to cope"
    state = _ss_state(
        raw_message=msg,
        message_en=msg,
        primary_intent="new_skill",
        emotional_intensity=6,
    )
    result = await skill_select_node(state)
    routed = _routed_skill(result)
    assert routed in {"behavioral_activation", "self_compassion_break"}
    assert routed not in {"problem_solving_therapy", "worry_time"}


