-- 010_rls_shadow_register_eval.sql
-- Restricted clinical-text table (shadow_arabic_text). Service-role only.
-- ENABLE+FORCE so the owner role is not exempt; REVOKE so no future policy can
-- silently re-open client access.
--
-- Background: migration 009 created shadow_register_eval with no RLS at all.
-- Supabase grants default table privileges (SELECT/INSERT/UPDATE/DELETE) to
-- anon and authenticated on every new public-schema table unless revoked, and
-- PostgREST executes client requests as one of those two roles. Without RLS,
-- shadow_register_eval — which stores shadow_arabic_text, a clinical response
-- text field in the same restricted-retention class as
-- identity_substitution_audit.original_response_text — was reachable by any
-- anon/authenticated client through the standard REST endpoint
-- (/rest/v1/shadow_register_eval). This migration closes that gap:
--   - ENABLE ROW LEVEL SECURITY turns on the default-deny behaviour for all
--     non-bypassrls roles (anon, authenticated included) — with zero policies
--     defined, every client request is denied.
--   - FORCE ROW LEVEL SECURITY additionally applies RLS to the table owner,
--     so a future ownership or grant change cannot silently exempt a role
--     from the RLS boundary.
--   - REVOKE ALL FROM anon, authenticated removes the default privilege grant
--     outright, so even if a future migration adds a permissive policy by
--     mistake, there is no underlying grant for PostgREST's anon/authenticated
--     roles to exercise it against.
-- The service role (used by src/sage_poc/audit.py's _supabase_insert /
-- shadow_eval.write_shadow_eval_row) bypasses RLS entirely and is unaffected —
-- writes from the backend continue to work unchanged.

ALTER TABLE shadow_register_eval ENABLE ROW LEVEL SECURITY;
ALTER TABLE shadow_register_eval FORCE ROW LEVEL SECURITY;
REVOKE ALL ON shadow_register_eval FROM anon, authenticated;
