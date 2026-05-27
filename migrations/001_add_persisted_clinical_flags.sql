-- Migration 001: Add persisted_clinical_flags column to user_therapeutic_profiles
-- Date: 2026-05-27
-- Purpose: Store persistent clinical flags (substance_use, trauma_indicator, etc.)
--          that inform prompt adaptation across the session
-- Related: Clinical Flag Lifecycle Design (docs/superpowers/plans/2026-05-27-clinical-flag-lifecycle-design.md)

ALTER TABLE public.user_therapeutic_profiles
  ADD COLUMN IF NOT EXISTS persisted_clinical_flags JSONB DEFAULT '[]'::jsonb;

COMMENT ON COLUMN public.user_therapeutic_profiles.persisted_clinical_flags IS
  'Array of clinical flags set during the session. Category A flags (substance_use, trauma_indicator, eating_concern, medication_mention, domestic_situation, third_party_si) that persist for the duration of the session. Informs prompt framing via Rules Service (PI-CF-001 through PI-CF-005). Non-blocking; does not gate skill delivery.';
