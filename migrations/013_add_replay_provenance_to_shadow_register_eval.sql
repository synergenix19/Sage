-- 013_add_replay_provenance_to_shadow_register_eval.sql
-- Extends shadow_register_eval (migration 009) for the OFFLINE historical-replay
-- driver (scripts/register_eval/replay_driver.py). That driver replays real
-- Arabic user messages (source='historical_replay') and the curated seed set
-- (source='seed') through generate_shadow_arabic — rows that have no live
-- session_id/turn_number the way a served turn does (migration 009's writer,
-- shadow_eval.write_shadow_eval_row, still populates those for source='live').
--
-- Columns:
--   source              — 'live' | 'seed' | 'historical_replay'; provenance of the row.
--   source_message_id   — the messages.id (historical_replay) or seed_inputs.json
--                          entry id (seed) this row was generated from. NULL for 'live'
--                          rows (the live writer has no upstream message id to carry).
--   run_id              — the replay_driver.py invocation that produced this row;
--                          lets a killed/rerun batch be traced without being part of
--                          the idempotency key itself (re-running under a NEW run_id
--                          must still collapse onto the same row per Blocking below).
--   gender_marked       — deterministic 'f' | 'm' | 'none' computed by
--                          scripts/register_eval/gender_marker.py::detect_gender_marking
--                          from the RAW user input text (never message_en, never a
--                          rater/LLM judgment). Drives register-measurement
--                          stratification for the shadow-measure's "mirror-when-marked,
--                          neutral-when-unknown" gender policy, and the mis-gender
--                          secondary metric (did the generation mirror a marked input).
--
-- session_id / turn_number become NULLABLE: seed rows have no live session/turn to
-- attach (they are curated calibration inputs, not real conversation turns), so the
-- migration-009 NOT NULL constraint cannot hold across all three sources.
--
-- Idempotency (Blocking): a partial UNIQUE index on (source_message_id,
-- shadow_exemplar_version) WHERE source_message_id IS NOT NULL. This is additive to
-- migration 009's existing `unique (session_id, turn_number)`, not a replacement —
-- live rows (source_message_id IS NULL) continue to dedupe on (session_id,
-- turn_number) exactly as before; every seed/historical_replay row instead dedupes on
-- (source_message_id, shadow_exemplar_version). This is what makes the driver safe to
-- re-run: the same input replayed twice under the same exemplar version can produce
-- at most one row (ON CONFLICT upsert in the driver targets this index), and it keeps
-- two different exemplar_version generations of the same input as two distinct rows —
-- required so a blinded rater pool can be pulled for exactly one exemplar_version
-- (scripts/register_eval/replay_driver.py::select_pool) without silently mixing
-- generations of the same input into one comparison.
--
-- NOT applied — rides the coordinated deploy per MIGRATIONS.md convention (009/010/011
-- were exceptions applied out-of-band; that was flagged as a one-off, not a pattern to
-- repeat). Do NOT psql this directly.

ALTER TABLE shadow_register_eval
  ADD COLUMN IF NOT EXISTS source text,
  ADD COLUMN IF NOT EXISTS source_message_id text,
  ADD COLUMN IF NOT EXISTS run_id text,
  -- Per-row gate-replay detail (cultural rule-ids fired, banned-opener, format tokens,
  -- back-translation) — the durable, reviewable gate-port backlog signal. Persisted
  -- per-row rather than only aggregated into the driver's returned gate_summary.
  ADD COLUMN IF NOT EXISTS gate_replay_result jsonb,
  -- Deterministic 'f' | 'm' | 'none' from detect_gender_marking(raw user text) — drives
  -- register stratification + the mis-gender secondary metric. Never rater/LLM-judged.
  ADD COLUMN IF NOT EXISTS gender_marked text;

ALTER TABLE shadow_register_eval ALTER COLUMN session_id DROP NOT NULL;
ALTER TABLE shadow_register_eval ALTER COLUMN turn_number DROP NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS shadow_register_eval_source_message_exemplar_uidx
  ON shadow_register_eval (source_message_id, shadow_exemplar_version)
  WHERE source_message_id IS NOT NULL;
