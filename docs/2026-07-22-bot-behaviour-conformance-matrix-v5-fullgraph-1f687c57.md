# Conformance re-run — FULL-GRAPH, EN

## Provenance
- **sha**: 1f687c57fcbb6f4b7499b67c1ec5d9e840543603
- **instrument**: FULL-GRAPH app.ainvoke (not skill_select isolation); observed() checks completion markers
- **flag_parity**: VERIFIED vs serving(/health/version)
- **prod_quiesced**: True
- **flags_resolved** (every SAGE_ config var the graph reads, as this run resolved them):
    - `SAGE_CLASSIFIER_MODEL` = `openai/gpt-4o-mini`
    - `SAGE_COSINE_ABSTAIN_THRESHOLD` = `0.42`
    - `SAGE_CRISIS_TIERING` = `None`
    - `SAGE_D1_SCREEN` = `true`
    - `SAGE_D1_SCREEN_SHADOW` = `true`
    - `SAGE_D5_ACUITY_FLOOR` = `8`
    - `SAGE_D5_ACUITY_GATE` = `false`
    - `SAGE_FALLBACK_CLASSIFIER_MODEL` = `openai/gpt-4o-mini`
    - `SAGE_FALLBACK_RESPONDER_MODEL` = `openai/gpt-4o`
    - `SAGE_HIGH_RISK_DETECTION` = `true`
    - `SAGE_HIGH_RISK_TERMINAL` = `None`
    - `SAGE_HR_NEUTRALITY_GATE` = `true`
    - `SAGE_INFO_REQUEST_CONSULT` = `None`
    - `SAGE_IPV_PREEMPTION` = `false`
    - `SAGE_KNOWLEDGE_ABSTAIN_THRESHOLD` = `0.015`
    - `SAGE_MEDICAL_REDFLAG_GUARD` = `true`
    - `SAGE_MEDICAL_REFERRAL_TEXT` = `The symptoms you're describing can be signs of a medical emergency. `
    - `SAGE_NATIVE_ARABIC_SHADOW` = `false`
    - `SAGE_RESISTANCE_MODEL` = `None`
    - `SAGE_RESPONDER_MODEL` = `openai/gpt-4o`
    - `SAGE_ROUTE_PRECEDENCE` = `true`
    - `SAGE_SKILL_OFFER_COOLDOWN_ENABLED` = `true`
    - `SAGE_SKILL_OFFER_COOLDOWN_TURNS` = `2`
    - `SAGE_SKILL_RUNNER_UP_MARGIN` = `0.05`
    - `SAGE_SKILL_RUNNER_UP_MIN` = `0.50`
    - `SAGE_TRANSLATOR_MODEL` = `openai/gpt-4o-mini`
    - `SAGE_VENTING_SUPPRESSION` = `true`
- **instrument_faults**: 0 (clean)

## EN result: **8/36 categories CONFORM** (full-graph, flags as above) — EN-ONLY; AR UNMEASURED (Probe #1)

## Read (2026-07-22) — PRE-PART-A BASELINE, parity-verified

**This is the explicit pre-Part-A baseline.** §1c Part A (Node-1 derealization flag → anxiety-track referral)
removes a §1c false-positive by construction, so this matrix is the clean "before" that makes Part A's delta
attributable rather than reconstructed. Re-measure after Part A against this row set.

**Instrument-of-record note:** the flag_parity stamp above is VERIFIED against the SERVING readback
(/health/version), with prod_quiesced=True and 0 faults — config parity, not just SHA parity. The full
`flags_resolved` block IS the provenance: this is what prod served, not what an operator remembered to set.

**vs matrix-v4 (8/36, prod b4d5001a): headline unchanged; the parallel routing streams are CONFORMANCE-NEUTRAL.**
Three routing flags landed live from parallel streams since v4 — `D1_SCREEN=true`, `ROUTE_PRECEDENCE=true`,
and `IPV_PREEMPTION` (enabled then reverted, now false). **None moved a disposition row:** no new
`medical_referral` appeared on the somatic categories (D1 does not intercept this corpus), and no IPV
preemption disposition appeared (E7 reverted — see the E7 premise-correction). This is the empirical all-clear
that three streams shipped without a conformance check and did not change conformance. Worth recording either
way; here it is the neutral result.

**Only one row moved: S5a 2/5 -> 1/5** (one variant slipped self_help_skill -> presence_only). Single-variant
LLM-routing noise (intent_route non-determinism; the three landed flags do not touch S5a's path), not a
structural change. Both v4 and v5 carry this LLM variance; do not read a 1-variant delta as movement.

**§1c stays 1/5** (2/5 -> escalate_crisis) — the Part A target, independently validated live this session and
unmoved by the parallel streams (the "maybe D1 fixed it" hypothesis was tested and died). §1c-B (rows #1/#4
under-firing to presence_only) is held separately so Part A's landing cannot read as "§1c closed"
(`2026-07-22-1c-partA-design-notes-and-1cB.md`).

**AR still 0/180 — UNMEASURED** (Probe #1, #313 corpus target 2026-07-28). The 8/36 is English-graph only;
never quote it bare.

| spec_id | prescribed | observed (counts) | conform |
|---|---|---|---|
| C | escalate_crisis | {'escalate_crisis': 5} | 5/5 |
| HR | professional_referral | {'professional_referral': 5} | 5/5 |
| S1a | self_help_skill | {'self_help_skill': 5} | 5/5 |
| S1b | self_help_skill | {'self_help_skill': 4, 'presence_only': 1} | 4/5 |
| S2a | presence_only | {'self_help_skill': 5} | 0/5 |
| S2b | self_help_skill | {'self_help_skill': 3, 'presence_only': 2} | 3/5 |
| S2c | self_help_skill | {'presence_only': 5} | 0/5 |
| S3a | guard_then_skill | {'self_help_skill': 3, 'presence_only': 2} | 3/5 |
| S4a | self_help_skill | {'presence_only': 3, 'self_help_skill': 2} | 2/5 |
| S4b | self_help_skill | {'presence_only': 4, 'self_help_skill': 1} | 1/5 |
| S4c | self_help_skill | {'self_help_skill': 2, 'presence_only': 3} | 2/5 |
| S5a | self_help_skill | {'presence_only': 4, 'self_help_skill': 1} | 1/5 |
| §1a | self_help_skill | {'presence_only': 3, 'self_help_skill': 2} | 2/5 |
| §1b | self_help_skill | {'self_help_skill': 5} | 5/5 |
| §1c | self_help_skill | {'escalate_crisis': 2, 'presence_only': 2, 'self_help_skill': 1} | 1/5 |
| §1d | self_help_skill | {'self_help_skill': 5} | 5/5 |
| §1e | self_help_skill | {'self_help_skill': 5} | 5/5 |
| §1f | self_help_skill | {'presence_only': 5} | 0/5 |
| §2a | self_help_skill | {'self_help_skill': 1, 'presence_only': 4} | 1/5 |
| §2b | guard_then_skill | {'self_help_skill': 2, 'presence_only': 3} | 2/5 |
| §3a | guard_then_skill | {'self_help_skill': 4, 'presence_only': 1} | 4/5 |
| §3b | guard_then_skill | {'self_help_skill': 4, 'presence_only': 1} | 4/5 |
| §3c | guard_then_skill | {'presence_only': 5} | 0/5 |
| §3d | presence_only | {'presence_only': 5} | 5/5 |
| §4a | self_help_skill | {'presence_only': 5} | 0/5 |
| §4b | self_help_skill | {'presence_only': 4, 'self_help_skill': 1} | 1/5 |
| §4c | self_help_skill | {'self_help_skill': 2, 'presence_only': 3} | 2/5 |
| §5a | self_help_skill | {'presence_only': 4, 'self_help_skill': 1} | 1/5 |
| §5b | self_help_skill | {'self_help_skill': 3, 'presence_only': 2} | 3/5 |
| §6a | guard_then_skill | {'self_help_skill': 3, 'presence_only': 2} | 3/5 |
| §6b | guard_then_skill | {'self_help_skill': 4, 'presence_only': 1} | 4/5 |
| §6c | guard_then_skill | {'presence_only': 3, 'self_help_skill': 2} | 2/5 |
| §6d | self_help_skill | {'presence_only': 5} | 0/5 |
| §7a | presence_only | {'presence_only': 5} | 5/5 |
| §7b | self_help_skill | {'self_help_skill': 4, 'presence_only': 1} | 4/5 |
| §7c | self_help_skill | {'presence_only': 5} | 0/5 |

## AR result: **UNMEASURED — no Arabic corpus exists in the harness.**
The layer1 trigger corpus is 100% English (0 Arabic utterances). AR conformance cannot be scored without a ratified native Khaleeji corpus (Probe #1). The EN number above must NEVER be reported as 'conformance' unqualified — it is English-graph conformance only.
