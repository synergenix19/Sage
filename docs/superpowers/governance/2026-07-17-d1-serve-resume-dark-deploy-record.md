# D1 serve/resume — dark-deploy record (#338)

**Status: DEPLOYED DARK + VERIFIED 2026-07-17. Prod at 17cb186b; SAGE_D1_SCREEN unset (enforce OFF),
SAGE_D1_SCREEN_SHADOW=true (shadow window undisturbed).** Authorized by user 2026-07-17.

## What deployed
serve/resume enforce render path (terminal node + held-skill resume + one-turn-hold property) + /health/version
D1 flag readback. Flag-dark: the enforce path is unreachable with SAGE_D1_SCREEN off, so it is byte-identical
to master. Landed AHEAD of the flip so the flip touches zero code (migration 015 + one flag only).

## Execution
- PR #351 merged green (Safety-surface + Ferry pass) → deploy SHA **17cb186b95c4be02d252bfc7e24af9b1a10a55cd**.
- Control #6 clinical-surface diff: **STOP-AND-LOOK resolved clean.** medical_screen.py (a signed-field-backing
  file) changed +34/-10, but every hunk is serve/resume MECHANISM (consume_pending_screen / decide_screen /
  apply_screen_at_route); NO signed-constant line (_SIGNED_QUESTIONS / SCREEN_QUESTION_EN / _ROUTES) changed;
  both signed hashes match (6a). The expected answer — "no signed fields changed" — confirmed, not shrugged.
- deploy_prod.sh: lock claimed, ancestry passed, cache-bust set. railway up from worktree@17cb186b.

## The SHA-lie caught by the behavioral probe (the reason /health SHA is necessary-NOT-sufficient)
The var-triggered git redeploy (79c9ea9f) served a tree **missing the readback** while stamping
build_sha=17cb186b — a lying SHA. The behavioral probe caught it: /health/version reported the correct SHA
but `d1_screen_enabled` was ABSENT on that replica. Held until my railway up's uploaded source (1e846d34,
correct tree) fully promoted; readback then **converged 8/8** across replicas. This is exactly why the deploy
discipline verifies BEHAVIOR, not the SHA label.

## Behavioral signature (VERIFIED)
- **Standing safety set:** prod smoke 9/9 must-pass (crisis EN/AR, helpline 800-4673, derealization hold,
  precedence proxy, flag readbacks). Only FAIL = tier_b_auth (report-only, frontend storage-state).
- **Identity proof #1 — serve/resume unreachable, shadow undisturbed:** acute-overwhelm TIPP turn →
  screen NOT served (response byte-identical to pre-deploy), active_skill_id=dbt_tipp, and the shadow row
  STILL lands (screen_shadow_action=ask_screen). Enforce audit columns correctly ABSENT from the DB
  (migration 015 is the flip gate, not applied).
- **Identity proof #2 — readback truthful:** /health/version reports d1_screen_enabled=False,
  d1_screen_shadow=true (converged 8/8) — the flag state TOLD by the endpoint, not inferred. This closes the
  readback gap logged in the shadow dark-deploy record.

## Rollback
Trivial by construction: the deployed enforce code is unreachable with SAGE_D1_SCREEN off (proven
byte-identical). The flag state IS the rollback — no code deploy needed.

## State after this deploy (the quietest true state of the arc)
Every line of code on the flip path is in production, DARK. Every human confirm is in (Vee's two lines).
Every criterion / closing condition / checklist is pre-registered (shadow N=40 / 14-day; flip checklist).
The ONLY moving part is N accruing on real traffic. Flip day = migration 015 + one flag against a tree
already serving — the smallest irreversible step, achieved by making every prior step reversible and proving it.
