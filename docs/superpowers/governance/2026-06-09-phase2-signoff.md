# Phase 2 Sign-off — Semantic Routing Production Architecture

**Date:** 2026-06-09
**Branch:** feat/semantic-routing-production-architecture
**Plan:** docs/superpowers/plans/2026-06-09-semantic-routing-production-architecture.md
**Status:** Phase 2 COMPLETE — machinery built, governance holds verified, Phase 3 blocked on clinical sign-off

---

## Sign-off record

### Phase 2 approved

Phase 2 (Tasks 2 and 6) is signed off. Both commits are on the branch and clean:

- `dbcb6a6` / `62ba69a` — Task 2: Tier-1 best-match scoring (SF-1)
- `711358f` — Task 6: multi-vector anchor index + cluster argmax + state-in-query + rename cascade

All non-gated tests green. All gated tests correctly xfail.

---

## Governance log entries

### Entry 1 — TASK-5 holds verified-real (2026-06-09)

**Method:** Temporarily added representative anchors to `grief_loss.json` and `interpersonal_effectiveness.json`. Ran the three TASK-5 xfail tests. All three returned `[XPASS(strict)]` — which under `strict=True` is a CI failure. Reverted both JSON files to `semantic_anchors: []`.

**What this proves:**
1. The underlying assertions are correct: with appropriate anchors, the routing machinery routes the probe phrases to the right skill.
2. `strict=True` fires the instant anchor content appears without authorization — the CI gate is working, not decorative.
3. The holds are red because the anchor arrays are empty, not because the machinery is broken.

**Current state:** `grief_loss.semantic_anchors = []`, `interpersonal_effectiveness.semantic_anchors = []`. Both confirmed clean post-revert.

**Approval status:** Task 5 remains blocked on clinical sign-off. The holds stay in place until sign-off is appended here.

---

### Entry 2 — Task 6 conftest modification (flag for clinical reviewer)

**Commit:** 711358f (`feat(skill_select): multi-vector anchor index + rename cascade`)

**What happened:** Task 6's rename (`_semantic_*` → `_anchor_*`) required updating `tests/conftest.py` (the `_stub_bge_m3` fixture) and `tests/test_audit_group3.py` and `tests/test_routing.py`. These are test-infrastructure changes that were not in the plan's original file map. They are correct and necessary, but they were bundled into the same commit as the production code change rather than separated.

**Clinical reviewer note:** The conftest change is in a `feat(skill_select)` commit, not a `test(conftest)` commit. When reviewing commit 711358f, the diff includes both `src/sage_poc/nodes/skill_select.py` (production) and `tests/conftest.py` (test infrastructure). The test-infrastructure changes are: updating the `_manage_bge_m3_state` fixture to save/restore `_anchor_*` instead of `_semantic_*`, and mirroring the new pairs-construction logic (one entry per semantic_description + one per semantic_anchors item). These are pure structural changes with no clinical content implications.

**Engineering note:** Future plan file maps should include `tests/conftest.py` when renaming globals in `skill_select.py`.

---

### Entry 3 — Index rebuild duplication standard

**Context:** Three places in the codebase independently re-implement the skill index construction:

1. `_tier1_match()` in `tests/test_wrong_skill_routing.py` — mirrors the Tier-1 keyword loop
2. `_stub_bge_m3` fixture in `tests/conftest.py` — mirrors the `_ensure_semantic_ready` pairs construction
3. `scripts/calibrate_threshold.py` — builds its own one-per-skill matrix from `semantic_description` only

The calibrate_threshold.py instance is the first to cause a concrete problem: it omits `semantic_anchors` from its matrix construction. After Task 5 adds anchors to three skills, the script will measure one-centroid scores while production uses max-over-anchors. The gap estimate will be directionally misleading: the script reports a smaller gap than production has, which could trigger threshold tampering (see the explicit "do not raise into the 0.46–0.47 somatic band" guard).

**Standard (applies to all future test/script code):**

> Test and script code that scores against the skill index must call `_ensure_semantic_ready()` and read `_anchor_embeddings` / `_anchor_skill_ids`, not rebuild the matrix from scratch. A local re-implementation is a future version of this bug.

The fix for `calibrate_threshold.py` is a Task 9 blocking prerequisite (see plan, Task 9 Step 0). The other two re-implementations (_tier1_match, conftest fixture) are currently harmless and will be addressed if/when they diverge.

---

---

### Entry 4 — MI+STOP cluster decision: split confirmed, rationale documented (2026-06-09)

**Decision:** Keep `readiness_ambivalence: [mi_readiness_ruler]` and `impulse_pause: [stop_technique]` as single-skill clusters. The split already shipped in 895e365 is correct. No code change required.

**Clinical rationale (confirmed by user 2026-06-09):**

STOP (DBT distress-tolerance) and MI readiness ruler address opposite sides of the change process:

- **STOP** is an emergency intervention for an *acute, high-arousal, present-tense urge* — Linehan's own framing is "creating a crucial gap between impulse and action when the urge to act is nearly irresistible." The user's state is hot, immediate, dysregulated.
- **MI readiness ruler** targets *deliberative, future-oriented ambivalence* — the contemplation stage, low arousal. MI's stance is the inverse of urgency: the clinician resists their "righting reflex." The user's state is cold, reflective, ambivalent.

They share a treatment-modality lineage (both touch mindfulness) and a vague "self-regulation" umbrella, but they address completely different clinical presentations at completely different points in the change cycle. User language is disjoint: "part of me wants to change and part doesn't" (MI) and "I'm about to do something I'll regret" (STOP) do not occupy the same semantic neighborhood.

**Why this settles the clustering question:**

The cluster is a *routing-authority grant*, not a label. `_CLUSTER_ARGMAX_FLOOR = 0.42` lets one skill in a cluster win *below* the 0.4593 threshold because it outranked its clustermate. This mechanism is only safe when the two skills genuinely compete for the same user utterances — i.e., a message scoring moderately for both is a real close call and relative ranking is trustworthy.

MI and STOP fail this test. A message scoring 0.43 for both is not a close call between two good candidates — it is a low-confidence match to two clinically unrelated things. Pairing them would grant sub-threshold routing authority to a competition that should never happen, and when it did fire it would be a coin-toss between clinically opposite interventions.

**Taxonomy principle for future clustering decisions:**

> Clusters group skills by *shared clinical presentation* (the user's words and emotional state), not by shared modality, shared treatment lineage, or a vague categorical umbrella. The test: "do these two skills compete for the same user utterances?" If not, they don't belong in the same cluster regardless of what they share conceptually.

The existing clusters that passed audit (somatic_distress, ruminative_anxiety, values_communication) all group skills that genuinely compete for the same presentations. This principle gives the clinical team a reusable rule for the next clustering question (values_clarification vs. ACT, the psychoeducation trio) without relitigating each pair from scratch.

**Action:** None. Conservative split is already live. Append this rationale to the governance record so the principle is documented, not just the outcome.

---

## Task 3 + Task 5 clinical sign-off package

The following are blocked on clinical sign-off. They must NOT merge until the sign-off record is appended here.

### Task 3 — keyword ownership decisions (2 items)

1. **Remove `catastrophizing` / `catastrophising` / `cant stop thinking about it` from `worry_time.target_presentations`**
   - Clinical question: are these phrases solely cognitive_restructuring territory, or is there a legitimate worry_time clinical presentation they capture?
   - Decision required: yes/no to removal from worry_time + yes/no to addition of catastrophizing keywords to cognitive_restructuring

2. **Add `catastrophizing` / `catastrophising` / `i keep catastrophizing` / `always catastrophizing` to `cognitive_restructuring.target_presentations`**
   - Conditional on decision 1 above

Sign-off record (append here when received):
```
Task 3 — clinical sign-off
Reviewer: [name]
Date: [date]
Decision: [approved/rejected, with rationale]
```

### Task 5 — semantic_anchors (24 sentences across 3 skills)

The 24 anchor sentences are specified in the plan at Task 5 Steps 1–3. They are representative user utterances — clinical presentations of each skill's domain. Each sentence must be reviewed for:
- Clinical accuracy (does it represent a genuine clinical presentation of this skill?)
- Cultural appropriateness (Gulf context)
- Safety (no anchor must sit in the passive-SI scoring region — Task 9 Step 2 validates this automatically post-merge)

**MI + STOP cluster question (also requires sign-off):**

`CLINICAL_CLUSTERS` was updated during Phase 1 (commit 895e365) to split `readiness_change: [mi_readiness_ruler, stop_technique]` into two single-skill clusters:
- `readiness_ambivalence: [mi_readiness_ruler]`
- `impulse_pause: [stop_technique]`

The split is the conservative default (single-skill clusters disable argmax routing). If there is clinical rationale for keeping MI and STOP in a shared cluster (they share a "readiness / self-regulation" clinical region), the clinical lead can affirm the pairing and the clusters can be restored. Without explicit affirmation, the split stands.

Sign-off record (append here when received):
```
Task 5 — clinical sign-off
Reviewer: [name]
Date: [date]
Decision: [approved/rejected for each of the 3 skills' anchor sets]
MI+STOP cluster: [affirm pairing / confirm split]
```

---

## Pre-pilot items (not pre-Gitex)

The following are correctly deferred to pre-pilot (demo sessions have empty therapeutic profiles, so these are dormant for Gitex):

### State-in-query coverage gap

Two tests needed before any pilot where `therapeutic_profile.summary` is populated:

1. **Fast-path equivalence** (`profile_context=""` → identical routing to no-profile path):
   ```python
   @pytest.mark.slow
   async def test_state_in_query_empty_profile_context_identical_to_no_profile():
       """When profile_context is empty string, query is identical to message_en alone.
       Routing result must match the no-profile baseline for the same phrase."""
       # ... assert same active_skill_id for profile=None and profile={"summary": ""}
   ```

2. **Slow-path degradation guard** (populated profile_context that contains non-target vocabulary must not corrupt routing):
   ```python
   @pytest.mark.slow
   async def test_state_in_query_profile_context_does_not_corrupt_routing():
       """A profile summary containing incidental vocabulary from non-target skills
       must not change routing outcome for a phrase that has a clear keyword match."""
       # phrase = grief phrase; profile = "user has discussed breathing difficulties"
       # assert active_skill_id == "grief_loss" (keyword match wins; semantic tier not reached)
   ```

These tests are needed before the unified memory layer starts producing non-empty `therapeutic_profile.summary` values in pilot sessions.
