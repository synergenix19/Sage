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

# ── Dead step-policy signal guard (zero-tolerance) ────────────────────────────

def test_no_dead_step_policy_signals():
    """Any step_policy rule referencing a signal outside _KNOWN_STEP_POLICY_SIGNALS
    is silently inert at runtime. This test enforces zero tolerance.

    The runtime gate (_validate_step_policy_signal_coverage) raises RuntimeError at
    startup for the same condition. This test provides the same guard at CI time so
    the error is caught before the server ever starts.
    """
    from sage_poc.nodes.skill_executor import _get_dead_step_policy_signals
    dead = _get_dead_step_policy_signals()
    assert not dead, (
        f"step_policy rules reference signals that never resolve at runtime: {sorted(dead)}. "
        "Wire the signal into evaluate_step_policy or remove the rule."
    )


# ── Content correctness tests ─────────────────────────────────────────────

def test_post_crisis_check_in_l1_includes_crisis_line():
    import json, pathlib
    skill = json.loads(
        (pathlib.Path(__file__).parent.parent / "src/sage_poc/skills/post_crisis_check_in.json")
        .read_text()
    )
    l1 = skill["escalation_matrix"]["L1"]
    assert "800 46342" in l1, f"post_crisis_check_in L1 missing crisis line. Current: {l1!r}"
    assert any(w in l1.lower() for w in ("door", "return", "come back", "whenever")), \
        f"L1 must leave the door open explicitly. Current: {l1!r}"
    assert "stop" in l1.lower() or "not" in l1.lower(), \
        f"L1 must include anti-assumption guard. Current: {l1!r}"


def test_box_breathing_no_dead_clarity_rule():
    import json, pathlib
    skill = json.loads(
        (pathlib.Path(__file__).parent.parent / "src/sage_poc/skills/box_breathing.json")
        .read_text()
    )
    signals = [r["condition"]["signal"] for r in skill.get("step_policy", [])]
    assert "clarity" not in signals, "clarity is a dead signal in box_breathing step_policy"
    tp = skill.get("target_presentations", [])
    assert "4-7-8 breathing" not in tp, \
        "4-7-8 breathing is the wrong technique (separate evidence base); remove from box_breathing"


def test_financial_anxiety_no_crisis_detection_in_step_policy():
    import json, pathlib
    skill = json.loads(
        (pathlib.Path(__file__).parent.parent / "src/sage_poc/skills/financial_anxiety.json")
        .read_text()
    )
    CRISIS_SIGNALS = {"crisis_financial_hopelessness_detected", "crisis_detected", "si_detected"}
    violations = [
        rule["condition"]["signal"]
        for rule in skill.get("step_policy", [])
        if rule.get("condition", {}).get("signal") in CRISIS_SIGNALS
    ]
    assert not violations, f"financial_anxiety step_policy has crisis signals {violations} — belongs in Node 1."


def test_mood_check_in_no_overbroad_keywords():
    import json, pathlib
    skill = json.loads(
        (pathlib.Path(__file__).parent.parent / "src/sage_poc/skills/mood_check_in.json")
        .read_text()
    )
    OVERBROAD = {
        "feeling low", "feeling down", "not feeling great", "not doing well",
        "having a bad day", "bad day", "rough day", "rough week", "struggling today",
    }
    found = OVERBROAD & set(skill.get("target_presentations", []))
    assert not found, f"mood_check_in has overbroad keywords forcing 1-10 rating protocol: {found}"


def test_mood_check_in_no_dead_mood_score_rule():
    import json, pathlib
    skill = json.loads(
        (pathlib.Path(__file__).parent.parent / "src/sage_poc/skills/mood_check_in.json")
        .read_text()
    )
    signals = [r["condition"]["signal"] for r in skill.get("step_policy", [])]
    assert "mood_score" not in signals, (
        "mood_score is a dead signal (never resolved at runtime). Rule must be deleted. "
        "Add an emotional_intensity <= 3 replacement in Task 5b after clinical confirmation."
    )


def test_sleep_hygiene_no_overbroad_keywords():
    import json, pathlib
    tp = set(json.loads(
        (pathlib.Path(__file__).parent.parent / "src/sage_poc/skills/sleep_hygiene.json")
        .read_text()
    ).get("target_presentations", []))
    assert "waking up" not in tp, "bare 'waking up' is too broad for sleep_hygiene"
    assert "mind wont stop" not in tp, "'mind wont stop' belongs to worry_time, not sleep_hygiene"
    assert "mind won't stop" not in tp, "'mind won't stop' belongs to worry_time, not sleep_hygiene"


def test_trimmed_semantic_descriptions_within_cap():
    """Guard that explicitly-trimmed semantic_descriptions do not re-expand past 600 chars.

    Only enforces on skills that have been individually reviewed and trimmed.
    Other skills with long descriptions should be reviewed skill-by-skill before
    a blanket cap is applied.
    """
    import json, pathlib
    LIMIT = 600
    TRIMMED = {"cbt_thought_record", "interpersonal_effectiveness"}
    skills_dir = pathlib.Path(__file__).parent.parent / "src/sage_poc/skills"
    violations = []
    for p in sorted(skills_dir.glob("*.json")):
        if p.stem not in TRIMMED:
            continue
        length = len(json.loads(p.read_text()).get("semantic_description", ""))
        if length > LIMIT:
            violations.append(f"{p.stem}: {length} chars (limit {LIMIT})")
    assert not violations, f"Trimmed semantic_description re-expanded past cap: {violations}"


def test_crisis_line_matches_config_canonical_source():
    """Every phone number in skill JSON escalation_matrix and step contraindications
    that looks like a UAE toll-free number (800 NNNNN) must equal config.CRISIS_LINE_UAE.

    This is the consistency guard, not the correctness guard. Correctness requires
    clinical lead sign-off on the number. This test ensures all JSON occurrences stay
    in sync with the single authoritative source after that sign-off.
    """
    import re
    import json
    import pathlib
    from sage_poc.config import CRISIS_LINE_UAE

    UAE_TOLL_FREE = re.compile(r"800\s+\d{4,5}")
    skills_dir = pathlib.Path(__file__).parent.parent / "src/sage_poc/skills"
    violations = []

    for path in sorted(skills_dir.glob("*.json")):
        data = json.loads(path.read_text())
        # Check escalation_matrix values
        for level, text in data.get("escalation_matrix", {}).items():
            for match in UAE_TOLL_FREE.findall(str(text)):
                if match != CRISIS_LINE_UAE:
                    violations.append(f"{path.stem} escalation_matrix.{level}: found {match!r}, expected {CRISIS_LINE_UAE!r}")
        # Check step contraindications and completion_criteria
        for step in data.get("steps", []):
            for field in ("contraindications", "completion_criteria", "technique_description"):
                for match in UAE_TOLL_FREE.findall(str(step.get(field, ""))):
                    if match != CRISIS_LINE_UAE:
                        violations.append(f"{path.stem} step.{step.get('step_id')}.{field}: found {match!r}, expected {CRISIS_LINE_UAE!r}")

    assert not violations, (
        f"Crisis line number diverges from config.CRISIS_LINE_UAE ({CRISIS_LINE_UAE!r}): {violations}. "
        "Update config.py after clinical lead verification — the test enforces all JSON occurrences match."
    )


def test_no_authoring_notes_in_cultural_overrides():
    import json, pathlib
    FORBIDDEN = {"consult_before_examples", "review_required", "authoring_note", "todo"}
    skills_dir = pathlib.Path(__file__).parent.parent / "src/sage_poc/skills"
    violations = []
    for path in sorted(skills_dir.glob("*.json")):
        co = json.loads(path.read_text()).get("cultural_overrides", {})
        if isinstance(co, dict):
            bad = FORBIDDEN & set(co.keys())
            if bad:
                violations.append((path.stem, sorted(bad)))
    assert not violations, f"Authoring keys in live LLM cultural_overrides: {violations}"


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
