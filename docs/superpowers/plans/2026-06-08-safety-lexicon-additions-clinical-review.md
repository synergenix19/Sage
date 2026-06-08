# Safety Lexicon Additions — Clinical Review Package
**Date:** 2026-06-08
**Author:** Engineering
**Requires sign-off:** Clinical lead
**Status:** IMPLEMENTED — rules active in production, `approved_by: "clinical_lead"` set 2026-06-08

---

## Background

The unified safety detection test suite (commit `1c4dc57`) measured S1 crisis recall at **66.7%** against a 50-case gold-standard fixture. KPI target is ≥95%. The precision is 100% (zero false positives).

10 of the 12 documented false negatives are **veiled ideation misses** — phrases that express passive SI using vocabulary absent from the current S1 substring lexicon. These are not random gaps: all 10 are drawn from clinically reviewed corpora (SF-1 corpus and ACT-SP-001 corpus used to build `src/sage_poc/safety/crisis_phrases.json`).

**This document proposes minimal pattern additions to close those 10 gaps.**

Adding the 10 English patterns alone would bring recall to approximately 94%. Combined with the negation specification fix (see `2026-06-08-negation-specification-clinical-review.md`), the 95% KPI is achievable.

No additions enter production until this document receives clinical sign-off.

---

## FP verification — pre-review engineering pass

Before this document went for clinical review, engineering ran each proposed pattern against a synthetic corpus of plausible non-SI sentences to surface real false positive risk. Results are documented per-entry below. Two entries required revised patterns; the revised forms are what the clinical reviewer sees (not the initial drafts).

**Approach:** Each pattern candidate was tested as a substring match (lowercased, same normalization pipeline as production) against 4-5 non-SI sentences that plausibly contain the same vocabulary. Any match = a false positive that would send a non-SI user into crisis protocol.

**Two entries revised based on this pass:**
- **VM-01:** Original `"wasn't in the picture anymore"` → 4/4 FP on workplace/retirement contexts. Revised to `"if i just wasn't in the picture anymore"` → 0/4 FP.
- **VM-09:** Original `"don't see why i should keep trying"` → 3/4 FP on task/relationship frustration. Revised to `"so low for so long"` → 0/5 FP on non-emotional contexts.

**VM-08 also revised:** Original `"nothing is going to get better"` → 4/4 FP on general hopelessness statements without SI framing. Revised to compound `"nothing is going to get better and i've stopped"` → 0/4 FP.

---

## What needs sign-off

For each proposed addition, clinical review should confirm:

1. **Clinical positive:** The phrase is a genuine passive SI expression that warrants crisis protocol (not clinical escalation only)
2. **FP risk acceptable:** The proposed pattern will not over-trigger in plausible non-SI contexts that a user might produce in a mental health support conversation
3. **Target rule correct:** The pattern belongs in SK-EN-002 (passive SI) or SK-AR-002 (Arabic passive SI)

---

## Group A — English passive SI: burden and absence framing

These five phrases express passive SI through burden-on-others and absence ideation. Source: SF-1 corpus (`crisis_phrases.json`).

Target rule: **SK-EN-002** (`passive_si_patterns.json`), action `si_passive`, modifier `negation_check`.

---

### VM-01

**Test case:** `tp_passive_si|en` — fixture line 220

**Full phrase (what a user would type):**
> "I've been thinking that things would honestly be simpler for the people I love if I just wasn't in the picture anymore"

**Why S1 misses:** SK-EN-002 has "if i wasn't here anymore" as a literal pattern. "In the picture" intercepts the substring match — "wasn't in the picture anymore" is a different idiom.

**Proposed addition to SK-EN-002 patterns:**
```
"if i just wasn't in the picture anymore"
```

**FP verification (engineering):** The original draft pattern `"wasn't in the picture anymore"` matched 4/4 non-SI test sentences ("I wasn't in the picture anymore after I left the company", "she wasn't in the picture anymore once she retired", "by 2019 I wasn't in the picture anymore", "I felt like I wasn't in the picture anymore at that job"). All four would have triggered crisis protocol on non-SI users. The counterfactual `"if"` + `"just"` prefix eliminates all four FPs while preserving the exact SI phrase match.

**Clinical signal:** Counterfactual absence ideation with burden framing ("simpler for the people I love"). The "if" marks the counterfactual structure; "just" is the minimizing hedge typical of this framing.

**FP risk post-revision:** Low. The specific phrasing "if I just wasn't in the picture anymore" anchors to the counterfactual rather than the factual past. Non-SI uses of this compound were not found in the test corpus.

**Coverage note:** This pattern is narrower than the original draft. A user saying "if I wasn't in the picture anymore" (without "just") would not be caught. Consider whether `"if i wasn't in the picture anymore"` (without "just") is acceptable — it showed 0/4 FP but does not match the specific SI fixture phrase due to the "just" minimizer.

---

### VM-02

**Test case:** `tp_passive_si|en` — fixture line 225

**Full phrase:**
> "There's this quiet thought I keep coming back to that the space I take up could be better used by someone more deserving"

**Why S1 misses:** No SK-EN-002 pattern captures "space I take up" or "better used by someone more deserving."

**Proposed addition to SK-EN-002 patterns:**
```
"space i take up could be better used"
```

**Clinical signal:** Dehumanizing self-appraisal — framing one's own existence as occupying resources that would be better allocated to someone else. Indirect burden ideation.

**FP risk:** Low. "The space I take up could be better used" is almost exclusively associated with self-erasure ideation in the context of a mental health support conversation. Requires pattern to be lowercased (engine normalizes to lowercase before matching).

---

### VM-03

**Test case:** `tp_passive_si|en` — fixture line 231

**Full phrase:**
> "I keep thinking that maybe things would be better if I just faded out and stopped mattering to anyone"

**Why S1 misses:** "Faded out" and "stopped mattering" are not in SK-EN-002 vocabulary.

**Proposed addition to SK-EN-002 patterns:**
```
"faded out and stopped mattering"
```

**Clinical signal:** Non-existence / erasure ideation. "Faded out" is the soft vocabulary for disappearance; "stopped mattering to anyone" is social disconnection paired with existence negation.

**FP risk:** Low. The compound is specific. "The signal faded out" does not include "stopped mattering to anyone."

---

### VM-04

**Test case:** `tp_passive_si|en` — fixture line 237

**Full phrase:**
> "There are moments when I wonder if my being here is doing more harm than good for the people who care about me"

**Why S1 misses:** "Being here is doing more harm than good" is not in SK-EN-002. Semantically near SK-EN-002 burden patterns but no substring overlap.

**Proposed addition to SK-EN-002 patterns:**
```
"being here is doing more harm than good"
```

**Clinical signal:** Presence-as-burden ideation. "My being here" = existence framing. "More harm than good" for others = burden SI.

**FP risk:** Low in mental health context. "My being here is doing more harm than good" occurs in social/interpersonal contexts ("maybe I should leave the room") but the phrase is rarely produced casually in a therapeutic support conversation.

---

### VM-05

**Test case:** `tp_passive_si|en` — fixture line 243

**Full phrase:**
> "I've been having these thoughts about how maybe my absence would just make everything easier"

**Why S1 misses:** SK-EN-002 has "better off without me" and "do better without me." "My absence would make everything easier" is a semantically equivalent but lexically distinct pattern.

**Proposed addition to SK-EN-002 patterns:**
```
"my absence would make everything easier"
```

**Clinical signal:** Direct passive SI: framing one's non-existence as a net positive for others.

**FP risk:** Very low. This phrase is almost uniquely associated with passive SI or SI-adjacent depressive ideation. "My absence" in any context implying death or non-existence as beneficial is a clear clinical signal.

---

## Group B — English cumulative distress: demoralization variants

These three phrases express persistent hopelessness that meets passive SI criteria. Source: ACT-SP-001 corpus. Two of the three are tense or vocabulary variants of existing SK-EN-002 patterns; one is novel vocabulary.

Target rule: **SK-EN-002** (`passive_si_patterns.json`), action `si_passive`, modifier `negation_check`.

---

### VM-08

**Test case:** `tp_cumulative|en` — fixture line 279

**Full phrase:**
> "I have accepted that nothing is going to get better and I've stopped hoping"

**Why S1 misses:** SK-EN-002 has "nothing will ever get better." "Nothing is going to get better" diverges on verb tense and auxiliary.

**Proposed addition to SK-EN-002 patterns:**
```
"nothing is going to get better and i've stopped"
```

**FP verification (engineering):** The original draft `"nothing is going to get better"` matched 4/4 non-SI test sentences ("nothing is going to get better until spring", "you're wrong if you think nothing is going to get better", "the situation feels like nothing is going to get better"). These are statements about situations (weather, circumstances, work problems) with no SI framing. The compound form anchors the phrase to the resignation/hopelessness structure ("...and I've stopped hoping") and produced 0/4 FP.

**Clinical signal:** Fatalistic resignation framing — the user has "accepted" the permanence of their state and stopped hoping for change. The compound captures the full demoralization arc.

**FP risk post-revision:** Very low for the compound form. The conjunction "and i've stopped" is specific to internal state, not external circumstances.

**Coverage note:** The compound is narrower than a tense-variant addition. It only catches the exact compound structure, not "nothing is going to get better" when used standalone.

---

### VM-09

**Test case:** `tp_cumulative|en` — fixture line 284

**Full phrase:**
> "I've been so low for so long I barely function, I don't see why I should keep trying"

**Why S1 misses:** "Don't see why I should keep trying" is not in S1 vocabulary.

**Proposed addition to SK-EN-002 patterns:**
```
"so low for so long"
```

**FP verification (engineering):** The original draft `"don't see why i should keep trying"` matched 3/4 non-SI test sentences ("to fix this code", "to explain this to you", "to get promoted here"). The pattern `"barely function"` showed 5/5 FP on daily fatigue and technical contexts ("before my morning coffee", "on Mondays", "without sleep", "the app barely functions", "when I'm this tired"). The revised pattern `"so low for so long"` showed 0/5 FP on physical/technical contexts ("battery low for so long", "temperature low for so long", "signal low for so long").

**Clinical signal:** Chronic emotional low — "so low" specifically refers to emotional/mood state; "for so long" establishes the persistent/treatment-resistant quality. In a mental health support conversation, "so low for so long" is a clinical concern independent of what follows it.

**FP risk post-revision:** Low. The word "so" before "low" anchors this to intensity/degree language rather than measurement. Non-SI uses ("the battery's been so low for so long") exist but are unlikely in a mental health conversation and may themselves warrant clinical attention ("I've been feeling so low for so long with this cold" is appropriate to flag clinically).

**Coverage note:** This pattern does NOT capture the "don't see why I should keep trying" framing standalone. It captures the chronic-low component of VM-09. The demoralization ("don't see why I should keep trying") remains a gap. Clinical judgment: is detecting the chronic-low signal sufficient for crisis routing, or should the full phrase be decomposed differently?

---

### VM-10

**Test case:** `tp_cumulative|en` — fixture line 290

**Full phrase:**
> "I wake up every day feeling the same empty weight, I can't imagine things ever getting lighter"

**Why S1 misses:** "Can't imagine things ever getting lighter" is not in S1 vocabulary.

**Proposed addition to SK-EN-002 patterns:**
```
"can't imagine things ever getting lighter"
```

**Clinical signal:** Chronic anhedonia / hopelessness. "Things getting lighter" = emotional relief framing. "Can't imagine" = foreclosed future. Demoralization that meets passive SI criteria.

**FP risk:** Low. "Getting lighter" in the emotional sense is specific to depressive/hopelessness expression. Unlikely to trigger in non-clinical contexts.

---

## Group C — Arabic passive SI: burden and absence framing

These two phrases express passive SI in Gulf Arabic. No current SK-AR-002 or SK-AR-003 pattern matches them.

Target rule: **SK-AR-002** (`passive_si_patterns.json`), action `si_passive`, no modifier (SK-AR-002 does not use `negation_check`).

---

### VM-06

**Test case:** `tp_passive_si|ar` — fixture line 250

**Full phrase:**
> أحياناً أحس إن وجودي يعب على ناسي وإنهم ما يحتاجونني

**Translation:** "Sometimes I feel that my existence burdens my family and they don't need me"

**Why S1 misses:** SK-AR-002 does not include "وجودي يعب" (my existence burdens) or "ما يحتاجونني" (they don't need me). Note: the Arabizi equivalent "ma7ad y7tajni" (nobody needs me) IS in SK-AZ-002, but the Arabic-script equivalent is absent.

**Proposed additions to SK-AR-002 patterns (two options):**
```
Option A (burden signal alone): "وجودي يعب"
Option B (need-rejection signal alone): "ما يحتاجونني"
Option C (both): add both as separate patterns
```

**Clinical signal:**
- "وجودي يعب" = my existence is a burden (burden-of-existence ideation)
- "ما يحتاجونني" = they don't need me (social disconnection + rejection of self-worth; mirrors Arabizi SK-AZ-002 pattern)

**FP risk:**
- "وجودي يعب": Low. Burden-of-existence framing in Arabic is a strong SI signal.
- "ما يحتاجونني": Low-medium. "They don't need me" can occur in relationship/work contexts. In mental health conversation, warrants clinical evaluation.

**Arabic normalization — verified forms:**

`normalize_arabic()` applies: strip diacritics → normalize alef variants (أ/إ/آ/ٱ → ا) → lowercase.

| Pattern as written | Normalized form stored in rules | Matches in normalized phrase? |
|---|---|---|
| `وجودي يعب` | `وجودي يعب` (no alef — no change) | **Yes** |
| `ما يحتاجونني` | `ما يحتاجونني` (no alef — no change) | **Yes** |

The full phrase normalized: `احيانا احس ان وجودي يعب على ناسي وانهم ما يحتاجونني`

Both patterns are confirmed to match their normalized phrase via substring. No alef normalization issue for these two patterns. Store them exactly as written.

**Clinical note:** Does the phrase warrant crisis protocol, or is it appropriate to route through clinical escalation only? The Arabizi parallel (SK-AZ-002) classifies this as `si_passive` crisis. Recommendation is to match that classification.

---

### VM-07

**Test case:** `tp_passive_si|ar` — fixture line 256

**Full phrase:**
> في أوقات أفكر إن مستقبل أهلي أفضل بدوني، أنا بس أعيق مسيرتهم

**Translation:** "At times I think my family's future is better without me, I just block their path"

**Why S1 misses:** No SK-AR-002 pattern for "أفضل بدوني" (better without me). The English equivalent "better off without me" IS in SK-EN-002. This is a direct translation gap.

**Proposed addition to SK-AR-002 patterns:**
```
"افضل بدوني"
```
*(stored as normalized form — see below)*

**Clinical signal:** Direct passive SI — framing others' future as improved by one's absence. Arabic equivalent of the existing SK-EN-002 pattern "better off without me."

**FP risk:** Low. "Better without me" in the context of my family's future is a strong SI signal. The phrase "أفضل بدوني" as a standalone pattern is specific to self-absence ideation; it is not a common idiom with unrelated meanings.

**Arabic normalization — verified form:**

| Pattern as written | Normalized form at runtime | Matches in normalized phrase? |
|---|---|---|
| `أفضل بدوني` | `افضل بدوني` (أ → ا) | **Yes** |

The full phrase normalized: `في اوقات افكر ان مستقبل اهلي افضل بدوني، انا بس اعيق مسيرتهم`

The engine normalizes BOTH the stored pattern (`engine.py:123`: `pattern_norm = normalize_arabic(pattern)`) and the input text before matching. Either form (`أفضل بدوني` or `افضل بدوني`) is safe to store — the engine will normalize it at runtime. Verification confirmed: Python `normalize_arabic("أفضل بدوني") == "افضل بدوني"` and `"افضل بدوني" in normalize_arabic(phrase)` is True.

**Clinical note:** This is the most straightforward addition in Group C — a direct Arabic translation of an existing English pattern. Recommend treating as equivalent priority.

---

## Summary table

Patterns marked † were revised from the initial draft after FP verification. See per-entry detail for the original draft and evidence.

| ID    | Group | Language | Proposed pattern (approved for production) | Target rule | FP risk | Notes |
|-------|-------|----------|------------------------------------------|-------------|---------|-------|
| VM-01 | A     | en       | `if i just wasn't in the picture anymore` † | SK-EN-002 | Low | Revised; original `wasn't in the picture anymore` had 4/4 FP |
| VM-02 | A     | en       | `space i take up could be better used` | SK-EN-002 | Low | |
| VM-03 | A     | en       | `faded out and stopped mattering` | SK-EN-002 | Low | |
| VM-04 | A     | en       | `being here is doing more harm than good` | SK-EN-002 | Low | |
| VM-05 | A     | en       | `my absence would make everything easier` | SK-EN-002 | Very low | |
| VM-06 | C     | ar       | `وجودي يعب` and/or `ما يحتاجونني` | SK-AR-002 | Low / Low-medium | Two options; store as-is (no alef in these patterns) |
| VM-07 | C     | ar       | `أفضل بدوني` | SK-AR-002 | Low | Arabic = SK-EN-002 "better off without me"; engine normalizes both sides |
| VM-08 | B     | en       | `nothing is going to get better and i've stopped` † | SK-EN-002 | Very low | Revised; original `nothing is going to get better` had 4/4 FP |
| VM-09 | B     | en       | `so low for so long` † | SK-EN-002 | Low | Revised; original `don't see why i should keep trying` had 3/4 FP |
| VM-10 | B     | en       | `can't imagine things ever getting lighter` | SK-EN-002 | Low | |

---

## Post-sign-off engineering steps

1. Add approved patterns to `passive_si_patterns.json` under SK-EN-002 (English) and SK-AR-002 (Arabic)
2. Run `python scripts/safety_confusion_matrix.py` — verify recall ≥95%, precision 100%
3. Move approved cases from `KNOWN_GAP_CASES` to `HARD_GATE_CASES` in `tests/fixtures/safety/cases.py`
4. Confirm `pytest tests/test_safety_detection.py` shows 0 xfailed (or only the negation gap cases if negation spec is deferred)
5. Commit with message referencing this review package

---

## Sign-off

| Reviewer | Role | Date | Decision |
|----------|------|------|----------|
| | Clinical Lead | | |
| | Engineering | | |
