# Gate-6 Values — DRAFT proposal for sign-off

**Date:** 2026-06-22 · **rev 2026-06-23** (coordinator + clinical-lead review folded in).
**Status:** SIGNED except #4-arm, 2026-06-23. Clinical **#3 (0.80) + #7 (1.0/4.0)** SIGNED (clinical lead). Engineering **#5 (30) + #6 (8)** SET. Product/risk owner **SIGNED #1 (δ=0.05) + #2 (per-stratum 0.05/0.03)**, and risk-accepted **#4 in principle — but the BINARY ARM is unspecified**: POC-phased (≤4.6% @ N≈65 + ≤1%/~300 pre-commit) **vs** ≤1% up front (~300). Until the arm is named the `ar/id_oos` cell cannot be sized (schedule gate). Every other value is real and signed. **Not closeable by this doc:** §3a (safety determination, native-dialect+task#21 only) and A2 set *existence* (labor, not approval) — see companion + brief.
**Companion:** `2026-06-22-A1-boundary-freeze-DRAFT.md`, harness spec §1.4/§2.4.

---

## Decision ledger (who sets each value)

| Row | Structure | The number | Set by | Status |
|---|---|---|---|---|
| #1 δ tolerance | endorsed | **0.05** | product / risk owner | ✅ SIGNED 2026-06-23 |
| #2 δ granularity (per-stratum) | endorsed | **0.05 / 0.03 worst-cell** | product / risk owner | ✅ SIGNED 2026-06-23 |
| #3 abstain floor | endorsed | **0.80** | clinical lead | ✅ SIGNED 2026-06-23 |
| #4 mis-route bar + phasing | endorsed | risk-accepted; **ARM UNSPECIFIED** (POC-phased vs ≤1%-upfront) | product / risk owner | ⚠ ARM PENDING — gates ar/id_oos sizing |
| #5 per-cell N floor | endorsed | 30 | engineering | ✅ set |
| #6 per-skill min-N | endorsed | 8 | engineering | ✅ set |
| #7 loss weights | ordering endorsed | **1.0 / 4.0** | clinical lead | ✅ SIGNED 2026-06-23 |

Engineering supplies #5/#6 and the *mechanics* of #1/#2; it does **not** supply the digits in #3/#4/#7. Those encode relative clinical harm or risk acceptance and must come from their owners.

## Proposed values

| # | Value | Proposed | Tag | Rationale |
|---|---|---|---|---|
| 1 | **δ parity tolerance** | 0.05 (AUGRC units, 0–1) — *owner to confirm* | ⚠[risk] | A 5-point generalized-risk gap is a modest dialect penalty; tighter risks an unachievable bar given EN↔Khaleeji embedding-space differences (research found *zero* validation of shared-space parity), looser tolerates real degradation on Sage's reason-to-exist axis. |
| 2 | **δ granularity** | per-stratum: 0.05 in_scope/far_oos, **0.03 ar/id_oos** — *owner to confirm* | ⚠[risk] | The worst cell concentrates unrecoverable override-misroutes; a uniform δ lets it hide behind easy-cell slack. Tighter δ on the worst cell is conservative. |
| 3 | **abstain floor (6b-i)** | *clinician supplies* (eng straw-man 0.80) | ⚠[clin] | A floor is needed; the exact value is a clinical tolerance for over- vs under-abstention. **Engineering does not supply this digit.** |
| 4 | **mis-route bar (6b-ii)** | *owner supplies*; eng proposal = POC accept "0 obs, ≤4.6% @ N≈65", pre-commit ≤1% (~300) pre-pilot | ⚠[risk] | See "Statistical honesty" below — the ≤4.6% is a rule-of-three **upper bound**, not evidence of safety. Whether it's acceptable for a zero-exposure POC is a risk-acceptance call the owner makes. |
| 5 | **per-cell N floor** | 30 held-out rows | [stat] | Below ~30 the bootstrap CI on AUGRC is too wide for a binding **parity/AUGRC** verdict → `insufficient_to_assert`. **This is a floor below which you must NOT assert — not a point above which you are safe.** It certifies the parity verdict only (see coupling note). |
| 6 | **per-skill min-N** | 8 held-out examples | [stat] | Below ~8 paraphrases a per-route threshold overfits; fall back to the cluster threshold. |
| 7 | **loss weights** | ordering endorsed (override > misroute); **ratio clinician-supplied** (eng straw-man 4×) | ⚠[clin] | Override-misroutes are unrecoverable (no abstain fallback, §5.3) so weigh heavier — *ordering* endorsed. The *magnitude* (e.g. 4×) is a clinical harm ranking; **engineering does not supply this digit.** |

## Statistical honesty (clinical-lead-reinforced, 2026-06-23)

1. **The mis-route bar's ≤4.6% is a rule-of-three upper bound, not a measured rate.** 3/65 ≈ 4.6% is the one-sided 95% upper confidence bound for zero observed events in N≈65. It is **not** evidence the true override-misroute rate is below 4.6% — only that rates up to 4.6% cannot be ruled out at that N. Reaching a ≤1% bound the same way needs ~300 clean cases, which is why the pre-pilot figure is ~300 (internally consistent).

2. **#4 and #5 measure different things at different N — do not conflate.** The per-cell N floor (#5 = 30) certifies the **AUGRC/parity** verdict. It does **not** certify the **mis-route bar** (#4): 30 rows cannot distinguish a 1% from a 4.6% override-misroute rate. The mis-route bar carries its own N (≈65 for the POC bound, ~300 for the pilot bound). Anyone reading "N≥30" as certifying #4 is misreading it; this note exists to prevent that.

## Schedule gate — #4 blocks worst-cell labeling (do not let provisional harden)

**HARD GATE for Track A (now narrowed to the arm):** #4 is risk-accepted, but the `ar/id_oos` held-out cell **must not be sized or labeled until #4's ARM is named** — POC-phased (N≈65) vs ≤1%-upfront (~300). The acceptance closed; the *number* did not, and the number is the cell's N. Sizing to the wrong arm is a 4–5× swing in worst-cell labeling — exactly the F2 rework, re-introduced at execution time. **All other (lang × stratum) cells may proceed now against the frozen boundary** — #4 sizes only the worst cell. The arm is the single value still standing between A2 and full sizing.

## Sign-off

```
#3 abstain floor (0.80) + #7 loss ratio (1.0/4.0):  SIGNED clinical lead (name: ______)  Date: 2026-06-23
#1 δ (0.05) / #2 granularity (0.05/0.03):           SIGNED product/risk owner   Date: 2026-06-23
#4 mis-route bar — accepted; ARM (65 vs 300):       ______________  Date: ____  (ARM PENDING — gates sizing)
#5 N floor (30) / #6 min-N (8):                      SET engineering, on rationale     Date: 2026-06-23
```
Clinical + engineering rows are signed; the three risk rows carry provisional working values and are **not risk-accepted** until the product/risk owner signs. A clinician's approval does not cover risk acceptance — that separation is deliberate.
