# Clinician Sign-off Packet — v7.1 Crisis Tiering INTERNAL flag-flip

**For:** product owner + clinical lead signatures. **Decision:** set `CRISIS_TIERING_ENABLED=ON` in the **internal/staging** environment. (Prod flip is a separate, later signed gate — external-exposure.)
**Merge:** PR #85 merged to master, SHA `8611547` (flag default OFF; anchor test passes on master = verified baseline).

## Internal-flip gate list
| Gate | Status |
|------|--------|
| G1–G4 clinical sign-off | ✅ signed 2026-07-03 |
| A–H audit | ✅ all green |
| Per-case non-inferiority regression | ✅ NON_INFERIOR (0 regression) on tip `4bcde0b` |
| Deterministic B replay (flag-OFF = master) | ✅ ZERO DIFF, anchor test passes on master |
| Migration 006 applied + verified in staging | ✅ (see below) |
| Tester-battery replay diffs | ⏳ local ✅; **deployed-app run pending** (this packet, below) |

## Proof outputs
**Proof 2 — per-case non-inferiority (design gate):**
```
232 true-SI cases | fired→T2: 89 | no-signal (pre-existing gap): 143
TIERING-REGRESSION SET {true-SI resolving T1}: 0 → NON_INFERIOR
```
Every fired true-SI case routes T2 via S1; **S3 fired 0/232** at 0.8059 — the strongest empirical evidence that grading English S3-solo signals to a warm tier removes false alarms without losing any detected crisis. (Artifact: `tests/fixtures/recall_baseline_2026-07-03.json`.)

**Proof 1 — deterministic B replay (merge gate):** flag-OFF routing surface **ZERO DIFF** vs the real master tree; `crisis_tier` audit fields absent flag-OFF. (Anchor: `tests/fixtures/deterministic_surface_master.json`.)

## Migration 006 verification (staging DB, isolated from prod)
```
turn 1 (flag-ON T1): crisis_tier=T1  tier_rule_id=s3_solo_en   ✅
turn 2 (flag-ON T2): crisis_tier=T2  tier_rule_id=s1_any       ✅
turn 3 (flag-OFF)  : crisis_tier=NULL tier_rule_id=NULL         ✅
```
Prod preflight ✅: prod flag unset (OFF), prod `session_audit` has NO `crisis_tier` column (006 not on prod — deploy gate holds).

## Deployed-app live replay (staging, flag ON)
**⛔ BLOCKED on a Railway deploy-activation issue — NOT a code/tiering defect.** Merged code was deployed to staging (`railway up`, build + healthcheck **succeeded**) and `SAGE_CRISIS_TIERING=true` is confirmed set on the correct service (`sage-api`/`160e9f65`, serving `sage-api-staging-a334`). But across **two** redeploys, the running app still behaves flag-OFF (`i am feeling hopeless` → `crisis_response`, `crisis_tier=NULL`) — the deployment carrying the flag is not becoming the active one. **Ruled out — flag name/value/scope (the most likely cause, checked):** code reads `os.getenv("SAGE_CRISIS_TIERING")`; staging has `SAGE_CRISIS_TIERING=true` on the **staging** scope; prod has it absent. Correct name, value (`true`), and scope — **not** a `SAGE_CRISIS_TIERING` vs `CRISIS_TIERING_ENABLED` mismatch (the latter is the derived boolean, not an env var).

**Handoff (needs Railway dashboard):** project `4f1811e7`, service `sage-api` `160e9f65`, staging env; latest `railway up` deployment id `5a7378e1-4b11-4a37-973c-fee17aea6515`. Confirm that deployment is **Active/serving** (not a stuck newer build with the old one still live); promote/restart if needed. Then `hopeless → crisis_tier=T1` on the live app, and re-run `scripts/staging_live_replay.py` + the snapshot query.

**What this does NOT block (already verified without the deployed app):**
- Migration 006 + the audit-field write path — proven end-to-end against the **real staging DB** (the T1/T2/flag-OFF table above).
- The tiering routing logic — proven by the local routing replay (2 FP→T1, all crisis→T2) and the per-case regression.

## Day-zero §G monitor snapshot (staging)
_[PENDING the deployed-app run above — the monitors are ready (`scripts/staging_tiering_monitors.sql`); the day-zero snapshot needs the flag-ON app producing live tier rows.]_

## Detection findings (Gate-1 — NOT tiering regressions; carried for full picture)
1. **Arabizi explicit-SI miss** (`ana 3ayez amot…`) — fires nothing (S1-az gap + S3 blind). Missed identically flag-OFF/ON. → clinician queue: candidate S1-az keywords.
2. **EN plan+means euphemism miss** (`i have pills and a plan to end it`, S3 0.793) — **HIGHER priority (B9 never-soften)**; directional hazard: if S3 ever fires it, lands T1 without severity info. → clinician queue: **`si_explicit` plan/means keywords** (urgent). Guarded by a hard drift test.

**Both are pre-existing Gate-1 detection gaps (the documented ~37% recall / S2-MARBERT territory), reinforcing the pilot NO-GO. Tiering neither causes nor cures them.**

## Clinician sign-off sheet — A–D (APPROVED 2026-07-03)
| # | Decision | Recommendation | Status |
|---|----------|----------------|--------|
| **A** | Internal flip — `SAGE_CRISIS_TIERING=ON` in internal/staging, against the completed gate list | Approve (stepped/graded care; both proofs green; false-RED fixed; alarm-fatigue is a real harm) | ✅ **APPROVED 2026-07-03** |
| **B** | Confirm G3 = non-inferiority (Δrecall ≥ 0 vs flag-off), decoupled from the ≥95% pilot KPI | Approve (recall is a detector property; tiering can't move it; proof 2 = 0 detected crises lost) | ✅ **RATIFIED 2026-07-03, recorded here** (formal record of the ruling already made + approved earlier this cycle — not a second decision) |
| **C** | Plan/means → `si_explicit` keywords ("a plan to end it", "end it all", "end my life", "pills and a plan") — **URGENT, B9-class** | Approve urgently, independent of the flip | ✅ **APPROVED 2026-07-03** (exact patterns FP-checked + presented FYI-or-amend) |
| **D** | Arabizi SI → `si_az` keywords (`3ayez amot`, variants) | Approve (fail-closed gate makes routing safe once fired; exposure is in firing) | ✅ **APPROVED 2026-07-03** (rides C's lexicon release) |

**Signatures:** Product owner: ______________  Clinical lead: ______________  Date: 2026-07-03

## G8 risk-acceptance (helpline) — retained
Internal phase keeps `800 46342` / "24/7"; residual risk accepted (IWRC, mislabelled-not-dead + correct co-listed 999). External-exposure gate (dial-test + W7 commit-2 + L0 re-sign) parked until the first external milestone.

## Signatures
Product owner: ______________________  Clinical lead: ______________________  Date: __________
Post-flip: **48 hours of DAILY §G monitor checks** (not weekly) recommended.
