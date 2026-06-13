# Decision record: semantic_anchors dropped for grief_loss, financial_anxiety, interpersonal_effectiveness — CLOSED

**Date:** 2026-06-14
**Status:** CLOSED. Approved by product/architecture owner 2026-06-14.
**Type:** Architecture decision (within v7), not a deviation.
**Related:** safety escalation `2026-06-14-passive-si-detection-gap-s3-empirical.md`; plan `2026-06-09-semantic-routing-production-architecture.md` (Task 5); `SKILL_AUTHORING_CONVENTIONS.md §semantic_anchors`

## Decision

No `semantic_anchors` will be authored or submitted for **grief_loss**, **financial_anxiety**, or **interpersonal_effectiveness**. These three skills route via **Tier 1 keywords + Node 1 safety + freeflow**. The Task-5 anchor workstream for these skills is closed.

## Why — empirical, not an authoring failure

31 candidate anchors were authored across the three skills using every low-bleed framing the conventions prescribe and scored through `scripts/check_anchor_si_boundary.py`: **0 PASS, 0 WARN, 31 BLEED** (range 0.467–0.692 vs the passive-SI probe bank; even the flattest factual sentence cleared the gate). Full evidence and root-cause in the linked safety escalation.

The root cause is **BGE-M3 embedding geometry**: fluent distress-domain language is inseparable from passive-SI language in this model's space. The sharper statement of why this is a true dead end rather than a calibration problem: **the bleed is the safety property.** Any threshold loose enough to admit a 0.60 grief anchor is loose enough to admit a 0.60 passive-SI utterance into the same Node-4 skill. Calibration cannot separate them; it only trades a content gap for a safety regression.

## Why this is inside the architecture, not a deviation

v7 **§4.3** designates **rule-based matching as the MVP approach for `skill_select`**, with embeddings as fallback, and explicitly defers **semantic-primary matching to Full Build (50+ skills)**. Dropping anchors for these three skills keeps `skill_select` on its v7-designated MVP path. **No deviation flag required.**

The multi-vector machinery (schema field + max-over-anchors + cluster argmax, commits `fdf1e39` / `711358f`) remains in place and dormant for these skills. It is available for non-SI-adjacent confusable skills if a real, observed confusion ever justifies it — see "deferred" below.

## Scope boundary (important)

Closing the anchor workstream removes an active **misrouting** vector. It does **not** close the passive-SI **detection** gap — that is a separate, higher-priority safety item (linked escalation). Do not let this closure read as "Node 1 handles it," because two of Node 1's three detectors (S1 regex, S3 BGE-M3) demonstrably cannot carry the passive-SI phenotype.

## Follow-up action (bounded, sign-off-ready): Tier 1 keyword SI-overlap audit

Before "keywords-only" is declared safe for these three, the Tier 1 lists must be clinician-audited so that no keyword does double duty as veiled SI (a phrase that should route to safety review, not silently to a skill). Engineering pre-screen of the current lists:

**grief_loss — FLAG for clinician review (vague-distress / void-adjacent, not grief-specific):**
- `hollowed out` — emptiness/void register; closest to SI-adjacent
- `eating me up` — generic consuming-distress; not grief-specific
- `أتعب من الحزن` ("tired of the grief") — "tired" edges toward exhaustion-with-life; confirm it reads as scoped-to-grief
- `keep expecting them to` — repetitive-thought construction (lower concern, note only)

**interpersonal_effectiveness — low risk.** Keywords are relationship-mechanics (DEAR MAN, boundaries, conflict). `تعب من الخلافات` ("tired of the conflicts") is scoped. No flags; confirm in audit.

**financial_anxiety — low risk.** Keywords are financial-scoped (kafala, remittance, provider role, debt). `can't afford to fail` / `can't make ends meet` are financial-bounded. No flags; confirm in audit.

Disposition of any flagged phrase: if a clinician judges it carries veiled-SI load, it is **removed from the skill's `target_presentations`** (so it cannot route to a coping skill) and, if appropriate, **added to the Node 1 passive-SI pattern set** instead. This is content-change governance — route through the normal sign-off.

## Answers logged

- "Create anchors I can take to clinicians" → **no submittable anchors exist** for these skills; submitting bleeding anchors is against process. Closed, not deferred.
- "Would semantic anchors simplify our matching?" → not for these distress skills (model-imposed); the simplification story for them is keyword fast-path + freeflow.

## Deferred (do not action now)

Scoping non-distress confusable skill pairs for anchors is **deferred** unless a specific, observed misrouting in the current skill set justifies it. Anchors only pay off for non-SI-adjacent skills and even there trade keyword maintenance for threshold-calibration maintenance — not worth a speculative pass pre-Gitex.
