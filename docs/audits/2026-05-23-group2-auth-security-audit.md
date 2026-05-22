# Group 2: Post-Implementation Audit Results

**Date:** 2026-05-23
**Auditor:** Claude (automated)
**Repos:**
- sage-poc @ `f7a4f90df88bfa721e0f2ccb3412420e128da147`
- cdai @ `8018630025b4cf5523d6c6049c9d978ac7c83100`

---

## Summary

| Metric | Count |
|--------|-------|
| PASS | 56 |
| FAIL | 0 |
| NOTE (informational) | 3 |

**Overall verdict: APPROVED**

All Group 2 auth & API security tasks (FE-C1, FE-C2, FE-C3, FE-C4×2, FE-C7, FE-H1, FE-H5) are correctly implemented. Defense-in-depth is in place, ferry interop is preserved, and all regression tests pass.

Test totals: sage-poc 772 passed; cdai Group 2 files 37/37 passed.

---

## Phase 0: Environment

| Check | Status | Detail |
|-------|--------|--------|
| 0.1 sage-poc HEAD commits present | PASS | `f7a4f90` FE-H5 hmac + `97e37dc` FE-H5 key validation |
| 0.1 cdai HEAD commits present | PASS | All expected Group 2 commits present (FE-C1, C2, C3, C4, C7, H1, H5) |
| 0.2 sage-poc full suite | PASS | 772 passed, 15 warnings |
| 0.2 cdai apps/web full suite | PASS | 17 test files passed, 91 tests passed |
| 0.3 sage-poc git clean | PASS | Working tree clean |
| 0.3 cdai git clean | NOTE | Untracked `docs/superpowers/plans/2026-05-22-group2-auth-security.md` — plan doc, not a code change |

---

## Phase 1: Static Code Review

### 1.1 FE-C1 — Auth check at /api/chat

| Item | Status | Detail |
|------|--------|--------|
| 1.1.1 Auth check FIRST meaningful op | PASS | route.ts:58–60 — before classifyIntent, any DB write, sage fetch |
| 1.1.2 `getUser()` not `getSession()` | PASS | route.ts:59; no `getSession` in file |
| 1.1.3 Guard checks `authError \|\| !user` | PASS | route.ts:60 |
| 1.1.4 Status `401` | PASS | route.ts:60 |
| 1.1.5 Test coverage | PASS | Tests: 401-no-user, 401-auth-error, no-sage-call, no-insert |

### 1.2 FE-C4 — Session ownership at /api/chat

| Item | Status | Detail |
|------|--------|--------|
| 1.2.1 Ownership AFTER auth, BEFORE insert | PASS | route.ts:62–68; auth at line 60, insert at line 73 |
| 1.2.2 Double `.eq()` — id AND user_id | PASS | route.ts:65–66 |
| 1.2.3 `.select('id')` minimal | PASS | route.ts:64 |
| 1.2.4 Status `403` | PASS | route.ts:68 |
| 1.2.5 `user.id` from server-verified token | PASS | Destructured from `getUser()` at line 59 |
| 1.2.6 403 and proceed test coverage | PASS | route.test.ts:299–337 |
| 1.2.7 Execution order | NOTE | Ownership check runs BEFORE `classifyIntent` — more secure than audit plan stated (rejects unauthorized before spending LLM call). Improvement. |

### 1.3 FE-C4 — messageId ownership at /api/feedback

| Item | Status | Detail |
|------|--------|--------|
| 1.3.1 Two-step ownership chain | PASS | feedback/route.ts:21–34 |
| 1.3.2 messages → session_id → chat_sessions w/ user_id | PASS | route.ts:22 then route.ts:29 |
| 1.3.3 404 missing / 403 wrong user (distinct) | PASS | route.ts:26 (404), route.ts:34 (403) |
| 1.3.4 Ownership BEFORE upsert | PASS | Ownership ends line 34; upsert line 36 |
| 1.3.5 `getUser()` not `getSession()` | PASS | feedback/route.ts:15 |
| 1.3.6 Test coverage | PASS | 6/6 tests pass (404, 403, upsert-not-called assertions) |

### 1.4 FE-H5 — Shared secret

| Item | Status | Detail |
|------|--------|--------|
| 1.4.1 `Header` import + param in signature | PASS | server.py:11, 171 |
| 1.4.2 `hmac.compare_digest`, per-request env read, bypass-on-empty | PASS | server.py:172–174 |
| 1.4.3 Key check FIRST in handler | PASS | server.py:172–174 before any other logic |
| 1.4.4 `import os` and `import hmac` | PASS | server.py:5–6 |
| 1.4.5 4 API key tests pass | PASS | missing→401, wrong→401, correct→200, unset→200 |
| 1.4.6 Ferry tests pass with no key | PASS | 6 ferry tests pass (bypass path active) |
| 1.4.7 cdai conditional spread | PASS | route.ts:87 |
| 1.4.8 No `NEXT_PUBLIC_SAGE_API_KEY` | PASS | No matches across codebase |
| 1.4.9 `vi.stubEnv` + `afterEach` cleanup | PASS | route.test.ts:87–88 afterEach; line 341 stubEnv |
| 1.4.10 Ferry gate CI does NOT set SAGE_API_KEY | PASS | Both workflow files: no SAGE_API_KEY entry (bypass path handles CI correctly) |

### 1.5 FE-H1 — getUser() in middleware

| Item | Status | Detail |
|------|--------|--------|
| 1.5.1 `getSession()` absent | PASS | Zero matches in middleware.ts |
| 1.5.2 `getUser()` exactly once | PASS | middleware.ts:23 |
| 1.5.3 `user` destructuring, no `session` refs | PASS | Zero session references in file |
| 1.5.4 Profile query uses `user.id` | PASS | middleware.ts:49 |
| 1.5.5 4 middleware tests pass | PASS | 4/4 |

### 1.6 FE-C2 — Auth callback route

| Item | Status | Detail |
|------|--------|--------|
| 1.6.1 Open-redirect guard: `startsWith('/') && !startsWith('//')` | PASS | callback/route.ts:11 |
| 1.6.2 `exchangeCodeForSession(code)` | PASS | callback/route.ts:28 |
| 1.6.3 Error path → `/sign-in?error=callback-failed` | PASS | callback/route.ts:34 |
| 1.6.4 No-code path → error URL, no exchange | PASS | Falls through `if (code)` block to line 34 |
| 1.6.5 `/auth/callback` in AUTH_PATHS | PASS | middleware.ts:4 |
| 1.6.6 6 callback tests pass | PASS | 6/6 |
| 1.6.7 Cookie `setAll` pattern | PASS | callback/route.ts:21–24 |

### 1.7 FE-C3 — Password reset page

| Item | Status | Detail |
|------|--------|--------|
| 1.7.1 `redirectTo` → `/auth/callback?next=/reset-password` | PASS | forgot-password/page.tsx:17 |
| 1.7.2 `/reset-password` in AUTH_PATHS | PASS | middleware.ts:4 |
| 1.7.3 reset-password page invariants | PASS | `'use client'`(L1), `createClient`(L4), `updateUser({password})`(L18), success→`/chat`(L21), inline error(L42), `minLength={6}`(L39), `required`(L40), `autoComplete="new-password"`(L35) |
| 1.7.4 UI imports resolve | PASS | packages/ui/src/index.ts exports Button and Input |

### 1.8 FE-C7 — StepGuard forward-skip

| Item | Status | Detail |
|------|--------|--------|
| 1.8.1 Backward `Math.min(storedStep, 6)`, forward `Math.max(storedStep, 1)`, `else if` | PASS | step-guard.tsx:11–15 |
| 1.8.2 Floor guard + store initial step=1 | PASS | `Math.max(storedStep, 1)` present; onboarding-store.ts:30 `step: 1`; floor guard handles pre-hydration edge |
| 1.8.3 5 StepGuard tests pass | PASS | 5/5 |

---

## Phase 2: Cross-Task Integration

| Item | Status | Detail |
|------|--------|--------|
| 2.1.1 chat route order | PASS | parse → validate(400) → getUser(401) → ownership(403) → classifyIntent → insert → sage(+key) → stream |
| 2.1.2 feedback route order | PASS | parse → validate(400) → getUser(401) → msg-lookup(404) → ownership(403) → upsert |
| 2.2.1 Final AUTH_PATHS | PASS | `['/sign-in', '/sign-up', '/forgot-password', '/auth/callback', '/reset-password']` |
| 2.2.2 `startsWith` matching (not exact) | PASS | middleware.ts:33, 45 `.some(p => pathname.startsWith(p))` |
| 2.2.3 No AUTH_PATH is dangerous prefix | PASS | None of the 5 paths is a prefix of any protected route |
| 2.3.1 Defense-in-depth: middleware + route both use `getUser()` | PASS | middleware.ts:23 + route.ts:59 + feedback/route.ts:15 |
| 2.4.1 Ferry tests pass (both repos) | PASS | sage-poc 6 ferry tests; cdai route 16/16 |
| 2.4.2 Ferry response headers present | PASS | route.ts:246–250 — all 5 ferry headers set |
| 2.5.1 Error response consistency | PASS | Consistent within each route; JSON only for upstream errors |

---

## Phase 3: Security Tests (unit-verified)

| Item | Status | Test Location |
|------|--------|---------------|
| 3.1 Unauthenticated API rejection (401) | PASS | route.test.ts — 401, no sage call, no insert |
| 3.2 Wrong-session rejection (403) | PASS | route.test.ts + feedback/route.test.ts — 403, upsert not called |
| 3.3 Shared secret rejection (sage-poc) | PASS | test_server.py — missing/wrong→401, correct→200, unset→bypass |
| 3.4 Open redirect blocked (`//evil.com`) | PASS | callback.test.ts — `evil.com` not in location header |
| 3.5 reset-password page + AUTH_PATHS | PASS | Page exists; middleware.ts includes path |
| 3.6 StepGuard forward-skip redirects | PASS | step-guard.test.tsx — storedStep=2, pageStep=5 → `/step-2` |

> **Note on Phase 3.1–3.3 live tests:** Servers not running locally during audit. The curl-based tests from the audit plan (3.1.1–3.3.3) are deferred to staging QA. Unit test coverage above provides equivalent confidence for the code paths.

---

## Phase 4: Regression Sweep

| Item | Status | Detail |
|------|--------|--------|
| 4.1 Full sage-poc suite | PASS | 772 passed, 15 warnings |
| 4.2 cdai Group 2 targeted run | PASS | 5 test files, 37/37 tests |
| 4.3 No `getSession()` in any app route | PASS | Zero matches in `apps/web/app/` |
| 4.4 No `NEXT_PUBLIC_SAGE_API_KEY` | PASS | Zero matches across codebase |

---

## Findings Log

| # | Phase.Check | Status | Detail |
|---|-------------|--------|--------|
| 1 | 0.3 cdai | NOTE | Untracked `docs/superpowers/plans/2026-05-22-group2-auth-security.md` — plan doc only, not a code artifact. Safe to commit or leave. |
| 2 | 1.2.7 / 2.1.1 | NOTE | Ownership check runs BEFORE `classifyIntent` (not after, as audit plan stated). This is a security improvement: unauthorized requests are rejected before incurring an LLM API call. No corrective action needed. |
| 3 | cdai vitest root | NOTE | Running `npx vitest run` from `/cdai` root picks up Playwright `.spec.ts` files (10 parse errors). The correct scope is `apps/web/` (17 files, 91 tests — all pass). Recommend adding `exclude: ['**/playwright/**']` to the root `vitest.config.ts` in a future cleanup task. |

---

## Implementation Upgrades Beyond Spec

Two improvements made during implementation that exceeded the plan spec:

**1. `hmac.compare_digest` for FE-H5 (sage-poc)**
The plan acknowledged constant-time comparison wasn't strictly required for server-to-server traffic on the same network. The implementer used `hmac.compare_digest` anyway. This is the right call — zero cost, removes the timing-attack vector from the threat model entirely.

**2. `Math.max(storedStep, 1)` floor guard for FE-C7 (StepGuard)**
The plan specified `router.replace(\`/step-${storedStep}\`)` without a floor. The implementer added `Math.max(storedStep, 1)`. This addresses audit check 1.8.2 — Zustand initializes `step: 1` but the pre-hydration window where `storedStep = 0` could redirect to `/step-0` (invalid route). The floor guard prevents this.

---

## Post-Merge Actions (remaining)

| # | Action | Owner | Priority |
|---|--------|-------|----------|
| 1 | Set `SAGE_API_KEY` in both production/staging environments (same value; `openssl rand -hex 32`; never `NEXT_PUBLIC_`) | DevOps / deploy | **REQUIRED before prod** |
| 2 | Run browser QA checklist: (a) email confirmation flow, (b) password reset flow, (c) StepGuard forward-skip at `/step-5` from step 2 | QA / dev | Before prod |
| 3 | Enable `"Auth security tests"` as required status check in GitHub branch protection (cdai `main`) — matches the new `auth-gate.yml` job name | Repo admin | Recommended |
| 4 | Confirm CORS origins env var for sage-poc production (`server.py:41` TODO) | Backend | Before prod |
| 5 | Monitor Supabase auth server latency after production deploy — `getUser()` adds a network round-trip per middleware invocation vs the previous cookie-only `getSession()` | Ops | Post-deploy |
| 6 | Add `exclude: ['**/playwright/**']` to root `vitest.config.ts` | Dev | Low priority cleanup |

---

## Audit Completion Criteria

- [x] Phase 0: Both test suites green
- [x] Phase 1: All 8 task audits passed (1.1–1.8)
- [x] Phase 2: Cross-task integration checks passed
- [x] Phase 3: All rejection tests verified (unit-level)
- [x] Phase 4: No regressions; Group 1 ferry intact
- [x] Phase 5: Findings log — 0 FAIL, 3 NOTE (all informational)

**Group 2 is approved.**
