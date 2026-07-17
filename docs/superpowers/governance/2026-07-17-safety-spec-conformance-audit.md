# Safety spec-conformance audit — EN baseline vs the BOT BEHAVIOUR spec (#337 ∪ CR-0)

**One artifact, not scattered findings.** Unifies #337 (EN medical/safety phrase files vs spec) and
CR-0 (crisis-lexicon canonical table). Source of record: `bot-behaviour-spec-source-2026-07-08.md`.

**Prediction on record:** this finds more. Every targeted audit this fortnight (parity, raw-vs-translated,
governance-cross-ref) paid out multiples; the fainting gap was found incidentally, which is the tell that
the systematic pass has yield.

## Method (per row)
`detector / phrase-file` → **spec section** (descriptor classes) → **coverage diff** (spec class present in
data? EN and AR?) → **gap** → **ticket / disposition**. The AR-parity gate (#329) already guarantees *AR
matches EN*; this audit is the missing leg — *does EN match the document*. Parity to a spec-incomplete
baseline is fake completeness.

## Unified conformance table (first pass — CONFIRMED rows + per-file spec section)

| detector / file | spec section | status | gap / disposition |
|---|---|---|---|
| `medical_redflag_phrases` | §1 universal red-flag override (L16–21, L58); quality-check (L101, L105); guard (L148) | **PARTIAL** | ✅ crushing/stabbing/searing/spreading + one-sided numbness (EN+AR). ✅ **fainting** added tonight (L148). ❌ **real breathlessness** is NOT keyword-able (L54 panic overlap) → contextual screen, **#338** (unimplemented L58/L101 quality-check). |
| crisis (`crisis_keywords` + `passive_si_patterns`) | §Crisis canonical trigger table (the recall test set) | **RECALL GAP (CR-0)** | ❌ passive-ideation / burden / can't-continue / hopelessness rows — CRADLE recall ~37% / self-harm ~18% vs ≥95% fail-closed = **GL-0 NO-GO**. Fix = S2/MARBERT (NOT BGE-M3: distress/SI bleed is the safety property), validated bilingual eval. Corpus/recall work, not routing. |
| `ocd_compulsion_patterns` | OCD-type markers (L235/L277) | **PARTIAL** | ✅ checking/washing (EN + interim AR, deployed). ❌ **reassurance-seeking** + **intrusive-thought** compulsion markers (L235) not covered → Tier-2 (#330). |
| `harm_intrusive_patterns` | ego-dystonic harm ideation (E7 / veto) | **AR gap tracked (#330)** | EN present; AR absent (translation currently catches; #330). Spec-completeness of the EN markers: **TO-DIFF**. |
| `clinical_flag_patterns` | §clinical-flag categories (substance/trauma/eating/medication) | **TO-DIFF** | 121 entries, EN+AR present (parity ✅). Diff each category's markers vs spec: **TO-DO**. |
| `passive_si_patterns` | §passive SI / burden / hopelessness | **overlaps CR-0** | 157 entries; the recall gap above is the headline. Per-marker spec-diff: **TO-DO**. |
| `ipv_preempt_expansion` | SG-1 six recognition types | **TO-DIFF** | flag-OFF on prod (#330); SG-1 types mostly transcription, idiom cells (walking-on-eggshells) need clinician. |
| `false_positive_exclusions` | (exclusions — inverse) | **TO-DIFF** | verify exclusions don't suppress a spec-mandated trigger. |
| `sensitive_topic_suppression_lexicon` | §sensitive topics | bilingual ✅ | per-category spec-diff: **TO-DO**. |

## Confirmed this fortnight (feed the two-tier packet pipeline)
- **medical fainting** (L148) — added, deployed EN+AR.
- **real-breathlessness** — correctly NOT a keyword (contextual, L54/L216) → **#338** screening-question build.
- **AR parity** across all safety files — enforced by the armed gate (#329); EXEMPT-with-ticket for the 3 EN-only detectors (#330).

## Execution note (the focused desk work that remains)
The `TO-DIFF` rows are the genuine remaining audit — per-file, spec-section-by-spec-section, semantic
(mapping descriptor classes to entries, not string-matching). ~an afternoon. Findings route to the
two-tier packet (interim doc-cited → Tier-2 clinician). Mechanize later as a governance-touch check
listing the spec section + governance decisions per data file (the primary-source-for-data rule).

Refs #337 CR-0 #338 #330 #329 #313.
