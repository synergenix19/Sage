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

## Hard constraints

### 1. Do not source phrases from the CRADLE miss list

The CRADLE miss list (`docs/cradle-s1-miss-list-2026-06-05.json`) is the test set. Lifting phrases directly from it to add to the corpus trains the model on its own test instrument. That will make CRADLE recall go up and tell you nothing about real-user coverage — you'll have fit the bench, not the problem. Phrase sources must be independent of CRADLE.

Acceptable sources: clinical literature, validated crisis communication frameworks, independent clinician authorship based on practice experience, other held-out corpora the clinical lead selects.

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
