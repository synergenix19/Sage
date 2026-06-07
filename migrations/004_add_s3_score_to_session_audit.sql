-- Add s3_score column to session_audit.
-- s3_score is the advisory BGE-M3 cosine similarity from the S3 semantic crisis check.
-- It has been written by safety_check_node since v7 but the column was never created.
-- Existing rows get NULL (no backfill needed — historical rows have no score to recover).
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS s3_score float;
