# tests/test_clinical_flag_lifecycle.py
#
# Tests covering the clinical flag lifecycle design:
#
# T2: escalating_distress does not persist across turns via set-union (M1 fix)
# T8: persisted_clinical_flags from therapeutic_profile seeds session clinical_flags

import pytest
from sage_poc.nodes.safety_check import safety_check_node


def _make_state(**kwargs) -> dict:
    defaults = {
        "raw_message":           "",
        "detected_language":     "en",
        "message_en":            "",
        "is_safe":               True,
        "crisis_flags":          [],
        "clinical_flags":        [],
        "new_clinical_flags_turn": [],
        "crisis_state":          "none",
        "s7_result":             None,
        "s7_method":             None,
        "distress_trajectory":   [],
        "engagement_trajectory": [],
        "conversation_summary":  None,
        "code_switching":        False,
        "primary_intent":        None,
        "secondary_intent":      None,
        "intent_confidence":     0.0,
        "emotional_intensity":   5,
        "engagement":            5,
        "active_skill_id":       None,
        "active_step_id":        None,
        "executed_step_id":      None,
        "step_instruction":      None,
        "skill_match_method":    None,
        "semantic_score":        None,
        "escalation_triggered":  None,
        "gate_path":             None,
        "response_en":           None,
        "response":              None,
        "path":                  [],
        "turn_count":            0,
        "conversation_history":  [],
        "therapeutic_profile":   None,
        "knowledge_passages":    [],
        "knowledge_abstain":     False,
        "knowledge_source":      "",
    }
    return {**defaults, **kwargs}


# ── T2: escalating_distress does not persist via set-union (M1 fix) ──────────

class TestT2EscalatingDistressMustNotPersist:
    """M1 fix: escalating_distress is a computed signal and must not carry
    forward via clinical_flags set-union when distress subsequently drops.

    Previously: safety_check_node union'd all prior clinical_flags including
    escalating_distress, causing it to accumulate permanently. The fix
    explicitly excludes escalating_distress from the carry-forward set and
    recomputes it from the current distress trajectory each turn.
    """

    async def test_escalating_distress_added_during_high_distress_streak(self):
        """Baseline: escalating_distress is added when the trajectory crosses the threshold."""
        state = _make_state(
            raw_message="I cannot cope, everything is falling apart.",
            emotional_intensity=8,
            distress_trajectory=[7, 7],   # + 8 this turn = [7, 7, 8] — all ≥ 6 → escalating
        )
        result = await safety_check_node(state)
        assert "escalating_distress" in result["clinical_flags"], (
            "escalating_distress must be added during a high-distress streak"
        )

    async def test_escalating_distress_cleared_when_distress_drops(self):
        """Core M1 regression: after a high-distress turn, clinical_flags from
        the checkpoint carry escalating_distress into the next turn. When distress
        drops, the node must NOT retain it via set-union — it must be cleared."""
        # Turn 1: high distress streak
        state1 = _make_state(
            raw_message="I cannot cope, everything is falling apart.",
            emotional_intensity=8,
            distress_trajectory=[7, 7],
        )
        result1 = await safety_check_node(state1)
        assert "escalating_distress" in result1["clinical_flags"]

        # Turn 2: simulate LangGraph checkpoint carrying clinical_flags forward.
        # Distress drops significantly — escalating_distress must NOT persist.
        state2 = _make_state(
            raw_message="I went for a walk and feel a bit better.",
            emotional_intensity=3,
            # clinical_flags from the checkpoint includes escalating_distress
            clinical_flags=result1["clinical_flags"],
            # trajectory carries the prior values; current turn appends 3
            distress_trajectory=[7, 7, 8],
        )
        result2 = await safety_check_node(state2)
        assert "escalating_distress" not in result2["clinical_flags"], (
            "escalating_distress must be cleared when distress drops — "
            "it is a computed signal, not a persistent clinical fact"
        )

    async def test_other_clinical_flags_still_carry_forward(self):
        """Category A flags (substance_use etc.) must still accumulate across turns."""
        state = _make_state(
            raw_message="I went for a walk and feel a bit better.",
            emotional_intensity=3,
            distress_trajectory=[3, 3, 3],
            # Simulate a prior-turn substance_use flag in checkpoint
            clinical_flags=["substance_use"],
        )
        result = await safety_check_node(state)
        assert "substance_use" in result["clinical_flags"], (
            "Legitimate Category A flags must carry forward across turns"
        )


# ── T8: cross-session persisted_clinical_flags seeds clinical_flags ───────────

class TestT8CrossSessionFlagSeeding:
    """At session start (clinical_flags empty, checkpoint empty), flags stored in
    therapeutic_profile.persisted_clinical_flags must seed the session's clinical_flags.

    This implements cross-session clinical context persistence: if substance_use was
    detected and persisted in a prior session, it informs prompt framing on the next session.
    """

    async def test_persisted_flag_from_profile_seeds_clinical_flags(self):
        """A flag in therapeutic_profile.persisted_clinical_flags must appear in
        clinical_flags even when the checkpoint is empty (first turn of new session)."""
        state = _make_state(
            raw_message="I went for a walk today and felt peaceful.",
            clinical_flags=[],   # empty checkpoint — new session
            therapeutic_profile={"persisted_clinical_flags": ["substance_use"]},
        )
        result = await safety_check_node(state)
        assert "substance_use" in result["clinical_flags"], (
            "substance_use must be seeded from therapeutic_profile.persisted_clinical_flags "
            "into clinical_flags at session start"
        )

    async def test_seeding_is_idempotent_on_subsequent_turns(self):
        """On subsequent turns, the persisted flag is already in the LangGraph checkpoint;
        unioning it again from therapeutic_profile must produce the same set (idempotent)."""
        state = _make_state(
            raw_message="I went for a walk today.",
            clinical_flags=["substance_use"],   # already in checkpoint
            therapeutic_profile={"persisted_clinical_flags": ["substance_use"]},
        )
        result = await safety_check_node(state)
        # substance_use should appear exactly once (set union, not append)
        flag_count = result["clinical_flags"].count("substance_use")
        assert flag_count == 1, "Duplicate flag from seeding — set union must deduplicate"

    async def test_no_seeding_when_therapeutic_profile_is_none(self):
        """When there's no therapeutic profile (unauthenticated or new user),
        clinical_flags must remain empty if no flags are detected this turn."""
        state = _make_state(
            raw_message="I went for a walk today and felt peaceful.",
            clinical_flags=[],
            therapeutic_profile=None,
        )
        result = await safety_check_node(state)
        # Only substance-neutral message — no clinical flags expected
        assert "substance_use" not in result["clinical_flags"]

    async def test_multiple_persisted_flags_all_seeded(self):
        """All flags in persisted_clinical_flags are seeded, not just the first one."""
        state = _make_state(
            raw_message="Everything feels okay today.",
            clinical_flags=[],
            therapeutic_profile={
                "persisted_clinical_flags": ["trauma_indicator", "medication_mention"]
            },
        )
        result = await safety_check_node(state)
        assert "trauma_indicator"   in result["clinical_flags"]
        assert "medication_mention" in result["clinical_flags"]
