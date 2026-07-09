-- 017_rls_knowledge_articles.sql
-- Harden RLS on knowledge_articles. Closes an anon/authenticated read+write
-- exposure that migration 007 shipped and that is LIVE in prod
-- (tcekehffneiqcdyhzobi), verified 2026-07-09 via information_schema grants +
-- pg_policies + pg_class.relforcerowsecurity.
--
-- Background: 007 did `enable row level security` and then created a policy
-- named "service role full access" as `using (true) with check (true)` with NO
-- role target -- so it applies to PUBLIC (every role), not service_role.
-- Combined with Supabase's default table grants (SELECT/INSERT/UPDATE/DELETE to
-- anon and authenticated on every new public-schema table), any anon or
-- authenticated PostgREST client can READ and WRITE the clinical corpus through
-- /rest/v1/knowledge_articles -- including the is_crisis_content rows that carry
-- crisis-card / helpline copy. Read is low severity (psychoeducation content
-- shown to users anyway); WRITE is an integrity + safety exposure on a
-- mental-health surface: the corpus feeds RAG responses to at-risk users, and
-- crisis article text / helpline numbers could be silently altered or deleted.
--
-- This mirrors 010_rls_shadow_register_eval in the sage-poc migration tree and
-- the standing convention "restricted/clinical tables ship RLS ENABLE+FORCE +
-- revoke anon/authenticated in the creation migration" (007 predates it).
--
-- Safety of this change (why nothing legitimate breaks):
--   * Runtime RAG retrieval AND deploy-time corpus ingestion both run in the
--     sage-poc backend over the asyncpg pool as the Supabase `postgres`
--     superuser (DATABASE_URL), which has BYPASSRLS -- unaffected by
--     ENABLE / FORCE / REVOKE. service_role likewise bypasses RLS.
--   * The cdai frontend never queries knowledge_articles directly: the only
--     readers/writers of the table are the backend RAG repository and
--     knowledge/sync.py; the frontend renders passages from the chat API
--     response, not from PostgREST. So no anon/authenticated path is broken.
-- Idempotent: safe to re-run; safe against a fresh DB built from 007.

alter table public.knowledge_articles enable row level security;
alter table public.knowledge_articles force  row level security;

-- Replace the mis-scoped PUBLIC "using(true)" policy with a correctly
-- service_role-scoped one. The bug in 007 was the missing role target, not the
-- intent; this preserves service_role admin access while removing the PUBLIC
-- grant. (A zero-policy default-deny, as in sage-poc/010, is also acceptable --
-- the backend bypasses RLS either way; a scoped policy is kept here to honour
-- 007's stated intent.)
drop policy if exists "service role full access" on public.knowledge_articles;
drop policy if exists "service_role full access" on public.knowledge_articles;
create policy "service_role full access" on public.knowledge_articles
  to service_role using (true) with check (true);

-- Remove the default client grants outright, so even a future permissive policy
-- has no underlying grant for anon/authenticated to exercise against the table.
revoke all on public.knowledge_articles from anon, authenticated;
