# Sample media manifest (source cards) — 2026-07-07

> **⛔ SUPERSEDED / RESOLVED 2026-07-07 — the article videos below were PULLED.** They were off-spec: the BOT BEHAVIOUR `Format: Video` attaches to **skill delivery** (Item 3), not KB info-request articles, and the content was wrong (an explainer is not a technique video; 5-4-3-2-1 is `Visual + guided conversation`, not Video). `video_url` was removed from all four corpus JSONs; the articles keep their accurate **article-link** cards. The real, correct video curation is the skill-video set → **`docs/kb/2026-07-07-skill-video-curation.md`**. Table below kept for provenance only.

Historical record of the placeholder `video_url` that briefly lived in the corpus article JSON (content-as-code). Now removed.

## Sample media set (REMOVED — historical)
All four were the relaxation cluster, carrying ONE placeholder video (Wim Hof breathing clip) — chosen for guaranteed-render, not topic accuracy. This is exactly the mismatch that surfaced the correction. All now removed.

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
