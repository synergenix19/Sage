# Work Order: crisis_phrases.json Corpus Expansion

**Created:** 2026-06-05  
**Priority:** High — pre-Gitex if possible, required before any clinical adequacy claim  
**Owner:** Clinical lead (phrase authorship + sign-off)  
**Engineering support:** Calibration, testing, deployment gate  
**Blocking:** English self-harm crisis recall is 18% (17/92). Combined S1+S3 production recall is 37.1%. Target ≥95%.

---

## Why this is a clinician task, not an engineering task

crisis_phrases.json is the semantic ground truth for what counts as a crisis utterance in the BGE-M3 (S3) layer. Adding phrases to it is encoding the clinical judgment "this language means someone is at risk." That judgment has false-negative and false-positive consequences in both directions, and it must be owned by someone clinical — for exactly the same reason the four unsigned crisis rules came off the path on 2026-06-05. The corpus is the same category of artifact.

An engineer hand-adding self-harm forum phrasings to improve CRADLE recall recreates the `approved_by: null` problem inside the corpus rather than the rules file.

---

## What the data shows

All 75 self-harm CRADLE misses score 0.43–0.68 against S3_THRESHOLD=0.8059 (median 0.572, min 0.427). None bottom out near zero. The problem is one coherent band of sub-threshold signal — self-harm forum/recovery register language that is semantically close to crisis but not close enough to the current corpus. Corpus expansion is the single correct lever for all 75.

Full score distribution and context: `docs/crisis-recall-gap-2026-06-05.md`  
Miss list with full text: `docs/cradle-s1-miss-list-2026-06-05.json`

---

## Scope

Add self-harm phrasings to `src/sage_poc/safety/crisis_phrases.json` that represent the register gap: first-person self-harm language in clinical/forum/recovery discourse, not just explicit suicidality.

Target: pull the 0.43–0.68 scoring cases above S3_THRESHOLD (0.8059) after re-calibration.

---

## Using the CRADLE miss list as source material

The miss list (`docs/cradle-s1-miss-list-2026-06-05.json`) contains real, clinically-annotated self-harm language from Reddit. It is the right place to start — it shows exactly what register the current corpus doesn't cover. Reading it to understand the gap is correct use of the data.

The miss cases cluster into identifiable patterns:
- **Concealment language:** "how do I hide my cuts", "put concealer on my arm"
- **SH abbreviation register:** "I sh out of anger", "tw: sh", "obviously don't normalize sh"
- **Recovery/clean streak language:** "100 days clean from cutting", "relapsed", "getting bad urges", "trying to stay clean"
- **Wound management:** "wounds sweating", "cuts bleeding", "scars itch"
- **Indirect disclosure:** "my sleeves rolled up", "people seeing my marks"

**What to do with this:** Use these patterns to draft phrases that generalise the register, not to copy the texts verbatim. The goal is phrases that represent the semantic neighbourhood, so BGE-M3 catches the class of inputs, not just the specific CRADLE instances.

**What not to do:** Copy miss case texts into crisis_phrases.json directly. If you do, re-running CRADLE shows improvement because you put the test cases into the oracle — the recall number becomes circular and no longer measures generalisation to new inputs. The phrases that go in should be representative of the pattern, drafted to cover it, not lifted from the test set itself.

**The ambiguous cases — where clinical judgment is essential:** Some miss cases are recovery-positive, not active-crisis. "100 days clean from cutting" and "trying to stay clean this week" describe someone in recovery, not someone currently self-harming. Whether S3 should fire on these is a clinical call with real consequences in both directions: firing escalates someone who may be stable; not firing misses someone who is struggling. That specific judgment — recovery language vs. active risk — is exactly what must be owned by the clinical lead, not resolved by recall numbers.

## Hard constraints

### 1. Phrases must generalise the pattern, not copy the test cases

Draft phrases that represent the register class identified from the miss cases. Do not copy miss case texts verbatim. The test for whether a phrase belongs in the corpus is: "would a clinician say this language indicates someone is at risk?" — not "does this phrase appear in the CRADLE miss list?"

### 2. Re-calibration is mandatory before any merge to master

Adding phrases to crisis_phrases.json changes the embedding space the threshold was calibrated against. The 0.8059 threshold is not portable across corpus changes. After any expansion:

1. Run `scripts/calibrate_s3_threshold.py` with the updated corpus
2. Verify the output threshold still satisfies both gates:
   - All SF-1 GATE phrases score ≥ threshold
   - All SF-6 FP phrases score < threshold (especially `الله ياخذني من هالدنيا`, currently 0.6087)
3. If the FP boundary shifts upward — expansion pushed it — stop and review before proceeding

### 3. Arabic false-positive check is required — CRADLE cannot do this

The threshold calibration includes Arabic FP phrases (SF-6). After any corpus change, the Arabic FP boundary must be explicitly re-checked. CRADLE is English-only and will not surface Arabic specificity damage. Do not rely on CRADLE recall improvement as evidence that Arabic specificity held.

Instrument for Arabic FP check: `scripts/calibrate_s3_threshold.py` with the SF-6 phrase set (already includes Arabic). Verify `الله ياخذني من هالدنيا` and any other Arabic FP phrases in the calibration set score below the new threshold.

### 4. BGE-M3 determinism check after re-calibration

If the threshold changes, the embedding index needs to be rebuilt. After rebuilding:
- Run the determinism test suite (`pytest -m slow tests/test_s3_semantic.py`)
- Confirm scores are stable across two runs before publishing the new threshold

### 2. Re-calibration is mandatory before any merge to master

Adding phrases to crisis_phrases.json changes the embedding space the threshold was calibrated against. The 0.8059 threshold is not portable across corpus changes. After any expansion:

1. Run `scripts/calibrate_s3_threshold.py` with the updated corpus
2. Verify the output threshold still satisfies both gates:
   - All SF-1 GATE phrases score ≥ threshold
   - All SF-6 FP phrases score < threshold (especially `الله ياخذني من هالدنيا`, currently 0.6087)
3. If the FP boundary shifts upward — expansion pushed it — stop and review before proceeding

### 3. Arabic false-positive check is required — CRADLE cannot do this

The threshold calibration includes Arabic FP phrases (SF-6). After any corpus change, the Arabic FP boundary must be explicitly re-checked. CRADLE is English-only and will not surface Arabic specificity damage. Do not rely on CRADLE recall improvement as evidence that Arabic specificity held.

Instrument for Arabic FP check: `scripts/calibrate_s3_threshold.py` with the SF-6 phrase set (already includes Arabic). Verify `الله ياخذني من هالدنيا` and any other Arabic FP phrases in the calibration set score below the new threshold.

### 4. BGE-M3 determinism check after re-calibration

If the threshold changes, the embedding index needs to be rebuilt. After rebuilding:
- Run the determinism test suite (`pytest -m slow tests/test_s3_semantic.py`)
- Confirm scores are stable across two runs before publishing the new threshold

---

## Sign-off gate (same as crisis rules)

No corpus change merges to master without:

- [ ] Phrases reviewed and approved by clinical lead (name + date on the PR)
- [ ] Re-calibration run completed, new threshold documented
- [ ] SF-6 Arabic FP check passed (threshold still above Arabic FP boundary)
- [ ] BGE-M3 determinism check passed
- [ ] CRADLE recall re-run showing before/after S1 and S1+S3 numbers
- [ ] Engineering sign-off on calibration output

The PR description must include the before/after recall numbers and the new threshold value.

---

## What to measure when done

Run the combined S1+S3 CRADLE bench (script at `/tmp/cradle_combined.py` or via the test suite with S3 unpatched) and report:

| Metric | Before | After |
|---|---|---|
| S1+S3 crisis recall | 37.1% | ? |
| Self-harm recall | 18% | ? |
| Specificity (safe→no flag) | 95.7% | ? |
| S3_THRESHOLD | 0.8059 | ? |
| Arabic FP phrase score | <0.8059 | ? |

---

## What this work order does not cover

- Lexicon expansion (S1 keywords) for passive SI and active SI misses — that is a separate work item, also clinician-authored, also requiring sign-off per pattern
- Arabic/Arabizi self-harm coverage — no eval instrument exists; a separate Arabic bench is prerequisite to any Arabic corpus expansion
- Threshold lowering — explicitly ruled out; crossing the Arabic FP boundary trades English recall for Arabic specificity on a bench that cannot see the damage
