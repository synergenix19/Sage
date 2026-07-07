# Session Coordination

**Why this file exists.** `CLAUDE.md` names the multi-session risk: two sessions acting against the same repo with no shared view produce contradicting records. On 2026-07-07 it happened — a V2-deploy session authored an escalation saying `mindfulness_meditation` was live-while-unsigned "on a 24-hour clock," not knowing the product owner had already authorized that go-live in another session. The escalation was true-but-stale. This file is the cheap fix.

## Protocol (every session)

1. **At session start:** add/update your row in *Active sessions* below — your working branch(es) and what you're touching.
2. **Before authoring an escalation or a plan:** read *Open governance items* first. If your concern is already ruled on here, amend the existing record — do not open a parallel one.
3. **Memory writes** still follow `CLAUDE.md`: only the active command session writes the `~/.claude/.../memory/` dir. This file is the repo-side complement (branches + governance state), not a memory substitute.

## Active sessions / branches (2026-07-07)

| Branch | Purpose | State |
|---|---|---|
| `master` | trunk | MM (#139) live; V2 flags OFF (V1 routing live) |
| `feat/mm-referral-example` (#144) | MM entry-screen disclosure→referral example | **clinician-gated, DO NOT MERGE** (phrasing = escalation-matrix) |
| `feat/mm-governance-reconcile` | escalation resolution + v2 plan constraint + this file | docs, mergeable |
| `reconcile/v2-onto-db8eb39` | V2 reranker → prod (make-v2-live plan) | parallel effort; re-gate with 28 skills owed (see below) |

## Open governance items

- **MM live-while-unsigned escalation — RESOLVED 2026-07-07: INTENDED.** Ruling in `docs/superpowers/governance/2026-07-07-mm-registration-live-in-prod-escalation.md` (RESOLUTION section). Rollback prepared-but-UNARMED. `approved_by` deliberately left null (not fully-signed — the record's value is that it's true).
- **#131** (MM referral-escalation guard, spec line 144) — clinician confirm pending. Escalated priority.
- **#144** (MM entry-screen referral *example* phrasing) — clinician confirm pending; bundle into #131 review. Escalated priority.
- **V2 go-live re-gate** — the `routing_eval` gate + global-τ on the V2 branch were measured on 27 skills WITHOUT MM. Current master has 28. Re-gate on the reconciled tree with 28 candidates before any flag-flip. Binding line added to make-v2-live plan Global Constraints. Owner: make-v2-live effort.

## Standing board (non-v2)

Lane 1 critical path is unchanged: MARBERT data-readiness gate, E7 remediation Part 2. See memory `[[project_workstream_lane1]]`.
