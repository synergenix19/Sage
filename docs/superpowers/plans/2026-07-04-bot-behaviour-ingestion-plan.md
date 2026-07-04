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
*pending*

## §5 — External dependencies & open clinical decisions
*pending*

## §6 — Sign-off → unlock matrix
*pending*
