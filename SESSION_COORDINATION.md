# Session Coordination

**Why this file exists.** `CLAUDE.md` names the multi-session risk: two sessions acting against the same repo with no shared view produce contradicting records. On 2026-07-07 it happened — a V2-deploy session authored an escalation saying `mindfulness_meditation` was live-while-unsigned "on a 24-hour clock," not knowing the product owner had already authorized that go-live in another session. The escalation was true-but-stale. This file is the cheap fix.

## Protocol (every session)

1. **At session start:** add/update your row in *Active sessions* below — your working branch(es) and what you're touching.
2. **Before authoring an escalation or a plan:** read *Open governance items* first. If your concern is already ruled on here, amend the existing record — do not open a parallel one.
3. **Memory writes** still follow `CLAUDE.md`: only the active command session writes the `~/.claude/.../memory/` dir. This file is the repo-side complement (branches + governance state), not a memory substitute.
4. **Governance-doc edits rebase onto current master before merge; conflicting edits RECONCILE, never overwrite.** The ledger (rules 1–3) stops *authoring-time* races but not *merge-time* ones: a branch cut before another's merge can silently overwrite the other's edit to the same governance doc. This has now happened twice on the #139 escalation (contradicting records, then a git-layer overwrite of #145 by #146). So: before merging any edit to a `docs/superpowers/governance/` file, rebase onto current master; if another session has touched the same doc, merge the *true parts of both* into one superseding section that cites both PRs — never let last-writer-wins silently erase a ruling.

## Active sessions / branches (2026-07-07)

| Branch | Purpose | State |
|---|---|---|
| `master` | trunk | MM (#139) live; V2 flags OFF (V1 routing live) |
| `feat/mm-referral-example` (#144) | MM entry-screen disclosure→referral example | **clinician-gated, DO NOT MERGE** (phrasing = escalation-matrix) |
| `feat/mm-governance-reconcile` | escalation resolution + v2 plan constraint + this file | docs, mergeable |
| `reconcile/v2-onto-db8eb39` | V2 reranker → prod (make-v2-live plan) | parallel effort; re-gate with 28 skills owed (see below) |

## Open governance items

- **MM live-while-unsigned escalation — RESOLVED 2026-07-07: INTENDED (reconciled).** The reconciled RESOLUTION in `docs/superpowers/governance/2026-07-07-mm-registration-live-in-prod-escalation.md` supersedes BOTH #145 and #146 (cites both, erases neither). Rollback prepared-but-UNARMED. `approved_by` deliberately null (honest).
- **#131 — LANDED (`8ab2169`) + deployed; code-complete, NOT a pending PR.** (Earlier "pending #131" records were stale — corrected.) The entry-screen holds live; referral renders softly pending #144.
- **Operative remaining gate = CMS/clinician sign-off of the referral PHRASING** (the deployed #131 text + the #144 example). **#144** (referral-example phrasing) is clinician-gated, DO NOT MERGE. Escalated priority, Lane 3.
- **Prod smoke suite — COMPLETE (Tasks 1–4), merged; wired as the MANDATORY post-deploy gate** (deploy-provenance-trail verification contract step 3: `run.py --tier all` must exit 0). Tier A ran GREEN vs prod; Tier B all 5 validated live. **Two dependencies a parallel session must NOT re-implement:**
  - (a) Tier C flag-readback CONSUMES `/health/ready` flag exposure — delivered by **make-v2-live Task 1**; do not duplicate; keep report-only until that field ships.
  - (b) **Tier B frontend auth loads a stored Playwright `storage_state` (env `SAGE_SMOKE_STORAGE_STATE`); it deliberately does NOT implement login. The cdai Playwright auth harness OWNS login + its storageState invariant. If you hit the storage-state gap, produce the file via that harness — do NOT re-implement auth in the smoke suite.**
  - Remaining SETUP (not build): helpline digit fill (PO, coupled to GL-1 dial-test), the storage-state file, the `/health/ready` field.
- **V2 go-live re-gate** — the `routing_eval` gate + global-τ on the V2 branch were measured on 27 skills WITHOUT MM. Current master has 28. Re-gate on the reconciled tree with 28 candidates before any flag-flip. Binding line added to make-v2-live plan Global Constraints. Owner: make-v2-live effort.

## Standing board (non-v2)

Lane 1 critical path is unchanged: MARBERT data-readiness gate, E7 remediation Part 2. See memory `[[project_workstream_lane1]]`.
