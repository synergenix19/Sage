# Prod deploy control — LOCKED pre-Gitex (2026-07-08)

**Why:** in ONE session, prod suffered **two clobbers** and **two stale-build-cache incidents**. The clobbers resolved only because both trees happened to be merged to master (luck, not a control); the stale builds served correct output only because the change was byte-identical (luck, not a control). Neither is acceptable under Gitex load. These controls are mandatory.

## Controls (mandatory)
1. **One writer to prod.** Exactly one session deploys at a time; claim the window explicitly. Parallel `railway up` is banned — it caused both clobbers (item3 `76f339d`→`944939b`; crisis-templating `27bfd3b`→`7ed83cf`).
2. **Always deploy current `origin/master`, never a feature branch.** `git checkout --detach origin/master` before `railway up`. Feature-branch deploys silently drop other merged work (item3 was dropped twice). Master is a moving target during active merging — pin the SHA you actually deploy and record it.
3. **Cache-bust correctly** (earned lesson, twice): `railway up` MUST set `RAILWAY_GIT_COMMIT_SHA=<deploy-sha>` (bumping the ARG invalidates the `COPY . .` layer — Dockerfile line 41/45). **Do NOT set/override `SAGE_BUILD_SHA` as a service var** — let it derive from the ARG (`ENV SAGE_BUILD_SHA=$RAILWAY_GIT_COMMIT_SHA`), so `/health/version` reflects BUILT code. Overriding it is what made `/health` lie **both** times.
4. **`/health/version` SHA is necessary, NOT sufficient — behavioral probe mandatory.** And the sharper rule this session earned: for a **byte-identical** change (crisis templating), there is **no output probe** — `/health` can lie and the crisis smoke can't tell stale from fresh. So:
   - **Add a provenance field to `/health/version`** — e.g. `crisis_copy_templated: bool` that checks whether the *raw* crisis source still carries a `{{crisis_}}` placeholder (present only in the templated tree). This gives byte-identical deploys a real probe.
   - Until that field exists, a byte-identical deploy is verified ONLY by the **cache-bust structural guarantee** (ARG changed → `COPY` rebuilt → new source), and must be recorded as *"cache-bust-verified,"* NOT *"behaviorally verified."*
5. **Ancestry gate before every deploy:** `git merge-base --is-ancestor <hotfix> <tree>` for each load-bearing commit (OCD-veto, harm-veto, crisis-templating, item3).

## This session's incidents (evidence, so this isn't abstract)
- **Clobber 1:** item3 (`76f339d`, verified) reverted by parallel `944939b`.
- **Clobber 2:** crisis-templating (`27bfd3b`) reverted by parallel `7ed83cf` (#196 "Phase 1").
- **Stale build (mine):** deployed "`9f5705c`" via `railway up` + set `SAGE_BUILD_SHA` — but `RAILWAY_GIT_COMMIT_SHA` stayed `7ed83cf`, so the container ran `7ed83cf` code under a `9f5705c` label. `/health` lied; the byte-identical smoke couldn't catch it. Caught only by reading `RAILWAY_GIT_COMMIT_SHA`; fixed by cache-busting to current master (`e34e97f`).
