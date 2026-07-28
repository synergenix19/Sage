# Conformance instrument — noise-floor characterization (N=3, full prod config) — graph @ 1f687c57

**Purpose:** publish the conformance instrument's noise floor before its readings gate any decision (the
ARCHITECTURE_BOUNDARIES rule earned this month). Until this existed, single-run deltas were read as signal —
producing the retracted "8→7→6 regression." This is the calibration that makes v5 mean something and gives
Part A an attributable acceptance target.

## Method
Three independent full-graph runs of the same graph (prod SHA `1f687c57`; master's `src/**` is byte-identical
to it, verified), each at the **identical, fully prod-faithful config**: the fixed flag-parity guard (#366)
reported **VERIFIED with 0 diffs and 0 unverified vars** — all 41 railway vars mirrored, `SAGE_COSINE_ABSTAIN_
THRESHOLD=0.42` and `SAGE_INFO_REQUEST_CONSULT=true` included (the two vars the earlier runs silently missed).
`instrument_faults=0` on every run. Runs executed one-at-a-time (the chained wrapper hit an environment
duration limit twice; single ~13-min runs complete reliably).

## Result — the aggregate is stable; the noise is per-category and bounded at ±1

**Totals: 10/36, 10/36, 10/36 — zero aggregate variance across N=3.** The headline conformance number is stable.

**32 of 36 categories are fully stable (band 0). 4 carry ±1-case noise:**

| category | r1 | r2 | r3 | band | note |
|---|---|---|---|---|---|
| S3a | 2/5 | 3/5 | 2/5 | ±1 | partial-cell noise (never reaches 5/5 → verdict unaffected) |
| S4a | 2/5 | 1/5 | 1/5 | ±1 | partial-cell noise |
| **§1d** | 5/5 | 4/5 | 4/5 | ±1 | **verdict flips 5/5↔4/5** |
| **§1e** | 4/5 | 5/5 | 5/5 | ±1 | **verdict flips 5/5↔4/5** |

**§1d and §1e anti-correlate** — when one is 5/5 the other is 4/5, and they trade between runs. That is exactly
why the aggregate holds at 10 while two category verdicts flip. These are the **same two cells** I earlier
reported as a "regression" (§1d/§1e falling 5→4); this N=3 run **confirms they are sampling noise, not drift.**

## The reading rules this establishes (for the drift gate and any future comparison)
1. **Aggregate (X/36): noise floor ±0 across N=3.** A change in the total IS worth investigating — but confirm
   with a 2nd run before calling it, since ±1 is plausible at larger N.
2. **A single category's verdict carries ±1-case noise.** Do NOT read one category moving 5/5↔4/5 as signal —
   §1d/§1e prove a verdict can flip on identical config. A category is "moved" only if it shifts **>±1 case**
   or moves consistently across ≥2 runs.
3. **The drift gate must alert on movement OUTSIDE this band**, not on any delta — else it cries wolf on
   §1d/§1e every run and gets disabled (disarmed-alarm). Threshold: aggregate delta ≥1 confirmed by a 2nd run,
   OR any single category moving >±1 case.

## §1c — Part A's acceptance target is on STABLE ground
§1c is **byte-identical across all three runs:** `{escalate_crisis: 2, presence_only: 2, self_help_skill: 1}`,
1/5. Part A removes the 2 `escalate_crisis` by construction; because those cells do **not** flicker, a
post-Part-A measurement showing `escalate_crisis → 0` is **attributable to Part A, not sampling.** A single-run
read suffices for the §1c acceptance, with a 2-run confirm as cheap insurance. (Contrast: if §1c had been in
the noisy set, Part A acceptance would have required a multi-run read — the reason we characterized first.)

## The prod-faithful v5 baseline is 10/36 (supersedes the earlier config-artifact numbers)
The v5 number rose as config fidelity rose — **6/36** (cosine off-prod at 0.0) → **8/36** (cosine fixed but
`info_request_consult` and others still off) → **10/36** (fully prod-faithful, guard-VERIFIED on all 41 vars).
The first two are config artifacts, not variance; **10/36 is the first fully prod-faithful v5 measurement** and
is the baseline of record. This supersedes the reconciled doc's interim "8/36 prod-faithful" (which predated
the guard-coverage fix that surfaced the remaining un-mirrored vars). AR remains **0/180 UNMEASURED** (Probe #1);
EN numbers are English-graph only.

## Downstream
- **Part A** acceptance: §1c `escalate_crisis` 2 → 0 by construction, read against this 10/36 baseline; single
  run sufficient on the stable §1c cells, 2-run confirm optional.
- **Drift gate** (when built): thresholds per the reading rules above; sentinel set should include the 4 noisy
  cells explicitly so their ±1 is expected, not alarmed.
- The parallel-streams question ("did the three routing streams move conformance?") remains **formally
  unanswered** — this characterizes the instrument, not a v4→now controlled comparison; that would need v4
  re-measured at the same full config.

## Provenance
Graph SHA `1f687c57` (src-identical to master); guard `measure_layer1_fullgraph.py` post-#366 (full-config
parity); config VERIFIED 0-diff 0-unverified; faults=0 ×3; corpus `layer1_trigger_corpus.jsonl` (180 EN).
