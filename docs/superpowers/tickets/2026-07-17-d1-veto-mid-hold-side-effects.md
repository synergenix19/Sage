# Ticket — D1 veto/containment-mid-hold: flag + containment SIDE-EFFECTS (not route safety) (#338)

**Priority: deferred, monitored. Moves up if monitoring shows the case is not rare.**

## The precise boundary (safe, not silent)
When a screen is pending (question emitted, TIPP held) and the user's NEXT turn discloses veto-matching or
containment-matching content (e.g. a harm-intrusive OCD disclosure), the current serve/resume classifies that
utterance as an evaded screen answer → **grounding fail-safe**, hold released.

**What IS correct on that turn (route safety — intact):**
- The hold releases (property holds: screen_pending never survives >1 turn).
- Nothing contraindicated is served (routed AWAY from TIPP).
- A warm response is delivered (grounding).

**What is DEFERRED (side-effects — do NOT fire on that single turn):**
- The **L2 clinical flag** that the disclosure should raise.
- The **containment psychoeducation / enrichment** the disclosure should trigger (the veto's abstain →
  low_confidence clarification path, or the containment L3/L4 template).

So the gap is **flag + containment side-effects on the mid-hold turn**, NOT route safety. A user gets a warm,
safe, non-contraindicated response; what they miss is the specific clinical flag + psychoed that a disclosure
outside a pending screen would have triggered — for exactly one turn (the disclosure re-lands on any later
turn and fires normally).

## Why the deferral is acceptable
The disclosure must land in the **single pending turn** — a narrow coincidence window (one turn between the
screen emitting and its answer). The shadow window (fire-volume) and the monitored-enforce window
(answer-class distribution) should CONFIRM this case is as rare as expected. **If monitoring shows it is not
rare, the fix moves up the queue.**

## The fix (when it moves up)
A **veto-marker signal** into `apply_screen_at_route`: on an `answering_screen` turn, if the result carries a
veto/containment marker (active_skill_id=None due to a veto, or containment_directive set), DEFER to that
layer's own routing (its abstain/enrichment) and abandon the hold — rather than classifying the utterance as
a screen answer. Supremacy chain made explicit at the answer-turn seam (crisis > vetoes > containment >
screen), the same unification consume_pending_screen achieved for crisis.

## Monitoring hook
Shadow/monitored-enforce: count answer-turn rows where the raw utterance would have matched a veto/containment
pattern (a would-have-fired probe on the answer text) → the incidence of this case. Report it in the window
read-outs. Target: rare. Owner: D1 (serve/resume follow-up). Tracked from 2026-07-17.
