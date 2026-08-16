# GOVERNANCE ITEM (own item, highest process severity) — no cross-session ownership protocol

**2026-07-23.** Two Claude sessions drove the SAME two workstreams (E7 correction, conformance v5) to master
concurrently, with **no ownership handoff protocol** between them. This is filed as its own board item, at
severity above any single conformance number — it is the same class as the lock-bypass finding, and the
lock bypass turned out to be the deploy that caused the month's worst safety regression (silent revert of the
harm-to-others backstop). Coordination controls that exist only on paper get bypassed under deadline pressure;
that is exactly when they cause the most damage.

## What actually happened (cost already incurred, not hypothetical)
- **A contradictory v5 baseline reached master** — two docs for the same SHA, 8/36 vs 6/36, opposite headlines
  ("conformance-neutral" vs "regression"), because two sessions measured in parallel with no single writer.
  Worse, the two runs weren't even the same config (cosine 0.42 vs 0.0), which neither session caught until a
  post-merge reconciliation compared their flag stamps.
- **MEMORY.md was written concurrently** — a `feedback_measurement_parity.md` index entry appeared authored by
  the parallel session while this session was mid-work, against the DOCUMENTED 2026-05-27 flat-file crash RCA.
  This session declined to write memory on seeing it; that was luck of timing, not a protocol.
- **Two PRs (#360, #361) merged to master with no handoff signal in either direction** — #360 merged ahead of
  the reconciliation step both sessions' work depended on, producing the split record above.
- **HEAD in the shared worktree (`sage-poc-b1-wt`) moved under this session twice** — another session was
  switching branches in the same working directory.

## The gap
There is no answer to: **who holds the pen, how a handoff is signalled, and which branches/files are
single-writer.** "Assume they're done when pushes stop" is inference; this project spent a month replacing
inference with citation, and the ownership question deserves the same. The one-writer rule in CLAUDE.md names
the invariant but provides **no enforcement and no handoff signal** — so it degrades to hope.

## What it needs (proposal, not built here)
1. **An explicit pen-holder for each merge path**, named before work starts, and a **stated stand-down signal**
   (a citation — a commit, a comment, a message — not "pushes stopped") before another session touches a
   shared surface the holder was mid-write on.
2. **Single-writer branches/files declared** — at minimum `MEMORY.md` and any branch with an open PR to master.
   MEMORY.md concurrent writes are already prohibited by the crash RCA; make it mechanically enforced (lock
   file, or a pre-write owner check) rather than convention.
3. **A merge-order interlock for dependent PRs** — #360 (instrument) depended on the reconciliation that #360's
   own merge then stranded. Dependent docs/data PRs need an ordering gate or a single author.

## Record
This reconciliation (`2026-07-23-bot-behaviour-conformance-v5-reconciled-baseline-1f687c57.md`) is the artifact
that caught the confound the parallel measurement missed; the parity-guard coverage ticket
(`2026-07-23-parity-guard-readback-coverage-gap.md`) is the instrument defect it surfaced. Both exist because
one session eventually reconciled — there is no guarantee the next split gets reconciled at all. That is the
risk this item is about.
