-- supabase/migrations/001_initial_schema.sql

create table public.user_profiles (
  id             uuid primary key references auth.users(id) on delete cascade,
  name           text,
  age_range      text,
  role           text check (role in ('parent', 'service_user', 'professional')),
  locale         text not null default 'en' check (locale in ('en', 'ar')),
  is_admin       boolean not null default false,
  onboarding_complete boolean not null default false,
  onboarding_step     int not null default 1,
  wellness_q1    text,
  wellness_q2    text,
  created_at     timestamptz not null default now()
);
alter table public.user_profiles enable row level security;
create policy "own profile" on public.user_profiles
  for all using (auth.uid() = id);

create table public.chat_sessions (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references public.user_profiles(id) on delete cascade,
  name       text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.chat_sessions enable row level security;
create policy "own sessions" on public.chat_sessions
  for all using (auth.uid() = user_id);

create table public.messages (
  id         uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.chat_sessions(id) on delete cascade,
  role       text not null check (role in ('user', 'ai', 'system', 'crisis')),
  content    text not null,
  intent     text check (intent in ('knowledge', 'emotional')),
  created_at timestamptz not null default now()
);
alter table public.messages enable row level security;
create policy "own messages" on public.messages
  for all using (
    auth.uid() = (select user_id from public.chat_sessions where id = session_id)
  );

create table public.mood_scores (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references public.user_profiles(id) on delete cascade,
  session_id uuid not null references public.chat_sessions(id) on delete cascade,
  score      numeric(3,1) not null check (score >= 1 and score <= 5),
  created_at timestamptz not null default now()
);
alter table public.mood_scores enable row level security;
create policy "own mood scores" on public.mood_scores
  for all using (auth.uid() = user_id);

create table public.session_insights (
  id         uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.chat_sessions(id) on delete cascade,
  user_id    uuid not null references public.user_profiles(id) on delete cascade,
  content    text not null,
  topic_tag  text not null,
  created_at timestamptz not null default now()
);
alter table public.session_insights enable row level security;
create policy "own insights" on public.session_insights
  for all using (auth.uid() = user_id);
