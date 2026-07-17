-- Add hr_branch / hr_distress_score to session_audit (HR-1 Stage 2 high_risk_response
-- terminal). audit.py writes these columns ONLY when a distress branch actually resolved
-- this turn (hr_branch set in state, by high_risk_response's _deliver_branch), so a
-- flag-OFF / non-HR / mid-protocol row (T1 entry, or the one T2 reask before a branch
-- resolves) stays byte-identical to master (Check B). This migration is a DEPLOY GATE
-- for the flag flip: it MUST run on the target environment (staging, then prod) before
-- SAGE_HIGH_RISK_TERMINAL is set true there, or the flag-ON audit write fails on unknown
-- columns (CRITICAL AUDIT FAILURE in _write_session_audit_row, same failure mode migration
-- 012 closed for SAGE_MEDICAL_REDFLAG_GUARD). Existing rows get NULL (no backfill,
-- historical turns predate the HR terminal).
--   hr_branch:          the resolved distress branch, "higher" or "lower" -- which
--                        redirect copy was delivered (999/ER escalation vs see-a-doctor),
--                        needed for post-hoc referral review and the clinician-ratified
--                        HR_HIGH_FLOOR threshold audit.
--   hr_distress_score:  the parsed 0-10 distress score that resolved the branch (null when
--                        the branch was forced by risk-language screening or the T3
--                        fail-to-higher default rather than a clean numeric parse).
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS hr_distress_score int;
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS hr_branch text;
