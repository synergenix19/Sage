"""Shared fixtures for Experiment 4.4 test suite."""
import pytest
from unittest.mock import AsyncMock, patch

from sage_poc.skills.schema import load_skill


@pytest.fixture
def cbt():
    return load_skill("cbt_thought_record")


@pytest.fixture
def dbt_tipp():
    return load_skill("dbt_tipp")


@pytest.fixture
def mi():
    return load_skill("mi_readiness_ruler")


@pytest.fixture
def ba():
    return load_skill("behavioral_activation")


@pytest.fixture
def sleep():
    return load_skill("sleep_hygiene")


@pytest.fixture
def grounding():
    return load_skill("grounding_5_4_3_2_1")


@pytest.fixture
def mood():
    return load_skill("mood_check_in")


def make_executor_state(
    skill_id: str,
    step_id: str,
    message_en: str = "I have been thinking about this and it feels difficult to manage.",
    emotional_intensity: int = 5,
    engagement: int = 7,
    resistance_history: list | None = None,
    engagement_trajectory: list | None = None,
    new_clinical_flags_turn: list | None = None,
    clinical_flags: list | None = None,
    therapeutic_profile: dict | None = None,
    crisis_state: str = "none",
    **kwargs,
) -> dict:
    """Build a minimal SageState dict for skill_executor_node tests."""
    return {
        "active_skill_id":         skill_id,
        "active_step_id":          step_id,
        "message_en":              message_en,
        "raw_message":             message_en,
        "emotional_intensity":     emotional_intensity,
        "engagement":              engagement,
        "resistance_history":      list(resistance_history or []),
        "engagement_trajectory":   list(engagement_trajectory or []),
        "resistance_score":        None,
        "new_clinical_flags_turn": list(new_clinical_flags_turn or []),
        "clinical_flags":          list(clinical_flags or []),
        "therapeutic_profile":     therapeutic_profile or {},
        "crisis_state":            crisis_state,
        "s7_result":               None,
        "path":                    [],
        **kwargs,
    }


@pytest.fixture
def no_resistance():
    """Patch Phase 2 resistance scoring to return None (skip LLM call)."""
    with patch(
        "sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
        new=AsyncMock(return_value=None),
    ):
        yield


@pytest.fixture
def resistance_score_4():
    """Patch Phase 2 resistance scoring to return 4 (below threshold)."""
    with patch(
        "sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
        new=AsyncMock(return_value=4),
    ):
        yield


@pytest.fixture
def resistance_score_8():
    """Patch Phase 2 resistance scoring to return 8 (above threshold > 6)."""
    with patch(
        "sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
        new=AsyncMock(return_value=8),
    ):
        yield
