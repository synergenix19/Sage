-- 012_rbac_backfill.sql
-- Backfill user_roles from the existing is_admin boolean (Doc A §6.2).
-- Must run after 011_rbac_roles.sql.
--
-- Strategy:
--   is_admin = true  → super_admin for bootstrap (reassign to specific staff roles manually)
--   is_admin = false → member
--
-- The tenant UUID is read from the tenants table by name, not hardcoded here,
-- so this migration stays correct if the tenant row is ever re-seeded.
-- The UUID must byte-equal NEXT_PUBLIC_TENANT_ID — confirmed by the P1.3 check after push.

do $$
declare
  v_tenant_id uuid;
begin
  select id into v_tenant_id from public.tenants where name = 'SAGE POC' limit 1;

  if v_tenant_id is null then
    raise exception 'Backfill aborted: no tenant row found with name = ''SAGE POC''. '
      'Run 011_rbac_roles.sql first.';
  end if;

  -- is_admin = true → super_admin (bootstrap; reassign to clinical_reviewer /
  -- operations_admin as a separate manual step before Gitex demo).
  insert into public.user_roles (user_id, tenant_id, role, granted_by, granted_at)
  select id, v_tenant_id, 'super_admin'::public.role_key, id, now()
  from public.user_profiles
  where is_admin = true
  on conflict (user_id, tenant_id, role) do nothing;

  -- is_admin = false → member
  insert into public.user_roles (user_id, tenant_id, role, granted_by, granted_at)
  select id, v_tenant_id, 'member'::public.role_key, id, now()
  from public.user_profiles
  where is_admin = false
  on conflict (user_id, tenant_id, role) do nothing;
end;
$$;

-- ─────────────────────────────────────────────
-- After this migration runs, assign staff roles manually before the Gitex demo.
-- Example — grant clinical_reviewer to a known user UUID:
--
--   INSERT INTO user_roles (user_id, tenant_id, role, granted_by, granted_at)
--   VALUES ('<REVIEWER_UUID>', (SELECT id FROM tenants WHERE name = 'SAGE POC'),
--           'clinical_reviewer', '<SUPER_ADMIN_UUID>', now())
--   ON CONFLICT DO NOTHING;
--
-- Verify least-privilege (Phase 4 step 15):
--   SELECT role, count(*) FROM user_roles GROUP BY role ORDER BY role;
-- Expected: member rows + operations_admin or clinical_reviewer rows.
-- If only super_admin appears, the reassignment step was skipped — fix before demo.
-- ─────────────────────────────────────────────
