-- 005_session_summaries.sql
-- One row per session (UNIQUE session_id). BGE-M3 1024-dim embeddings.

create extension if not exists vector;

create table public.session_summaries (
  id           uuid primary key default gen_random_uuid(),
  session_id   uuid not null unique references public.chat_sessions(id) on delete cascade,
  user_id      uuid not null references public.user_profiles(id) on delete cascade,
  summary_text text not null,
  embedding    vector(1024) not null,
  safety_level text not null default 'normal'
               check (safety_level in ('normal', 'clinical', 'crisis')),
  skills_used  text[] not null default '{}',
  mood_score   float,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

alter table public.session_summaries enable row level security;
create policy "own session summaries" on public.session_summaries
  for all using (auth.uid() = user_id);

-- HNSW index for fast approximate cosine similarity
create index session_summaries_embedding_idx
  on public.session_summaries
  using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 64);

create index on public.session_summaries (user_id, safety_level);
