-- cdai/supabase/migrations/003_complete_trace_fields.sql
-- Per-turn trace fields (Priority 1) + clinical_flags_detail + feedback table (Priority 2).
-- All ADD COLUMN operations use IF NOT EXISTS for idempotency on live pilot DB.

-- 1a. intent_classification: 8-way intent from Python intent_route_node.
--     Values: skill_continuation | new_skill | general_chat | crisis |
--             info_request | exit_skill | scope_refusal | jailbreak
ALTER TABLE public.messages
  ADD COLUMN IF NOT EXISTS intent_classification text;

-- 1b. semantic_score: cosine similarity (0.0–1.0) when skill matched
--     semantically via skill_select_node. NULL when matched by keyword or
--     no skill active.
ALTER TABLE public.messages
  ADD COLUMN IF NOT EXISTS semantic_score real;

-- 1c. prompt_layers: ordered list of layer names included in the composed
--     LLM prompt for this turn. Maps to v7 §5.6 progressive disclosure layers.
--     Example: ["persona", "intent", "cultural", "clinical_adaptation",
--               "history", "skill_instruction"]
ALTER TABLE public.messages
  ADD COLUMN IF NOT EXISTS prompt_layers jsonb;

-- 1d. token_usage: input/output/total token counts from the responder LLM.
--     Example: {"input": 420, "output": 87, "total": 507}
--     NULL for scope_refusal and jailbreak paths (no LLM call).
ALTER TABLE public.messages
  ADD COLUMN IF NOT EXISTS token_usage jsonb;

-- 1e. turn_number: 1-indexed sequential turn within the session (matches
--     SageState.turn_count post-increment in output_gate_node).
ALTER TABLE public.messages
  ADD COLUMN IF NOT EXISTS turn_number integer;

-- 1f. clinical_flags_detail: timestamped detail for each clinical flag detected
--     this turn. Supplements the existing clinical_flags text[] column, which
--     remains for backward compatibility with current route.ts writes.
--     Structure: {"substance_use": {"detected_at": "2026-05-22T14:30:00Z",
--                                   "turn_number": 4}}
--     Used by: clinician dashboard timeline, Priority 3 cross-session flag
--     aggregation (session memory plan). NULL when no flags on this turn.
ALTER TABLE public.messages
  ADD COLUMN IF NOT EXISTS clinical_flags_detail jsonb;

-- 2. message_feedback table for thumbs up/down per AI message per user.
--    UNIQUE(message_id, user_id) enforces one feedback entry per pair,
--    allowing upsert on conflict for feedback changes.
CREATE TABLE IF NOT EXISTS public.message_feedback (
  id         uuid primary key default gen_random_uuid(),
  message_id uuid not null references public.messages(id) on delete cascade,
  user_id    uuid not null references public.user_profiles(id) on delete cascade,
  value      smallint not null check (value in (-1, 1)),
  created_at timestamptz not null default now(),
  unique (message_id, user_id)
);

ALTER TABLE public.message_feedback ENABLE ROW LEVEL SECURITY;

-- Users manage their own feedback.
CREATE POLICY IF NOT EXISTS "own feedback"
  ON public.message_feedback
  FOR ALL
  USING (auth.uid() = user_id);

-- Admins can read all feedback for dashboard aggregation.
CREATE POLICY IF NOT EXISTS "admin read feedback"
  ON public.message_feedback
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND is_admin = true
    )
  );

-- 3. Index on message_feedback.message_id for admin dashboard joins.
--    The UNIQUE constraint on (message_id, user_id) creates a composite index,
--    but dashboard queries aggregate by message_id alone (joining to messages
--    for skill_id, intent, etc.). Without this, every admin dashboard load
--    does a sequential scan on message_feedback.
CREATE INDEX IF NOT EXISTS idx_feedback_message_id
  ON public.message_feedback(message_id);
