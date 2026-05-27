-- Migration 002: Add flags_timeline column to clinician_review_queue
-- Date: 2026-05-27
-- Purpose: Maintain chronological record of all clinical flags that triggered review
--          for audit trail and clinician context
-- Related: Clinical Flag Lifecycle Design (docs/superpowers/plans/2026-05-27-clinical-flag-lifecycle-design.md)

ALTER TABLE public.clinician_review_queue
  ADD COLUMN IF NOT EXISTS flags_timeline JSONB DEFAULT '[]'::jsonb;

COMMENT ON COLUMN public.clinician_review_queue.flags_timeline IS
  'Chronological array of clinical flag objects that triggered review escalation. Each entry contains timestamp, flag name, reason, source, and severity. Built via ON CONFLICT DO UPDATE append pattern (jsonb_build_array). Enables clinicians to trace how flags evolved during the session.';
