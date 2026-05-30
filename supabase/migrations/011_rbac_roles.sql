-- 011_rbac_roles.sql
-- Capability-based RBAC: role_key enum, user_roles table, RLS, view, backward-compat trigger.
-- Doc A: 2026-05-30-frontend-rbac-schema-spec.md

-- ─────────────────────────────────────────────
-- 0. Minimal tenants table (Gitex POC: single tenant)
--    tenant_id is carried on user_roles for multi-tenant readiness.
--    Full tenant provisioning model is out of scope for this migration.
-- ─────────────────────────────────────────────
create table if not exists public.tenants (
  id         uuid primary key default gen_random_uuid(),
  name       text not null,
  created_at timestamptz not null default now()
);
alter table public.tenants enable row level security;
create policy "service_role_only" on public.tenants
  for all to service_role using (true) with check (true);

-- Authenticated users may read tenant metadata (needed for tenant name display).
-- The tenant UUID itself is injected via NEXT_PUBLIC_TENANT_ID env var for middleware;
-- this policy allows UI components to resolve tenant display names.
create policy "tenants_authenticated_read" on public.tenants
  for select to authenticated using (true);

-- ─────────────────────────────────────────────
-- 1. role_key enum
--    Closed set — ALTER TYPE ... ADD VALUE requires a reviewed migration.
--    Order: end users first, staff/clinical middle, platform last.
-- ─────────────────────────────────────────────
create type public.role_key as enum (
  'member',
  'clinical_reviewer',
  'clinician_author',
  'clinical_approver',
  'operations_admin',
  'dpo',
  'super_admin'
);

-- ─────────────────────────────────────────────
-- 2. user_roles table
-- ─────────────────────────────────────────────
create table if not exists public.user_roles (
  user_id    uuid        not null references public.user_profiles(id) on delete cascade,
  tenant_id  uuid        not null references public.tenants(id)       on delete cascade,
  role       public.role_key not null,
  granted_by uuid                 references public.user_profiles(id) on delete set null,
  granted_at timestamptz not null default now(),

  primary key (user_id, tenant_id, role)
);

-- ─────────────────────────────────────────────
-- 3. Indexes
-- ─────────────────────────────────────────────
create index if not exists idx_user_roles_user_tenant on public.user_roles (user_id, tenant_id);
create index if not exists idx_user_roles_granted_by  on public.user_roles (granted_by);
create index if not exists idx_user_roles_tenant_role on public.user_roles (tenant_id, role);

-- ─────────────────────────────────────────────
-- 4. Row-level security
-- ─────────────────────────────────────────────
alter table public.user_roles enable row level security;

-- Users may read their own roles only
create policy "user_roles_self_read" on public.user_roles
  for select to authenticated
  using (user_id = auth.uid());

-- Writes via service-role client only
create policy "user_roles_service_write" on public.user_roles
  for all to service_role
  using (true) with check (true);

-- ─────────────────────────────────────────────
-- 5. Roles view — security_invoker ensures RLS on user_roles applies to the caller.
--    Without security_invoker = true (PG 15+), the view definer's rights are used
--    and the user_roles_self_read policy is bypassed, allowing cross-user role reads.
--    If on PG 14, use the get_my_roles() function fallback below instead.
-- ─────────────────────────────────────────────

-- Guard: security_invoker = true on views requires PostgreSQL 15+.
-- On PG 14, this option is rejected, leaving the migration in a partial state.
-- On PG 15+, it enforces RLS on user_roles with the caller's identity,
-- preventing cross-user role enumeration via the view.
do $$
begin
  if current_setting('server_version_num')::int < 150000 then
    raise exception 'Migration 011 requires PostgreSQL 15+ for security_invoker view support. Supabase new projects ship PG 15+. Check: SELECT version();';
  end if;
end;
$$;

create or replace view public.v_user_roles_for_tenant
  with (security_invoker = true)
as
select
  user_id,
  tenant_id,
  coalesce(array_agg(role order by role), ARRAY[]::public.role_key[]) as roles
from public.user_roles
group by user_id, tenant_id;

-- PG 14 fallback function (SECURITY INVOKER by default for SQL functions).
-- If the project is on PG 14, call rpc('get_my_roles', { p_tenant_id: tenantId })
-- from middleware instead of querying the view.
create or replace function public.get_my_roles(p_tenant_id uuid)
returns public.role_key[]
language sql
security invoker
stable
set search_path = public
as $$
  select coalesce(array_agg(role order by role), ARRAY[]::public.role_key[])
  from public.user_roles
  where user_id = auth.uid() and tenant_id = p_tenant_id
$$;

-- ─────────────────────────────────────────────
-- 6. Backward-compatibility trigger
--    Keeps user_profiles.is_admin = true iff the user holds any non-member role
--    in ANY tenant. Allows existing code to function during the cutover window.
--    Drop this trigger and the is_admin column post-Gitex once all references are removed.
-- ─────────────────────────────────────────────
create or replace function public.sync_is_admin()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  update public.user_profiles
  set is_admin = exists (
    select 1 from public.user_roles
    where user_id = coalesce(new.user_id, old.user_id)
      and role <> 'member'
  )
  where id = coalesce(new.user_id, old.user_id);
  return coalesce(new, old);
end;
$$;

drop trigger if exists trg_sync_is_admin on public.user_roles;
create trigger trg_sync_is_admin
  after insert or delete on public.user_roles
  for each row execute function public.sync_is_admin();

-- ─────────────────────────────────────────────
-- 7. action_log audit columns (deferred)
--    Doc A §7.1 specifies adding authorized_by_capability and actor_roles to action_log.
--    The action_log table does not exist in this codebase yet.
--    These columns must be added in the migration that creates action_log.
--    When that migration is written, add:
--      ALTER TABLE action_log ADD COLUMN authorized_by_capability text;
--      ALTER TABLE action_log ADD COLUMN actor_roles role_key[];
-- ─────────────────────────────────────────────
