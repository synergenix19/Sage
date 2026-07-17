# D1 medical screen — SHADOW dark-deploy record (#338)

**Status: PREPARED, HELD at the lock chain on enumerated blockers (below). Artifact verified-deployable.**
Deploy authorized by user 2026-07-17 (explicit go + enumerated constraints). One-writer-to-prod: this record
is the claim.

## What deploys
The D1 silent-shadow artifact on `cdai/d1-medical-screen`, merged with `origin/master` (b4d5001a), verified
tree. Steady state: `SAGE_D1_SCREEN=OFF` (enforce off), `SAGE_D1_SCREEN_SHADOW=ON` (shadow window open,
route-identity — observes, never serves). Rollback = `SAGE_D1_SCREEN_SHADOW=0` → proven identity.

## Ratified monitoring constraint (verbatim, user 2026-07-17)
> "…post-flip monitoring against the answer-class distribution criteria — the unclear/evaded/clear_no/
> contraindication_disclosed rates from RULING 3, unchanged in number, read from the first N real screened
> turns (or a fixed window, whichever fills first) as a monitored-enforce gate: if unclear dominates, the
> question wording returns to Vee before the screen is called verified; if the zero-tolerance rows fire
> (crisis-in-answer mishandled, audit swallow), enforce halts back to shadow, not tunes."

**RULING 3 gate split (ruled as proposed):** shadow reads **fire-volume + disclosure-population**; post-flip
monitored-enforce reads **answer-class distribution**. Thresholds unchanged; only gate placement made honest.
This gate-placement change **rides the one-message-two-confirms owed to Vee** (comma-swap bytes + this split)
— her two lines are owed **before the flip**, and per (a)-sequencing need **not** land before this dark
deploy (shadow serves nothing and reads no answer rows).

## Deploy-record constraints (enumerated, user 2026-07-17)
1. Lock claimed via `deploy_prod.sh production <merge-sha>` (not raw `railway up`).
2. Ancestry gate (deploy_prod.sh built-in: bc3cb4b 5852ea1 944939b 27bfd3b 8079caa 7a57107).
3. Full-SHA cache-bust (`RAILWAY_GIT_COMMIT_SHA=<sha>`, `SAGE_BUILD_SHA` deleted).
4. Control #6 clinical-surface diff. Signed-field files entering prod: the D1 EN question bytes +
   `_ROUTES` branch table. **Cite:** sign-off `2026-07-17-d1-vee-signoff-V.md`. **Open line item (honest):**
   the comma-swap bytes confirm from Vee is **pending** (owed with the RULING 3 split, before flip — not
   before this shadow deploy). Named here, not a footnote.
5. **Migration 014** (`014_add_screen_shadow_to_session_audit.sql`) MUST run on prod BEFORE
   `SAGE_D1_SCREEN_SHADOW=1`, or the shadow audit write fails on unknown columns (the 012/013 failure mode).
6. Behavioral signature post-deploy: standing probe set (crisis, both vetoes, #219 pair, BA, §1e) PLUS the
   D1-specific pair — (i) acute-overwhelm TIPP-routing turn, shadow ON → served route byte-identical to
   pre-deploy AND the shadow audit row lands with the observation keys; (ii) a non-screen turn → row
   byte-identical to master.
7. Rollback: `SAGE_D1_SCREEN_SHADOW=0` (proven identity). Held here.

## BLOCKERS to a clean autonomous fire (held, surfaced to user)
- **B1 — cannot read current PROD SHA.** `/health/version` returns `Unauthorized` (needs `SAGE_API_KEY`).
  Control #6's clinical-surface diff needs `PROD_SHA..DEPLOY_SHA`; without the prod SHA the baseline is
  unverifiable. Need the key (or you run `! curl -H "x-api-key: $SAGE_API_KEY" .../health/version`).
- **B2 — deploy tree couples HR-1 #348.** master tip (b4d5001a) includes the HR-1 §5 neutrality interim
  fix (`fc8b7f3d`) and #348 verification. If prod is behind master, deploying master-tip carries that
  change live as a side effect of the D1 deploy. Control #2 mandates deploying master-tip (don't drop
  others' work), but "one writer to prod" + Lane coordination means #348's owner should confirm it is
  either already-on-prod or cleared-to-ride. Unverifiable until B1.
- **B3 — merge-to-master is a PR+CI gate.** Branch protection: PR required + CI hard gate. The merge SHA
  (the real deploy tree, control #2) does not exist until the PR merges green. Deploy pins THAT sha.

## Verification already banked (deployable artifact)
- Merged tree: signed-fields ✅ (8/8, incl. master's HR-1 activation re-sign + D1 pins), state-channels ✅,
  parity ✅, reads-raw ✅. 65 D1 tests + 83 HR-1 tests green. Regression delta zero (the 2 SK-EN-002 FP
  failures pre-exist on clean origin/master; not introduced by this merge).
- Shadow route-identity proven byte-for-byte; seam declared+reset+persisted; PDPL approved (anonymised
  class+route). GATE 0 addendum (shadow surface) on the record.
