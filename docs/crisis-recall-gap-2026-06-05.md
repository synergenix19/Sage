# Crisis Recall Gap — Tracked Finding

**Date:** 2026-06-05  
**Instrument:** CRADLE Bench (600 cases, 7 crisis types) — English synthetic dataset  
**Run type:** S1-only (S3 patched to 0.0) + Combined S1+S3 (BGE-M3 warm, threshold 0.8059)  
**Owner:** Clinical lead + DPO  

## Numbers

| Layer | Recall | vs KPI |
|---|---|---|
| S1 only (keyword rules) | 37.1% (86/232) | −57.9pp below 95% gate |
| S1 + S3 combined (production config) | 37.1% (86/232) | identical — S3 adds zero on this bench |
| **KPI target** | **≥ 95%** | |

### Breakdown by category

| Category | Recall | Missed |
|---|---|---|
| active_suicide_ideation | 52% (34/65) | 31 |
| passive_suicide_ideation | 47% (35/75) | 40 |
| **self_harm** | **18% (17/92)** | **75** |

Self-harm is the dominant gap. 75 of 146 total misses. The system catches fewer than 1 in 5 self-harm crisis cases CRADLE presents.

## Why S3 adds zero on this bench

S3_THRESHOLD is calibrated to 0.8059 (scripts/calibrate_s3_threshold.py, 2026-06-03). The CRADLE self-harm cases score 0.49–0.67 — above the false-positive floor but below the threshold. These are clinical/forum-register phrasings ("cuts", "clean", "SH out of anger") that are semantically distant from the explicit suicidality corpus in crisis_phrases.json. Lowering the threshold to capture them crosses the Arabic false-positive boundary (~0.61). S3 is correctly calibrated; the corpus is the gap.

## What this number means for production

- This bench is English only. CRADLE does not model Khaleeji/Arabizi self-harm language.
- The 18% self-harm recall is a **lower bound** if CRADLE phrasings are more clinical than real user input, or an **upper bound** if real users use shorter/vaguer expressions.
- No Arabic-language self-harm bench exists. The actual Arabic recall is unmeasured.
- S1 + S3 combined in production = same 37.1% on CRADLE. Production may be higher if real inputs skew toward explicit suicidality language that S3 does catch.

## Fix path

1. **Lexicon expansion (S1):** Expand crisis_keywords.json and passive_si_patterns.json using the CRADLE miss set as the target list. Miss list at: `docs/cradle-s1-miss-list-2026-06-05.json` (146 cases with full text). Self-harm phrasings are the priority — 75 cases. Requires clinician sign-off on each new pattern before merge to master.

2. **Corpus expansion (S3):** Add self-harm forum/clinical phrasings to crisis_phrases.json, then re-run calibrate_s3_threshold.py. Must not lower the threshold below the Arabic FP boundary. Requires BGE-M3 ANE recompile + determinism check on new embeddings.

3. **Arabic eval instrument:** CRADLE cannot measure Arabic/Arabizi recall. An Arabic crisis recall bench is needed before any Arabic crisis pattern claims are defensible.

## PDPL / governance note

A known sub-gate crisis recall number that is not written down is its own liability under PDPL. This document is the written record. It should be visible to the clinical lead and DPO, not living in a terminal session.

**This gap does not block the current POC deployment** — the system is deployed with known limitations, clinician-acknowledged, with a clear remediation path. It does block any claim of clinical adequacy.
