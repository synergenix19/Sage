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

## Sign-off + readiness status (corrected 2026-06-14)

**Crisis-path authorisation is binary and per-value — there is NO "provisional sign-off to
build."** (Earlier framing retired.) The real per-value / per-content sign-offs below are
**OUTSTANDING**. A loose "proceed for now" does not authorise building anything that depends
on an un-signed crisis-path value or un-authored crisis-protocol content, because these
govern a crisis path and do not clear on engineering judgement. Nothing ships, merges, or
pilots until each specific sign-off is obtained and recorded **with name + date**.

**Owners (advisory; the named parties grant, engineering does not):**
- **G1 `acute_net_threshold` + G2 `clinical_priority` order** → clinical lead + crisis-protocol
  accountable owner; record name + date. (`extreme_threshold = 8` is the only value that
  reconciles to an existing signed threshold — `acute_direct_entry ≥ 8` — but still confirm.)
- **05a PMR content + 05c branched flow** → clinical authoring + review.
- **02 passive-SI eval** → clinical (phenotypes/taxonomy) + ML (eval run). **Highest stakes on
  the board** (gates Crisis recall ≥95% KPI), **independent of every branch question here** —
  keep it on its own track; do not let SF-2/C1 plumbing absorb its oxygen.
- **03 keyword SI-audit** → clinical / CMS.

### Fork decision: (a), conditioned — confirmed

**Topology (verified 2026-06-14):** origin/master = `a1a5a1b` (pre-R1 `_best_kw`; no C1 fix; no
`skill_matching` infra). The C1 fix + B.2/B.3/twins live **in PR #12, unmerged** — built on the
`_best_kw` base, **not on master**. R1's `_resolve_entry` + `skill_matching` infra live only on
feat/PR #4. (Prior "C1 lives on master" phrasing was wrong; corrected.)

SF-2 is **safety-net hardening**, not a fix for an active misrouting (Node 1 still fires for
real crisis), so it need not be rushed — which removes the case for the bad options:
- **(b) rejected** — putting crisis routing on the engagement PR couples a safety change to a
  feature timeline/review. Auditable crisis code must not ride a feature PR.
- **(c) rejected for now** — re-speccing against `_best_kw` means authoring + reviewing
  crisis-routing code twice. No double review on a crisis path for a non-emergency.
- **(a) chosen** — let R1/PR #4 merge **on its own merits**, then build SF-2/C1 cleanly on
  `_resolve_entry` + `clinical_priority` (the data-driven design C1 is meant to converge to).

**Condition on (a):** R1 must be on a path to merge in a reasonable window. **Risk flag:** R1
(PR #4) is itself gated on the one-hour English clinician scoring + an approving review, neither
done — so R1 is NOT imminently mergeable. If R1 stalls, **re-raise** SF-2/C1 and reconsider
scope rather than holding the safety-net hostage indefinitely.

**Conscious supersession:** PR #12's `_best_kw` C1 tiebreak is a **deliberate** stopgap that the
data-driven `clinical_priority` version **replaces** when R1 lands — a planned replacement, not
an accident. The bucket-lock test carries forward.

### The remaining engineering blocker (after the base decision)

1. **Architecture base (blocks SF-2 + C1) — RESOLVED to (a):** wait for R1 merge, then build on
   `_resolve_entry` + `clinical_priority`. See condition + risk flag above.

2. **Clinical authoring depth (blocks 05c + 05a).** 05c is **not** a mechanical threshold edit:
   step_policy default-advance follows step-array order, so "extreme→temperature / else→
   paced_breathing" requires authoring the **branched protocol flow** (which step follows which
   in each path) — clinical authoring. 05a (PMR content) likewise. Engineering applies once the
   authored flow + PMR text arrive. `emotional_intensity` IS a valid step_policy signal and
   `extreme_threshold = 8` reconciles with the existing `acute_direct_entry ≥ 8`, so the
   *threshold* is ready; the *flow* is not.

**Net + parallelism:** nothing crisis-path-behavioural ships from engineering until its sign-off
lands (correctly). But the tracks are independent and must run in parallel, not behind the base
decision:
- **05a PMR authoring is the pilot critical path** — required before pilot, clinical-authoring-blocked,
  architecture-independent (a dbt_tipp.json edit that works on master today and survives R1). It waits
  on no engineering decision and no fork — **clinical authoring should start now.** It is the longer pole
  to pilot than the SF-2/C1 base decision.
- **02 passive-SI eval** runs on its own track (highest stakes; gates Crisis recall ≥95%; branch-independent).
- **SF-2/C1** are the only items behind the base decision (a) → R1 merge.
- **Docs decomposed** from the gated crisis code (below) so they merge without waiting on sign-off.

**PR decomposition (this turn):** the C1/B.2/B.3/twins **code** (crisis routing, clinically signed) is
isolated into its own gated PR; the governance/plan/lock-pass **docs** go in a separate PR that merges
now. Docs no longer ride with — or are held hostage by — gated crisis code.

## Cross-references

- 05a/05b/05c detail + the bucket-audit worklist: docs/superpowers/governance/2026-06-13-overwhelm-routing-c1-conflict.md
- SF-1 passive-SI relates to the existing negation-gap / safety-detection-baseline findings.
- LOCK-SF2C1-04 plan: docs/superpowers/plans/2026-06-14-sf2-c1-intensity-routing-plan.md
