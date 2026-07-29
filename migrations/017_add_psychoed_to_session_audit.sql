-- Add psychoed_* columns to session_audit (Phase 2 Task 11; psychoed pathways, spec §4.1/§6.2).
-- audit.py writes these columns ONLY when a psychoed signal fired this turn (a serve payload, a
-- matched trigger row, a collision/framing disposition, a weave in flight/fired, or the verbatim
-- hash gate having run -- see _build_session_audit_row's psychoed conditional block), so a
-- flag-OFF / non-psychoed row stays byte-identical to master (Check B, same discipline as
-- migrations 006/008/012/013/014/015). This migration is the DEPLOY GATE for the
-- SAGE_PSYCHOED_PATHWAYS flip: it MUST run on the target environment (staging, then prod) before
-- the flag is set true there, or the flag-ON audit write fails on unknown columns (the
-- 012/013/014/015 failure mode). Existing rows get NULL (no backfill; historical turns predate
-- the pathway).
--   psychoed_block_ids:        block_id(s) actually served this turn via the psychoed store
--                               (currently at most one per turn -- a list for forward
--                               compatibility with a future multi-block turn).
--   psychoed_matched_row_id:   the trigger-table row id the resolver matched (Node-4), or the
--                               semantic-backstop marker (null=None) when outcome-2 fired instead.
--   psychoed_collision_path:   which collision-table disposition resolved a cross-category
--                               ambiguity ("clean" / a collision-table winner id /
--                               "semantic_backstop"), or null when no collision logic ran.
--   psychoed_framing:          "personal" | "abstract" (or the classifier fallback) -- which
--                               framing this turn's serve/weave disposition used.
--   psychoed_weave_state:      "pending" | "fired" | "escalated" | null -- the PSY-WEAVE-1
--                               disposition for this turn (derived by
--                               audit.derive_psychoed_weave_state; "escalated" only on the
--                               crisis-node escalation-turn patch, gap-2).
--   psychoed_template_version: the serve_templates.en.json version the turn-1 composition used
--                               (freeflow_respond enriches the psychoed_serve payload with this
--                               once serve.compose_turn1 resolves it).
--   psychoed_gate_action:      "pass" | "reserved" | "fallback" | null -- the Node-8 verbatim hash
--                               gate's disposition this turn ("reserved" = re-served the pinned
--                               recomposition after a text-drift mismatch; "fallback" = block_id
--                               corruption, served the manifest check_in alone instead).
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS psychoed_block_ids TEXT[];
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS psychoed_matched_row_id TEXT;
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS psychoed_collision_path TEXT;
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS psychoed_framing TEXT;
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS psychoed_weave_state TEXT;
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS psychoed_template_version TEXT;
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS psychoed_gate_action TEXT;
