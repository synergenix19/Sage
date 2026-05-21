# Database Migration: Complete Trace Fields + Feedback Table

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `003_complete_trace_fields.sql` adding 5 per-turn trace columns + `clinical_flags_detail` to `messages`, a new `message_feedback` table, and a query-performance index.

**Architecture:** Single idempotent SQL migration using `IF NOT EXISTS`. No application code changes — those are in the trace-and-feedback plan. This migration is the prerequisite for both that plan and the dashboard redesign.

**Tech Stack:** Supabase (PostgreSQL 15), supabase CLI

---

## File Structure

| File | Action |
|---|---|
| `cdai/supabase/migrations/003_complete_trace_fields.sql` | Create |

---

### Task 1: Write the migration file

**Files:**
- Create: `cdai/supabase/migrations/003_complete_trace_fields.sql`

- [ ] **Step 1: Create the migration file**

```sql
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
```

- [ ] **Step 2: Verify the file was created**

Run:
```bash
cat cdai/supabase/migrations/003_complete_trace_fields.sql
```
Expected: the full SQL content above, no truncation.

- [ ] **Step 3: Apply the migration to local Supabase (if running locally)**

If a local Supabase instance is running:
```bash
cd /Users/knowledgebase/Documents/Sage/cdai
npx supabase db reset
```
Expected: output ends with `Finished supabase db reset.` without errors.

If not running locally, this step is skipped — the migration will be applied manually to the pilot DB via the Supabase dashboard SQL editor or `supabase db push`.

- [ ] **Step 4: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add supabase/migrations/003_complete_trace_fields.sql
git commit -m "feat(db): add trace fields, clinical_flags_detail, and feedback table

003_complete_trace_fields.sql adds:
- intent_classification, semantic_score, prompt_layers, token_usage, turn_number to messages
- clinical_flags_detail jsonb for timestamped flag detection (clinician timeline)
- message_feedback table with RLS for per-turn thumbs up/down data
- idx_feedback_message_id for admin dashboard join performance"
```

---

## Notes for downstream plans

- The `trace-and-feedback` plan writes `intent_classification`, `semantic_score`, `prompt_layers`, `token_usage`, `turn_number`, and `clinical_flags_detail` from Python response headers.
- `clinical_flags_detail` is written by `route.ts` when `clinicalFlags` is non-empty: `{"flag_name": {"detected_at": timestamp, "turn_number": N}}`.
- The `trace-and-feedback` plan writes `message_feedback` rows via `/api/feedback`.
- The `dashboard-redesign` plan reads these columns in Supabase queries.
- `CREATE POLICY IF NOT EXISTS` requires PostgreSQL 14+. Supabase Cloud runs PG15. If running on an older local dev instance, run `DROP POLICY IF EXISTS "own feedback" ON public.message_feedback;` before applying.
