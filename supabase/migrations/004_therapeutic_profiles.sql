-- 004_therapeutic_profiles.sql
-- Standard Postgres only. No auth.uid() in sage-poc queries — service-role connection.
-- Three v7-required fields included: cultural_preferences, mood_trajectory,
-- total_skills_completed (missing from initial design).

create table public.user_therapeutic_profiles (
  user_id                uuid    primary key references public.user_profiles(id) on delete cascade,
  effective_techniques   text[]  not null default '{}',
  ineffective_techniques text[]  not null default '{}',
  distortion_patterns    text[]  not null default '{}',
  disclosed_concerns     text[]  not null default '{}',
  communication_style    text,
  cultural_preferences   jsonb   not null default '{}',
  mood_trajectory        jsonb   not null default '[]',
  total_skills_completed integer not null default 0,
  session_count          integer not null default 0,
  last_extraction_turn   integer not null default 0,
  observations           jsonb   not null default '[]',
  last_updated_at        timestamptz not null default now()
);

alter table public.user_therapeutic_profiles enable row level security;
create policy "own therapeutic profile" on public.user_therapeutic_profiles
  for all using (auth.uid() = user_id);

-- Versioned history for PDPL audit trail and rollback.
-- Each upsert appends one row here before overwriting the main table.
create table public.therapeutic_profile_history (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid not null references public.user_profiles(id) on delete cascade,
  session_id         uuid,
  extraction_source  text not null
                     check (extraction_source in ('llm_extraction', 'clinician_edit', 'user_correction')),
  snapshot           jsonb not null,
  created_at         timestamptz not null default now()
);

alter table public.therapeutic_profile_history enable row level security;
create policy "own profile history" on public.therapeutic_profile_history
  for select using (auth.uid() = user_id);

create index on public.therapeutic_profile_history (user_id, created_at desc);
