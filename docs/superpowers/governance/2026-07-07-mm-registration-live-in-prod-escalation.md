# ESCALATION — clinically-unsigned skill `mindfulness_meditation` is live and routable in production

**Date raised:** 2026-07-07
**To:** Clinical lead / clinical clock (Lane 3)
**From:** Engineering (command session). Surfaced during the V2-routing deploy prep; **not caused by this session's changes.**
**Decision requested:** explicit **intended / not-intended** ruling on a **24-hour clock**, mirroring the L2 clinical-flag review discipline.
**Severity:** clinical-safety governance (referral-escalation = escalation-matrix / L2–L3 behaviour), not housekeeping.

## ✅ RESOLUTION — 2026-07-07 (reconciled; supersedes both the interim UPDATE and the #145 draft)

Product-owner ruling, executed by the active command session. This section reconciles two parallel governance edits into one true record (see *Provenance of this record* below) and supersedes both. The header's "24-hour clock" and the interim UPDATE are **closed**.

**Ruling: INTENDED.** Registering and deploying `mindfulness_meditation` to production was authorized.
- **Clinical basis (for `approved_by`):** the clinician's **#130-cycle approval** of the skill package ("approved it all", merged #130).
- **Go-live basis:** **product-owner authorization** (Rohan) of registration + deploy under **zero-user mode** (no real users on the prod surface).

**Factual correction (credit to PR #146):** the referral-escalation fix **PR #131 has LANDED on master (`8ab2169`) and is deployed** — the skill is code-complete, not mid-fix. An earlier record (the #145 draft) called #131 "pending"; that was **stale**. The live entry-screen now HOLDS on a derealization disclosure; the referral renders softly pending the #144 example.

**Honest residual — the operative gate is CMS/clinician phrasing sign-off, NOT code.** `approved_by` **stays null on purpose**: the referral phrasing (the deployed #131 text + the #144 example) has **not** received CMS/clinician sign-off. Recording a clean signature would be false — the record's value is that it is true.
- **24-hour rollback clock: CANCELLED.** The prepared de-registration rollback stays **prepared but UNARMED** — one reviewed PR away if the ruling ever reverses.
- **Open at ESCALATED priority (Lane 3 clinician clock):** CMS/clinician sign-off of the referral phrasing, carried by **#131** (landed text) + **#144** (the disclosure→referral example, clinician-gated). This is the single remaining gate.

**Provenance of this record (neither prior version erased):**
- **PR #145** (`0542a90`) wrote the first RESOLUTION (ruling INTENDED, rollback cancelled) but predated #131's landing, so it called #131 "pending".
- **PR #146** (`df580c4`), branched before #145 merged, **overwrote** #145's RESOLUTION with the interim UPDATE — correctly noting #131 had landed, but not knowing the PO had already ruled INTENDED, so it left the ruling "open, sharpened to the CMS gate".
- This section merges the true parts of both: #145's ruling + #146's fact + the honest null-`approved_by`.

*This overwrite is the exact failure `SESSION_COORDINATION.md` targets; the protocol is hardened in the same change — governance-doc edits rebase onto current master and reconcile, never overwrite.*

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
