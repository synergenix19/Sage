-- 009_session_audit.sql
-- Per-turn clinical audit trail. Written by output_gate and crisis_response in sage-poc.
-- No conversation text -- clinical metadata only. PII boundary preserved.
--
-- Receives one row per conversation turn from the Python backend (sage-poc) using the
-- service role key. The table is subscribed to by the Next.js frontend (/live panel)
-- via Supabase Realtime. Admin reads are gated by user_profiles.is_admin, consistent
-- with the existing admin RLS pattern in this schema (see 006_clinician_review_queue.sql).

create table public.session_audit (
  id                    uuid        primary key default gen_random_uuid(),
  inserted_at           timestamptz not null    default now(),
  session_id            text        not null,
  turn_number           integer     not null,
  node_path             text[]      not null    default '{}',
  primary_intent        text,
  secondary_intent      text,
  intent_confidence     numeric,
  active_skill_id       text,
  active_step_id        text,
  skill_match_method    text,
  knowledge_source      text,
  knowledge_passage_ids text[]               default '{}',
  knowledge_abstain     boolean,
  crisis_state          text,
  crisis_flags          text[]               default '{}',
  clinical_flags        text[]               default '{}',
  engagement            integer,
  emotional_intensity   integer,
  model_version         text,
  latency_ms            integer,
  user_id               uuid        references auth.users(id)
);

alter table public.session_audit enable row level security;

create policy "admin_read" on public.session_audit
  for select using (
    exists (
      select 1 from public.user_profiles
      where id = auth.uid() and is_admin = true
    )
  );

create index session_audit_session_turn on public.session_audit (session_id, turn_number);
create index session_audit_recent      on public.session_audit (inserted_at desc);

alter publication supabase_realtime add table public.session_audit;
