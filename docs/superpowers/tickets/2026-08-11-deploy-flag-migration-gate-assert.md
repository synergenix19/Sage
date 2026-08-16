# Ticket: deploy pipeline should mechanically assert flag→migration-gate correspondence

**Filed:** 2026-08-11 · **Source:** PR #414 merge-cycle migration reconciliation (controller check of prod schema vs migrations ledger)
**Status:** open · **Type:** deploy-pipeline hardening (small) · **Not a regression**

## The reconciliation that prompted this (and its verdict: no defect)

Prod `session_audit` has 018's column (`knowledge_retrieval_purpose`) and none of 017's
`psychoed_*` columns. Initial read was out-of-order application; the ledger
(`migrations/MIGRATIONS.md`) shows it is the flag-gated design working as documented:
migrations are numbered/claimed on master but APPLIED per-flag ("DEPLOY GATE for SAGE_X
flip" in each header). 018 applied because SAGE_CONSULT_SOURCES flipped (#389); 017 stays
claimed because SAGE_PSYCHOED_PATHWAYS is OFF. audit.py writes gated columns only when the
corresponding signal fired, so flag-OFF rows are byte-identical and code deploys are safe
ahead of their migrations (Check B discipline; pinned by the flag-off suites).

## The gap worth closing

The flag→migration correspondence is enforced by convention (migration headers + operator
care at flip time). The 012/013/014/015 failure mode named in 017's own header — flag ON
before its migration → audit write fails on unknown columns — has no mechanical guard.
016's flip verified columns manually; nothing stops a future flip from skipping that step.

## Fix shape

In the deploy/flip pipeline (deploy_prod.sh + the apply/watchdog path, #386 conventions):
a pre-flip assert that, for every SAGE_* flag resolving true in the target environment,
the migration(s) its header names as DEPLOY GATE have their columns present
(information_schema query, read-only). Refuse the flip on absence, listing the missing
migration by number. A maintained flag→migration map is acceptable if it carries a
sync-check against the migration headers (house pattern: vocabulary/table sync tests).

## Non-goals

NOT a contiguous-sequence assert — non-contiguous applied-sets are by design (claimed vs
applied). NOT a schema-migration runner change. The 2026-07-07 out-of-band 009-011 notice
stands separately.

## DoD

Assert wired into the sanctioned flip path; one negative test proving a flag with an
unapplied gate migration refuses with the migration named; MIGRATIONS.md note pointing at
the assert as the mechanical successor to header-convention-only.
