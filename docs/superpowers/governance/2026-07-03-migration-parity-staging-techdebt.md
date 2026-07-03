# Tech Debt — migrations don't reach staging (schema drift) 

**Filed:** 2026-07-03 (caught during the tiering staging validation). **Severity:** deploy-process / data-integrity. **Owner:** _repo admin / eng lead (assign)_.

## The hole
Staging (`jrfrficjdwguqbvumdyo`) and prod (`tcekehffneiqcdyhzobi`) are **separate Supabase projects** and migrations do **not** auto-sync. **PR #84's migration 005 (knowledge_query columns) ran on prod but never on staging** — so staging's `session_audit` was two migrations behind (missing 004 + 005). Any audit write from current code fails on staging (`PGRST204: column not found`), and **staging validation silently runs against the wrong schema** — the exact thing staging exists to prevent.

## Caught + fixed this time
Applied 004/005/006 to staging manually during the tiering validation. But the *cause* is a process gap, not a one-off.

## Required fix (deploy checklist)
1. **Migrations must apply to staging before or with prod** — never prod-only.
2. Add a **schema-parity check** to the deploy checklist: compare the applied-migration list (or `session_audit` columns) between staging and prod; **fail the deploy/validation if they diverge**. Cheap (one `\d` diff) and prevents the next silent drift.

Same weight as the CI-cannot-enforce-required-checks item — both are safety/data-integrity process holes surfaced by this workstream.
