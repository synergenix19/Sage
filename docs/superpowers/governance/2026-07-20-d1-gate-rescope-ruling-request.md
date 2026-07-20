# D1 — one ruling: re-scope the shadow gate to the measured base rate (#338)

## ✅ RULED: (c) APPROVED — Vee (clinical lead), 2026-07-20 (relayed via coordinator)
Re-scope approved. Transcription of Vee's stated reasoning (record precedes the flip, GL-1):
- **The hold's reason has expired.** The bot-behaviour document tiers acute overwhelm to TIPP (L69) and notes
  the cardiac/pregnancy contraindications (L194). Grounding-first was never the document's position — it was a
  hold since 2026-06-13 for ONE stated reason: no contraindication screen existed. That reason is now gone.
  Keeping the hold once a verified screen exists permanently withholds the document's own indicated
  intervention rather than asking one warm question — over-caution presenting as safety.
- **The screening principle is satisfied in the direction that matters.** Routes away, never clears; both
  halves covered (L101 red-flags + L194 contraindications) — the "robust screen" the C1 revisit-trigger named.
- **The asymmetry makes a small sample acceptable (inverse of the usual case).** Worst case of flipping thin =
  someone gets grounding instead of resumed TIPP = today's behaviour = the downside of being wrong is the
  status quo. Worst case of NOT flipping = the contraindication question keeps not being asked while the SG-2
  delivery-side caveat relies on users self-screening mid-exercise. Every day dark, the risk stays live.
- **The honesty clause makes it defensible not convenient.** (c) doesn't lower the bar; it moves answer-class
  measurement to the only window where answers exist, reports descriptively until n supports, and keeps the
  two absolute halts (crisis mishandled, screen decision unrecorded). The C1 revisit will state exactly what
  the evidence establishes (mechanism live on every branch, zero halts) and what it does not (statistical
  confidence in the answer distribution). No overclaim.
- Alternatives rejected: recalibrate-to-8–10 = near-tautological number; extend-six-weeks = max dark, min gain.

**Consequence:** the shadow gate is re-scoped to *mechanism-proven-live + zero-breach*. That condition is MET.
The flip proceeds on the frozen checklist. Operational/product go: coordinator (this session). Primary record:
this file. Flip record to follow: `2026-07-20-d1-enforce-flip-record.md`.

---


**For: Vee (clinical) + PO (product). One decision. Approve / reject / edit.** Nothing changes the screen's
behaviour or its signed content — this is only about *what evidence must accrue before the screen goes live*.

## The situation in one paragraph
The D1 medical screen is built, signed, and running in prod in SHADOW (it observes, serves nothing, changes
nothing). The plan was: let the shadow window collect 40 TIPP-routed turns, confirm the screen behaves, then
flip it live. **New measured fact:** TIPP is a rare route in production — 22 times in the deployment's entire
history, 4.5% of skill turns, and **0 in the first 3 days** of the window. Acute-overwhelm is mostly reaching
`box_breathing` (a safe, non-contraindicated skill), not TIPP. So 40 TIPP turns will not accrue inside the
14-day window. The shadow gate as written is unreachable.

## What the shadow window has ALREADY proven (live, in prod)
- The screen fires on the right turns, serves the exact signed question, and every branch routes correctly:
  clear answer resumes the skill; a disclosed heart condition / pregnancy routes to grounding; a red-flag
  symptom routes to 998; crisis abandons the screen to the crisis path. Driven both directions, verified live.

## What shadow CANNOT prove (by design)
A silent screen serves no question, so it collects no answers — it cannot measure how people actually answer.
That was always going to be measured *after* go-live. The base rate just makes the "40 turns first" number
impossible to reach.

## The recommendation: (c) re-scope the gate — flip on what's proven, measure the rest live
> Move the answer-measurement to the live (monitored-enforce) window, where real answers exist and the
> fail-safe is actively protecting people. Flip when the mechanism is proven (it is) and no safety breach has
> occurred (none has), rather than waiting for a count that cannot arrive.

**Why this is safe to do on a small sample:** every branch of this screen fails safe toward grounding. Its
failure mode is routing someone *away* from a technique, never *into* a contraindicated one. So flipping on
thin data costs, at worst, a few people getting grounding instead of a resumed skill — it never costs a
contraindicated exposure. Meanwhile, every day it stays dark, the contraindication risk it guards is live.

## Choose one
- **▢ (c) APPROVE re-scope — RECOMMENDED.** Flip now on: mechanism proven live + zero safety breaches. The
  answer-class rates (how many say clear/disclose/evade) are measured live afterward and reported to you as
  descriptive context, not as a pass/fail number, until enough turns accrue.
- **▢ Recalibrate the number instead.** Keep a fire-rate gate but drop it to ~8–10 TIPP turns with a
  "small sample" caveat. (Buys little: the screen fires on every TIPP turn by design, so this number isn't
  clinically informative.)
- **▢ Keep 40, extend the window.** Wait ~6 weeks for a still-thin number while the screen stays dark on a
  live-risk surface. (Recommend against: longest exposure, smallest gain.)
- **▢ EDIT:** _______________________________________________

## Held constant no matter what you choose (not up for trade)
**Any crisis mishandled in an answer, or any failure to record a screen decision, HALTS the screen back to
shadow immediately.** These are safety stops, not statistical thresholds. They do not move.

## What you are told when this comes back to you (the C1 revisit on TIPP-leads)
"D1 verified" will mean: **the mechanism worked live on every branch, and no safety stop fired** — with the
answer-class picture given as descriptive context, honestly labelled as small-sample until it isn't. You will
never be handed a false claim of statistical confidence. Your grounding-first ruling held until the screen was
real; the screen is now real, measured on what is measurable, and signed at every layer.

**Ruling:**  ▢ Vee (clinical) ______   ▢ PO (product) ______   Date ______
Evidence + full options: `2026-07-17-d1-shadow-window-criteria.md` (amendment 2026-07-20).
