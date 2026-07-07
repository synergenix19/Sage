# Sample media manifest (source cards) — 2026-07-07

Record of which KB articles carry **placeholder** sample `video_url` media, pending clinician-curated replacement. The media now lives **in the corpus article JSON (content-as-code)** and is carried into `citation_metadata` by the ingestion sync — it is durable across deploys, not out-of-band DB state. Purpose: when clinician-curated, per-topic links/videos replace these, the change is a **diff against this known list**, not an audit of the whole corpus.

## Sample media set (content-as-code, `data/knowledge_corpus/en/*.json`, EN)
All four are the **relaxation / self-regulation cluster**, carrying ONE verified-working video (a breathing/regulation clip) — plausibly on-topic for each, and guaranteed to render (an unverified per-topic ID risks "video unavailable", which reads worse to testers than a consistent working relaxation video).

| article_id | file | media | value |
|---|---|---|---|
| `anxiety-001` | `en/anxiety-001.json` | video | `https://www.youtube.com/watch?v=tybOi4hjZFQ` |
| `breathing-001` | `en/breathing-001.json` | video | `https://www.youtube.com/watch?v=tybOi4hjZFQ` |
| `grounding-001` | `en/grounding-001.json` | video | `https://www.youtube.com/watch?v=tybOi4hjZFQ` |
| `mindfulness-001` | `en/mindfulness-001.json` | video | `https://www.youtube.com/watch?v=tybOi4hjZFQ` |

(Article **links** are not listed — every KB article already carries a real `source_url`, so it renders an article card without any placeholder. Only `video_url` is placeholder.)

## ✅ Durable — content-as-code (the DB re-apply ritual is OBSOLETE)
The `video_url` key is a top-level field in each article JSON. Ingestion reads it (`article.get("video_url")`) and it is in `_HASHED_FIELDS`, so adding it changed the content hash and the four articles **re-ingest automatically on the next sync** — a backend deploy now *preserves* this media instead of wiping it.

**History (no longer applicable):** before this change (2026-07-06→07), the media was seeded directly into `knowledge_articles.citation_metadata` via `jsonb_set`, which the deploy-time KB re-sync (#36) overwrote — requiring a re-apply after every backend deploy. That ritual is retired by moving the media into the corpus source. No post-deploy re-seed step is needed.

## Curated-links replacement (deferred)
When clinician-curated per-topic media replaces these placeholders, edit the same `video_url` fields (and/or add curated `source_url`s) in these article JSON files — a content diff against the table above. Ties into the deferred link/curation allowlist work on the before-external-exposure checklist.

## Provenance
Introduced during Lane 2 Item 1 go-live + Item 1.5 (persistence). Feature: `X-Sage-Sources` header → source card; persistence via `messages.sources` (cdai migration 016). Media moved to content-as-code 2026-07-07.
