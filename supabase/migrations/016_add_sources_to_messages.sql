-- 016_add_sources_to_messages.sql
-- Lane 2 Item 1.5: persist the rendered source-card list per AI message.
-- Additive, nullable — existing rows get NULL (no card on reopen, as before this feature).
-- Holds the deduped/capped/typed [{type,title,url,citation}] list the X-Sage-Sources header
-- carried (see Source type in packages/types) — the exact parsed+rendered list, not raw
-- passages, and NULL (never a stale/mismatched list) on crisis-turn rows.

alter table public.messages
  add column if not exists sources jsonb;
