# Pilot Deploy Readiness — V1 to production — **DEPLOYED**

**Date:** 2026-06-23
**Status: DEPLOYED + crisis-smoke-verified 2026-06-23.** Pilot is **supervised-go**.
**Deploy target:** `master` = **pure V1** (`SKILL_ROUTING_V2` not merged → routing-regression risk structurally zero, not flag-gated).

---

## Deploy result
- **Deployment `2902c05d` — SUCCESS** (Railway `sage-api`/production) via `railway up` from a clean throwaway master worktree. Zero downtime (old release served until new passed `/health/ready`).
- Health: `/health/ready` + `/docs` + `/openapi.json` = **200**. BGE-M3 + S3 crisis index warmed before ready.
- Prod URL: `sage-api-production-3328.up.railway.app`.
- Carries integrated master (V1 routing + concurrent merges: knowledge-ingestion #36, L4 formatting, X-Sage-Direction RTL, output_gate T6, session_audit latency_ms #49).

## Crisis-path smoke — PASSED (smoke-verified, NOT exhaustively tested)
One synthetic explicit-SI phrase → node path `[safety_check, crisis_response]`, `X-Sage-Skill-Id` empty (no skill routed), crisis_flags `[si_explicit, s3_semantic]`, body `[[CRISIS_DETECTED]]` + UAE MoHAP 800 46342 + 999. **Proves the path fires once on a clear phrase — NOT recall/robustness.** "Smoke passed" ≠ "crisis detection validated."

## Gate dispositions (all closed for POC)
| Gate | Status |
|---|---|
| SAGE_API_KEY / CORS / warmup / CRQ guard | ✅ cleared (file:line evidence in deploy turn) |
| pool characterization | 🟡 accepted-for-pilot, hard revisit trigger (concurrency >~10 or cohort expansion → load test; true ceiling unknown) |
| browser QA | ✅ approved (backend-only deploy; frontend/crisis-UX unchanged) |
| crisis risk-acceptance (external users on NO-GO posture) | ✅ approved for POC |

## SUPERVISED-GO condition (load-bearing, not a footnote)
Crisis path is live + functional but **NOT recall-validated** (~38% CRADLE vs ≥95% target → ~6/10 crises may not trip the protocol). **The pilot must run under human-in-the-loop / escalation supervision — the crisis path is NOT a safety net.** "Deploy clean" = infra/gate level only.

## Known pre-pilot reopenings (signed ≠ closed-for-all-time)
1. **#4 mis-route bar** is signed for the **POC arm** (≤4.6%@N≈65); the ≤1%/~300 bar is deferred to pre-pilot → the ar/id_oos eval cell may re-size 4–5× when graduating toward pilot.
2. **Crisis recall** (S2/MARBERT unbuilt, ~38%) must be raised before unsupervised exposure.

## Routing improvement (V2) — NOT shipped, by design
V2 (exemplar embedding) measured to REGRESS (gap-collapse probe); flag stays off, code not on master. The real improvement = §2/§3 calibration + retrieval-core, measured through the §1 harness on held-out eval; ships only when it beats V1 on gate-6 per-stratum (Khaleeji on own calibration). Fixture-green ≠ gate-6 pass.

## Deploy process invariant (added 2026-06-24 after a stale-base incident)
**Always `git fetch` and branch/deploy off freshly-fetched `origin/master` — NEVER a local `master` ref.**
Incident: a SK-AR-006 safety deploy was built from a stale local `master` (362eff2) that was ~2h behind `origin/master` (78644d6, PR #41). The deploy silently **rolled back PR #41** in prod (a real-user-RCA routing fix) because the deploy base did not contain it. `railway up` carries no git SHA, so the regression was invisible until reconstructed from `git reflog`.
Rules:
1. Before any `railway up`: `git fetch origin master` and build from `origin/master` (or a branch freshly based on it), not a local ref.
2. Verify the deploy delta against **current prod**, computed from `origin/master`, not a stale local pointer.
3. Reconcile prod to a known commit; treat "what's actually in prod" as a fact to verify (reflog/CI), never assume — `railway up` deploys leave no SHA to recover later.

## SCHEDULED structural hardening — do at the next coast-clear window (no active concurrent session)
**Why now (not "someday"):** the 2026-06-24 incident is the argument. A crisis-rule deploy silently rolled back a confirmed break-fix (#41), and recovering *what shipped* required `git reflog` timestamp forensics because the deploy tooling is SHA-blind. The written "fetch origin/master" invariant (above) is load-bearing human vigilance — the same kind that held explicit-pathspec for collisions #1–5; it works until the once it doesn't, and this was that once. The two fixes below make the invariant **unnecessary**, not remembered.

**Trigger:** next coast-clear moment (no concurrent session), because the worktree install mutates the shared checkout (can't free an already-checked-out branch mid-session). Do not attempt while parallel sessions are active.

1. **Worktree-per-session (install, not aspiration).** Every working session operates in its own `git worktree add ../sage-poc-<branch> <branch>`, never the shared main checkout. This removes the shared-ref hazard that produced the stale local `master`. Project already uses `.worktrees/` for some branches — make it the rule for all sessions, including the command session.
2. **Deploy carries its source SHA (kill the SHA-blindness).** `railway up` records no commit, so prod's deployed SHA is unreadable after the fact. Fix: a thin deploy wrapper that stamps `git rev-parse HEAD` into a `BUILD_SHA` file (or build ARG) before `railway up`; the app reads it and exposes it (e.g. `/version` endpoint or an `x-sage-build` header). Then "what's in prod" is a one-line read, not reflog archaeology — and a stale-base deploy is visible immediately, not hours later.

Owner: engineering. Status: **scheduled, next coast-clear window.** Until done, the "fetch origin/master before deploy" invariant (above) stands as the interim guard.
