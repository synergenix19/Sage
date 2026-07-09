-- PDPL Art. 6 right-to-challenge backing store for identity-substitution audit.
-- Restricted clinical text (original_response_text) — service-role only, per the standing
-- RLS-in-creation-migration convention (docs/ARCHITECTURE_BOUNDARIES.md). See the audit-trail
-- incident: the write path (audit.py write_identity_substitution_audit) has had no table since
-- 2026-05-27 (ade88cb). Columns match that writer's row dict exactly.
CREATE TABLE IF NOT EXISTS identity_substitution_audit (
  id                       bigint generated always as identity primary key,
  session_id               text,
  turn_number              integer,
  rule_id                  text,
  original_response_hash   text,
  original_response_text   text,
  substitute_with          text,
  user_id                  text,
  created_at               timestamptz default now()
);
ALTER TABLE identity_substitution_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity_substitution_audit FORCE ROW LEVEL SECURITY;
REVOKE ALL ON identity_substitution_audit FROM anon, authenticated;
