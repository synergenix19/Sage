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
