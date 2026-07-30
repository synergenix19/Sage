# Deploy Record — Determinism Pins + Audit Provenance (a16b0a02)

Date: 2026-07-28. Deploy owner authorized the full sequence in-conversation
(push -> PR -> CI -> merge on green -> deploy w/ migration 016 -> flags live ->
readback confirm). Executor: command session.

## What shipped

- PR #376, merge SHA `a16b0a0215c1886bdf83b9b7b7c3f438dc63517d` (CI green incl.
  required Safety-surface unit tests; ancestry gate passed).
- Migration 016 applied to prod Supabase BEFORE the flag flip; five classifier_*
  columns verified by information_schema query.
- Flags set with the deploy (single rollout): SAGE_CLASSIFIER_SEED=20260728,
  SAGE_OPENROUTER_PROVIDER_PIN=openai, SAGE_AUDIT_CLASSIFIER_PROVENANCE=true.
- Readback confirm (authed /health/version, serving): build_sha matches; seed
  resolved 20260728 (int); pin resolved "openai"; provenance enabled true;
  crisis_copy_templated true; six new readback fields live.
- Behavioral probe: prod_smoke 9/10, ALL must-pass green (crisis EN+AR, helpline
  800-4673, derealization entry-screen hold, precedence header proxy). The single
  FAIL is report-only Tier B (no Playwright storage-state in this environment).
- Lock claimed via current deploy_prod.sh, LOCKED_DEPLOY_LOG headed by
  a16b0a0215c1, lock released after verification.

## Incidents during the deploy (self-caused, gate worked)

Two failed builds preceded the successful one:
1. First attempt ran deploy_prod.sh from the STALE main checkout (263 commits
   behind), a version predating the LOCKED_DEPLOY_LOG append; the #258 build-side
   gate correctly blocked the build as an apparent bypass.
2. Retry chained `railway up` behind a piped script call; the pipe masked the
   script's abort (own unexpired lock) and fired a second gate-blocked build.
**Runbook note (add to prod-deploy-control):** always run deploy_prod.sh FROM THE
DEPLOY WORKTREE at the deploy SHA, never from a long-lived checkout; and never
chain `railway up` behind a piped script invocation — check the script's exit
status bare.

## Discovery surfaced by the new readback coverage (DECISION ITEM, deploy owner)

`SAGE_INFO_REQUEST_CONSULT` is FALSE in prod — desired AND serving (raw_env
"false"). Earlier today it read true; the parallel deployment stream (93bd5abf,
live 17:23) flipped it off. This de-activates psychoed Mechanism-A (the
Vee-approved B1 flip, matrix 8->11/36). Not touched by this deploy; surfaced as
its own ratify/revert decision per the deploy-owner standing rule. Consequence if
it stays off: EMR three-surface picture changes (surface-1 absorption dormant);
the Phase 0 baseline must not run until this flag's intended state is ratified,
else it baselines a transient config.

## Prod state after this deploy

Serving a16b0a02 with: HIGH_RISK_DETECTION, HR_NEUTRALITY_GATE,
MEDICAL_REDFLAG_GUARD, VENTING_SUPPRESSION, ROUTE_PRECEDENCE, D1_SCREEN(+shadow),
CRISIS_TIERING, SKILL_MEDIA, pins + provenance ON; IPV_PREEMPTION off;
INFO_REQUEST_CONSULT off (see decision item). Rollback: flags off individually;
code rollback = redeploy 93bd5abf via deploy_prod.sh.
