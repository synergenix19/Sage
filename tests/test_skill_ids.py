def test_skill_ids_importable_and_complete():
    """skill_ids.py must exist and export SKILL_REGISTRY as a plain list.

    This module is the canonical source of skill IDs. It must have no
    heavy dependencies so server.py can import it without triggering the
    numpy / sentence-transformers import chain.
    """
    from sage_poc.skill_ids import SKILL_REGISTRY

    assert isinstance(SKILL_REGISTRY, list), "SKILL_REGISTRY must be a list"
    assert len(SKILL_REGISTRY) == 27, f"Expected 27 skills, got {len(SKILL_REGISTRY)}"

    # Original 5 skills
    assert "cbt_thought_record" in SKILL_REGISTRY
    assert "grounding_5_4_3_2_1" in SKILL_REGISTRY
    assert "sleep_hygiene" in SKILL_REGISTRY
    assert "post_crisis_check_in" in SKILL_REGISTRY
    assert "dbt_tipp" in SKILL_REGISTRY

    # Track A: 7 new psychoed/values/communication skills (Sprint 5)
    assert "psychoed_anxiety" in SKILL_REGISTRY
    assert "psychoed_depression" in SKILL_REGISTRY
    assert "psychoed_stress" in SKILL_REGISTRY
    assert "values_clarification" in SKILL_REGISTRY
    assert "assertive_communication" in SKILL_REGISTRY
    assert "self_compassion_break" in SKILL_REGISTRY
    assert "mindfulness_body_scan" in SKILL_REGISTRY

    # Phase 2 sprint (2026-05-31): 4 new skills SK-021 to SK-024
    assert "cognitive_restructuring" in SKILL_REGISTRY
    assert "interpersonal_effectiveness" in SKILL_REGISTRY
    assert "financial_anxiety" in SKILL_REGISTRY
    assert "grief_loss" in SKILL_REGISTRY

    assert all(isinstance(sid, str) for sid in SKILL_REGISTRY), \
        "All SKILL_REGISTRY entries must be strings"
    assert len(SKILL_REGISTRY) == len(set(SKILL_REGISTRY)), \
        "SKILL_REGISTRY must not contain duplicates"


def test_skill_select_still_exports_skill_registry():
    """skill_select.py must re-export SKILL_REGISTRY for backward compatibility."""
    from sage_poc.nodes.skill_select import SKILL_REGISTRY as sr_registry
    from sage_poc.skill_ids import SKILL_REGISTRY as ids_registry
    assert sr_registry is ids_registry, (
        "skill_select.SKILL_REGISTRY must be the same object as skill_ids.SKILL_REGISTRY — "
        "skill_select should import from skill_ids, not define its own copy"
    )
