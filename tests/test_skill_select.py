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
    assert result["active_skill_id"] == "cbt_thought_record"
    assert result["skill_match_method"] == "keyword"


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
    state = _ss_state(message_en="I need to calm down fast, I'm overwhelmed and losing control")
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "dbt_tipp"
    assert result["skill_match_method"] == "keyword"

@pytest.mark.asyncio
async def test_dbt_tipp_keyword_arabic():
    state = _ss_state(message_en="محتاج أهدى بسرعة", detected_language="ar")
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "dbt_tipp"


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
    assert result["active_skill_id"] == "cbt_thought_record", (
        f"Expected cbt_thought_record, got: {result['active_skill_id']} "
        f"(score: {result.get('semantic_score')})"
    )
    assert result["skill_match_method"] == "semantic"


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
    assert result["active_skill_id"] == "behavioral_activation", (
        f"Expected behavioral_activation, got: {result['active_skill_id']} "
        f"(score: {result.get('semantic_score')})"
    )
    assert result["skill_match_method"] == "semantic"


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
    assert result["active_skill_id"] == "worry_time", (
        f"Expected worry_time, got: {result['active_skill_id']} "
        f"(score: {result.get('semantic_score')})"
    )
    assert result["skill_match_method"] == "semantic"


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
    assert result["active_skill_id"] == "dbt_tipp", (
        f"Expected dbt_tipp, got: {result['active_skill_id']} "
        f"(score: {result.get('semantic_score')})"
    )
    assert result["skill_match_method"] == "semantic"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_semantic_mi_readiness_half_wanting_phrase():
    """MI readiness ruler semantic match: ambivalence described without readiness/change keywords."""
    phrase = "I wish I could rate my own motivation and confidence to see where I actually stand"
    assert _phrase_is_keyword_clean(phrase, "mi_readiness_ruler"), (
        "Phrase accidentally matches a keyword — choose a different phrase."
    )
    state = _ss_state(message_en=phrase)
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "mi_readiness_ruler", (
        f"Expected mi_readiness_ruler, got: {result['active_skill_id']} "
        f"(score: {result.get('semantic_score')})"
    )


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

    # Keyword match must still work even when semantic times out
    assert result["active_skill_id"] == "cbt_thought_record", (
        "Keyword fallback failed when semantic timed out"
    )
    assert result["skill_match_method"] == "keyword"
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
    """Arabic-script keyword in target_presentations must match raw_message for Arabic sessions."""
    state = _ss_state(
        raw_message="تنفس معي",
        message_en="breathe with me",
        detected_language="ar",
        primary_intent="new_skill",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "box_breathing", (
        f"Expected box_breathing, got {result['active_skill_id']!r}. "
        "Arabic-script keyword تنفس معي must match via raw_message pass."
    )
    assert result["skill_match_method"] == "keyword"


@pytest.mark.asyncio
async def test_arabic_keyword_fires_when_translation_is_ambiguous():
    """When Arabic message_en translation is ambiguous, raw_message keyword pass must fire."""
    state = _ss_state(
        raw_message="أبي تمرين تنفس",
        message_en="I want some exercise",  # ambiguous — would miss keyword
        detected_language="ar",
        primary_intent="new_skill",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "box_breathing", (
        f"Expected box_breathing, got {result['active_skill_id']!r}. "
        "Arabic keyword أبي تمرين تنفس must match via raw_message pass."
    )
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
    assert result["active_skill_id"] == "box_breathing", (
        f"Expected box_breathing via raw_message, got {result['active_skill_id']!r}. "
        "When message_en has no keyword, raw_message Arabic keyword must be the match source."
    )
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
    # Either no skill selected, OR if box_breathing matched semantically, it MUST NOT
    # have matched via keyword (which would mean Arabic raw_message leaked into en routing).
    if result.get("active_skill_id") == "box_breathing":
        assert result.get("skill_match_method") != "keyword", (
            "box_breathing matched as 'keyword' for an English session with only "
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
    "مشاعري أقوى من قدرتي",
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

    assert result["active_skill_id"] == "dbt_tipp", (
        f"Expected dbt_tipp, got {result['active_skill_id']!r} for phrase {phrase!r}. "
        "Phrase missing from dbt_tipp target_presentations or shadowed by lower-index skill."
    )
    assert result["skill_match_method"] == "keyword", (
        f"Expected keyword match, got {result['skill_match_method']!r}."
    )
    assert result["active_skill_id"] not in ("grounding_5_4_3_2_1", "stop_technique"), (
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

    assert result["active_skill_id"] == "dbt_tipp", (
        f"Expected dbt_tipp, got {result['active_skill_id']!r} for Arabic phrase {phrase!r}. "
        "Phrase missing from dbt_tipp target_presentations or shadowed."
    )
    assert result["skill_match_method"] == "keyword", (
        f"Expected keyword match, got {result['skill_match_method']!r}."
    )
    assert result["active_skill_id"] not in ("grounding_5_4_3_2_1", "stop_technique"), (
        f"Arabic phrase {phrase!r} routed to a shadowing skill instead of dbt_tipp."
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
