# G6 Item #4 — Mis-route Arm: Decision Request (Product Owner)

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

---
*Does not gate, and must not be conflated with: the production red-flag detector and ~38% crisis recall — those are **pilot-graduation** gates, separate column. This decision gates **V2 flip-eligibility** only.*
