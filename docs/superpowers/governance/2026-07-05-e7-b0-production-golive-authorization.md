# E7 + B0 — production go-live authorization (2026-07-05)

**Action authorized:** flip `SAGE_ROUTE_PRECEDENCE` (B0) and `SAGE_IPV_PREEMPTION` (E7) **ON in production**, after applying migration 008, via merge of `feat/e-build-b0-precedence` → master → Railway prod deploy.

## Authorization basis
- **Clinical launch sign-off:** ATTESTED by PO this session (2026-07-05). ⚠️ **PO-relayed, not a countersigned artifact.** This is distinct from Rohan Sarda's 2026-07-04 *mechanism/build* approval (review-cycle-package §E), which was explicitly "build, not the flag flip." **Obligation:** file the durable clinician launch sign-off (or a note confirming Rohan's approval extended to launch) against this record.
- **Prod recall number:** PO confirms the E7 recall gate holds on the production detector config (the POC-vs-prod re-confirm caveat the harness flags). Recorded as attested; a prod harness run is the durable confirmation and should be attached.
- **Recall gate (measured):** E7 100% positives / 100% precision on the POC `safety_check` (fixture ground truth). B0 has no recall gate (mechanism + audit only).

## Why this is not blocked by GL-0
GL-0 (crisis recall ~37% vs ≥95%) is fail-closed for **external launch** (opening to new pilot users). These flags do NOT open the product — the platform is already live. E7 is strictly *safer* for the affected population (IPV disclosers get a referral instead of assertiveness coaching); B0 only adds audit observability. Neither degrades crisis handling.

## Prerequisites (order)
1. **Migration 008 applied to prod** (`fired_safety_routes`, `precedence_winner` on `session_audit`) — DEPLOY GATE. Without it, a flag-ON audit write fails (CRITICAL AUDIT FAILURE). Additive, nullable, no backfill — low risk.
2. Merge to master → Railway deploys (flags still OFF by default → byte-identical until step 4).
3. Verify prod healthy on the new build (flags OFF).
4. Flip both env vars ON (`railway variables`).
5. Functional-test via Playwright (E7 §6 suppression + DFWAC/Ewaa referral; B0 precedence; crisis+IPV multi-hit).

## Reversibility
Both flags are instant kill-switches: `SAGE_ROUTE_PRECEDENCE=false` / `SAGE_IPV_PREEMPTION=false` reverts to byte-identical v7 with **no redeploy**. Migration 008 is additive and stays (harmless when flags OFF).

## Still-open obligations (post-flip, tracked — not blockers)
- Durable clinician launch sign-off artifact (above).
- Prod re-confirm harness run attached as evidence.
- **CF-005 consolidation fold** (E7): fold `ipv_preempt_expansion` into CF-005 vNext via CMS, retire the flag-gated side-path. The flag-gated path is the ship mechanism; the fold is the destination.
