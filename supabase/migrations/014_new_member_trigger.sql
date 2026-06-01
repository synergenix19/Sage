-- 014_new_member_trigger.sql
-- Automatically assign 'member' role when a user_profiles row is first created.
-- Removes reliance on the application-layer fallback in getSessionRoles() as the
-- sole guarantee of access control for new users.
--
-- Trigger fires on INSERT only (not UPDATE) to avoid a circular chain:
--   user_profiles INSERT → user_roles INSERT → trg_sync_is_admin → user_profiles UPDATE
-- Using INSERT-only breaks the cycle at step 3 (UPDATE does not re-fire this trigger).
--
-- SECURITY DEFINER: runs as function owner (bypasses user_roles RLS write restriction).
-- ON CONFLICT DO NOTHING: idempotent — safe to re-run if user_profiles is re-inserted.

create or replace function public.assign_member_role()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_tenant_id uuid;
begin
  select id into v_tenant_id from public.tenants where name = 'SAGE POC' limit 1;
  if v_tenant_id is null then
    return new;
  end if;

  insert into public.user_roles (user_id, tenant_id, role, granted_by, granted_at)
  values (new.id, v_tenant_id, 'member', new.id, now())
  on conflict (user_id, tenant_id, role) do nothing;

  return new;
end;
$$;

drop trigger if exists trg_assign_member_role on public.user_profiles;
create trigger trg_assign_member_role
  after insert on public.user_profiles
  for each row execute function public.assign_member_role();
