# Seeded sample media manifest (source cards) — 2026-07-07

Tracks the **placeholder** `video_url` values seeded directly into the **prod** KB (`knowledge_articles.citation_metadata`) to exercise the Lane 2 source-card feature under zero-user mode. Purpose: when clinician-curated, per-topic links/videos replace these, the change is a **diff against this known list**, not an audit of the whole corpus.

## Seeded set (prod, Supabase `tcekehffneiqcdyhzobi`, EN)
All four are the **relaxation / self-regulation cluster**, seeded with ONE verified-working video (a breathing/regulation clip) — plausibly on-topic for each, and guaranteed to render (an unverified per-topic ID risks "video unavailable", which reads worse to testers than a consistent working relaxation video).

| article_id | media type | value |
|---|---|---|
| `anxiety-001` | video | `https://www.youtube.com/watch?v=tybOi4hjZFQ` |
| `breathing-001` | video | `https://www.youtube.com/watch?v=tybOi4hjZFQ` |
| `grounding-001` | video | `https://www.youtube.com/watch?v=tybOi4hjZFQ` |
| `mindfulness-001` | video | `https://www.youtube.com/watch?v=tybOi4hjZFQ` |

(Article **links** are not seeded — every KB article already carries a real `source_url`, so it renders an article card without seeding. Only `video_url` is placeholder.)

## ⚠️ Ephemerality — DB-level seeding is wiped by a backend deploy
The KB uses **deploy-time auto-sync (content-as-code, #36)**: a backend deploy re-ingests the corpus from the repo and **overwrites `citation_metadata`**, dropping any DB-only `video_url`. Observed 2026-07-06: `breathing-001` was seeded before the source-cards `railway up` finished and was wiped by that deploy's sync; it was re-seeded after. **After ANY backend (sage-api) deploy, re-apply this seed set** (`/tmp/seed_media.sql` pattern: `jsonb_set(citation_metadata,'{video_url}', to_jsonb(<url>::text))` per article).

## Durable path (when this graduates from placeholder)
Add `video_url` to the KB **article source files** (content-as-code) so re-sync preserves it — this is the same field the ingestion pipeline already hashes (`_HASHED_FIELDS`) and passes through `citation_meta`. At that point the clinician-curated per-topic videos live in the repo, survive deploys, and this manifest is retired. Ties into the deferred link/curation allowlist work.

## Provenance
Seeded during Lane 2 Item 1 go-live + Item 1.5 (persistence) verification. Feature: `X-Sage-Sources` header → source card; persistence via `messages.sources` (cdai migration 016).
