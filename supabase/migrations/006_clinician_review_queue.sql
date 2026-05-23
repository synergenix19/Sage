-- 006_clinician_review_queue.sql
-- Clinician review queue for flagged sessions requiring clinical oversight.
-- One row per session (UNIQUE session_id).
-- NOTE: Assumes user_profiles table has an is_admin boolean column.

create table public.clinician_review_queue (
  id           uuid primary key default gen_random_uuid(),
  session_id   uuid not null unique references public.chat_sessions(id) on delete cascade,
  user_id      uuid not null references public.user_profiles(id) on delete cascade,
  source       text not null
               check (source in ('layer1_safety', 'llm_flag_for_review', 'manual')),
  severity     text not null default 'medium'
               check (severity in ('low', 'medium', 'high', 'critical')),
  reason       text not null,
  status       text not null default 'pending'
               check (status in ('pending', 'in_review', 'resolved', 'dismissed')),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

alter table public.clinician_review_queue enable row level security;

-- Only admins can access via RLS (browser/dashboard queries).
-- The sage-poc backend uses service role (bypasses RLS).
create policy "admin only" on public.clinician_review_queue
  for all using (
    exists (
      select 1 from public.user_profiles
      where id = auth.uid() and is_admin = true
    )
  );

create index on public.clinician_review_queue (status, created_at);
create index on public.clinician_review_queue (user_id);
