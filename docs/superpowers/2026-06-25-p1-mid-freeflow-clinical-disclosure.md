# Clinical disclosure + design question — heavy-disclosure coldness (§15.3) and P1(mid)

**To:** Rohan Sarda (clinical lead)
**From:** engineering
**Date:** 2026-06-25
**Status:** Item 1 is a clinical-design question that needs your decision. Item 2 is a disclosure only (P1 ships as engineering, no gate). Item 1 is the clinically urgent one — read it first.

---

## 1. URGENT — clinical-design question: the high-band posture may be miscalibrated for grief

### What we measured (2026-06-25)

A bereavement disclosure — *"my dad passed away last month and I don't think I've really dealt with it"* — scores **emotional_intensity 7 in 6/6 runs**. At intensity ≥7 the system applies the high-band guidance:

> "Name the specific thing they said... Ask one focused question. Do NOT paraphrase or reflect back what they said. Do NOT begin with 'It sounds like' or any reflective opener. Do NOT offer guidance yet."

Result: the bereaved user received a **24-word reply** (median across samples), while ordinary mid-band disclosures (sad about a sick dog, lonely) receive fuller, warmer replies. **A grieving person gets the coldest, most clipped response in the system** — the inverse of what the moment calls for.

### Why this is a design question, not a wording bug

The high-band "do not paraphrase or reflect back" rule appears designed for **acute agitated distress**, where reflective mirroring can amplify rumination or escalate arousal. That is a defensible posture for that presentation.

**Grief is the opposite presentation.** In bereavement support, reflection, validation, and presence are precisely indicated — the evidence base treats acute grief as a *normal* process needing companioning, not a state needing containment. So the issue is not the wording of one string; it is that the band conflates **emotional weight** (high) with **agitation/acuity** (which grief is low on), and applies an agitation-calibrated posture to a presentation that needs the opposite. This is a clinical-design call only the L0/L2 owner can make, and it may be larger than editing a string.

### Engineering's evidence-based recommendation (for your sign-off, not a decision we own)

Treat **grief/loss/bereavement as a distinct high-weight, low-agitation presentation** that should receive *more* validation and reflection, not less. Specifically:

1. **Suspend the "do not reflect back" rule for grief.** Reflective acknowledgement of the loss is indicated, not contraindicated. (Anchor: reflective listening is core to grief support; the anti-reflection rule's rationale — rumination amplification — applies to agitated arousal, not bereavement.)
2. **Honor the L0 "heavy disclosure deserves a longer, more present reply" exception at the high band for grief** — right now the high-band string overrides it, producing the cold reply. The extra length should be presence and validation, not advice (consistent with your existing L0 wording).
3. **Allow naming the loss specifically and gently inviting them to say more** about the person or the death (loss-orientation), rather than redirecting away from it. (Anchor: Dual Process Model of grief, Stroebe & Schut — oscillation between loss- and restoration-orientation; do not steer the bereaved away from loss-orientation.)
4. **Do not impose stages or timelines.** No "it's been a month" framing, no Kübler-Ross stage-prescribing (not evidence-based as a prescriptive model). Grief is non-linear; normalize that.
5. **Keep the safety layer attentive but not the response posture clipped.** Bereavement is an elevated suicide-risk window, so crisis screening stays on — but warmth, not containment, is the response register. These are separable.
6. **Over time, watch for prolonged grief disorder markers** (now a formal diagnosis in DSM-5-TR and ICD-11; ~1 in 10 of the bereaved). This is a longitudinal flag, not a turn-1 action, and is a "bridge to professional support" signal, not something the companion treats.

Frameworks behind the above, for your reviewer: Worden's tasks of mourning; Dual Process Model (Stroebe & Schut); continuing-bonds; the normal-grief vs prolonged-grief distinction (DSM-5-TR / ICD-11); the critique of Kübler-Ross stages as prescriptive. Engineering is surfacing the evidence base, not adjudicating it — the calibration is yours.

### How this relates to P1 (below)

P1 fixes **everyday mid-band coldness**. It deliberately does **not** touch the ≥7 acute band, so it **cannot** fix this grief case. P1 and this §15.3 item are **complementary, not competing**: P1 = everyday warmth (mid), §15.3 = heaviest-disclosure warmth (high). Two turns ago engineering told you §15.3 was a low-urgency ≥7 corner case; **that was wrong as a global priority** — grief is the canonical heavy-disclosure case and produces the worst output in the system. We are correcting that and asking you to prioritise it.

---

## 2. Disclosure only — P1 now leans on your signed L0 "longer reply" clause

P1 (branch `feat/p1-mid-freeflow-shape`) fixes the everyday cold-reply defect (the "my dog hasn't been eating" screenshot) on mid-band (intensity 4–6) pure-freeflow turns. It touches **no signed template**, contains **no normalization** (your P2, still parked) and **no menu/fork** (P3, still gated). It ships as engineering, no sign-off needed. Two things to know:

**(a) It is now load-bearing on a clause you own.** A plain "write 40–80 words" instruction did nothing — L0's signed concision cap *"Keep replies concise, two to four sentences"* overrode it. P1 only works because it **invokes the exception you already signed**: *"...unless the person needs more; a heavy disclosure deserves a longer, more present reply even when it is brief..."* If a future L0 edit drops or tightens that exception, P1 silently reverts to cold. We guard this with a code comment at the injection site and a CI test that fails if the clause leaves L0. **Ask:** treat that exception as a dependency when you next revise L0.

**(b) Its reach grew.** The exception now fires across freeflow general-chat at intensity 4–6, including lighter mid disclosures, not only heavy ones. We judged this in-scope for "needs more"; you own the clause, so you should know.

---

## Evidence summary (P1)

- Floor moved: dog case pre-median 33 words (0/5 ≥40) → ~39–47 post (boundary; shortest case lifted to the floor, accepted as soft — see PR).
- Arabic: **engineering-only, confirmed.** AR generates in English against the same L0 (no separate Khaleeji L0), so the same exception applies; both AR cases cleared the floor in generation. (Separate finding: the absence of a dedicated Khaleeji L0 is logged as its own backlog ticket — it is the root of the eval's P-3 "pure MSA not Khaleeji" gap and should precede any Khaleeji-resonance clinical claim.)
- Acute exclusion verified end-to-end: crisis (EN + AR) routes `safety_check → crisis_response`, never freeflow.

## Caveat on our read

The L0 concision clause and its exception are not verbatim in the v7 spec; they live in the composer/CMS L0 template. Engineering asserts this wording from the live template. The principle (L0 is always-on, system-layer, clinician-owned) is what the spec confirms.
