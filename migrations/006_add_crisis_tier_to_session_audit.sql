-- Add crisis_tier / tier_rule_id to session_audit (v7.1 crisis tiering).
-- The tier classification (T1 warm / T2 acute / none) and the tier_routing.json rule that
-- resolved it are auditable ONLY when SAGE_CRISIS_TIERING is ON; audit.py writes these columns
-- only when present in state, so a flag-OFF row is unchanged. This migration is a DEPLOY GATE
-- for the flag flip: it MUST run on the target environment (staging, then prod) before
-- SAGE_CRISIS_TIERING is set true there, or the flag-ON audit write fails on unknown columns.
-- Existing rows get NULL (no backfill — historical turns predate tiering).
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS crisis_tier text;
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS tier_rule_id text;
