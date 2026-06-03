# SageAI Psychotic Symptoms Safety Layer — Findings Register

**Audit scope:** Tasks 1–8, branch `feat/psychotic-symptoms-safety`  
**Audit date:** 2026-06-04  
**Auditor:** Automated audit (S0 pre-audit gates)  
**Anchored to:** `docs/SageAI_architecture_current.md` (9-node live implementation)  
**Baseline:** Python 3.12.4 via uv, S3_THRESHOLD=0.8059, gap=0.3234  

---

## Severity Rubric (S7)

| Severity | Meaning |
|---|---|
| **Critical** | Safety rule fires incorrectly or doesn't fire; data loss; wrong clinical routing in a live session |
| **High** | Activation blocker; schema violation; mis-gated rule (active wrong state) |
| **Medium** | Integration gap that degrades behaviour but doesn't produce wrong clinical outcome |
| **Low** | Documentation inconsistency, test gap, cosmetic |

---

## S0 Findings

### Standing OPEN (activation blockers — not closeable by this audit)

| ID | Section | Finding | Severity | Owner | Status |
|---|---|---|---|---|---|
| F-S01-001 | S0.1 | **Option B governance gap.** `docs/SageAI_architecture_current.md` is a developer-authored living reference, not ratified as v8 through external sign-off (devil's advocate, clinical-scenario validation, peer review, clinician sign-off). `knowledge_retrieve` (9th node) was added 2026-05-26 by the architect without a formal approval record. The plan is anchored to a document whose supersession claim is self-asserted. All engineering PASS results in this audit mean *correct against current code*, not *cleared for users*. | **High (activation blocker)** | Architecture/clinical lead | OPEN |
| F-S01-002 | S0.1 | **9-node crisis topology not clinically validated.** No clinical-scenario + adversarial validation equivalent to v7's 10-scenario gate exists for the 9-node design, specifically the `crisis_response` node and its documented `output_gate` bypass. The bypass was verified as intentional in the architecture doc (§2.1, four stated reasons), but its clinical safety properties have not been independently validated against a scenario corpus. | **High (activation blocker)** | Clinical lead | OPEN |

---

### S0.2 — Activation state findings

| ID | Section | Finding | Severity | Status |
|---|---|---|---|---|
| F-S02-001 | S0.2 | **Skill has no direct `active` field.** `psychotic_referral.json` has no `active` field (skills schema does not support one). The audit plan expected `active: false` on the skill itself. The actual gating is **transitive**: the skill is in `KEYWORD_SEMANTIC_SKIP` and `CLUSTER_EXCLUSIONS`, has empty `target_presentations` and `semantic_description`, and can only be reached via the `psychotic_disclosure` clinical flag auto-select path — which is gated by CF-006 being `active: false`. Gating chain is correct and sufficient, but indirect. | **Low** | Engineering | ACCEPTED — by design |

**All four activation states verified:**

| Artifact | Required | Actual | Result |
|---|---|---|---|
| CF-006 (`clinical_flag_patterns.json`) | `active: false` | `active: false` | ✅ PASS |
| PI-CF-006 (`clinical_flag_adaptations.json`) | `active: false` | `active: false` | ✅ PASS |
| `psychotic_referral` skill | gated | Transitively gated via CF-006 (see F-S02-001) | ✅ PASS (with note) |
| CK-CH-001 (`crisis_keywords.json`) | `active: true` | `active: true` | ✅ PASS |
| CK-CH-002 (`crisis_keywords.json`) | `active: true` | `active: true` | ✅ PASS |

---

### S0.3 — Environment & dependency integrity

| Check | Expected | Actual | Result |
|---|---|---|---|
| Project Python (via uv) | 3.12.x | 3.12.4 | ✅ PASS |
| System `python` command | — | 3.14.3 (system PATH, not project Python) | ℹ️ NOTE |
| `uv.lock` diff | empty (no new deps) | empty | ✅ PASS |
| Test collection (5 new files) | no import errors | 44 tests collected, 0 errors | ✅ PASS |

**Note on Python 3.14:** System `python` command returns 3.14.3 (Homebrew). All test execution uses `uv run` which resolves to 3.12.4 via the project venv. No impact on correctness.

---

### S0.4 — Database schema

| Table | Required columns present | Baseline rows | Result |
|---|---|---|---|
| `clinician_review_queue` | All: user_id, session_id, reason, source, severity, payload, status, flags_timeline, created_at | 1 row | ✅ PASS |
| `mood_scores` | All: user_id, session_id, score, created_at | 0 rows (expected — mood_check_in skill not triggered) | ✅ PASS |
| `session_summaries` | All: session_id, user_id, summary_text, embedding, safety_level, mood_score, created_at | 6 rows baseline | ✅ PASS |

**PostgresNotifier column alignment:** INSERT statement in `notification.py` references all columns present in `clinician_review_queue` schema. No mismatch. ✅

---

### S0.5 — Baseline capture (REOPENED — recall gate AMBER, not PASS)

> **Audit note:** The initial S0.5 entry incorrectly recorded the crisis-recall gate as PASS. Three errors in that assessment were identified and corrected here. This section supersedes the original S0.5 entry.

#### S3 threshold and calibration

| Metric | Value | Gate | Result |
|---|---|---|---|
| S3_THRESHOLD | 0.8059 | unchanged (branch vs master scores identical to 4dp) | ✅ PASS |
| S3 calibration gap | 0.3234 | ≥ 0.10 required | ✅ PASS |
| This branch caused score drift | NO — verified by direct comparison | no regression from Task 6 | ✅ CONFIRMED |

**Score comparison (branch vs master, all 6 near-threshold phrases):**

| Phrase | Master score | Branch score | Delta | Status |
|---|---|---|---|---|
| CATCH-1 (SF-1 paraphrase) | 0.8559 | 0.8559 | 0.0000 | catches |
| CATCH-2 (SF-1 paraphrase) | 0.8370 | 0.8370 | 0.0000 | catches |
| CATCH-3 (SF-1 paraphrase) | 0.8158 | 0.8158 | 0.0000 | catches |
| CATCH-4 (SF-1 paraphrase, narrowest) | 0.8089 | 0.8089 | 0.0000 | catches in isolation; **fails under load** |
| MISS-1 (xfail, pre-existing) | 0.7950 | 0.7950 | 0.0000 | misses |
| MISS-2 (xfail, pre-existing) | 0.7670 | 0.7670 | 0.0000 | misses |

Task 6's command_hallucination corpus additions are semantically orthogonal to passive SI phrases. Zero score drift. The pre-existing/not-caused-by-branch claim is **demonstrated, not asserted**.

#### Crisis recall — AMBER (gate not yet met)

**Finding F-S05-001 (Critical — activation blocker):** S3 passive-SI recall is below the ≥95% gate. This is a pre-existing finding documented in `test_s3_semantic.py` lines 113–128 as *"PRE-PRODUCTION SAFETY BLOCKER"* with `strict=True` xfail markers.

**Correct denominator:** SI phrases the system should detect = SF1_GATE_PHRASES (12) + SF1_PARAPHRASE_CATCH (4) + SF1_PARAPHRASE_KNOWN_MISS (2) = **18 total SI phrases**

| Condition | Detected | Total | Recall | Gate (≥95%) |
|---|---|---|---|---|
| Isolated serial (best case) | 16 | 18 | **88.9%** | ❌ BELOW GATE |
| Under full-suite load (production proxy) | 12 | 18 | **66.7%** | ❌ BELOW GATE |

**Error in original assessment:** `28/28 non-xfail = 100%` computed recall only over phrases not already marked as failures, excluding the 2 known-miss SI phrases from the denominator. The 30 total test cases include 4 infrastructure tests + 2 SF-6 false-positive tests + 12 SI gate phrases + 4 SI paraphrase-catch + 2 SI known-miss. The recall gate applies to SI detection, not the full test count.

**Under-load failures are safety-relevant, not "environmental":** The 4 `SF1_PARAPHRASE_CATCH` phrases fail under load because CATCH-4 has a margin of only +0.0030. Production runs with the model loaded once at startup — which eliminates ANE contention for individual requests — but this audit cannot verify that claim on non-deployment hardware. The under-load behavior documents a genuine threshold margin risk.

**Hardware:** MacBook Pro, Apple M4, 16 GB RAM. This is the development machine, not production infrastructure. Step 3 of the recall investigation (deployment-hardware verification) cannot be completed locally and remains OPEN.

#### Non-crisis regression: CONFIRMED NONE

| Check | Result |
|---|---|
| Full suite (excl. test_s3_semantic.py), serial | **1423 passed, 0 failed, 10 skipped, 1 xfailed** ✅ |
| Full suite master vs branch — S3 test IDs | Pre-existing ID comparison pending (background run) |
| New test count | 1434 passed in full run ✅ |

---

### S0.6 — Ground rules compliance

| Rule | Status |
|---|---|
| Every finding has exact command + expected + actual | ✅ Documented in register |
| Severity uses S7 rubric; clinical impact dominates | ✅ Applied |
| No real/simulated user exposed to output | ✅ Test harness only |
| Read-only DB access — no PII writes | ✅ Only SELECT queries in S0.4 |

---

## Summary

### S0 Exit Criteria Assessment

| Gate | Status | Detail |
|---|---|---|
| S0.2: All four activation states match table | ✅ PASS | CF-006 inactive, CK-CH-001/002 active, skill transitively gated |
| S0.3: No dependency drift | ✅ PASS | `uv.lock` unchanged; Python 3.12 via uv confirmed |
| S0.4: DB targets exist and match write spec | ✅ PASS | All columns present, write signature aligned |
| S0.5: Baseline captured; recall ≥ 95% | ⚠️ **AMBER** | Recall 88.9% isolated / 66.7% under load — below 95% gate. Pre-existing (scores unchanged from master). Deployment-hardware verification incomplete. |
| S0.1: Governance rows logged as OPEN | ✅ RECORDED | F-S01-001 and F-S01-002 logged as activation blockers |

**S0 exit criteria: NOT MET.** F-S05-001 (Critical) blocks exit. S0.5 recall gate is AMBER, not PASS. Activation is blocked until the recall gate is resolved independently of how S1–S7 come back.

---

## Open Findings Summary

| ID | Section | Severity | Summary | Closeable by engineering? |
|---|---|---|---|---|
| F-S01-001 | S0.1 | **High (activation blocker)** | Option B governance gap — v8 ratification pending | No — architecture/clinical lead |
| F-S01-002 | S0.1 | **High (activation blocker)** | 9-node crisis topology not clinically validated | No — clinical-scenario validation program |
| F-S05-001 | S0.5 | **Critical (activation blocker)** | S3 passive-SI recall 88.9% isolated / 66.7% under load — below ≥95% gate. Pre-production blocker documented in codebase; this audit confirms it is unresolved and must be fixed before user exposure. Near-term partial: add S1 keyword patterns for highest-frequency passive-ideation constructions ("better off without me", "my absence would", "space I take up", "relieved if I were gone"). Full fix: richer S3 corpus anchors + recalibration. | Yes — engineering + clinician sign-off on new patterns |
| F-S05-002 | S0.5 | **High** | Deployment-hardware recall verification incomplete. Scores measured on M4/16GB MacBook (dev machine). Production ANE behavior is unconfirmed. Under-load failures cannot be attributed purely to local hardware contention without a production-environment run. | Partially — requires production-class hardware run |
| F-S02-001 | S0.2 | **Medium** (upgraded from Low) | `psychotic_referral` skill has no direct `active` gate; CF-006 sign-off and skill sign-off are listed as separate approval checklist items but share a single activation mechanism. Flipping CF-006 to `active: true` silently activates the skill in the same move. Recommend a pre-activation CI assertion verifying the skill has been independently approved. | Yes — CI/pre-commit gate |
| F-S03-001 | S0.3 | **Low** | System `python` command returns 3.14.3 (Homebrew). No CI guard prevents a worker from invoking bare `python` instead of `uv run`. If any agentic implementer or CI job calls bare `python`, they run against 3.14. | Yes — CI guard |
