# Crisis Recall Gap — Tracked Finding

**Date:** 2026-06-05  
**Instrument:** CRADLE Bench (600 cases, 7 crisis types) — English synthetic dataset  
**Run type:** S1-only (S3 patched to 0.0) + Combined S1+S3 (BGE-M3 warm, threshold 0.8059)  
**Owner:** Clinical lead + DPO  

## Numbers

### Aggregate

| Layer | Recall | vs KPI |
|---|---|---|
| S1 only (keyword rules) | 37.1% (86/232) | -57.9pp below 95% gate |
| S1 + S3 combined (production config) | 37.1% (86/232) | identical — S3 adds zero on this bench |
| **KPI target** | **>=95%** | |

### Self-harm (own KPI line — do not fold into aggregate)

Self-harm has its own tracked KPI because its recall floor is structurally lower than SI and its miss count (75) dominates the aggregate gap. Folding it into "37.1% overall" obscures that fewer than 1 in 5 self-harm cases are caught.

| Layer | Self-harm recall | vs KPI | Missed |
|---|---|---|---|
| S1 only | **18% (17/92)** | **FAIL** | 75 |
| S1 + S3 combined | 18% (17/92) | FAIL | 75 — S3 adds zero |
| **KPI target** | **>=50% (interim)** | | |

Interim KPI of 50% is a pre-Gitex checkpoint, not clinical adequacy. Clinical adequacy requires ≥95% recall with an Arabic eval instrument. The 18% number must be visible to the clinical lead and DPO, separately from the SI categories.

### Breakdown by SI category

| Category | Recall | Missed |
|---|---|---|
| active_suicide_ideation | 52% (34/65) | 31 |
| passive_suicide_ideation | 47% (35/75) | 40 |

### Combined crisis specificity (safe cases)

| Layer | Specificity | FPs / 186 safe |
|---|---|---|
| S1 only | 95.7% | 8 |
| S1 + S3 at 0.8059 | 95.7% | 8 — S3 adds no new FPs at current threshold |

## S3 threshold sweep — verdict: demote (2026-06-05)

Sweep run 2026-06-05 (`scripts/s3_threshold_sweep.py`) across passive_SI CRADLE slice (75 cases) and safe set (186 cases). Results:

| T | S3-only adds | Combined passive SI | New FPs | Decision |
|---|---|---|---|---|
| 0.65 | 10 | 45/75 (60.0%) | **14** | skip — FP cost unacceptable |
| 0.70 | 3 | 38/75 (50.7%) | 2 | skip — worse than 1:1 tradeoff |
| 0.75 | 0 | 35/75 (46.7%) | 0 | skip — no adds |
| 0.80 | 0 | 35/75 (46.7%) | 0 | skip — no adds |
| 0.8059 (deployed) | 0 | 35/75 (46.7%) | 0 | **zero recall contribution** |

**Verdict: S3 is demoted.** At no tested threshold does it meet the criterion for a useful second tier (>5 S3-only adds at FP count ≤ baseline 8). The crisis phrase corpus is anchored to direct SI phrasing — it catches paraphrases of what S1 already catches, not the hopelessness/indirect-expression cluster that constitutes the 40 passive-SI misses. BGE-M3's embedding space cannot separate therapeutic acceptance language from suicidal acceptance language at any threshold viable for production.

S3 status in all documentation: "OR-fusion tier present, adds 0 measured recall above S1 on CRADLE passive_SI slice (75 cases). No threshold (0.65–0.81) meets the recall/FP criterion. Paraphrase-matcher at current corpus. Full semantic coverage requires MARBERT (Exp 4.2)."

## Why S3 adds zero on this bench

S3_THRESHOLD is calibrated to 0.8059 (scripts/calibrate_s3_threshold.py). CRADLE self-harm cases score in the 0.43-0.68 band and passive-SI misses score 0.62-0.72 — both uniformly below the threshold. Lowering to the 0.65-0.72 range gains 10 passive-SI catches at cost of 14 new FPs (see sweep table above). S3 is correctly calibrated; the corpus is the gap.

## S3 score distribution — all 75 self-harm misses (confirmed 2026-06-05)

Scored with BGE-M3 warm against S3_THRESHOLD=0.8059:

| Band | Count | % | Notes |
|---|---|---|---|
| near_zero (<0.3) | 0 | 0% | |
| low (0.3-0.5) | 8 | 10.7% | avg 0.466 |
| sub_threshold (0.5-0.8059) | 67 | 89.3% | avg 0.584 |
| above_threshold (>=0.8059) | 0 | 0% | |

Min=0.427, Median=0.572, Max=0.681, Mean=0.572

All 75 misses carry S3 semantic signal (minimum 0.427). None are pure lexicon gaps with zero semantic footprint. The entire distribution sits in a coherent band uniformly below the threshold — corpus expansion is the path for all 75, not a two-lever problem. Threshold tuning is not the fix: lowering to 0.5-0.6 crosses the Arabic FP boundary (~0.61) and trades English self-harm recall for Arabic specificity on a bench that cannot see the cost.

## What this number means for production

- This bench is English only. CRADLE does not model Khaleeji/Arabizi self-harm language.
- The 18% self-harm recall is a **lower bound** if CRADLE phrasings are more clinical than real user input, or an **upper bound** if real users use shorter/vaguer expressions. The actual direction is unknown without real-user input analysis.
- No Arabic-language self-harm bench exists. Arabic recall is unmeasured.
- Production runs S1+S3 combined = same 37.1% on CRADLE. S3 may recover additional cases on real-user input that skews toward explicit suicidality language; this is unconfirmed.

## Fix path

1. **Corpus expansion (S3) — primary lever for all 75 self-harm misses:** Add self-harm forum/clinical phrasings to crisis_phrases.json that pull scores from the 0.43-0.68 band above 0.8059. After expansion, re-run calibrate_s3_threshold.py and verify the FP boundary holds. Requires BGE-M3 determinism check on new embeddings. Do not lower the threshold as a shortcut.

2. **Lexicon expansion (S1) — for passive SI and active SI misses:** Expand crisis_keywords.json and passive_si_patterns.json against the miss set. Miss list: `docs/cradle-s1-miss-list-2026-06-05.json` (146 cases with full text and S1 flags). Requires clinician sign-off per pattern before merge to master.

3. **Arabic eval instrument:** CRADLE cannot measure Arabic/Arabizi recall. An Arabic crisis recall bench is needed before any Arabic crisis pattern claims are defensible.

## Open question

How representative are CRADLE's self-harm phrasings of what real Khaleeji/Arabizi users actually type? The 18% recall is only as good as the bench's fidelity to real input distribution. This needs real-user input analysis before the number can be treated as a reliable production estimate.

## Arabic crisis coverage — two distinct states (do not conflate)

This section must be read as two separate rows in any governance table:

| Item | State |
|---|---|
| Arabic crisis rules authored | SK-AR-004 (SI method), SK-AR-005 (third-party), SK-AR-006 (escape/non-return) drafted |
| Arabic crisis coverage LIVE | **NONE beyond SK-AR-001/002/003** — SK-AR-004/005 reverted pending sign-off; SK-AR-006 active=false |

"Drafted" must not read as "handled." Three rules in the pending queue is three Arabic crisis classes with zero live coverage at any tier (S1 has no rule, S3 is advisory at zero recall).

The three rules are bundled into a single sign-off package: `docs/arabic-crisis-rules-signoff-package-2026-06-05.md`. One clinical action unblocks all three.

**Gulf Arabic escape/non-return (SK-AR-006 class) specifically:** zero coverage at S1, S2 not built, S3 advisory. A user expressing "ودي امشي ولا ارجع" will not trigger any crisis response in the current system.

## PDPL / governance note

A known sub-gate crisis recall number that is not written down is its own liability under PDPL. This document is the written record. It must be visible to the clinical lead and DPO, not living in a terminal session.

**This gap does not block the current POC deployment** — the system is deployed with known limitations, clinician-acknowledged, with a clear remediation path. It does block any claim of clinical adequacy.
