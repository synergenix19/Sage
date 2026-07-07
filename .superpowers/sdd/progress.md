Task 1: dispatched (runner + Tier C)
Task 1: complete (commit 74989a9, runner+TierC, 5 unit tests, /health/ready flag-gap found)
Task 2: complete (Tier A safety, 10 unit tests, helpline placeholders + live-verify pending)

--- HANDOFF NOTES for fresh session (resume off origin/feat/prod-smoke-suite) ---
- Tasks 1-2 DONE (commits 74989a9, 206f493). 10 unit tests green. Plan committed.
- REMAINING: Task 3 (Tier B Playwright), Task 4 (post-deploy wiring + runbook), live-prod fill.
- CONTROLLER live steps pending: fill cases.py helpline placeholders (DEPLOYED_WRONG_HELPLINE / EXPECTED_CORRECT_HELPLINE) from live prod crisis copy + GL-1 note; run `railway run python scripts/prod_smoke/run.py --tier a` + `--tier c` against prod.
- KNOWN CAVEAT: tier_c flag_readback is currently must_pass=True but /health/ready does NOT expose the 3 flags yet -> it FAILs -> --tier c exits 1. Either (a) wait for make-v2-live Task 1 to ship the /health/ready flag field, or (b) make flag_readback report-only (must_pass=False) interim. Plan documents this dependency. Do NOT wire the suite as a hard gate until resolved.
