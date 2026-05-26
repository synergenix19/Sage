-- 008_secondary_intent.sql
-- Adds secondary_intent_classification to messages for v7 §6.4 blended intent support.
-- Mirrors intent_classification: stores the second concurrent intent when present,
-- NULL when only one intent detected. Written from X-Sage-Secondary-Intent header.
--
-- Design decision (POC): intent is written to BOTH the user message row and the AI
-- message row for the same turn. This is intentionally redundant — it simplifies
-- analytics queries (filter by intent without joining across rows) at the cost of
-- doubled storage. The AI message row is the AUTHORITATIVE intent source because it
-- reflects the intent that the graph actually processed. The user message row carries
-- the same value for query convenience only. Do not treat them as independent sources
-- in a future schema refactor.

ALTER TABLE public.messages
  ADD COLUMN IF NOT EXISTS secondary_intent_classification text;
