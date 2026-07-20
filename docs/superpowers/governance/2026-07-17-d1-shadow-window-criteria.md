# D1 shadow window — pre-registered criteria + closing condition (#338)

**Pre-registered BEFORE the window fills (opened 2026-07-17), so it closes by rule, not by impatience.**
Reads only anonymised class+route audit columns (PDPL-approved). Derives from RULING 3 (thresholds unchanged).

## What the shadow window measures (silent shadow = fire-volume only)
- **Trigger fire-rate:** `count(screen_shadow_action='ask_screen') / count(active_skill_id='dbt_tipp')` over
  the window. RULING 3 band: **70–95%** of TIPP-routed turns. (In the current design the screen fires on
  every fresh contraindicated routing, so this is expected high; a materially-below-band read means the
  contraindicated-set or the gating logic drifted and is the signal to investigate.)
- **Disclosure-population:** count of `screen_shadow_action='reroute_grounding'` with
  `screen_shadow_answer_class='contraindication_disclosed'` — the session-prior-driven reroutes, i.e. users a
  disclosed condition already routed away. The direct measure of who the old delivery-side SG-2 self-screen
  was silently failing.
- **NOT measured here:** answer-class distribution (unclear/evaded/clear_no rates) — silent shadow serves
  nothing, so no answers exist. That is the **post-flip monitored-enforce** gate (RULING 3 split, Vee line 2).

## CLOSING CONDITION (pre-registered — the small-n lesson)
The window closes when **BOTH**:
1. **n_floor met:** at least **N = 40** TIPP-routed turns observed in the window (the fire-rate denominator).
   Rationale (n_floor logic): a fire-rate band read off a dozen turns is noise wearing a percentage — at
   n=40 a single-count swing moves the rate ≤2.5pp, so an 70–95% band is separable from sampling noise. If
   real TIPP volume is low, **duration cap = 14 days** closes the window regardless, and the read is reported
   WITH its n and a small-n caveat rather than silently treated as complete (no silent truncation).
2. **No zero-tolerance breach open:** no `abandon_crisis` mis-handling and no audit-swallow (ScreenAuditError)
   observed in the window. A single breach **halts the window** (does not tune) and routes back to review.

**Whichever of {n=40, 14-day cap} fills first closes the window; the report states which, with n.** The flip
decision then reads: fire-rate in band AND disclosure-population non-trivial AND zero breaches → proceed to
the monitored-enforce window (post serve/resume + Vee's two lines). Out-of-band or any breach → back to Vee.

## Rollback during the window
`SAGE_D1_SCREEN_SHADOW=0` → proven identity (deploy record). No code path serves; closing early is free.

---

# AMENDMENT 2026-07-20 — recalibrate the gate to the MEASURED base rate (for Vee/PO ruling)

**Why now, not at day 14:** the base rate is now measured rather than assumed, and it shows a gate whose N is
unreachable inside its own cap — a scheduled 14-day stall with a foreknown outcome. Raising it on day 3 rather
than discovering it on day 14 is the same discipline the project runs on: do not let the record claim for two
weeks something we already know today. This is exactly the "cap-before-N is a finding" clause firing early.

## Evidence (measured, cited from the prod audit — rule on data, not on our characterization)
- **`dbt_tipp` routing base rate:** 22 real routings ALL-TIME, **4.48%** of skill-routed turns, **rank 10 of
  27** skills (query over `session_audit`, non-test sessions).
- **Accrual so far:** window opened 2026-07-17; **N = 0/40 after ~3 days** (zero real TIPP-routed shadow
  rows). Shadow confirmed armed and recording (synthetic probes landed `ask_screen` both directions).
- **Clinically interesting in its own right:** acute-overwhelm in prod is largely reaching **`box_breathing`**
  (a NON-contraindicated skill), not TIPP. The acute-overwhelm population the screen was built to guard is
  mostly already routing to a safe skill — context for how much exposure D1 is actually gating.
- **Projection:** at 22 all-time, N=40 (nearly double the entire history) is not reachable inside the 14-day
  cap. The gate would stall to cap and read a low, non-informative n.

## The finding underneath the arithmetic
The screen fires DETERMINISTICALLY on every fresh contraindicated routing — so "fire-rate" was never an
informative measurement (no threshold behaviour to observe, just a denominator counting TIPP routings).
RULING 3's fire-rate band assumed a recall-biased trigger that might under/over-fire against acute-overwhelm
presentations; the measured picture is different (acute-overwhelm lands on box_breathing; TIPP is rank 10 at
4.5%). So the honest question is not "tune the band" but "measure what shadow can actually learn."

## Options (with SAFETY cost, not just statistical cost)

The asymmetry that frames all three: **every branch of this screen fails safe toward grounding.** The failure
mode is routing-away, never over-routing-into a contraindicated skill. So the risk of flipping on thin data is
materially LOWER here than for a mechanism whose failure mode is exposure — a mis-scoped-thin flip costs, at
worst, a few users getting grounding instead of a resumed TIPP; it never costs a contraindicated exposure.

- **▢ (c) RE-SCOPE the gate to what shadow can learn — RECOMMENDED.** Shadow's gate = *mechanism engages
  correctly* (ALREADY proven live in prod, both directions, 2026-07-17) + *disclosure-population accrues as it
  comes* (descriptive). Fire-rate and answer-class confidence move to the **monitored-enforce** window, where
  the traffic is equally thin but the fail-safe is LIVE and the measurement is finally of something real
  (actual answers, not hypothetical ones). Same honesty as moving the answer-class rows post-flip, applied one
  step further now that the base rate is measurable. **Safety cost:** flip happens SOONER with a mechanism
  proven in shadow but a small disclosure sample — acceptable given the fail-safe asymmetry above.
- **▢ Recalibrate N** to the measured base rate (e.g. N=8–10 TIPP turns) with an **explicit small-n caveat**
  on every read. **Safety cost:** similar to (c) but retains a fire-rate number that is near-tautological by
  design; buys little over (c) and still stalls weeks.
- **▢ Extend the cap (ARGUE AGAINST).** Buys a statistically thin number ~6 weeks later while leaving a
  signed, verified, fail-safe screen sitting **dark on a surface where the contraindication risk is live
  today**. **Safety cost is borne by exactly the users the screen protects** — the longest-dark option for the
  smallest measurement gain. Recommend reject.

## Untouched in EVERY option (not statistical thresholds — they do not move)
**Zero-tolerance halt rows:** any crisis-in-answer mishandled OR any audit swallow (ScreenAuditError) → the
window HALTS back to shadow, not tunes. A single breach halts, in shadow and in monitored-enforce alike.

## Pre-registered NOW: the monitored-enforce window's honest closing condition (same base-rate reality)
At this base rate the monitored-enforce window will ALSO fill slowly — so its closing condition is
pre-registered here with the small-n caveat stated up front, not discovered again:

> **"D1 verified" for the purpose of firing the C1 revisit = mechanism verified LIVE (each branch driven
> end-to-end post-flip) + ZERO zero-tolerance events over the window.** The answer-class distribution
> (unclear/evaded/clear_no/contraindication_disclosed rates) is **reported as DESCRIPTIVE, not thresholded,
> until n supports more.** If `unclear` visibly dominates even at small n, that still returns to Vee.

This keeps the revisit-trigger honest: when TIPP-leads comes back to Vee, she is told **exactly what the
evidence does and does not establish** — mechanism proven + fail-safe intact + no breaches, with the
answer-class picture as descriptive context, not a false claim of statistical confidence.

## Disposition
▢ Vee (clinical) / ▢ PO (product) rule on the option. Recommendation: **(c)**, recalibrated-N secondary,
cap-extension rejected. Zero-tolerance rows and the monitored-enforce honesty clause hold under any choice.
Carried to Vee/PO on the same channel as their other open items (alongside the containment escalation).

