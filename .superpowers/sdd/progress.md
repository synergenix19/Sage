Task 1: dispatched (runner + Tier C)
Task 1: complete (commit 74989a9, runner+TierC, 5 unit tests, /health/ready flag-gap found)
Task 2: complete (Tier A safety, 10 unit tests, helpline placeholders + live-verify pending)

--- HANDOFF NOTES for fresh session (resume off origin/feat/prod-smoke-suite) ---
- Tasks 1-2 DONE (commits 74989a9, 206f493). 10 unit tests green. Plan committed.
- REMAINING: Task 3 (Tier B Playwright), Task 4 (post-deploy wiring + runbook), live-prod fill.
- CONTROLLER live steps pending: fill cases.py helpline placeholders (DEPLOYED_WRONG_HELPLINE / EXPECTED_CORRECT_HELPLINE) from live prod crisis copy + GL-1 note; run `railway run python scripts/prod_smoke/run.py --tier a` + `--tier c` against prod.
- KNOWN CAVEAT: tier_c flag_readback is currently must_pass=True but /health/ready does NOT expose the 3 flags yet -> it FAILs -> --tier c exits 1. Either (a) wait for make-v2-live Task 1 to ship the /health/ready flag field, or (b) make flag_readback report-only (must_pass=False) interim. Plan documents this dependency. Do NOT wire the suite as a hard gate until resolved.
Task 3: complete (Tier B Playwright — 5 checks encoded from LIVE prod validation 2026-07-07, all 5 PASSed live; report-only, storageState auth). 
Task 4: complete (docs/runbooks/prod-smoke.md — post-deploy gate wiring, XFAIL/dependency/auth notes).
LIVE-VALIDATED THIS SESSION (Playwright vs prod): KB source card (3 links, capped), skill-media video card (box breathing/CHI), persistence-on-reopen, pre-feature no-card-no-crash, Arabic RTL card (legible Arabic title, dir=rtl, screenshot).
STILL PENDING (controller/setup): fill cases.py helpline digits; produce SAGE_SMOKE_STORAGE_STATE via cdai auth harness for AUTOMATED tier B; resolve tier_c must_pass vs /health/ready gap (make-v2-live Task 1).
