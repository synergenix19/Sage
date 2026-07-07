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
