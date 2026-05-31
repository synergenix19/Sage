-- 013_rls_rbac_migration.sql
-- Replace is_admin-gated RLS policies with capability-based RBAC policies.
-- Must run after 011_rbac_roles.sql (creates user_roles, v_user_roles_for_tenant).
--
-- Background: 003_complete_trace_fields.sql, 006_clinician_review_queue.sql, and
-- 009_session_audit.sql defined admin-read policies that check user_profiles.is_admin.
-- The initial migration draft used `role <> 'member'` — too broad, grants operations_admin
-- access to clinical monitoring tables. The persona split requires:
--   - session_audit, clinician_review_queue: clinical roles only
--     (clinical_reviewer, clinical_approver, super_admin)
--   - message_feedback: clinical roles only (individual feedback is clinical data)
-- operations_admin has admin:read + analytics:read — population aggregates, not
-- individual clinical session data. The frontend routes ops away from /live; RLS
-- enforces the same boundary at the data layer.
--
-- This migration:
--   1. Drops both the old is_admin-gated policies AND any partial 'staff_read' policies
--      created during a failed earlier run.
--   2. Replaces them with clinical-role-only policies.
--   3. Does NOT drop the is_admin column or sync_is_admin trigger — those removals
--      happen in 014_drop_is_admin.sql after all remaining is_admin references are
--      confirmed dead in application code.

-- ⚠️  COUPLING: The role list below ('clinical_reviewer', 'clinical_approver', 'super_admin')
-- is a second expression of the clinical-data access rule. The first expression is the
-- PERMISSIONS map in apps/web/lib/auth/edge-permissions.ts — roles with flags:read or
-- live:read are the roles that legitimately need clinical session data.
-- These two must stay in sync:
--   - If a role gains flags:read or live:read in edge-permissions.ts, add it here.
--   - If a role is added here, verify it holds flags:read or live:read in the map.
-- Drift between them means RLS and the frontend make different access decisions.
--
-- Roles that may read clinical monitoring data:
--   clinical_reviewer  — monitors live sessions (live:read, flags:read)
--   clinical_approver  — reviews and countersigns flags (flags:read, review:action)
--   super_admin        — break-glass wildcard
-- Roles explicitly excluded from clinical table access:
--   operations_admin   — population analytics only; must not see individual session data
--   clinician_author   — drafts skills/KB; no access to patient session records
--   dpo                — audit log + data requests; not individual session monitoring
--   member             — end users

-- ─────────────────────────────────────────────
-- 1. session_audit — clinical roles only
-- ─────────────────────────────────────────────
drop policy if exists "admin_read" on public.session_audit;
drop policy if exists "staff_read" on public.session_audit;

create policy "clinical_read" on public.session_audit
  for select
  using (
    exists (
      select 1
      from public.user_roles ur
      where ur.user_id = auth.uid()
        and ur.tenant_id = (
          select id from public.tenants where name = 'SAGE POC' limit 1
        )
        and ur.role in ('clinical_reviewer', 'clinical_approver', 'super_admin')
    )
  );

-- ─────────────────────────────────────────────
-- 2. clinician_review_queue — clinical roles only
-- ─────────────────────────────────────────────
drop policy if exists "admin read review queue" on public.clinician_review_queue;
drop policy if exists "staff_read_review_queue" on public.clinician_review_queue;

create policy "clinical_read_review_queue" on public.clinician_review_queue
  for select
  using (
    exists (
      select 1
      from public.user_roles ur
      where ur.user_id = auth.uid()
        and ur.tenant_id = (
          select id from public.tenants where name = 'SAGE POC' limit 1
        )
        and ur.role in ('clinical_reviewer', 'clinical_approver', 'super_admin')
    )
  );

-- ─────────────────────────────────────────────
-- 3. message_feedback — clinical roles only
--    Individual message feedback is clinical data (linked to user sessions).
--    Population-level analytics (count/aggregates) can be derived server-side
--    without granting operations_admin raw row access.
-- ─────────────────────────────────────────────
drop policy if exists "admin read feedback" on public.message_feedback;
drop policy if exists "staff_read_feedback" on public.message_feedback;

create policy "clinical_read_feedback" on public.message_feedback
  for select
  using (
    exists (
      select 1
      from public.user_roles ur
      where ur.user_id = auth.uid()
        and ur.tenant_id = (
          select id from public.tenants where name = 'SAGE POC' limit 1
        )
        and ur.role in ('clinical_reviewer', 'clinical_approver', 'super_admin')
    )
  );

-- ─────────────────────────────────────────────
-- Verification queries (run after applying):
--
-- 1. Confirm policy names — no is_admin references:
--   SELECT tablename, policyname, qual
--   FROM pg_policies
--   WHERE tablename IN ('session_audit', 'clinician_review_queue', 'message_feedback')
--   ORDER BY tablename, policyname;
--
-- 2. Confirm operations_admin gets zero rows (the persona split test):
--   -- Run as e2e-ops@test.internal:
--   SELECT count(*) FROM session_audit;          -- must return 0
--   SELECT count(*) FROM clinician_review_queue; -- must return 0
--   SELECT count(*) FROM message_feedback;       -- must return 0
--
-- 3. Confirm clinical_reviewer gets rows (read access preserved):
--   -- Run as e2e-reviewer@test.internal:
--   SELECT count(*) FROM session_audit;          -- > 0 if sessions exist
-- ─────────────────────────────────────────────
