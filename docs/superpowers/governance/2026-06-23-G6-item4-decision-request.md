# G6 Item #4 — Mis-route Arm: Decision Request (Product Owner)

> ## DECIDED 2026-06-23 — **Arm A (POC-phased)**. Product owner signed.
> `ar/id_oos` sized to **~65** (≤4.6% mis-route, rule-of-three upper bound). The ≤1%/~300 bar is a **tracked pre-pilot reopening**, not dropped — it binds exactly when worst-cell precision becomes safety-relevant. Rationale on the record: Arm A defers a *routing-quality* tolerance, not a *safety* one, and reversibly; the POC safety net is human oversight + NO-GO-by-default crisis handling, neither of which this touches. **G6 item #4 → SIGNED; all G6 values now signed.** Native reviewer's Phase-2 cell can now be sized.



**One binary decision. It is fast to make and it gates the slowest work on the board** — the native Khaleeji reviewer cannot be given a target size for the Arabic worst cell (`ar/id_oos`) until this is named, and that cell is the long pole to V2 flip-eligibility. Everything else in the dataset is either done (EN side, all three cells now N≥30) or sequenced behind this.

## What's being decided
The acceptable **mis-route bar** for the worst stratum, and at what sample size we commit to it. This sizes how many `ar/id_oos` (Arabic in-domain-out-of-scope) cases the native reviewer must produce — a **4–5× swing**.

| | **Arm A — POC-phased (recommended for POC)** | **Arm B — ≤1% upfront** |
|---|---|---|
| Bar now | ≤4.6% mis-route @ **N≈65** (one-sided 95% upper bound, rule-of-three) | ≤1% mis-route @ **N≈300** |
| `ar/id_oos` size | **~65 cases** | **~300 cases** |
| ≤1%/~300 bar | deferred to **pre-pilot** (named, not dropped) | met now |
| Native-reviewer load | ~65 reviewed cases (weeks) | ~300 reviewed cases (4–5× longer) |
| Risk posture | POC-appropriate; worst-cell precision re-confirmed before pilot | strongest now; large up-front cost |

## Why it's the highest-leverage unblock
- It's a **binary you can answer in one decision** (no new analysis needed).
- It gates a **people-paced cell** (native review can't parallelize, and can't even *start* its worst cell without the target).
- Leaving it "open, running in parallel" does **not** keep things moving — it silently stalls the Arabic long pole at its hardest cell.

## Recommendation
**Arm A (POC-phased).** This is a POC; ~65 gives a defensible worst-cell verdict (rule-of-three upper bound ≤4.6%), lets native review start now, and the ≤1%/~300 bar resurfaces as a **named pre-pilot reopening** — not a dropped requirement. Consistent with the #4-POC-arm framing already in the G6 draft.

## Decision
```
Arm (A / B): ______    Product owner: ______________   Date: ______
If A: confirm ≤1%/~300 bar is a tracked pre-pilot reopening (not dropped): ______
```
On decision: native reviewer gets the `ar/id_oos` target N and starts; G6 item #4 moves from RISK-ACCEPTED-arm-unspecified to SIGNED. Records into `2026-06-22-G6-values-DRAFT.md`.

## Stopping rule + power-floor honesty (clinician refinement)
**The ≤4.6% bound is fragile and must not be read as a tolerance for one error.** `3/N ≈ 4.6%` at N≈65 is the rule-of-three upper bound **conditional on ZERO observed mis-routes**. A single mis-route at N=65 breaks it: the exact 95% upper bound for 1/65 is ≈8.6%, well past 4.6%. So the **fail rule is explicit: ≥1 mis-route in the held-out `ar/id_oos` cell fails Arm A's bar** — it triggers either more labeled data to re-establish the bound (~N≥100+ to re-bound after one error) or a routing fix. It is **not** "one mistake is within budget."

**The `in_scope`/`far_oos` N≥30 floor was asserted (the #5 eng value), not derived — naming that honestly.** N=30 is a *minimum-stable-estimate* floor; it is **not** a powered detector of a δ=0.05 parity difference (that needs N in the hundreds). To put it on the same derived footing as the id_oos bound, state its effect size via the same rule-of-three: **N=30 at 0 errors gives a ≤10% upper bound.** So either (a) adopt **≤10% upper bound at zero errors** as the explicit `in_scope`/`far_oos` tolerance (deriving N≥30 the same way ≤4.6% derives N≈65), or (b) if a tighter bound or a true powered parity test is wanted, **N must rise** — and that's a value for the product owner / clinical lead to set, not something the harness should assert. **Recommend (a) for POC, flagged as a deliberately weaker bound than the worst cell.** *(Open value — please confirm or set.)*

### CONFIRMED 2026-06-24 (clinical lead) — per-cell, three profiles, NOT global
A uniform ≤10% was rejected as the convenient-but-wrong answer (the F8-shaped error: one number masking the cell needing the tightest). Settled:
| Cell(s) | Tolerance | Derived N (rule of three) | Judged by |
|---|---|---|---|
| `in_scope`, `far_oos` (both langs) | **≤10%** | ≥30 | tolerance gate |
| `ar/id_oos` (worst cell) | **≤4.6%** (Arm A) | ≥66 (~65) | tolerance gate |
| path-assertions (crisis / harm-to-others / medical-referral) | **none** | — | **harm gate only** (no % tolerance — a 10% tolerance on a cell asserting crisis escalation would mean accepting 1-in-10 crisis mis-routes) |

Built in `tolerances.py` as a **per-cell** config, separate from BC3 (verified: BC3's `insufficient_to_assert` reads only `n_floor`+`delta`, never a mis-route count — a test now locks that the two gates don't collapse). N floor is **derived** from the tolerance (`ceil(3/tol)`), not asserted.

**OPEN — `en/id_oos` bound (needs your call).** Your three buckets named `in_scope`/`far_oos` (easy) and `ar/id_oos` (worst) but not `en/id_oos`. I set it **fail-closed to the tight 0.046** as a recommendation, because id_oos is where the safety-relevant over-route failure (route-when-should-ABSTAIN) lives and that's language-independent. **Consequence:** at ≤4.6% its derived floor is ~66, so the current `en/id_oos` (35 cases) is **underpowered** — needs ~31 more EN cases (which I can author). If you'd rather treat it as an easy cell (≤10%/30), it's already done at 35. Please pick:
```
en/id_oos tolerance: [ ] 0.046 tight (recommended; needs ~31 more EN cases)   [ ] 0.10 easy (done at 35)   [ ] other: ____
```

---
*Does not gate, and must not be conflated with: the production red-flag detector and ~38% crisis recall — those are **pilot-graduation** gates, separate column. This decision gates **V2 flip-eligibility** only.*
