# Deploy-Provenance Trail — sage-api

The audit anchor for "what is actually running in each environment." Started 2026-07-07 to close the provenance gap (no `SAGE_BUILD_SHA`, no git `commitHash` on `railway up` deploys). Every deploy appends an entry with the pinned SHA and the two-endpoint verification.

**Verification contract (per deploy):** `/health/ready` → expected `routing_mode`; `/health/version` (X-Sage-Api-Key) → `build_sha` == the deployed SHA. Both must pass or the deploy is not "good."

---

## Entry 1 — 2026-07-07 · Phase 0 / Task 1 · truthful flags + routing_mode

**Tree:** master `1c9dfeb` ("Merge PR #138"). Delta over what prod already ran (#139, `mindfulness_meditation` registration, live since 12:20) = **only the additive #138** health-field change (`compute_routing_mode` + `routing_mode` on `/health/ready`).
**Intent:** correct the inert-flag misreport (`SKILL_ROUTING_V2`/`SKILL_RERANK_ENABLED` = 1 on a V1 build) and pin both environments to a **known SHA** for the first time.
**Flags set:** `SKILL_ROUTING_V2=0`, `SKILL_RERANK_ENABLED=0`, `SAGE_BUILD_SHA=1c9dfeb`. (`SKILL_RERANK_PRECISION` left unset → fp32 default.)

### Staging — VERIFIED ✅
- Deploy id `3a4ce887…`; prior staging deploy was 2026-07-05 (staging was behind; this brings it to `1c9dfeb`).
- `/health/ready` → `{"status":"ready","routing_mode":"v1"}` ✅
- `/health/version` → `build_sha: 1c9dfeb` ✅
- vars read-back → `SKILL_ROUTING_V2=0`, `SKILL_RERANK_ENABLED=0`, `SAGE_BUILD_SHA=1c9dfeb` ✅

### Production — VERIFIED ✅
- Deploy id `4dadfc3b…` from `1c9dfeb`.
- Prior prod state: **unknown SHA** (`SAGE_BUILD_SHA` null, no `commitHash`); `cliMessage` "Register mindfulness_meditation … (#139)"; image `sha256:b8b65fb7…`; deployed 12:20. **As of this deploy, prod is pinned to a known SHA (`1c9dfeb`) — the provenance gap is closed for prod.**
- `/health/ready` → `{"status":"ready","routing_mode":"v1"}` ✅
- `/health/version` → `build_sha: 1c9dfeb` ✅
- vars read-back → `SKILL_ROUTING_V2=0`, `SKILL_RERANK_ENABLED=0`, `SAGE_BUILD_SHA=1c9dfeb` ✅

**Outcome:** the inert-flag misreport is corrected on both environments; both run the same known tree `1c9dfeb` (pure V1 + additive health field), truthfully labeled `routing_mode:"v1"`. This is the "prod runs pure V1, truthfully labeled" anchor for Task 2's frozen comparator.

**Cross-refs:** `2026-07-07-mm-registration-live-in-prod-escalation.md` (the #139 finding surfaced by this deploy); `2026-07-07-make-v2-semantic-routing-live.md` Task 10 (the runbook rules this trail enforces).

---

## Entry 2 — 2026-07-07 · OCD-compulsion iatrogenic veto (approved safety hotfix)

**Tree:** master `bc3cb4b` (PR #155). Delta over Entry 1: the deterministic Node-4 OCD-compulsion veto (`ocd_compulsion.py` + `ocd_compulsion_patterns.json` + `skill_select.py`), arm-independent, ABSTAIN→Node 3. Approved expedited hotfix for the live iatrogenic route (`2026-07-07-v1-iatrogenic-ocd-routing-escalation.md`). V2 flags unchanged (still 0; this is a V1 fix).

### Staging — VERIFIED ✅ · Production — VERIFIED ✅
- Both: `railway up` `bc3cb4b`, `SAGE_BUILD_SHA=bc3cb4b`, `/health/ready` `routing_mode:"v1"`, `/health/version` `build_sha:bc3cb4b`.
- **Behavioral (live):** OCD compulsion (stove-checking / door-tapping) → empathic clarification via Node 3, **NOT** a worry/rumination skill; ordinary worry / overwhelm → skill offer (worry_time / TIPP) as normal. Veto discriminates correctly on both environments.
- **Measured (driver):** harm gate **6→0 leaks** on both arms; zero in_scope degradation; zero in_scope false-positive vetoes; unit test 27/27.

**Outcome:** the live iatrogenic OCD-compulsion → worry-tool route is closed in production. **Follow-up (clinician, non-blocking):** Node-3 copy sometimes offers a generic "guided exercise" for vetoed-OCD cases (no skill queued → no back-door; but the spec signposts professional referral for OCD, so the Node-3 copy is a refinement candidate); `"intrusive thoughts"` in cbt_thought_record `target_presentations` flagged as clinically dual-use (not eng-edited).

---

## RUNBOOK RULE — in_scope recall tripwire (V2 flip, earned 2026-07-08)

The V2 re-verdict (`2026-07-08-v2-reverdict-FLIP.md`) cleared the signed in_scope recall conjunct by **0.31pp** (V2 52.08% vs the 51.77% floor = V1 56.77% − T=5pp). A thin pass under a signed criterion is a pass — re-litigating it would be engineering overriding the signature from the cautious side. The correct response is monitoring, not hesitation:

- **Task 12's prod measurement asserts the in_scope recall conjunct EXPLICITLY** (V2 recall ≥ V1+veto recall − 5pp), against the post-veto comparator.
- **Any future re-measurement of in_scope recall below 51.77% AUTOMATICALLY reopens the criterion conversation with PO + clinician.** Nobody absorbs a sub-floor number as drift; named and tripwired, the thin edge is just an honest number. The danger is only silent erosion.

## RUNBOOK RULE — deploy numbers cite a committed fixture SHA (from the comparator-correction incident)

Any number that gates a deploy MUST cite a committed fixture SHA; the corpus is part of the artifact. A measurement whose inputs aren't in the repo is an anecdote, not a gate.

---

## Entry 3 — 2026-07-08 · V2 semantic routing STAGING flip (EN-first) + ABSTAIN→Node 3 fix

**Tree:** staging `944939b` (PR #165 V2-live merge `202aff5` → flip → PR #171 abstain-Node3 fix). Flags `SKILL_ROUTING_V2=1 SKILL_RERANK_ENABLED=1 SKILL_RERANK_PRECISION=fp32`, `SAGE_BUILD_SHA=944939b`. **PRODUCTION NOT FLIPPED — held for command go.**

### Staging hard gates — PASS
`/health/ready` `routing_mode:"v2"` + `reranker_head_control:"passed"` (fp32 head loaded; headless→503, so 200 is the real check), `/health/version` `build_sha:944939b`, ancestry-contains-veto (`bc3cb4b` ∈ `944939b`) ✓.

### The live probe caught what every offline gate was blind to
Offline gates measured routing *decisions* (skill vs abstain), never graph *destinations*. The first staging probe showed a V2 reranker ABSTAIN landing in `freeflow_respond`, **violating binding condition #1** (ABSTAIN→Node 3, Cardinal Rule 5) — on which the clinician's signed −4.7pp recall acceptance and soft-abstain-recovery monitoring rest. Fixed by the wiring (PR #171, `fc671bb`), **not** by amending the condition. Re-probe on `944939b` confirms it live: `skill_select → keyword_rerank_veto → low_confidence_respond → output_gate`.

### Latency (Finding 2) — attribution answered, NOT a V2 regression
Full-turn tail 10–16s exceeds the signed 9.6s bound, BUT: the reranker-heavy abstain probe is **8.5s (< bound)**, and **prod V1 hit 11.68s on the identical in_scope turn** — the tail is **pre-existing LLM-generation cost present in V1**, not V2 overhead. Disposition: 9.6s bound recorded **met for reranker overhead, missed for full-turn tail**; the tail filed as a pre-existing generation-latency item against the north-star **<3s p95 KPI** (a real POC-wide gap, not this deploy's regression).

### CONDITIONS-SATISFIED TABLE (STANDING PRACTICE — earned by Finding 1)
Prod-go authorization requires this table: each signed condition → implementing commit → **live-probe evidence**. A signed condition rode through verdict/merge/gates unimplemented because nothing traced conditions to commits; the offline gate was structurally blind (routing decisions, never destinations). Three rows make this class of gap impossible to ride through silently again.

| Signed condition | Implementing commit | Live-probe evidence (staging `944939b`) |
|---|---|---|
| **#1** V2 ABSTAIN → Node 3, not freeflow (Cardinal Rule 5) | `fc671bb` (PR #171) | `keyword_rerank_veto → low_confidence_respond` observed in `X-Sage-Node-Path` ✓ |
| **#2** Per-language fail-closed (AR τ absent → V1, no reranker abstain) | Task 6b (in V2 reconcile `202aff5`) | AR turn → `rtl`, `arabic_offer_excluded → skill_executor` (routed via V1 tiers, reranker not applied) ✓ |
| **#3** `semantic_anchors` empty (passive-SI bleed held) | (anchors-empty guard test, `test_skill_schema`) | guard test green on the deploy SHA ✓ |

### PRODUCTION FLIP — VERIFIED ✅ (2026-07-08)

**Tree:** prod `944939b` (the EXACT staging-verified SHA — no-daylight). Deployed v1-first (byte-identical), then flipped `SKILL_ROUTING_V2=1 SKILL_RERANK_ENABLED=1 SKILL_RERANK_PRECISION=fp32 SAGE_BUILD_SHA=944939b`. **Divergence note:** prod's prior tree (`76f339d`) had 4 `item3` **docs-only** commits not in `944939b` (preserved on master, empty code-delta, zero runtime impact); `944939b` contains the veto `bc3cb4b`, so ancestry-not-recency (a *safety*-commit rule) is satisfied.

**Hard gates PASS:** `/health/ready` `routing_mode:"v2"` + `reranker_head_control:"passed"` (fp32 head; headless→503 so 200 is the real check), `/health/version` `build_sha:944939b`, ancestry-contains-veto ✓.

**Acceptance probe (mirror of staging + crisis-invariance) — ALL PASS:**
- in_scope EN → skill offer ✓
- veto-abstain → `keyword_rerank_veto → low_confidence_respond` (the Task-6 fix, live in prod) ✓
- Arabic → `rtl`, `arabic_offer_excluded → skill_executor` (V1 tiers, fail-closed) ✓
- **crisis-invariance** → `node_path = [safety_check, crisis_response]` ONLY (skill_select/reranker never reached), tier T2, `[[CRISIS_DETECTED]]` — Node 1 short-circuits identically under flags-on ✓

**Task 12 (sampled prod measurement):** 3/3 id_oos clinician-territory corpus cases **abstain, 0 routed-to-skill** — the +45pp id_oos win (V1+veto 46.9% → V2 92.2%, driver on `944939b` = prod code) confirmed live end-to-end. Recall tripwire armed: in_scope 52.1% ≥ 51.77% floor.

**ROLLBACK (pre-staged, on-call lever):** set `SKILL_ROUTING_V2=0` + `SKILL_RERANK_ENABLED=0` — the byte-identical guard proves this restores exact V1 behavior with **no redeploy** (a variable write, seconds).

**Latency:** full-turn tail 13–17s = pre-existing LLM-generation cost (prod V1 = 11.68s on the identical turn), not V2 overhead; filed against the north-star <3s p95 KPI. Reranker overhead within the 9.6s bound (abstain probe 7.2s).


## RUNBOOK RULE — the harness mirrors the runtime tiers (earned 2026-07-08, 2nd instance)

Any change to the live routing tiers — a veto added, a tier reordered, a threshold moved — MUST land with its harness/driver mirror in the SAME PR. An instrument that does not track the runtime measures a tree that does not exist. Two instances now: (1) "V1 of record = V1+veto" — the OCD veto shifted flags-off id_oos, so the frozen comparator no longer matched the running tree; (2) the reverdict driver measured the PRE-veto leak until `is_harm_intrusive` was mirrored into `routed_of`. Belongs next to the corpus-in-repo rule.


## Entry 4 — 2026-07-08 · Phase 1 harm-intrusive veto (clinician-approved) + STALE-BUILD lesson

**Tree:** prod + staging `7ed83cf` (harm-intrusive veto merged; SHA verified BEHAVIORALLY, not by /health alone). Clinician-approved 2026-07-08.

**Full-feature regression on prod 7ed83cf (all behaviorally verified):** V2 in_scope→skill; harm-intrusive→`harm_intrusive_veto` (leak closed); OCD→`ocd_compulsion_veto`; reranker-abstain→`keyword_rerank_veto→low_confidence_respond`; Arabic→`arabic_offer_excluded` fail-closed; substance→`clinical_flag_abstain`; crisis→`[safety_check, crisis_response]` T2; parenting-worry→routes (no over-veto). 8/8.

### ⚠️ STALE-BUILD-CACHE lesson (earned again, 2026-07-08) — new runbook rules
The first `railway up 7ed83cf` deployed **SUCCESS / healthy / `/health/version`=7ed83cf** but served **STALE code without the veto** — the harm-intrusive probe routed to a skill (leak still open). Root cause: `railway up` from a local dir leaves the Dockerfile cache-bust `ARG RAILWAY_GIT_COMMIT_SHA=unknown`, so the `COPY . .` layer was reused (Railway/Kaniko quirk); and `SAGE_BUILD_SHA` is an env var I *set*, so `/health/version` reported a tree the container was not running.
- **RULE: `/health/version` SHA is NECESSARY BUT NOT SUFFICIENT.** It can be a set env var, not the running code. A **behavioral probe of the actual change is MANDATORY** on every deploy (the probe pair is what caught this; the green health gate lied).
- **RULE: `railway up` MUST set `RAILWAY_GIT_COMMIT_SHA=<deploy-sha>`** (feeds the Dockerfile cache-bust ARG) so the `COPY` layer rebuilds. Without it, code edits under `src/` can silently not deploy.
- **RULE: do NOT override `SAGE_BUILD_SHA` as a service var** — let it derive from the cache-bust ARG so `/health/version` reflects the BUILT code, not a hand-set label.
- Fix applied: set `RAILWAY_GIT_COMMIT_SHA=7ed83cf`, rebuilt, re-probed → veto fires. Earlier 944939b prod deploy was behaviorally verified at the time (probe pair), so it was not stale.

## Entry 5 — 2026-07-08 · crisis-number templating (single-config) + STALE-BUILD lesson REPEATED

**Tree:** prod advanced `7ed83cf` → `9f5705c` (stale) → **`e34e97f`** (current master: crisis templating #193 + item3 + both vetoes). Crisis `number`/`hours` PO-**verified** (`800 46342` / `24/7`).

**What shipped:** crisis phone numbers templated to ONE config source (`config.CRISIS_CONFIG`), resolved at load, fail-closed boot guard. **Byte-identical mechanism** (resolved output == prior literals).

**Verification — cache-bust-verified, NOT behaviorally.** Because it's byte-identical, the crisis smoke (response resolves `800 46342`, no `{{crisis` leak) CANNOT distinguish templated from literal. So it's verified by the **cache-bust structural guarantee** (`RAILWAY_GIT_COMMIT_SHA 7ed83cf→e34e97f` → `COPY` rebuilt) + the boot guard (app booted → no unresolved placeholder) — not an output probe. Recorded as such, deliberately not as "behaviorally verified."

**⚠️ STALE-BUILD LESSON REPEATED (mine).** First attempt: `railway up` + set `SAGE_BUILD_SHA=9f5705c` **without** bumping the cache-bust ARG → container ran stale `7ed83cf` code under a `9f5705c` label; `/health` lied; the byte-identical smoke gave a **false PASS**. Caught only by reading `RAILWAY_GIT_COMMIT_SHA` (=`7ed83cf`). Fix: bump `RAILWAY_GIT_COMMIT_SHA`→`e34e97f`. This is the **second** stale-build incident this session — the reason for `docs/superpowers/governance/2026-07-08-prod-deploy-control.md`, which adds the sharper rule: **byte-identical changes have no output probe → add a `/health/version` templating-provenance field.**

**Clobbers this session (context):** item3 (`76f339d`) and crisis-templating (`27bfd3b`) were each reverted by **parallel prod deploys**; each resolved by redeploying current master. → the one-writer-to-prod + always-deploy-master control.

## Entry 5 — 2026-07-09 · BA §3a recall fix + crisis-templating (deploy master 7f2b30d)
**Tree:** prod + staging master `7f2b30d` (BA recognition clause 8079caa + crisis-templating 27bfd3b + health-provenance 0fc4b0a). Clinician-signed 2026-07-08; signed gate CLEARED (BA recall 0/7→7/7, id_oos 0.9219 held byte-for-byte, harm-0, per-pathway floor clears; wrong-route +2.6pp = 0 true regressions).
**Prod behaviorally verified:** depression ("lost interest / no motivation") → **behavioral_activation** offer ("small steps plan, pick one small activity"); passive-SI ("what's the point of any of it") → `crisis_response` (NOT BA); crisis → `crisis_response`, clean templated copy (no `{{ }}` leak); `crisis_copy_templated=True`.

### ⚠️ STALE-BUILD RECURRENCE #3 — short-SHA ARG bump can SILENTLY fail to bust
First prod `railway up` set `RAILWAY_GIT_COMMIT_SHA=7f2b30d` (short) — the ARG changed (7ed83cf→7f2b30d) so `/health` label updated to 7f2b30d, but the **COPY layer was still served from cache** → prod ran OLD code (BA veto still fired; `crisis_copy_templated` MISSING). Staging (same short SHA) busted fine — so it's non-deterministic. **Caught by: (a) the behavioral probe (BA still vetoed), and (b) `crisis_copy_templated` absent from `/health`.** Fixed by re-bumping the ARG to the **FULL 40-char SHA** (`7f2b30de0…`) — a genuinely-distinct value Docker can't match to any cached layer → COPY rebuilt → fresh code.
**New rules:** (1) cache-bust with the **FULL SHA** (or a nonce), not the short SHA — short can collide/fail. (2) Gate the deploy poll on a **fresh-code provenance field** (`crisis_copy_templated`), NOT `build_sha` (which is just the ARG label and can lie). (3) The behavioral probe remains mandatory and is what actually caught it. See prod-deploy-control §4.

## Entry 6 — 2026-07-09 · §1e box_breathing recall fix (prod master 7a57107, one-writer)
**Tree:** prod + staging master `7a57107` (§1e box_breathing two-part edit; §6b/§6c assertive HELD). One-writer window claimed; detached origin/master; full-SHA cache-bust (`RAILWAY_GIT_COMMIT_SHA=7a57107fef1b…`, SAGE_BUILD_SHA deleted so /health derives from ARG); fresh-code verified via `crisis_copy_templated=True`.
**Gate (MARGIN FRAMING — new runbook rule, distance-from-floor not pass/fail):** id_oos abstain **0.9219 = +0.0159 above the 0.906 floor** (master baseline, ZERO regression — box_breathing proven innocent of anchor leak by ablation); §1e recall 10/12→box_breathing; harm-domain leaks 0; cluster-gap 0.0526. Clinician-approved wording.
**Prod behaviorally verified (three-probe + regression):** "dreading my presentation tomorrow" → **box breathing** offer (spec §1e offer-first); "I worry about everything" → worry_time (bin-(b) exclusion held); "anxious all week" → empathic clarify, NO breathing offer (§1a-c over-pull guard held — event-anchored wording defeats it, OBSERVED not assumed); BA/§3a → skill offer intact; harm-intrusive → veto intact.
**§6b/§6c: HELD** (mechanism-4 anchor margin cost) → rehome to `interpersonal_effectiveness` (DEARMAN, spec-primary per §6b) pending clinician confirm + its own full gate.
