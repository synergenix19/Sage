# Prod deploy control — LOCKED pre-Gitex (2026-07-08)

**Why:** in ONE session, prod suffered **two clobbers** and **two stale-build-cache incidents**. The clobbers resolved only because both trees happened to be merged to master (luck, not a control); the stale builds served correct output only because the change was byte-identical (luck, not a control). Neither is acceptable under Gitex load. These controls are mandatory.

## Controls (mandatory)
1. **One writer to prod.** Exactly one session deploys at a time; claim the window explicitly. Parallel `railway up` is banned — it caused both clobbers (item3 `76f339d`→`944939b`; crisis-templating `27bfd3b`→`7ed83cf`).
2. **Always deploy current `origin/master`, never a feature branch.** `git checkout --detach origin/master` before `railway up`. Feature-branch deploys silently drop other merged work (item3 was dropped twice). Master is a moving target during active merging — pin the SHA you actually deploy and record it.
3. **Cache-bust correctly** (earned lesson, twice): `railway up` MUST set `RAILWAY_GIT_COMMIT_SHA=<deploy-sha>` (bumping the ARG invalidates the `COPY . .` layer — Dockerfile line 41/45). **Do NOT set/override `SAGE_BUILD_SHA` as a service var** — let it derive from the ARG (`ENV SAGE_BUILD_SHA=$RAILWAY_GIT_COMMIT_SHA`), so `/health/version` reflects BUILT code. Overriding it is what made `/health` lie **both** times.
4. **`/health/version` SHA is necessary, NOT sufficient — behavioral probe mandatory.** And the sharper rule this session earned: for a **byte-identical** change (crisis templating), there is **no output probe** — `/health` can lie and the crisis smoke can't tell stale from fresh. So:
   - **Add a provenance field to `/health/version`** — e.g. `crisis_copy_templated: bool` that checks whether the *raw* crisis source still carries a `{{crisis_}}` placeholder (present only in the templated tree). This gives byte-identical deploys a real probe.
   - Until that field exists, a byte-identical deploy is verified ONLY by the **cache-bust structural guarantee** (ARG changed → `COPY` rebuilt → new source), and must be recorded as *"cache-bust-verified,"* NOT *"behaviorally verified."*
   - **Assert convergence ACROSS REPLICAS, not a single endpoint read** (added 2026-07-17, 5th stale-build event — the first caught by the mechanism built from the prior four). A behavioral/provenance probe MUST poll the endpoint enough times to see every replica, and PASS only when the signal is consistent across all hits. One replica serving a stale tree while stamping the new `build_sha` is a *partial* lying-SHA that a single probe can miss by luck of load-balancer routing. Citation: the D1 serve/resume dark deploy — a var-triggered git redeploy served a tree missing the new `/health/version` D1-flag readback while stamping `build_sha=17cb186b`; the field was ABSENT on that replica and present on others; the deploy was accepted only after the readback converged 8/8 across replicas (`2026-07-17-d1-serve-resume-dark-deploy-record.md`). The instrument that caught it was the readback field itself — whose design premise, *verify flag state behaviorally, never infer from metadata*, was the exact instrument its own deploy needed.
5. **Ancestry gate before every deploy:** `git merge-base --is-ancestor <hotfix> <tree>` for each load-bearing commit (OCD-veto, harm-veto, crisis-templating, item3).
6. **Clinical-surface diff before every deploy** (added 2026-07-10, from the trim-shipped-unconfirmed miss — the 591 trim rode a parallel deploy live before its sign-off was recorded). A deploy must not silently change a clinician-signed field. Two commands, both before `railway up`:
   ```
   python scripts/check_signed_fields.py                       # (a) deploy tree fully signed
   git diff --stat <PROD_SHA>..<DEPLOY_SHA> -- $(python scripts/check_signed_fields.py --files)
   ```
   (a) FAILS if any signed field changed without its manifest sign-off (belt-and-suspenders to the CI gate). The second command lists which signed-field-backing files change in THIS deploy. For **every** signed field that changes, name it + its sign-off reference in the deploy-provenance entry — "deploying interpersonal_effectiveness.semantic_description change, signed Vee 2026-07-10 (item 5)". A signed-field change with no sign-off to cite = STOP, not a footnote. Manifest: `signed_clinical_fields.json`.

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

**✅ ENABLED ON PROD 2026-07-13 (`ENFORCE_DEPLOY_LOCK=1`).** Both staging tests passed with cited build evidence (Entry 9): POSITIVE `3e9fc51e` build-log `✅ build-lock: 5fca40a3bd77 claimed the deploy lock` with the ENFORCE arg `"1"` (proves Railway injects both vars + verify passes a legit deploy); NEGATIVE `a4c1d4b1` bypass build **FAILED at build phase, `image=NONE`** (verify exited 1, no image — vs the transient positive failure `2ae47518` which was `image=YES` = deploy-phase). Prod post-flip probe: deterministic harm-to-others backstop LIVE. The lock arc is closed (tripwire detects, build-side prevents). Historical note follows (the pre-enablement procedure).

**STAGING TEST RUN 2026-07-13 — positive PASSED (non-blocking); negative test WAS REQUIRED, now DONE (above).**
Set `ENFORCE_DEPLOY_LOCK=1` on staging, deployed `5fca40a` via `deploy_prod.sh staging` (which populated
staging's `LOCKED_DEPLOY_LOG` with the SHA), build reached `Healthcheck succeeded` — so **ENFORCE=1 does
NOT break a legit lock-claimed deploy.** BUT: **Railway's build logs do NOT surface the `verify_build_lock`
RUN-step stdout/stderr**, so a non-blocking build cannot distinguish "verify passed with ENFORCE injected"
from "verify was dormant because Railway didn't inject the var." **Therefore the NEGATIVE test is the
definitive confirmation and is mandatory before the prod flip:** with `ENFORCE=1`, a direct `railway up`
of a SHA NOT in `LOCKED_DEPLOY_LOG` (bypassing `deploy_prod.sh`) must **FAIL the build**. If it fails →
injection confirmed, flip prod. If it passes → Railway isn't injecting `LOCKED_DEPLOY_LOG`; switch to
passing it as an explicit `--build-arg` from `deploy_prod.sh` (or bake the verdict into `/health` so it's
observable). Staging reset to `ENFORCE_DEPLOY_LOCK=0` after the test; prod untouched.
**Evidence bar for enabling is otherwise MET** — the incident record now shows the one bypass deploy
(`7cbc77c`) caused the month's worst safety regression, so this is enable-on-confirmation, not enable-if-motivated.

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

## GATE 0 — new-safety-mechanism pre-deploy step (standing, added 2026-07-17)

Before any NEW safety mechanism ships (screen, veto, guard, detector), it clears **GATE 0** — the
layer-attribution + red-verify rules composed into a pre-deploy gate:
1. **Code-review** the mechanism (the deterministic consequence especially — where a bug is dangerous).
2. **Drive every branch** end-to-end on staging/shadow, not just isolated tests: each route taken,
   the fail-safe default reached, re-entry semantics (per-session state) exercised, crisis-supremacy
   over the mechanism exercised.
3. **Markers asserted, not echoes** (the #338/#342 harness lesson): a probe that greens on a surface
   token while the behaviour is wrong is a lie in the suite.
4. **Audit written-and-read-back** (#160 alert-or-fail): the mechanism's decision record is present.
5. **Bilingual + flow-aware** (the parity + flow-assumption lessons): every language's flow driven;
   any language whose signed content isn't ready holds the fail-safe default (grounding), verified by
   driving a turn in that language.
"No go-live on an unverified safety path; don't sign green you haven't driven." Procedure, not vigilance.
