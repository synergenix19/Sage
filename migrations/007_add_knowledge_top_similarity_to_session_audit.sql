-- Add knowledge_top_similarity to session_audit: the best cosine similarity in the
-- returned evidence pack, which drives the abstain decision. Recording it lets future
-- (corpus >100 gate) calibration read production score distributions for free.
-- Existing rows get NULL. Fixed-column table (Supabase PostgREST) — apply before deploy.
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS knowledge_top_similarity double precision;
