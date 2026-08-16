# RCA — deploy-path: enforcement advisory-then-proven, collisions, premature enable (2026-07-28/29)

Companion to the conformance-number RCA (`2026-07-28-rca-correct-conformance-number.md`). Both are the same
root class: **desired-state trusted as served-state**, control existed but wasn't verified applied. This session
hit that class five+ times.

## Finding 1 — the deploy lock was ADVISORY in prod (built + verified weeks ago, but ENFORCE_DEPLOY_LOCK off)
`ENFORCE_DEPLOY_LOCK` is a build-time Dockerfile ARG (`verify_build_lock.sh`): when `=1`, a build whose SHA is
not in `LOCKED_DEPLOY_LOG` FAILS. It shipped **default-OFF** (`ARG ENFORCE_DEPLOY_LOCK=0`), pending a staging
test that Railway actually passes the args into the build (the script's own docstring flagged this unverified).
During this session's premature enable, it was **unset in prod** → the lock was advisory → raw `railway up`
bypass was expected behavior, not an anomaly. **Served-vs-desired on the control itself**: the prevention
existed in code, verified in both directions offline, but was not armed in prod.

## Finding 2 — NEGATIVE TEST: enforcement now PROVEN live (the citation)
After `ENFORCE_DEPLOY_LOCK=1` was set, a controlled bypass test (with de-risk: test SHA = current master tip
`32c4dfbb`, a safe superset, so even a non-failure lands nothing harmful):
- Setup: `32c4dfbb` **NOT** in `LOCKED_DEPLOY_LOG` (confirmed) + `ENFORCE_DEPLOY_LOCK=1` + raw `railway up`
  (no `deploy_prod.sh`, so the SHA never entered the log).
- **bypass#1 `dba2e366` → FAILED, no deploy. bypass#2 `41d60732` → FAILED, no deploy.** Reproduced.
- **Serving unchanged at `09013f19` throughout** — the bypass was PREVENTED, not merely reported.
- **Proof it failed AT the lock check (not a coincidental build error):** if Railway did not pass
  `ENFORCE_DEPLOY_LOCK=1` into the build, the ARG default (`0`) makes `verify_build_lock.sh` DORMANT →
  build PASSES. The build FAILED → therefore `=1` WAS passed AND the check blocked (`32c4dfbb` not in log,
  the only failing path). This simultaneously **closes the docstring's open question**: Railway does pass both
  `ENFORCE_DEPLOY_LOCK` and `LOCKED_DEPLOY_LOG` into the Dockerfile build ARG. Both bypasses failed quickly
  (early build stage = the lock RUN at Dockerfile L55, before the ~6-8 min BGE step), consistent with the lock
  check and inconsistent with a late dependency error.
- **Citation limit (honest):** the raw `verify_build_lock.sh` stderr line
  (`🚨 build-lock: 32c4dfbbf935 is NOT in LOCKED_DEPLOY_LOG … BLOCKING`) is in the Railway build-log UI for
  build ids `dba2e366` / `41d60732`; the CLI does not surface build stderr for failed builds. The verdict rests
  on: reproduced fast-fail on an unclaimed SHA + no deploy + the dormant-would-have-passed logic.
- **Consequence:** the deploy lock is now a **build-time guarantee**, not a courtesy. Raw `railway up` of an
  unclaimed SHA is mechanically blocked. Serialization is physics, not policy — for every deploy after this.

## Finding 3 — premature enable onto the unenforced path (process miss, owned)
The Part A panic-grounding flag was enabled (redeploy) **before** `ENFORCE_DEPLOY_LOCK` was verified on, and
without checking it — onto what was then an advisory-only path. It succeeded because quiescence held through the
~2-min window (luck, not guarantee). Outcome (Part A live + verified, §1c fix working) does not license the bet.
Graded separately: good outcome, unsound process. Recorded at that severity.

## Finding 4 — SAGE_INFO_REQUEST_CONSULT: THREE uncommanded desired-state flips in one day
Decision (owner): revert to `false` (unratified live routing change, no provenance for who set it `true`). It
was flipped back to `true` **three times**, twice within minutes of a re-revert — an active writer (likely the
parallel session's continuous deploys carrying it in their env) keeps re-asserting it. Served OFF throughout
(the running `09013f19` predates each flip), so **live behavior stayed conformance-8 safe**, but desired-state
on this var is demonstrably unstable. **Action: it joins the parity guard's asserted set** (desired-state on it
cannot be trusted), and the repeated re-assertion is a coordination conflict a var-war cannot resolve — it needs
a single owner. This is unratified-live-change provenance failing exactly as Decision 1 anticipated.

## Finding 5 — the "bypass race" resolved to a LOCK-CLAIMED superset (the good surprise)
The apparent bypass collision (my `93bd5abf` vs parallel `1f687c57` raw fires) resolved to prod serving
`09013f19`, which **IS in `LOCKED_DEPLOY_LOG`** (tripwire OK) and is a **superset** of my deploy (Part A
preserved). So the parallel session's landing deploy used `deploy_prod.sh` properly; the three raw `railway up`
fires at 12:43 were the anomaly, not the norm. **Open item for the coordinator:** establish which session fired
those raw bypasses and whether they predate the coordination doc — but the steady-state parallel deploys claim
the lock.

## Standing consequence (for the coordinator)
Prod deploys via `deploy_prod.sh` exclusively (claims the lock); raw `railway up` to prod is now mechanically
blocked by the proven enforcement. Rapid iteration ("cheap-gains" cadence) belongs on staging with promoted
batches — the collision rate this session is the product of two sessions treating the prod crisis-path service
as a continuous-integration target. Serialize deploy-path access; it is now the top process item, and the
enforcement proof is what makes the serialization a guarantee rather than a request.

## Live board (end state)
Part A panic-grounding: **live + served** (§1c → grounding, real-crisis supremacy verified). info_request:
served OFF / desired unstable (re-reverted, flagged). ENFORCE_DEPLOY_LOCK: **on + PROVEN**. Prod `09013f19`
(superset, lock-claimed). A substantially safer crisis path than session start — with the deploy control now
proven, not assumed.
