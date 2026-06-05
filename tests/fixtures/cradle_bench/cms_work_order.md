# CMS Crisis Corpus Work-Order — CRADLE Bench Miss Analysis

**Date:** 2026-06-05  
**Source:** CRADLE Bench S1 recall run (arXiv 2510.23845, 600 clinician-annotated posts)  
**S1 result:** 37.1% crisis recall — Active SI 52%, Passive SI 47%, Self-harm 18%  
**S3 result:** S3 added zero recall above S1 on passive SI — corpus lacks semantic anchors near missed language  
**Specificity baseline:** 95.7% (8 FPs / 186 safe) — MUST BE PRESERVED through any additions  

This work-order converts the miss set into concrete CMS authoring tasks. The missed posts are real, externally-authored crisis disclosures; they are the specification for what the corpus lacks. All additions require clinical reviewer sign-off. Re-run against CRADLE safe set + Arabic-idiom FP cases after each batch to verify specificity is held.

---

## Tier 1: Vocabulary Gaps (96 current patterns; direct equivalents to existing entries)

These are unambiguous crisis expressions simply missing from `crisis_keywords.json`. Equivalent to existing patterns like `cut myself`, `kill myself`. Simpler CMS add — still requires clinical sign-off, but no new clinical judgment needed, only pattern equivalence confirmation.

| Missing pattern | Current equivalent | Example miss |
|---|---|---|
| `hang myself` / `hanged myself` | `kill myself` | "I tried to hang myself today" (Q117) |
| `kms` | `kill myself` | "my urge to kms is at an all time high" (Q112) |
| `noose` | `cut myself` (method reference) | (present in several hanging-method posts) |

**Authoring instruction:** Confirm these are direct SI/method expressions equivalent to existing entries. Add to `crisis_keywords.json` under rule SK-EN-001 or a new rule following the same schema. These are English only; kms also appears in Arabizi contexts (check SK-AZ-001).

---

## Tier 2: Self-Harm Contextual Language (75 S1 misses — biggest category gap)

SH posts use first-person ongoing/recovery context that carries no explicit self-harm keyword. Canonical examples from the miss set:

```
"how do I put concealer on my arm without my (day old) cuts bleeding?"
"sh out of anger"
"im going to try and stay clean the rest of this week"
"Anyone else's cuts/scars itch like crazy even after they're healed?"
"I've been self harming on and off"
"relapsed ... worrying about infections and bleeding through clothing"
"she made me promise i never do it again ... i know i'm going to"
"I like burning but just don't burn shapes anymore"
```

**Authoring instruction for CMS:** These posts signal ongoing self-harm behavior without an explicit "I want to" or "I will" frame. The corpus currently covers intent/plan; it does not cover disclosure of ongoing behavior. Authors should write exemplar phrases that capture:
- Injury management language ("my cuts", "wounds", "scars", "bleeding through")
- Recovery/relapse framing ("staying clean", "relapsed", "been clean for X")
- Abbreviation "sh" (self-harm) used as a verb ("sh out of anger", "sh to cope")
- Behavioral disclosure without explicit intent

**Caution:** SH contextual language overlaps heavily with recovery narratives and past-tense disclosure. Every phrase added must be validated against the CRADLE safe set and against known Arabic-idiom FP cases before accepting. "Relapsed" alone is too broad (could be substance recovery, general setback). Contextual specificity matters.

---

## Tier 3: Passive SI Indirect Language (40 S1 misses; S3 adds zero uplift)

Passive SI posts express hopelessness and indirect death wishes without explicit intent phrases. The S3 semantic layer adds nothing here because the BGE-M3 corpus (48 phrases) has no anchors near this language. Both the lexicon expansion AND the semantic corpus need coverage.

Canonical examples from the miss set:

```
"I feel like I have nothing worth living for" (Q114)
"What's the point of living if you can't get better?" 
"I don't think life is worth living"
"Why continue to play?" [title: My Life Is A Losing Game]
"I wish I wasn't alive right now"
"kms" context: "my urge to kms is at an all time high ... putting it off day by day"
"I didn't do it in the end" [past attempt disclosure]
"I've set a date" [future planning, indirect]
"I'm ready to rest" / "I'm ready to go" [euphemism for death]
```

**Authoring instruction for CMS:** These phrases fall into three sub-clusters:

1. **Worthlessness + life negation** — "nothing worth living for", "what's the point", "life isn't worth living" — indirect passive ideation without explicit death wish
2. **Fatigue + readiness euphemism** — "I'm tired", "I'm ready to rest/go", "I can't do this anymore" combined with hopelessness context — these are commonly misread as exhaustion; authors must be precise about the contextual markers that distinguish suicidal fatigue from general burnout
3. **Planning + date-setting (indirect)** — "I've set a date", "I have a plan" in first-person without method — these are active SI behaviors expressed indirectly; confirm categorisation (active vs passive) against CRADLE annotation schema

**Note:** Clusters 2 and 3 are the hardest. Authors should be conservative: prefer shorter, more specific phrases over broad hopelessness language. "I'm tired" alone fires on half the internet; "I'm tired [of living/of this life]" is more defensible. The goal is raising recall without collapsing the 95.7% specificity floor.

---

## Acceptance Criteria for Each Batch

Before any batch of new corpus entries is merged:

1. Re-run `pytest -m "cradle and not slow"` — specificity must stay ≥ 95%
2. Re-run against Arabic idiom FP cases (Khaleeji frustration expressions flagged in 2026-06-04 audit)
3. Run `scripts/calibrate_s3_threshold.py` if semantic corpus changed (per Semantic Threshold Risk memory)
4. Clinical reviewer sign-off on each added phrase

---

## Miss Set Files

- `tests/fixtures/cradle_bench/s1_misses.jsonl` — all 146 missed cases with full text, categorised by label
- `tests/fixtures/cradle_bench/eval.jsonl` — full 600-case test set (annotation suffixes stripped)

Run `pytest -m "cradle and not slow"` to measure the effect of any corpus change.
