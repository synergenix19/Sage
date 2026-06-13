# Work Order — External Pre-Launch Audit (calendar now, run before production)

**Date opened:** 2026-06-13
**Owner:** Product + Clinical lead (commission); external auditor (execute)
**Status:** OPEN — schedule it now; it is a long-pole that is painful to discover unscheduled.
**Not this week's problem; this week's task is to put it on the calendar.**

## Why this is a standing requirement, not an option

The PR #4 engagement audit was rigorous — its evidence pass caught a flaw that originated inside the review chain itself (the `ignore_declined` clause, introduced in review, overturned by the literature check), which is the strongest signal that the process works. But the audit's own **independence caveat stands**: it was orchestrated by the same assistant session that orchestrated the implementation. Fresh agent contexts re-deriving from primary sources is meaningfully stronger than self-report, and the claim-mapping table proves it caught real qualifications — but it is not a genuinely external pass.

Under DESC accountability and the human-in-the-loop posture (architecture §13), the **production launch wants a genuinely external audit**, not a same-session one. This internal audit is sufficient to merge a POC branch; it is not the last audit this system needs before real users. (Recorded in the audit report's independence caveat and Addendum; this work order makes it a scheduled item rather than a footnote.)

## Scope the external audit should cover (minimum)

- The deterministic safety layer end-to-end: S1/S3 crisis detection, S7 post-crisis, crisis_response bypass, the psychotic-referral routing fix (S2-10), the entry-screen invariants and the freeflow guided-protocol guardrail (S2-7 B1), the acute-substitution + safety-floor logic.
- The crisis-recall gap (CRADLE 37.1% S1 recall, clinically owned and tracked) — confirm the corpus-expansion remediation and recalibration before pilot exposure.
- The consent gate's degraded-path behavior (S1-1 unseen-offer voiding) and the per-session concurrency lock (the offer lifecycle as a sensitive surface — currently POC-acceptable, production needs the lock).
- Bilingual / Khaleeji behavior with authored Arabic content in the loop (not the en-fallback POC state), scored by raters outside the build chain.
- Governance enforcement actually being a control, not process-only (branch protection with real reviewers, the governance suite wired as a required check once the unsigned-rules backlog clears).
- The C-4 audit-write race and its KPI-denominator impact (acceptance-rate reconciliation).

## Preconditions to have ready before the external pass

- PR #4 + the safety PRs (#6, #8) merged; the clinical sign-offs and content ratifications recorded.
- The two-rater scoring complete (the Khaleeji calibration is the current long pole).
- The pre-prod blockers resolved (SAGE_API_KEY, CORS, warmup, pool characterization, CRQ UUID) per the pre-prod-blockers record.
- Reviewers with GitHub identities so branch protection binds everyone (enforce_admins → true).

## Action this week

Put it on the launch plan with an owner and a target window, sequenced after the merges + scoring + pre-prod blockers but before any real-user exposure. It is the kind of long-pole that should not be discovered unscheduled.

## Status

OPEN. Not started. Calendar item to create now.
