# D1 medical screen — Vee packet (#338) — ONE sitting, THREE rulings

**GATE 0 evidence attached** (`2026-07-17-d1-gate0-evidence-pack.md`): your tick is on a **driven mechanism,
38 branches + 92 regression green**, not a spec. **Framing:** this is the **C1 revisit-trigger's key** — your
(a) grounding-first ruling holds *until D1 verifies*; this tick starts that clock, so the TIPP-leads question
you deferred comes back to you honestly once shadow proves the screen. **Recommendation: approve all three.**

## RULING 1 — A1 question wording (approve / edit tone)
> *"Before we try this one — quick check first: does anything about how this feels seem different from your
> usual anxiety? Like a sharp or crushing pain rather than tightness, pain spreading to your arm, jaw, or
> back, real trouble breathing rather than shallow breathing, or numbness or weakness on one side?"*

Spec L101's discriminating markers in warm framing. **Edit tone freely; the markers are the clinical payload
and stay.**  ▢ approve ▢ edit: ______

## RULING 2 — A2 branch table + fail-safe (approve / edit)
Safe-by-construction — **routes away, never clears** (GATE 0 proved `proceed` reachable only from clear_no):

| answer | route |
|---|---|
| clear **no** ("same as always") | proceed with the skill |
| **red-flag quality** (spreading to arm/jaw, real trouble breathing, one-sided numbness) | **medical guard (998)** |
| yes / unclear / evaded / no-answer / topic-change | **grounding — silently and warmly** (fail-safe) |

Crisis content in any answer → crisis path wins, screen abandoned (audited). AR: **grounding-only until the AR
question is separately signed.**  ▢ approve ▢ edit: ______

**A3 rides:** both artifacts enter `signed_clinical_fields.json` on your tick — CI-locked, can't drift unsigned.

## RULING 3 — shadow flip criteria (engineering proposes numbers; you tick thresholds)
Pre-registered **before** shadow runs, so the flip decision reads itself. Proposed:

| dimension | proposed threshold | what it catches |
|---|---|---|
| **trigger fire-rate** | screen fires on **70–95%** of TIPP-routed turns | <70% = trigger under-recalls (misses acute language); >95% w/ high non-acute = over-fires |
| **answer-class distribution** | `unclear` **< 20%** of answers | if `unclear` dominates, the question isn't discriminating in the wild → **back to you before flip** |
| **fail-safe (route-away) rate** | **~15–35%** expected | the safety cost being purchased; >50% = over-trigger or confusing question |
| **ZERO-TOLERANCE** | any crisis-in-answer mishandled **OR** any audit-row swallow → **shadow STOPS, not tunes** | the two invariants; a single breach halts |

▢ approve thresholds ▢ edit: ______   *(numbers are eng's proposal; the rulings are yours)*

---
*Ride-along, not for this sitting: the BGE-M3 semantic trigger tier is parked as shadow-informed tuning — the
keyword net's recall bias is the safe launch posture; shadow's fire-rate decides if the anchor tier is needed.*
