# ESCALATION — clinically-unsigned skill `mindfulness_meditation` is live and routable in production

**Date raised:** 2026-07-07
**To:** Clinical lead / clinical clock (Lane 3)
**From:** Engineering (command session). Surfaced during the V2-routing deploy prep; **not caused by this session's changes.**
**Decision requested:** explicit **intended / not-intended** ruling on a **24-hour clock**, mirroring the L2 clinical-flag review discipline.
**Severity:** clinical-safety governance (referral-escalation = escalation-matrix / L2–L3 behaviour), not housekeeping.

---

## ✅ RESOLUTION — 2026-07-07 (ruling: INTENDED; fix is documentation, not rollback)

Product owner ruling, recorded by the active command session. The escalation surfaced a **true record gap**, not an unauthorized action; the fix is to make the record honest, not to roll back.

- **Ruling: INTENDED.** Routing `mindfulness_meditation` to production was authorized.
  - **Approval basis (approved_by):** the clinician's **#130-cycle approval** of the skill package ("approved it all", which merged #130). This is the clinical half.
  - **Go-live basis:** **product-owner authorization** (Rohan) of registration + deploy under **zero-user mode** (no real users on the prod surface). This is the product half.
- **24-hour rollback clock: CANCELLED.** The prepared de-registration rollback stays **prepared but UNARMED** — recoverable in one reviewed PR if the ruling ever reverses.
- **NOT backfilled as fully-clinically-signed.** `approved_by` is deliberately **left absent/null in the JSON** — because the skill's **referral-escalation guard is genuinely still pending** (open PR #131) and the entry-screen disclosure→referral **example phrasing** is pending (open PR #144, clinician-gated). Recording a clean `clinical_lead` signature would be false. The record's value is that it is true: package-approved + PO-authorized-live, escalation-matrix rendering pending.
- **Open items, held at ESCALATED priority (Lane 3 clinician clock):** (1) **#131** referral-escalation guard confirm; (2) **#144** referral-example phrasing confirm. Both are the escalation-matrix layer; until they land, MM runs live with the gate holding correctly on serious disclosures but the referral rendered softly (documented, acceptable interim under zero-user mode).

Superseding note: the "24-hour clock" framing in the header is **closed** by this section. The header is retained unedited for provenance.

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
