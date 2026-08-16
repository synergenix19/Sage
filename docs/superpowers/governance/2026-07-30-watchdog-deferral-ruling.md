# Ruling: scheduled flag watchdog DEFERRED to production hardening (PO, 2026-07-30)

**Decision (PO, in-session 2026-07-30):** do not implement the scheduled watchdog now. The
structural fix for the drift class is already merged and costs nothing ongoing: config-as-code
apply. The flag state lives in a committed file; every deploy re-asserts it idempotently, so a
pasted stale env block or a parallel stream's template gets corrected at the next deploy
instead of persisting silently, and any deliberate change goes through a PR the signed-value
check inspects. The scheduled watchdog is a detection layer on top and is deferred to
production hardening. **POC drift controls = config-as-code apply + deploy probe.**

**Premise verification and cure (same day):** at ruling time the "every deploy re-asserts it"
premise was NOT yet true — `deploy_prod.sh` did not invoke `apply_prod_flags.py` (the
enforcement-surface-misses-the-path class, fifth instance this week). Cured in the same PR as
this record: step 5 of `deploy_prod.sh` now runs the idempotent apply on production deploys
(refusal aborts the deploy and releases the lock), and the mandatory post-deploy probe
instructions now include the one-shot `flag_watchdog.py` drift check.

**Accepted residual, stated for the record:** between deploys, a direct variable write serves
until the next deploy or on-demand probe detects/corrects it. That inter-deploy window is the
detection layer the deferral gives up; the PO accepts it for the POC phase. The on-demand
watchdog remains available at any time (`scripts/flag_watchdog.py`, alert-first, no
auto-revert per the 2026-07-29 stand-down).

**What reopens this:** production hardening phase, or a fourth drift incident — a recurrence
is a watchdog-named incident per the register row and would be evidence the inter-deploy
window is being exploited faster than the deploy cadence closes it.

**Supersedes:** the open "Ruling 1" question from the 2026-07-29 session (environment-clock
scheduling + heartbeat) — closed as deferred, not rejected; the heartbeat requirement travels
with it to production hardening.
