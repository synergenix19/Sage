# Risk acceptance — pilot proceeds with known crisis-recall gap (2026-06-14)

**Decision:** the product owner (synergenix) has **explicitly accepted, for now**, the
crisis-recall risk in order to deploy production for **pilot user feedback**. Production is
redeployed to current master on this basis. "We will improve it later."

**This is the explicit risk-acceptance the re-pointed pilot gate required** to override the
NO-GO default. Recorded here, dated, on the PDPL-sensitive automated-crisis-classification
surface, so the readiness decision is on the record as a *knowing* override — not a silent one.

## What is being accepted (the real numbers, not the curated suite)
- CRADLE Bench S1 crisis recall **37–38%** (live ~38.4%, 89/232) vs ≥95% KPI — FAIL.
- Self-harm recall **19.6%** (18/92) vs ≥50% interim — FAIL.
- **S2/MARBERT unbuilt**; S3 adds 0 on the passive-SI slice.
- **Arabic crisis recall entirely unmeasured** (CRADLE is English-only).
Source: docs/governance-table-2026-06-06.md; docs/crisis-recall-gap-2026-06-05.md;
docs/superpowers/escalations/2026-06-14-pilot-gate-false-green-and-arabic-blindspot.md.

## What remains true / mitigations in place
- S1 deterministic crisis lexicon + crisis_response path are unchanged and still fire for the
  crises they do catch; explicit suicidal/self-harm language is detected. The gap is veiled/
  passive/indirect phrasing and all Arabic.
- The fix is unchanged: **S2/MARBERT build + CRADLE-class English set + an Arabic crisis bench**
  re-measuring above the clinical line (tasks #18, #21). This acceptance is temporary, for pilot
  feedback, and does not retire those.

## Open governance flag
The pilot gate framed the go/no-go as a **clinical-lead** call. This acceptance is recorded as
the **product owner's** decision; it should be **co-signed by the clinical lead** for the record
(name + date). The pilot should also carry the 05d instrumentation (gate completion / self-report
reliability) so the accepted risk is monitored, not just assumed.

**Recorded by:** engineering, 2026-06-14, at the product owner's explicit instruction.
