# ESCALATION — clinically-unsigned skill `mindfulness_meditation` is live and routable in production

**Date raised:** 2026-07-07
**To:** Clinical lead / clinical clock (Lane 3)
**From:** Engineering (command session). Surfaced during the V2-routing deploy prep; **not caused by this session's changes.**
**Decision requested:** explicit **intended / not-intended** ruling on a **24-hour clock**, mirroring the L2 clinical-flag review discipline.
**Severity:** clinical-safety governance (referral-escalation = escalation-matrix / L2–L3 behaviour), not housekeeping.

## What is live

- `mindfulness_meditation` is present in the live `SKILL_REGISTRY` (`src/sage_poc/skill_ids.py:10`) → **registered and routable** in production.
- Its skill JSON (`src/sage_poc/skills/mindfulness_meditation.json`) has **`approved_by: null`** — no clinician sign-off on record (evidence_base is present).
- Its referral-escalation fix is tracked in **open PR #131** ("fix/mm-referral-escalation") — **pending clinician confirmation**. Referral-escalation is escalation-matrix territory (how the skill hands a user up to L2/L3), which is exactly why an unsigned version being routable is a safety question, not a content nicety.
- Cluster membership was also adjusted (`src/sage_poc/clinical_clusters.py`), a routing-surface change whose own acceptance gate ("verify no routing change") is not on record as run.

## How it got there (provenance)

- Merged to master as **PR #139** (`feat/mm-registration`, merge commit `1e7dbc6`, "Register mindfulness_meditation + deprecate mi_readiness_ruler").
- Deployed to **production** via a manual `railway up` on **2026-07-07 ~12:20 UTC** — confirmed by the prod deployment `cliMessage`: *"Register mindfulness_meditation + deprecate mi_readiness_ruler (#139)"*. Human-initiated, outside this session.
- Prod had **no `SAGE_BUILD_SHA`** and the deploy carries **no git `commitHash`** (the deploy-provenance gap), so the exact tree is known only by the `cliMessage` + image digest `sha256:b8b65fb7…`.

## Scope note (what this ruling is and isn't about)

This escalation is **purely about #139's own merge and deploy** — nothing in the 2026-07-07 V2-live session created, registered, or routed this skill. That session only (a) added a `/health/ready` `routing_mode` field and (b) flipped the inert `SKILL_ROUTING_V2`/`SKILL_RERANK_ENABLED` flags to `0`. Those flags gate the V2 reranker, which is **not** in the deployed tree; **flags-off V1 routing is byte-identical regardless of their value**, so flipping them did not change how `mindfulness_meditation` (or any skill) routes. The ruling is entirely about whether registering/deploying the unsigned skill via #139 was intended — not about anything from this session.

## The ask

A ruling: **was routing `mindfulness_meditation` to real users in production before #131 sign-off intended?**
- **If intended:** record the sign-off basis (who approved shipping the unsigned skill, against what evidence) and close #131's gate, so the registry state and the approval record agree.
- **If not intended:** execute the prepared rollback (below) via a reviewed one-line PR.

## Prepared rollback (NOT executed)

Per governance, engineering will **not** unilaterally de-register — doing so is itself an ungoverned prod routing change (same sin, opposite direction). The fix is prepared and one reviewed PR away:

- Remove `"mindfulness_meditation",` from `SKILL_REGISTRY` in `src/sage_poc/skill_ids.py:10` (de-registration → skill becomes unreachable, inert).
- Revert the `clinical_clusters.py` membership entry added by #139.
- Redeploy. Net effect: the skill content stays in the tree but is not routable until sign-off lands.

## Governance rule this incident confirms

**Clinically-pending skill content must be inert-by-default — unregistered or flag-gated — until its clinician sign-off lands.** "Merged to master" must never imply "routable in prod." This is now cited as a concrete incident in the deploy runbook (make-v2-live plan, Task 10): **prod deploys pin to named, audited SHAs, never a branch tip; unsigned skill content ships inert.** This is the second near-miss from an unpinned deploy path; the runbook rule is what makes it the last.
