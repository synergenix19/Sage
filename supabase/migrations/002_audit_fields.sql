-- supabase/migrations/002_audit_fields.sql
-- Runtime audit trail columns for the messages table.
--
-- model, latency_ms, node_path were applied ad-hoc to the pilot DB and are
-- included here with IF NOT EXISTS so this migration is idempotent on both
-- fresh instances (all 9 columns created) and the live pilot DB (3 skipped).

ALTER TABLE public.messages
  ADD COLUMN IF NOT EXISTS model               text,
  ADD COLUMN IF NOT EXISTS latency_ms          integer,
  ADD COLUMN IF NOT EXISTS node_path           jsonb,
  ADD COLUMN IF NOT EXISTS skill_id            text,
  ADD COLUMN IF NOT EXISTS step_id             text,
  ADD COLUMN IF NOT EXISTS gate_path           text,
  ADD COLUMN IF NOT EXISTS crisis_flags        jsonb,
  ADD COLUMN IF NOT EXISTS clinical_flags      jsonb,
  ADD COLUMN IF NOT EXISTS emotional_intensity integer;
