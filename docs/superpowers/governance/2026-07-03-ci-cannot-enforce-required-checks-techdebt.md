# Tech Debt — CI cannot enforce required status checks (standing governance hole)

**Filed:** 2026-07-03 (surfaced by PR #85 crisis-tiering). **Severity:** governance/safety-process. **Owner:** _repo admin / eng lead (assign)_.

## The hole
This is a **safety-critical** repo (crisis detection/routing lives here), yet its CI **cannot act as a merge gate**: checks are **advisory-not-hard**, and the path-filtered checks **deadlock non-code PRs** (the "guard-job" issue, previously ticketed). Consequence: nothing technically prevents a merge with a red safety-surface gate, a red flag-OFF anchor test, or without the per-case recall regression having run.

## Current stopgap (PR #85)
The tiering merge gate is enforced **procedurally**: the reviewer must be shown a **green per-case regression run on the exact tip SHA** before merging (recorded in the PR). This works for one PR but does not scale and relies on human diligence.

## Required fix (beyond this PR)
Wire branch protection so the following are **required status checks** on `master` (path rules for `safety_check.py` / `rules/data/tier_routing/` / `graph.py` routing if supported, else repo-wide):
- the safety-surface gate,
- `test_crisis_tiering.py` (incl. the flag-OFF deterministic anchor),
- (trigger-gated) the per-case recall regression on any PR touching the safety/tiering paths.
This depends on first resolving the guard-job deadlock so required checks don't block legitimate non-code PRs.

Until then, every safety-path PR carries the same procedural stopgap — a standing risk, not a one-off.
