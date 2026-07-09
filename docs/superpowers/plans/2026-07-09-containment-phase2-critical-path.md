# Containment Phase 2 — Task-Sequenced Plan Against 2026-07-31 (for review BEFORE build)

**Task 0 SIGNED** (Vee clinical + Rohan arch/PO, 2026-07-09). This sequences the build. **Human-gate latency, not engineering, has been the schedule risk every time** — so the critical path is drawn around the clinician touchpoints, and those are front-loaded.

## The serial spine (must be in order — each depends on the prior)
- **T1 — `containment_directive` state field** (SageState + per-turn reset). ~hours. Blocks everything.
- **T2 — `contain` Rules-Service action** (4th action; CMS-authorable draft→review→approve→publish). Depends on T1. ~1 day.
- **T3 — ONE conditional graph edge** (directive present → knowledge_retrieve → freeflow L3+L4, or skill_executor). Depends on T2. ~hours.
- **T4 — wire the three approved families to `contain`** (harm-intrusive enrich, OCD upgrade, safeguarding). Depends on T3. Per-family.

## Parallelizable (no inter-dependency; can run alongside the spine)
- **P5 — containment template** (validate→psychoeducate→differentiate→**refer**→engage; the ego-syntonic→crisis branch). Clinical content; can draft during T1–T3.
- **P6 — KB content** for the families (feeds L4). Content work; independent of the graph.
- **P7 — AR checklist / bilingual** (few-shot ≥3 EN+AR, Khaleeji renderings, per-language fail-safe). Independent.

## The safeguarding family (#1, TARGET 2026-07-31) — its clinician touchpoints ARE the critical path
Safeguarding rides T4 but needs its OWN clinician sign-offs BEFORE it can wire:
- **HG-1 — safeguarding trigger patterns** (third-party/behavioural child-harm; the first-person-vs-third-party split). Clinician. ← front-load THIS week.
- **HG-2 — tier + posture** (referral-with-urgency + mandatory L2 review; L3-adjacent, clinician-ruled).
- **HG-3 — referral copy** (safeguarding signpost, verbatim-pinned like #218's ERP line).
**Backward math from 07-31:** T1–T3 (engineering, ~3-4 days) can start now; but safeguarding's HG-1/2/3 gate its T4 wiring. If HG-1/2/3 don't land by ~mid-next-week, T4-safeguarding slips → 07-31 slips. **Front-load HG-1/2/3 now, in parallel with T1–T3.**

## Recommended kickoff (this week)
1. Engineering: **T1 now** (state field, gated behind default-OFF — inert until T2/T3/T4 + sign-offs, per the never-build-live-ahead-of-sign-off rule; the FLIP is gated, the scaffolding is not).
2. Clinician (Vee): **HG-1 safeguarding patterns** packet — the front-loaded human gate.
3. Parallel: P5 template draft, P6 KB seed.

**Not started blind:** this is the plan for review. On approval, T1 begins; the safeguarding clinician packet (HG-1) goes out same-day, since it's the long pole.
