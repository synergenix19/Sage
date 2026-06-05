-- 015_safety_tier_active.sql
-- Add safety_tier_active to session_audit so degraded-mode runs are visible
-- in the audit trail rather than inferred from the absence of a warning log.
--
-- Values: 'S1+S3' (both layers active) | 'S1_only' (S3 timed out or failed).
-- Set by safety_check_node on every turn; written by audit.write_session_audit.
-- NULL means the row was written before this migration (pre-2026-06-01 turns).
--
-- S2 (MARBERT) is not yet implemented; when added it extends the value to 'S1+S2+S3'.

alter table public.session_audit
  add column if not exists safety_tier_active text;
