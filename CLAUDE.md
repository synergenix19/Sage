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
