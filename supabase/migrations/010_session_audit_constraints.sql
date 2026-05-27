-- 010_session_audit_constraints.sql
-- Adds write policy, unique turn index, and CHECK constraints to session_audit.
-- session_id remains text (not uuid) — sage-poc session IDs are not UUIDs.

-- C-1: Explicit INSERT policy (service role bypasses RLS but this prevents latent failures)
create policy "service_role_insert" on public.session_audit
  for insert with check (true);

-- C-3: Replace plain index with unique index to prevent duplicate turn rows
drop index if exists public.session_audit_session_turn;
create unique index session_audit_session_turn on public.session_audit (session_id, turn_number);

-- I-2: Engagement and intensity are 1-10 scores
alter table public.session_audit
  add constraint engagement_range check (engagement between 1 and 10),
  add constraint emotional_intensity_range check (emotional_intensity between 1 and 10);

-- I-3: Crisis state is an enumerated set
alter table public.session_audit
  add constraint crisis_state_values check (
    crisis_state in ('none', 'active', 'monitoring', 'resolved')
  );

-- I-4: knowledge_abstain should default false, not null
alter table public.session_audit
  alter column knowledge_abstain set not null,
  alter column knowledge_abstain set default false;
