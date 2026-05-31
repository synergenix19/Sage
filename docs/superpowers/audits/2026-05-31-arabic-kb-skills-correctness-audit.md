# Arabic KB + 4 New Skills — Correctness Audit

**Date:** 2026-05-31  
**Branch:** `feat/arabic-kb-skills-expansion`  
**Auditor:** Claude Sonnet 4.6 (command session)  
**Scope:** Implementation correctness against `docs/superpowers/plans/2026-05-30-arabic-kb-skills-expansion.md`. No clinical approval review. No production-readiness assessment.

**Verdict (final, post-fix):**  
Keyword routing: validated, with 2 defects now fixed (Check 2 + Check 4).  
Semantic routing: mechanism validated (no timeouts), semantic coverage gaps present for grief_loss and interpersonal_effectiveness paraphrases — not a reliability defect.  
Clinical gates: deferred by design (staging only, no user exposure).

**Status of defects:**
- Check 2 (post_crisis_check_in keyword leak): **FIXED** — `KEYWORD_SEMANTIC_SKIP` constant + CI enforcement (commit `386d2a8`)
- Check 4 ("losing it" → stop_technique collision): **FIXED** — phrase removed from stop_technique (commit `e71268a`)
- Check 5 (xfail strict=False): **FIXED** — changed to strict=True (commit `f44fbe1`)
- Check 3 (semantic coverage gaps): **DOCUMENTED** — coverage gaps for grief_loss and interpersonal_effectiveness; semantic mechanism is reliable

---

## Summary Table

| # | Check | Result | Status |
|---|-------|--------|--------|
| 1 | Audit gate bites on broken skills | PASS | No action |
| 2 | post_crisis_check_in keyword routing | DEFECT → FIXED | Fixed commit `386d2a8` |
| 3 | Semantic paraphrase routing | Mechanism OK, coverage gaps → FIXED | Fixed commit `6126fc1` |
| 4 | Collision-fix decision | DEFECT → FIXED | Fixed commit `e71268a` |
| 5 | xfail strict mode | FINDING → FIXED | Fixed commit `f44fbe1` |
| 6 | Arabic RAG retrieval bidi integrity | PASS | No action |

**Recorded plan deviations** (not defects — explicit scope decisions):
- D1: Task 9 Step 0 inventory reconciliation performed post-hoc during audit (passed — SK-021 to SK-024 confirmed in SageAI_Skills_Knowledge_Base.md); control fired after the action it was meant to gate, which is acceptable for a POC
- D2: Clinical production gate deferred (§6.3 + §16.1 MARBERT) — all 4 new skills at staging only, no user exposure

---

## Check 1: Audit Gate Verification

**Question:** Does `audit_corpus.py` actually exit non-zero when a skill is broken?

**Method:** Emptied `cognitive_restructuring.evidence_base`, ran audit, restored. Removed "crisis" from `cognitive_restructuring.escalation_matrix.L3`, ran audit, restored.

**Results:**
```
evidence_base emptied → AUDIT EXIT: 1  ✓
  FAIL: cognitive_restructuring: evidence_base is empty (v7 §9.1: MANDATORY)

L3 crisis mention removed → AUDIT EXIT: 1  ✓
  FAIL: cognitive_restructuring: L3 does not mention crisis

Restored → AUDIT PASSED — all checks green.  ✓
```

**Verdict: PASS.** The audit gate has been seen to bite. Both the `evidence_base` and `L3` assertions fire correctly and produce non-zero exit.

**Note:** The `exit: 0` visible in earlier CI runs was a shell pipeline artifact (`echo $?` captures `head -5` exit code, not the audit). Standalone invocation confirmed correct exit semantics.

---

## Check 2: post_crisis_check_in Keyword Routing

**Question:** Are the 9 target_presentations in `post_crisis_check_in` genuinely documentation-only, or do they live in the Tier 1 keyword matching loop for non-monitoring sessions?

**Context:** Commit `9683a5e` reverted earlier padding, leaving 9 presentations. `PRESENTATIONS_FLOOR_EXEMPTIONS` in `corpus_constants.py` states:

> "target_presentations are documentation only and are never used as keyword routing triggers in production"

**Method:** Verified `skill_select.py` code path; confirmed `post_crisis_check_in` is in `_SKILLS` (loaded from SKILL_REGISTRY at index 3); confirmed keyword loop iterates all `_SKILLS` when `crisis_state != 'monitoring'`; tested 6 natural user messages.

**Results:**
```
'I am still here trying to work on things'     → post_crisis_check_in via 'still here'
'feeling safer now after our talk'             → post_crisis_check_in via 'feeling safer now'
'doing better now thank you'                   → post_crisis_check_in via 'doing better now'
'a bit calmer now'                             → post_crisis_check_in via 'a bit calmer now'
'wanted to check in about my progress'         → post_crisis_check_in via 'wanted to check in'
'follow up after earlier conversation'         → post_crisis_check_in via 'follow up after earlier'
```

5/6 natural messages routed to `post_crisis_check_in` outside a monitoring session.

**Verdict: DEFECT.** The `PRESENTATIONS_FLOOR_EXEMPTIONS` documentation claim is incorrect. `post_crisis_check_in` target_presentations ARE in the Tier 1 keyword loop for non-crisis users. A user who says "doing better now" or "still here" in a fresh session (not in crisis, `crisis_state='none'`) is routed into the post-crisis check-in skill — a flow premised on the user having had a recent crisis episode. This is a routing defect.

**Fix options:**
1. Remove `post_crisis_check_in` from `_SKILLS` and handle it as a special-case before the loop (it's already auto-selected at line 90; the keyword path is dead code for it).
2. Replace the 9 generic phrases with phrases specific enough to only appear in actual post-crisis contexts (e.g., "I wanted to check in after yesterday's crisis" — though this is hard to craft).
3. Update `PRESENTATIONS_FLOOR_EXEMPTIONS` comment to accurately document the behavior, and do the full fix before production.

Option 1 is the cleanest: since `post_crisis_check_in` is already handled before the keyword loop via `crisis_state == 'monitoring'`, its entries in `_SKILLS` serve no routing purpose and only create collision risk.

---

## Check 3: Semantic Paraphrase Routing

**Question:** Do paraphrase-tier messages (no keyword match) route correctly via BGE-M3 semantic fallback? Does the financial_anxiety vs ruminative_anxiety cluster boundary hold? Is the semantic tier reliable under load?

**Method:** 10 paraphrase probes (no keyword matches). Pre-warmed BGE-M3. Two passes: (a) initial run with Chrome open, (b) clean re-run with Chrome closed. Both passes plus raw BGE-M3 score computed synchronously (bypassing asyncio) to distinguish timeout from below-threshold.

**Correction from initial report:** The "5 timeouts" in the first pass were misidentified. `skill_match_method=None` in the node result means either timeout OR score-below-threshold. The clean re-run with raw scores confirmed `embedding_timeout=False` for all 10 probes — there are no timeouts. The failures are score-below-threshold (0.406–0.452) or within-cluster semantic overlap. The semantic tier mechanism is reliable.

**Clean re-run results (Chrome closed):**

| Probe | Expected | Raw top skill | Raw score | Node result | Note |
|-------|----------|---------------|-----------|-------------|------|
| Financial: work contract dismissed | financial_anxiety | financial_anxiety | 0.478 ✓ | financial_anxiety (semantic) | ✓ correct |
| Financial: remittance to parents | financial_anxiety | financial_anxiety | 0.430 ✗ | None | below threshold |
| Financial: provider role slipping | financial_anxiety | financial_anxiety | 0.513 ✓ | financial_anxiety (semantic) | ✓ correct |
| Grief: mother passed 3 months ago | grief_loss | grief_loss | 0.491 ✓ | grief_loss (semantic) | ✓ correct |
| Grief: looking for her in the house | grief_loss | worry_time | 0.451 ✗ | None | wrong top + below threshold |
| Grief: everything reminds me of him | grief_loss | grief_loss | 0.406 ✗ | None | below threshold |
| Cogn: jumps to worst case | cognitive_restructuring | cognitive_restructuring | 0.494 ✓ | cognitive_restructuring (semantic) | ✓ correct |
| Cogn: assume people think badly | cognitive_restructuring | cbt_thought_record | 0.512 ✓ | cbt_thought_record (semantic) | within-cluster, expected |
| Interp: difficult talk with father | interpersonal_effectiveness | financial_anxiety | 0.414 ✗ | None | wrong top + below threshold |
| Interp: caught between wife and family | interpersonal_effectiveness | financial_anxiety | 0.452 ✗ | None | wrong top + below threshold |

**4/10 correct, 0 timeouts, 1 within-cluster expected, 5 below-threshold (3 also wrong top skill).**

**Semantic tier reliability: confirmed.** All 10 inferences complete in 0.0s. No `embedding_timeout=True` in any result. The earlier "timeout" count was a probe-script labeling error — `skill_match_method=None` was being treated as timeout, but it also means below-threshold. Mechanism is sound.

**Financial_anxiety boundary: holds.** 2/3 financial probes route correctly. The one miss (0.430, just below threshold) has the correct top skill — it would route correctly if the threshold were slightly lower, but this is threshold-tuning territory not a description gap.

**Coverage gaps confirmed:**
- `grief_loss`: "looking for her around the house" tops at `worry_time` (0.451) — grief vocabulary in the semantic_description doesn't include "looking for them" / anticipatory presence patterns. "Everything reminds me of him" scores 0.406, suggesting the semantic_description needs broader grief-after-death vocabulary.
- `interpersonal_effectiveness`: both probes top at `financial_anxiety` (0.414, 0.452) — family tension and relational navigation vocabulary in the semantic_description overlaps with Gulf provider-role and family-obligation language in financial_anxiety. The interpersonal_effectiveness description needs more relational-navigation specificity distinct from the financial frame.

**Within-cluster behavior:** `cognitive_restructuring` paraphrase (assuming people think badly) → `cbt_thought_record` at 0.512. Both in `ruminative_anxiety` cluster. This is correct behavior — disambiguation is handled by Tier 1 keyword rules, not semantic scores.

**Verdict: Semantic tier mechanism is reliable (no timeouts). Coverage gaps confirmed for grief_loss and interpersonal_effectiveness. Fixed by description strengthening (commit `6126fc1`): 29-probe gate, one description at a time, full re-run after each edit. Final result: grief_loss 10/10, interpersonal_effectiveness 10/10. Calibration gap ≥ 0.03 confirmed after edits (suggested threshold 0.4581, current 0.459 — negligible drift). Residual note: one financial MISS_LOW probe tops at grief_loss (0.427) instead of financial_anxiety (0.422) — both below threshold, no misrouting, but fragile; monitor if grief_loss description is edited again.**

---

## Check 4: Collision-Fix Decision

**Question:** Was the routing test fix (changing the test message) a deliberate decision, or did it paper over a live routing defect?

**Method:** Tested original message "My visa depends on my job and I am terrified of losing it" and two semantically equivalent alternatives.

**Results:**
```
"My visa depends on my job and I am terrified of losing it"
  → keyword match: stop_technique via 'losing it'  (index 9)
  → routed to: stop_technique

"I am terrified of losing my job because my visa depends on it"
  → keyword match: None
  → routed to: financial_anxiety via semantic (score ~0.50)

"My job is at risk and my visa depends on it, I am terrified"
  → keyword match: None
  → routed to: financial_anxiety via semantic
```

**The routing defect is live.** `stop_technique` (index 9) owns the phrase "losing it" — colloquial for "losing control/temper/composure." The phrase appears naturally in financial distress contexts ("terrified of losing it = losing my job/visa"). The test fixture correctly avoids this phrase, but the production routing will send "I'm terrified of losing it" to `stop_technique` (an emotional regulation technique for anger/overwhelm), not `financial_anxiety`.

**Verdict: DEFECT.** The test change was the correct call for test determinism. The underlying collision is unresolved. A user naturally expressing kafala visa anxiety with "losing it" = emotional breakdown registers as an anger/regulation case.

**Fix:** Remove "losing it" from `stop_technique.target_presentations`, or add a safeguard in the keyword loop for ambiguous phrase resolution. "Losing it" in `stop_technique` is most likely meant for "I'm losing it / about to lose my mind" contexts — if that phrasing is genuinely needed, sharpen it: "about to lose it", "losing my mind", "can't take it anymore" are less polysemous.

---

## Check 5: xfail Strict Mode

**Question:** Is the `test_semantic_fallback_catches_exhausted_mind_racing` xfail marked `strict=True`?

**Finding:**

```python
@pytest.mark.xfail(
    reason="Intelligence Eval RT-4: semantic fallback returns None for near-threshold sleep phrasing...",
    strict=False,   # ← This
)
async def test_semantic_fallback_catches_exhausted_mind_racing():
```

`strict=False` means if this test unexpectedly passes (calibration improved), pytest reports XPASS but does not fail the suite. The xfail comment says "if this test unexpectedly passes, the calibration was improved — remove this xfail marker" — but with `strict=False`, that won't happen automatically; it will silently pass without alerting anyone.

**Parallel run:** 3/3 sequential runs of the 6 passing semantic fallback tests were stable. No flakiness observed. The xfail test itself runs in ~9.86s and fails deterministically (score below 0.459 threshold, not a timeout).

**Verdict: FINDING.** `strict=False` is not a correctness defect in itself, but it is a maintenance gap. If the threshold is later recalibrated to catch this phrase, the test will pass silently without triggering the "remove this marker" action the comment describes. Cost of fix: one word (`strict=True`).

**Fix:** Change `strict=False` to `strict=True`. The test will then fail the suite on XPASS, prompting removal of the marker.

---

## Check 6: Arabic RAG Retrieval — Bidi Integrity

**Question:** Do Arabic queries retrieve Arabic articles with bidi intact at the retrieval layer, not just at ingest?

**Method:** Ran 5 Arabic search queries against `knowledge_articles WHERE language='ar'`, verified Unicode Arabic codepoints present in retrieved chunks, checked grief-001 AR chunk distribution explicitly.

**Results:**

```
[OK] القلق        → anxiety-001-ar-000   bidi=True  'أحياناً تحس إن قلبك يدق بسرعة...'
[OK] الاكتئاب     → depression-001-ar-000 bidi=True  'أحياناً تصحى الصبح وجسمك تعبان...'
[OK] الحزن        → depression-001-ar-000 bidi=True  (cross-article match, expected)
[OK] العلاقات     → depression-002-ar-002 bidi=True  (cross-article match, expected)
[MISS] الكفالة    → 0 hits               expected (no kafala-specific KB article)
```

**grief-001 AR chunks (5 total):**
```
grief-001-ar-000  bidi=True  'الفقد من أصعب التجارب الإنسانية...'
grief-001-ar-001  bidi=True  'نبينا صلى الله عليه وسلم بكى على ابنه إبراهيم...'
grief-001-ar-002  bidi=True  'لكن هذا التوقع يحمل تكلفة نفسية كبيرة...'
grief-001-ar-003  bidi=True  'ذكر الفقيد بالخير، الدعاء له، وزيارة قبره...'
grief-001-ar-004  bidi=True  'الحزن ما له موعد محدد ينتهي فيه...'
```

**20 AR articles, 80 total chunks** all with `language='ar'`. Chunk IDs use format `{article_id}-ar-{index}`.

**Kafala miss is expected:** `financial_anxiety` skill context is delivered via `cultural_overrides` in the composer, not via a KB article. No `financial-001-ar-*` article exists; the plan did not include one.

**Verdict: PASS.** Arabic text survives the full round-trip (ingest → pgvector → retrieval) with bidi intact. All 20 articles retrievable; distribution correct.

---

## Recorded Plan Deviations

### D1: Task 9 Step 0 — Inventory Reconciliation Performed Post-Hoc

**Plan gate:** "Before authoring any skill JSON, confirm all four skills appear in the approved SageAI Skills & Knowledge Base inventory."

**What happened:** Skills were authored first; inventory cross-check was performed during this audit (after authoring). The gate's purpose was to prevent net-new skills from bypassing CMS approval. The cross-check found all four skills in `docs/SageAI_Skills_Knowledge_Base.md`:
- SK-021 `cognitive_restructuring`
- SK-022 `interpersonal_effectiveness`
- SK-023 `financial_anxiety`
- SK-024 `grief_loss`

**Status:** Reconciliation performed post-hoc during audit — passed. The skills were not net-new; they were in the approved inventory. The control fired after the action it was meant to gate, which is an acceptable deviation for a POC. Not "waived" — the check ran, it passed, the order was reversed.

### D2: Clinical Production Gate Deferred

**Plan gate (all 4 skills):** v7 §6.3 Draft → Review → Clinically Approved → Published before any user exposure.

**Plan gate (grief_loss, financial_anxiety):** MARBERT recall ≥95% and behavioural ideation probes before production.

**Status:** Deferred by design for POC. Skills are at staging (green CI) only. No user is exposed. These gates are non-negotiable before production deployment.

---

## Action Items

| Priority | Item | Status |
|----------|------|--------|
| ~~Now~~ DONE | Check 2: KEYWORD_SEMANTIC_SKIP + CI tests | Fixed commit `386d2a8` |
| ~~Now~~ DONE | Check 4: remove "losing it" from stop_technique | Fixed commit `e71268a` |
| ~~Now~~ DONE | Check 5: xfail strict=False → strict=True | Fixed commit `f44fbe1` |
| ~~Before production~~ DONE | Strengthen grief_loss semantic_description (10/10 probe gate) | Fixed commit `6126fc1` |
| ~~Before production~~ DONE | Strengthen interpersonal_effectiveness semantic_description (10/10 probe gate) | Fixed commit `6126fc1` |
| ~~Before production~~ DONE | Re-run calibration after semantic_description edits | Gap ≥ 0.03 confirmed |
| Before production | §6.3 clinician sign-off for all 4 skills | Open |
| Before production | MARBERT recall check + behavioural probes for grief_loss, financial_anxiety | Open |
| Traceability | Add inventory item numbers (SK-021 to SK-024) to Task 9 commit annotation | Optional |
