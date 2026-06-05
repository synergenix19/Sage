# SageAI POC — Safety & Readiness Governance Table

**Date:** 2026-06-06  
**Scope:** Gitex demo readiness + post-Gitex clinical adequacy path  
**Owner:** Clinical Lead + DPO + Engineering Lead  
**Status:** Pre-Gitex review required

This table states the safety posture plainly. Green test results are recorded where they exist; gaps and open questions are stated without softening.

---

## I. Crisis Detection — Deterministic Floor

| Item | Status | Number | Owner |
|---|---|---|---|
| Overall S1 recall (CRADLE Bench, 232 crisis cases) | **FAIL** | **37.1%** vs ≥95% KPI | Clinical Lead |
| Self-harm recall (S1, CRADLE, 92 cases) | **FAIL — own KPI line** | **18%** vs ≥50% interim KPI | Clinical Lead |
| Active SI recall (S1, CRADLE, 65 cases) | MEASURED | 52% — above interim, below clinical adequacy | Clinical Lead |
| Passive SI recall (S1, CRADLE, 75 cases) | MEASURED | 47% — above interim, below clinical adequacy | Clinical Lead |
| S1 specificity (safe cases, 186) | PASS | 95.7% (8 FPs / 186) | Engineering |

**The 37.1% floor is the headline number for clinical accountability.** Self-harm (18%) is structurally lower than SI and must be tracked separately; folding it into the aggregate obscures that fewer than 1 in 5 self-harm expressions are caught.

**The bench is English only.** CRADLE does not model Khaleeji/Arabizi crisis language. Arabic deterministic recall is unmeasured.

---

## II. S3 Semantic Tier — Demoted (Advisory Only)

| Item | Status | Details |
|---|---|---|
| S3 recall contribution above S1 | **ZERO** | At every tested threshold (0.65–0.8059); see scripts/s3_threshold_sweep.py |
| S3 on crisis path | YES — advisory | Records `s3_score` in state and audit row; labeled in code as non-recall-bearing |
| S3 FP risk | MANAGED | 8 FPs at 0.8059 (same as S1-only); no additional FPs at current threshold |
| S3 promotion path | BLOCKED | Miss cluster (0.62–0.72 cosine) overlaps therapeutic acceptance language; BGE-M3 cannot separate without context. MARBERT required. |

**Do not cite S3 as a safety tier providing recall coverage.** It is a paraphrase-matcher for what S1 already catches.

---

## III. Interim Safety Posture — Predominantly Probabilistic

**This is the headline the governance table must state:**

> Interim safety (POC) rests on four LLM-dependent decision points and one deterministic floor measured at 37%. The deterministic floor is load-bearing for Arabic and Arabizi (S3 does not generalize at production threshold). MARBERT is the gated path to a ≥95% deterministic floor.

| Node | Type | Gate | Measured |
|---|---|---|---|
| Node 1 S1 keyword (safety_check) | Deterministic | Crisis detection — crisis path | 37.1% recall / 95.7% specificity on CRADLE |
| Node 2 intent carve-out (intent_route) | **LLM** | Routes crisis vs. technique-switch | Gate cleared 2026-06-05: 6/6 crisis, 0/3 FP |
| Node 5 entry screens (criteria_eval) | **LLM** | Holds skill-start on contraindication | Gate cleared 2026-06-06: 18/18 across 5 skills |
| S3 semantic (safety_check) | Embedding | Advisory, non-recall-bearing | DEMOTED — 0 recall adds at any threshold |
| Resistance scoring | **LLM** | Step policy engagement signal | Not gated; feeds therapeutic profile only |

**Node 1 (S1) is structurally independent of the LLM pool — confirmed under 45-concurrent load.** Pool saturation cannot starve the deterministic crisis floor. Entry-screen holds degrade gracefully (recoverable); Node 1 degradation would be unacceptable and is structurally prevented.

---

## IV. Arabic Crisis Coverage

Three rows. Do not conflate live exposure, authored-but-inactive rules, and the pending fix.

### Live exposure (what a real user can hit today)

| Crisis class | S1 live | S3 | Coverage |
|---|---|---|---|
| Arabic SI explicit phrasing | SK-AR-001/002/003 | Advisory (0 recall) | Partial — 3 rules, unmeasured recall |
| Arabic SI method references | **NONE** (SK-AR-004 reverted) | Advisory (0 recall) | **ZERO** |
| Arabic third-party crisis | **NONE** (SK-AR-005 reverted) | Advisory (0 recall) | **ZERO** |
| Gulf escape/non-return | **NONE** (SK-AR-006 inactive) | Advisory (0 recall) | **ZERO** |

**A user expressing "ودي امشي ولا ارجع" will not trigger any crisis response in the current system.** This is a live exposure, not a pending item. The gap exists right now, for Arabic-speaking users, in the population most likely to use this idiom.

Arabic crisis recall is unmeasured — CRADLE is English-only. The three live rules (SK-AR-001/002/003) have no validated recall figure.

### Queued remediation (what can close the gap)

| Rule | What it covers | Status |
|---|---|---|
| SK-AR-004 | Arabic SI method references | Authored, reverted — awaiting clinical sign-off |
| SK-AR-005 | Arabic third-party crisis | Authored, reverted — awaiting clinical sign-off |
| SK-AR-006 | Gulf escape/non-return ideation | Authored (active=false) — awaiting clinical sign-off |

**Clinical sign-off required (bundled package):** `docs/arabic-crisis-rules-signoff-package-2026-06-05.md` — one clinical action activates all three. Bundling was done for speed; the risk is that three distinct Arabic crisis classes clear on a single review gesture rather than individual clinical scrutiny of each pattern set. The sign-off package asks explicit questions per rule to prevent rubber-stamping.

---

## V. Entry-Screen Criteria Rewrites — Pending Clinical Sign-Off

Four skill criteria were rewritten to add affirmative-target carve-outs after adversarial FP testing revealed 4/4 false holds on the target population (panic patients for TIPP, stress tension for PMR, emotional depletion for body scan, visualization uncertainty for safe place).

**Green tests verify LLM behavior matches the criteria text. They do not verify the criteria are medically correct.** Engineering rewrote clinician-authored content; clinical sign-off is required before these carve-outs are treated as authoritative.

| Skill | FP found | Fix | Pending |
|---|---|---|---|
| dbt_tipp | Racing heart from anxiety → false HOLD | IMPORTANT: anxiety symptoms ≠ cardiac condition | Clinical sign-off |
| progressive_muscle_relaxation | Stress tension → false HOLD | IMPORTANT: muscle tension from stress = target, not contraindication | Clinical sign-off |
| mindfulness_body_scan | "Tired and stressed" → false HOLD | IMPORTANT: emotional depletion ≠ dissociation risk | Clinical sign-off |
| safe_place_visualization | First-timer / uncertainty → false HOLD | IMPORTANT: uncertainty ≠ inability; skill helps find the place | Clinical sign-off |

**Sign-off package:** `docs/skill-criteria-signoff-package-2026-06-05.md` — same signer, same action as Arabic rules.

**Net pending clinical actions: 1 person, 2 packages, 7 items.** Clearing this unblocks 3 Arabic crisis classes + 4 skill safety boundaries.

**Individual judgment required, not a batch approval:** Seven safety-relevant items clearing on a single signer's single review is efficient but carries a scrutiny risk. Each item requires individual clinical judgment — the Arabic rules need pattern-by-pattern review (is "ودي امشي في الصحراء ولا ارجع" unambiguous in the UAE pilot population?), and each criteria rewrite has its own clinical question (does "racing heart from panic is NOT a cardiac condition" adequately preserve the cardiac edge case?). The sign-off package asks these questions explicitly; the signer should answer each one, not tick a single box. The record should show that individual scrutiny was asked for and provided.

---

## VI. Pool Characterization — Gitex Conditions

**Full characterization:** `docs/pool-characterization-2026-06-06.md`

| Condition | Result | KPI |
|---|---|---|
| False-hold rate at 45 concurrent calls (Gitex peak) | **0/45 (0%)** | PASS |
| p95 per-call latency at 45 concurrent (warm) | **1892ms** | PASS (< 3s) |
| Node 1 independence under 45-concurrent LLM load | **CONFIRMED** — S1 makes zero LLM pool calls | PASS |
| Retry asymmetry | **CORRECT by construction** — resilient_invoke retries on transport errors only, never on a successful "no" | PASS |

**Open Gitex gate item — cold-start latency:**

| Item | Measured | KPI | Decision |
|---|---|---|---|
| First classifier call after startup/idle (TCP cold-start) | **4678ms** | > 3s KPI | **IMPLEMENTED — verify post-deploy** |
| Subsequent calls (warm) | 665ms p50 / 800ms p95 | Within KPI | PASS |

**Option A implemented (2026-06-06):** `_warmup_task()` now makes a classifier call before setting `_bge_ready = True`. Uses the same shared `_ASYNC_HTTP_CLIENT` (300s keepalive_expiry) as real requests — a different client would warm a different pool and have no effect. Railway's readiness probe (`/health/ready`) returns 503 until `_bge_ready = True`, so LB traffic is held until both BGE-M3 AND the classifier connection are warm.

**Post-deploy verification required:** The readiness gate holding until warmup completes can only be confirmed against a deployed Railway service — local startup proves the code exists, not that Railway's LB honors the 503 before switching traffic. Verify once on staging: deploy → watch Railway healthcheck status → confirm first user after /health/ready turns 200 sees ≤1s on skill-start.

**keepalive_expiry=300 covers booth idle gaps:** httpx default (5s) would re-pay TCP/TLS after any quiet period between demos. 300s (5 minutes) covers typical between-demo gaps without holding idle connections indefinitely. The shared client is module-level — all 6 LLM roles share the same pool.

---

## VII. Pre-Gitex Conditions Summary

Items that must be resolved before the demo. Not a GA checklist — the POC is deployed with known limitations acknowledged below.

| # | Item | Owner | Status |
|---|---|---|---|
| G-1 | SAGE_API_KEY deployment secret set in Railway environment | DevOps | Open |
| G-2 | Browser QA — full golden path on mobile + desktop | QA | Open |
| G-3 | CORS env var (`CORS_ALLOWED_ORIGINS`) set to demo frontend URL | DevOps | Open |
| G-4 | DB migration 013 run on production Supabase before demo | Engineering | Open (E2E DPIA fix) |
| G-5 | **Cold-start latency** — Option A implemented; verify post-deploy on staging (see §VI) | Engineering | Implemented — verify |
| G-6 | Clinical sign-off — Arabic rules + skill criteria (2 packages, 1 signer) | Clinical Lead | Pending |

**G-6 is not a Gitex blocker** if the clinical lead explicitly accepts the known limitations in writing. It IS a blocker for any clinical adequacy claim.

---

## VIII. Post-Gitex Clinical Adequacy Path

Items that must be completed before the system makes any clinical adequacy claim. Not in scope for the demo.

| Item | Gap | Path |
|---|---|---|
| Self-harm recall ≥95% | Currently 18% | Corpus expansion (crisis_phrases.json) + MARBERT |
| SI recall ≥95% | Currently 37.1% overall | S1 lexicon expansion + MARBERT deterministic classifier |
| Arabic crisis recall measured | Unmeasured (no bench) | Build Arabic eval instrument; CRADLE is English-only |
| Arabic crisis rules live | SK-AR-004/005/006 pending sign-off | Clinical sign-off → activate |
| MARBERT integration | Not built | Exp 4.2 — raises deterministic floor from 37% → target ≥95% |
| Full-turn pool load test | Criteria_eval tested in isolation | Complete turn-level load test under 45 concurrent sessions |
| Consent infra + onboarding audit events | MVP-phase | Not POC scope |

**The system is deployed with known limitations, clinician-acknowledged, with a clear remediation path. It does not claim clinical adequacy. This document is the written record of that position.**

---

## IX. Documents Referenced

| Document | Contents |
|---|---|
| `docs/crisis-recall-gap-2026-06-05.md` | CRADLE bench results, self-harm own KPI, S3 sweep verdict, Arabic two-row coverage |
| `docs/arabic-crisis-rules-signoff-package-2026-06-05.md` | SK-AR-004/005/006 clinical sign-off package |
| `docs/skill-criteria-signoff-package-2026-06-05.md` | 4 skill criteria rewrites, clinical review questions, sample-size caveat |
| `docs/pool-characterization-2026-06-06.md` | False-hold rate curve, cold-start finding, Node 1 independence confirmation |
| `docs/RULES_AUTHORING_CONVENTIONS.md` | Affirmative-target criteria framing rule, S3 single-clause corpus rule |
| `scripts/s3_threshold_sweep.py` | S3 demotion data: threshold sweep across passive_SI CRADLE slice |
| `scripts/calibrate_s3_threshold.py` | GATE_SUPPRESS acceptance-framed phrases; threshold calibration |
| `scripts/pool_characterize_entry_screen.py` | Reproducible pool characterization script |
| `tests/test_entry_screen_integration.py` | 18-test Node 5 gate: explicit + oblique + FP arms; Arabizi stochasticity note |
| `tests/test_cradle_bench.py` | CRADLE bench harness; SK-AR-004/005 revert status documented |
