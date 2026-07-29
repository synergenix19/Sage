# Tier-B Storage State — Credential-Class Artifact Handling

Status: STANDING (2026-07-29). Companion to `docs/runbooks/prod-smoke.md` and the
2026-07-29 ledger item "Prod-Smoke Tier B Auth Harness (gap, must not fossilize)".

## What the artifact is

`SAGE_SMOKE_STORAGE_STATE` points at a Playwright storage-state JSON: the cookies and
localStorage of a **signed-in staff session** on the cdai frontend. Whoever holds the
file holds the session. It is therefore **credential-class** — the same handling class
as an API key or a session token, not a test fixture.

## Rules

1. **Never in version control.** The file lives OUTSIDE the repo (e.g.
   `~/.sage/smoke-storage-state.json` on the machine that runs deploy verification, or
   the deploy environment's secret store). Committing it is a credential leak: the
   session must then be rotated (sign the staff account out everywhere / invalidate
   the session), not just the file deleted — git history keeps it.
2. **Deploy-secrets handling.** Distribute it the way `SAGE_API_KEY` is distributed
   (environment secret), never via the repo, chat, or shared drives. File mode `600`.
3. **Enforced, not assumed.** The prod smoke suite runs a MUST-PASS refusal check
   (`storage_state_not_in_vcs`, first check of Tier B, runs even when no storage state
   is configured): the run FAILS if any `*storage*state*.json` is tracked in git, or if
   the `SAGE_SMOKE_STORAGE_STATE` path points inside the repo at a tracked file. A path
   inside the repo that is merely untracked passes with a loud warning — move it out.
4. **Expiry is expected.** Storage state embeds session tokens; when it expires Tier B
   reports its report-only "cannot auth" FAIL. Regenerate per below — do not extend
   session lifetimes to avoid regeneration.

## Producing the artifact

Produced ONCE per environment via the **cdai Playwright auth harness** (see the
prod-smoke runbook), which owns login and its storageState invariant
(`storageState: undefined` + try/finally context close in tests — the harness
invariant). This requires **interactive cdai staff authentication**; it is a
human-in-the-loop step by design and is NOT performed by automation or agents.
Until the deploy environment holds a storage state produced this way, every deploy
record must carry the Tier-B-skipped line explicitly (ledger directive: "report-only,
no harness" must not fossilize into "never checked").
