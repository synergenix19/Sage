-- Add classifier provenance columns to session_audit (Node-2 intent bistability finding,
-- docs/superpowers/governance/2026-07-28-node2-intent-bistability-finding.md, consequence 3:
-- PDPL auditability — with path-level nondeterminism, the existing trace is necessary but
-- not sufficient to reconstruct a classifier decision).
-- audit.py writes these columns ONLY when SAGE_AUDIT_CLASSIFIER_PROVENANCE is ON, so a
-- flag-OFF row stays byte-identical to master (Check B; same discipline as migration 012's
-- gate_path/medical_flags). This migration is a DEPLOY GATE for the flag flip: it MUST run
-- on the target environment (staging, then prod) before SAGE_AUDIT_CLASSIFIER_PROVENANCE is
-- set true there, or the flag-ON audit write fails on unknown columns (CRITICAL AUDIT
-- FAILURE in _write_session_audit_row). Existing rows get NULL (no backfill — historical
-- turns predate provenance capture).
--   classifier_model:        the classifier model id in force (config CLASSIFIER_MODEL).
--   classifier_provider:     upstream provider that served the call — the response
--                            metadata "provider" field if OpenRouter returns it and the
--                            client surfaces it, else the SAGE_OPENROUTER_PROVIDER_PIN
--                            value, else NULL.
--   classifier_seed:         the SAGE_CLASSIFIER_SEED in force, or NULL (no seed sent).
--   classifier_system_fingerprint: the system_fingerprint the provider echoed on the
--                            response (seed HONOR signal: the requested seed proves
--                            intent, the fingerprint identifies the backend config that
--                            actually served the call), or NULL when the provider
--                            exposes none — recorded null, never fabricated.
--   classifier_context_hash: sha256 hex of the exact assembled classifier prompt messages,
--                            computed in intent_route immediately before invocation. This
--                            captures the stochastic-history component (the classifier
--                            prompt embeds temp-0.7 responder turns): two "identical"
--                            user-level turns with different histories hash differently,
--                            making the decision input reconstructable. NULL when the flag
--                            is ON but the turn bypassed intent_route (crisis short-circuit).
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS classifier_model text;
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS classifier_provider text;
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS classifier_seed bigint;
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS classifier_context_hash text;
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS classifier_system_fingerprint text;
