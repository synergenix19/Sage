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

---

# Second infra finding (same rollout) — Railway env-injection unreliable

**2026-07-03.** A **configured** service variable (`SAGE_CRISIS_TIERING=true`, staging `sage-api`) was **not reliably injected into the running container**: `railway run … printenv` and `railway variables` both showed `true`, but the deployed container behaved as if it were empty/unset. Confirmed across `railway up`×3 (deployments `5a7378e1`, `b61ae37a`, `4c3e6bb8` — all `SUCCESS`/serving, new code confirmed live), `railway variables --set`×2 (incl. staging-linked), and `railway redeploy`. Ruled out: var name/scope, `.env` shadow (`.dockerignore` excludes it), Dockerfile `ENV`, `load_dotenv(override=False)`. Best-supported mechanism: the platform delivered an **empty string**, which the old `== "true"` parse read as OFF.

**Mitigations shipped (PR #90/#91):** (a) code default flipped ON so tiering no longer depends on injection; (b) strict fail-safe parse (only `"false"` disables — empty/garbage → signed default); (c) boot-observable log of the resolved flag + raw env. **Consequence going forward:** don't rely on Railway var injection for safety-critical toggles; assert runtime state from the boot log, not the config UI.

**Pattern:** two infra findings from one rollout (migration parity + env injection) — worth a paragraph in the Full-Build infra review, and a mild argument for the **Azure target env** in v7 proper.
