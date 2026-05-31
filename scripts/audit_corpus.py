"""Corpus and skill integrity audit.

Run:   uv run python scripts/audit_corpus.py
Exit:  0 = all checks pass; 1 = failures (details printed to stdout)

Derives the AR work-list from the EN corpus at runtime. Explicit DEFERRED_AR
in corpus_constants.py is the single source of truth — no silent gaps.
"""
from __future__ import annotations
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sage_poc.corpus_constants import (
    CLUSTER_EXCLUSIONS,
    CRISIS_GATE,
    DEFERRED_AR,
    PLACEHOLDER_MARKERS,
    PRESENTATIONS_FLOOR_EXEMPTIONS,
    REQUIRED_POLICY_SIGNALS,
)
from sage_poc.clinical_clusters import CLINICAL_CLUSTERS
from sage_poc.prompts.composer import build_cultural_override_block

EN_DIR = ROOT / "data" / "knowledge_corpus" / "en"
AR_DIR = ROOT / "data" / "knowledge_corpus" / "ar"
SKILLS_DIR = ROOT / "src" / "sage_poc" / "skills"

_FAILURES: list[str] = []


def fail(msg: str) -> None:
    _FAILURES.append(msg)
    print(f"  FAIL: {msg}")


def ok(msg: str) -> None:
    print(f"  ✓ {msg}")


def check_kb() -> None:
    print("\n=== KB Article Checks ===")
    from sage_poc.knowledge.ingestion import validate_article_schema

    en_articles: dict[str, dict] = {}
    for f in sorted(EN_DIR.glob("*.json")):
        article = json.loads(f.read_text())
        try:
            validate_article_schema(article)
            en_articles[article["article_id"]] = article
            ok(f"EN schema: {f.name}")
        except ValueError as e:
            fail(f"EN schema error {f.name}: {e}")

    ar_articles: dict[str, dict] = {}
    if AR_DIR.exists():
        for f in sorted(AR_DIR.glob("*.json")):
            article = json.loads(f.read_text())
            try:
                validate_article_schema(article)
                ar_articles[article["article_id"]] = article
                ok(f"AR schema: {f.name}")
            except ValueError as e:
                fail(f"AR schema error {f.name}: {e}")

    for article_id, en_art in en_articles.items():
        if article_id in CRISIS_GATE:
            ok(f"crisis-gated: {article_id}")
        elif article_id in DEFERRED_AR:
            ok(f"deferred: {article_id} — {DEFERRED_AR[article_id]}")
        elif article_id not in ar_articles:
            fail(f"missing AR pair: {article_id} (not in DEFERRED_AR, not in CRISIS_GATE)")
        else:
            ok(f"AR pair exists: {article_id}")

    for article_id in ar_articles:
        if article_id not in en_articles:
            fail(f"orphan AR article: {article_id} has no EN counterpart")

    for article_id, ar_art in ar_articles.items():
        if article_id in en_articles:
            en_crisis = en_articles[article_id]["is_crisis_content"]
            ar_crisis = ar_art["is_crisis_content"]
            if en_crisis != ar_crisis:
                fail(
                    f"is_crisis_content mismatch {article_id}: "
                    f"EN={en_crisis}, AR={ar_crisis}"
                )
            if ar_crisis and not ar_art.get("requires_clinical_review"):
                fail(
                    f"crisis AR article {article_id} missing requires_clinical_review: true"
                )
            if ar_art.get("source_url") != en_articles[article_id].get("source_url"):
                fail(f"source_url mismatch: {article_id}")
            if ar_art.get("citation") != en_articles[article_id].get("citation"):
                fail(f"citation mismatch: {article_id}")

    for article_id, ar_art in ar_articles.items():
        content = json.dumps(ar_art, ensure_ascii=False)
        for marker in PLACEHOLDER_MARKERS:
            if marker in content:
                fail(f"placeholder '{marker}' in {article_id}")


def check_skills() -> None:
    print("\n=== Skill Checks ===")
    from sage_poc.skill_ids import SKILL_REGISTRY
    from sage_poc.skills.schema import load_skill

    for sid in SKILL_REGISTRY:
        if not (SKILLS_DIR / f"{sid}.json").exists():
            fail(f"SKILL_REGISTRY entry '{sid}' has no JSON file")

    for f in sorted(SKILLS_DIR.glob("*.json")):
        if f.stem not in SKILL_REGISTRY:
            fail(f"orphan skill JSON: {f.name} not in SKILL_REGISTRY")

    for sid in SKILL_REGISTRY:
        try:
            skill = load_skill(sid)
        except FileNotFoundError:
            fail(f"{sid}: JSON file missing (already caught above)")
            continue
        except Exception as e:
            fail(f"{sid}: load failed — {e}")
            continue

        if len(skill.steps) < 2:
            fail(f"{sid}: fewer than 2 steps ({len(skill.steps)})")

        signals = {r.condition.signal for r in skill.step_policy}
        for req in REQUIRED_POLICY_SIGNALS:
            if req not in signals:
                fail(f"{sid}: step_policy missing required signal '{req}'")

        for level in ("L1", "L2", "L3", "L4"):
            if level not in skill.escalation_matrix:
                fail(f"{sid}: escalation_matrix missing {level}")

        if "crisis" not in skill.escalation_matrix.get("L3", "").lower():
            fail(f"{sid}: L3 does not mention crisis")

        if sid not in PRESENTATIONS_FLOOR_EXEMPTIONS and len(skill.target_presentations) < 20:
            fail(
                f"{sid}: only {len(skill.target_presentations)} target_presentations "
                f"(minimum 20)"
            )
        elif sid in PRESENTATIONS_FLOOR_EXEMPTIONS:
            ok(f"{sid}: presentations floor exempt — {PRESENTATIONS_FLOOR_EXEMPTIONS[sid][:70]}")

        if not skill.semantic_description.strip():
            fail(f"{sid}: semantic_description is empty")

        if not skill.evidence_base.strip():
            fail(f"{sid}: evidence_base is empty (v7 §9.1: MANDATORY)")

        if skill.self_evolution != "manual_only":
            fail(
                f"{sid}: self_evolution = {skill.self_evolution!r} — "
                f"must be 'manual_only' (v7 v5 hardening)"
            )

        if skill.cultural_overrides:
            block = build_cultural_override_block(skill)
            if block is None:
                fail(
                    f"{sid}: cultural_overrides exceed the 200-word cap — "
                    f"they will be silently dropped at runtime. Condense them."
                )

        ok(f"skill valid: {sid}")


def check_cluster_coverage() -> None:
    print("\n=== Cluster Coverage ===")
    from sage_poc.skill_ids import SKILL_REGISTRY

    clustered = {sid for skills in CLINICAL_CLUSTERS.values() for sid in skills}

    for sid in SKILL_REGISTRY:
        if sid in CLUSTER_EXCLUSIONS:
            ok(f"excluded: {sid} — {CLUSTER_EXCLUSIONS[sid][:60]}")
        elif sid not in clustered:
            fail(
                f"{sid} not in any CLINICAL_CLUSTER and not in CLUSTER_EXCLUSIONS. "
                f"Add to a cluster or add to corpus_constants.CLUSTER_EXCLUSIONS with a reason."
            )
        else:
            cluster = next(c for c, skills in CLINICAL_CLUSTERS.items() if sid in skills)
            ok(f"{sid} → {cluster}")


def main() -> None:
    check_kb()
    check_skills()
    check_cluster_coverage()

    print(f"\n{'─' * 60}")
    if _FAILURES:
        print(f"AUDIT FAILED — {len(_FAILURES)} issue(s):")
        for f in _FAILURES:
            print(f"  • {f}")
        sys.exit(1)
    else:
        print("AUDIT PASSED — all checks green.")


if __name__ == "__main__":
    main()
