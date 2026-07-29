# Ledger Additions — 2026-07-29

## 1. Signed-Flag Deploy Gate (fast-follow, sibling of classifier_degraded)

**The invariant to make structural (reviewer-required):** the flag register gains a
`signed_value` column for every flag carrying a clinical or governance signature,
and the deploy gate (the #258 build-side machinery, natural host) REFUSES any
deploy whose resulting config would change a signed flag's value unless the deploy
references a ratification record. Same pattern as the ancestry check: drift blocked
at the gate, not discovered at readback.

**Rationale document (same-day incident):** 2026-07-28 — two individually
legitimate deploy streams sharing one environment silently reversed a
clinician-signed activation (`SAGE_INFO_REQUEST_CONSULT`, Vee B1). The deploy lock
worked as designed for BOTH deploys and protected against none of it: the lock
serializes deploys; nothing reconciles their semantic intent. This is the third
instrument failure of the same shape (run-1 non-parity flags; the
silent-unpin-by-construction resilience path; now signed-flag drift). The new
readback coverage detected it within minutes — detection-after-serving is the
weakest acceptable posture for signed flags, hence this gate.

**Sequencing note:** implementation rides the flag-class taxonomy sign-off (the
register is where `signed_value` lives); until then, the readback + deploy-record
discipline is the compensating control.

## 2. Prod-Smoke Tier B Auth Harness (gap, must not fossilize)

The 2026-07-28 deploy's behavioral probe ran 9/10 with Tier B (frontend) skipped:
no `SAGE_SMOKE_STORAGE_STATE` Playwright storage-state file exists in the deploy
environment. Reviewer directive: ledger it so "report-only, no harness" does not
fossilize into "never checked." Fix: produce the storage state via the cdai
Playwright auth harness (per prod_smoke runbook) and store it where deploy
verification runs; until then every deploy record must carry the Tier-B-skipped
line explicitly.
