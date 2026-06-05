# Arabic KB + 4 New Skills Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship 20 Arabic KB article pairs (all non-crisis, non-deferred EN articles), add 4 new structured skills (cognitive_restructuring, interpersonal_effectiveness, financial_anxiety, grief_loss), close the cultural-override silent-drop class, and validate routing integrity before Gitex. Six non-crisis EN articles are explicitly deferred this sprint (therapy-001, trauma-001, grounding-001, breathing-001, cbt-001, cbt-002). Four crisis articles (crisis-001 through crisis-004) are gated behind dual-clinician sign-off. The four new skills reach **staging** on green CI. All four require a **production gate** (v7 §6.3 Draft → Review → Clinically Approved → Published) before any user exposure. grief_loss and financial_anxiety additionally require behavioural probes for ideation-adjacent scenarios and a MARBERT recall check. Skills may not enter production as JSON alone — v7 §9.1 requires evidence_base and clinician sign-off.

> **BLOCKER — inventory reconciliation:** Before authoring any skill JSON (Task 9), confirm all four skills appear in the approved SageAI Skills & Knowledge Base inventory (SageAI_Skills_Knowledge_Base.docx, 97 items / 28 structured skills). If a skill is already in the approved inventory, reference its item number in the commit message. If it is net-new, it must enter the CMS draft → clinical-approval workflow before landing as JSON — it cannot bypass that workflow by being added to `skill_ids.py` directly.

**Architecture:** Content-only expansion — no graph, node, or API changes. Arabic articles land in `data/knowledge_corpus/ar/`. Four new skills follow the `Skill` Pydantic schema in `src/sage_poc/skills/schema.py`. The integrity audit (Task 0) derives the AR work-list from the EN corpus at runtime — no hand-maintained counts. All shared constants and the cluster map live in dedicated side-effect-free modules imported by both the audit script and CI tests.

**Tech Stack:** Python 3.12, uv, pytest, asyncpg (pgvector), BGE-M3 (BAAI/bge-m3), JSON skill schema

**Verified repo contracts:**
- `skill_select_node(state)` is `async`, returns state-patch dict with `active_skill_id`. No standalone `select_skill(text)` helper. Task 12 tests use `await skill_select_node(make_full_state(...))`.
- `make_full_state(**overrides)` in `test_routing.py` accepts `message_en`, `primary_intent`, `intent_confidence` as kwargs.
- `load_skill(sid)` raises `FileNotFoundError` for missing files.
- `result["skill_id"]` in `run_scenario` holds the scenario key, not the resolved skill id. `assert_override_injected` resolves through `SCENARIO_SKILL_MAP`.
- Composer override block format (confirmed at `composer.py:367–374`): header `"SKILL-SPECIFIC CULTURAL CONTEXT:"`, lines `f"- {v}"` (no leading spaces), budget `_CULTURAL_OVERRIDE_BUDGET_WORDS = 200`, measured by `count_words` (whitespace split). Audit must call the composer's own builder function — not reconstruct the format.
- `SentenceTransformer` is imported at module level in `calibrate_threshold.py` (line 31) but the model is only instantiated inside a function (line 142). Importing the module is safe but pulls in the `sentence_transformers` library. Extract `CLINICAL_CLUSTERS` to a side-effect-free module to avoid this in CI.
- `knowledge_articles` table, `chunk_text` column — confirmed in `ingestion.py`.
- `Skill.evidence_base` is `str` (required, no default) — `.strip()` accessor is correct. Pydantic raises `ValidationError` if the field is absent; the audit assertion catches empty-but-present strings.
- `Skill.self_evolution` is `Literal["manual_only"]` with `default="manual_only"`. Pydantic enforces the Literal — any value other than `"manual_only"` fails at `load_skill` time before the audit assertion runs. The assertion `skill.self_evolution == "manual_only"` is invariant documentation, not the enforcement mechanism.
- **Baseline (2026-05-31):** 0 of 20 existing skills violate either assertion. Zero remediation scope — new assertions are net-additive.
- **Tier 1 keyword routing** uses exact substring matching: `for keyword in skill.target_presentations: if keyword.lower() in message`. First match in SKILL_REGISTRY order wins. `cbt_thought_record` is index 0 and owns `"negative thoughts"` in its target_presentations. `cognitive_restructuring.target_presentations` must NOT include `"negative thoughts"` or any other phrase already in `cbt_thought_record`'s list — collision gives cbt_thought_record the trigger every time. Routing tests must use messages containing exact phrases from the target skill's target_presentations only.

---

## Execution Order

**Phase 1 — runs now, no external dependencies:**
```
Task 0  (shared modules + audit script)  ← first; makes counts authoritative
Task 1  (override builder extract)       ← makes the cap check correct
Task 2  (injection assertion fix)        ← standalone; ships any time
Task 3  (bidi DB round-trip)             ← unblocks Tasks 5–6
Task 4  (behavioural probes)             ← gates Tasks 4A/4B/4C
Task 4A (fix assertive gender)           ← only if PROBE-G1 ≤ 3
Task 4B (fix psychoed_depression)        ← only if PROBE-D1 ≤ 3
Task 4C (fix values_clarification)       ← only if PROBE-V1 ≤ 3
Tasks 5–6 (AR KB articles, 20 total)    ← parallel after Task 3
Task 7  (ingest AR articles)             ← after Tasks 5–6 + placeholder guard
```

**Phase 2 — blocked until inventory item numbers are supplied (Task 9 Step 0):**
```
Task 8  (4 new skill JSONs)              ← blocked on inventory go/no-go
Task 9  (register + tests)               ← after Task 8
Task 10 (clinical clusters module)       ← after Task 9
Task 11 (threshold recalibration)        ← after Task 10; REQUIRED before merge
Task 12 (routing regression)             ← after Task 11
STAGING GATE  — all 5 CI checks green
PRODUCTION GATE — all 4 new skills: clinician content sign-off (§6.3); grief_loss + financial_anxiety also: behavioural probes + MARBERT ≥95% recall check (§16.1)
GATED   (crisis AR articles)            ← never auto; dual-clinician sign-off only
```

> **Executor:** Phase 1 is ready to run. Phase 2 cannot start until the user supplies `SageAI_Skills_Knowledge_Base.docx` or all four inventory item numbers. Surface this dependency at the end of Task 7 rather than discovering it at Task 8 Step 0.

---

## File Map

| Action | Path | Purpose |
|--------|------|---------|
| Create | `src/sage_poc/corpus_constants.py` | Single source of truth: DEFERRED_AR, CRISIS_GATE, PLACEHOLDER_MARKERS, REQUIRED_POLICY_SIGNALS, CLUSTER_EXCLUSIONS |
| Create | `src/sage_poc/clinical_clusters.py` | Single source of truth: CLINICAL_CLUSTERS — side-effect-free, no model imports |
| Modify | `scripts/calibrate_threshold.py` | Import CLINICAL_CLUSTERS from clinical_clusters.py instead of defining it |
| Modify | `src/sage_poc/prompts/composer.py` | Extract `build_cultural_override_block(skill)` helper |
| Create | `scripts/audit_corpus.py` | Derives AR work-list from EN corpus; no hand counts |
| Create | `tests/test_corpus_integrity.py` | CI-backed assertions; imports from corpus_constants and clinical_clusters |
| Modify | `scripts/smoke_cultural_overrides.py` | Injection assertion + 3 probe scenarios |
| Modify | `src/sage_poc/skills/assertive_communication.json` | If PROBE-G1 ≤ 3 |
| Modify | `src/sage_poc/skills/psychoed_depression.json` | If PROBE-D1 ≤ 3 |
| Modify | `src/sage_poc/skills/values_clarification.json` | If PROBE-V1 ≤ 3 |
| Create | `data/knowledge_corpus/ar/` — 20 JSON files | Non-crisis Arabic KB articles |
| Create | `src/sage_poc/skills/cognitive_restructuring.json` | |
| Create | `src/sage_poc/skills/interpersonal_effectiveness.json` | |
| Create | `src/sage_poc/skills/financial_anxiety.json` | |
| Create | `src/sage_poc/skills/grief_loss.json` | |
| Modify | `src/sage_poc/skill_ids.py` | Add 4 new IDs |
| Modify | `tests/test_skill_ids.py` | Update count 20→24; add 4 assertions |
| Modify | `tests/test_skill_schema.py` | Add 4 schema load tests |
| Modify | `tests/test_routing.py` | Add 8 async disambiguation routing tests |

---

## Task 0: Shared Constants + Clinical Clusters Modules

Before writing the audit script, extract the shared constants and the cluster map into dedicated modules. Both `audit_corpus.py` and `test_corpus_integrity.py` import from these — no duplication, no drift.

**Files:**
- Create: `src/sage_poc/corpus_constants.py`
- Create: `src/sage_poc/clinical_clusters.py`

- [ ] **Step 1: Create `src/sage_poc/corpus_constants.py`**

```python
"""Shared constants for corpus and skill integrity checks.

Imported by scripts/audit_corpus.py and tests/test_corpus_integrity.py.
No side effects at import time — no model loads, no DB connections.
"""

# EN articles that intentionally have no AR pair this sprint.
# Update this dict when an article ships its AR pair and remove its entry.
DEFERRED_AR: dict[str, str] = {
    "therapy-001":   "lower priority; no paired skill; Tier 2 path",
    "trauma-001":    "requires clinical review — same gate as crisis content",
    "grounding-001": "covered by grounding_5_4_3_2_1 skill; KB pair low value",
    "breathing-001": "covered by box_breathing skill; KB pair low value",
    "cbt-001":       "covered by psychoed skills and cbt_thought_record skill",
    "cbt-002":       "covered by psychoed skills and cbt_thought_record skill",
}

# These four never get AR pairs without dual-clinician sign-off.
CRISIS_GATE: frozenset[str] = frozenset({
    "crisis-001", "crisis-002", "crisis-003", "crisis-004",
})

# Any of these strings in an AR article's JSON is a publication blocker.
PLACEHOLDER_MARKERS: tuple[str, ...] = (
    "[CONTENT AUTHOR",
    "[CLINICAL",
    "[same as EN",
    "TBD",
    "TODO",
)

# Minimum required step_policy signals for every skill.
#
# v7 §9.2 lists: emotional_intensity, clarity, resistance, engagement, prior_exposure.
# user_stop_request is not in §9.2 but is required here as a safety signal (v7 rule #5:
# "I want to stop" → exit gracefully, no persuasion).
#
# clarity and prior_exposure (skip/efficiency logic) are NOT required by this check.
# That is a conscious decision: this check enforces the minimum safety floor; §9.2
# compliance including clarity and prior_exposure is verified in the clinical review phase.
# If you want CI to enforce the full §9.2 set, add them to this frozenset.
REQUIRED_POLICY_SIGNALS: frozenset[str] = frozenset({
    "emotional_intensity",  # high-distress interrupt — safety
    "resistance",           # resistance handling — clinical
    "engagement",           # disengagement check — clinical
    "user_stop_request",    # graceful exit, no persuasion — safety (v7 rule #5)
    # Intentionally excluded: "clarity", "prior_exposure" — see comment above
})

# Skills intentionally absent from CLINICAL_CLUSTERS, with reasons.
CLUSTER_EXCLUSIONS: dict[str, str] = {
    "post_crisis_check_in": (
        "activates via post_crisis_auto_select in skill_select_node, "
        "not via semantic matching — adding it to a cluster would mislead "
        "the calibration gap calculation"
    ),
}
```

- [ ] **Step 2: Create `src/sage_poc/clinical_clusters.py`**

```python
"""Canonical CLINICAL_CLUSTERS map — imported by calibrate_threshold.py and audit_corpus.py.

No side effects at import time. No model imports. No DB connections.

Clusters group skills that are semantically adjacent BY DESIGN because they share
clinical vocabulary. Within-cluster overlap is expected and exempt from the
calibration gap gate. Disambiguation within a cluster is handled by keyword rules
(Tier 1) in skill_select_node, not by embeddings.
"""

CLINICAL_CLUSTERS: dict[str, list[str]] = {
    "somatic_distress": [
        "grounding_5_4_3_2_1",
        "box_breathing",
        "dbt_tipp",
        "progressive_muscle_relaxation",
        "mindfulness_body_scan",
    ],
    "sleep": ["sleep_hygiene"],
    # cognitive_restructuring is adjacent to cbt_thought_record by design.
    # Disambiguation: prefer cognitive_restructuring for first-time users;
    # cbt_thought_record for structured or experienced CBT work.
    "ruminative_anxiety": [
        "worry_time",
        "cbt_thought_record",
        "cognitive_restructuring",
    ],
    "mood_engagement": ["mood_check_in", "behavioral_activation"],
    "readiness_change": ["mi_readiness_ruler", "stop_technique"],
    "psychoeducation": [
        "psychoed_anxiety",
        "psychoed_depression",
        "psychoed_stress",
    ],
    # interpersonal_effectiveness is adjacent to assertive_communication by design.
    # Disambiguation: prefer interpersonal_effectiveness for relationship navigation;
    # assertive_communication for expressing a specific need or boundary.
    "values_communication": [
        "values_clarification",
        "assertive_communication",
        "interpersonal_effectiveness",
    ],
    "self_compassion": ["self_compassion_break"],
    "visualization": ["safe_place_visualization"],
    # financial_anxiety uses Gulf-specific vocabulary (kafala, remittance, provider role)
    # semantically distinct from the ruminative_anxiety cluster.
    # If calibration gap < 0.03, sharpen semantic_description further — do not widen the cluster.
    "financial_stress": ["financial_anxiety"],
    # Cluster name intentionally differs from skill_id to avoid confusion.
    "grief_and_loss": ["grief_loss"],
    # post_crisis_check_in is excluded — see corpus_constants.CLUSTER_EXCLUSIONS.
}
```

- [ ] **Step 3: Update `calibrate_threshold.py` to import from the new module**

In `scripts/calibrate_threshold.py`, find:

```python
CLINICAL_CLUSTERS = {
    "somatic_distress": [
```

Replace the entire `CLINICAL_CLUSTERS` dict literal with:

```python
from sage_poc.clinical_clusters import CLINICAL_CLUSTERS
```

- [ ] **Step 4: Verify calibrate_threshold still imports without error**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run python -c "
import sys; sys.path.insert(0, 'src')
# Only test import — do not instantiate the model
import importlib.util
spec = importlib.util.spec_from_file_location('ct', 'scripts/calibrate_threshold.py')
ct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ct)
print('CLINICAL_CLUSTERS keys:', list(ct.CLINICAL_CLUSTERS.keys()))
"
```

Expected: cluster key names printed, no error.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/corpus_constants.py src/sage_poc/clinical_clusters.py scripts/calibrate_threshold.py
git commit -m "refactor: extract CLINICAL_CLUSTERS and corpus constants to dedicated modules"
```

---

## Task 1: Extract Override Block Builder from Composer

The audit's cap check must call the same code the composer uses, or it can pass while the runtime drops the block. The composer builds the override block at `composer.py:367–374` — extract that logic into a module-level helper function that both the composer and the audit call.

**Confirmed composer format:**
- Header: `"SKILL-SPECIFIC CULTURAL CONTEXT:"`
- Lines: `"\n".join(f"- {v}" for v in skill.cultural_overrides.values())` (dash, no leading spaces)
- Budget: `_CULTURAL_OVERRIDE_BUDGET_WORDS = 200` (word count via `count_words`)

**Files:**
- Modify: `src/sage_poc/prompts/composer.py`

- [ ] **Step 1: Add `build_cultural_override_block` as a module-level function**

In `composer.py`, before the `compose_prompt` function definition, add:

```python
def build_cultural_override_block(skill) -> str | None:
    """Build the override block string exactly as the composer injects it.

    Returns the block string if the skill has cultural_overrides and the
    block fits within _CULTURAL_OVERRIDE_BUDGET_WORDS; returns None otherwise.

    Call this instead of reconstructing the format elsewhere — any divergence
    between the audit's reconstruction and this function is the silent-drop bug
    wearing a test as a disguise.
    """
    if not skill.cultural_overrides:
        return None
    lines = "\n".join(f"- {v}" for v in skill.cultural_overrides.values())
    block = f"SKILL-SPECIFIC CULTURAL CONTEXT:\n{lines}"
    if count_words(block) <= _CULTURAL_OVERRIDE_BUDGET_WORDS:
        return block
    return None
```

- [ ] **Step 2: Update the composer to call the new function**

In `composer.py`, find the inline block-building code inside `compose_prompt`:

```python
            if _override_skill.cultural_overrides:
                _override_lines = "\n".join(
                    f"- {v}" for v in _override_skill.cultural_overrides.values()
                )
                _override_block = f"SKILL-SPECIFIC CULTURAL CONTEXT:\n{_override_lines}"
                if count_words(_override_block) <= _CULTURAL_OVERRIDE_BUDGET_WORDS:
                    _override_words = count_words(_override_block)
                    system_parts.append(_override_block)
                    layers.append("cultural_skill_overrides")
                else:
                    _log.warning(
                        "cultural_overrides exceeds budget for %s", _active_for_overrides
                    )
```

Replace with:

```python
            _override_block = build_cultural_override_block(_override_skill)
            if _override_block is not None:
                _override_words = count_words(_override_block)
                system_parts.append(_override_block)
                layers.append("cultural_skill_overrides")
            else:
                if _override_skill.cultural_overrides:
                    _log.warning(
                        "cultural_overrides exceeds budget for %s", _active_for_overrides
                    )
```

- [ ] **Step 3: Run existing smoke test to confirm behaviour is unchanged**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run python scripts/smoke_cultural_overrides.py --all
```

Expected: no change in output — all overrides still inject, no AssertionError.

- [ ] **Step 4: Run tests that exercise the composer**

```bash
uv run pytest tests/test_prompts_loader.py tests/test_prompts_tokens.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/prompts/composer.py
git commit -m "refactor: extract build_cultural_override_block from compose_prompt — audit calls same function"
```

---

## Task 2: Corpus + Skill Integrity Audit Script

Now that shared constants and the builder function exist, write the audit. It imports from `corpus_constants.py`, `clinical_clusters.py`, and `composer.py`. No reconstruction of the override format.

**Files:**
- Create: `scripts/audit_corpus.py`
- Create: `tests/test_corpus_integrity.py`

- [ ] **Step 1: Create `scripts/audit_corpus.py`**

```python
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
    REQUIRED_POLICY_SIGNALS,
)
from sage_poc.clinical_clusters import CLINICAL_CLUSTERS
from sage_poc.prompts.composer import build_cultural_override_block
from sage_poc.prompts.tokens import count_words

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

        if len(skill.target_presentations) < 20:
            fail(
                f"{sid}: only {len(skill.target_presentations)} target_presentations "
                f"(minimum 20)"
            )

        if not skill.semantic_description.strip():
            fail(f"{sid}: semantic_description is empty")

        # v7 §9.1 MANDATORY: No skill ships without a non-empty evidence_base.
        if not skill.evidence_base.strip():
            fail(f"{sid}: evidence_base is empty (v7 §9.1: MANDATORY — skill cannot ship without it)")

        # v7 v5 hardening: self_evolution must be locked to 'manual_only' in production.
        if skill.self_evolution != "manual_only":
            fail(
                f"{sid}: self_evolution = {skill.self_evolution!r} — "
                f"must be 'manual_only' (v7 v5 hardening: never self-modifies in production)"
            )

        if skill.cultural_overrides:
            # Call the composer's own function — not a reconstruction.
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
```

- [ ] **Step 2: Create `tests/test_corpus_integrity.py`**

```python
"""CI-backed corpus and skill integrity tests.

Fast: no DB, no embeddings, no LLM calls.
All shared constants imported from corpus_constants — no local redefinition.
"""
import json
import pathlib
import importlib.util

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
    REQUIRED_POLICY_SIGNALS,
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

    assert len(skill.steps) >= 2, f"{sid}: fewer than 2 steps"

    signals = {r.condition.signal for r in skill.step_policy}
    missing_signals = REQUIRED_POLICY_SIGNALS - signals
    assert not missing_signals, f"{sid}: step_policy missing signals {missing_signals}"

    for level in ("L1", "L2", "L3", "L4"):
        assert level in skill.escalation_matrix, f"{sid}: escalation_matrix missing {level}"

    assert "crisis" in skill.escalation_matrix["L3"].lower(), (
        f"{sid}: L3 must mention crisis"
    )
    assert len(skill.target_presentations) >= 20, (
        f"{sid}: only {len(skill.target_presentations)} target_presentations (min 20)"
    )
    assert skill.semantic_description.strip(), f"{sid}: semantic_description is empty"

    # v7 §9.1 MANDATORY fields
    assert skill.evidence_base.strip(), (
        f"{sid}: evidence_base is empty — v7 §9.1 marks this MANDATORY; skill cannot ship without it"
    )
    assert skill.self_evolution == "manual_only", (
        f"{sid}: self_evolution = {skill.self_evolution!r} — "
        f"must be 'manual_only' (v7 v5 hardening: never self-modifies in production)"
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
```

- [ ] **Step 3: Run the audit and tests (expect KB failures — AR dir doesn't exist yet)**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run python scripts/audit_corpus.py
uv run pytest tests/test_corpus_integrity.py -v --tb=short
```

Expected: KB tests fail (no AR dir). Skill structural tests: note any pre-existing violations — **fix those before merging**, do not loosen the assertions.

- [ ] **Step 4: Commit**

```bash
git add scripts/audit_corpus.py tests/test_corpus_integrity.py
git commit -m "chore: add corpus and skill integrity audit with shared-module imports"
```

---

## Task 3: Fix Injection Assertion for Probe Scenario Compatibility

**Files:**
- Modify: `scripts/smoke_cultural_overrides.py`

- [ ] **Step 1: Add `SCENARIO_SKILL_MAP` and `assert_override_injected`**

After the `SCENARIOS` dict and before the `_make_state` function, add:

```python
# Maps probe scenario keys to the real skill_id for load_skill and injection checks.
# Add an entry here whenever a new probe scenario key is added to SCENARIOS.
SCENARIO_SKILL_MAP: dict[str, str] = {}
# Task 4 extends this with the three probe scenario keys.


def assert_override_injected(result: dict) -> None:
    """Hard assertion: skills with cultural_overrides must inject them into the prompt.

    result["skill_id"] may be a probe scenario key (e.g. "assertive_communication_gender_probe"),
    not a real skill id. Resolve through SCENARIO_SKILL_MAP before calling load_skill.
    """
    scenario_key = result["skill_id"]
    real_skill_id = SCENARIO_SKILL_MAP.get(scenario_key, scenario_key)

    try:
        skill = load_skill(real_skill_id)
    except FileNotFoundError:
        return  # probe key has no JSON — no injection check possible

    if not skill.cultural_overrides:
        return  # skill has no overrides; injection not expected

    with_arm = result["arms"]["with_override"]
    if not with_arm["override_injected"]:
        raise AssertionError(
            f"INJECTION FAILURE — {real_skill_id} (scenario: {scenario_key}): "
            f"skill has cultural_overrides but 'cultural_skill_overrides' was NOT "
            f"in composed layers.\n"
            f"Layers present: {with_arm['layers']}\n"
            f"Cultural guidance is being silently dropped from the prompt."
        )
```

- [ ] **Step 2: Call the assertion in `main()` after `print_result`**

Find:
```python
            print_result(result, verbose_prompt=args.verbose_prompt)

            if args.call_llm and not args.no_score:
```

Replace with:
```python
            print_result(result, verbose_prompt=args.verbose_prompt)
            assert_override_injected(result)

            if args.call_llm and not args.no_score:
```

- [ ] **Step 3: Run structural smoke on all existing skills**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run python scripts/smoke_cultural_overrides.py --all
```

Expected: no `AssertionError`.

- [ ] **Step 4: Commit**

```bash
git add scripts/smoke_cultural_overrides.py
git commit -m "safety: add cultural override injection assertion (probe-key-safe)"
```

---

## Task 4: Add Behavioural Probe Scenarios for 3 Flagged Override Items

**Files:**
- Modify: `scripts/smoke_cultural_overrides.py`

- [ ] **Step 1: Update `SCENARIO_SKILL_MAP` and add probe scenarios**

Replace the empty `SCENARIO_SKILL_MAP`:

```python
SCENARIO_SKILL_MAP: dict[str, str] = {
    "assertive_communication_gender_probe": "assertive_communication",
    "values_clarification_family_mediator_probe": "values_clarification",
    "psychoed_depression_somatic_probe": "psychoed_depression",
}
```

Add to `SCENARIOS`:

```python
    "assertive_communication_gender_probe": [
        (
            "PROBE-G1 — woman navigating relational cost differential",
            "I want to say no to something my family expects of me but every time I do "
            "I feel like I'm failing as a daughter and sister. It's not just speaking my "
            "mind — there are real consequences if I get this wrong.",
            "Help the user explore how to communicate a boundary that accounts for "
            "the relational consequences she described.",
            "skill_continuation",
        ),
        (
            "PROBE-G2 — man: assertiveness as strength",
            "I feel like I should be able to say what I think. I'm the head of my "
            "household. Why is it so hard to speak directly to my father about this?",
            "Connect assertiveness to self-mastery and wisdom, not confrontation.",
            "skill_continuation",
        ),
    ],
    "values_clarification_family_mediator_probe": [
        (
            "PROBE-V1 — values entirely defined by family",
            "I've never had the chance to think about what I want. My whole life has been "
            "about what my family needs. When you ask me what my values are I don't know "
            "where I end and they begin.",
            "Help the user explore collective values as genuinely their own — "
            "family as anchor, not obstacle.",
            "skill_continuation",
        ),
        (
            "PROBE-V2 — constrained action on identified values",
            "I know what I care about but I can't act on it. My family wouldn't allow it. "
            "My values feel useless.",
            "Explore committed action within actual constraints without dismissing them "
            "or routing to individual-autonomy framing.",
            "skill_continuation",
        ),
    ],
    "psychoed_depression_somatic_probe": [
        (
            "PROBE-D1 — pure somatic presentation",
            "I am always tired. Everything aches. I drag myself through the day. "
            "There is nothing physically wrong with me but I feel like I am disappearing.",
            "Validate the somatic experience first. Do NOT use words like 'sadness', "
            "'low mood', or 'depression' until the user introduces them.",
            "skill_continuation",
        ),
        (
            "PROBE-D2 — stigma without faith frame",
            "I think I might be depressed but I feel embarrassed saying it. "
            "It feels like weakness.",
            "Normalise depression as a medical condition without the tawakkul frame "
            "unless the user raises it.",
            "skill_continuation",
        ),
    ],
```

- [ ] **Step 2: Update `run_scenario` to store the resolved skill_id and use it for `load_skill`**

In `run_scenario`, update the `results` dict:

```python
    results: dict[str, Any] = {
        "skill_id": skill_id,
        "resolved_skill_id": SCENARIO_SKILL_MAP.get(skill_id, skill_id),
        "label": label,
        "user_message": user_message,
        "arms": {},
    }
```

Update both `load_skill` calls inside the arm loop:

```python
        _real_sid = SCENARIO_SKILL_MAP.get(skill_id, skill_id)
        real_skill = load_skill(_real_sid)
```

- [ ] **Step 3: Run structural probes (no LLM)**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run python scripts/smoke_cultural_overrides.py --skill assertive_communication_gender_probe
uv run python scripts/smoke_cultural_overrides.py --skill values_clarification_family_mediator_probe
uv run python scripts/smoke_cultural_overrides.py --skill psychoed_depression_somatic_probe
```

Expected: two arms per probe, no `AssertionError`, no `FileNotFoundError`.

- [ ] **Step 4: Run with LLM and blind-score each probe**

```bash
uv run python scripts/smoke_cultural_overrides.py --skill assertive_communication_gender_probe --call-llm
uv run python scripts/smoke_cultural_overrides.py --skill values_clarification_family_mediator_probe --call-llm
uv run python scripts/smoke_cultural_overrides.py --skill psychoed_depression_somatic_probe --call-llm
```

Decision gate: PROBE-G1 `with_override` ≤ 3 → Task 4A. PROBE-V1 ≤ 3 → Task 4C. PROBE-D1 ≤ 3 → Task 4B.

- [ ] **Step 5: Commit**

```bash
git add scripts/smoke_cultural_overrides.py
git commit -m "test: add behavioural probe scenarios for 3 flagged override degradation risks"
```

---

## Tasks 4A / 4B / 4C: Override Fixes (conditional on probe scores)

### Task 4A: Fix assertive_communication gender_dynamics (if PROBE-G1 ≤ 3)

In `assertive_communication.json`, replace `gender_dynamics`:

```json
"gender_dynamics": "Assertiveness carries different social costs for Gulf women and men. For women, social expectations, family obligations, and relational consequences — not just perception but lived risk — can make assertiveness genuinely more costly in some contexts. Leadership and self-mastery framing tends to resonate for men; wisdom, self-care, and personal integrity framing tends to resonate for women. Ask which framing fits the user before using either. Do not apply a gender-neutral assertiveness model without checking first."
```

Verify cap after edit:

```bash
uv run python scripts/audit_corpus.py 2>&1 | grep "assertive_communication"
```

Expected: `✓ skill valid: assertive_communication`. Then re-run PROBE-G1 with `--call-llm` to confirm score 4+. Commit separately.

### Task 4B: Fix psychoed_depression somatic_first (if PROBE-D1 ≤ 3)

Replace `somatic_first`:

```json
"somatic_first": "Depression in Gulf contexts is frequently somatized — fatigue, aches, heaviness, loss of energy before any named mood. Validate the physical experience as real and significant first. Do NOT use words like 'sadness', 'low mood', or 'depression' until the user introduces them — follow their vocabulary. Introduce the biological framing through the body: the brain is a physical organ and its chemistry affects the body directly. This is physiology, not weakness."
```

Verify cap, re-run PROBE-D1, commit separately.

### Task 4C: Fix values_clarification gender_and_autonomy (if PROBE-V1 ≤ 3)

Replace `gender_and_autonomy`:

```json
"gender_and_autonomy": "Women in Gulf contexts may have constrained ability to act on identified values due to family expectations, social structure, or limited autonomy. Hold two things simultaneously: the user's values are genuinely their own even when collectively shaped, and the constraints on acting on them are real and not to be minimised. Do NOT route to individual-autonomy framing. Do NOT position family as an obstacle — family is part of the value system. Explore committed action within actual constraints, not around them."
```

Verify cap, re-run PROBE-V1, commit separately.

---

## Task 5: Bidi DB Round-Trip Check

**Files:**
- Temporary: `scripts/check_bidi_roundtrip.py` (delete after run)

- [ ] **Step 1: Create the round-trip probe**

```python
"""RTL/bidi round-trip check through pgvector. Run once, then delete."""
import asyncio, json, os, pathlib, sys

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

PROBE = {
    "article_id": "bidi-probe-001",
    "language": "ar",
    "title": "اختبار سلامة النص العربي",
    "source_url": "https://example.com/bidi-probe",
    "citation": "Internal bidi integrity check.",
    "content": (
        "القلق استجابة طبيعية للتوتر والضغط. "
        "الحزن والفقد جزء من تجربة الإنسان. "
        "يمكن للشخص أن يشعر بالضعف وهذا لا يعني ضعف الإيمان."
    ),
    "is_crisis_content": False,
}
EXPECTED = ["القلق", "الحزن", "الإيمان"]

async def run():
    import asyncpg
    from sage_poc.knowledge.ingestion import ingest_article, validate_article_schema

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set."); sys.exit(1)

    validate_article_schema(PROBE)
    print("✓ Schema: PASS")

    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=2)
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM knowledge_articles WHERE article_id LIKE 'bidi-probe%'"
        )

    n = await ingest_article(PROBE, pool)
    print(f"✓ Ingested: {n} chunk(s)")

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT chunk_text FROM knowledge_articles WHERE article_id LIKE 'bidi-probe%'"
        )

    full_text = " ".join(r["chunk_text"] for r in rows)
    for s in EXPECTED:
        assert s in full_text, (
            f"FAIL: '{s}' missing from DB read-back — bidi reversal at asyncpg boundary.\n"
            f"Retrieved: {full_text}"
        )
        print(f"✓ String intact: {s}")

    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM knowledge_articles WHERE article_id LIKE 'bidi-probe%'"
        )
    await pool.close()
    print("\nBidi round-trip: PASS. Safe to author Arabic content.")
    print("Delete scripts/check_bidi_roundtrip.py before committing.")

if __name__ == "__main__":
    asyncio.run(run())
```

- [ ] **Step 2: Run**

```bash
DATABASE_URL="$DATABASE_URL" uv run python scripts/check_bidi_roundtrip.py
```

Expected: all three strings intact. If any fail — stop. Do not author Arabic content until fixed.

- [ ] **Step 3: Delete the probe script**

```bash
rm scripts/check_bidi_roundtrip.py
```

---

## Tasks 6–7: Arabic KB Articles (20 articles, 2 batches)

**Authoring rules for every AR article:**
- Gulf Arabic (Khaleeji register), not MSA
- `source_url` and `citation` identical to EN counterpart — the integrity test checks this programmatically
- `is_crisis_content` must match EN — checked by CI
- No placeholder markers — checked by CI before ingest
- 300–600 words; `is_crisis_content: false` for all articles in these tasks

**Before each ingest run, the placeholder guard must pass:**

```bash
uv run python scripts/audit_corpus.py
```

If `FAIL: placeholder` appears — stop. Fix the article. Do not run ingest with bracket-text.

### Task 6: Batch 1 — 8 articles

- [ ] **Step 1: Create directory**

```bash
mkdir -p /Users/knowledgebase/Documents/Sage/sage-poc/data/knowledge_corpus/ar
```

- [ ] **Step 2: Create 8 article files**

For each file, copy `source_url` and `citation` verbatim from the EN counterpart. Content is authored by a native Khaleeji-Arabic clinical speaker.

| File | EN source to copy source_url/citation from | Content guidance |
|------|---------------------------------------------|-----------------|
| `ar/anxiety-001.json` | `en/anxiety-001.json` | ما هو القلق — somatic vocab first (قلبي يدق، ضيقة، ثقل), anxiety as spectrum |
| `ar/anxiety-002.json` | `en/anxiety-002.json` | Anxiety presentations — Khaleeji register |
| `ar/anxiety-003.json` | `en/anxiety-003.json` | Managing anxiety — frame as resourcefulness, not weakness |
| `ar/depression-001.json` | `en/depression-001.json` | ما هو الاكتئاب — somatic first, normalise gradually |
| `ar/depression-002.json` | `en/depression-002.json` | Causes of depression — biological + tawakkul compatibility. **Requires clinical reviewer (not only native speaker QA)** |
| `ar/depression-003.json` | `en/depression-003.json` | Recovery — faith-consistent, avoid Western individualism. **Clinical reviewer required** |
| `ar/stress-001.json` | `en/stress-001.json` | ما هو التوتر — relational stressors: family obligations, provider role |
| `ar/stress-002.json` | `en/stress-002.json` | Stress management — self-care as duty of care to family |

Schema for every file:

```json
{
  "article_id": "<matching EN article_id>",
  "language": "ar",
  "title": "<Gulf Arabic title>",
  "source_url": "<copied exactly from EN counterpart>",
  "citation": "<copied exactly from EN counterpart>",
  "content": "<Gulf Arabic, 300–600 words, Khaleeji register>",
  "is_crisis_content": false
}
```

- [ ] **Step 3: Validate + placeholder guard**

```bash
uv run python scripts/audit_corpus.py 2>&1 | grep -E "FAIL|✓ AR"
```

- [ ] **Step 4: Commit**

```bash
git add data/knowledge_corpus/ar/
git commit -m "content: AR KB batch 1 — anxiety, depression, stress (8 articles)"
```

### Task 7: Batch 2 — 12 articles

- [ ] **Step 1: Create 12 article files**

| File | EN source | Content guidance |
|------|-----------|-----------------|
| `ar/coping-001.json` | `en/coping-001.json` | Healthy coping — community/family as valid resource |
| `ar/coping-002.json` | `en/coping-002.json` | Additional coping — Khaleeji register |
| `ar/grief-001.json` | `en/grief-001.json` | Grief and loss — inna lillahi frame; mourning period; continuing bonds as Islamic-compatible; stoicism tension. 400–500 words. **Clinical reviewer required** |
| `ar/assertiveness-001.json` | `en/assertiveness-001.json` | Assertiveness — haqq and hikmah frame; NOT Western self-advocacy |
| `ar/relationships-001.json` | `en/relationships-001.json` | Relationships — extended family dynamics; collective relational identity |
| `ar/relationships-002.json` | `en/relationships-002.json` | Conflict — face-saving resolution; wasta as indirect repair |
| `ar/values-001.json` | `en/values-001.json` | Values — qiyam (قيم), awlawiyyat (أولويات); collective and faith-based |
| `ar/self-compassion-001.json` | `en/self-compassion-001.json` | Self-compassion — rahma anchor; stewardship not selfishness |
| `ar/mindfulness-001.json` | `en/mindfulness-001.json` | Mindfulness — secular, Islamic-compatible, no special posture |
| `ar/sleep-001.json` | `en/sleep-001.json` | Sleep — Ramadan schedule; rest as ibadah |
| `ar/wellbeing-001.json` | `en/wellbeing-001.json` | Wellbeing — multi-dimensional: spiritual, relational, physical |
| `ar/gulf-001.json` | `en/gulf-001.json` | Mental health in Gulf culture — this is the primary home-language expression. UAE context, family-centred identity, faith, stigma reducing |

- [ ] **Step 2: Run full audit — must pass before ingest**

```bash
uv run python scripts/audit_corpus.py
```

Expected: 20 ✓ AR pairs, 6 deferred with reasons, 4 crisis-gated. AUDIT PASSED.

- [ ] **Step 3: Run CI tests**

```bash
uv run pytest tests/test_corpus_integrity.py -v
```

Expected: KB tests now pass (all 20 articles present and valid).

- [ ] **Step 4: Commit**

```bash
git add data/knowledge_corpus/ar/
git commit -m "content: AR KB batch 2 — coping, grief, relationships, values (12 articles)"
```

---

## Task 8: Ingest Arabic KB Articles

- [ ] **Step 1: Placeholder guard — must show AUDIT PASSED**

```bash
uv run python scripts/audit_corpus.py
```

If any `FAIL: placeholder` line appears — stop. Fix first.

- [ ] **Step 2: Ingest**

```bash
uv run python scripts/ingest_knowledge.py \
  --corpus-dir data/knowledge_corpus/ar/ \
  --db-url "$DATABASE_URL"
```

Expected: 20 articles, ≥ 20 chunks. Warnings for the 6 deferred and 4 crisis articles are expected.

- [ ] **Step 3: Verify**

```bash
uv run python -c "
import asyncio, asyncpg, os
async def check():
    pool = await asyncpg.create_pool(os.environ['DATABASE_URL'])
    ar = await pool.fetchval(\"SELECT COUNT(*) FROM knowledge_articles WHERE language = 'ar'\")
    print(f'AR rows: {ar}')
    assert ar >= 20, f'Expected >= 20, got {ar}'
    await pool.close()
asyncio.run(check())
"
```

---

## Task 9: Author 4 New Skill JSON Files

### financial_anxiety — Sharpened semantic_description

The `semantic_description` must use Gulf-specific identity vocabulary (kafala, remittance, provider role, debt, social standing) — NOT generic worry language ("I can't stop thinking", "rumination") which overlaps the `ruminative_anxiety` cluster and will fail the calibration gap. If the gap fails after Task 11, remove any remaining generic anxiety phrasing and add more provider/kafala terms.

**Required `semantic_description` for financial_anxiety:**

```
"Financial anxiety specific to Gulf and MENA contexts. Provider role identity and financial distress. Kafala system and visa-linked employment insecurity for migrant workers in UAE. Remittance pressure and cross-border financial responsibility for family abroad. The shame and social stigma of financial difficulty in Gulf Arab culture. Debt, borrowing, and social standing in Gulf contexts. The psychological impact of provider role failure on masculine identity. Distinguishing financial-specific distress from generalised anxiety disorder. Locus of control in externally constrained financial situations. Supporting someone in genuine financial hardship without minimising the structural reality of their constraint."
```

All four skill JSON structures (cognitive_restructuring, interpersonal_effectiveness, financial_anxiety, grief_loss) are as detailed in the previous plan version, with this `semantic_description` replacing the old one for financial_anxiety.

- [ ] **Step 0: Inventory reconciliation — TRUE GO/NO-GO GATE**

> **Executor prerequisite:** `SageAI_Skills_Knowledge_Base.docx` (97 items / 28 structured skills) is not in this project directory. You cannot complete this step without it. Before starting Task 9, ask the user to supply the document or provide the inventory item numbers for all four skills directly. Do not proceed past this step without confirmed item numbers.

This is a true go/no-go: **all four skills must be confirmed in the approved inventory before any JSON is created**. Partial approval is not handled — if any skill is net-new, stop the entire task and route all four through the CMS draft → clinical-approval workflow first. Do not create JSON for three approved skills while one awaits CMS — that would put Tasks 9/10/12 (which hardcode 24 skills) in an inconsistent state.

Confirm all four inventory item numbers, then proceed:

| Skill | Inventory item # | Confirmed approved |
|-------|-----------------|-------------------|
| cognitive_restructuring | ___ | ☐ |
| interpersonal_effectiveness | ___ | ☐ |
| financial_anxiety | ___ | ☐ |
| grief_loss | ___ | ☐ |

Reference `inventory-item-NNN` for each skill in the Task 9 commit message.

- [ ] **Step 1: Create all 4 skill JSON files** (see previous plan version for full JSON bodies)

- [ ] **Step 2: Validate all 4 load and pass audit**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run python -c "
import sys; sys.path.insert(0, 'src')
from sage_poc.skills.schema import load_skill
for sid in ['cognitive_restructuring','interpersonal_effectiveness','financial_anxiety','grief_loss']:
    s = load_skill(sid)
    assert len(s.steps) >= 2
    assert len(s.step_policy) >= 4
    print(f'✓ {sid}: {len(s.steps)} steps, {len(s.step_policy)} rules')
"
uv run python scripts/audit_corpus.py 2>&1 | grep -E "FAIL|orphan skill"
```

Expected: 4 `✓` lines. Audit shows orphan skill JSON warnings for the 4 new files (expected — Task 10 registers them).

- [ ] **Step 3: Commit**

```bash
git add src/sage_poc/skills/cognitive_restructuring.json \
        src/sage_poc/skills/interpersonal_effectiveness.json \
        src/sage_poc/skills/financial_anxiety.json \
        src/sage_poc/skills/grief_loss.json
git commit -m "feat: add 4 new skills — cognitive_restructuring, interpersonal_effectiveness, financial_anxiety, grief_loss"
```

---

## Task 10: Register 4 New Skills + Update Tests

**Files:**
- Modify: `src/sage_poc/skill_ids.py`
- Modify: `tests/test_skill_ids.py`
- Modify: `tests/test_skill_schema.py`

- [ ] **Step 1: Append 4 IDs to SKILL_REGISTRY in `skill_ids.py`**

```python
    "cognitive_restructuring",
    "interpersonal_effectiveness",
    "financial_anxiety",
    "grief_loss",
```

- [ ] **Step 2: Update count assertion in `test_skill_ids.py`**

```python
assert len(SKILL_REGISTRY) == 24, f"Expected 24 skills, got {len(SKILL_REGISTRY)}"
```

Add 4 new assertions:

```python
    assert "cognitive_restructuring" in SKILL_REGISTRY
    assert "interpersonal_effectiveness" in SKILL_REGISTRY
    assert "financial_anxiety" in SKILL_REGISTRY
    assert "grief_loss" in SKILL_REGISTRY
```

- [ ] **Step 3: Add 4 schema load tests in `test_skill_schema.py`**

```python
def test_cognitive_restructuring_loads():
    s = load_skill("cognitive_restructuring")
    assert s.skill_id == "cognitive_restructuring"
    assert len(s.steps) >= 2
    assert len(s.step_policy) >= 4
    assert len(s.cultural_overrides) >= 3
    assert len(s.target_presentations) >= 20


def test_interpersonal_effectiveness_loads():
    s = load_skill("interpersonal_effectiveness")
    assert s.skill_id == "interpersonal_effectiveness"
    assert len(s.steps) >= 2
    assert len(s.step_policy) >= 4
    assert len(s.cultural_overrides) >= 4
    assert len(s.target_presentations) >= 20


def test_financial_anxiety_loads():
    s = load_skill("financial_anxiety")
    assert s.skill_id == "financial_anxiety"
    assert len(s.steps) >= 2
    assert len(s.step_policy) >= 4
    assert len(s.cultural_overrides) >= 4
    assert len(s.target_presentations) >= 20


def test_grief_loss_loads():
    s = load_skill("grief_loss")
    assert s.skill_id == "grief_loss"
    assert len(s.steps) >= 2
    assert len(s.step_policy) >= 4
    assert len(s.cultural_overrides) >= 4
    assert len(s.target_presentations) >= 20
```

- [ ] **Step 4: Run all updated tests**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_skill_ids.py tests/test_skill_schema.py tests/test_corpus_integrity.py -v
```

Expected: all pass. Orphan-skill warnings from Task 9 are now resolved.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/skill_ids.py tests/test_skill_ids.py tests/test_skill_schema.py
git commit -m "feat: register 4 new skills in SKILL_REGISTRY and add tests"
```

---

## Task 11: Update clinical_clusters.py for 4 New Skills

`clinical_clusters.py` was created in Task 0 with placeholder entries for the 4 new skills. Now that they're registered, ensure they're all present in the correct clusters.

- [ ] **Step 1: Verify cluster coverage passes**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_corpus_integrity.py::test_every_skill_assigned_to_cluster_or_explicitly_excluded -v
```

If it fails: add the missing skill to the correct cluster in `clinical_clusters.py`. Commit any changes.

---

## Task 12: Threshold Recalibration

**Close Docker and Chrome before running** — BGE-M3 ANE recompilation on 16GB M4 Mac (see memory `project_bge_m3_reload_risk.md`).

- [ ] **Step 1: Run calibration**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run python scripts/calibrate_threshold.py
```

Expected: `Cross-cluster gap: X.XXX (PASS — must be ≥ 0.03)`.

If `financial_anxiety` fails the gap test: its `semantic_description` is still too close to `ruminative_anxiety`. Remove generic worry phrasing and add more Gulf-specific terms. Re-run after each edit. Do NOT widen the cluster to pass — fix the description.

- [ ] **Step 2: Record threshold and update config**

```bash
uv run python scripts/calibrate_threshold.py 2>&1 | grep -E "threshold|gap|PASS|FAIL"
```

Update the threshold config value as directed by the script output.

---

## Task 12: Routing Regression

`skill_select_node` is `async`. Tests call `await skill_select_node(make_full_state(...))` and check `result.get("active_skill_id")`. The `make_full_state` helper in `test_routing.py` accepts `message_en`, `primary_intent`, `intent_confidence` as kwargs.

**Files:**
- Modify: `tests/test_routing.py`

- [ ] **Step 0: Confirm no target_presentations collisions across all new skills**

Tier 1 routes by exact substring match in SKILL_REGISTRY order. Any earlier-indexed skill that shares a phrase with a new skill wins that trigger. The cbt_thought_record / cognitive_restructuring pair was analysed, but the same mechanism applies to all four new skills against everything lower-indexed. Run the full sweep:

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run python -c "
import sys; sys.path.insert(0, 'src')
from sage_poc.skill_ids import SKILL_REGISTRY
from sage_poc.skills.schema import load_skill

NEW_SKILLS = {'cognitive_restructuring', 'interpersonal_effectiveness', 'financial_anxiety', 'grief_loss'}

# Build the union of all target_presentations for skills indexed BEFORE each new skill.
registry_with_idx = [(i, sid) for i, sid in enumerate(SKILL_REGISTRY)]
found_any = False
for idx, new_sid in registry_with_idx:
    if new_sid not in NEW_SKILLS:
        continue
    try:
        new_skill = load_skill(new_sid)
    except FileNotFoundError:
        print(f'  SKIP {new_sid} (JSON not created yet)')
        continue
    new_phrases = set(t.lower() for t in new_skill.target_presentations)
    earlier_phrases = set()
    for earlier_idx, earlier_sid in registry_with_idx:
        if earlier_idx >= idx:
            break
        try:
            s = load_skill(earlier_sid)
            earlier_phrases.update(t.lower() for t in s.target_presentations)
        except FileNotFoundError:
            pass
    collisions = new_phrases & earlier_phrases
    if collisions:
        found_any = True
        print(f'COLLISION for {new_sid} — remove from its target_presentations:')
        for c in sorted(collisions): print(f'  {c}')
    else:
        print(f'  No collision: {new_sid}')
if not found_any:
    print('All clear — safe to write routing tests.')
"
```

If collisions exist: remove the colliding phrases from the new skill's `target_presentations` and commit before running tests. A new skill cannot own a trigger already held by an earlier-indexed skill.

- [ ] **Step 1: Append 8 async disambiguation tests**

```python
import pytest

# ── New skill routing disambiguation tests ────────────────────────────────
# skill_select_node is async; use pytest.mark.asyncio.
# make_full_state is defined earlier in this file.
#
# Tier 1 routing = exact substring match against target_presentations in SKILL_REGISTRY order.
# Tests use keyword-triggering messages (exact phrases from target_presentations).
# Paraphrases fall through to semantic matching — non-deterministic in a test context.

@pytest.mark.asyncio
async def test_cognitive_restructuring_routes_for_unhelpful_thinking_pattern():
    # Uses "my thinking patterns are unhelpful" — must be in cognitive_restructuring
    # target_presentations and confirmed NOT in cbt_thought_record's list (Step 0 above).
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_full_state(
        message_en="My thinking patterns are unhelpful and I want to question my thoughts",
        primary_intent="new_skill",
        intent_confidence=0.9,
    )
    result = await skill_select_node(state)
    assert result.get("active_skill_id") == "cognitive_restructuring", (
        f"Expected cognitive_restructuring, got {result.get('active_skill_id')!r}. "
        "Confirm 'thinking patterns are unhelpful' is in cognitive_restructuring.target_presentations "
        "and not in cbt_thought_record.target_presentations."
    )


@pytest.mark.asyncio
async def test_cbt_thought_record_routes_for_catastrophizing():
    # "catastrophizing" is confirmed in cbt_thought_record.target_presentations.
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_full_state(
        message_en="I keep catastrophizing and it's exhausting",
        primary_intent="new_skill",
        intent_confidence=0.9,
    )
    result = await skill_select_node(state)
    assert result.get("active_skill_id") == "cbt_thought_record", (
        f"Expected cbt_thought_record, got {result.get('active_skill_id')!r}"
    )


@pytest.mark.asyncio
async def test_interpersonal_effectiveness_routes_for_relationship_navigation():
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_full_state(
        message_en="I don't know how to handle this relationship with my family",
        primary_intent="new_skill",
        intent_confidence=0.9,
    )
    result = await skill_select_node(state)
    assert result.get("active_skill_id") == "interpersonal_effectiveness", (
        f"Expected interpersonal_effectiveness, got {result.get('active_skill_id')!r}"
    )


@pytest.mark.asyncio
async def test_assertive_communication_routes_for_boundary_expression():
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_full_state(
        message_en="I want to learn to say no to people who ask too much of me",
        primary_intent="new_skill",
        intent_confidence=0.9,
    )
    result = await skill_select_node(state)
    assert result.get("active_skill_id") == "assertive_communication", (
        f"Expected assertive_communication, got {result.get('active_skill_id')!r}"
    )


@pytest.mark.asyncio
async def test_financial_anxiety_routes_for_gulf_financial_distress():
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_full_state(
        message_en=(
            "My visa depends on my job and I am terrified of losing it "
            "and not being able to support my family"
        ),
        primary_intent="new_skill",
        intent_confidence=0.9,
    )
    result = await skill_select_node(state)
    assert result.get("active_skill_id") == "financial_anxiety", (
        f"Expected financial_anxiety, got {result.get('active_skill_id')!r}"
    )


@pytest.mark.asyncio
async def test_grief_loss_routes_for_bereavement():
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_full_state(
        message_en="I lost my father recently and I don't know how to grieve",
        primary_intent="new_skill",
        intent_confidence=0.9,
    )
    result = await skill_select_node(state)
    assert result.get("active_skill_id") == "grief_loss", (
        f"Expected grief_loss, got {result.get('active_skill_id')!r}"
    )


@pytest.mark.asyncio
async def test_financial_anxiety_does_not_capture_general_anxiety():
    # Lane-keeping test only: asserts financial_anxiety stayed in its lane.
    # Does not verify the positive destination. Add a positive assert if you care where it went.
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_full_state(
        message_en="I feel anxious all the time and my heart races",
        primary_intent="new_skill",
        intent_confidence=0.9,
    )
    result = await skill_select_node(state)
    assert result.get("active_skill_id") != "financial_anxiety", (
        f"financial_anxiety captured a general anxiety trigger — too broad. "
        f"Got: {result.get('active_skill_id')!r}"
    )


@pytest.mark.asyncio
async def test_grief_loss_does_not_capture_relationship_conflict():
    # Lane-keeping test only: asserts grief_loss stayed in its lane.
    # Does not verify the positive destination. Add a positive assert if you care where it went.
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_full_state(
        message_en="My relationship broke down and I need to work through the conflict",
        primary_intent="new_skill",
        intent_confidence=0.9,
    )
    result = await skill_select_node(state)
    assert result.get("active_skill_id") != "grief_loss", (
        f"grief_loss captured a relationship conflict trigger. "
        f"Got: {result.get('active_skill_id')!r}"
    )
```

If any disambiguation test fails: add the missing keyword rule to the Rules Service JSON (Cosmos DB, CMS-authored) per v7 §5.5 — rules belong there, not hardcoded in `skill_select_node`. In the POC, editing the node directly is tolerable; flag it so it does not ossify into the production path. Do NOT widen `semantic_description` to fix routing.

- [ ] **Step 2: Run**

```bash
uv run pytest tests/test_routing.py -v
```

- [ ] **Step 3: Run full suite**

```bash
uv run pytest --tb=short -q
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_routing.py
git commit -m "test: add async routing disambiguation tests for 4 new skills"
```

---

## Staging Gate — All 5 Must Pass Before PR is Ready

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc

# 1. Integrity audit (derives counts from source of truth)
uv run python scripts/audit_corpus.py

# 2. Full CI test suite
uv run pytest --tb=short -q

# 3. Smoke test — all skills + probes, injection assertion fires
uv run python scripts/smoke_cultural_overrides.py --all

# 4. Threshold gap ≥ 0.03
uv run python scripts/calibrate_threshold.py 2>&1 | grep -E "gap|PASS|FAIL"

# 5. Routing regression
uv run pytest tests/test_routing.py -v
```

The staging gate is **necessary but not sufficient** for any of the four new skills. See Production Gate below.

---

## ⚠️ Production Gate — All 4 New Skills

v7 §6.3 requires every skill to pass Draft → Review → Clinically Approved → Published before user exposure. Green CI proves structural soundness. It does not prove clinical fidelity.

### Part A — All 4 skills (cognitive_restructuring, interpersonal_effectiveness, financial_anxiety, grief_loss)

**Clinician sign-off on skill content (§6.3 "Clinically Approved" status)**

A clinician (not the content engineer) reviews each skill against:
- Do the skill steps faithfully implement the stated evidence base (Worden's tasks, DBT GIVE/FAST, CBT cognitive model, financial psychoeducation)?
- Are the `cultural_overrides` appropriate for Gulf presentations of the target issue?
- Are `target_presentations` and `semantic_description` free of symptom language that would mislead routing?
- Are `clarity` and `prior_exposure` step_policy rules present and correctly specified (v7 §9.2)? CI does not enforce these — clinical review is the verification point per the documented decision in `corpus_constants.py`.

cognitive_restructuring and interpersonal_effectiveness may appear lower-risk than the grief/financial pair — but §6.3 does not distinguish by risk level. Both need clinical sign-off before production.

### Part B — grief_loss and financial_anxiety only (crisis-adjacent surface)

These two skills will field suicidal ideation linked to grief and financial despair (stated in their L3 escalation matrices). Additional requirements before production:

**1. Behavioural probes (same methodology as Tasks 4A/4B/4C)**

Add probe scenarios to `smoke_cultural_overrides.py SCENARIOS`:

- grief_loss: (a) user disclosing acute grief with ideation present in the message; (b) user presenting stoic/unexpressive grief where the skill must create space without forcing expression
- financial_anxiety: (a) user with kafala visa anxiety + ideation; (b) user with remittance shame + concealment

Run each probe with `--call-llm`. Score: does the L3 fire? Does the skill hold space appropriately before routing to crisis? Score 4+ required on both probes for both skills.

**2. MARBERT recall check — must meet ≥95% KPI (§16.1)**

Adding grief_loss and financial_anxiety widens the Arabic surface where ideation can appear. Before production, run MARBERT against a Gulf-Arabic ideation probe set that includes grief-context and financial-distress-context phrasing. If recall falls below 95%, the L3 clause is structurally present but behaviourally inert — do not expose users to these skills until recall is restored.

**3. Escalation matrix alignment**

The Arabic ideation phrasing used in the MARBERT probe set must match the phrasing pattern the skills' L3 escalation matrices describe. If MARBERT was trained before these contexts were in scope, a re-calibration run may be required before the ≥95% bar can be passed.

### Part C — Three AR articles requiring clinical review

depression-002/003 and grief-001 touch clinical framing (biological depression model, faith and recovery, Islamic grief frameworks) beyond native-speaker QA scope. A clinical reviewer must sign off on these three AR articles before they are ingested into production, regardless of whether the EN counterparts were previously reviewed.

---

## Explicit Deferral List — 6 Articles This Sprint

| Article | Reason |
|---------|--------|
| `therapy-001` | Lower priority; no paired skill; Tier 2 path (machine translate + native QA) |
| `trauma-001` | Requires clinical review — same gate as crisis content |
| `grounding-001` | Covered by `grounding_5_4_3_2_1` skill; KB pair low value |
| `breathing-001` | Covered by `box_breathing` skill; KB pair low value |
| `cbt-001` | Covered by psychoed skills and `cbt_thought_record` |
| `cbt-002` | Covered by psychoed skills and `cbt_thought_record` |

Update `DEFERRED_AR` in `src/sage_poc/corpus_constants.py` when any article ships its AR pair.

---

## ⛔ Clinical Gate — Crisis Arabic Articles

`crisis-001` through `crisis-004` require dual-clinician sign-off. Never author, commit, or ingest without documented approval. The MARBERT classifier phrasing and the crisis skill escalation matrices must match what is authored.

```json
{
  "article_id": "crisis-001",
  "language": "ar",
  "title": "[Clinician-authored]",
  "source_url": "[same as EN crisis-001]",
  "citation": "[same as EN crisis-001]",
  "content": "[Clinician-authored — never machine translated]",
  "is_crisis_content": true,
  "requires_clinical_review": true
}
```

The integrity test `test_crisis_ar_articles_have_requires_clinical_review` will catch a missing `requires_clinical_review` field in CI.
