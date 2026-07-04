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

## §2 — The non-blocked lane
*pending — next turn*

## §3 — Shared recall-measurement harness
*pending*

## §4 — Sequenced build phases
*pending*

## §5 — External dependencies & open clinical decisions
*pending*

## §6 — Sign-off → unlock matrix
*pending*
