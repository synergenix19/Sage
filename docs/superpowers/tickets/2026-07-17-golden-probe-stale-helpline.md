# Ticket: `deploy_golden_probe.sh` hard-codes the removed helpline `800 46342`

**Found:** 2026-07-17, during the HR-1 Stage 1 flip deploy verification.

**Problem:** `scripts/deploy_golden_probe.sh` asserts `GOLDEN="800 46342"` on every run. The GL-1
reversal (2026-07-13, `docs/superpowers/governance/2026-07-13-gl1-crisis-helpline-reversal.md`)
removed `46342` from prod in favour of the National Mental Support Line `800-HOPE (800-4673)`.
Prod is live-verified to carry `4673` and NOT `46342`. So this probe, if run as a deploy gate today,
would **false-fail** — a green control asserting a value that is deliberately gone.

**Impact:** Not a live-safety issue (the crisis card is correct in prod). It is a *stale guard*: a
control that no longer watches reality. It was **not** used as a gate for the HR-1 deploy.

**Fix:** Update `GOLDEN` to `4673` (or `800-HOPE`), matching the single-source `CRISIS_RESOURCES` /
`CRISIS_CONFIG.number`. Cross-check against `signed_clinical_fields.json:crisis_helpline_number`
(sha pinned, PO-signed 2026-07-13) so the probe and the signed field cannot drift apart again.

**Owner:** safety lane (crisis-copy). Low effort, do before the next deploy that would run it.
