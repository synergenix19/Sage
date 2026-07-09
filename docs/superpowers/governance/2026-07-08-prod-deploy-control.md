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

## #258 — build-side deploy-lock enforcement (prevent, not just detect) — shipped DORMANT 2026-07-10

The tripwire (`deploy_tripwire.sh`) fires AFTER an unlocked deploy is live — it deters, it does not
prevent. `scripts/verify_build_lock.sh` runs INSIDE the image build (`Dockerfile`, after `COPY . .`)
and FAILS the build when the SHA being built never claimed the lock (its short SHA absent from
`LOCKED_DEPLOY_LOG`, which `deploy_prod.sh` populates before `railway up`). A direct `railway up`
bypassing `deploy_prod.sh` never logs its SHA → its build fails → the bypass is prevented.

**Shipped DEFAULT-OFF** (`ARG ENFORCE_DEPLOY_LOCK=0`): dormant warn-and-pass on every build today,
no behavior change. Self-tested offline (`verify_build_lock.sh --self-test`, gated in CI via
`tests/test_deploy_build_lock.py`).

**Enablement (do NOT flip blind — one staging build test first):**
1. Confirm Railway passes `LOCKED_DEPLOY_LOG` into the Dockerfile build ARG — this is UNVERIFIED from
   a dev box and is the one real unknown. Deploy to STAGING via `deploy_prod.sh` with
   `ENFORCE_DEPLOY_LOCK=1` set; the build must PASS (SHA is in the log).
2. Negative test on staging: a direct `railway up` (no `deploy_prod.sh`) with `ENFORCE_DEPLOY_LOCK=1`
   must FAIL the build (SHA not in log). If it passes, Railway is not passing the var → the check is
   inert and needs a different proof channel (pass `LOCKED_DEPLOY_LOG` as an explicit `--build-arg`
   from `deploy_prod.sh`).
3. Only then set `ENFORCE_DEPLOY_LOCK=1` on production. Break-glass for a legit emergency direct
   deploy = set it to 0 for the one build, justified + logged (below), re-enable after.

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
