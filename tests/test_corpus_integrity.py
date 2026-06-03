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
