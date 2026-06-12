# tests/test_cross_task_interactions.py
#
# Phase C cross-task interaction tests verifying that the Task 1–8 fixes
# compose correctly when their code paths touch in the same invocation.
#
# C-1: Staleness + info_request (Task 2 × Task 3)
# C-2: Re-escalation + S3 timeout (Task 4 × Task 1)
# C-3: Criteria evaluator + step_policy rule priority (Task 7 × Task 8)
# C-4: LLM criteria fallback for non-target skill (Task 6 × Task 8)
# C-5: Staleness + re-escalation flag (Task 2 × Task 4)

import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock


# ── Helpers ───────────────────────────────────────────────────────────────────


def _checkpoint(active_skill_id=None, crisis_state="none", hours_ago=0):
    last_turn_at = (
        datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    ).isoformat()
    return {
        "last_turn_at":    last_turn_at,
        "active_skill_id": active_skill_id,
        "crisis_state":    crisis_state,
    }


def _ss_state(**overrides):
    """Minimal SageState for skill_select_node tests."""
    base = {
        "raw_message":         "",
        "detected_language":   "en",
        "message_en":          "",
        "is_safe":             True,
        "crisis_flags":        [],
        "clinical_flags":      [],
        "crisis_state":        "none",
        "s7_result":           None,
        "s7_method":           None,
        "primary_intent":      None,
        "secondary_intent":    None,
        "intent_confidence":   1.0,
        "emotional_intensity": 5,
        "engagement":          7,
        "active_skill_id":     None,
        "active_step_id":      None,
        "executed_step_id":    None,
        "step_instruction":    None,
        "escalation_triggered": None,
        "gate_path":           None,
        "response_en":         None,
        "response":            None,
        "path":                [],
        "turn_count":          0,
        "conversation_history": [],
        "skill_match_method":  None,
        "semantic_score":      None,
        "distress_trajectory": [],
        "code_switching":      False,
    }
    base.update(overrides)
    return base


def _crisis_node_state(**overrides):
    """Minimal SageState for _crisis_response_node tests."""
    base = {
        "raw_message":          "I want to hurt myself",
        "detected_language":    "en",
        "message_en":           "I want to hurt myself",
        "is_safe":              False,
        "crisis_flags":         ["si_explicit"],
        "clinical_flags":       [],
        "crisis_state":         "none",
        "s7_result":            None,
        "s7_method":            None,
        "primary_intent":       "crisis",
        "secondary_intent":     None,
        "intent_confidence":    1.0,
        "emotional_intensity":  9,
        "engagement":           3,
        "active_skill_id":      None,
        "active_step_id":       None,
        "executed_step_id":     None,
        "step_instruction":     None,
        "escalation_triggered": None,
        "gate_path":            None,
        "response_en":          None,
        "response":             None,
        "path":                 ["safety_check"],
        "turn_count":           1,
        "conversation_history": [],
        "skill_match_method":   None,
        "semantic_score":       None,
        "distress_trajectory":  [],
        "code_switching":       False,
    }
    base.update(overrides)
    return base


def _mock_crisis_rules_engine():
    """Return a MagicMock that behaves like rules_engine.evaluate for crisis_content."""
    fired_rule = MagicMock()
    fired_rule.action = {"response_text": "Please reach out for support. UAE: 800 46342."}
    fired_rule.rule_id = "crisis_en_001"
    mock_result = MagicMock()
    mock_result.fired = [fired_rule]
    mock_engine = MagicMock()
    mock_engine.evaluate.return_value = mock_result
    return mock_engine


# ── C-1: Staleness + info_request during stale monitoring (Task 2 × Task 3) ──


class TestC1StalenessAndInfoRequest:
    """When _stale_skill_overrides resets crisis_state to 'none' (crisis-only stale),
    and skill_select_node is invoked with primary_intent='info_request', the
    info_request guard (Task 3, A-1 fix) must fire before the monitoring block
    regardless of the incoming crisis_state value.

    This verifies: Task 2 (CSM-3: crisis-only stale correctly returns {'crisis_state': 'none'})
    composes with Task 3 (A-1: info_request guard is at the TOP of skill_select_node).
    """

    def test_crisis_only_stale_returns_crisis_state_none_only(self):
        """_stale_skill_overrides with active_skill_id=None and crisis_state=monitoring
        must return only {'crisis_state': 'none'} — no skill keys in overrides."""
        from sage_poc.server_helpers import _stale_skill_overrides

        snap = _checkpoint(active_skill_id=None, crisis_state="monitoring", hours_ago=5)
        overrides = _stale_skill_overrides(snap)

        assert overrides.get("crisis_state") == "none", (
            "Crisis-only stale session must reset crisis_state to 'none'"
        )
        assert "active_skill_id" not in overrides, (
            "No active_skill_id to clear — must not appear in overrides"
        )
        assert "stale_skill_id" not in overrides, (
            "Task 3: info_request guard result must not include stale_skill_id"
        )

    async def test_info_request_guard_fires_before_monitoring_block(self):
        """skill_select_node with primary_intent='info_request' and crisis_state='monitoring'
        must preserve active_skill_id in the checkpoint and must NOT include stale_skill_id.

        When a skill is active, skill_select omits active_skill_id from its return dict so
        the checkpoint value is preserved — the skill resumes on the turn after the info lookup.
        """
        from sage_poc.nodes.skill_select import skill_select_node

        # Simulate state after staleness cleared crisis_state to 'none',
        # but also verify the stronger case: even if crisis_state='monitoring'
        # remains (e.g., non-stale session), info_request guard fires first.
        state = _ss_state(
            message_en="what is the crisis line number",
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
        assert "active_step_id" not in result, (
            "info_request with active skill must NOT write active_step_id"
        )
        assert result["skill_match_method"] is None, (
            "info_request guard must not attempt skill matching"
        )
        assert "stale_skill_id" not in result, (
            "Task 3 A-1 fix: result dict must not include stale_skill_id key"
        )

    async def test_info_request_bypasses_monitoring_even_with_active_post_crisis_skill(self):
        """Even when crisis_state='none' (stale-reset), info_request routes away from skill."""
        from sage_poc.nodes.skill_select import skill_select_node

        # This is the post-stale-reset scenario: crisis_state='none', but user asks info
        state = _ss_state(
            message_en="tell me about the crisis resources",
            crisis_state="none",
            primary_intent="info_request",
        )
        result = await skill_select_node(state)

        assert result["active_skill_id"] is None
        assert "stale_skill_id" not in result, (
            "info_request guard path must not include stale_skill_id in its return dict"
        )


# ── C-2: Re-escalation + S3 logging (Task 4 × Task 1) ────────────────────────


class TestC2ReEscalationAndS3Timeout:
    """When a message triggers crisis AND S3 times out (B-2 fix logs WARNING),
    the system must:
    1. Log the S3 timeout (Task 1 / B-2): WARNING level, not silent pass.
    2. Set re_escalation_within_monitoring=True when prior crisis_state='monitoring' (Task 4).

    These are independent paths in different nodes but compose in the same turn flow.
    The critical ordering guarantee: is_reescalation is computed from state.get('crisis_state')
    BEFORE any S3 call has a chance to modify state (S3 runs in safety_check_node,
    re_escalation is computed at the top of _crisis_response_node using the crisis_state
    from the graph checkpoint — S3 cannot change that value).
    """

    async def test_s3_timeout_logs_not_silent(self):
        """B-2 fix: S3 asyncio.TimeoutError must emit an ERROR log, not silently pass.

        The log level is ERROR (not WARNING) so that log-based alerting fires when S3
        is unavailable — S3 degradation to S1-only is a safety-relevant event.
        """
        from sage_poc.nodes.safety_check import safety_check_node
        import logging

        state = _ss_state(
            raw_message="I want to hurt myself",
            message_en="I want to hurt myself",
            crisis_state="monitoring",
            active_skill_id="post_crisis_check_in",
            active_step_id="acknowledge_and_check",
            engagement_trajectory=[],
            therapeutic_profile={},
        )

        with patch("sage_poc.nodes.safety_check.asyncio.wait_for",
                   side_effect=asyncio.TimeoutError), \
             patch("sage_poc.nodes.safety_check.evaluate_s7",
                   new_callable=AsyncMock,
                   return_value=("STILL_DISTRESSED", "keyword")), \
             patch("sage_poc.nodes.safety_check._log") as mock_log:
            result = await safety_check_node(state)

        mock_log.error.assert_called_once()
        error_args = mock_log.error.call_args[0]
        assert error_args, "S3 timeout must emit an error log with a message"
        assert "S3" in error_args[0], "Error log must mention S3 so on-call knows which layer timed out"

    async def test_s3_timeout_does_not_crash_turn(self):
        """S3 timeout must not prevent safety_check_node from returning a valid result.
        S1 crisis detection must still function (is_safe=False for crisis phrase)."""
        from sage_poc.nodes.safety_check import safety_check_node

        state = _ss_state(
            raw_message="I want to hurt myself",
            message_en="I want to hurt myself",
            crisis_state="monitoring",
            active_skill_id="post_crisis_check_in",
            active_step_id="acknowledge_and_check",
            engagement_trajectory=[],
            therapeutic_profile={},
        )

        with patch("sage_poc.nodes.safety_check.asyncio.wait_for",
                   side_effect=asyncio.TimeoutError), \
             patch("sage_poc.nodes.safety_check.evaluate_s7",
                   new_callable=AsyncMock,
                   return_value=("STILL_DISTRESSED", "keyword")):
            result = await safety_check_node(state)

        # S1 lexicon should still catch the crisis phrase even without S3
        assert result["is_safe"] is False, (
            "S1 crisis detection must still function when S3 times out"
        )
        assert len(result["crisis_flags"]) > 0, (
            "S1 must still populate crisis_flags when S3 is unavailable"
        )

    async def test_re_escalation_true_when_prior_crisis_state_is_monitoring(self):
        """Task 4 / CSM-2: _crisis_response_node must set re_escalation_within_monitoring=True
        when the incoming crisis_state is 'monitoring'. This is computed from state BEFORE
        any modification — S3 timeout in the prior safety_check turn cannot affect it."""
        from sage_poc.graph import _crisis_response_node

        state = _crisis_node_state(crisis_state="monitoring")
        mock_engine = _mock_crisis_rules_engine()

        with patch("sage_poc.rules.engine", mock_engine), \
             patch("sage_poc.graph.asyncio.create_task"):
            result = await _crisis_response_node(state)

        assert result.get("re_escalation_within_monitoring") is True, (
            "Task 4: re_escalation_within_monitoring must be True when prior crisis_state was 'monitoring'"
        )
        assert result.get("crisis_state") == "monitoring", (
            "_crisis_response_node must set crisis_state back to 'monitoring'"
        )

    async def test_is_reescalation_computed_before_s3_can_alter_state(self):
        """Ordering invariant: is_reescalation reads state.get('crisis_state') at the
        top of _crisis_response_node — no S3 call inside this node can change it.

        This test verifies the composition: when prior crisis_state='monitoring',
        re_escalation_within_monitoring=True regardless of what S3 did in the
        preceding safety_check turn."""
        from sage_poc.graph import _crisis_response_node

        # S3 ran (in safety_check) and timed out — it did not add 's3_semantic' to
        # crisis_flags, but it also cannot change crisis_state in the checkpoint.
        # The crisis_state is 'monitoring' in the checkpoint, passed into the node.
        state = _crisis_node_state(
            crisis_state="monitoring",
            crisis_flags=["si_explicit"],  # S1 fired; S3 timed out (no s3_semantic flag)
        )
        mock_engine = _mock_crisis_rules_engine()

        with patch("sage_poc.rules.engine", mock_engine), \
             patch("sage_poc.graph.asyncio.create_task"):
            result = await _crisis_response_node(state)

        # re_escalation must be True because crisis_state was 'monitoring' in state
        assert result.get("re_escalation_within_monitoring") is True, (
            "S3 timeout in safety_check cannot retroactively change crisis_state "
            "in the checkpoint; re_escalation must still reflect the 'monitoring' checkpoint"
        )


# ── C-3: Criteria evaluator + step_policy rule priority (Task 7 × Task 8) ─────


class TestC3CriteriaEvaluatorAndRulePriority:
    """When emotional_intensity=3 triggers the deterministic 'advance' rule in
    post_crisis_check_in (acknowledge_and_check → bridge_or_close), Task 7's
    _criteria_blocked sentinel is NOT set (the rule fired first with action='advance',
    not 'stay'). Therefore the LLM evaluator from Task 8 is NOT called.

    This verifies the Phase 1 deterministic rule priority over the criteria
    evaluation path: deterministic rules always pre-empt LLM criteria evaluation.
    """

    async def test_deterministic_rule_preempts_llm_criteria_evaluator(self):
        """emotional_intensity=3 fires the advance rule in post_crisis_check_in;
        _criteria_blocked is never set, so LLM evaluator is never called."""
        from sage_poc.nodes.skill_executor import skill_executor_node

        state = {
            "active_skill_id":         "post_crisis_check_in",
            "active_step_id":          "acknowledge_and_check",
            "message_en":              "ok",   # single word — heuristic would block
            "emotional_intensity":     3,       # <= 4 → advance rule fires in Phase 1
            "engagement":              7,
            "new_clinical_flags_turn": [],
            "resistance_history":      [],
            "engagement_trajectory":   [],
            "s7_result":               None,
            "therapeutic_profile":     {},
            "path":                    [],
            "crisis_state":            "monitoring",
        }

        with patch(
            "sage_poc.nodes.criteria_eval._call_llm",
            new_callable=AsyncMock,
        ) as mock_llm:
            result = await skill_executor_node(state)

        mock_llm.assert_not_called(), (
            "Task 8: LLM evaluator must not be called when a deterministic Phase 1 rule fires"
        )
        assert result["active_step_id"] == "bridge_or_close", (
            "Deterministic advance rule must advance step to bridge_or_close"
        )

    def test_evaluate_step_policy_advance_rule_does_not_set_criteria_blocked(self):
        """evaluate_step_policy must not include _criteria_blocked when a deterministic
        advance rule fires — the result action is 'advance', not 'stay'."""
        from sage_poc.nodes.skill_executor import evaluate_step_policy
        from sage_poc.skills.schema import load_skill

        skill = load_skill("post_crisis_check_in")
        result = evaluate_step_policy(
            skill=skill,
            current_step_id="acknowledge_and_check",
            emotional_intensity=3,
            engagement=7,
            message_en="ok",  # single word
        )

        assert result["action"] == "advance", (
            "emotional_intensity=3 must fire the advance rule"
        )
        assert result.get("_criteria_blocked") is None, (
            "Task 7: _criteria_blocked must NOT be set when a rule fires — only when "
            "no rule fires AND heuristic blocks"
        )
        assert result["next_step_id"] == "bridge_or_close"

    async def test_llm_evaluator_called_only_when_no_rule_fires_and_heuristic_blocks(self):
        """Contrast: emotional_intensity=6 (above advance threshold <= 4, below validate_only > 7)
        means no deterministic rule fires. Single-word response → heuristic blocks →
        _criteria_blocked=True → LLM evaluator IS called."""
        from sage_poc.nodes.skill_executor import skill_executor_node

        state = {
            "active_skill_id":         "post_crisis_check_in",
            "active_step_id":          "acknowledge_and_check",
            "message_en":              "ok",   # single word
            "emotional_intensity":     6,       # no rule fires (not <= 4, not > 7)
            "engagement":              7,
            "new_clinical_flags_turn": [],
            "resistance_history":      [],
            "engagement_trajectory":   [],
            "s7_result":               None,
            "therapeutic_profile":     {},
            "path":                    [],
            "crisis_state":            "monitoring",
        }

        with patch(
            "sage_poc.nodes.criteria_eval._call_llm",
            new_callable=AsyncMock,
            return_value="no",
        ) as mock_llm, patch(
            "sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await skill_executor_node(state)

        mock_llm.assert_called_once(), (
            "Task 8: LLM evaluator must be called when no rule fires AND heuristic blocks"
        )
        # LLM said no, step stays
        assert result["active_step_id"] == "acknowledge_and_check"


# ── C-4: LLM criteria fallback for non-target skill (Task 6 × Task 8) ─────────


class TestC4NonTargetSkillNeverUsesLlm:
    """When skill_id is NOT in _LLM_CRITERIA_SKILLS (box_breathing) and the
    heuristic blocks (_criteria_blocked=True on 'inhale' step with single-word reply),
    the LLM evaluator must NOT be called. The step stays without LLM consultation.

    This verifies Task 8's guard: `if p1_criteria_blocked and skill_id in _LLM_CRITERIA_SKILLS`.
    """

    async def test_non_target_skill_does_not_call_llm_evaluator(self):
        """box_breathing is not in _LLM_CRITERIA_SKILLS; heuristic block must not
        trigger LLM evaluation — step stays on 'inhale'."""
        from sage_poc.nodes.skill_executor import skill_executor_node, _LLM_CRITERIA_SKILLS

        assert "box_breathing" not in _LLM_CRITERIA_SKILLS, (
            "Precondition: box_breathing must not be in _LLM_CRITERIA_SKILLS"
        )

        state = {
            "active_skill_id":         "box_breathing",
            "active_step_id":          "inhale",
            "message_en":              "ok",    # single word → heuristic blocks
            "emotional_intensity":     5,        # no step_policy rule fires (not > 7)
            "engagement":              7,
            "new_clinical_flags_turn": [],
            "resistance_history":      [],
            "engagement_trajectory":   [],
            "s7_result":               None,
            "therapeutic_profile":     {},
            "path":                    [],
            "crisis_state":            "none",
        }

        with patch(
            "sage_poc.nodes.criteria_eval.evaluate_completion_criteria",
            new_callable=AsyncMock,
        ) as mock_eval, patch(
            "sage_poc.nodes.criteria_eval._call_llm",
            new_callable=AsyncMock,
        ) as mock_llm:
            result = await skill_executor_node(state)

        mock_eval.assert_not_called(), (
            "Task 8: evaluate_completion_criteria must not be called for non-target skills"
        )
        mock_llm.assert_not_called(), (
            "Task 6: _call_llm must not be called for non-target skills"
        )
        assert result["active_step_id"] == "inhale", (
            "Non-target skill: step must stay on 'inhale' when heuristic blocks"
        )
        assert result["active_skill_id"] == "box_breathing"

    async def test_non_target_skill_single_word_stays_without_llm(self):
        """Even if non-target skill has completion_criteria, heuristic blocks and
        LLM is never consulted — step stays."""
        from sage_poc.nodes.skill_executor import skill_executor_node
        from sage_poc.nodes.skill_executor import _LLM_CRITERIA_SKILLS

        # grounding_5_4_3_2_1 is also not in _LLM_CRITERIA_SKILLS
        assert "grounding_5_4_3_2_1" not in _LLM_CRITERIA_SKILLS

        state = {
            "active_skill_id":         "grounding_5_4_3_2_1",
            "active_step_id":          "sight",  # first step
            "message_en":              "ok",      # single word
            "emotional_intensity":     5,
            "engagement":              7,
            "new_clinical_flags_turn": [],
            "resistance_history":      [],
            "engagement_trajectory":   [],
            "s7_result":               None,
            "therapeutic_profile":     {},
            "path":                    [],
            "crisis_state":            "none",
        }

        with patch(
            "sage_poc.nodes.criteria_eval._call_llm",
            new_callable=AsyncMock,
        ) as mock_llm:
            result = await skill_executor_node(state)

        mock_llm.assert_not_called(), (
            "Task 8: LLM must not be called for grounding_5_4_3_2_1 (non-target skill)"
        )


# ── C-5: Staleness + re-escalation flag (Task 2 × Task 4) ────────────────────


class TestC5StalenessAndReEscalationFlag:
    """After a 4h+ gap with crisis_state='monitoring' and active_skill_id=None,
    _stale_skill_overrides resets crisis_state to 'none'. If crisis then fires
    again, _crisis_response_node sees crisis_state='none' (cleared by staleness)
    and sets re_escalation_within_monitoring=False — NOT True.

    This verifies that staleness correctly 'forgives' the monitoring state, and
    subsequent crisis is treated as a fresh first crisis, not a re-escalation.
    """

    def test_crisis_only_stale_resets_crisis_state_to_none(self):
        """_stale_skill_overrides: monitoring + no active skill + 5h gap → crisis_state=none."""
        from sage_poc.server_helpers import _stale_skill_overrides

        snap = _checkpoint(active_skill_id=None, crisis_state="monitoring", hours_ago=5)
        overrides = _stale_skill_overrides(snap)

        assert overrides.get("crisis_state") == "none", (
            "Task 2 (CSM-3): Stale monitoring session with no active skill must reset "
            "crisis_state to 'none'"
        )
        # No skill keys in overrides since active_skill_id was None
        assert "active_skill_id" not in overrides
        assert "stale_skill_id" not in overrides

    async def test_post_stale_crisis_sets_re_escalation_false(self):
        """After stale override cleared crisis_state to 'none', if crisis fires again,
        _crisis_response_node must set re_escalation_within_monitoring=False.

        The user's monitoring state was 'forgiven' by the staleness check — from the
        system's perspective, this is a fresh crisis turn, not a re-escalation."""
        from sage_poc.graph import _crisis_response_node

        # State reflects what the graph receives after _stale_skill_overrides applied:
        # crisis_state is now 'none' (was 'monitoring', reset by stale check).
        # User then sends a new crisis message → safety_check fires → crisis_response_node invoked.
        state = _crisis_node_state(
            crisis_state="none",  # cleared by _stale_skill_overrides
            crisis_flags=["si_explicit"],
        )
        mock_engine = _mock_crisis_rules_engine()

        with patch("sage_poc.rules.engine", mock_engine), \
             patch("sage_poc.graph.asyncio.create_task"):
            result = await _crisis_response_node(state)

        assert result.get("re_escalation_within_monitoring") is False, (
            "Task 4: When staleness cleared crisis_state to 'none', subsequent crisis "
            "is NOT a re-escalation (re_escalation_within_monitoring must be False)"
        )
        assert result.get("crisis_state") == "monitoring", (
            "crisis_state must be set to 'monitoring' after crisis response"
        )

    async def test_re_escalation_true_only_when_stale_did_not_reset(self):
        """Contrast: when no stale reset occurred (gap < 4h, crisis_state='monitoring'
        persists), re_escalation_within_monitoring must be True."""
        from sage_poc.graph import _crisis_response_node

        # No stale reset — crisis_state stayed 'monitoring' because gap was short
        state = _crisis_node_state(
            crisis_state="monitoring",
            crisis_flags=["si_explicit"],
        )
        mock_engine = _mock_crisis_rules_engine()

        with patch("sage_poc.rules.engine", mock_engine), \
             patch("sage_poc.graph.asyncio.create_task"):
            result = await _crisis_response_node(state)

        assert result.get("re_escalation_within_monitoring") is True, (
            "Task 4: When crisis_state was 'monitoring' (not stale-reset), "
            "re_escalation_within_monitoring must be True"
        )

    def test_stale_reset_two_hour_gap_does_not_trigger(self):
        """A 2h gap is below the 4h threshold; stale override must return empty {}
        even if crisis_state='monitoring' with no active skill."""
        from sage_poc.server_helpers import _stale_skill_overrides

        snap = _checkpoint(active_skill_id=None, crisis_state="monitoring", hours_ago=2)
        overrides = _stale_skill_overrides(snap)

        assert overrides == {}, (
            "A 2h gap is below the 4h threshold; stale override must return {} "
            "(crisis_state must not be reset prematurely)"
        )


# ── Crisis offer-clearing contract ────────────────────────────────────────────


async def test_crisis_response_clears_pending_offer():
    """Crisis bypasses the consent gate; a pending offer must not survive the turn.
    declined_skills intentionally DOES survive (preference state, not workflow position)."""
    from sage_poc.graph import _crisis_response_node

    state = _crisis_node_state(
        offered_skill_ids=["worry_time"],
        declined_skills=["box_breathing"],
    )
    mock_engine = _mock_crisis_rules_engine()

    with patch("sage_poc.rules.engine", mock_engine), \
         patch("sage_poc.graph.asyncio.create_task"):
        result = await _crisis_response_node(state)

    assert result["offered_skill_ids"] is None
    assert "declined_skills" not in result
