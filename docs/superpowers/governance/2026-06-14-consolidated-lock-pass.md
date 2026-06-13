# Consolidated lock pass — acute routing + safety (2026-06-14)

Decisions relayed from clinical + architecture, validated against the DBT evidence base.
Canonical record; owners and status per item. Engineering owns only LOCK-SF2C1-04 (plan).

| ID | Bucket | Decision | Status | Owner |
|----|--------|----------|--------|-------|
| LOCK-ANCHORS-01 | Semantic anchors for grief_loss / financial_anxiety / interpersonal_effectiveness | **DROP** — no anchors authored; any gate loose enough to pass distress anchors widens passive-SI misrouting (BGE-M3 geometry, model-imposed, not a content gap; v7 §4.3 rules-first MVP) | **CLOSED** | architecture (closed) / clinical (informed) |
| LOCK-SF1-02 | Passive-SI recall gap in Node 1 S3 (BGE-M3 blind to veiled SI) | **ESCALATE** as formal safety item: build passive-SI eval set (EN + Gulf-AR veiled phenotypes); measure MARBERT (S2) actual recall against it. S1 (regex) + S3 (BGE-M3) both demonstrably miss passive SI; recall concentrates on S2 alone, untested = Intelligence-Eval SF-1 (CRITICAL) | **OPEN — HIGH** (gates Crisis recall ≥95% KPI) | clinical + ML eval |
| LOCK-KWAUDIT-03 | Tier-1 keyword lists, three distress skills | Clinician audit for SI-overlap; any veiled-SI-ambiguous phrase routes to **safety, not skill**. Precondition for declaring keywords-only safe here | **OPEN — scheduled, low effort** | clinical (CMS) |
| LOCK-SF2C1-04 | Routing off brittle signals | **APPROVED TO PLAN.** SF-2 (intent-route intensity → dbt_tipp reachable on acute intent) + C1 (clinical-priority override). Disambiguate this "SF-2" from Intelligence-Eval SF-2 (crisis-in-mid-skill) | **OPEN — plan authored** (docs/superpowers/plans/2026-06-14-sf2-c1-intensity-routing-plan.md) | architecture (plan) / clinical (sign-off) |
| LOCK-TIPP16-05a | dbt_tipp missing PMR (second P) | **ADD PMR step.** Required before pilot. Lowest-risk component (no cardiac/ED contraindication); restores full TIPP fidelity (T-I-P-**P**); serves as low-arousal closer + safe default entry. Not a design change — fidelity restoration | **OPEN** — clinical authoring (goal/technique/tone/few_shot/completion_criteria + transitions); engineering applies mechanically | clinical (authoring) / engineering (apply) |
| LOCK-TIPP16-05b | dbt_tipp entry_screen gate | **CONFIRMED SUFFICIENT** as primary control for pilot. Aligned with Linehan cautions + dive-reflex literature (cardiac, beta-blocker/low-HR, cold allergy, eating-disorder electrolyte risk; dive response individually unpredictable, rare arrhythmia). Item 4 "screen before cold water" satisfied | **CLOSED for pilot** / instrument (05d) | clinical (confirmed) |
| LOCK-TIPP16-05c | dbt_tipp step order ("reorder" request) | **SUPERSEDE static reorder** with a `step_policy` entry-branch on `emotional_intensity` + gate state: contraindication→redirect (exists); extreme→temperature (gate cleared cold-water risk; fastest interrupt); else→paced_breathing/PMR (low-risk default). Static reorder is **not** a pilot blocker. Preferred for pilot if authoring allows; else keep temperature-first + gate for pilot, branch for GA. step_policy JSON, **no graph change** | **OPEN** — folded into the LOCK-SF2C1-04 plan | clinical (authoring) / engineering (apply) |
| LOCK-TIPP16-05d | Gate reliability (the clinical learning) | **Instrument pilot** — gate completion/skip rates + self-report accuracy under acute arousal. Self-report contraindication screening of a user in acute distress is a known weak point; "the gate exists" does not close the loop. If reliability poor → low-risk-default entry becomes the conservative GA stance | **OPEN** — pilot instrumentation | clinical + analytics |

## The clinical learning handed back (what the clinicians asked us for)

The open question is **not** the step order — it is the **reliability of a self-report
contraindication screen administered to a user in acute distress**, a known weak point.
Cold-water TIPP is a sensory-shock intervention with an individually-unpredictable cardiac
response, delivered unsupervised — that combination is why the screen-plus-low-risk-default
posture is worth *validating in pilot* rather than *assuming*. 05d is that validation.

## Cross-references

- 05a/05b/05c detail + the bucket-audit worklist: docs/superpowers/governance/2026-06-13-overwhelm-routing-c1-conflict.md
- SF-1 passive-SI relates to the existing negation-gap / safety-detection-baseline findings.
- LOCK-SF2C1-04 plan: docs/superpowers/plans/2026-06-14-sf2-c1-intensity-routing-plan.md
