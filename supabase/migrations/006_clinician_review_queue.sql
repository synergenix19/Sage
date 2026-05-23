-- 006_clinician_review_queue.sql
-- source column distinguishes deterministic (layer1_safety) from LLM-perceived
-- (llm_flag_for_review) triggers — clinicians use this in triage.

create table public.clinician_review_queue (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references public.user_profiles(id) on delete cascade,
  session_id  uuid not null references public.chat_sessions(id) on delete cascade,
  reason      text not null,
  source      text not null default 'layer1_safety'
              check (source in ('layer1_safety', 'llm_flag_for_review', 'manual')),
  severity    text not null default 'medium'
              check (severity in ('low', 'medium', 'high')),
  payload     jsonb,
  status      text not null default 'pending'
              check (status in ('pending', 'reviewed', 'escalated', 'dismissed')),
  reviewed_by uuid references public.user_profiles(id),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (session_id)
);

alter table public.clinician_review_queue enable row level security;
create policy "admin read review queue" on public.clinician_review_queue
  for select using (
    exists (
      select 1 from public.user_profiles
      where id = auth.uid() and is_admin = true
    )
  );

create index on public.clinician_review_queue (status, created_at desc);
create index on public.clinician_review_queue (user_id);
create index on public.clinician_review_queue (source);
create index on public.clinician_review_queue (severity);
