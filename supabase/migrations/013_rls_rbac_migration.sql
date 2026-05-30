-- 013_rls_rbac_migration.sql
-- Replace is_admin-gated RLS policies with user_roles-based RBAC policies.
-- Must run after 011_rbac_roles.sql (creates user_roles, v_user_roles_for_tenant).
--
-- Background: 003_complete_trace_fields.sql, 006_clinician_review_queue.sql, and
-- 009_session_audit.sql defined admin-read policies that check user_profiles.is_admin.
-- That field was a bootstrap mechanism; 011_rbac_roles.sql introduced the canonical
-- user_roles table and flagged is_admin for removal post-Gitex.
--
-- The is_admin field must NOT be the access gate for clinical monitoring tables:
-- - Any direct upsert to user_profiles (e.g., an E2E seed) can set is_admin = true,
--   bypassing the sync_is_admin trigger and granting cross-user clinical data access.
-- - The sync_is_admin trigger only fires on INSERT/DELETE to user_roles, not on
--   user_profiles updates, creating a window where is_admin and user_roles diverge.
--
-- This migration:
--   1. Drops the three is_admin-gated policies.
--   2. Replaces them with role-based policies that check user_roles directly.
--      Roles that grant clinical read access: clinical_reviewer, clinical_approver,
--      clinician_author, operations_admin, super_admin (all non-member roles).
--   3. Does NOT drop the is_admin column or sync_is_admin trigger — those removals
--      happen in 014_drop_is_admin.sql after all remaining is_admin references are
--      confirmed dead in application code.

-- ─────────────────────────────────────────────
-- 1. session_audit — replace is_admin read with role-based read
-- ─────────────────────────────────────────────
drop policy if exists "admin_read" on public.session_audit;

create policy "staff_read" on public.session_audit
  for select
  using (
    exists (
      select 1
      from public.user_roles ur
      where ur.user_id = auth.uid()
        and ur.tenant_id = (
          select id from public.tenants where name = 'SAGE POC' limit 1
        )
        and ur.role <> 'member'
    )
  );

-- ─────────────────────────────────────────────
-- 2. clinician_review_queue — replace is_admin read with role-based read
-- ─────────────────────────────────────────────
drop policy if exists "admin read review queue" on public.clinician_review_queue;

create policy "staff_read_review_queue" on public.clinician_review_queue
  for select
  using (
    exists (
      select 1
      from public.user_roles ur
      where ur.user_id = auth.uid()
        and ur.tenant_id = (
          select id from public.tenants where name = 'SAGE POC' limit 1
        )
        and ur.role <> 'member'
    )
  );

-- ─────────────────────────────────────────────
-- 3. message_feedback — replace is_admin read with role-based read
-- ─────────────────────────────────────────────
drop policy if exists "admin read feedback" on public.message_feedback;

create policy "staff_read_feedback" on public.message_feedback
  for select
  using (
    exists (
      select 1
      from public.user_roles ur
      where ur.user_id = auth.uid()
        and ur.tenant_id = (
          select id from public.tenants where name = 'SAGE POC' limit 1
        )
        and ur.role <> 'member'
    )
  );

-- ─────────────────────────────────────────────
-- Verification query (run manually after applying):
-- Expected: no is_admin references in any policy definition on these three tables.
--
--   SELECT tablename, policyname, qual
--   FROM pg_policies
--   WHERE tablename IN ('session_audit', 'clinician_review_queue', 'message_feedback')
--   ORDER BY tablename, policyname;
--
-- Also verify the E2E identity cannot read session_audit after the seed is fixed:
--   SELECT count(*) FROM session_audit;  -- run as sage-e2e@test.internal; must return 0
-- ─────────────────────────────────────────────
