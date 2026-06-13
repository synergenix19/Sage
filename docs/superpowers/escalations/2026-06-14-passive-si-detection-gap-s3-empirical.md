# SAFETY ESCALATION: passive-SI detection gap — S3 empirically cannot separate SI from distress; OR-fusion recall rests on unmeasured MARBERT

**Date:** 2026-06-14
**Status:** OPEN — CRITICAL. Outranks all routing work. Detection precedes routing.
**Owner:** Clinical lead + safety engineering
**Bears on KPI:** Crisis recall ≥ 95% (passive / veiled SI)
**Ties to:** Intelligence Evaluation **SF-1** (crisis recall gap — MARBERT passive-SI recall never measured)

> **Label disambiguation (read first).** Two separate "SF-x" namespaces exist in this repo and they collide. This doc concerns the **Intelligence Evaluation** namespace: **IE-SF-1** = passive-SI / MARBERT recall gap; **IE-SF-2** = crisis-in-mid-skill. It is NOT the **skill-routing audit** namespace (2026-06-07: Routing-SF-1 = dominant shadower / first-match-wins; Routing-SF-2 = intent-route intensity blindness / dbt_tipp reachability; Routing-SF-3 = worry_time de-confliction). Where this doc says SF-1 it means **IE-SF-1** unless prefixed otherwise.

## One-line for the clinical lead

We now have direct empirical evidence that **S3 (BGE-M3 semantic crisis search) cannot distinguish passive-suicidal-ideation language from ordinary emotional-distress language** in the 0.40–0.69 cosine band. Under Node 1's OR-fusion (S1 OR S2 OR S3), that leaves passive-SI recall resting almost entirely on **S2 (MARBERT)** — which is not in the live fusion path, and whose passive-SI recall (even fine-tuned on TD3) has never been benchmarked. The crisis-recall ≥95% KPI is therefore unverified for the veiled/passive phenotype.

## How this surfaced (new evidence, 2026-06-14)

While evaluating whether `semantic_anchors` (multi-vector Tier-2 routing) could be authored for the three distress-domain skills (grief_loss, financial_anxiety, interpersonal_effectiveness), 31 candidate anchors were authored using every low-bleed framing the authoring conventions prescribe (factual, action-oriented, task-of-mourning, faith-based, boundary-setting) and scored through `scripts/check_anchor_si_boundary.py` (max cosine vs the SF-1 passive-SI probe bank).

**Result: 0 PASS, 0 WARN, 31 BLEED.** Every candidate scored ≥ 0.4593 against passive-SI probes. Distribution:

- High: 0.64–0.69 (grief, provider-role-failure, financial shame)
- Mid: 0.51–0.64 (boundary-setting, kafala constraint, repair conversations)
- Lowest: **0.467** — "My visa is tied to my job, so if I lose the job I lose my right to stay" (the flattest, most factual sentence constructible for this domain) — still above gate.

This is the same model limitation already documented for S3 crisis detection (`safety_check.py:9-17`: "missed passive-SI cluster sits at 0.62–0.72 cosine, overlapping with therapeutic acceptance language — BGE-M3 cannot separate them"). The anchor experiment confirms it from the other direction and extends it across the full distress domain.

## Why this is a true dead end, not a calibration problem

**The bleed is the safety property, not a tuning artifact.** Any Tier-2 threshold loose enough to admit a grief/financial anchor at 0.60–0.69 cosine is, by construction, loose enough to let a passive-SI utterance at the same distance match that same skill in Node 4. You cannot tune a gate that passes these anchors without simultaneously widening the misrouting door (a passive-SI disclosure routing to a coping skill instead of triggering crisis). Per-skill threshold calibration does not rescue this — it trades a content gap for a safety regression. The distress region and the passive-SI region are not separable in BGE-M3's geometry at any operating point that is also useful for routing.

## The OR-fusion decomposition (why recall now concentrates on S2)

Node 1 passive-SI recall = S1 OR S2 OR S3. Taking each detector on the veiled/passive phenotype:

| Detector | Mechanism | Passive-SI capability | Evidence |
|---|---|---|---|
| **S1** | regex lexicon | Blind to veiled/indirect phrasing **by construction** — matches surface tokens, not implied meaning | `crisis_keywords.json`; design |
| **S3** | BGE-M3 semantic | **Empirically cannot separate** SI from distress in 0.40–0.69 band | this doc; `safety_check.py:9-17` |
| **S2** | MARBERT classifier | **Unknown** — not in live fusion path; FT-on-TD3 variant's passive-SI recall never benchmarked | arch doc §3.2 line 197 ("S2 not implemented"); `docs/TD3_audit_results_20260521.md` |

Two of three detectors demonstrably cannot carry the passive-SI phenotype. The third — the only one that plausibly can — is untested for it and not wired in. "Node 1 catches it" is doing load-bearing work that the live detectors cannot do.

## Required action (detection before routing)

1. **Build the passive-SI evaluation set** — EN + Gulf-Arabic veiled phenotypes, covering all three IPTS registers so a one-phenotype-heavy set cannot give false comfort:
   - Perceived burdensomeness ("my family would be better off without me" / provider-role variant)
   - Thwarted belongingness ("no one would notice if I was gone")
   - Hopelessness / purposelessness ("wondering what the point is anymore")
   Source: INQ items for the IPTS construct space; Gulf-context burdensomeness is likely the load-bearing phenotype (provider-role, kafala, family-dependency — see `2026-06-10-node1-crisis-recall-gap.md`).
2. **Measure MARBERT's actual passive-SI recall** against that set (the FT-on-TD3 model). This is the single open question that determines whether the crisis-recall KPI is met for the veiled phenotype.
3. **Decide S2 productionisation** based on (2): if MARBERT recall is adequate, wire it into the live OR-fusion path before pilot exposure; if not, the KPI is not currently meetable by any built component and that is a launch-gating finding.

## Relationship to the anchor decision

Dropping `semantic_anchors` for the three distress skills (logged closed, `2026-06-14-semantic-anchors-distress-skills-closed.md`) removes an active **misrouting** vector and is necessary and correct. **It does not close this detection gap.** The two are separate items. This one outranks the routing backlog because it bears directly on the crisis-recall KPI; the anchor drop is hygiene, this is safety.

## Disposition

OPEN. Assigned to clinical lead + safety. No code change proposed here — the deliverable is the passive-SI eval set and a measured MARBERT recall number. Routing work (Routing-SF-2 / C1) may proceed in parallel since it is independent of detection, but **does not substitute for this** and must not be cited as mitigating it.
