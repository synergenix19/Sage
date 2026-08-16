# v5 conformance baseline — RECONCILED (supersedes both prior v5 docs) — prod 1f687c57

**This is the single v5 baseline of record.** It supersedes (does NOT delete) the two prior v5 docs, both of
which remain in the repo with their original text and a header pointing here:
- `2026-07-22-bot-behaviour-conformance-matrix-v5-fullgraph-1f687c57.md` — 8/36, "conformance-neutral" (Rohan)
- `2026-07-23-bot-behaviour-conformance-matrix-v5-1f687c57.md` — 6/36, "regression" (this author) — **RETRACTED, see below**

## The honest joint conclusion
Two independent full-graph runs of prod SHA `1f687c57` produced **8/36 and 6/36.** They are **NOT the same
configuration**, so the difference cannot be read as either drift or LLM variance:

**The runs differ on exactly one flag — and it is a routing-relevant one:**

| flag | Rohan's run (8/36) | this author's run (6/36) | prod (railway DESIRED) |
|---|---|---|---|
| `SAGE_COSINE_ABSTAIN_THRESHOLD` | **0.42** | **0.0** | **0.42** |
| (all other ~26 config vars) | identical | identical | — |

`0.0` is the config default and is documented **"FAIL-OPEN (never abstains = pre-fix behaviour)"** — i.e. the
6/36 run had the KB cosine-abstain gate effectively **disabled**, which is **off-prod** (prod runs 0.42). The
per-category disagreement is isolated to {S3a, §1d, §1e}, but with a config confound present, **those 3 cells
cannot be attributed to sampling noise** — the cosine difference is an uncontrolled variable.

**Therefore:**
- **The prod-faithful v5 baseline is 8/36** (Rohan's run — cosine 0.42 matches prod, all other flags match).
- **The 6/36 run is NOT a valid prod baseline** — it ran with the KB abstain gate off-prod. Retracted as a
  baseline (see retraction).
- **Drift vs v4 is INDETERMINATE.** No cross-SHA drift claim is defensible until a controlled variance run at
  FIXED prod config exists.

## RETRACTION (this author, explicit)
My `2026-07-23` doc claimed the parallel routing streams caused a real conformance regression (8→7→6, §1e/§1d
fell 5→4, "nobody caught it"). **RETRACTED — twice over:** (1) a same-SHA run disagreed on exactly the cells I
called regressions; (2) my run was not even at prod config (cosine 0.0 vs prod 0.42), so it was never a valid
prod measurement to read a trend from. I read a trend off single, un-characterized, and — it turns out —
off-prod runs. That is the error, owned.

## FINDING — the parity guard has a readback-coverage hole (instrument defect in #360)
Both runs passed the flag-parity guard as **VERIFIED** despite differing on `SAGE_COSINE_ABSTAIN_THRESHOLD`.
Root cause: when the `/health/version` serving readback is available, the guard compares parity **only on the
vars prod exposes there** — 8 `*_raw_env` flags (crisis_tiering, skill_media, route_precedence,
medical_redflag_guard, venting_suppression, ipv_preemption, d1_screen, d1_screen_shadow). The other ~19 config
vars `config.py` reads — including cosine/knowledge thresholds, runner-up margins, model names — are **not in
the readback, so they are silently un-asserted.** The guard's "VERIFIED" is only as strong as the readback's
coverage, and the coverage is partial. **Fix (guard hardening ticket filed):** assert EVERY config var — for
vars absent from the serving readback, fall back to railway DESIRED (the guard already fetches it) and FAIL if
any config var is matched by neither source. Ticket: `2026-07-23-parity-guard-readback-coverage-gap.md`.

## Rows read (unchanged content, now correctly attributed to the prod-faithful 8/36 run)
- **§6 / IPV: unchanged** — `SAGE_IPV_PREEMPTION=false` (reverted); E7 contributes nothing, consistent with
  the enable probe. No IPV preemption in any cell.
- **§1c over-escalation present** — the known, independently-validated false-positive Part A removes by
  construction. This is the clean "before."
- **Zero `medical_referral` across all 180 cases** despite `SAGE_MEDICAL_REDFLAG_GUARD=true` — candidate
  emergency-phrase probe (possible same verbatim-miss class as E7/CF-005); corpus doesn't directly test it.

## Provenance of the process (not just the SHA)
**#360 merged AHEAD of this reconciliation step.** The planned sequence was reconcile → merge; what actually
happened was merge (in a parallel stream) → reconcile. Recorded for process provenance, not blame — the
instrument reaching master is the genuine win; this note exists so the record shows the sequence that actually
happened rather than the one planned. (Provenance discipline applies to process as much as to SHAs.)

## What this baseline blocks/unblocks downstream
- **Variance characterization (next):** N=3–5 on `1f687c57` at FIXED prod config (cosine **0.42**, every config
  var mirrored, not just the 8 readback flags), per-category, **§1c `escalate_crisis` cells called out** — if
  those cells are themselves noisy, Part A's acceptance must be a multi-run read, not a single measurement.
- **Part A** acceptance is defined against the measured band from that run, reading against the **8/36
  prod-faithful** baseline (not the retracted 6/36).

## AR: UNMEASURED (0/180) — no Arabic corpus in the harness (Probe #1). EN numbers are English-graph only.
