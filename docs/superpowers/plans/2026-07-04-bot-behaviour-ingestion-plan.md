# BOT BEHAVIOUR — Ingestion & Build Sequencing Plan

**Status:** DRAFT (sections added one per review turn, Phase-2 discipline).
**Companions:** `../governance/2026-07-04-extensions-e1-e7-approval.md` (the signable mechanism anchor) · `../specs/2026-07-04-crisis-hr-protocol-conversion.md` (§C/§HR content map).
**Branch:** `feat/bot-behaviour-safety-protocols`.

---

## §0 — How to read this plan (gating header)

> **No build step in this plan is authorized until (a) its extension entry is signed and (b) its stated preconditions are met. This document sequences; it does not approve.**

This plan orders work and shows dependencies. It confers no authorization. A step's appearance here — including its estimated position in the sequence — is not permission to start it; the step's own gate markers govern that, and they are repeated on every step on purpose, because this document will be read by people who skip headers.

**Marker legend (used on every step):**
| Marker | Meaning |
|---|---|
| 🔒 `E#` | Blocked until that extension entry is **signed** (PO mechanism + clinical lead where the entry requires it). |
| ⛔ `<precondition>` | Blocked until a named non-signature gate clears — a recall ≥95% gate, the helpline dial-test + L0 re-sign, or the §4.5 precedence ratification. |
| 🟢 | **Non-blocked — authorized now.** No signature, no precondition. |

A step may carry more than one marker; it is unblocked only when **all** clear. The complete signature/precondition → unlock mapping is the matrix in §6.

---

## §1 — Critical path & dependency map

**The pilot's critical path is GL-0 crisis recall, not this plan.** Production crisis recall is ~37% (CRADLE) / 18% (self-harm) / 88.9% (S3 passive-SI CPU path) against a **≥95% fail-closed bar**. GL-0 is a NO-GO for external users that **no signature waives**; it requires S2/MARBERT + a validated bilingual eval. Everything sequenced below is downstream of, or parallel to, that reality — the days that matter are spent on GL-0, not on paperwork or plan revisions.

**This plan is deliberately off the critical path.** It is a sequencing artifact drafted in parallel with the signature loop so that the moment signatures land (and GL-0 clears), the build order is already settled. If signing amends E4's per-class gates or the §4.5 precedence order — the two items the approval record flags as clinical decisions to ratify — a sequencing doc is cheap to revise; signatures landing with no plan ready is not.

**The one measurement pipeline, four gates.** GL-0 and the three safety-route recall gates (E3 medical, E4 HR, E7 IPV) all measure the same *kind* of thing — deterministic recall against positive/negative fixtures with an Arabic obligation. They **reuse one fixture harness (§3)**, not four parallel efforts. This makes fixture-set authoring (§2) the single highest-value non-blocked item: the trigger tables become fixture files this week and **feed GL-0 directly**, independent of when the harness or any signature lands.

**Two external dependencies, surfaced here so neither is discovered mid-build:**
1. **§4.5 precedence-order ratification (clinical).** The order `crisis > medical > HR > IPV > tier/category` is a clinical decision the record explicitly defers to sign-off. It **unlocks Phase-B routing-order finalization** — the routes can be built independently, but the order they resolve multi-hits in is not frozen until this ratifies.
2. **Gap #65 semantic-tier decision.** Flag detection is keyword-only today; naturalistic disclosures are known to slip it (E4 psychosis/mania/dissociation, E7 coercive control). This decision **bounds the feasible ceiling of the E4/E7 keyword-only recall gates** — if keywords can't reach ≥95% on naturalistic phrasing, those gates need a semantic/MARBERT tier (the same escalation crisis takes from S1→S2). It must be answered before E4/E7 recall targets are treated as achievable-as-specified.

**Dependency map:**
```
        ┌─────────────────────── NON-BLOCKED LANE (§2) — starts now ───────────────────────┐
        │  Appendix-A content/config   ·   fixture-set authoring   ·   staged helpline payload │
        └───────────────────────────────────────┬───────────────────────────────────────────┘
                                                 │ fixtures feed
                                                 ▼
                              ┌──────────────  GL-0 recall harness (§3)  ──────────────┐
                              │        one measurement pipeline · Arabic obligation       │
                              └───────┬───────────────┬───────────────┬─────────────────┘
                    ≥95% gate consumers │               │               │
                                        ▼               ▼               ▼
   GL-0 crisis recall (critical path)  E3 gate         E4 gate         E7 gate
        │  (S2/MARBERT, bilingual eval)  │               │               │
        │                                └──── 🔒 signatures + ⛔ gates ───┘
        ▼                                                 │
   §C detection half (Phase A) ────────────────┐          ▼
   §C content half ── ⛔ dial-test + L0 re-sign │   Phase B routes ── ⛔ §4.5 ratification · Gap #65 ceiling
                                                └──────────┬──────────┘
                                                           ▼
                                              Phase C (E1) ──► Phase D (E2)
```

*(§2 non-blocked lane · §3 shared harness · §4 sequenced phases · §5 external-dependency tracking · §6 sign-off→unlock matrix follow.)*

---

## §2 — The non-blocked lane (start this week)

Three workstreams need **no extension signature** and can proceed now. A plan that shows everything frozen understates what is legitimately startable.

**§2.1 — Appendix-A content/config. 🟢**
The two former-candidate items resolved as content (approval record Appendix A): the **offload intent-taxonomy label** and the **skill-suggestion-suppression rule** for §3d "just needs to offload." Both are Rules Service / content edits, no mechanism, no signature. (Diagnosis-refusal needs no work — already covered by L0 + `scope_refusal`.)

**§2.2 — Fixture-set authoring. 🟢 — the single highest-value non-blocked item.**
Pure test data, derived directly from tables the clinician has **already authored in the spec**, so it is genuinely startable now — and it feeds GL-0 directly (see §3). Sources named per gate so this is real work, not a placeholder:

| Gate | Positive fixtures (must fire) | Negative fixtures (must NOT fire) |
|---|---|---|
| **§C crisis** (→ GL-0) | canonical trigger table, all 8 rows (direct SI, passive ideation, burden, can't-continue, hopelessness, wanting-pain-to-stop, self-harm, loss-of-self-trust) | existing false-positive exclusions; idiomatic non-crisis |
| **E3 medical** | §1 universal red-flag descriptors (pressure/heaviness, crushing/stabbing/searing, spreading to arm/jaw/back, one-sided numbness/weakness) + cross-category medical-guard phrases | Mild/Moderate chest-and-breathing tables ("chest feels a little tight," anxious shallow breathing, panic racing heart) |
| **E4 HR** | §HR psychosis / mania / dissociation phrase lists | neighbouring §3a low-mood ("I feel numb," "nothing feels real"), §4a can't-name-the-feeling, positive-mood excitement ("so much energy today") |
| **E7 IPV** | expanded coercive-control set (surveillance/monitoring, financial control, fear-of-reaction) + existing `domestic_situation` keywords | ordinary relationship conflict ("husband and I keep arguing," "mother-in-law criticizes everything"), workplace-"controlling" ("my boss is controlling") |

Each set is English-first now; the Arabic (Khaleeji / MSA / Arabizi) equivalents are the tracked debt (§5), authored in parallel and required before any gate is production-satisfied. **These files are the content input the §3 harness consumes — authoring them is NOT blocked on the harness being built** (they are version-controlled first; the runner reads them when it exists).

**§2.3 — Staged helpline commit-2 payload. ⛔ dial-test + L0 re-sign (payload already authored).**
The corrected copy (800-HOPE / 800 4673 / 8am–8pm + tiered 999/SAKINA/DHA/Sharjah + off-hours re-anchor) is already staged in the conversion doc. Preparing the full edit set (9 source files + ~15 test assertions) is authorable, but under the GL-1 product-owner deferral it **ships only on your dial-test + L0 re-sign** — it is in this lane because no *extension signature* gates it, not because it is unconditionally startable.

---

## §3 — Shared recall-measurement harness (one pipeline, four gates)

**One runner, not four.** GL-0 and the three safety-route recall gates (E3/E4/E7) all measure the same kind of thing — deterministic recall on positive fixtures, precision against negatives, with an Arabic obligation. They share **one fixture-driven measurement runner** — the machinery already being built for GL-0 crisis recall (the CRADLE / S3 recall harness), extended to additional fixture sets — rather than four parallel recall efforts.

**Consumers:**
| Gate | Fixture set (from §2.2) | Bar |
|---|---|---|
| GL-0 | §C crisis positives/negatives | ≥95% recall (critical path) |
| E3 | medical positives/negatives | ≥95% recall; precision at clinician tolerance |
| E4 | HR positives/negatives (per class) | ≥95% recall per class |
| E7 | IPV positives/negatives | ≥95% recall; precision at clinician tolerance |

**Fixture→harness relationship (refinement #1, made explicit):** the harness *consumes* the §2.2 fixture files; it is not a precondition for authoring them. Fixtures land first as versioned data; the runner reads whatever is present. So fixture authoring proceeds this week even though the harness extension is a later step.

**The one design constraint (drift-prevention).** **Fixture files are clinician-editable content** — same CMS-adjacent governance as the lexicons (Cardinal Rule 2/4 territory): a clinician can add or move a trigger phrase without an engineering change. **The harness *runner* is engineering-owned code.** The measurement pipeline must never become a place where trigger phrases get hardcoded into Python — the same drift-prevention the E1 entry made for tier thresholds. Phrases live in data; the runner lives in code; the two never merge.

**Gating.** The harness runner itself is 🟢 (measurement infrastructure — engineering, no clinical signature). What a *passing* gate (≥95%) unblocks is the activation of the corresponding safety route (§4); building the runner and authoring fixtures are not themselves gated.

## §4 — Sequenced build phases

> Reminder (per §0): no step below is authorized until its markers clear. Each phase lists **entry criteria** (what must be signed/true to start), **exit criteria** (what must be demonstrably true to be done — a phase-gated plan without exit criteria degrades into signature-checking), and a **demonstrable outcome** (what a stakeholder sees working — one of the POC demonstrables).

### Phase A — §C crisis conversion (existing infra; no extension signature)

§C rides existing `crisis_response` + `crisis_tier`, so Phase A carries **no 🔒** — only two *distinct* preconditions on two *distinct* halves:
- **A1 — detection-recall half. ⛔ GL-0 ≥95%.** Convert the 8-row canonical trigger table into `crisis_keywords` / `passive_si_patterns` fixtures + recall (the §2.2 §C set); this is GL-0 itself, needing S2/MARBERT + bilingual eval. The hardest work; the critical path.
- **A2 — content half. ⛔ dial-test + L0 re-sign.** The staged commit-2 payload: tiered resource set, 999-lead branching, behavioral guardrails. **Independent of A1** — it is blocked on the dial-test, *not* on the recall milestone, and must not be shown as waiting on GL-0.
- (§HR conversion is realized in Phase B via E4 — not duplicated here.)

**Exit:** S1/S3 fixtures pass ≥95% on the §C set (A1); crisis reply emits the corrected, correctly-labelled tiered resources with 999-lead branching (A2).
**Demonstrable:** a crisis disclosure yields the right resources — 999-led when there's immediate-danger language, else the national line — with accurate hours.

### Phase B — new safety routes (precedence-wired first)

The three routes are signature-independent but **contend for the same substrate** (Node-1 evaluation + the §4.5 chain), so precedence is wired once, first:

- **B0 — precedence wiring. ⛔ clinical ratification of the §4.5 order** (`crisis > medical > HR > IPV > tier/category`). One change establishing deterministic evaluation order with **all fired flags written to state + audit**. The three routes then land behind it **in any order** as their own gates clear — preventing three PRs from each independently touching route-ordering logic.
- **B1 — E3 medical. 🔒 E3 · ⛔ E3 recall ≥95% (dual-fixture).** On the `f3-f4-tipp-clinical-gated` deterministic-contraindication contract.
- **B2 — E4 HR (§HR). 🔒 E4**, then split like Phase A:
  - *E4-shape (proceeds once E4 signed):* the §HR step shape (distress-rating-first, standardized message, escalate-by-distress) restructured on `psychotic_referral` — **psychosis rides the live route**, so this signed work moves immediately.
  - *E4-detect (waits):* mania + dissociation detection — **⛔ per-class recall gates + the Gap #65 semantic-tier ceiling answer.** Gated work waits while signed shape-work lands.
  - *E4-activation:* the CF-006 three-part motion (skill sign-off + CF-006 approval + safety suite green, together).
- **B3 — E7 IPV. 🔒 E7 · ⛔ E7 recall ≥95%.** Formalize the `coaching_confrontation` contraindication class on the §6 skills; scoped pre-emption (grounding/offload/sleep stay available).

**Exit:** precedence resolves multi-hit deterministically with all flags audited (B0); each route fires on positives, holds on its negatives at ≥95% recall, and defers correctly to higher-precedence routes; **anxiety §F "silently divert to crisis" is testable end-to-end** (this is also Phase C's entry condition).
**Demonstrable:** "crushing pain spreading to my arm" screens up to medical referral, while "my chest feels a little tight" proceeds to box breathing — and a psychosis disclosure gets the one-question distress → neutral referral, never a coping skill.

### Phase C — E1 supervisor + `care_pathway`

- **Entry: 🔒 E1 · ⛔ Phase B exit.** Per E1's own dependency text, tiering rides *on top of* the safety routes — the universal overrides must be functioning (§F silent-divert live, precedence deterministic) before a tier transition can be trusted to defer to them. **Phase B exit = Phase C entry.**
- Steps: the `care_pathway` state channel (tier, cleared_screens, tried_skills, loop counters) + the `switch_skill` executor action + the deterministic supervisor (tier classification, step-up/down, ceiling).

**Exit:** a step-up switches to a different skill without re-running a cleared screen; step-down requires user assent; `consecutive_no_improvement=2` triggers step-up; ceiling routes to human support; a crisis/medical/HR/IPV hit still preempts any transition.
**Demonstrable:** a user moving Mild→High mid-conversation gets TIPP offered directly, with the already-cleared medical screen carried forward (no re-screen).

### Phase D — E2 category grouping

- **Entry: 🔒 E2 · ⛔ Phase C exit.** E2's metadata drives transitions over E1's `care_pathway`; without it live, the ladder has nothing to run on.
- Steps: `pathway_id` / `tier` / `offer_rank` on the skill schema + Rules Service routing + pathway-inherited residual (non-safety) guards.

**Exit:** offer-second surfaces only after the offer-first check-in; `tried_skills` are not re-offered; ≤2 offered at once; a pathway contraindication suppresses the whole category; a `pathway_id=null` skill routes exactly as v7.
**Demonstrable:** within the anxiety category, box breathing is offered first and grounding second after a no-help check-in — never all six at once.

## §5 — External dependencies & open clinical decisions

Each carries an **owner** and a **resolution form** — a dependency without both is a worry, not a tracked item.

**§5.1 — §4.5 precedence-order ratification.**
*Owner:* clinical lead. *Resolution form:* signature on the approval record's §4.5 line (already built into its sign-off table). *Unlocks:* Phase B0. Until signed, the three routes can be built, but the order they resolve multi-hits in is not frozen.

**§5.2 — Gap #65 semantic-tier decision.**
*Owner:* engineering + clinical lead (joint). *Resolution form:* a choice among three outcomes, each with a mapped consequence for E4/E7 gate feasibility —
| Outcome | Consequence |
|---|---|
| (a) keyword-only suffices for POC gates | E4/E7 ≥95% achievable on keyword fixtures; no semantic tier for POC |
| (b) semantic tier required | E4/E7 recall gates need a MARBERT/semantic tier before they can pass; added scope, mirrors crisis S1→S2 |
| (c) hybrid — keyword for POC, semantic deferred to production | E4/E7 pass POC on keyword with a documented production-recall obligation (like the Arabic debt) |
*Must be answered before E4/E7 recall targets are treated as achievable-as-specified.*

**§5.3 — GL-0 crisis recall.**
*Owner:* safety/ML workstream (S2/MARBERT). *Current trajectory:* ~37% CRADLE / 18% self-harm / 88.9% S3 passive-SI vs ≥95%; needs S2/MARBERT + a validated bilingual eval. *Resolution form:* the recall harness demonstrates ≥95% on the §C fixtures. *Unlocks:* Phase A1 — and remains the pilot's true critical path.

**§5.4 — Helpline dial-test + L0 re-sign.**
*Owner:* product owner (dial-test — physically confirm `800 4673` is live + correct) + clinical lead (L0 persona re-sign). *Resolution form:* dial-test confirmation recorded on the GL-1 governance entry + L0 version bump re-signed. *Unlocks:* Phase A2 (commit-2 ships).

---

## §6 — Sign-off → unlock matrix

**Closure property (maintenance rule):** this matrix is **closed over the plan** — every phase and sub-phase in §4, plus the non-blocked lane (§2) and the external decisions (§5), appears here **exactly once** with its full gate set; and no gate referenced here is undefined in §0/§5. This table is the plan's integrity check: **a future edit to §4 must update §6 in the same commit**, or the two drift out of reconciliation.

| Item | 🔒 signature | ⛔ precondition(s) | Unlocks / status |
|---|---|---|---|
| §2.1 Appendix-A content/config | — | — | 🟢 authorized now |
| §2.2 fixture-set authoring | — | — | 🟢 authorized now (feeds GL-0) |
| §2.3 staged helpline payload | — | dial-test + L0 re-sign (§5.4) | prep 🟢; ship gated |
| A1 — §C detection-recall | — | GL-0 ≥95% (§5.3) | crisis detection at gate |
| A2 — §C content | — | dial-test + L0 re-sign (§5.4) | corrected tiered resources live |
| B0 — precedence wiring | — | §4.5 ratification (§5.1) | deterministic multi-hit order; gates B1–B3 order-finalization |
| B1 — E3 medical | E3 | E3 recall ≥95%; B0 | medical screen-up route |
| B2a — E4 §HR shape | E4 | B0 | distress-first neutral referral (psychosis, live route) |
| B2b — E4 mania/dissociation detection | E4 | E4 per-class recall ≥95%; Gap #65 (§5.2); CF-006 activation; B0 | full HR trigger coverage |
| B3 — E7 IPV pre-emption | E7 | E7 recall ≥95%; B0 | scoped §6 pre-emption + referral |
| C — E1 supervisor + `care_pathway` | E1 | Phase B exit (§F silent-divert testable) | mid-conversation tier step-up |
| D — E2 category grouping | E2 | Phase C exit (`care_pathway` live) | offer-first/second ladder |
| *ext* §5.1 precedence ratification | (clinical lead) | — | unlocks B0 |
| *ext* §5.2 Gap #65 decision | (eng + clinical) | — | bounds B2b / B3 gate feasibility |

**Change control.** This plan **cites** the approval record; it does not restate it. If a signer amends the record during the signature loop — most likely E4's per-class gates or the §4.5 precedence order, the two items flagged as clinical decisions to ratify — those amendments **propagate here**, and the affected §4 phases + §6 rows re-open. That is the accepted cost of drafting the plan in parallel with signing rather than after it, and it is cheap: a sequencing doc is far easier to revise than it is to have signatures land with no plan ready.

---

*Plan complete — §0–§6. Companion to the approval record (mechanism) and the conversion doc (§C/§HR content). Nothing herein authorizes a build step; the markers and §6 matrix do.*
