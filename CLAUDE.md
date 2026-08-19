# Sage — Claude Code Project Instructions

## CRITICAL: Memory Write Coordination

**The memory directory is owned exclusively by the command session.**

The auto-memory system (`~/.claude/projects/.../memory/`) uses flat files with no concurrency control. Parallel sessions writing to the same files is the documented root cause of the 2026-05-27 memory crash (confirmed by file-history forensics). This rule is non-negotiable.

### The Rule

- `MEMORY.md` and all files in the memory directory are written **only by the active command session**
- Work sessions — parallel sprints, audits, subagent chains — **do not write memory directly**
- Work sessions produce findings in-conversation; the command session reads those findings and writes the memory update

### Before Starting Any Multi-Session Sprint

1. Open **one command session** that will own memory for this sprint window
2. Launch work sessions (content sprint, audit, code review, etc.) from this coordinator, or as separate sessions that report back
3. When a work session finishes a deliverable, bring its output back to the command session in-conversation
4. The command session reconciles and writes the single source of truth to memory

### Context Rollover Protocol

Long sessions hit context limits and auto-summarize. When a rollover happens:

- If the **command session** rolls over: its continuation is still the command session and still owns writes
- If a **work session** rolls over: the continuation must **not** write memory — surface findings to the user, who relays them to the command session

### Why This Matters

This maps directly to how SageAI's own LangGraph is designed: one shared state object, transitions through controlled nodes — not parallel uncoordinated mutations. The same invariant applies to the tooling layer.

Violating this rule under Gitex deadline pressure is exactly when it will cause the most damage.

## Repo-State Reads: Assert the Ref Before Quoting

**Never quote code or config state from a checkout's working tree without first asserting which ref it is on.** The main `sage-poc` checkout is routinely parked on a feature branch (worktree discipline means feature work lives elsewhere, but the main checkout itself is not pinned), so a read from it can serve stale state that looks current.

The rule, mechanical form:

- To cite current state, use `git show origin/master:<path>` (after `git fetch`), or read from a worktree created from `origin/master` for the task.
- If reading a working tree anyway, run `git branch --show-current` first and include the ref in the citation. A quote of "current" state from a non-master ref is not evidence.
- This is the read-side twin of the existing compare rule (no bare stash; compare via `git show origin/master:` or a temp worktree).

Origin: 2026-08-19 — a stale-checkout read of `config.py` (main checkout on a feature branch predating the H4 crisis-config adoption) produced a false safety finding that reached a PR record twice before being run to ground and retracted (PR #457).

**Escalated the same day, after the class recurred on the WRITE side.** A targeted corpus repair run from that same parked checkout shipped pre-refresh Arabic articles into production, reverting two clinician-approved citation upgrades. It was caught by a post-write integrity comparison, not prevented. Two consequences:

- **Writes are guarded in code, not by this rule.** `scripts/prod_write_guard.py` (`assert_source_ref`) refuses any prod write unless the guarded paths are byte-identical to `origin/master`, and is mandatory in `scripts/repair_corpus_articles.py`. This section remains the READ-side rule; the two are complementary, not redundant.
- **Un-parking the main checkout is no longer deferred** to "when the current feature branch lands". That checkout has now caused a bad prod write, and 46 corpus files diverge on it. Park it on master this week, coordinated with whoever holds its state — do not yank another session's working tree.

The scheduling lesson is worth stating plainly: this rule existed as an open, unmerged PR for the entire window in which the incident happened. **A defense that is written but not landed is indistinguishable from absent at the moment it is needed.**
