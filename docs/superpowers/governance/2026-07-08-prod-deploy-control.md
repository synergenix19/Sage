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

## Break-glass — bypassing the required CI gate in a genuine emergency (2026-07-10)

`master` branch protection now requires the `Safety-surface unit tests` check (strict) AND
`enforce_admins=true` — the gate binds everyone, including admins, by design (an admin bypass
on a safety gate is the lock-bypass pattern with better credentials: it exempts exactly the
people moving fastest under pressure, which is when the gate matters most). Emergencies are
handled by a RECORDED exception, not a standing hole. Every real emergency this project has had
(GL-1 helpline, the iatrogenic-OCD hotfix) still cleared its gates in hours — the evidence says
we do not need the hole.

**Break-glass procedure (all five steps, in order):**
1. **Record the justification FIRST** — append an entry to `2026-07-07-deploy-provenance-trail.md`:
   what is bypassing, why it cannot wait for CI, who authorized, timestamp.
2. **Temporarily disable** — `gh api -X PUT .../branches/master/protection` with `enforce_admins:false`
   (keep `required_status_checks` as-is). This is the smallest possible opening.
3. **Merge the one change**, then **immediately re-enable** `enforce_admins:true` (same PUT, flipped).
   The window is minutes, not a session.
4. **Verify the gate is back on** — re-read protection; confirm `enforce_admins.enabled==true`.
5. **Post-hoc review within 24h** — the bypassed change goes through the normal gate retroactively
   (open a follow-up PR that runs the suite, or run it locally and attach the result to the
   provenance entry). If it would have failed, that is an incident, not a footnote.

A break-glass with steps 1/4/5 skipped is just an admin bypass wearing a runbook — the recorded
justification and the re-enable are what make it an exception rather than a hole.

## This session's incidents (evidence, so this isn't abstract)
- **Clobber 1:** item3 (`76f339d`, verified) reverted by parallel `944939b`.
- **Clobber 2:** crisis-templating (`27bfd3b`) reverted by parallel `7ed83cf` (#196 "Phase 1").
- **Stale build (mine):** deployed "`9f5705c`" via `railway up` + set `SAGE_BUILD_SHA` — but `RAILWAY_GIT_COMMIT_SHA` stayed `7ed83cf`, so the container ran `7ed83cf` code under a `9f5705c` label. `/health` lied; the byte-identical smoke couldn't catch it. Caught only by reading `RAILWAY_GIT_COMMIT_SHA`; fixed by cache-busting to current master (`e34e97f`).

## Deploy mechanics — reliable vs. loaded gun (2026-07-10, consistent across 3 deploys: #256, #272)

Three consecutive deploys produced the same evidence about the CLI surface — this is now a documented mechanism, not an anecdote:

- **RELIABLE — `railway up`:** uploads a *named local tree*, so it deploys exactly what you checked out with no pin inheritance. Combined with `railway deployment list --environment <env> --service <svc> --json` for status (BUILDING → DEPLOYING → SUCCESS/FAILED). A `SUCCESS` means the container passed its `/health/ready` healthcheck — the observable proof that a fail-to-boot guard (e.g. `assert_crisis_locale_parity()`) passed, since a tripped guard crash-loops to FAILED.
- **LOADED GUN — `railway redeploy --from-source`:** re-deploys the *currently-pinned* commit, NOT the branch HEAD. Observed re-deploying `d27987f` three times while master was far ahead. Its failure mode is silently reverting a live fix; never use it while a hotfix is load-bearing. Deploy a **named SHA** instead.
- **BROKEN HELPER — `use-railway/scripts/railway-api.sh`:** reads `.user.token`, which the CLI leaves `null` (the real token is `.user.accessToken`), so its GraphQL polling returns `null` every poll. Use `railway deployment list` for status, not the API helper.
- **Provenance consequence (fixed this turn):** because `railway up` cannot set `RAILWAY_GIT_COMMIT_SHA`, `/health/version.build_sha` now falls back `SAGE_BUILD_SHA → RAILWAY_GIT_COMMIT_SHA → "unknown"` (loud, never blank) and reports `build_sha_source`. The durable class-fix is to stop deploying by manual upload: a named-SHA git-integration deploy re-points the source off the stale pin and makes `RAILWAY_GIT_COMMIT_SHA` truthful, closing both the `--from-source` gun and the lying-SHA in one motion.
