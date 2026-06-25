# Ticket: Make CI a true hard merge gate without deadlocking non-code PRs

**Filed:** 2026-06-24 · **Status:** open · **Type:** CI/branch-protection follow-up

## Problem
Branch protection was reconfigured 2026-06-24 to remove the admin-bypass need (PR required,
**approvals = 0**). The intended third property — **CI-required as a hard merge gate** — could
NOT be turned on as-is: `unit-gate.yml` and `ferry-gate.yml` are **path-filtered**
(`src/sage_poc/**`, `tests/**`, `server.py`, …). A PR that touches only docs / scripts / .github
triggers **no run**, so a required status check **never reports**, and with `strict` the PR
**deadlocks** (can only merge via admin bypass — the exact thing the reconfig removed).
Confirmed live: PR #62 (docs-only) reported "no checks" and was unmergeable until the required
checks were dropped.

## Interim state (now)
`required_pull_request_reviews.required_approving_review_count = 0`, `required_status_checks = null`,
`enforce_admins = false`. Net: PR required, self-merge allowed (no bypass), **CI runs and is
visible on code PRs but is not a hard block.** A red code PR could merge if the author ignores CI.

## Fix — guard-job pattern (gives hard CI without deadlock)
For each gate workflow add a job that triggers on **all** PRs (no path filter) and **reports the
same required context name**, but only runs the heavy suite when relevant paths changed (e.g.
`dorny/paths-filter` or a `git diff` guard); otherwise it passes trivially. Then re-add the two
contexts to `required_status_checks` (strict). Result: code PRs are hard-gated on the real suite;
docs/scripts PRs get a trivially-passing report → no deadlock, no bypass.
(The refactor PR itself runs the new always-on job, so no chicken-and-egg.)

## Acceptance
- A docs-only PR shows both required checks as passing (trivially) and merges with no bypass.
- A code PR with a failing suite is blocked from merge.
- `enforce_admins` can then be set true if desired, with bypass no longer needed for any PR.
