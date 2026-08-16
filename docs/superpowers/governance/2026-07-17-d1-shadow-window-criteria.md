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
