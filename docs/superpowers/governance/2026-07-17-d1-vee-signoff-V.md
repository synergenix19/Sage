# D1 medical screen (#338) — Vee sign-off record

**Record precedes merge (GL-1).** Transcription of the clinical lead's ruling, not invention. The packet
presented three rulings in one sitting (`2026-07-17-d1-vee-packet.md`, rev. with the L194 dual-coverage
revision named in it); this records the disposition.

## Disposition: ALL THREE APPROVED (as drafted)

| ruling | artifact | disposition |
|---|---|---|
| **1 — A1 question** | the two-beat wording: L101 acute symptom-quality + L194 contraindication disclosure | **APPROVED as drafted** |
| **2 — A2 branch table** | clear_no→proceed · red_flag→998 · **contraindication_disclosed→grounding (not 998)** · else→grounding; routes-away-never-clears; AR grounding-only until its own tick | **APPROVED as drafted** |
| **3 — flip criteria** | trigger fire-rate 70–95%; unclear <20%; contraindication_disclosed tracked-separately-measured; fail-safe 15–35%; zero-tolerance halt rows | **APPROVED as drafted** |

**Dual coverage certified:** the tick is explicitly on a screen that asks BOTH the L101 (panic-vs-emergency
→ 998) and L194 (chronic heart/pregnancy → grounding) halves. This is what makes the C1 revisit-trigger's
"robust" honest — the deferred TIPP-leads question returns to the clinical lead legitimately once shadow
verifies this screen.

## What this sign-off unblocks
- The placeholder guard (`UnsignedScreenError`) lifts for **EN only** — `_SIGNED_QUESTIONS["en"]` populated
  with the approved bytes. **AR stays unsigned** (grounding-only) until a separate AR tick.
- Both signed artifacts pinned in `signed_clinical_fields.json` (A3): the EN question and the `_ROUTES`
  branch table — CI-locked, cannot drift unsigned.
- RULING 3 thresholds are now **pre-registered** for the shadow window (numbers eng-proposed, thresholds
  clinician-ticked).

## What this sign-off does NOT do (honest boundary)
- Does **not** make D1 serve: the serve/resume render path (how `screen_question_text` reaches the user and
  the answer resumes the held skill) is **not yet wired**.
- Does **not** start shadow: a shadow-measurement branch (run trigger+classify+audit WITHOUT altering the
  served route) is **not yet built**; `D1_SCREEN_ENABLED` off is pure identity today.
- Sequence remains: build serve/resume + shadow branch → dark deploy (flag-off) through the lock chain →
  shadow with these pre-registered criteria → end-to-end drive in shadow → flip.

## Pre-freeze disposition (RESOLVED)
The approved A1 wording contained an em-dash ("Before we try this one — quick check first"). Standing rule:
no em-dash in content that can mirror into LLM output. **Dispositioned (clinical lead, 2026-07-17): comma-swap
applied before freeze** — "Before we try this one, a quick check first: …". This is an eng-applied typographic
convention fix within the approved tone, NOT a wording change (both clinical beats and every marker are
byte-identical otherwise). These comma bytes are the frozen signed value pinned as `d1_screen_question_en`.
No future re-tick incurred.

**Signed:** Vee (clinical lead), 2026-07-17 · relayed via user (command-session coordinator).
