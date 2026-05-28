-- Migration 003: Add re_escalation_within_monitoring column to session_audit
-- Date: 2026-05-28
-- Purpose: Persist the re-escalation detection flag from _crisis_response_node
--          so re-escalation events are queryable for PDPL compliance and clinician review.
-- Related: CSM-2 routing fix (feat/2026-05-28-safety-fixes-criteria-eval branch)
-- Prerequisite: re_escalation_within_monitoring field added to SageState in Task 4.

ALTER TABLE public.session_audit
  ADD COLUMN IF NOT EXISTS re_escalation_within_monitoring BOOLEAN;

COMMENT ON COLUMN public.session_audit.re_escalation_within_monitoring IS
  'True when a crisis response fired while crisis_state was already "monitoring" (re-escalation during post-crisis monitoring period). NULL when no crisis response occurred this turn. Set by _crisis_response_node and persisted here for PDPL audit trail and clinician review queries.';
