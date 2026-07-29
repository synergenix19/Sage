# RCA — what is the correct conformance number? (serving vs desired; 8/36 not 10/36)

**Question:** the EN conformance number has been quoted as 10/34, 8/36, 7/36, 6/36, 8/36, 10/36. Which is
correct? **Answer:** the correct **current-SERVING** number is **8/36**. 10/36 is the DESIRED / post-next-deploy
number. This corrects `2026-07-28-conformance-variance-characterization-1f687c57.md`, which labeled 10/36
"prod-faithful" — it is prod-**desired**-faithful.

## The measurements, reconciled
| doc | instrument | cosine | info_request_consult | number | status |
|---|---|---|---|---|---|
| v2 (`...matrix-v2`) | skill_select ISOLATION | — | — | 10/34 | **invalid instrument** — over-counts (skips intent_route freeflow gate) |
| v3 (5b33a0e) | full-graph | — | — | 7/36 | superseded (older graph) |
| v4 (b4d5001a) | full-graph | 0.42 | OFF | **8/36** | valid at that config/SHA |
| v5 "mine" (1f687c57) | full-graph | **0.0** (off-prod) | OFF | 6/36 | **RETRACTED** — cosine off-prod |
| v5 "Rohan" (1f687c57) | full-graph | 0.42 | OFF | **8/36** | valid — equals current SERVING config |
| variance N=3 (1f687c57) | full-graph | 0.42 | **ON** | 10/36 | **DESIRED config, NOT served** |

## Root cause — two confounds, one still live
1. **Instrument (resolved).** v2's 10/34 was skill_select isolation, which over-counts by skipping the
   intent_route freeflow gate (the F6-phantom class, per the v2 doc's own supersession note). Full-graph
   `app.ainvoke` is the only valid instrument. Every number from v3 on uses it.
2. **Config, serving-vs-desired (LIVE).** The two vars that move the number — `SAGE_COSINE_ABSTAIN_THRESHOLD`
   and `SAGE_INFO_REQUEST_CONSULT` — are **not exposed in `/health/version`'s `*_raw_env` readback** (only 8
   flags are). So every conformance run, INCLUDING the "guard-VERIFIED" variance run after the parity-coverage
   fix (#366), resolved those two from railway **DESIRED**, because #366 falls back to desired for vars the
   readback does not expose. The variance run set `info_request_consult=true` (railway desired) and measured
   10/36 — but **prod serves it OFF.**

## Empirical settle (measured, not inferred — the discipline this whole thread turned on)
Behavioral probe against prod (1f687c57), info_request about a technique:
- `x-sage-intent: info_request`, **`x-sage-active-step-id:` empty**, **`x-sage-skill-id:` empty** → prod
  returns KB info with **no skill consult**. If `info_request_consult` were serving ON, the consult path
  (`info_request_skill_consult`) would populate active_step_id/skill_id. **It is serving OFF.**
- Cosine 0.42 is served with high confidence (shipped PR#86 / migration 007, long before 1f687c57; requires an
  applied migration). Not directly probed here; noted as inferred-from-deploy-history, not readback-confirmed.

Prod's SERVING config is therefore **cosine 0.42 + info_request OFF = the 8/36 configuration** (Rohan's v5 run).

## The correct number
- **Current SERVING: 8/36** (full-graph, cosine 0.42, info_request_consult OFF). This is what prod delivers to
  users today.
- **DESIRED / post-next-deploy: 10/36** — railway has `info_request_consult=true` already; the running prod
  process (deployed ~07-23) predates that set, so it serves OFF. The next master→prod deploy restarts the
  process, picks up `info_request=true`, and prod begins serving **10/36**. (So the pending deploy moves the
  live conformance number 8→10 by realizing an already-desired flag — independent of Part A.)
- **6/36: retracted** (off-prod cosine 0.0). **10/34: invalid** (isolation instrument).

## The structural finding (the real lesson)
**No conformance run has ever measured against CONFIRMED-serving config for the non-readback vars.** "Prod-
faithful" has meant prod-**desired**-faithful throughout — the same serving-vs-desired gap that has bitten this
project repeatedly (the IPV mid-restart, the deploy-storm), now on the measurement instrument itself. The
parity guard cannot close it (it falls back to desired for unexposed vars). The fix is the parity-ticket
secondary item — **expose ALL routing-relevant config vars in `/health/version` `*_raw_env`** — so serving is
measurable. Until then, every conformance number MUST be labeled "desired-config; serving-unconfirmed for
cosine + info_request_consult."

## Corrections filed
- `2026-07-28-conformance-variance-characterization-1f687c57.md`: "10/36 prod-faithful" → "10/36 prod-DESIRED;
  current SERVING = 8/36 (info_request served OFF, confirmed)." Noise-floor result (±0 aggregate, band on
  {S3a,S4a,§1d,§1e}, §1c stable) is UNAFFECTED — it was measured at fixed config, so it characterizes the
  instrument regardless of which config; only the absolute baseline label changes 10→8 for serving.
- Parity-guard ticket (`2026-07-23-parity-guard-readback-coverage-gap.md`): the /health-readback-coverage
  secondary item is upgraded from nice-to-have to REQUIRED — it is what makes "the correct number" answerable
  at the serving layer.
