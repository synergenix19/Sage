-- Add screen_shadow_action / screen_shadow_answer_class / screen_shadow_branch to session_audit
-- (D1 medical screen #338, SILENT shadow). audit.py writes these columns ONLY when the screen
-- shadow-fired this turn (screen_shadow_action set in state, by apply_screen_at_route when
-- SAGE_D1_SCREEN_SHADOW is on and enforce is off), so a flag-OFF / non-screen row stays
-- byte-identical to master (Check B). This migration is the DEPLOY GATE for the shadow flip: it
-- MUST run on the target environment (staging, then prod) before SAGE_D1_SCREEN_SHADOW is set true
-- there, or the flag-ON audit write fails on unknown columns (CRITICAL AUDIT FAILURE in
-- _write_session_audit_row, the same failure mode migrations 012/013 closed for their flags).
-- Existing rows get NULL (no backfill; historical turns predate the screen). Anonymised class +
-- route ONLY, no message content (PDPL-approved 2026-07-17).
--   screen_shadow_action:        the would-be decide_screen action this turn --
--                                ask_screen | proceed | reroute_grounding | to_medical_guard |
--                                abandon_crisis. On a fresh contraindicated routing with no prior
--                                this is "ask_screen" (the screen would have fired) -- the
--                                fire-volume numerator for the shadow-window gate.
--   screen_shadow_answer_class:  the would-be answer class when a session prior drove the decision
--                                (clear_no | red_flag | contraindication_disclosed | yes | unclear |
--                                no_answer); null on an ask/fire turn.
--   screen_shadow_branch:        the would-be branch (proceed | medical_guard | grounding |
--                                abandoned_crisis); null on an ask/fire turn.
-- NOTE: the ENFORCE columns (screen_asked / screen_answer_class / screen_branch_taken) get their
-- own migration at the SAGE_D1_SCREEN (enforce) flip gate -- they never write during the shadow
-- window, so they are deliberately NOT added here (one migration per flag-flip, per control doc).
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS screen_shadow_action text;
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS screen_shadow_answer_class text;
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS screen_shadow_branch text;
