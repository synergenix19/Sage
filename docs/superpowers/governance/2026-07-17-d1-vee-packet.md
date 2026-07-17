# D1 medical screen — Vee packet (#338) — ONE sitting, THREE rulings

**GATE 0 evidence attached** (`2026-07-17-d1-gate0-evidence-pack.md`): your tick is on a **driven mechanism,
50 branches + regression green**, not a spec. **Framing:** this is the **C1 revisit-trigger's key** — your
(a) grounding-first ruling holds *until D1 verifies*; this tick starts that clock, so the TIPP-leads question
you deferred comes back to you honestly once shadow proves the screen. **Recommendation: approve all three.**

> **REVISION named for this sitting (eng-caught pre-issue):** the screen now covers **BOTH** clinical halves,
> not one. The first draft asked only the **L101 acute symptom-quality** differentiation (panic vs emergency
> → 998). But D1 exists *because of TIPP's L194 contraindications* — the ice-water/dive-reflex step is a
> cardiac load, the intense-exercise step is contraindicated in pregnancy. A user with a known heart
> condition having an ordinary panic day would answer the L101 question truthfully — "no, same as always" —
> clear_no, proceed, ice-water. The screen would have missed the exact person it was built for, and the
> revisit-trigger's "robust" would be a false clear. **The screen now asks both halves**; your tick certifies
> that dual coverage. This also *promotes the spec's own SG-2 caveat* ("heart condition → skip those steps")
> from delivery-side self-screen to routing-side gate — D1's whole purpose.

## RULING 1 — A1 question wording, **two beats** (approve / edit tone)
> *"Before we try this one — quick check first: does anything about how this feels seem different from your
> usual anxiety? Like a sharp or crushing pain rather than tightness, pain spreading to your arm, jaw, or
> back, real trouble breathing rather than shallow breathing, or numbness or weakness on one side?*
> *And is there anything like a heart condition, or a pregnancy, that I should know about before we try it?"*

Beat 1 = spec L101 acute-quality markers (→ 998 if red-flag). Beat 2 = spec **L194 contraindication**
disclosure (→ grounding, a routing fact not an emergency). **Edit tone freely; both clinical payloads stay —
the L194 beat is the half that closes the gap.**  ▢ approve ▢ edit: ______

## RULING 2 — A2 branch table + fail-safe (approve / edit)
Safe-by-construction — **routes away, never clears** (GATE 0 proved `proceed` reachable only from clear_no):

| answer | route |
|---|---|
| clear **no** on **both** beats ("same as always", no condition) | proceed with the skill |
| **red-flag quality** (spreading to arm/jaw, real trouble breathing, one-sided numbness) | **medical guard (998)** |
| **contraindication disclosed** (heart condition / pregnancy), symptoms not red-flag | **grounding — silently and warmly** (a *routing fact*, NOT 998; a stable condition is not an emergency) |
| yes / unclear / evaded / no-answer / topic-change | **grounding — silently and warmly** (fail-safe) |

A disclosed contraindication **wins over a clear_no on symptom quality** — the two are separate questions.
Crisis content in any answer → crisis path wins, screen abandoned (audited). AR: **grounding-only until the AR
question is separately signed.**  ▢ approve ▢ edit: ______

**A3 rides:** both artifacts enter `signed_clinical_fields.json` on your tick — CI-locked, can't drift unsigned.

## RULING 3 — shadow flip criteria (engineering proposes numbers; you tick thresholds)
Pre-registered **before** shadow runs, so the flip decision reads itself. Proposed:

| dimension | proposed threshold | what it catches |
|---|---|---|
| **trigger fire-rate** | screen fires on **70–95%** of TIPP-routed turns | <70% = trigger under-recalls (misses acute language); >95% w/ high non-acute = over-fires |
| **answer-class distribution** | `unclear` **< 20%** of answers | if `unclear` dominates, the question isn't discriminating in the wild → **back to you before flip** |
| **`contraindication_disclosed` rate** | **tracked separately, no threshold — measured** | the direct count of users the old delivery-side SG-2 self-screen was silently failing; the number that justifies D1 existing |
| **fail-safe (route-away) rate** | **~15–35%** expected (incl. contraindication + unclear) | the safety cost being purchased; >50% = over-trigger or confusing question |
| **ZERO-TOLERANCE** | any crisis-in-answer mishandled **OR** any audit-row swallow → **shadow STOPS, not tunes** | the two invariants; a single breach halts |

▢ approve thresholds ▢ edit: ______   *(numbers are eng's proposal; the rulings are yours)*

---
*Ride-along, not for this sitting: the BGE-M3 semantic trigger tier is parked as shadow-informed tuning — the
keyword net's recall bias is the safe launch posture; shadow's fire-rate decides if the anchor tier is needed.*
