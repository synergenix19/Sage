# ESCALATION — production (V1) iatrogenically mis-routes OCD checking-compulsions to worry/rumination skills

**Date raised:** 2026-07-07 · **To:** clinical lead · **Clock:** 24h (same discipline as the #139 escalation) · **From:** engineering (command session), surfaced by the Task-5 harm-gate measurement.
**Severity:** production clinical-safety incident — live iatrogenic harm pattern in a clinical-adjacent system. **This is owed regardless of the V2 decision.**

## Finding

The Task-5 harm gate — run by the validated real-model routing driver on the committed corpus (`5e6b86e`), flags-OFF = the routing prod runs today — found that **production V1 routes 6 of 9 iatrogenic OCD-compulsion cases to skills, instead of abstaining to a safe terminal:**

- **`worry_time` ×3, `cbt_thought_record` ×2, `grounding_5_4_3_2_1` ×1** (the 3 that correctly abstain/refer are the remainder).
- All 9 are `harm_severity: iatrogenic` — OCD checking-compulsions / intrusive thoughts. Example: *"I keep getting horrible thoughts I might've left the stove on, so I check…"* → `worry_time`.

## Why this is iatrogenic (not a routing nicety)

Worry/rumination tools **reinforce** compulsions — engaging a checking-compulsion with `worry_time` or `grounding` can entrench the very loop it should interrupt. **The BOT BEHAVIOUR spec already says so:** the Worry Loops/Rumination category flags OCD-type markers ("I have to check," "I need reassurance," compulsive checking) → **route to professional referral, NOT the Worry Tree/Worry Time**, which "can reinforce compulsive patterns." **Production is currently violating the spec's own OCD guard.**

## The ask (24h)

1. **Confirm** the iatrogenic-risk assessment (OCD compulsion → worry/rumination skill).
2. **Approve the deterministic safety fix (drafted below) as an expedited hotfix to production V1** — it is arm-independent and cuts live patient-facing risk today; it must not wait on the V2 timeline.

## Fix (DRAFT for clinician approval — engineering drafts, clinician owns the content)

Root cause is content-layer: `worry_time`'s `target_presentations` / veto surface does not distinguish **checking-compulsions** from ordinary worry. Two-part remedy, both clinician-owned (CMS discipline), expedited under this finding:

1. **Deterministic Node-4 veto (Rules Service).** A checking-compulsion pattern set → **suppress** routing to `worry_time` / `cbt_thought_record` / `grounding_5_4_3_2_1` and **ABSTAIN to Node 3** (professional-referral / clarification). Candidate patterns (clinician to confirm/extend): *check the stove/lock/door/oven/appliance*, *keep checking*, *have to check … times*, *left the … on so I check*, *need to make sure … (repeatedly)*, *can't stop checking*. Deterministic, so it is auditable and arm-independent — no LLM, no probabilistic gate.
2. **`target_presentations` correction.** Remove checking-compulsion phrasings from `worry_time`'s match surface so it stops attracting these disclosures in the first place.

## Relationship to V2 (context, not a dependency)

V2's reranker-ABSTAIN gate already catches **5 of these 6** (harm leaks 6→1 under V2). But **this fix lands on V1 prod now, independently** — the deterministic veto is the correct primary control, V2 is a defense-in-depth improvement, and prod cannot hold patient-facing iatrogenic risk hostage to the V2 decision. After the fix: **re-measure the harm gate on both arms** with the same driver/corpus; target is 0 leaks on both.

## Provenance

Measured by `real_model_driver.py` @ tree `69ded58`, fixtures `5e6b86e`, flags-off (V1). Full 9-case list attached separately (being compiled from the run). Cross-ref: `2026-07-07-v1-comparator-correction.md` (the harm gate ran alongside the Task-5 flip gate).
