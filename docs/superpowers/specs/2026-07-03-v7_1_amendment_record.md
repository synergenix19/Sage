# v7.1 Amendment Record — Crisis Tiering (2026-07-03)

**Status:** spec artifact riding `feat/crisis-tiering` (Absolute Rule 1: spec + code merge together).
**Clinical sign-off:** G1–G5 + G8 signed 2026-07-03 (see `governance/2026-07-03-crisis-tiering-clinical-signoff.md`).

## §5.1 — OR-fusion, amended
**v7 (superseded):** *"OR-fusion: S1 OR S3 catching → `crisis_response`, regardless of crisis_state."* Binary {safe ↔ crisis}.

**v7.1:** detection is unchanged (S1 OR S3 still fire on every signal), but the fired-signal set is mapped to a **tier** that grades the RESPONSE:
- **T2 (acute):** any S1 keyword flag (all languages); OR an S3 semantic hit in `ar`/`az`. → `crisis_response` (RED). This is the non-negotiable safety floor.
- **T1 (warm):** an S3 semantic hit **alone** (no keyword corroboration) in `en`. → normal graph with `supportive_posture` (validate, gently explore, offer-not-force). NOT `crisis_response`.
- **none:** no signal.

The boundary is data: `rules/data/safety/tier_routing.json` (3 rules, clinician-editable). `safety_check` reads the resolved tier; it hardcodes no boundary. Gated by `SAGE_CRISIS_TIERING` (default **OFF** → behaviour identical to v7 / master).

## §5.6.1 — "Dialect mirroring rules" wording, clarified
The v7 spec row read *"Dialect mirroring rules,"* which was ambiguous; the implementation (CU-DM-001 = **"Khaleeji register calibration"**) and the signed L0 v2.2.0 (register-matching scoped to **tone/formality**, not sub-dialect) mean **fixed Khaleeji** is the baseline. §5.6.1 is corrected to read "Khaleeji register calibration (fixed register; tone/formality matched, not user sub-dialect)." Any move to MSA/hybrid is a future amendment (G6), not a bug.

## Crisis-recall KPI — REDEFINED under v7.1 (binding)
> **Under v7.1, "crisis recall" = the fraction of true-SI corpus cases that resolve to TIER T2 (i.e. route to `crisis_response`).**
> A case whose only fired signal is `s3_semantic` in English resolves to **T1** and therefore **counts as a recall MISS**, even though a detector technically fired.

This is the single place tiering could silently degrade safety while every detector still "works." The ≥95% recall KPI is measured against this definition. The blocking regression (`test_crisis_tiering_recall`, CRADLE self-harm + passive-SI + Arabic) runs with the flag **ON** and asserts flag-ON T2-recall **≥ the committed flag-OFF baseline** (`tests/fixtures/recall_baseline_2026-07-03.json`). The safety argument (per the CRADLE sweep: S3 adds 0 recall above S1 in English) predicts the moved set is empty — the regression is what proves it.

## Scope guards (unchanged from §H)
Detection sensitivity untouched; T2 floor absolute; flag OFF until G8 clears + the recall regression is green + the staging tester-battery replay is attached to the clinician packet.
