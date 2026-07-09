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

---

# Third infra finding (same rollout) — Railway deploy cutover unreliable

**2026-07-03, staging `sage-api`.** New builds passed healthcheck and were reported **active/SUCCESS** (`4c3e6bb8`, `5a521a2c`, `78ea56da`), yet **traffic kept serving stale code**: the #89 lexicon fired (post-#89 serving) but the #90 default-ON + #91 strict-parse behaviour never took effect (`hopeless`→OFF with the var UNSET, which #91 makes impossible for live post-#91 code) and the #91 `[sage/startup]` boot log never appeared. i.e. the serving container was pinned post-#89/pre-#90 while the dashboard reported the newest deployment active. Reproduced across `railway up`×3, `railway variables --set`×2 + delete, `railway redeploy`/restart×2.

**Impact:** you cannot trust `railway up ... SUCCESS` as proof that new code is serving. Verify with a **behavioural probe + boot log**, not the deploy status. This is why the crisis-tier flip could not be validated on staging from the CLI.

**Combined pattern (3 findings, one rollout):** (1) migrations don't reach staging; (2) env vars not injected into containers; (3) deploys don't cut over. All three are **deployment-substrate reliability** gaps. Strong, concrete input for the **v7 Full-Build case to move the target env to Azure**, where deployment cutover and env application are contractually observable. Mitigation already shipped in-code: default-ON (independent of injection) + strict parse (immune to mangled values) + boot-observable flag log (turns "is new code serving?" into a log read).

---

# Note — /health/version deep-diagnostics must be gated before external exposure

The deep `/health/version` (added during the 2026-07-04 bug-#2 hunt) executes the crisis-tier resolver and exposes module paths, `PYTHONPATH`, and the flag state on an **unauthenticated** endpoint. Acceptable for the internal POC; **before external exposure, gate or strip the deep fields** (keep only a minimal `{status}` or require the API key). Rides the existing external-exposure gate (dial-test + W7 commit-2 + L0 re-sign).
