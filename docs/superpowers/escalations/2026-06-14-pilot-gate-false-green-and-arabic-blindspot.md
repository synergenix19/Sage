# ESCALATION (2026-06-14) — pilot-gate false-green correction + Arabic crisis blind spot

**Severity:** stop-the-line for anything pilot-facing on the crisis path.
**Surface:** automated crisis classification — PDPL-sensitive. Route to Clinical Lead + DPIA/DPO.
**Author/date:** engineering, 2026-06-14. **Numbers of record:** docs/governance-table-2026-06-06.md.

This is recorded at the same volume as the original recall gap — not folded into a backlog task.

---

## 1. The pilot-gate readiness signal was wrong; now corrected (governance event)

Until 2026-06-14, `scripts/check_pilot_gate.py` scored `_TP_PASSIVE_SI_RECALL_GAPS` from the
**curated SF-1/SF-6 fixture** — the suite S1 was *tuned* to pass (commit ea33684, recall
66.7%→100%). Those gaps read "resolved," so the gate **exited 0 / PASS**. Meanwhile the
representative-bench crisis recall was **37.1%** (self-harm 18%) and Arabic was unmeasured.

**The consequence to name plainly:** a "green pilot gate" existed that could have been cited
as evidence the automated-crisis-classification surface met a ≥95% standard **it does not
meet**. The readiness signal certified PASS against a fitted fixture, not the real population.
On a PDPL-sensitive surface, a readiness artifact that misrepresents crisis-detection
performance is itself a governance event, not merely an engineering bug.

**Correction (this change):** the gate is re-pointed at the CRADLE Bench and made
**fail-closed**. It now reports — and **BLOCKS** on — the real numbers:
- overall crisis recall **38.4%** (89/232) vs ≥95% — **FAIL** (live S1 floor; ~37.1% locked
  2026-06-05, now 38.4% as S1 improved — the gate measures live and will reflect S2 when built);
- self-harm recall **19.6%** (18/92) vs ≥50% interim — **FAIL**;
- Arabic crisis bench **absent → FAIL-closed**;
- curated SF-1/SF-6 fixture **demoted** to a non-verdict regression-sanity line.
Gate exit code is now **1 (BLOCKED)**. The record should show the readiness signal was wrong
and is now fixed, owner-named, dated — not just that "a gap exists somewhere."

## 2. Arabic crisis recall is unmeasured — its own line item, its own owner

CRADLE is **English-only.** For a Khaleeji-first product, **zero measured Arabic crisis
recall** is arguably a larger hole than the 37.1% English number, because 37.1% is at least
known. This is **not a subset of the S2/MARBERT (English) work** — it is a co-equal gap that
needs its own bench, its own data, and its own go/no-go. The gate now fails closed on its
absence: "we have not measured Arabic" keeps the pilot red until an Arabic crisis bench exists
and passes, **or** an accountable owner explicitly signs to accept the unmeasured risk.
**Owner: needs assignment (clinical + ML), separate from the English S2 build.**

## 3. Pilot posture: no-go by default

Crisis recall **38.4% / self-harm 19.6%** on the only representative bench, **Arabic
unmeasured**, and the component meant to close it (**S2/MARBERT**) **unbuilt** — the system
cannot detect roughly two of three crisis turns and four of five self-harm turns in the one
population measured, and nothing in Arabic. **Pilot is a NO-GO by default.** Re-pointing the
gate is the *symptom* fix (the instrument now tells the truth); the *disease* fix is S2/MARBERT
+ a CRADLE-class English set + an Arabic crisis bench re-measuring above the clinical line.
Proceeding to pilot before then is an explicit, signed clinician risk-acceptance against the
real number — not a default the momentum of "everything else is turn-key" should carry past.

**S2/MARBERT is the highest-priority engineering effort in the program**, ranked above
SF-2 / C1 / the R1 fork / PR #15 (all of which only route once a turn is already deemed safe).
