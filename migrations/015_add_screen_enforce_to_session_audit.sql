-- Add screen_asked / screen_answer_class / screen_branch_taken to session_audit (D1 medical screen #338,
-- ENFORCE path). audit.py writes these ONLY on a real screen turn (screen_asked set by screen_response, or
-- screen_branch_taken set by apply_screen_at_route on an answer turn), so a flag-OFF / shadow-only / non-
-- screen row stays byte-identical to master (Check B). This migration is the DEPLOY GATE for the ENFORCE
-- flip (SAGE_D1_SCREEN=true): it MUST run on the target environment before enforce is set true there, or the
-- flag-on audit write fails on unknown columns (the 012/013/014 failure mode). Existing rows get NULL.
-- Paired in the SAME PR with the #160 alert-or-fail induced-failure test (write_screen_audit raises
-- ScreenAuditError; the enforce audit is loud, never swallowed), so the schema and its loudness guarantee
-- land as ONE gated unit. The SHADOW columns (screen_shadow_*) shipped separately in migration 014.
--   screen_asked:         the contraindication question was asked this turn (the emit turn).
--   screen_answer_class:  clear_no | red_flag | contraindication_disclosed | yes | unclear | no_answer.
--   screen_branch_taken:  proceed | medical_guard | grounding | abandoned_crisis.
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS screen_asked boolean;
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS screen_answer_class text;
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS screen_branch_taken text;
