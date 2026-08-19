# Standing rule: the committed record is the ratification; the conversation is the relay

**Date:** 2026-08-19 · **Owner-ratified** · **Class closed at its origin.**

## The failure mode (confirmed, recurring)

Twice this cycle an approval-bearing message failed to cross the session boundary intact,
and both times the defect was caught downstream by luck-shaped vigilance rather than
mechanism:
1. The P2 authorization turn was lost; caught only because the owner flagged a
   byte-identical resend of an already-dispositioned report.
2. The #475 merge conditions (B1a/B1b) were lost before the watchdog merge landed; caught
   only because the owner checked the merged artifact against their own prior turn.

The third occurrence lands somewhere nobody is looking.

## The rule

1. **Each owner approval/condition turn is committed to the governance directory (or
   appended to the applicable rulings record) BEFORE the action it authorizes executes.**
   The repo-side ratification record is authoritative; the conversation is the relay, not
   the record.
2. **The merge-gate condition check reads from that committed record**, never from what a
   session recalls receiving. (PR #503's rule — conditions named in the PR description —
   covers the PR surface; this rule covers the surface upstream of it, where the loss
   actually happened.)

Same shape as every instrument fix this cycle: serving-truth sources over recall.

## First record under this rule — the owner's rulings of 2026-08-19 (committed before execution)

**Ruling 1 (this rule itself):** as above, verbatim-substance.

**Ruling 2 (B1a ambiguity tie-break, pinned as a future fixture):** "Ambiguity fails
toward the more urgent presentation" is the correct instantiation of fail-toward-crisis
for the resource-ordering context — an ambiguous immediacy signal ("she keeps talking
about the pills") serves the 999-led variant, never the helpline-led one. When Vee
authors the intent-now boundary, this tie-break lands as a fixture in the R4 regression
set alongside her trigger vocabulary — the invariant encoded, not incidental, exactly as
F1's containment tie-breaks were.

**Board disposition (same turn):** relay cleared to send; the board holds on Vee's ticks
or the PO's direction; B1b's "a decided state, never a discovered one" framing stands as
carried in the flip predeclaration.
