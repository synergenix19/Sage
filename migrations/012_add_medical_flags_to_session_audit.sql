-- Add gate_path / medical_flags to session_audit (B1 medical red-flag guard).
-- audit.py writes these columns ONLY when a medical turn actually fired (medical_flags
-- non-empty in state), so a flag-OFF / non-medical row stays byte-identical to master
-- (Check B). This migration is a DEPLOY GATE for the flag flip: it MUST run on the target
-- environment (staging, then prod) before SAGE_MEDICAL_REDFLAG_GUARD is set true there, or
-- the flag-ON audit write fails on unknown columns (CRITICAL AUDIT FAILURE in
-- _write_session_audit_row). Existing rows get NULL (no backfill — historical turns
-- predate the medical red-flag guard).
--   gate_path:      the routing gate that resolved the turn (e.g. "medical"); mirrors the
--                    gate_path already carried elsewhere in state, recorded here so a
--                    medical-terminal row (which bypasses output_gate) is self-describing.
--   medical_flags:  WHICH red-flag phrase(s) fired (e.g. "crushing") — recall measurement,
--                    post-hoc referral review, and the B1-full >=95% gate all depend on
--                    knowing which phrase matched, not just that a medical turn occurred.
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS gate_path text;
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS medical_flags text[];
