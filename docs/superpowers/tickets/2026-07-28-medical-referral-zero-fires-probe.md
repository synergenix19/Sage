# Ticket — medical red-flag guard fires ZERO `medical_referral` across 180 cases; needs a paraphrase-independent probe

**Priority: high (safety detection, this week). Found by the v5 conformance runs.** Possibly the same
verbatim-miss class as E7 and CF-005 — a third detection route with unknown real-language coverage — and it
sits directly under D1's subtle-red-flag branch.

## The observation
Across all 180 EN utterances, in every full-graph run at prod config (`SAGE_MEDICAL_REDFLAG_GUARD=true`),
**no cell ever observed a `medical_referral` disposition.** The guard is ON and the flag is VERIFIED-parity
with prod, yet it produces zero referrals over the whole corpus.

## Why this is not automatically fine
The §1 conformance categories prescribe `self_help_skill`, so the corpus does **not directly test**
medical-emergency dispositions — a zero could just mean "no emergency utterances in the corpus." **But** the
medical red-flag guard (B1 interim, `detect_medical_redflag`) is an **English-only deterministic phrase match**
over the §1 emergency phrase list — the same architecture (verbatim/substring keyword match) that E7 and CF-005
use, and that E7 just demonstrated **fails on naturalistic paraphrase** (fired on 0 of 3 real coercive-control
disclosures despite "covering" the concept). If the medical guard only fires on verbatim red-flag phrasing, its
real-language recall is unknown and possibly near-zero — and it is the guard gating D1's acute-overwhelm→TIPP
contraindication path, so a miss there is a routing-safety miss, not just a disposition miss.

## The probe (this is the actual work)
A dedicated emergency-phrase probe, **paraphrase-independent fixtures** — per the recall-fixture-independence
rule E7 bought (`ARCHITECTURE_BOUNDARIES.md`): fixtures must NOT be the guard's own phrase strings.
1. Build a small set of naturalistic medical-emergency disclosures (chest pain radiating to the arm, worst
   headache of my life, can't feel one side, etc.) phrased as a real user would — **not** copied from the §1
   emergency phrase list.
2. Drive them full-graph at prod config; measure whether `medical_referral` (or the medical-guard path) fires.
3. Report recall on naturalistic phrasing — the number that actually matters — separately from verbatim recall.
4. If recall is low, the guard needs the same remedy as E7/CF-005 (semantic tier or a real paraphrase lexicon),
   as new clinician content with its own sign-off. Do NOT lower a threshold to paper it.

## Links
Same detection-architecture class as `project_e7_verbatim_match_gap`, Clinical-Flag Detection Gap #65, and the
recall-fixture-independence + noise-floor rules in `ARCHITECTURE_BOUNDARIES.md`. Guard code:
`detect_medical_redflag` (safety_check.py, B1 interim). Sits under D1's subtle-red-flag branch
(`test_screen_serve_resume_graph.py` documents that branch).
