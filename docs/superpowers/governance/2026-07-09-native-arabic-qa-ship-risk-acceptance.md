# Risk Acceptance — Native-Arabic Generation to Internal-QA Production

**Date:** 2026-07-09 · **Decision owner:** PO / coordinator · **Type:** documented risk acceptance (NOT "no risk")

## Decision
Defer the formal offline register measurement (rating pass + Layer 2). Optionally ship native-Arabic **generation** to an internal QA/test cohort in production to observe break-it behaviour ahead of the measurement.

## What is being accepted — honestly
Serving native-Arabic generation **bypasses the output-side deterministic gates**, which run on the English response *pre-translate* (`output_gate`, verified):
- **ACCEPTED GAP — identity substitution** (`CUO-ID-001`, "wellness companion, not a therapist"): native output may present as a clinician or give a diagnosis, ungated. Regulated line.
- **ACCEPTED GAP — cultural_output blocklist**: native output may breach cultural rules, ungated.
- **ACCEPTED GAP — contraindication / banned-opener / format** output gates: ungated.
- **NOT affected — crisis:** detection/response short-circuits *before* generation (verified: crisis invariance). The MoHAP-helpline path stays intact.

This is a **safety-control bypass, not deferred optimisation.** QA *will* reproduce these bypasses on purpose — that is the expected outcome, and the input to sizing the Arabic gate-port. It must not be recorded as "no risk / debt."

## Conditions (required for this to be defensible)
1. **Internal QA/test accounts ONLY** — no real or vulnerable users (same containment as the shadow cohort). If any real user can reach it, this acceptance is void.
2. **Flag-gated + instant kill-switch** (off ⇒ revert to the gate-safe translate-out path).
3. **Time-boxed** QA window with a named end date.
4. **Findings logged**; identity/cultural bypasses expected and catalogued toward the gate-port.

## Exit criterion (non-waivable)
Native generation reaches **any real user** only after the **clinician-signed Arabic gate-port** (output gates re-implemented for native Arabic) exists. This decision does not waive that.

## Notes of record
- **Formal measurement (register rating + Layer 2): DEFERRED — debt, to be scheduled.**
- **Technical:** the shadow arm is **containment-only by design** (never served). Serving native to QA requires **building a flag-gated serve-native path** — it is *not* a flag flip.
- **Safe alternative** for user-perceived native-quality Arabic **without** the bypass: **#220** (translate-out gender fix) — fires *after* every gate.
