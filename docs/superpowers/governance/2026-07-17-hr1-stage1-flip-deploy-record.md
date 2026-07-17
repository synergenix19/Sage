# HR-1 Stage 1 flip — production deploy record (2026-07-17)

**What shipped:** High-risk psychiatric disclosure detection Stage 1 — mania, dissociation, and
psychosis-variant disclosures now route to the existing `psychotic_referral` terminal instead of
being offered a contraindicated self-help skill. Clinician-ratified 2026-07-17 (consolidated
approval sheet A1). PR **#347** (merge `7a5cb997`).

## Deployed artifact

| | |
|---|---|
| Code SHA (pinned `RAILWAY_GIT_COMMIT_SHA`) | `7a5cb997b520c3d23a19247b2b55cb11773a0e72` |
| Prior prod SHA (full-revert target) | `a3ca60f7d2a7f9dd0c107fe9f3f4d2f5f6f64090` |
| Forward-only | prior prod is an ancestor of the new tree (verified) |
| Railway deploy (code) | `d93e39b5` SUCCESS |
| Railway deploy (flag restart) | `e94d3531` SUCCESS |
| `SAGE_HIGH_RISK_DETECTION` | **`true`** (flipped this deploy) |
| Kept OUT (confirmed unset) | `SAGE_INFO_REQUEST_CONSULT`, `SAGE_DELIVERY_FORMAT`, `SAGE_HIGH_RISK_TERMINAL` |

**Deploy path:** sanctioned `scripts/deploy_prod.sh production <sha>` (lock claimed, ancestry gate
passed, cache-bust SHA pinned) → `railway up --detach`. `LOCKED_DEPLOY_LOG` fed `7a5cb997b520`.

## The crucial gating fact — this flip has TWO halves with DIFFERENT triggers

- **Psychosis variants (CF-009, now `active:true`)** route on **rule ACTIVATION ALONE**.
  `psychotic_disclosure` is the live psychosis path and is **not** flag-gated. This half went live
  the instant the code deployed, *before* the flag flip. (This was surfaced at the checkpoint and is
  why the deploy — not just the flag — is the irreversible step.)
- **Mania / dissociation (CF-007/008)** fire their clinical flags always, but only **route** when
  `SAGE_HIGH_RISK_DETECTION=true`.

## Verification — behavioral signature, two phases (SHA self-report lies until #254)

Signal = `session_audit.skill_match_method == 'psychotic_disclosure_auto_select'`. Drives verbatim
from `tests/test_hr_routing.py`. Tripwire-muted test user, self-cleaning. Script:
`scripts/prod_smoke/hr1_stage1_verify.py`.

**Phase A — flag OFF (9/9):** psychosis variants route; mania/dissociation carry their flags
(`mania_disclosure` / `dissociation_disclosure`) but stay at `semantic_offer`/`<none>` (gated);
all controls clean. *This phase is the observed rollback-target state — see below.*

**Phase B — flag ON (9/9):** psychosis + mania + dissociation all route to `psychotic_referral`;
all controls still clean.

**Negative controls (mandated over-catch proof, both phases NOT routed):** grief
("nothing's felt real since the funeral"), panic-derealization, good-news idiom, **the A2 case
"I have so much energy today after the gym"**, and a **plain-anxiety** turn — every one carries no
HR flag (`flags={}`) and never reaches the referral.

## Rollback levers — explicit, tested-in-principle before flipping forward

1. **Fast partial (mania/dissociation only):** set `SAGE_HIGH_RISK_DETECTION=false`. Returns those
   classes to the **exact Phase-A state observed live above** (flags fire, no routing). This is the
   instant-off lever and it is *demonstrated*, not assumed — Phase A ran with the flag off.
   Caveat: a var change triggers a Railway redeploy/restart (~10 min), not an instant hot-swap.
2. **Full revert (includes the psychosis-variant half):** the flag alone does **not** undo
   psychosis-variant routing (it is activation-driven, not flag-gated). Full revert = redeploy prior
   prod SHA `a3ca60f7d2a7f9dd0c107fe9f3f4d2f5f6f64090` via `deploy_prod.sh`, or deactivate CF-009 on
   disk + redeploy.

## Provenance on what the green does NOT cover (do not misread the ancestry gate as clean baseline)

- The required "Safety-surface unit tests" gate that passed on #347 **does not include**
  `tests/test_clinical_governance.py` (absent from the gate's CANDIDATES list) and the `governance`
  marker is deselected by the default `addopts`. Its three tests
  (`test_no_active_rule_without_approved_by`, `test_no_live_template_without_approved_by`,
  `test_draft_templates_are_actually_inert`) are therefore **outside** the green.
- Locally they cannot be executed here at all: a session-scoped autouse fixture imports
  `sentence_transformers`, which is not installed in this environment → **ERROR at setup**, not a
  code failure. Known-preexisting environment gap, not introduced by this flip.
- The invariant the most relevant of these asserts (active rule ⇒ `approved_by` present) **is**
  satisfied by this flip (CF-007/008/009 carry `approved_by: clinical_lead`) **and** is separately
  enforced by the signed manifest (`safety_rule_activation_map` in `signed_clinical_fields.json`,
  covered by `tests/test_signed_fields_manifest.py`, which **is** in the gate and ran green).

## Separate finding (not a blocker for this deploy)

`scripts/deploy_golden_probe.sh` still hard-codes `GOLDEN="800 46342"`, the helpline the GL-1
reversal (2026-07-13) removed. Run today it would **false-fail**. It was **not** used as a gate here.
Needs updating to `4673` / `800-HOPE`. Filed to the doc-side queue.

## Deploy lock

Held (`knowledgebase@…|production|7a5cb997b520`); left to auto-expire at the 1200s TTL (sanctioned
no-churn release — clearing the var would trigger another redeploy). Correctly serializes deploys
until expiry.

## Sequencing honored

One irreversible safety step, verified alone. Psychoed (`SAGE_INFO_REQUEST_CONSULT`) and P0b
(`SAGE_DELIVERY_FORMAT`) kept out (confirmed unset). HR-1 Stage-2 terminal remains blocked on its
code prerequisite (A7 per-class re-engagement, ticket `2026-07-17-hr-reengagement-default.md`).
