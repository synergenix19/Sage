-- §G post-flip monitors — v7.1 crisis tiering. Run against the STAGING session_audit after the
-- flag flip (requires migration 006: crisis_tier / tier_rule_id columns). Day-one signal that the
-- design behaves as proven. Parameterize the window; examples use the last 24h.

-- 1. Tier distribution (the core signal): T1 (warm) should be non-zero for distress, T2 for crisis.
SELECT crisis_tier, count(*)
FROM session_audit
WHERE created_at > now() - interval '24 hours' AND crisis_tier IS NOT NULL
GROUP BY crisis_tier ORDER BY crisis_tier;

-- 2. Which rule resolved each tier — watch s3_failclosed (fail-closed catch-all): a spike means
--    language-ID uncertainty (Arabizi/code-switch) is common; investigate, but it is SAFE (T2).
SELECT tier_rule_id, crisis_tier, count(*)
FROM session_audit
WHERE created_at > now() - interval '24 hours' AND tier_rule_id IS NOT NULL
GROUP BY tier_rule_id, crisis_tier ORDER BY count(*) DESC;

-- 3. INVARIANT CHECK: no true-SI keyword hit should ever resolve T1 (must be 0). si_* is S1 ->
--    s1_any -> T2 always. A non-zero result is a design violation — page immediately.
SELECT count(*) AS si_keyword_resolved_T1_MUST_BE_ZERO
FROM session_audit
WHERE crisis_tier = 'T1'
  AND (crisis_flags::text LIKE '%si_explicit%' OR crisis_flags::text LIKE '%si_passive%');

-- 4. Empty responses (the #58 failure mode) — must stay 0 post-flip.
SELECT date_trunc('hour', created_at) h, count(*)
FROM messages
WHERE role IN ('ai','crisis') AND length(trim(content)) < 15
  AND created_at > now() - interval '24 hours'
GROUP BY h ORDER BY h DESC;

-- 5. G1b cumulative-distress flags (clinician_review_queue, severity low) — the once-per-session
--    2nd-T1 write. Confirms G1b fires and is not flooding.
SELECT date_trunc('hour', created_at) h, count(*)
FROM clinician_review_queue
WHERE severity = 'low' AND reason ILIKE '%cumulative warm-tier%'
  AND created_at > now() - interval '24 hours'
GROUP BY h ORDER BY h DESC;

-- 6. Monitoring-turn volume (should fall vs pre-tiering, since fewer users enter crisis wrongly).
SELECT count(*) AS monitoring_turns
FROM session_audit
WHERE crisis_state = 'monitoring' AND created_at > now() - interval '24 hours';
