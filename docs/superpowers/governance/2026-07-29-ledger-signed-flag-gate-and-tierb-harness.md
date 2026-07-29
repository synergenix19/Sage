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

**RECURRENCE #2 — 2026-07-29, same flag, ACTIVE mechanism (escalates urgency):**
within ~18h of the owner-ratified restore, `SAGE_INFO_REQUEST_CONSULT` desired went
`false` AGAIN with no new record on master, and a restart served it before
detection (the parity helper's refuse-on-drift caught the desired/serving split;
by verification time serving had flipped too). Twice in 24h = an active reset
mechanism (likely a variable-template or env-block in one of the parallel streams'
deploy tooling), not one-off human error. Ruling Step 2b re-executed by the command
session (standing authorization, "executable without returning to me"): restored
`true`, readback-poll to confirm. Consequences: (a) this gate item is no longer a
fast-follow nicety — until it lands, the compensating control must include
IDENTIFYING AND DISABLING the reset mechanism, which is now its own action item for
the deploy owner + parallel-stream owners; (b) the EMR Phase 0 baseline requires a
QUIESCED signed-flag state — re-blocked until the reset source is found or two
consecutive clean readback checks span a deploy cycle.

## 2. Prod-Smoke Tier B Auth Harness (gap, must not fossilize)

The 2026-07-28 deploy's behavioral probe ran 9/10 with Tier B (frontend) skipped:
no `SAGE_SMOKE_STORAGE_STATE` Playwright storage-state file exists in the deploy
environment. Reviewer directive: ledger it so "report-only, no harness" does not
fossilize into "never checked." Fix: produce the storage state via the cdai
Playwright auth harness (per prod_smoke runbook) and store it where deploy
verification runs; until then every deploy record must carry the Tier-B-skipped
line explicitly.
