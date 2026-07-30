# K3/K4 — two recognition clauses for you to AUTHOR (not tick) (2026-07-30)

**The ask, in one line:** write the sentence (or two) per skill that teaches the router to recognize
two presentations it currently drops — the *wish to reconnect* (behavioral_activation) and
*self-identified boundary-crossing* (interpersonal_effectiveness). You author the wording; engineering
never edits clinical sentences (your C1 principle). Everything below is context and constraints.

## What happened (mechanism, diagnosed 2026-07-30 on staging, single-variable attribution)
The 07-28 keyword additions K3/K4 are loaded and MATCH on prod — but a matched keyword only produces
an offer if the V2 reranker also recognizes the phrasing against the skill's `semantic_description`.
K3/K4's phrasings score below the routing threshold there, so the match is vetoed and the user gets a
plain exploratory reply instead of the prescribed offer. This is the same mechanism class as the §3a
low-mood finding (#202), fixed then by a clinician-authored recognition clause — and that fix is the
model: **K1 "my mood has dropped" survives today precisely because your §3a clause covers it.**
K2 "no value as a person" survives the same way. The fix route is proven; only the two clauses are missing.

## Clause 1 — behavioral_activation: the reconnection wish (K4, §7b lineage)
Dead today: *"I want to reconnect with people"*, *"reconnect"*. The presentation: someone naming a
wish to re-engage socially after withdrawal — BA's re-engagement territory by the doc.

**Your boundary call (yours alone):** where reconnection-talk must NOT route to BA —
grief-driven reconnection ("reconnect with people since the loss…" → S2a/grief territory?),
reconnection framed from isolation with passive-SI adjacency (must keep escalating/abstaining).
The §3a bins are the precedent: bin(a) route, bin(b) deliberately-excluded, bin(c) your call.

## Clause 2 — interpersonal_effectiveness: self-identified boundary-crossing (K3, §6b lineage)
Dead today: *"I need to stop crossing a line"*. The presentation: the user names THEMSELVES as the
one crossing a line and wants to stop. Spec §6b prescribes DEARMAN (interpersonal_effectiveness).

**Your boundary call:** the self-as-transgressor framing is clinically distinct from
asking-for-a-boundary (the covered IE territory). Confirm DEARMAN is right for it — and where
crossing-a-line talk must NOT route (toward-harm content: "crossing a line" + harm-adjacency must
keep escalating; the §6a coercive-control neighborhood stays with its own mechanisms).

## Constraints on the wording (mechanical, engineering-enforced)
- Third person, no first-person pronouns; ~400-char cap per description (CMS validation).
- Presentation-recognition sentences, narrow and specific — the description feeds routing for ALL
  phrasings, and an over-broad clause burns the shared id_oos safety margin (currently 0.9219 vs the
  0.906 floor; the §6c attempt burned it to 0.9062 and was reverted — margin is shared safety
  infrastructure, not one fix's budget).
- Routing threshold τ is NOT touched (it bought the id_oos win; last lever).

## What happens after you author (the signed gate, all mechanical)
Known-failing fixtures first (paraphrase-independent — deliberately different phrasings from any the
router matches, the E7 lesson) → your clauses land → `calibrate_threshold` re-run (mandatory on any
description edit) → full signed gate: harm-0 both arms, id_oos ≥ 0.906 byte-check, per-pathway recall
floor, wrong-route no-regress → staging probe pair (target phrasings route; excluded-bin phrasings do
NOT) → prod deploy under lock + live behavioral probe. EN-only this pass; AR rides the AR track
(honesty precedent from §3a).

## Deliverable
Your authored sentence(s) for each skill + the two boundary rulings (bins). Reply in this doc or via
the PO relay, whichever is faster for you.
