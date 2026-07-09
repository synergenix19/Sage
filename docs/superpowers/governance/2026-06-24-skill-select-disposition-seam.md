# Seam announcement: `skill_select_disposition` on clinical flag definitions

**To: the crisis / safety sprint. From: the V2 routing work. Not a permission ask — a seam announcement.**

## What was added (2026-06-24, branch `feat/v2-calibrated-retrieval-core`)
A new optional field on clinical flag definitions in `src/sage_poc/rules/data/safety/clinical_flag_patterns.json`:

```json
"action": {"type": "clinical_flag", "flag_id": "substance_use", "skill_select_disposition": "abstain"}
```

V2 `skill_select` (behind `SKILL_ROUTING_V2`, default OFF) now **consumes** this field: under flag-on, if Node 1 set a clinical flag whose declared `skill_select_disposition` is `"abstain"`, `skill_select` defers (routes no skill — pure freeflow) instead of routing the turn to a self-help skill, even if it would score above threshold.

## The division of ownership
- **Mechanism (routing layer, ours):** `skill_select` reads the declared field and enforces ABSTAIN. It does **not** decide which flags defer and does **not** detect crisis (acute crisis stays Node 1's, intercepted upstream — BC1).
- **Policy (safety lane, yours):** *which* flags carry `skill_select_disposition: "abstain"` is **yours to declare** on the flag definitions. Add the field to a flag's rule action and V2 routing enforces it automatically — no routing-layer change needed.

## Current state
- **Seeded:** `substance_use → abstain` only — the one **signed** disposition (SBIRT-positive screen → refer, steer to medical, don't coach self-cessation; V2 sign-off package).
- **Undeclared (route as V1 until you sign them):** `trauma_indicator`, `eating_concern`, `medication_mention`. A flag with no `skill_select_disposition` field routes exactly as V1 — the safe default. These are your Batch-2 contraindication territory; declare them here when signed and routing follows.

## Why this message
So you build Batch-2 dispositions **against this field** rather than inventing a parallel flag→routing-disposition structure. The divergence hazard isn't that substance_use is enforced (it's signed) — it's two independently-built mechanisms on the same boundary. The seam exists; you own the policy entries.
