-- Add knowledge_query_raw / knowledge_query_searched to session_audit.
-- The knowledge rewriter now normalizes Arabic queries inside the repository
-- base layer, so the query actually searched differs from the query submitted.
-- Recording both keeps that transform visible to the audit trail (v7 traceability).
-- Existing rows get NULL (no backfill — historical turns predate the columns).
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS knowledge_query_raw text;
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS knowledge_query_searched text;
