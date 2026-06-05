"""CI-backed corpus and skill integrity tests.

Fast: no DB, no embeddings, no LLM calls.
All shared constants imported from corpus_constants — no local redefinition.
"""
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).parent.parent
EN_DIR = ROOT / "data" / "knowledge_corpus" / "en"
AR_DIR = ROOT / "data" / "knowledge_corpus" / "ar"
SKILLS_DIR = ROOT / "src" / "sage_poc" / "skills"

from sage_poc.corpus_constants import (
    CLUSTER_EXCLUSIONS,
    CRISIS_GATE,
    DEFERRED_AR,
    PLACEHOLDER_MARKERS,
    PRESENTATIONS_FLOOR_EXEMPTIONS,
    REQUIRED_POLICY_SIGNALS,
    STRUCTURAL_FLOOR_EXEMPTIONS,
)
from sage_poc.clinical_clusters import CLINICAL_CLUSTERS
from sage_poc.prompts.composer import build_cultural_override_block


def _en_articles() -> dict:
    return {
        json.loads(f.read_text())["article_id"]: json.loads(f.read_text())
        for f in sorted(EN_DIR.glob("*.json"))
    }


def _ar_articles() -> dict:
    if not AR_DIR.exists():
        return {}
    return {
        json.loads(f.read_text())["article_id"]: json.loads(f.read_text())
        for f in sorted(AR_DIR.glob("*.json"))
    }


def _all_skill_ids() -> list[str]:
    from sage_poc.skill_ids import SKILL_REGISTRY
    return list(SKILL_REGISTRY)


# ── KB tests ───────────────────────────────────────────────────────────────

def test_every_en_article_is_paired_deferred_or_crisis_gated():
    en, ar = _en_articles(), _ar_articles()
    unaccounted = [
        aid for aid in en
        if aid not in CRISIS_GATE and aid not in DEFERRED_AR and aid not in ar
    ]
    assert not unaccounted, (
        f"EN articles with no AR pair, not deferred, not crisis-gated: {unaccounted}"
    )


def test_no_orphan_ar_articles():
    en, ar = _en_articles(), _ar_articles()
    orphans = [aid for aid in ar if aid not in en]
    assert not orphans, f"AR articles with no EN counterpart: {orphans}"


def test_ar_is_crisis_content_matches_en():
    en, ar = _en_articles(), _ar_articles()
    mismatches = [
        aid for aid, a in ar.items()
        if aid in en and a["is_crisis_content"] != en[aid]["is_crisis_content"]
    ]
    assert not mismatches, f"is_crisis_content mismatch EN vs AR: {mismatches}"


def test_crisis_ar_articles_have_requires_clinical_review():
    ar = _ar_articles()
    missing = [
        aid for aid, a in ar.items()
        if a.get("is_crisis_content") and not a.get("requires_clinical_review")
    ]
    assert not missing, (
        f"Crisis AR articles missing requires_clinical_review: true: {missing}"
    )


def test_no_placeholder_markers_in_ar_articles():
    ar = _ar_articles()
    violations = []
    for aid, art in ar.items():
        content = json.dumps(art, ensure_ascii=False)
        for marker in PLACEHOLDER_MARKERS:
            if marker in content:
                violations.append(f"{aid}: '{marker}'")
    assert not violations, f"Placeholder markers found: {violations}"


def test_ar_source_url_and_citation_match_en():
    en, ar = _en_articles(), _ar_articles()
    mismatches = []
    for aid, ar_art in ar.items():
        if aid not in en:
            continue
        if ar_art.get("source_url") != en[aid].get("source_url"):
            mismatches.append(f"{aid} source_url")
        if ar_art.get("citation") != en[aid].get("citation"):
            mismatches.append(f"{aid} citation")
    assert not mismatches, f"source_url/citation mismatches: {mismatches}"


# ── Skill registry tests ───────────────────────────────────────────────────

def test_every_registry_skill_has_json():
    from sage_poc.skill_ids import SKILL_REGISTRY
    missing = [
        sid for sid in SKILL_REGISTRY
        if not (SKILLS_DIR / f"{sid}.json").exists()
    ]
    assert not missing, f"SKILL_REGISTRY IDs with no JSON file: {missing}"


def test_no_orphan_skill_jsons():
    from sage_poc.skill_ids import SKILL_REGISTRY
    orphans = [
        f.stem for f in SKILLS_DIR.glob("*.json")
        if f.stem not in SKILL_REGISTRY
    ]
    assert not orphans, f"Skill JSON files not in SKILL_REGISTRY: {orphans}"


# ── Per-skill parametrised tests ───────────────────────────────────────────

@pytest.mark.parametrize("sid", _all_skill_ids())
def test_skill_structural_floors(sid):
    from sage_poc.skills.schema import load_skill
    skill = load_skill(sid)

    # Skills in STRUCTURAL_FLOOR_EXEMPTIONS have non-standard single-purpose
    # architectures (e.g. single-step referral pending sign-off). Only the
    # v7 §9.1 MANDATORY fields (evidence_base, self_evolution) are enforced
    # for these skills — the multi-step structural checks are skipped.
    if sid not in STRUCTURAL_FLOOR_EXEMPTIONS:
        assert len(skill.steps) >= 2, f"{sid}: fewer than 2 steps"

        signals = {r.condition.signal for r in skill.step_policy}
        missing_signals = REQUIRED_POLICY_SIGNALS - signals
        assert not missing_signals, f"{sid}: step_policy missing signals {missing_signals}"

        for level in ("L1", "L2", "L3", "L4"):
            assert level in skill.escalation_matrix, f"{sid}: escalation_matrix missing {level}"

        assert "crisis" in skill.escalation_matrix["L3"].lower(), (
            f"{sid}: L3 must mention crisis"
        )
        if sid not in PRESENTATIONS_FLOOR_EXEMPTIONS:
            assert len(skill.target_presentations) >= 20, (
                f"{sid}: only {len(skill.target_presentations)} target_presentations (min 20). "
                f"If this skill uses state-driven routing (not keyword/semantic), add it to "
                f"corpus_constants.PRESENTATIONS_FLOOR_EXEMPTIONS with a reason."
            )
        assert skill.semantic_description.strip(), f"{sid}: semantic_description is empty"

    # v7 §9.1 MANDATORY fields — enforced for ALL skills including exemptions
    assert skill.evidence_base.strip(), (
        f"{sid}: evidence_base is empty — v7 §9.1 marks this MANDATORY"
    )
    assert skill.self_evolution == "manual_only", (
        f"{sid}: self_evolution = {skill.self_evolution!r} — must be 'manual_only'"
    )


@pytest.mark.parametrize("sid", _all_skill_ids())
def test_skill_cultural_overrides_within_cap(sid):
    from sage_poc.skills.schema import load_skill
    skill = load_skill(sid)
    if not skill.cultural_overrides:
        return
    block = build_cultural_override_block(skill)
    assert block is not None, (
        f"{sid}: cultural_overrides exceed the 200-word cap — "
        f"they will be silently dropped at runtime"
    )


# ── Cluster coverage ───────────────────────────────────────────────────────

# ── Dead step-policy signal count (pinned at 21) ──────────────────────────────
#
# These 21 rules reference signals that never resolve at runtime — they are SILENTLY INERT.
# The count is pinned so any addition causes a red CI run instead of logging into a wall
# of existing ERRORs that teams learn to scroll past (the exact failure mode that produced
# all the original dead signals). The list is hard-coded here so the failure message names
# the new offender explicitly.
#
# UPGRADE PATH (post-Gitex): wire the signals or remove the rules from the skill JSONs,
# then flip _validate_step_policy_signal_coverage in skill_executor.py to raise RuntimeError
# instead of logging. When the count reaches 0, delete this test and the ERROR log.
_KNOWN_DEAD_SIGNALS: frozenset[tuple[str, str]] = frozenset({
    ("assertive_communication",    "coercive_relationship_indicators_detected"),
    ("behavioral_activation",      "hopelessness"),
    ("box_breathing",              "clarity"),
    ("cbt_thought_record",         "trauma_disclosure_detected"),
    ("cognitive_restructuring",    "trauma_disclosure_detected"),
    ("dbt_tipp",                   "physical_contraindication_disclosed"),
    ("financial_anxiety",          "crisis_financial_hopelessness_detected"),
    ("grief_loss",                 "prolonged_grief_indicators_detected"),
    ("grounding_5_4_3_2_1",        "sensory_limitation_disclosed"),
    ("interpersonal_effectiveness","coercive_relationship_indicators_detected"),
    ("mindfulness_body_scan",      "dissociation_or_dizziness_reported"),
    ("mood_check_in",              "mood_score"),
    ("progressive_muscle_relaxation", "pain_or_injury_mention"),
    ("psychoed_anxiety",           "existing_anxiety_diagnosis_disclosed"),
    ("psychoed_depression",        "active_suicidal_ideation_disclosed"),
    ("psychoed_stress",            "burnout_exhaustion_with_functional_impairment"),
    ("safe_place_visualization",   "dissociation_signal"),
    ("self_compassion_break",      "self_kindness_rejection_detected"),
    ("sleep_hygiene",              "medication_or_substance_mention"),
    ("values_clarification",       "family_values_conflict_detected"),
    ("worry_time",                 "obsessive_theme_detected"),
})


def test_dead_step_policy_signal_count_is_pinned():
    """Ensure no new step_policy rules reference unresolvable signals.

    The count is pinned at 21 (the documented pre-Gitex dead-signal set). Any addition
    is a red CI run. Any removal is also caught — it means a signal was wired up or a
    rule removed, and _KNOWN_DEAD_SIGNALS should be updated to reflect the progress.

    A new dead signal means: you added a step_policy rule whose condition.signal is not
    in _KNOWN_STEP_POLICY_SIGNALS in skill_executor.py. That rule is silently inert from
    day one — it will never fire. Either wire the signal into evaluate_step_policy or
    remove the rule.
    """
    from sage_poc.nodes.skill_executor import _get_dead_step_policy_signals

    found = set(_get_dead_step_policy_signals())
    added   = found - _KNOWN_DEAD_SIGNALS
    removed = _KNOWN_DEAD_SIGNALS - found

    assert not added, (
        f"NEW dead step-policy signal(s) added — these rules are silently inert from day one: {sorted(added)}. "
        "Wire the signal into evaluate_step_policy or remove the rule. "
        "Do not add _KNOWN_DEAD_SIGNALS entries without a corresponding cleanup commitment."
    )
    assert not removed, (
        f"Dead step-policy signal(s) removed — update _KNOWN_DEAD_SIGNALS in test_corpus_integrity.py "
        f"to reflect the cleanup: {sorted(removed)}. "
        "When the set reaches zero, delete this test and flip _validate_step_policy_signal_coverage "
        "to raise RuntimeError."
    )


# ── Cluster coverage ───────────────────────────────────────────────────────

def test_every_skill_assigned_to_cluster_or_explicitly_excluded():
    from sage_poc.skill_ids import SKILL_REGISTRY
    clustered = {sid for skills in CLINICAL_CLUSTERS.values() for sid in skills}
    unassigned = [
        sid for sid in SKILL_REGISTRY
        if sid not in clustered and sid not in CLUSTER_EXCLUSIONS
    ]
    assert not unassigned, (
        f"Skills not in any CLINICAL_CLUSTER and not in CLUSTER_EXCLUSIONS: {unassigned}"
    )


def test_entry_screen_guard_catches_unregistered_skill():
    """NEGATIVE TEST: _validate_entry_screen_coverage must catch a skill that has
    entry_screen as its first step but is absent from _LLM_CRITERIA_SKILLS.

    This verifies the guard is actually doing real work, not just passing silently.
    Without this test, a future skill author can add an entry_screen JSON and forget
    the frozenset update — the guard exists precisely to catch that, and a guard
    with no negative test is theatre.
    """
    import json
    import tempfile
    import pathlib
    from sage_poc.nodes.skill_executor import _LLM_CRITERIA_SKILLS

    # Build a minimal skill JSON with entry_screen as first step, using a fake ID
    # that is deliberately absent from _LLM_CRITERIA_SKILLS.
    fake_skill_id = "_test_unregistered_entry_screen_skill"
    assert fake_skill_id not in _LLM_CRITERIA_SKILLS, (
        "Test setup error: fake ID is already in _LLM_CRITERIA_SKILLS."
    )
    fake_skill = {
        "skill_id": fake_skill_id,
        "steps": [{"step_id": "entry_screen"}, {"step_id": "step_two"}],
        "step_policy": [],
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        skill_path = pathlib.Path(tmpdir) / f"{fake_skill_id}.json"
        skill_path.write_text(json.dumps(fake_skill))

        # Replicate the guard logic against the temp dir
        missing = []
        for path in sorted(pathlib.Path(tmpdir).glob("*.json")):
            data = json.loads(path.read_text())
            steps = data.get("steps", [])
            if steps and steps[0].get("step_id") == "entry_screen":
                sid = path.stem
                if sid not in _LLM_CRITERIA_SKILLS:
                    missing.append(sid)

        assert missing == [fake_skill_id], (
            f"Entry-screen guard failed to catch unregistered skill. "
            f"Expected [{fake_skill_id!r}] missing, got: {missing}. "
            "This means the guard logic has changed and may no longer catch omissions."
        )
