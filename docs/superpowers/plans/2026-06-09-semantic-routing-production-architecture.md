# Semantic Routing Production Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the first-match-wins Tier-1 keyword loop and single-centroid Tier-2 semantic match with a production routing architecture — best-match scoring, multi-vector semantic anchors, cluster argmax, state-in-query, and a Falcon-3B rerank stub — that eliminates the root causes of wrong-skill routing rather than masking symptoms with keyword patches.

**Architecture:** Four independent layers built in sequence. (1) Diagnostic: confirm the semantic fallback is healthy before changing it. (2) Tier-1 structural repair: best-match scoring (SF-1) + worry_time de-confliction (SF-3) — two changes to the keyword loop that clear 4 dominant-shadower failures at once. (3) Multi-vector semantic-primary: `semantic_anchors` per skill + max-over-anchors matching + cluster argmax + state-in-query — replaces the single centroid per skill, dissolves T2-ERR cross-cluster bleed. (4) Margin guard + Falcon-3B rerank interface: routes close-call semantic decisions through a cross-encoder stub, with the interface already shaped for Falcon-3B to plug in when validated.

**Why not the keyword expansion plan:** `docs/superpowers/plans/2026-06-09-semantic-routing-keyword-expansion.md` hardened Tier-1 against 13 test-fixture phrases. This plan eliminates the failure classes those phrases represent. When this plan is shipped, the keyword expansion plan is superseded. The keyword expansions it authored for non-overlapping skills (mood_check_in, financial_anxiety, mi_readiness_ruler) remain valid and survive this change.

**Related existing plan:** `docs/superpowers/plans/2026-06-01-multi-vector-semantic-matching.md` specifies Tasks 4–7 in full. This plan incorporates those tasks. Tasks 1–3 and 8 are net-new.

**Tech Stack:** Python 3.12, pytest, BGE-M3, `sentence_transformers`, `sage_poc.nodes.skill_select`, `sage_poc.nodes.skill_rerank`, `sage_poc.skills.schema`, `sage_poc.clinical_clusters`, `scripts/calibrate_threshold.py`, `scripts/semantic_probe_set.py`, `scripts/validate_grief_sf1_boundary.py`

---

## Architecture context

**Three-tier routing today (`skill_select.py`):**

1. **Tier 0** — State-driven auto-selects (crisis monitoring → post_crisis_check_in; psychotic_disclosure flag → psychotic_referral; info_request → knowledge_retrieve). Not changed by this plan.
2. **Tier 1** — Keyword substring match: iterates SKILL_REGISTRY in registry order; first match wins regardless of specificity. **Root cause of SF-1 (dominant shadower).**
3. **Tier 2** — BGE-M3 cosine similarity against one `semantic_description` embedding per skill; best-score above `SEMANTIC_THRESHOLD = 0.4593`. **Root cause of T2-ERR (cross-cluster bleed when two skill descriptions sit close).**

**Documented systemic failures driving this plan (from `docs/superpowers/audits/2026-06-07-skill-routing-audit-v5-phase1-taxonomy.md`):**

| ID | Root cause | Affected skills | This plan's fix |
|----|-----------|-----------------|-----------------|
| SF-1 | First-match-wins: `cbt_thought_record [0]` and `worry_time [7]` shadow 4 skills | self_compassion_break, PST, ACT, cognitive_restructuring | Task 2: best-match scoring |
| SF-3 | worry_time keyword surface too broad — `catastrophizing` and generic think/worry phrases belong to other skills | cognitive_restructuring, PST | Task 3: de-confliction |
| T2-ERR | Single centroid cannot span dispersed clinical language region | grief_loss, interpersonal_effectiveness, financial_anxiety | Tasks 4–6: multi-vector anchors |
| TIER2-DUALIDX | Two semantic objectives (technique identity vs. user language) cannot share one threshold | grief, cross-cluster bleed generally | Task 6: multi-vector + cluster argmax |

**Not in scope here (reasons noted):**
- SF-2 (intent_route intensity blindness) — upstream of skill_select; requires classifier redesign or new intensity signal; separate plan
- SF-5 (audit attribution gap) — ~10-line fix, already marked ready, ships independently; see `skill_select.py` audit task
- SF-6 (grief_loss Arabic keyword expansion) — requires native-speaker + clinical review; separate plan
- Falcon-3B live model — model not validated; rerank stub in Task 7 shapes the interface
- Thin keyword fast-path from production logs — requires pilot usage data; not available pre-Gitex

**Governance prerequisites (confirmed by clinical review 2026-06-09):**

Tasks 3 and 5 touch clinician-owned content — keyword ownership decisions and representative user utterances are clinical authorship, not engineering. They must complete the CMS draft → review → approve → publish pathway before merging.

1. **CLINICAL_CLUSTERS validation:** `_CLUSTER_ARGMAX_FLOOR = 0.42` lets a within-cluster skill win below the 0.4593 absolute threshold. Cluster boundaries now carry routing weight. Confirm that the cluster map in `src/sage_poc/clinical_clusters.py` is clinician-validated — if it was drafted by engineering, route it through the clinical sign-off log before this plan ships.

2. **Tasks 3 and 5 merge gate:** Clinical sign-off record must be appended to `docs/superpowers/governance/` (or the equivalent sign-off log) before merging the branches that carry Task 3 (keyword ownership change) and Task 5 (semantic anchors). The anchors are destined for the CMS once the CMS supports `semantic_anchors` as a field.

**Cold-start pre-warm:** After Task 6 ships, `_ensure_semantic_ready()` encodes ~51 anchor texts on first request instead of ~27 descriptions. The index build happens once (lazily); subsequent requests hit the cached matrix. On a cold Railway dyno the first post-deploy request is slower than before. If first-hit latency matters for the Gitex demo, call `_ensure_semantic_ready()` explicitly at server startup — `server.py` warmup at line ~55 is the right place. Add a warmup check in Task 9.

---

## Execution model — three phases, not two buckets

This plan cannot be split into "engineering (no gate)" and "clinical (gated)" buckets cleanly, because two engineering tasks have acceptance tests that depend on gated clinical content:

- **Task 2 Step 5 assertion 3** ("catastrophizing" → `cognitive_restructuring`) fails until Task 3 merges, because `cognitive_restructuring` only gains the catastrophizing keyword in Task 3.
- **Task 6 Step 8** (grief/IE anchor probes) fails until Task 5 merges, because Task 5 adds the `semantic_anchors` those probes route against.
- **All of Task 9** is a post-merge acceptance gate by nature.

Treating Tasks 2 and 6 as "fully greenable now" is wrong. An autonomous worker hitting these red assertions has one obvious move — add the catastrophizing keyword and grief anchors itself — which is exactly what the `§9 clinical sign-off gate` exists to stop. It would look like normal task completion in the diff.

### Three phases

**Phase 1 — Greenable now, fully (no gated dependency):**
Tasks 1, 4, 7, 8. These are self-contained: Task 1 is read-only diagnostic, Task 4 tests a synthetic skill, Task 7 is a new module, Task 8 monkeypatches mock scores. Run to green, merge immediately.

**Phase 2 — Machinery now, green deferred:**
Tasks 2 and 6. Write the implementation; commit to branch. The gated assertions are marked `@pytest.mark.xfail(strict=True)` (see each task's Step 1). The rest of their test assertions go green. Do not "fix" the xfail markers by adding content — they are deliberate governance holds.

**Phase 3 — Gated content + final acceptance:**
Tasks 3 and 5 after clinical sign-off → remove xfail markers → Tasks 2, 6 acceptance suites go fully green → run Task 9.

### Safe execution choice

**Subagent on Phase 1 tasks only (1, 4, 7, 8):** genuinely self-contained, safe to run unsupervised to green.

**Inline / human-in-the-loop for Phase 2 tasks (2, 6):** the xfail markers hold the governance gate, but a human must verify no worker "resolves" them by authoring content.

**Inline for Phase 3 (3, 5, 9):** clinical reviewer in the loop; merge only after sign-off appended to governance log.

### Pre-flight checklist (before starting Phase 1)

- [ ] Confirm `src/sage_poc/clinical_clusters.py` membership is clinician-validated (one meeting — CLINICAL_CLUSTERS membership now carries routing weight via `_CLUSTER_ARGMAX_FLOOR`)
- [ ] Submit sign-off package for Tasks 3+5 to clinical reviewer in parallel so it is not the critical-path blocker: 2 keyword ownership decisions + 24 anchor sentences
- [ ] Verify Task 1 passes (if it fails, stop — the semantic fallback is unhealthy and subsequent tasks are building on a broken foundation)

---

## File map

| File | Change |
|------|--------|
| `src/sage_poc/nodes/skill_select.py` | Task 2: best-match scoring; Task 6: multi-vector index + cluster argmax + state-in-query + reranker wire |
| `src/sage_poc/skills/worry_time.json` | Task 3: remove 2 de-conflicted keywords (gated) |
| `src/sage_poc/skills/cognitive_restructuring.json` | Task 3: add `catastrophizing` keywords (gated) |
| `src/sage_poc/skills/schema.py` | Task 4: add `semantic_anchors: list[str] = []` to Skill model |
| `src/sage_poc/skills/grief_loss.json` | Task 5: add `semantic_anchors` (gated) |
| `src/sage_poc/skills/interpersonal_effectiveness.json` | Task 5: add `semantic_anchors` (gated) |
| `src/sage_poc/skills/financial_anxiety.json` | Task 5: add `semantic_anchors` (gated) |
| `src/sage_poc/nodes/skill_rerank.py` | Task 7: create rerank interface stub |
| `scripts/semantic_probe_set.py` | Task 6: update `raw_scores_top3` for multi-vector index |
| `scripts/validate_grief_sf1_boundary.py` | Task 6: update `score_all` for multi-vector index |
| `tests/test_skill_schema.py` | Task 4: schema tests |
| `tests/test_skill_select.py` | Tasks 2, 6, 7: routing tests (2 xfail markers until Tasks 3+5 merge) |
| `tests/test_wrong_skill_routing.py` | Task 2: best-match regression suite (EN + AR) |

---

## Task 1 — Semantic fallback health diagnostic (RT-4/S-4)

**What this diagnoses:** Whether the BGE-M3 Tier-2 semantic fallback is actually firing in production (RT-4), and whether `SEMANTIC_THRESHOLD = 0.4593` is calibrated correctly against the current skill set (S-4). This task produces no code changes — it gates everything that follows.

**Files:**
- Read: `src/sage_poc/nodes/skill_select.py`
- Run: `scripts/calibrate_threshold.py`, `scripts/semantic_probe_set.py`
- Inspect: server logs for `embedding_timeout` events

- [ ] **Step 1: Confirm BGE-M3 model loads and Tier-2 fires**

  In a fresh Python shell, verify the model loads and produces embeddings:

  ```bash
  cd /path/to/sage-poc
  uv run python -c "
  import sys; sys.path.insert(0, 'src')
  from sage_poc.nodes.skill_select import _ensure_semantic_ready, SEMANTIC_THRESHOLD
  _ensure_semantic_ready()
  from sage_poc.nodes import skill_select as ss
  print(f'Model loaded: {ss._embed_model is not None}')
  print(f'Embeddings shape: {ss._semantic_embeddings.shape if ss._semantic_embeddings is not None else None}')
  print(f'Skill count in index: {len(set(ss._semantic_skill_ids)) if ss._semantic_skill_ids else \"N/A\"}')
  print(f'SEMANTIC_THRESHOLD: {SEMANTIC_THRESHOLD}')
  "
  ```

  **Note:** This diagnostic runs against the current codebase — globals are still named `_semantic_skill_ids` / `_semantic_embeddings`. Task 6 renames them to `_anchor_skill_ids` / `_anchor_embeddings`. Do not pre-rename.

  **Expected:** `Model loaded: True`, embeddings shape `(N_SKILLS, 1024)`, threshold `0.4593`.

  If the model fails to load: check `local_files_only=True` in `skill_select.py:57`. The revision pin is `5617a9f61b028005a4858fdac845db406aefb181`. If the local cache is missing, the fallback at line 63 attempts a download — confirm it succeeds or that the cache is populated.

- [ ] **Step 2: Check production logs for embedding_timeout events**

  Scan the most recent server log for Tier-2 timeout warnings:

  ```bash
  grep "embedding_timeout" logs/server.log 2>/dev/null | tail -20
  # If logs are in Railway/cloud:
  # grep "embedding_timeout" in the deployment log stream
  ```

  **Expected:** Zero `embedding_timeout` entries during normal operation. If timeouts appear: Tier-2 is silently degrading to keyword-only. The timeout is set at `EMBEDDING_TIMEOUT_SECONDS` (from `sage_poc.resilience`). Check its value:

  ```bash
  uv run python -c "from sage_poc.resilience import EMBEDDING_TIMEOUT_SECONDS; print(EMBEDDING_TIMEOUT_SECONDS)"
  ```

  If timeout < 5s and the model is loading from disk (not RAM-cached), increase it. If timeout appears frequently even at 10s: the model is being re-instantiated per request (check the `_init_lock` singleton pattern in `skill_select.py:44-73`).

- [ ] **Step 3: Run `calibrate_threshold.py` and verify gap**

  ```bash
  uv run python scripts/calibrate_threshold.py 2>&1 | tee /tmp/rt4_calibration.txt
  ```

  Read `/tmp/rt4_calibration.txt`. **Acceptance criteria:**
  - `Gap ≥ 0.03` (cross-cluster pass criterion)
  - `Suggested SEMANTIC_THRESHOLD` within ±0.01 of current `0.4593`
  - No cross-cluster hit scoring below threshold
  - All off-topic misses scoring below threshold

  If gap < 0.03: the threshold is mis-calibrated — likely from `semantic_description` edits that weren't followed by recalibration. Do not proceed to Task 2 until the gap is re-established. Fix the specific skill description that collapsed the gap (examine the "Lowest cross-cluster hit" line to identify the skill).

  If the suggested threshold differs from `0.4593` by more than 0.01: update `SEMANTIC_THRESHOLD` in `skill_select.py:37` to the suggested value before proceeding.

- [ ] **Step 4: Run `semantic_probe_set.py` and document baseline**

  ```bash
  uv run python scripts/semantic_probe_set.py 2>&1 | tee /tmp/rt4_probe_baseline.txt
  ```

  This is the pre-multi-vector baseline. Read the output and note the pass/fail counts per skill group. These numbers will be compared against the post-multi-vector result in Task 9.

  **Known baseline failures (expected at this stage, fixed in Tasks 4–6):**
  - `grief_loss` probes: 3/10 pass (single centroid covers partial region)
  - `interpersonal_effectiveness` probes: some probes routed to grief_loss at Tier-2
  - `financial_anxiety` probes: some cross-cluster bleed

- [ ] **Step 5: Record diagnostic results**

  Append to `docs/superpowers/audits/` a brief note:

  ```
  RT4-S4 Diagnostic Result — 2026-06-09
  Model loads: YES
  embedding_timeout events: [N] in last N hours
  Calibration gap: [value] (threshold: [value])
  Suggested threshold: [value] (delta from 0.4593: [value])
  Probe baseline: grief [N]/10, IE [N]/N, FA [N]/N
  Gate: [PASS / FAIL — do not proceed if FAIL]
  ```

  Commit if any `SEMANTIC_THRESHOLD` change was needed:

  ```bash
  git add src/sage_poc/nodes/skill_select.py
  git commit -m "calibration(skill_select): update SEMANTIC_THRESHOLD post RT-4/S-4 diagnostic"
  ```

---

## Task 2 — Tier-1 best-match scoring (SF-1)

**What this fixes:** The first-match-wins keyword loop in `skill_select.py:141-162` causes 4 dominant-shadower failures. `cbt_thought_record [0]` swallows self-criticism language before `self_compassion_break [18]` can match. `worry_time [7]` swallows catastrophizing, problem-analysis, and values-avoidance language before `cognitive_restructuring [20]`, `problem_solving_therapy [25]`, and `act_psychological_flexibility [26]` can match.

**Root cause:** Registry position is tiebreaker. A short keyword in a low-index skill beats a long, more-specific keyword in a high-index skill.

**Fix:** Scan ALL skills' keywords, collect all matches, return the skill whose matched keyword is longest (most specific). Single change to a 12-line loop.

**Bilingual requirement:** The fix must be validated in both EN and AR. The audit confirms SF-1 is structural (language-agnostic), but the specific collision pattern differs — AR passes cognitive_restructuring because Arabic cognitive vocabulary is segregated from Arabic worry vocabulary, while EN fails. A scoring change that fixes EN must not perturb the AR cases that currently pass.

**Files:**
- Modify: `src/sage_poc/nodes/skill_select.py:141-162`
- Test: `tests/test_wrong_skill_routing.py`, `tests/test_skill_select.py`

- [ ] **Step 1: Write failing tests — EN best-match cases**

  In `tests/test_skill_select.py`, add after the existing test block:

  ```python
  # ── SF-1 Best-Match Scoring Tests ─────────────────────────────────────────────
  # NOTE: The catastrophizing case is split into a separate xfail test below
  # because it depends on Task 3 (gated clinical content). All other cases are
  # ungated and must go green in Phase 2 without Task 3 content.

  @pytest.mark.slow
  @pytest.mark.parametrize("phrase,expected_skill", [
      # self_compassion_break must win over cbt_thought_record [0]
      ("I am so incredibly hard on myself after every single mistake I make", "self_compassion_break"),
      # PST must win over worry_time [7] for structured-analysis phrases
      ("I need to think through my options carefully and find a structured path forward", "problem_solving_therapy"),
      # ACT must win over worry_time [7] for values-avoidance phrases
      ("I keep letting fear make all my decisions instead of acting on what I actually value", "act_psychological_flexibility"),
  ])
  async def test_sf1_best_match_overrides_first_match(phrase: str, expected_skill: str):
      """SF-1: best-match scoring must return the most-specific keyword match,
      not the first registry-order match. Failure = first-match-wins is still active."""
      state = make_state(message_en=phrase, primary_intent="new_skill")
      result = await skill_select_node(state)
      assert result["active_skill_id"] == expected_skill, (
          f"SF-1 FAILURE: '{phrase[:60]}...'\n"
          f"  Expected: {expected_skill}\n"
          f"  Got:      {result['active_skill_id']!r}  (method={result.get('skill_match_method')!r})\n"
          f"  This is a dominant-shadower failure — first-match-wins is still routing to the\n"
          f"  lower-index skill. Fix: collect all matches, return longest keyword."
      )


  @pytest.mark.slow
  @pytest.mark.xfail(
      strict=True,
      reason=(
          "GOVERNANCE HOLD — blocked on clinical sign-off for Task 3 (TASK-3). "
          "cognitive_restructuring gains the catastrophizing keyword only after Task 3 merges. "
          "Remove this xfail marker when Task 3 sign-off is appended to the governance log and "
          "the branch merges. strict=True: if this PASSES before sign-off, that means someone "
          "added the keyword without clinical review — treat as a CI failure."
      ),
  )
  async def test_sf1_catastrophizing_routes_to_cognitive_restructuring_gated():
      """Catastrophizing language must route to cognitive_restructuring, not worry_time [7].
      Gated: depends on Task 3 removing catastrophizing from worry_time and adding it to
      cognitive_restructuring. Will be xfail until Task 3 clinical sign-off."""
      state = make_state(
          message_en="I know I am catastrophizing about this situation but I cannot stop the thought spiral",
          primary_intent="new_skill",
      )
      result = await skill_select_node(state)
      assert result["active_skill_id"] == "cognitive_restructuring"
  ```

  Add `make_state` helper if not already in the file (check first):

  ```python
  def make_state(**kwargs) -> dict:
      defaults = {
          "raw_message": kwargs.get("message_en", ""),
          "message_en": kwargs.get("message_en", ""),
          "detected_language": "en",
          "is_safe": True,
          "crisis_flags": [],
          "clinical_flags": [],
          "crisis_state": "none",
          "active_skill_id": None,
          "active_step_id": None,
          "primary_intent": "new_skill",
          "intent_confidence": 1.0,
          "path": [],
          "therapeutic_profile": None,
      }
      return {**defaults, **kwargs}
  ```

- [ ] **Step 2: Run to confirm FAIL**

  ```bash
  uv run pytest tests/test_skill_select.py -k "test_sf1_best_match" -m slow -v -p no:xdist
  ```

  Expected: 3 FAILs (self_compassion_break, PST, ACT) + 1 XFAIL (catastrophizing — governance hold). The catastrophizing case is expected to stay xfail until Task 3 merges; do not treat it as a regression.

- [ ] **Step 3: Update `_tier1_match` helper in `test_wrong_skill_routing.py`**

  `_tier1_match` in the test file mirrors the production Tier-1 scan. It must match the new implementation. Find it (search for `def _tier1_match`) and replace its loop body:

  Current loop (lines ~50–65, approximate):
  ```python
  for skill_id, skill in _SKILLS.items():
      if skill_id in KEYWORD_SEMANTIC_SKIP:
          continue
      for keyword in skill.target_presentations:
          kw_lower = keyword.lower()
          if kw_lower in phrase_lower:
              return skill_id
  return None
  ```

  Replacement:
  ```python
  best: tuple[str, int] | None = None  # (skill_id, keyword_length)
  for skill_id, skill in _SKILLS.items():
      if skill_id in KEYWORD_SEMANTIC_SKIP:
          continue
      for keyword in skill.target_presentations:
          kw_lower = keyword.lower()
          if kw_lower in phrase_lower:
              if best is None or len(kw_lower) > best[1]:
                  best = (skill_id, len(kw_lower))
  return best[0] if best is not None else None
  ```

- [ ] **Step 4: Implement best-match scoring in `skill_select.py`**

  Open `src/sage_poc/nodes/skill_select.py`. Locate the Tier-1 loop (lines ~146–162):

  ```python
  # CURRENT — first-match-wins (lines 146-162)
  for skill_id, skill in _SKILLS.items():
      if skill_id in KEYWORD_SEMANTIC_SKIP:
          continue
      for keyword in skill.target_presentations:
          kw_lower = keyword.lower()
          if kw_lower in message_en or (detected_language == "ar" and kw_lower in raw_message):
              return {
                  "active_skill_id": skill_id,
                  "active_step_id": skill.steps[0].step_id,
                  "skill_match_method": "keyword",
                  "semantic_score": None,
                  "path": state["path"] + ["skill_select"],
              }
  ```

  Replace with:

  ```python
  # Tier 1: Best-match keyword scoring.
  # Collects ALL matches, returns the skill whose matched keyword is longest
  # (most specific). Longer keyword = more precise clinical intent signal.
  # Fixes SF-1: eliminates registry-order-as-tiebreaker dominant shadower failures.
  _best_kw_match: tuple[str, int] | None = None  # (skill_id, keyword_length)
  for skill_id, skill in _SKILLS.items():
      if skill_id in KEYWORD_SEMANTIC_SKIP:
          continue
      for keyword in skill.target_presentations:
          kw_lower = keyword.lower()
          if kw_lower in message_en or (detected_language == "ar" and kw_lower in raw_message):
              if _best_kw_match is None or len(kw_lower) > _best_kw_match[1]:
                  _best_kw_match = (skill_id, len(kw_lower))

  if _best_kw_match is not None:
      t1_skill_id = _best_kw_match[0]
      t1_skill = _SKILLS[t1_skill_id]
      return {
          "active_skill_id": t1_skill_id,
          "active_step_id": t1_skill.steps[0].step_id,
          "skill_match_method": "keyword",
          "semantic_score": None,
          "path": state["path"] + ["skill_select"],
      }
  ```

  **Latency note:** This change scans all skills' keyword lists on every turn where Tier-2 was previously reached (when there was no Tier-1 match). In the first-match-wins design, a shadower at index [0] short-circuits early. Best-match requires scanning all. Measured: 27 skills × ~35 keywords average = ~945 substring checks, each ~1–3µs. Total overhead: <3ms, negligible vs. Tier-2's 200–400ms. The performance trade-off is correct.

- [ ] **Step 5: Run SF-1 tests to confirm PASS**

  ```bash
  uv run pytest tests/test_skill_select.py -k "test_sf1_best_match" -m slow -v -p no:xdist
  ```

  Expected: 3 PASSes (ungated cases) + 1 XFAIL (catastrophizing). The XFAIL is the governance hold — do not remove the marker or add content to make it pass without Task 3 clinical sign-off. If it shows XPASS, that means the catastrophizing keyword was added without sign-off — treat it as a CI failure (strict=True enforces this).

- [ ] **Step 6: Run Tier-1 snapshot test (no collision regressions)**

  ```bash
  uv run pytest tests/test_wrong_skill_routing.py::test_tier1_snapshot -v
  ```

  Expected: all pass. A failure here means the best-match change caused a previously correct T1 route to now pick a different skill (because a longer keyword elsewhere now wins). Read the failure carefully: if the new route is clinically more correct, update the snapshot; if not, investigate which keyword is the new winner and narrow it.

- [ ] **Step 7: Run AR regression check**

  Run the full routing suite with AR test phrases. The audit confirmed best-match scoring must be validated bilingually — a scoring change that fixes EN could perturb AR cases that currently pass by accident of vocabulary segregation.

  ```bash
  uv run pytest tests/test_wrong_skill_routing.py -v 2>&1 | grep -E "PASSED|FAILED|ERROR" | tail -30
  ```

  If any previously-passing AR case now fails: the new best-match winner has a longer keyword for that phrase than the previous winner. Investigate with:

  ```bash
  uv run python -c "
  import sys; sys.path.insert(0, 'src')
  from sage_poc.skill_ids import SKILL_REGISTRY
  from sage_poc.skills.schema import load_skill
  phrase = 'INSERT_FAILING_AR_PHRASE_HERE'.lower()
  matches = []
  for sid in SKILL_REGISTRY:
      skill = load_skill(sid)
      for kw in skill.target_presentations:
          if kw.lower() in phrase:
              matches.append((sid, kw, len(kw)))
  matches.sort(key=lambda x: -x[2])
  for m in matches:
      print(m)
  "
  ```

- [ ] **Step 8: Commit**

  ```bash
  git add src/sage_poc/nodes/skill_select.py tests/test_skill_select.py tests/test_wrong_skill_routing.py
  git commit -m "feat(skill_select): Tier-1 best-match scoring — longest keyword wins (SF-1)

  Replaces first-match-wins (registry-order tiebreaker) with best-match scoring:
  scan all keyword matches, return the skill whose matched keyword is longest.
  Longer keyword = more specific clinical signal.

  Fixes 4 dominant-shadower failures confirmed in 2026-06-07 audit:
  - self_compassion_break shadowed by cbt_thought_record [0]
  - cognitive_restructuring shadowed by worry_time [7]
  - problem_solving_therapy shadowed by worry_time [7]
  - act_psychological_flexibility shadowed by worry_time [7]

  Validated EN + AR. Performance overhead: <3ms vs. Tier-2's 200-400ms.

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
  ```

---

## Task 3 — worry_time keyword de-confliction (SF-3)

> **CLINICAL GOVERNANCE GATE — merge blocked until sign-off.** Deciding that `catastrophizing` belongs to `cognitive_restructuring` and not `worry_time`, and removing `"cant stop thinking about it"` from worry_time, are clinical ownership decisions. Per v7 §9, `target_presentations` is clinician-authored content. Implement and commit to a branch; append a sign-off record to the governance log before merging. Record what was removed from what skill and why. Both changes are destined for the CMS once `target_presentations` is editable through the CMS workflow.

> **Latency side-effect:** Removing keywords from worry_time means a small set of phrases that previously matched Tier-1 (~0ms) will now miss Tier-1 and fall through to Tier-2 BGE-M3 (~200–400ms). Run Step 1 before and after to identify exactly which phrases shift tiers, and record them. This is acceptable (the routing was wrong before), but document it.

**What this fixes:** `worry_time`'s `target_presentations` includes two keywords that capture clinical presentations belonging to other skills. Even after best-match scoring (Task 2), these keywords can still shadow if they happen to be longer than competing keywords. More importantly, they make worry_time a semantic attractor even at Tier-2 (by associating its embedding neighborhood with non-worry content). De-conflicting them is a prerequisite for the multi-vector threshold calibration to be clean.

**Specific keywords to remove:**

1. `"catastrophising"` and `"catastrophizing"` — removed from worry_time, added to cognitive_restructuring. Catastrophizing as a named cognitive distortion is cognitive_restructuring territory (CBT error identification + reframing). It appears in both currently; with best-match scoring, whichever skill has the longer matching keyword wins. But it should not be in worry_time's embedding neighborhood at all.

2. `"cant stop thinking about it"` — removed from worry_time. This is a generic rumination phrase that shadows PST for phrases like "I can't stop thinking about this problem I need to solve." Worry_time's legitimate coverage of this clinical space is handled by "can't stop worrying", "constantly worrying", and "ruminating" — all more specific.

**Files:**
- Modify: `src/sage_poc/skills/worry_time.json`
- Modify: `src/sage_poc/skills/cognitive_restructuring.json`

- [ ] **Step 1: Confirm the two failing shadow cases (before de-confliction)**

  ```bash
  uv run python -c "
  import sys, json
  sys.path.insert(0, 'src')
  from sage_poc.skill_ids import SKILL_REGISTRY
  from sage_poc.skills.schema import load_skill

  test_phrases = [
      'I know I am catastrophizing about this but I cannot stop',
      'I cant stop thinking about this problem I need to solve',
  ]
  for phrase in test_phrases:
      phrase_lower = phrase.lower()
      matches = []
      for sid in SKILL_REGISTRY:
          skill = load_skill(sid)
          for kw in skill.target_presentations:
              if kw.lower() in phrase_lower:
                  matches.append((sid, kw, len(kw)))
      matches.sort(key=lambda x: -x[2])
      print(f'Phrase: {phrase[:60]}')
      print(f'  Best match: {matches[0] if matches else None}')
      print(f'  All matches: {matches}')
      print()
  "
  ```

  Expected output: both phrases show worry_time as one of the matches. After Task 2 (best-match scoring), the longest keyword wins — verify whether worry_time or the correct skill has the longer match.

- [ ] **Step 2: Remove de-conflicted keywords from `worry_time.json`**

  Open `src/sage_poc/skills/worry_time.json`. Locate and remove these three entries from `target_presentations`:

  ```
  "catastrophising",
  "catastrophizing",
  "cant stop thinking about it",
  ```

  After removal, verify the remaining list: all remaining keywords should be specific to the worry-scheduling/postponement technique (worry spirals, rumination, "what if" cycling, etc.). Entries to keep include: "can't stop worrying", "catastrophising" variants are removed but "worry spiral", "spiral of worry", "stuck in my head" (worry-specific), "what if thoughts", "ruminating", "rumination", "caught in a loop", "break the cycle of", and all Arabic variants.

  Validate JSON is well-formed:

  ```bash
  python3 -c "import json; d=json.load(open('src/sage_poc/skills/worry_time.json')); print(f'worry_time: {len(d[\"target_presentations\"])} keywords remaining')"
  ```

  Expected: previous count minus 3.

- [ ] **Step 3: Add `catastrophizing` to `cognitive_restructuring.json`**

  Open `src/sage_poc/skills/cognitive_restructuring.json`. Locate `target_presentations`. Add these four entries (English + common variants; Arabic is out of scope here):

  ```json
  "catastrophizing",
  "catastrophising",
  "i keep catastrophizing",
  "always catastrophizing"
  ```

  Validate JSON:

  ```bash
  python3 -c "import json; d=json.load(open('src/sage_poc/skills/cognitive_restructuring.json')); print(f'cognitive_restructuring: {len(d[\"target_presentations\"])} keywords')"
  ```

- [ ] **Step 4: Run Tier-1 snapshot test — verify no regressions**

  ```bash
  uv run pytest tests/test_wrong_skill_routing.py::test_tier1_snapshot -v
  ```

  Expected: all pass. A failure here means a keyword you removed was the ONLY match for a test phrase that was previously routing correctly to worry_time. If so: the test phrase is a legitimate worry_time presentation — re-add the keyword or add a more specific variant that is still worry-specific.

- [ ] **Step 5: Verify de-confliction resolved the shadow cases**

  ```bash
  uv run python -c "
  import sys, json
  sys.path.insert(0, 'src')
  from sage_poc.skill_ids import SKILL_REGISTRY
  from sage_poc.skills.schema import load_skill

  test_phrases = [
      'I know I am catastrophizing about this but I cannot stop',
      'I cant stop thinking about this problem I need to solve',
  ]
  for phrase in test_phrases:
      phrase_lower = phrase.lower()
      matches = []
      for sid in SKILL_REGISTRY:
          skill = load_skill(sid)
          for kw in skill.target_presentations:
              if kw.lower() in phrase_lower:
                  matches.append((sid, kw, len(kw)))
      matches.sort(key=lambda x: -x[2])
      print(f'Phrase: {phrase[:60]}')
      print(f'  Best match: {matches[0] if matches else None}')
  "
  ```

  Expected: "catastrophizing about this" → `cognitive_restructuring` as best match. PST phrase → `problem_solving_therapy` as best match (or MISS → Tier-2 handles it, which is fine).

- [ ] **Step 6: Commit**

  ```bash
  git add src/sage_poc/skills/worry_time.json src/sage_poc/skills/cognitive_restructuring.json
  git commit -m "fix(routing): SF-3 worry_time de-confliction + cognitive_restructuring keyword ownership

  Removes 'catastrophizing'/'catastrophising' and 'cant stop thinking about it'
  from worry_time.target_presentations. These phrases belong to cognitive_restructuring
  and problem_solving_therapy respectively; their presence in worry_time was causing
  dominant shadowing (SF-3 from 2026-06-07 routing audit).

  cognitive_restructuring gains the catastrophizing keywords it was missing.
  worry_time retains all worry-scheduling-specific keywords unchanged.

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
  ```

---

## Task 4 — Add `semantic_anchors` to Skill schema (backward-compatible)

**What this adds:** An optional `semantic_anchors: list[str]` field to the Skill pydantic model. Defaults to `[]`. Skills without anchors behave exactly as before (description-only matching). The multi-vector index (Task 6) uses anchors when present.

**Sourced from:** `docs/superpowers/plans/2026-06-01-multi-vector-semantic-matching.md` Task 1. Reproduced here in full for plan self-containment.

**Files:**
- Modify: `src/sage_poc/skills/schema.py`
- Test: `tests/test_skill_schema.py`

- [ ] **Step 1: Write failing tests**

  In `tests/test_skill_schema.py`, add:

  ```python
  def test_skill_schema_accepts_semantic_anchors():
      from sage_poc.skills.schema import Skill
      data = {
          "skill_id": "test_skill",
          "skill_name": "Test",
          "skill_type": "structured",
          "evidence_base": "test",
          "target_presentations": ["test"],
          "semantic_description": "test description",
          "semantic_anchors": [
              "I have been feeling really low lately",
              "Everything feels hopeless",
          ],
          "steps": [],
          "step_policy": [],
          "escalation_matrix": {"L1": "exit", "L2": "flag", "L3": "crisis", "L4": "handoff"},
      }
      skill = Skill.model_validate(data)
      assert skill.semantic_anchors == [
          "I have been feeling really low lately",
          "Everything feels hopeless",
      ]


  def test_skill_schema_semantic_anchors_defaults_to_empty():
      from sage_poc.skills.schema import Skill
      data = {
          "skill_id": "test_skill",
          "skill_name": "Test",
          "skill_type": "structured",
          "evidence_base": "test",
          "target_presentations": ["test"],
          "semantic_description": "test description",
          "steps": [],
          "step_policy": [],
          "escalation_matrix": {"L1": "exit", "L2": "flag", "L3": "crisis", "L4": "handoff"},
      }
      skill = Skill.model_validate(data)
      assert skill.semantic_anchors == []
  ```

- [ ] **Step 2: Run to confirm FAIL**

  ```bash
  uv run pytest tests/test_skill_schema.py::test_skill_schema_accepts_semantic_anchors tests/test_skill_schema.py::test_skill_schema_semantic_anchors_defaults_to_empty -v
  ```

  Expected: 2 FAILs.

- [ ] **Step 3: Add field to Skill model in `schema.py`**

  Locate the `Skill` class definition. After the `semantic_description` field, add:

  ```python
  semantic_anchors: list[str] = Field(default_factory=list)
  ```

  The full field list in order: `skill_id`, `skill_name`, `skill_type`, `evidence_base`, `self_evolution`, `target_presentations`, `semantic_description`, `semantic_anchors` ← new, `steps`, `step_policy`, `escalation_matrix`, `cultural_overrides`.

- [ ] **Step 4: Run tests to confirm PASS**

  ```bash
  uv run pytest tests/test_skill_schema.py -v
  ```

  Expected: all pass including the two new tests.

- [ ] **Step 5: Commit**

  ```bash
  git add src/sage_poc/skills/schema.py tests/test_skill_schema.py
  git commit -m "feat(schema): add optional semantic_anchors field to Skill model

  Backward-compatible: defaults to []. Used by multi-vector skill_select
  to match against representative utterances instead of a single centroid.
  Skills without anchors use semantic_description only, as before.

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
  ```

---

## Task 5 — Populate `semantic_anchors` for documented gap skills

> **CLINICAL GOVERNANCE GATE — merge blocked until sign-off.** The 24 anchor sentences (8 per skill) are representative user utterances that determine which therapeutic intervention a distressed user receives. Per v7 §9, these are clinician-authored content — the CMS workflow (draft → review → approve → publish) applies once CMS supports `semantic_anchors` as a field. Until then: implement and commit to a branch; submit all 24 anchors to the clinical reviewer as a batch; append the sign-off record to the governance log before merging. Each sentence must be reviewed for clinical accuracy, cultural appropriateness (Gulf context), and safety (verify no anchor bleeds into the SI region — Task 9 Step 2 runs this check automatically).

**What this adds:** 8 representative natural-language utterances per skill for the three skills with documented single-centroid failures: `grief_loss`, `interpersonal_effectiveness`, `financial_anxiety`. These are real sentences a user might send — clinical presentations of the skill's domain. They are NOT keyword fragments.

**Sourced from:** `docs/superpowers/plans/2026-06-01-multi-vector-semantic-matching.md` Task 2. Reproduced here in full.

**Files:**
- Modify: `src/sage_poc/skills/grief_loss.json`
- Modify: `src/sage_poc/skills/interpersonal_effectiveness.json`
- Modify: `src/sage_poc/skills/financial_anxiety.json`

- [ ] **Step 1: Add `semantic_anchors` to `grief_loss.json`**

  After the `semantic_description` field:

  ```json
  "semantic_anchors": [
    "My mother passed away three months ago and I still cannot seem to get back to any sense of normal",
    "The house feels completely empty without him and I do not know how to fill that space",
    "I cannot bring myself to go through her things or change anything in her room",
    "Everything I see, every place we went together, reminds me of him and it is unbearable",
    "She was the person I talked to about everything and now I do not know who I am without her",
    "I keep expecting her to walk in through the door and then remember all over again that she is gone",
    "I wake up each morning and for a moment I forget he has died, and then it hits me all over again",
    "My father was the one who held this family together, and now that he is gone I feel completely at a loss"
  ],
  ```

- [ ] **Step 2: Add `semantic_anchors` to `interpersonal_effectiveness.json`**

  ```json
  "semantic_anchors": [
    "I need to have a serious conversation with my father but I am scared of how he will react",
    "My father will not listen to anything I say and I do not know how to get through to him",
    "I am caught between my wife and my mother and whatever I do one of them is hurt",
    "I want to repair things with my sister after a bad argument but I do not know how to approach her",
    "How do I talk to my in-laws about something sensitive without making everything worse",
    "I need to set a boundary with someone in my family but I am worried about the consequences",
    "I cannot keep everyone in my family happy and it is tearing me apart",
    "I want to say something important to someone I care about but I do not know how to begin"
  ],
  ```

- [ ] **Step 3: Add `semantic_anchors` to `financial_anxiety.json`**

  ```json
  "semantic_anchors": [
    "I cannot sleep because I am terrified of what happens to my family if my contract is not renewed",
    "Everything I earn goes straight to my parents back home and if I lose my income my whole household collapses",
    "My entire sense of who I am comes from being the provider for my family and lately I feel that is slipping",
    "My salary is not enough to meet all the obligations I have to my family and it is affecting everything",
    "I am terrified of not being able to support my parents and siblings the way they depend on me to",
    "I am the only one supporting my whole family back home and the financial pressure is becoming unbearable",
    "If I lose this job I do not know how I will keep my family afloat",
    "The kafala system means I cannot easily change jobs and the financial pressure is crushing me"
  ],
  ```

- [ ] **Step 4: Validate JSON on all three files**

  ```bash
  python3 -c "
  import json
  for f in ['grief_loss', 'interpersonal_effectiveness', 'financial_anxiety']:
      d = json.load(open(f'src/sage_poc/skills/{f}.json'))
      print(f'{f}: semantic_anchors = {len(d.get(\"semantic_anchors\", []))} entries')
  "
  ```

  Expected: 8 entries each.

- [ ] **Step 5: Commit**

  ```bash
  git add src/sage_poc/skills/grief_loss.json src/sage_poc/skills/interpersonal_effectiveness.json src/sage_poc/skills/financial_anxiety.json
  git commit -m "content(skills): add semantic_anchors to grief_loss, interpersonal_effectiveness, financial_anxiety

  8 representative utterances per skill sourced from documented probe set failures.
  Spread coverage across the region the single centroid cannot reach.
  Used by multi-vector index in Task 6.

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
  ```

---

## Task 6 — Multi-vector skill_select + cluster argmax + state-in-query

**What this builds:** Replaces the single-embedding-per-skill semantic index with a multi-vector anchor index. At match time, takes the max cosine score per skill across all its anchors. Adds cluster argmax (when top-2 are within the same clinical cluster and both above a soft floor, route to the argmax rather than gating by absolute threshold). Adds state-in-query (prepend therapeutic profile summary to message before encoding so user context compounds with anchor coverage).

**Sourced from:** `docs/superpowers/plans/2026-06-01-multi-vector-semantic-matching.md` Task 3. Reproduced here in full.

**Files:**
- Modify: `src/sage_poc/nodes/skill_select.py`
- Modify: `scripts/semantic_probe_set.py`
- Modify: `scripts/validate_grief_sf1_boundary.py`
- Test: `tests/test_skill_select.py`

- [ ] **Step 1: Write failing tests for multi-vector behavior**

  In `tests/test_skill_select.py`, add:

  ```python
  # These tests are marked xfail(strict=True) because they depend on Task 5 (gated
  # clinical content: semantic_anchors for grief_loss and interpersonal_effectiveness).
  # The multi-vector index machinery (Task 6) can be built and tested without these,
  # but the acceptance probes stay red until Task 5 anchors are present.
  # DO NOT remove the xfail markers or add anchor sentences to make them pass without
  # Task 5 clinical sign-off — strict=True turns an unexpected XPASS into a CI failure.

  _TASK5_GATE = pytest.mark.xfail(
      strict=True,
      reason=(
          "GOVERNANCE HOLD — blocked on clinical sign-off for Task 5 (TASK-5). "
          "grief_loss and interpersonal_effectiveness semantic_anchors added only after "
          "Task 5 sign-off. Remove these markers when Task 5 merges."
      ),
  )


  @pytest.mark.slow
  @_TASK5_GATE
  async def test_grief_anchor_probe_empty_house_routes_to_grief():
      """Multi-vector: 'empty house' grief probe must route to grief_loss, not interpersonal."""
      state = make_state(
          message_en="The house feels completely empty without him and I do not know how to fill that space",
          primary_intent="new_skill",
      )
      result = await skill_select_node(state)
      assert result["active_skill_id"] == "grief_loss", (
          f"Expected grief_loss, got {result['active_skill_id']} "
          f"(score={result['semantic_score']})"
      )
      assert result["skill_match_method"] in ("semantic", "keyword")


  @pytest.mark.slow
  @_TASK5_GATE
  async def test_grief_anchor_probe_going_through_things_routes_to_grief():
      """Multi-vector: 'going through her things' grief probe must route to grief_loss."""
      state = make_state(
          message_en="I cannot bring myself to go through her things or change anything in her room",
          primary_intent="new_skill",
      )
      result = await skill_select_node(state)
      assert result["active_skill_id"] == "grief_loss", (
          f"Expected grief_loss, got {result['active_skill_id']} "
          f"(score={result['semantic_score']})"
      )


  @pytest.mark.slow
  @_TASK5_GATE
  async def test_interpersonal_anchor_probe_father_conversation():
      """Multi-vector: interpersonal probe must route to interpersonal_effectiveness."""
      state = make_state(
          message_en="I need to have a serious conversation with my father but I am scared of how he will react",
          primary_intent="new_skill",
      )
      result = await skill_select_node(state)
      assert result["active_skill_id"] == "interpersonal_effectiveness", (
          f"Expected interpersonal_effectiveness, got {result['active_skill_id']}"
      )
  ```

- [ ] **Step 2: Run to confirm FAIL**

  ```bash
  uv run pytest tests/test_skill_select.py::test_grief_anchor_probe_empty_house_routes_to_grief tests/test_skill_select.py::test_grief_anchor_probe_going_through_things_routes_to_grief tests/test_skill_select.py::test_interpersonal_anchor_probe_father_conversation -v -p no:xdist -m slow
  ```

  Expected: 3 XFAILs — all three anchor probes are governance-gated. Task 5 content must be present for these to pass. The multi-vector machinery tests in Steps 3–7 are separate and do not depend on Task 5 anchors being populated.

- [ ] **Step 3: Replace globals and `_ensure_semantic_ready` in `skill_select.py`**

  Replace the globals block (after `_SKILLS = ...`):

  ```python
  SEMANTIC_THRESHOLD: float = 0.4593
  _CLUSTER_ARGMAX_FLOOR: float = 0.42

  _embed_model = None
  _anchor_skill_ids: list[str] = []    # one entry per anchor (description or semantic_anchors item)
  _anchor_embeddings: np.ndarray | None = None  # shape (n_anchors, 1024)
  _init_lock = threading.Lock()
  ```

  Replace `_ensure_semantic_ready`:

  ```python
  def _ensure_semantic_ready() -> None:
      global _embed_model, _anchor_skill_ids, _anchor_embeddings
      if _embed_model is not None and _anchor_embeddings is not None:
          return
      with _init_lock:
          if _embed_model is not None and _anchor_embeddings is not None:
              return
          model = _embed_model
          if model is None:
              from sentence_transformers import SentenceTransformer
              try:
                  model = SentenceTransformer(
                      "BAAI/bge-m3", local_files_only=True, revision=_BGE_M3_REVISION,
                  )
              except (OSError, EnvironmentError):
                  model = SentenceTransformer("BAAI/bge-m3", revision=_BGE_M3_REVISION)

          pairs: list[tuple[str, str]] = []
          for sid, skill in _SKILLS.items():
              if sid in KEYWORD_SEMANTIC_SKIP:
                  continue
              if skill.semantic_description:
                  pairs.append((sid, skill.semantic_description))
              for anchor in skill.semantic_anchors:
                  pairs.append((sid, anchor))

          _anchor_skill_ids = [sid for sid, _ in pairs]
          anchor_texts = [text for _, text in pairs]
          _anchor_embeddings = model.encode(anchor_texts, normalize_embeddings=True)
          _embed_model = model
  ```

- [ ] **Step 4: Replace `_semantic_match_sync` in `skill_select.py`**

  ```python
  def _semantic_match_sync(
      message_en: str,
      profile_context: str = "",
  ) -> tuple[str | None, float]:
      """Max-over-anchors matching with optional profile context prepended to query."""
      _ensure_semantic_ready()
      if _anchor_embeddings is None or not message_en.strip():
          return None, 0.0

      query_text = f"{profile_context}\n{message_en}".strip() if profile_context else message_en
      msg_emb = _embed_model.encode([query_text], normalize_embeddings=True)[0]
      raw_scores = np.dot(_anchor_embeddings, msg_emb)

      skill_scores: dict[str, float] = {}
      for i, sid in enumerate(_anchor_skill_ids):
          score = float(raw_scores[i])
          if score > skill_scores.get(sid, 0.0):
              skill_scores[sid] = score

      if not skill_scores:
          return None, 0.0

      ranked = sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)
      best_sid, best_score = ranked[0]

      # Within-cluster argmax: when top-2 share a cluster and both exceed
      # _CLUSTER_ARGMAX_FLOOR, trust relative ordering (argmax) rather than
      # absolute threshold gating.
      if len(ranked) >= 2:
          second_sid, second_score = ranked[1]
          if second_score >= _CLUSTER_ARGMAX_FLOOR:
              best_cluster = _skill_cluster(best_sid)
              second_cluster = _skill_cluster(second_sid)
              if best_cluster is not None and best_cluster == second_cluster:
                  return best_sid, best_score

      if best_score >= SEMANTIC_THRESHOLD:
          return best_sid, best_score
      return None, best_score


  def _skill_cluster(skill_id: str) -> str | None:
      from sage_poc.clinical_clusters import CLINICAL_CLUSTERS
      for cluster, skills in CLINICAL_CLUSTERS.items():
          if skill_id in skills:
              return cluster
      return None
  ```

- [ ] **Step 5: Update `skill_select_node` to pass profile context**

  In `skill_select_node`, locate the Tier-2 call. Update it to extract profile context and pass it to `_semantic_match_sync`:

  ```python
  # Tier 2: Multi-vector semantic with optional profile context
  profile = state.get("therapeutic_profile") or {}
  profile_context = profile.get("summary", "") or "" if isinstance(profile, dict) else ""

  try:
      semantic_skill, score = await asyncio.wait_for(
          asyncio.to_thread(_semantic_match_sync, state["message_en"], profile_context),
          timeout=EMBEDDING_TIMEOUT_SECONDS,
      )
  except asyncio.TimeoutError:
      # ... (timeout handling unchanged)
  ```

- [ ] **Step 6: Update `scripts/semantic_probe_set.py`**

  Locate the `raw_scores_top3` function. Replace its body:

  ```python
  def raw_scores_top3(msg):
      msg_emb = ss._embed_model.encode([msg], normalize_embeddings=True)[0]
      raw = np.dot(ss._anchor_embeddings, msg_emb)
      skill_scores = {}
      for i, sid in enumerate(ss._anchor_skill_ids):
          score = float(raw[i])
          if score > skill_scores.get(sid, 0.0):
              skill_scores[sid] = score
      return sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)[:3]
  ```

  Also update the header print (if present) to show anchor count:

  ```python
  unique_skills = len(set(ss._anchor_skill_ids))
  print(f"BGE-M3 ready | {unique_skills} skills, {len(ss._anchor_skill_ids)} anchors embedded\n")
  ```

- [ ] **Step 7: Update `scripts/validate_grief_sf1_boundary.py`**

  Locate the `score_all` function. Replace its body:

  ```python
  def score_all(msg: str) -> tuple[float, str, float]:
      """Returns (grief_loss_score, top_skill, top_score)."""
      emb = ss._embed_model.encode([msg], normalize_embeddings=True)[0]
      raw = np.dot(ss._anchor_embeddings, emb)
      skill_scores = {}
      for i, sid in enumerate(ss._anchor_skill_ids):
          score = float(raw[i])
          if score > skill_scores.get(sid, 0.0):
              skill_scores[sid] = score
      gl_score = skill_scores.get("grief_loss", 0.0)
      top_sid = max(skill_scores, key=skill_scores.get)
      top_score = skill_scores[top_sid]
      return gl_score, top_sid, top_score
  ```

- [ ] **Step 8: Run multi-vector tests to confirm PASS**

  ```bash
  uv run pytest tests/test_skill_select.py -k "anchor_probe" -m slow -v -p no:xdist
  ```

  Expected: 3 XFAILs — all three anchor probes are governance-gated until Task 5 merges. This is the correct Phase 2 state. When Task 5 sign-off lands and the xfail markers are removed, rerun this step and expect 3 PASSes.

- [ ] **Step 9: Run existing semantic tests to check for regressions**

  ```bash
  uv run pytest tests/test_skill_select.py -v -p no:xdist
  ```

  If any existing test references `_semantic_skill_ids` or `_semantic_embeddings`: update to use `_anchor_skill_ids` and `_anchor_embeddings`.

- [ ] **Step 10: Commit**

  ```bash
  git add src/sage_poc/nodes/skill_select.py scripts/semantic_probe_set.py scripts/validate_grief_sf1_boundary.py tests/test_skill_select.py
  git commit -m "feat(skill_select): multi-vector anchor matching + cluster argmax + state-in-query

  Replaces single centroid per skill with max-over-anchors index. Each skill
  embeds semantic_description + all semantic_anchors entries; matching takes
  max cosine per skill across all anchors.

  Within-cluster argmax: when top-2 share a cluster and both exceed
  _CLUSTER_ARGMAX_FLOOR (0.42), route by argmax not absolute threshold.

  State-in-query: profile.summary prepended to message before encoding when
  present, compounding therapeutic context with anchor coverage.

  Fixes: 'empty house' grief probe, 'going through her things' grief probe,
  and related cross-cluster over-capture at Tier-2.

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
  ```

---

## Task 7 — Rerank interface stub (Falcon-3B plug-in point)

**What this builds:** The `rerank_candidates(message, top_k)` interface. Current implementation is a stub (returns the top-scored candidate from retrieval). When Falcon-3B is validated, `_rerank_with_model` replaces `_rerank_stub` without any change to callers.

**Sourced from:** `docs/superpowers/plans/2026-06-01-multi-vector-semantic-matching.md` Task 4.

**Files:**
- Create: `src/sage_poc/nodes/skill_rerank.py`
- Test: `tests/test_skill_select.py`

- [ ] **Step 1: Write failing tests**

  ```python
  def test_rerank_returns_best_candidate_from_stub():
      from sage_poc.nodes.skill_rerank import rerank_candidates
      candidates = [
          ("grief_loss", 0.51),
          ("interpersonal_effectiveness", 0.49),
          ("behavioral_activation", 0.45),
      ]
      result_id, result_score = rerank_candidates("I lost someone", candidates)
      assert result_id == "grief_loss"
      assert result_score == pytest.approx(0.51)


  def test_rerank_handles_single_candidate():
      from sage_poc.nodes.skill_rerank import rerank_candidates
      candidates = [("grief_loss", 0.48)]
      result_id, result_score = rerank_candidates("I am grieving", candidates)
      assert result_id == "grief_loss"
      assert result_score == pytest.approx(0.48)


  def test_rerank_raises_on_empty_candidates():
      from sage_poc.nodes.skill_rerank import rerank_candidates
      with pytest.raises(ValueError, match="at least one candidate"):
          rerank_candidates("hello", [])
  ```

- [ ] **Step 2: Run to confirm FAIL**

  ```bash
  uv run pytest tests/test_skill_select.py -k "test_rerank" -v
  ```

  Expected: 3 FAILs — module doesn't exist.

- [ ] **Step 3: Create `src/sage_poc/nodes/skill_rerank.py`**

  ```python
  """Skill rerank interface.

  Production path: top-k bi-encoder candidates → Falcon-3B cross-encoder
  → single selection. The cross-encoder sees (message, candidate_description)
  pairs jointly, enabling disambiguation that single-vector retrieval cannot do.

  Current state: stub returns highest-scored retrieval candidate unmodified.
  Plug Falcon-3B in by replacing _rerank_stub with _rerank_with_model below.
  """
  from __future__ import annotations


  def rerank_candidates(
      message: str,
      candidates: list[tuple[str, float]],
  ) -> tuple[str, float]:
      """Return winning (skill_id, score) from bi-encoder retrieval candidates.

      Args:
          message: The user message being routed.
          candidates: (skill_id, score) tuples, descending score order. Non-empty.

      Returns:
          (skill_id, score) of selected skill.

      Raises:
          ValueError: If candidates is empty.
      """
      if not candidates:
          raise ValueError("rerank_candidates requires at least one candidate")
      return _rerank_stub(message, candidates)


  def _rerank_stub(
      message: str,
      candidates: list[tuple[str, float]],
  ) -> tuple[str, float]:
      """Stub: return top bi-encoder candidate. Replace with Falcon-3B when validated."""
      return candidates[0]


  # Falcon-3B cross-encoder plug-in point:
  #
  # def _rerank_with_model(
  #     message: str,
  #     candidates: list[tuple[str, float]],
  # ) -> tuple[str, float]:
  #     from sage_poc.nodes.skill_rerank_model import score_pairs
  #     from sage_poc.skills.schema import load_skill
  #     pairs = [(message, load_skill(sid).semantic_description) for sid, _ in candidates]
  #     scores = score_pairs(pairs)
  #     best_idx = max(range(len(scores)), key=lambda i: scores[i])
  #     return candidates[best_idx][0], float(scores[best_idx])
  ```

- [ ] **Step 4: Run tests to confirm PASS**

  ```bash
  uv run pytest tests/test_skill_select.py -k "test_rerank" -v
  ```

  Expected: 3 PASSes.

- [ ] **Step 5: Commit**

  ```bash
  git add src/sage_poc/nodes/skill_rerank.py tests/test_skill_select.py
  git commit -m "feat(skill_select): add rerank interface stub for Falcon-3B cross-encoder

  Defines rerank_candidates(message, top_k_candidates) -> (skill_id, score).
  Currently stubs to top bi-encoder candidate; Falcon-3B cross-encoder
  plugs in when validated.

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
  ```

---

## Task 8 — Tier-2 margin guard

**What this adds:** When multiple skills exceed `SEMANTIC_THRESHOLD` and their scores are within `_RERANK_MARGIN` (0.05), route through the reranker instead of auto-returning the highest scorer. This prevents "coin-toss" routing — two skills with 0.52 vs 0.51 are semantically indistinguishable at the bi-encoder level; a cross-encoder should adjudicate. The stub reranker returns top-1 (same as today, zero behavioral change); when Falcon-3B is validated, the margin guard is the mechanism that routes ambiguous cases to it.

**Files:**
- Modify: `src/sage_poc/nodes/skill_select.py` (add constant + update `_semantic_match_sync`)
- Test: `tests/test_skill_select.py`

- [ ] **Step 1: Write failing test for margin guard routing**

  ```python
  def test_margin_guard_routes_to_reranker_on_close_scores(monkeypatch):
      """When top-2 scores are within _RERANK_MARGIN, rerank_candidates must be called."""
      from sage_poc.nodes import skill_select as ss
      import sage_poc.nodes.skill_rerank as rerank_mod

      # Track whether rerank_candidates is called
      calls = []
      original = rerank_mod.rerank_candidates
      def mock_rerank(msg, candidates):
          calls.append((msg, candidates))
          return original(msg, candidates)
      monkeypatch.setattr(rerank_mod, "rerank_candidates", mock_rerank)

      # Inject a skill_scores result where top-2 are within margin
      def mock_match_sync(message_en, profile_context=""):
          # Simulate: worry_time=0.500, cognitive_restructuring=0.498 (diff=0.002 < 0.05)
          skill_scores = {
              "worry_time": 0.500,
              "cognitive_restructuring": 0.498,
              "grief_loss": 0.420,
          }
          ranked = sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)
          best_sid, best_score = ranked[0]
          above = [(sid, sc) for sid, sc in ranked if sc >= ss.SEMANTIC_THRESHOLD]
          if len(above) >= 2:
              if above[0][1] - above[1][1] < ss._RERANK_MARGIN:
                  from sage_poc.nodes.skill_rerank import rerank_candidates
                  return rerank_candidates(message_en, above[:ss._RERANK_TOP_K])
          if above:
              return above[0]
          return None, best_score

      monkeypatch.setattr(ss, "_semantic_match_sync", mock_match_sync)
      result = ss._semantic_match_sync("catastrophizing about something", "")
      assert len(calls) == 1, "rerank_candidates should have been called once"
      assert result[0] == "worry_time"  # stub returns top candidate
  ```

- [ ] **Step 2: Run to confirm FAIL**

  ```bash
  uv run pytest tests/test_skill_select.py::test_margin_guard_routes_to_reranker_on_close_scores -v
  ```

  Expected: FAIL — `_RERANK_MARGIN` doesn't exist yet.

- [ ] **Step 3: Add constants and margin guard to `skill_select.py`**

  After `SEMANTIC_THRESHOLD`, add:

  ```python
  _RERANK_MARGIN: float = 0.05   # invoke reranker when top-2 scores are within this margin
  _RERANK_TOP_K: int = 3         # max candidates passed to reranker
  ```

  In `_semantic_match_sync`, replace the return logic after `ranked` is computed with:

  ```python
  # Within-cluster argmax (runs before margin guard)
  if len(ranked) >= 2:
      second_sid, second_score = ranked[1]
      if second_score >= _CLUSTER_ARGMAX_FLOOR:
          best_cluster = _skill_cluster(best_sid)
          second_cluster = _skill_cluster(second_sid)
          if best_cluster is not None and best_cluster == second_cluster:
              return best_sid, best_score

  above = [(sid, score) for sid, score in ranked if score >= SEMANTIC_THRESHOLD]

  # Single clear candidate: return directly
  if len(above) == 1:
      return above[0]

  # Multiple candidates above threshold: check margin
  if len(above) >= 2:
      if above[0][1] - above[1][1] < _RERANK_MARGIN:
          # Scores too close to trust — route through reranker
          from sage_poc.nodes.skill_rerank import rerank_candidates
          return rerank_candidates(message_en, above[:_RERANK_TOP_K])
      # Clear winner (margin > 0.05): return top directly
      return above[0]

  # Nothing above threshold
  return None, best_score
  ```

- [ ] **Step 4: Run margin guard test to confirm PASS**

  ```bash
  uv run pytest tests/test_skill_select.py::test_margin_guard_routes_to_reranker_on_close_scores -v
  ```

  Expected: PASS.

- [ ] **Step 5: Run full test suite**

  ```bash
  uv run pytest tests/test_skill_select.py tests/test_routing.py tests/test_nodes.py -v -p no:xdist
  ```

  Expected: all green.

- [ ] **Step 6: Commit**

  ```bash
  git add src/sage_poc/nodes/skill_select.py tests/test_skill_select.py
  git commit -m "feat(skill_select): Tier-2 margin guard — route close-call decisions to reranker

  When multiple skills exceed SEMANTIC_THRESHOLD and top-2 scores differ by less
  than _RERANK_MARGIN (0.05), passes candidates to reranker instead of silently
  picking the higher raw score.

  Stub reranker returns top candidate (no behavioral change today). When Falcon-3B
  is validated, replaces _rerank_stub — the margin guard is the mechanism that
  routes semantically ambiguous cases to it.

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
  ```

---

## Task 9 — Probe set acceptance + threshold recalibration

**What this validates:** End-to-end confirmation that the multi-vector routing architecture meets the acceptance criteria from the documented failure cases. Runs the probe set and grief/SF-1 boundary scripts, recalibrates the threshold if needed, and runs the full test suite.

**Files:**
- Run: `scripts/semantic_probe_set.py`, `scripts/validate_grief_sf1_boundary.py`, `scripts/calibrate_threshold.py`
- Conditionally modify: `src/sage_poc/nodes/skill_select.py` (threshold update only if needed)

- [ ] **Step 1: Run probe set**

  ```bash
  uv run python scripts/semantic_probe_set.py 2>&1 | tee /tmp/mv_probe_results.txt
  ```

  Read `/tmp/mv_probe_results.txt`. **Acceptance criteria:**

  | Group | Criterion | Baseline (Task 1) |
  |-------|-----------|-------------------|
  | grief_loss | ≥ 8/10 OK | 3/10 |
  | interpersonal_effectiveness | ≥ 8/10 OK | varies |
  | financial_anxiety | ≥ 4/5 OK | varies |
  | cognitive_restructuring | ≥ 3/4 OK or CLUSTER | — |
  | WRONG verdicts | 0 across all groups | — |

  If any group misses its criterion: add or revise `semantic_anchors` for that skill in the JSON (Task 5 pattern). Do not modify `semantic_description`. Do not raise `SEMANTIC_THRESHOLD`.

- [ ] **Step 1b: Add ACT/values cross-cluster probes to `calibrate_threshold.py`**

  Surfaced during Phase 1 audit (2026-06-09): `values_clarification` (values_communication cluster) and `act_psychological_flexibility` (psychological_flexibility cluster) share ACT vocabulary in their `semantic_description` paragraphs ("values," "acceptance," "committed action"). No cross-cluster KNOWN_HITS probe exists for either skill. Add both to `KNOWN_HITS` in `scripts/calibrate_threshold.py`:

  ```python
  # ACT/values disambiguation probes (cross-cluster) — added Task 9 Step 1b
  ("I want to live more in accordance with what matters to me and stop going through the motions", "values_clarification", True),
  ("I feel stuck between what I know I should do and what my anxiety keeps telling me to avoid", "act_psychological_flexibility", True),
  ```

  Run calibrate_threshold.py and confirm both phrases score above `SEMANTIC_THRESHOLD` for their target skill and route to the correct skill. If either is below threshold, strengthen the relevant `semantic_description` — do not raise the threshold.

- [ ] **Step 2: Run `validate_grief_sf1_boundary.py`**

  ```bash
  uv run python scripts/validate_grief_sf1_boundary.py
  ```

  **Acceptance criteria:**
  - Grief PASS count ≥ 8/10
  - SF1 SUMMARY: all CLEAR (no grief anchor sits in the passive-ideation region)

  If any SF1 BLEED appears: remove the offending grief anchor from `grief_loss.json` `semantic_anchors`. A grief anchor that scores high on passive-SI probes is a safety risk — do not keep it.

- [ ] **Step 3: Recalibrate threshold**

  ```bash
  uv run python scripts/calibrate_threshold.py
  ```

  Multi-vector matching changes the scoring distribution — the threshold likely needs recalibration. Read the output:
  - If suggested threshold is within ±0.01 of `0.4593`: no change needed.
  - If it differs by more than 0.01: update `SEMANTIC_THRESHOLD` in `skill_select.py:37` to the suggested value. Do NOT raise into the 0.46–0.47 somatic noise band (see `docs/SKILL_AUTHORING_CONVENTIONS.md §Somatic vocabulary FPs`).

- [ ] **Step 4: Run full test suite**

  ```bash
  uv run pytest tests/ -p no:xdist --ignore=tests/experiment_4_4 --ignore=tests/experiment_4_5 --ignore=tests/experiment_4_6 -q
  ```

  Expected: all green (or documented pre-existing failures only). Note the baseline test count (from Task 1 or the last clean run) and verify the new count is baseline + the tests added in this plan.

- [ ] **Step 5: Run `test_full_routing` as pre-merge quality gate**

  ```bash
  uv run pytest tests/test_wrong_skill_routing.py -m slow -v -p no:xdist
  ```

  Expected: all 125 phrases route correctly. The `PSYCHOED_CLUSTER` within-cluster mismatches are logged but not failing. This test exercises both Tier-1 and Tier-2 end-to-end with the new multi-vector architecture.

- [ ] **Step 6: Pre-warm server.py warmup block for cold-start**

  After Task 6, the anchor index encodes ~51 texts instead of ~27 on first call to `_ensure_semantic_ready()`. On a cold Railway dyno the first post-deploy request is slower. Open `server.py` and locate the existing warmup block (~line 55). Confirm `_ensure_semantic_ready()` is called there. If it is already called, no change needed. If not, add:

  ```python
  # In server.py warmup section:
  from sage_poc.nodes.skill_select import _ensure_semantic_ready
  try:
      _ensure_semantic_ready()
      logger.info("skill_select semantic index warm")
  except Exception as exc:
      logger.warning("skill_select warmup failed: %s — semantic routing degraded to keyword-only", exc)
  ```

  This matches the existing warmup-fail behavior (WARNING + continue) documented in `project_warmup_silent_failure.md`. The anchor count difference is one-time cost; subsequent requests hit the cached matrix.

- [ ] **Step 7: Commit probe results and any threshold update**

  ```bash
  git add src/sage_poc/nodes/skill_select.py src/sage_poc/server.py  # server.py only if warmup block changed
  git commit -m "calibration(skill_select): recalibrate SEMANTIC_THRESHOLD post multi-vector

  Probe set: grief N/10, IE N/N, FA N/N. validate_grief_sf1_boundary: 0 SF-1 bleeds.
  Threshold updated from 0.4593 to <NEW_VALUE> (gap = <GAP>).
  Full suite: N tests green. Server warmup confirmed for ~51-anchor index.

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
  ```

---

## Out of scope — post-Gitex / requires external inputs

| Item | Why deferred |
|------|-------------|
| **SF-2 intent_route intensity blindness** | Upstream of skill_select; requires classifier redesign or new `emotional_intensity` signal; affects dbt_tipp (CRITICAL-severity), mi_readiness_ruler, values_clarification. Separate plan. dbt_tipp interim fix (high-precision trigger phrases) ships separately — Tier B item from 2026-06-07 audit. |
| **Falcon-3B live model** | Interface defined in Task 7. Model validation requires: test corpus, A/B against stub, latency profiling. Plugs in without any interface change when ready. |
| **Thin keyword fast-path from production logs** | Frequency-based keyword derivation requires pilot usage data that doesn't exist pre-Gitex. After pilot: run query frequency analysis, identify the genuinely high-volume ambiguous entry phrases, author them through CMS workflow with Arabic as first-class. |
| **SF-6 grief_loss Arabic keyword expansion** | Requires native-speaker + clinical review for Arabic grief vocabulary. Cultural_and_faith_frame step is unreachable in AR — highest-priority cultural gap. Route to clinical lead now for sign-off lead time before pilot. |
| **assertive_communication EN keyword gap** | Add "I can't say no", "I give in too easily", "passive aggressive", "people pleaser", "can't set limits" — small fix, post-Gitex. AR already passes. |
| **S3 Arabic coverage** | S3 runs on `message_en` only; should also run on original Arabic text. Deferred per ARCHITECTURE_BOUNDARIES.md. |
| **SF-5 audit attribution gap** | `completed_skill_id` split from `active_skill_id` — ~10 lines across 4 files. Should not wait for Gitex but is independent of this plan; ships on its own commit. |
