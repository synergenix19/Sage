# SAGE_INFO_REQUEST_CONSULT write conflict — RCA + reclassification (2026-07-29, supersedes the 07-29 drift closure)

**Status:** flip sequence HELD at the pre-flip readback gate (amendment 1 of the C1 flip approval —
the gate caught it live). **Writer IDENTIFIED. Not drift. Not a breach. A cross-session ownership
conflict: both writers were the owner, via two parallel sessions, each acting on the owner's own
in-session instruction, each classifying the other as the rogue.**

## Identity (decisive evidence, from session transcripts — not Railway history)

Writer = Claude Code work session `31f8b5b8` (conformance/Part-A stream, worktree
`sage-poc-ocdarfix`). Four explicit writes of `SAGE_INFO_REQUEST_CONSULT=false`:

| When (UTC) | Its stated reason (verbatim from transcript) |
|---|---|
| 07-28 12:23 | "revert SAGE_INFO_REQUEST_CONSULT to false BEFORE the push" — owner chose **Revert** on its ratify-or-revert Decision 2 (clean dark ship of Part A/#369) |
| 07-29 07:08 | "re-revert (2nd uncommanded flip today)" — the command session's ratified restore, read as drift |
| 07-29 07:30 | "third uncommanded flip… during this turn… re-reverting once more" |
| 07-29 07:50 | "re-revert… should hold now the writer is stalled" + standing routing: "if they want it live, it comes as the owned decision with its 8→10 delta reviewed. Until then, false." |

## Reclassification chain

1. **07-28:** parallel session sets `false` — **owner-commanded** in that session (clean dark ship).
2. **07-29 morning:** command session finds `false`, no rationale discoverable in Railway/repo →
   closes as "drift", restores `true`, owner ratifies. **That closure is SUPERSEDED by this record:**
   the rationale existed, but lived only in the parallel session's conversation — exactly the
   cross-session ownership gap named in `2026-07-23-cross-session-ownership-protocol-gap.md`.
3. **07-29 07:08–07:50:** the var war — two owner-authorized standing orders in conflict, no shared
   ledger to reconcile them. The memory-crash class (2026-05-27), replayed on prod config.

## Resolution of the ownership question

The parallel session's demand — "the owned decision with its 8→10 delta reviewed" — **is satisfied
by the existing record**, which it had no line of sight to:
Vee-approved B1 (consult set) · go-live verification 2026-07-23 with the measured 8→11/36 delta
(PR#362) · owner drift-resolution ratification 2026-07-29 · v7.3 amendment record (PR#379, §approval
chain). **`SAGE_INFO_REQUEST_CONSULT=true` is the owned, ratified state. No new ruling needed.**
The parallel session's 07-28 revert served its purpose (that push shipped dark) and carries no
standing claim beyond it.

## Current served state (verified via /health/version readback, not desired)

`build_sha dec4a9e7` (C1 code, deployed under lock, ancestry-gated) · `consult_sources_enabled:
false` (C1 dark) · `info_request_consult_enabled: false` (this conflict) · `crisis_copy_templated:
true` · migration 018 applied, inert · DEPLOY_LOCK released. Zero user turns in the surrounding 6h —
no user-visible impact from any of it.

## Actions

1. **HOLD stands** until the write path is fixed: restoring `true` while a stalled session holds a
   standing re-revert order invites a fourth write mid-sequence. The owner closes/informs session
   `31f8b5b8` (this record is the message), THEN restore proceeds under the existing ratification.
2. **Write-path fix PROMOTED from fast-follow to now** — this incident is the proof case:
   version-controlled flag defaults (repo-committed, env as audited override), deploy assertion
   comparing readback to the intended manifest. Until it lands, prod flag writes route through ONE
   session per the coordinator pattern — the same rule CLAUDE.md already imposes for memory, now
   explicitly extended to prod config.
3. **Then:** restore `SAGE_INFO_REQUEST_CONSULT=true` (existing ratification) → readback verify →
   C1 flip per the amended sequence (readback both sides, three live checks, flip-event record).
4. **Carried debt noted:** `SAGE_CONSULT_SOURCES` has no committed default yet — rides the
   write-path fix.
