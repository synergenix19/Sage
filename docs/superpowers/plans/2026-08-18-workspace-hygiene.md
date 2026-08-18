# Workspace Hygiene (Worktree & Branch Cleanup) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reclaim ~15 GB of duplicate worktree checkouts, retire 167 merged branches, clear the shared stash hazard, and declutter the workspace root — without losing a single unmerged commit, dirty file, or stash.

**Architecture:** Read-only inventory already done (2026-08-18, this plan embeds it). Order: preserve first (stashes → branches, unpushed branches → origin, dirty files → inspected), then fix the one script dependency on a doomed worktree, then delete only from the user-approved list, tier by tier. `git worktree remove` (never `rm -rf`, never `--force`) and `git branch -d` (never `-D` except where this plan explicitly ratifies it) are the only deletion tools — both refuse when something would be lost.

**Tech Stack:** git worktrees, zsh. No Python changes except Task 2 (3 path literals in `scripts/bot_behaviour_audit/`).

**Spec:** The P5 section + P0-9 bullet of the Sage Simplification Audit (artifact `529d6973`, verified 2026-08-18); standing rules from project memory: delete-list-first, bare `stash`/`stash pop` BANNED (use `git stash branch`), deploy scripts run FROM the deploy worktree, memory dir written only by the command session.

## Global Constraints

- **Nothing is deleted before the user approves the delete-list in Task 3.** Tiers may be approved/rejected individually.
- Bare `git stash` / `git stash pop` are BANNED (3rd incident 2026-07-31). Stash recovery only via `git stash branch`.
- `sage-poc` (main checkout, on `feat/low-mood-3a-impl`, dirty) and `sage-poc-deploy` (deploy runbook requires running deploy scripts from it) are **KEEP — never on any delete list**.
- Also KEEP without asking: `sage-poc-f1-wt`, `sage-poc-f2-wt`, `sage-poc-kbrefresh-wt`, `sage-poc-conf-audit-wt`, `sage-poc-mastergraph` (all show 2026-08-17/18 activity).
- Every `git worktree remove` runs WITHOUT `--force`; if git refuses (dirty tree), stop and surface it — do not force.
- No pushes to `master`; the Task 2 code fix goes via PR under branch protection. No prod deploys anywhere in this plan.
- Do not write to the auto-memory directory (work-session rule).

---

## Embedded inventory (measured 2026-08-18)

Stashes (repo-level, shared by all worktrees):
- `stash@{0}`: "WIP on master: f44d30b docs(test): update s3_semantic header…" ← the known Lane-1 safety-WIP hazard stash
- `stash@{1}`: "On master: feat(observability): S3 tier tracking + readiness probe — review separately"

Worktrees are classified in Task 3's delete-list. Unpushed branches found: `feat/f3-f4-tipp-clinical-gated`, `fix/psychoed-resolver-reachability`, `test/cultural-overrides-condensation` (all exist ONLY locally).

---

### Task 1: Materialize both stashes as branches

**Files:** none modified — git refs only.

**Interfaces:** Produces branches `stash-recovery/lane1-safety-wip` and `stash-recovery/s3-tier-tracking`; empty stash list consumed by Task 12's verification.

- [ ] **Step 1: Create a temp worktree at each stash's base and run `git stash branch`** (it creates the branch at the stash's original base, applies, and drops — the sanctioned recovery path):

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git worktree add /tmp/stash-recovery-0 f44d30b --detach
git -C /tmp/stash-recovery-0 stash branch stash-recovery/lane1-safety-wip stash@{0}
git -C /tmp/stash-recovery-0 add -A && git -C /tmp/stash-recovery-0 commit -m "wip: recover Lane-1 safety stash (was stash@{0}, base f44d30b) — review before use"
```

- [ ] **Step 2: Repeat for stash@{1}** (after the drop in Step 1, the second stash is now `stash@{0}`):

```bash
base=$(git rev-parse 'stash@{0}^')
git worktree add /tmp/stash-recovery-1 "$base" --detach
git -C /tmp/stash-recovery-1 stash branch stash-recovery/s3-tier-tracking stash@{0}
git -C /tmp/stash-recovery-1 add -A && git -C /tmp/stash-recovery-1 commit -m "wip: recover S3 tier-tracking stash (review separately, per its own stash message)"
```

- [ ] **Step 3: Verify stash list is empty and branches exist**

Run: `git stash list; git branch --list 'stash-recovery/*'`
Expected: no stash entries; two branches listed.

- [ ] **Step 4: Remove the temp worktrees**

```bash
git worktree remove /tmp/stash-recovery-0
git worktree remove /tmp/stash-recovery-1
```

(The branches survive worktree removal.) Report both branch names to the user — the Lane-1 one satisfies the "delete when resolved" note in memory, which the command session should update.

- [ ] **Step 5: Assign the Lane-1 follow-up (amendment 3).** A branched-and-forgotten safety WIP is worse than a visible stash. Record in the delete-list file: **owner = user; review `stash-recovery/lane1-safety-wip` against current Node-1/safety_check behavior by 2026-08-25** (same cadence as the item-4 decisions), then resolve (fold into a PR) or delete with an explicit note. The command session updates `project_crisisfix_stash_recovery` accordingly.

### Task 2: Un-hardcode `sage-poc-v2live` from the three audit scripts

**Files:**
- Modify: `scripts/bot_behaviour_audit/measure_layer1.py:10`
- Modify: `scripts/bot_behaviour_audit/build_conformance_matrix.py:10`
- Modify: `scripts/bot_behaviour_audit/build_oracle_map.py:207,219`

**Interfaces:** Produces repo-relative `REPO` resolution; Task 7 may delete `sage-poc-v2live` only after this PR is merged (or the user accepts loud breakage instead).

- [ ] **Step 1: Create a branch from origin/master** (repo convention: `cdai/` prefix not needed for sage-poc):

```bash
git -C /Users/knowledgebase/Documents/Sage/sage-poc fetch origin
git worktree add /Users/knowledgebase/Documents/Sage/sage-poc-hygiene-wt -b fix/audit-scripts-repo-root origin/master
cd /Users/knowledgebase/Documents/Sage/sage-poc-hygiene-wt
```

(Fresh dedicated worktree per the contention rule; it is removed in Task 12.)

- [ ] **Step 2: Replace the literals with `__file__`-relative resolution.** In `measure_layer1.py` and `build_conformance_matrix.py` the constant is at line 10; in `build_oracle_map.py` the two literals are inside functions at lines 207 and 219 — hoist one module constant and reuse it:

```python
import pathlib
REPO = pathlib.Path(__file__).resolve().parents[2]  # scripts/bot_behaviour_audit/ -> repo root
```

In `measure_layer1.py` keep the existing string usages working: `REPO = str(pathlib.Path(__file__).resolve().parents[2])` if downstream code concatenates strings. In `build_oracle_map.py` replace the two absolute paths with `REPO / "docs/superpowers/governance"` and `REPO / "tests/fixtures/bot_behaviour_audit"`.

- [ ] **Step 3: Verify resolution and that no v2live literal remains**

Run: `python3 -c "import pathlib; print(pathlib.Path('scripts/bot_behaviour_audit').resolve().parents[0])" && grep -rn "sage-poc-v2live" scripts/ || echo CLEAN`
Expected: repo root printed; `CLEAN`.

- [ ] **Step 4: Commit and open a PR** (one commit — single finding, per commit-granularity rule):

```bash
git add scripts/bot_behaviour_audit/
git commit -m "fix(audit): resolve repo root from __file__, not a hardcoded sibling worktree

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push -u origin fix/audit-scripts-repo-root
gh pr create --title "fix(audit): repo-root resolution in bot_behaviour_audit scripts" --body "Removes hardcoded /Users/…/sage-poc-v2live paths (evidence-provenance break; audit P0-9). Prerequisite for deleting the sage-poc-v2live worktree.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

Expected: PR opens; safety gate runs (scripts-only change).

### Task 3: Present the delete-list — USER APPROVAL GATE

**Files:** Create: `/Users/knowledgebase/Documents/Sage/Docs/worktree-delete-list-2026-08-18.md` (the approved record).

**Interfaces:** Produces the approved tier list consumed by Tasks 5–10. **Execution stops here until the user answers.**

- [ ] **Step 1: Write the list below to the file and present it to the user, asking for approval per tier** (and per exception item). The list, from the measured inventory:

**Tier A — merged into origin/master, clean tree → remove worktree AND delete branch (nothing can be lost):**
`sage-poc-armonfix`, `sage-poc-b1arfix`, `sage-poc-baseline-wt`, `sage-poc-c1flip-wt`, `sage-poc-crisisfix` (after Task 1), `sage-poc-deploy-wt` (branch `docs/matrix-v6-baseline` — NOT the deploy worktree; that is `sage-poc-deploy`, kept), `sage-poc-idfix`, `sage-poc-mm-wt`, `sage-poc-ocdarfix`, `sage-poc-ocdfix`, `sage-poc-pins-wt`, `sage-poc-smokefix`, `sage-poc-tailfix`, `sage-poc-vee-sheet-wt`. **14 worktrees, ~11 GB.**

**Tier B — detached HEAD already on origin/master, clean → remove worktree (no branch involved):**
`sage-poc-caveat-wt`, `sage-poc-latency-wt`, `sage-poc-master-staging-wt`. **3 worktrees, ~2.4 GB.**

**Tier C — branch unmerged but pushed to origin with 0 local-ahead commits, clean tree → remove worktree, KEEP branch:**
`sage-poc-1a-wt` (`1a-gap-phase0`), `sage-poc-b1-wt` (`cdai/k3k4-keyword-debug-probe`), `sage-poc-r1-wt` (`cdai/r1-acute-anchor-tipp`), `sage-poc-findings` (`docs/profile-persistence-findings`), `sage-poc-v2live` (`docs/enforce-enabled-entry9`; **only after Task 2's PR merges**). **5 worktrees, ~4 GB.**

**Tier D — dirty or unpushed; Task 4 inspects each and reports back before anything happens:**
`sage-poc-1a-rerun` (detached on-master but dirty:2), `sage-poc-f6-wt` (merged, dirty:1), `sage-poc-hardening-wt` (merged, dirty:1), `sage-poc-phase0` (merged, dirty:10), `sage-poc-psychoed-spec-wt` (merged, dirty:1, contains embedded worktree `reachability-fix` — unpushed, dirty:3), `sage-poc-spec-wt` (pushed, dirty:2), `sage-poc-f3f4-wt` (clean but branch `feat/f3-f4-tipp-clinical-gated` exists ONLY locally), embedded `sage-poc/.worktrees/{crisis-phrases-expansion, feat-arabic-kb-skills-expansion, test-cultural-overrides-condensation}` (dirty:1/1/2; last one unpushed).

**cdai:** `cdai-labels-wt` (merged, clean → Tier A treatment, ~1 GB). `cdai-presence-wt` (`fix/history-mapping-siblings`, unmerged, clean — Tier C if pushed; Task 9 checks).

**Branch sweep:** the 167 local branches already merged to origin/master (Task 10 archives the exact names before deleting).

**PNG sweep:** 101 loose `*.png` at workspace root → move (not delete) to `Docs/screenshots/`.

- [ ] **Step 2: Record the user's per-tier verdicts in the file.** Only approved tiers proceed. Any name the user strikes moves to KEEP.

### Task 4: Inspect Tier D dirty files and report

**Files:** Append findings to `Docs/worktree-delete-list-2026-08-18.md`.

**Interfaces:** Produces a per-worktree disposition (salvage-then-delete / keep / delete-after-push) the user confirms before Tier D actions.

- [ ] **Step 1: For each Tier D worktree, list exactly what is dirty:**

```bash
for wt in sage-poc-1a-rerun sage-poc-f6-wt sage-poc-hardening-wt sage-poc-phase0 sage-poc-spec-wt sage-poc-psychoed-spec-wt; do
  echo "== $wt =="; git -C "/Users/knowledgebase/Documents/Sage/$wt" status --porcelain
done
for e in crisis-phrases-expansion feat-arabic-kb-skills-expansion test-cultural-overrides-condensation; do
  echo "== .worktrees/$e =="; git -C "/Users/knowledgebase/Documents/Sage/sage-poc/.worktrees/$e" status --porcelain
done
git -C "/Users/knowledgebase/Documents/Sage/sage-poc-psychoed-spec-wt/.worktrees/reachability-fix" status --porcelain
```

- [ ] **Step 2: Classify each dirty file** — untracked run-output/probe artifacts (name-matches `*.json`, `*.jsonl`, `*.png`, `*.log`) are salvage-to-`Docs/worktree-salvage-2026-08-18/<wt>/` candidates; modified tracked files are commit-or-keep decisions for the user. Present the table; wait for confirmation.

- [ ] **Step 2b: Content-aware check for the three clinical-adjacent embedded worktrees (amendment 1).** `crisis-phrases-expansion` maps to the S1 crisis lexicon (Node 1, clinician-editable), `feat-arabic-kb-skills-expansion` to the Skills & KB inventory, `test/cultural-overrides-condensation` to Node 8 cultural rules. These are NOT generic salvage candidates. For each: diff the dirty files AND the branch's unmerged commits against what actually shipped (`git -C <wt> diff origin/master -- <the rule/KB/lexicon data paths touched>` plus `git log origin/master..<branch> --stat`) and record in the delete-list file whether any safety/clinical content exists there that never landed. Anything unlanded is surfaced to the user (and onward to Vee if clinical) before the worktree is touched.

- [ ] **Step 3: Push all three unpushed branches (amendment 2 — `-D` is off the table):** `feat/f3-f4-tipp-clinical-gated`, `fix/psychoed-resolver-reachability`, and `test/cultural-overrides-condensation` are each pushed to origin as-is (`git -C <wt> push -u origin <branch>`). Pushing is free and non-destructive; a branch touching a deterministic-guardrail category is preserved even if superseded. No local branch deletion for these three in this plan.

### Task 4b: Bundle backups — full-ref insurance (amendment 4)

**Interfaces:** Produces two bundle files that make every subsequent deletion reversible (all refs, including the 167 branches about to be swept; stashes are already branches by Task 1).

- [ ] **Step 1: Create the bundles:**

```bash
git -C /Users/knowledgebase/Documents/Sage/sage-poc bundle create /Users/knowledgebase/Documents/Sage/sage-poc-backup-2026-08-18.bundle --all
git -C /Users/knowledgebase/Documents/Sage/cdai bundle create /Users/knowledgebase/Documents/Sage/cdai-backup-2026-08-18.bundle --all
```

- [ ] **Step 2: Verify both bundles:**

Run: `git -C /Users/knowledgebase/Documents/Sage/sage-poc bundle verify /Users/knowledgebase/Documents/Sage/sage-poc-backup-2026-08-18.bundle && git -C /Users/knowledgebase/Documents/Sage/cdai bundle verify /Users/knowledgebase/Documents/Sage/cdai-backup-2026-08-18.bundle`
Expected: both report the bundle is valid. Recovery path if ever needed: `git clone <bundle>` or `git fetch <bundle> <ref>`.

### Task 5: Remove Tier A worktrees and their merged branches

**Interfaces:** Consumes Task 3 approval and Task 4b's verified bundles. Each removal is one loop iteration; `git worktree remove` aborts the iteration if anything is dirty.

- [ ] **Step 0: Re-fetch and re-verify merged status (amendment 5)** — classification can drift between approval and execution:

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc && git fetch origin master --quiet
for wt in armonfix b1arfix baseline-wt c1flip-wt crisisfix deploy-wt idfix mm-wt ocdarfix ocdfix pins-wt smokefix tailfix vee-sheet-wt; do
  b=$(git -C "/Users/knowledgebase/Documents/Sage/sage-poc-$wt" branch --show-current)
  [ -z "$b" ] || git merge-base --is-ancestor "$b" origin/master || echo "DRIFTED — pull from list: sage-poc-$wt ($b)"
done
```

Expected: no DRIFTED lines. Any DRIFTED worktree is pulled from this tier and re-reported.

- [ ] **Step 1: Remove (no --force) and delete each merged branch with `-d`:**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
for wt in armonfix b1arfix baseline-wt c1flip-wt crisisfix deploy-wt idfix mm-wt ocdarfix ocdfix pins-wt smokefix tailfix vee-sheet-wt; do
  p="/Users/knowledgebase/Documents/Sage/sage-poc-$wt"
  b=$(git -C "$p" branch --show-current)
  git worktree remove "$p" && { [ -n "$b" ] && [ "$b" != "master" ] && git branch -d "$b"; true; } || echo "SKIPPED (refused): $p"
done
```

Expected: 14 removals, 13 branch deletions (crisisfix was on `master`), zero SKIPPED lines. Any SKIPPED line → stop, report, do not force.

- [ ] **Step 2: Verify**

Run: `git worktree list | wc -l` — expected: 14 fewer than before (was 40 incl. embedded).

### Task 6: Remove Tier B detached worktrees

- [ ] **Step 1:**

```bash
for wt in caveat-wt latency-wt master-staging-wt; do
  git worktree remove "/Users/knowledgebase/Documents/Sage/sage-poc-$wt" || echo "SKIPPED: $wt"
done
```

Expected: 3 removals, no SKIPPED.

### Task 7: Remove Tier C worktrees (branches preserved)

**Interfaces:** Consumes Task 2's merged PR before touching `sage-poc-v2live`.

- [ ] **Step 1: Confirm the Task 2 PR is merged:** `gh pr view fix/audit-scripts-repo-root --json state -q .state` → expected `MERGED`. If not merged, remove the other four and defer `v2live`. **Also re-verify (amendment 5)** that each Tier C branch is still on origin with 0 local-ahead commits: `git fetch origin --quiet && for b in 1a-gap-phase0 cdai/k3k4-keyword-debug-probe cdai/r1-acute-anchor-tipp docs/profile-persistence-findings docs/enforce-enabled-entry9; do echo "$b ahead: $(git rev-list --count origin/$b..$b)"; done` — expected all 0; any non-zero branch's worktree is pulled from this tier.

- [ ] **Step 2:**

```bash
for wt in 1a-wt b1-wt r1-wt findings v2live; do
  git worktree remove "/Users/knowledgebase/Documents/Sage/sage-poc-$wt" || echo "SKIPPED: $wt"
done
git branch --list '1a-gap-phase0' 'cdai/k3k4-keyword-debug-probe' 'cdai/r1-acute-anchor-tipp' 'docs/profile-persistence-findings' 'docs/enforce-enabled-entry9'
```

Expected: 5 removals; all 5 branches still listed (they are pushed; keeping local refs is free).

### Task 8: Execute the confirmed Tier D dispositions

**Interfaces:** Consumes Task 4's user-confirmed table. This task is written generically because dispositions depend on that confirmation.

- [ ] **Step 1: Salvage approved untracked artifacts:** `mkdir -p /Users/knowledgebase/Documents/Sage/Docs/worktree-salvage-2026-08-18/<wt>` and `mv` each approved file in.
- [ ] **Step 2: Push the two branches approved for pushing** (`git -C <wt> push -u origin <branch>`), commit any keep-decisions the user made in place.
- [ ] **Step 3: Remove embedded worktrees first** (`sage-poc/.worktrees/*`, then `sage-poc-psychoed-spec-wt/.worktrees/reachability-fix`), then their parents where approved, using the same no-force loop shape as Task 5. Goal state: `sage-poc/.worktrees/` does not exist.
- [ ] **Step 4: Run `git worktree prune` and re-list.**

### Task 9: cdai worktrees

- [ ] **Step 1: Remove the merged one and check the other's push state:**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git worktree remove ../cdai-labels-wt && git branch -d feat/source-card-labels
git rev-parse --verify -q origin/fix/history-mapping-siblings \
  && git rev-list --count origin/fix/history-mapping-siblings..fix/history-mapping-siblings
```

- [ ] **Step 2:** If the branch is on origin with 0 ahead → `git worktree remove ../cdai-presence-wt` (keep the branch). If not on origin → push it first (`git push -u origin fix/history-mapping-siblings` from the worktree), then remove. Note: cdai branch convention requires no rename here — the branch already exists; do not rename existing refs.

### Task 10: Merged-branch sweep (167 branches)

- [ ] **Step 1: Archive the exact list, then delete with `-d` only:**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git branch --merged origin/master | grep -vE '^\*|master|stash-recovery' > /Users/knowledgebase/Documents/Sage/Docs/deleted-branches-2026-08-18.txt
wc -l /Users/knowledgebase/Documents/Sage/Docs/deleted-branches-2026-08-18.txt
xargs git branch -d < /Users/knowledgebase/Documents/Sage/Docs/deleted-branches-2026-08-18.txt
```

Expected: ~165 deletions (167 minus refs deleted in Task 5 that were also in the count); `-d` refuses anything git considers unmerged — any refusal is reported, never escalated to `-D`. Two expected behaviors (amendment 6): the `master` filter matches anywhere in a name, so any branch merely *containing* "master" is over-kept (safe direction — note survivors rather than being surprised); and `-d` also refuses branches still checked out in surviving worktrees — those refusals are expected and accepted, not errors.

- [ ] **Step 2: Verify:** `git branch | wc -l` — expected under ~90 (252 − Task 5 − this sweep), all survivors either unmerged, `stash-recovery/*`, or checked out.

### Task 11: PNG sweep

- [ ] **Step 1:**

```bash
mkdir -p /Users/knowledgebase/Documents/Sage/Docs/screenshots
mv /Users/knowledgebase/Documents/Sage/*.png /Users/knowledgebase/Documents/Sage/Docs/screenshots/
ls /Users/knowledgebase/Documents/Sage/*.png 2>/dev/null | wc -l
```

Expected: 0 remaining. (Move, not delete — several are audit evidence referenced by docs.)

### Task 12: Final verification and report

- [ ] **Step 1: Verify end state:**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc && git worktree prune
git worktree list            # expected: main + deploy + the 5 named KEEPs + hygiene-wt + unresolved Tier D holds
git stash list               # expected: empty
du -sh /Users/knowledgebase/Documents/Sage
git worktree remove /Users/knowledgebase/Documents/Sage/sage-poc-hygiene-wt   # after Task 2's PR merged
```

- [ ] **Step 2: Report to the user:** worktrees removed, branches deleted (with the archive file path), GB reclaimed (before: ~15 GB in duplicates), stash-recovery branch names, and the list of deliberate KEEPs — so the command session can update memory (`project_crisisfix_stash_recovery`, `project_unmerged_branches`).

---

## Roadmap — subsequent plans (one per subsystem, in order)

1. **P0 correctness batch** (`sage-poc`): key rotation is **yours, same day, independent of everything** (Railway var + provisioning source; then the fail-closed reads land as a PR). Then one-commit-per-finding PRs: engine `az` one-liner + fixture; strict parse for the two default-ON flags; discriminating tokens for the three un-falsifiable tests; unconditional `gate_path` in the audit row; `testpaths`/`not slow`; `experiment_4_5` fixture repair; `lookup_*` deletion; frontend `parseInt` fix; derealization `response_en`. Vee packet in parallel: medical-screen boundary + panic/grief language gates.
2. **Keystones**: marker-based safety gate with fatal miss → `_strict_flag()` + live flag reads (+ parity readback) → `scripts/lib/prod_probe.py` + archive sweep + `scripts/README.md`.
3. **Core layer** (one PR each, byte-identical fixtures): skill_select helpers → router tables → output_gate phases → caching → resilience loop → mechanical dedup.
4. **Test consolidation** (only after the gate change): state factory → patch fixtures → parametrization → subdirectories.
5. **Frontend batch** (parallel to 3–4): dead twins → i18n registry → Supabase types → structural items.
6. **Vee-gated tail**: lands whenever sign-off arrives.
