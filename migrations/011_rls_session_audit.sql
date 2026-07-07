-- 011_rls_session_audit.sql
-- REMEDIATION — INSERT policy on session_audit lets anon/authenticated write rows.
--
-- session_audit is defined/versioned in the sibling cdai/supabase/migrations/
-- tree (009_session_audit.sql .. 015_safety_tier_active.sql), not in this
-- repo's ledger, but both sage-poc and cdai point at the same Supabase
-- project in dev (jrfrficjdwguqbvumdyo). This file is created here because
-- this audit found the gap from the sage-poc side; do NOT apply without
-- cdai-side sign-off, since this repo does not own that table.
--
-- READ path is fine: 013_rls_rbac_migration.sql (cdai) added a `clinical_read`
-- SELECT policy scoped to clinical_reviewer/clinical_approver/super_admin via
-- user_roles — verified live on jrfrficjdwguqbvumdyo (relrowsecurity=t, the
-- policy's USING clause checks auth.uid() against user_roles). anon and
-- authenticated cannot read rows they aren't entitled to. Do not touch this
-- policy or the SELECT grant — it is how clinical_reviewer/clinical_approver/
-- super_admin (authenticated role + RLS row filter) legitimately read the
-- table, e.g. cdai/apps/web/components/clinical-live/use-session-audit.ts.
--
-- WRITE path is the gap: 010_session_audit_constraints.sql (cdai) added
--   create policy "service_role_insert" on public.session_audit
--     for insert with check (true);
-- with no `TO service_role` clause. Postgres policies with no role list apply
-- to PUBLIC (all roles). Combined with anon/authenticated's standing default
-- INSERT grant (Supabase's default table privileges), this means ANY
-- anon-key or authenticated-JWT client can insert arbitrary rows into
-- session_audit today — verified live: pg_policy shows
-- service_role_insert.polcmd='a' with with_check_expr='true' and no role
-- restriction, and information_schema.role_table_grants shows INSERT granted
-- to both anon and authenticated. This is a write/spoofing exposure (fabricated
-- clinical-audit rows), not a confidentiality breach — but it undermines the
-- integrity of a clinical audit trail. sage-poc's own writer
-- (src/sage_poc/audit.py write_session_audit / _write_session_audit_row) only
-- ever uses SUPABASE_SERVICE_KEY, which bypasses RLS entirely (rolbypassrls=t)
-- and does not need this policy at all — it exists purely for defense in
-- depth per its own comment ("prevents latent failures"), so scoping it to
-- service_role changes nothing for any legitimate writer.

DROP POLICY IF EXISTS "service_role_insert" ON public.session_audit;

CREATE POLICY "service_role_insert" ON public.session_audit
  FOR INSERT
  TO service_role
  WITH CHECK (true);

-- Belt-and-suspenders: remove the standing default INSERT/UPDATE/DELETE grants
-- from anon/authenticated. SELECT is deliberately NOT revoked — the
-- clinical_read RLS policy already correctly scopes SELECT to clinical roles
-- for the authenticated role, and revoking the SELECT grant would break that
-- legitimate read path.
REVOKE INSERT, UPDATE, DELETE ON public.session_audit FROM anon, authenticated;
