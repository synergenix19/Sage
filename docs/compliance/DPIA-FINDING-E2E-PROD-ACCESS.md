# DPIA Finding: E2E Test Identity Writing to Production Clinical Tables

**Finding date:** 2026-05-30  
**Severity:** High — reportable-class under PDPL  
**Status:** Partially mitigated (immediate fix applied); structural fix pending migration  
**Owner:** Rohan Sarda  
**DPIA track:** Must be captured in the DPIA before user-facing production deploy

---

## What Was Found

The E2E test suite (`sage-e2e@test.internal`) seeds and writes to the same Supabase
project as production clinical data. There is no separate test project or branch.
Specifically:

1. **Same `auth.users` table.** The test identity is a real Supabase auth user in the
   production project. Synthetic test identities coexist with real user accounts in
   the same authentication namespace.

2. **Same clinical tables.** `global-setup.ts` inserts rows into `user_profiles`,
   `chat_sessions`, and `messages` on every test run. These are the same tables that
   hold real user mental health conversations.

3. **`is_admin: true` in the seed granted cross-user clinical data access.**
   Three RLS policies check `user_profiles.is_admin` rather than the RBAC system:
   - `session_audit` — "admin_read": SELECT on all users' turn-by-turn audit rows
     (node_path, primary_intent, crisis_state, clinical_flags, emotional_intensity,
     user_id, session_id)
   - `clinician_review_queue` — SELECT on all clinical flag reviews across all users
   - `message_feedback` — SELECT on all feedback across all users

   The seed's `is_admin: true` upsert bypasses the `sync_is_admin` trigger (which
   fires on `user_roles` changes, not `user_profiles` updates), so the E2E user held
   `is_admin = true` in `user_profiles` without a corresponding `user_roles` entry.
   The middleware's 403 check uses `v_user_roles_for_tenant` — the two systems were
   inconsistent, and the RLS layer used the more permissive one.

4. **Containment for `chat_sessions` and `messages` was tight.** The "own sessions"
   and "own messages" policies correctly restrict these to `auth.uid() = user_id`.
   The exposure was on the clinical monitoring overlay tables, not the core conversation
   tables.

---

## Processing Activity Description (for DPIA)

| Attribute | Value |
|---|---|
| Processing activity | Automated E2E test execution |
| Data subjects | All clinical users whose session_audit and clinician_review_queue rows existed |
| Personal data categories | Pseudonymised (user_id), mental health indicators (crisis_state, clinical_flags, emotional_intensity), behavioural (node_path, primary_intent) |
| Legal basis | Not established for synthetic test access to real clinical data |
| Cross-border transfer | n/a — Supabase UAE region (AWS ap-south-1) |
| Retention | Synthetic data per-run cleanup; real clinical rows unaffected |
| Sovereignty constraint | DESC/NCA controls require data residency and access logging; test automation accessing UAE-resident clinical data without a DPIA entry violates the control baseline |

---

## Actions Taken

**Immediate (2026-05-30):**
- `global-setup.ts` changed to seed `is_admin: false`. This closes the RLS gap
  immediately — the E2E identity no longer holds admin privileges in `user_profiles`.
- Confirmed STATE-1 Playwright test uses `v_user_roles_for_tenant` (not `is_admin`)
  for the 403 assertion; no E2E test breaks from this change.

**Pending migration (`013_rls_rbac_migration.sql`):**
- Three RLS policies on `session_audit`, `clinician_review_queue`, and
  `message_feedback` rewritten to use `user_roles` (non-member role check) instead
  of `user_profiles.is_admin`. Apply before Gitex demo.
- After migration, `is_admin: false` in the seed is defence-in-depth; the structural
  fix is the RBAC-based policies.

**Deferred (post-Gitex):**
- Stand up a separate Supabase branch or project for E2E. Synthetic identities should
  not transit production `auth.users`. This is tolerable for Gitex POC if RLS is
  proven tight after migration 013 applies.
- Drop `is_admin` column and `sync_is_admin` trigger from `user_profiles` once all
  remaining application references are removed (migration 014).
- E2E identity scoped to `member` role in `user_roles` (no admin grant anywhere).
- Confirm `super_admin` on `rohansarda@gmail.com` migrated to managed `@cdai.ae`
  identity; personal Gmail retired from privileged access.
- `sage@cdai.ae` sealed properly: direct login disabled, auth hook wired to alert
  on any login event, break-glass procedure documented.

---

## Residual Risk After Immediate Fix

After `is_admin: false` in the seed:
- E2E identity is a regular `member` in `user_profiles`
- RLS "admin_read" policies on clinical monitoring tables will not grant access
  (E2E user fails the `is_admin = true` check)
- Residual: `auth.users` still contains synthetic identities; `chat_sessions`/
  `messages` still receive synthetic rows on each run; RLS policies still gate on
  the legacy `is_admin` field rather than `user_roles`

After migration 013:
- RLS policies use canonical `user_roles` — no path for a `user_profiles` upsert
  to grant clinical data access
- Residual: shared `auth.users` (separate project removes this)

---

## DPIA Disposition

This finding must be documented in the DPIA as a processing activity that occurred
without a DPIA entry: automated test execution with cross-user clinical data access
via a production database. The DPO must sign off on the residual risk posture
(shared-DB, RLS containment) before user-facing production deploy under PDPL.

The finding does not gate Gitex demo (limited users, controlled environment) if:
1. Migration 013 is applied before the demo.
2. The demo uses a confirmed-non-clinical seed dataset.
3. This document is on file and the DPO is aware.

It does gate any broader production rollout.
