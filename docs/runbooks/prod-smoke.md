# Prod Smoke Suite — Runbook

The post-deploy health gate for SageAI. Answers **"does what we shipped still work?"** across the accumulated live surface (crisis routing, MM safety hold, precedence, KB source cards, skill-media videos, flags) — distinct from the BOT BEHAVIOUR clinical audit ("does it match the spec?").

## Run it (post-deploy gate)

Immediately AFTER every `railway up` to prod, before announcing the deploy healthy:

```bash
# from a worktree on the deployed tree:
railway run <venv>/python scripts/prod_smoke/run.py --tier all
```

- **Tier A** (safety invariants) + the **Tier C flag-readback** are **must-pass**: a `FAIL` there means **the deploy is NOT healthy** — investigate before announcing. Exit code is `1`.
- **Tier B** (frontend card renders) and the Tier C non-KB chat check are **report-only** in v1 (visible, non-gating).
- `XFAIL` never flips the exit code (see the two known XFAILs below).

Run a single tier with `--tier a|b|c`. Override the target with `--base-url` or `SAGE_SMOKE_BASE_URL` (default: prod).

## Reading the output

Each line: `PASS | FAIL | XFAIL  [tier]  name  (must-pass?)  detail`. Summary at the bottom: `N checks — pass=… fail=… xfail=…`. Exit non-zero iff a **must-pass** check `FAIL`ed.

## Known XFAILs (truthful-by-design, not hidden passes)

1. **`crisis_helpline_number_correct`** — prod crisis copy shows the **wrong helpline** (GL-1, PO-deferred). The check XFAILs against the correct number. **The day GL-1's dial-test fix deploys, this flips to an unexpected-PASS** — that is the signal to fill/confirm `EXPECTED_CORRECT_HELPLINE` in `cases.py` and retire the XFAIL. One action (the dial-test) retires both the placeholder and the wrong-number defect.
   - ⚠️ **Controller step still open:** `cases.py` `DEPLOYED_WRONG_HELPLINE` / `EXPECTED_CORRECT_HELPLINE` are `<controller-fills>` placeholders. Fill them from the live crisis copy + the GL-1 governance note so the XFAIL is *meaningful* (currently it's structurally-XFAIL on the placeholder).

## Tier C flag-readback dependency (do not duplicate)

`tier_c_regression.flag_readback` asserts `SAGE_ROUTE_PRECEDENCE` on / `SAGE_SKILL_MEDIA_ENABLED` on / `SAGE_IPV_PREEMPTION` off. As of 2026-07-07 `/health/ready` returns only `{status, routing_mode}` and does **not** expose these — so the readback returns an honest `FAIL` ("flag not observable"). The `/health/ready` flag exposure is **delivered by make-v2-live Task 1** (the truthful-health task that already owns that endpoint). Until it ships: **keep the flag-readback report-only — do NOT wire the suite as a hard gate on Tier C**, or every deploy will falsely report unhealthy.

## Tier B (frontend) auth setup — one-time

Tier B drives the real frontend, which needs a signed-in staff session. It loads a stored Playwright storage-state, it does not log in itself:

```bash
export SAGE_SMOKE_STORAGE_STATE=/path/to/staff-auth-state.json   # cookies + localStorage
<venv>/python -m playwright install chromium                     # once
```

Produce the storage-state via the **cdai Playwright auth harness** (it owns login + the storageState invariant — do not re-implement auth here). Without the file, Tier B returns one report-only `FAIL` "no storage state — cannot auth" and skips (never a fake pass). All five Tier B behaviours were validated live against prod 2026-07-07 (KB source card, skill-media video, persistence-on-reopen, pre-feature no-card-no-crash, Arabic RTL card).

## Wiring to deploy (the point of this suite)

"The app responds" is not health for this product; "the crisis route fires with correct resources" is. So: **the smoke run is part of the deploy, not the calendar.** After `railway up`, run the suite; treat a must-pass `FAIL` as a failed deploy. This pairs with the CI-on-PR task — CI catches breakage before merge, the smoke suite catches it after deploy. Zero-user mode makes prod the right place to run it (no user is disturbed by test traffic).
