# Crisis Recall Gap — Tracked Finding

**Date:** 2026-06-05  
**Instrument:** CRADLE Bench (600 cases, 7 crisis types) — English synthetic dataset  
**Run type:** S1-only (S3 patched to 0.0) + Combined S1+S3 (BGE-M3 warm, threshold 0.8059)  
**Owner:** Clinical lead + DPO  

## Numbers

| Layer | Recall | vs KPI |
|---|---|---|
| S1 only (keyword rules) | 37.1% (86/232) | -57.9pp below 95% gate |
| S1 + S3 combined (production config) | 37.1% (86/232) | identical — S3 adds zero on this bench |
| **KPI target** | **>=95%** | |

### Breakdown by category

| Category | Recall | Missed |
|---|---|---|
| active_suicide_ideation | 52% (34/65) | 31 |
| passive_suicide_ideation | 47% (35/75) | 40 |
| **self_harm** | **18% (17/92)** | **75** |

Self-harm is the dominant gap. 75 of 146 total misses. The system catches fewer than 1 in 5 self-harm crisis cases CRADLE presents.

## Why S3 adds zero on this bench

S3_THRESHOLD is calibrated to 0.8059 (scripts/calibrate_s3_threshold.py, 2026-06-03). CRADLE self-harm cases score in the 0.43-0.68 band — above the false-positive floor but uniformly below the threshold. S3 is correctly calibrated; the crisis phrase corpus is the gap.

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

## PDPL / governance note

A known sub-gate crisis recall number that is not written down is its own liability under PDPL. This document is the written record. It must be visible to the clinical lead and DPO, not living in a terminal session.

**This gap does not block the current POC deployment** — the system is deployed with known limitations, clinician-acknowledged, with a clear remediation path. It does block any claim of clinical adequacy.
