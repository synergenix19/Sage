# Critical-path work orders (2026-06-14) — clinical/ML, start now

These two items are the real critical path. **Both are independent of every branch/merge/fork
question** (R1, PR #15, SF-2/C1 base decision). Neither has an engineering precondition. Start
both today; the merge choreography is the less urgent track.

---

## A. 05a — dbt_tipp PMR step (pilot long pole) · owner: CLINICAL AUTHORING

PMR is the **missing second P of TIPP** (T-I-P-**P**). Restoring it is fidelity, not a design
change. It is the lowest-risk component (no cardiac/ED/cold contraindication) and serves as both
the low-arousal closer and the low-risk default entry the 05c branch routes to.

**Turn-key authoring brief** — author one skill step; engineering inserts it mechanically and
wires transitions (`paced_breathing → paired_muscle_relaxation → check_in`). Slots into
`dbt_tipp.steps` after `paced_breathing`, before `check_in`. Fields (skill schema):

- `step_id`: `paired_muscle_relaxation`
- `goal`, `technique` (paired/progressive tense-and-release), `technique_description`, `tone`
- `examples`: EN + AR, **Arabic at position [0]** (the executor's `[:2]` few-shot path is
  language-blind; AR must be first). **No em dashes** in any content string (they mirror into
  LLM output; use commas).
- `contraindications`: lowest-risk component; note any minor ones (e.g., acute injury) but it is
  the safe default.
- `completion_criteria`.

No engineering precondition. Architecture-independent (a `dbt_tipp.json` edit that works on
master today and survives R1). Required before pilot.

---

## B. 02 — passive-SI recall · owner: CLINICAL (phenotypes) + ML (build + eval). **SCOPE CORRECTED.**

**CRITICAL CORRECTION: S2/MARBERT is NOT built.** (Architecture doc §4, lines 197 & 1438;
`safety_check.py` documents the gap and intended path.) The lock-pass framing "measure MARBERT
(S2) recall" assumes a layer that does not exist. Today passive-SI recall is whatever **S1
(regex)** catches; **S3 (BGE-M3) adds 0** on the passive-SI set (per
`scripts/safety_confusion_matrix.py` docstring). So 02 is **not a measurement task** — it is:

1. **Clinical** — author the passive/veiled-SI **eval set**: phenotype taxonomy, EN + Gulf-Arabic
   veiled phenotypes. **Seed already on record** (bootstrap from these, don't start cold):
   - negation-gap: 5/6 SI-disclosures-with-negation missed (SK-EN-001);
   - safety-detection-baseline: 12 documented FNs (2 negation_check + 10 veiled).
2. **Eng/ML — measure the CURRENT baseline now** (no precondition):
   `scripts/safety_confusion_matrix.py` runs the S1 baseline + a Crisis-recall-≥95% KPI check.
   Run it against the new eval set to **quantify the gap today**.
3. **ML — BUILD S2/MARBERT** (the real lift; the intended dialectal-Arabic + passive-SI layer).
   This is what closes the ≥95% recall gap — measurement alone cannot.
4. **Re-measure** to validate S2 closes the gap.

Highest stakes on the board (gates the Crisis recall ≥95% KPI). Branch-independent. The "untested
S2" in the lock pass is more precisely an **unbuilt** S2 — surfacing this before clinical/ML spin
up a measurement that can't run.

### MEASURED BASELINE (2026-06-14) — and the false-comfort trap it exposes

Ran `scripts/safety_confusion_matrix.py` today: **crisis recall 100%, passive_si 25/25, KPI PASS**
on its fixture (`tests/fixtures/safety/cases.py`, 53 cases). **Do NOT read this as coverage.**
`ea33684` shows S1 was *tuned* to pass this curated SF-1/SF-6 suite (recall 66.7% → 100%); memory's
"66.7% baseline" is now stale. This suite is **not** the real passive-SI population — it is the
green-on-a-surface-it-doesn't-cover trap (same pattern as the unit-gate/test_nodes gap).

**The real number is already on record (Exhibit A, own data):**
- `docs/governance-table-2026-06-06.md` (owner: Clinical Lead): **CRADLE Bench S1 recall = 37.1%**
  (232 crisis cases) vs ≥95% KPI — **FAIL**; **self-harm recall = 18%** (92 cases) vs ≥50% interim
  KPI — **FAIL**.
- `docs/crisis-recall-gap-2026-06-05.md`: **S3 adds 0** above S1 on the CRADLE passive-SI slice (75
  cases) at any threshold; "full semantic coverage requires MARBERT (S2)."
- **Arabic crisis recall is entirely unmeasured** — CRADLE is English-only. A Khaleeji/Arabizi
  crisis bench is itself an open prerequisite.

**So the live deterministic crisis recall on the representative bench is 37.1% (self-harm 18%),
S3 contributes nothing, and S2 — the layer meant to close it — is unbuilt.** The curated suite's
100% overstates this. 02's eval set should be CRADLE-class (+ the missing Arabic bench), not the
SF-1/SF-6 fixture.

### Headline consequences (escalate to the lead + DPIA/DPO line — not buried in task 02)

1. **Governance/disclosure.** The represented crisis architecture (S1+S2+S3 OR-fusion) differs from
   what runs: **S2 absent; real-bench recall 37.1% / self-harm 18%.** This *is already disclosed*
   (`governance-table-2026-06-06.md`, owner Clinical Lead; `crisis-recall-gap-2026-06-05.md`) — it
   is **not** hidden — but it must be re-surfaced **as the headline of current work**, dated, owner
   named, on the PDPL-sensitive automated-crisis-classification surface, rather than living as a
   scope note on task 02.
2. **Re-ranking.** SF-2, C1, the R1 fork, PR #15 are all "route to a skill once a turn is safe."
   None matters at the rate a missed passive-SI/self-harm turn does, and the layer that catches
   those (S2) is the one confirmed not to exist. **Building S2/MARBERT is therefore the highest-
   priority engineering effort in the program** — state it that way to whoever allocates ML time.
   Keep the merge choreography parked, but do not let "parked" read as "the lower-priority items
   get attention while the critical one waits."
3. **Pilot gate.** A pilot must not start with S2 unbuilt and crisis recall at 37.1% (self-harm 18%)
   on the only representative bench — and with Arabic unmeasured entirely. **Flag:**
   `scripts/check_pilot_gate.py` reportedly exits 0; confirm that gate scores against the CRADLE
   bench (and an Arabic bench), not the curated SF-1/SF-6 suite — else the pilot decision inherits
   the same false-comfort.

---

**Engineering standing by to:** insert the authored PMR step + wire transitions (A); run/extend
`safety_confusion_matrix.py` against the eval set and integrate S2 once built (B). Neither waits
on the SF-2/C1 base decision or any merge.
