-- 007_knowledge_articles.sql
-- Knowledge base table for RAG retrieval via Node 6 and knowledge_lookup tool.
-- BGE-M3 produces 1024-dimensional embeddings (normalize_embeddings=True).
-- Bilingual alignment: article_id pairs use suffix convention: "cbt-001-en" / "cbt-001-ar".
-- is_crisis_content=true: stored as single whole-document chunk, never split.
-- POC abstain threshold: KNOWLEDGE_ABSTAIN_THRESHOLD = 0.0 (abstain on zero-score only).
-- Calibrate with scripts/calibrate_retrieval_threshold.py once corpus >= 10 articles.
-- Pre-production: migrate index to Azure AI Search UAE North, swap repository.py implementation.

create extension if not exists vector;

create table public.knowledge_articles (
  id                uuid    primary key default gen_random_uuid(),
  article_id        text    not null unique,
  language          text    not null check (language in ('en', 'ar')),
  parent_id         uuid    references public.knowledge_articles(id) on delete cascade,
  chunk_text        text    not null,
  chunk_embedding   vector(1024),
  chunk_tsv         tsvector generated always as (to_tsvector('english', chunk_text)) stored,
  is_crisis_content boolean not null default false,
  source_title      text,
  source_url        text,
  citation_metadata jsonb,
  created_at        timestamptz not null default now()
);

create index on public.knowledge_articles using ivfflat (chunk_embedding vector_cosine_ops)
  with (lists = 50);

create index on public.knowledge_articles using gin (chunk_tsv);
create index on public.knowledge_articles (language);
create index on public.knowledge_articles (is_crisis_content);

alter table public.knowledge_articles enable row level security;
create policy "service role full access" on public.knowledge_articles
  using (true) with check (true);
