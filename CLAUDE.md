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

Origin: 2026-08-19 — a stale-checkout read of `config.py` (main checkout on a feature branch predating the H4 crisis-config adoption) produced a false safety finding that reached a PR record twice before being run to ground and retracted (PR #457). Convention to complete the fix: when the current feature branch on the main checkout lands, park the main checkout on master and keep it there.
