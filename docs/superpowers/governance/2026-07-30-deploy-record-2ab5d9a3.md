# Deploy record — 2ab5d9a3 (2026-07-30): inaugural governed cycle of the flag re-assert path

**Authorization:** PO, in-session 2026-07-30, conditions 1–3 (full deploy discipline;
consult-row pre-verify; post-deploy readback). Explicitly NOT a feature push: every flag
rides exactly as registered; no activation gate closed.

**Delta correction (premise vs record):** the authorization listed #385/#386/#391/#392/#396
as the payload — those were ALREADY serving: the parallel stream's `ada1855a` deploy earlier
on 2026-07-30 carried them (including the #386 readback widening — 38 raw_env fields
serving). The actual delta `ada1855a..2ab5d9a3` = PR #374 (§1c reconciliation packet +
disposition-ownership registry + CI check) and PR #393 (shakedown artifact): docs + CI
machinery, **zero `src/` or `config/` changes**. The shakedown premise held, more literally
than stated.

## The cycle, as executed

1. **Pre-verify (condition 2, exceeded):** full three-way watchdog instead of a manual
   consult-row look — CLEAN across all 50 registered flags; `SAGE_INFO_REQUEST_CONSULT`
   agreed committed=desired=serving=`true` (the "seeded as-served false" line in the
   authorization was stale; the row has been true/signed since the #387 restore).
2. **deploy_prod.sh production 2ab5d9a3…** from the deploy worktree detached at the deploy
   SHA: lock claimed, ancestry passed (6/6), cache-bust set, and **step 5's inaugural run**
   — full 50-flag three-column convergence table, `[apply] already converged — nothing to
   do (idempotent)`. The previously-unbounded inter-deploy drift window closed EMPTY.
3. **`railway up --detach`** → serving converged to `2ab5d9a37430` (readback-verified,
   build_sha truthful).
4. **Readback (condition 3):** consult `true`, consult_sources `true`,
   `crisis_copy_templated: true` — all unchanged, as required.
5. **Drift probe (new checklist line, first post-deploy use):** watchdog CLEAN, 50 flags.
6. **Behavioral probe:** prod smoke `--tier all` — **all must-pass green** (crisis
   resources EN + AR; helpline `800-4673`; MM entry-screen derealization hold; precedence
   header proxy; storage-state-not-in-VCS guard; 3 flag readbacks; plain-turn header
   negative). **Tier B skipped — explicit line per the ledger directive:** report-only
   `tier_b_auth` FAIL, no `SAGE_SMOKE_STORAGE_STATE` on this machine. Producing it is
   an interactive human step by design (tier-b-storage-state runbook: "NOT performed by
   automation or agents"); the 10/10 probe begins the first deploy after a human runs the
   cdai auth harness once.
7. **Lock released** via `railway variable delete DEPLOY_LOCK` (singular — the working
   form); post-release readback stable at `2ab5d9a37430`.

## Rider dissolution (same PR as this record)

The widened readback now serves and the watchdog confirmed coverage, so per the register
header's dissolution rule the `serving_verified: false` riders are DELETED on the 20
now-covered vars. 13 rows keep the rider — vars the serving readback still does not expose
(infra/pool/corpus/SKILL_* families); they remain desired-only checks until a future
readback widening.

## Rollback

Redeploy `ada1855a` (docs/CI-only delta; no served-behavior difference between the two
builds by construction).
