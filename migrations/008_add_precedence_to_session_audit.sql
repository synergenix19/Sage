-- Add fired_safety_routes / precedence_winner to session_audit (B0 §4.5 route precedence).
-- audit.py writes these columns ONLY when SAGE_ROUTE_PRECEDENCE is ON and a safety route fired,
-- so a flag-OFF (or no-safety) row is byte-identical to today. This migration is a DEPLOY GATE for
-- the flag flip: it MUST run on the target environment (staging, then prod) before
-- SAGE_ROUTE_PRECEDENCE is set true there, or the flag-ON audit write fails on unknown columns
-- (CRITICAL AUDIT FAILURE in _write_session_audit_row). Existing rows get NULL (no backfill —
-- historical turns predate precedence).
--   fired_safety_routes: EVERY safety route that fired the turn (crisis/medical/hr/ipv), recorded
--                        even when precedence suppressed the lower ones (§4.5 never-dropped).
--   precedence_winner:   the highest-precedence route that won the turn's routing.
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS fired_safety_routes text[];
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS precedence_winner text;
