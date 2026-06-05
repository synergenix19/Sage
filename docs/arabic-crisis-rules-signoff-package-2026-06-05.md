# Arabic Crisis Rules — Clinician Sign-Off Package

**Date:** 2026-06-05  
**Author:** sage_clinics  
**Status:** PENDING CLINICAL SIGN-OFF — all rules are `active: false` or reverted; none are live  
**Signer:** [Clinical Lead — same as SK-AR-002/003]  
**Bundled because:** Three rules, same sign-off criteria, same Arabic eval gap — clearing them separately prolongs the coverage gap.

---

## Sign-Off Gate Criteria (same as SK-AR-002/003)

Before any rule in this package is activated:
1. `approved_by` field must be filled by the clinical reviewer
2. An Arabic eval instrument must exist (or the reviewer explicitly accepts the measurement gap)
3. Rule file `active` flipped to `true` in a separate commit from sign-off

The revert commit (`c9f9526`) for SK-AR-004/005 explicitly states: "specificity alone is not sufficient cover for unsigned rules on a live crisis path." This package addresses item 1 and documents item 2's status honestly.

---

## Rule 1: SK-AR-004 — Arabic SI Method References

**File:** `src/sage_poc/rules/data/safety/crisis_keywords.json`  
**Status:** Authored in commit `0776268`, reverted in `c9f9526`. Currently NOT in the file. Must be re-added after sign-off.  
**Mirrors:** SK-EN-003  
**Action:** `crisis_flag: si_method`  
**Language:** `ar`  
**Modifiers:** `negation_check`

**Patterns (12):**
```
كيف اخذ حبوب عشان اموت
كم حبة تقتلني
اقفز من الجسر
اقفز من الطابق
اشق معصمي
اقطع معصمي
اشنق نفسي
طرق انهاء حياتي
كيف اوذي نفسي بشكل خطير
طريقة اقتل نفسي
اقتل نفسي بالحبوب
كم حبة كافية عشان اموت
```

**Clinical review questions:**
- Are all 12 patterns unambiguous SI method references in Gulf Arabic context?
- Is `negation_check` appropriate for all 12, or should any bypass it (e.g., repetition of a plan stated as a question)?
- Are there Gulf dialect variants missing (e.g., `أشق` vs `اشق` — normalization confirmed in engine)?

---

## Rule 2: SK-AR-005 — Arabic Third-Party Crisis

**File:** `src/sage_poc/rules/data/safety/crisis_keywords.json`  
**Status:** Authored in commit `0776268`, reverted in `c9f9526`. Currently NOT in the file. Must be re-added after sign-off.  
**Mirrors:** SK-EN-004  
**Action:** `third_party_crisis: third_party_si` (sets `is_safe=True` for speaker)  
**Language:** `ar`  
**Modifiers:** none (third-party context, no negation_check)

**Patterns (12):**
```
صديقتي قالت تبغى تموت
صديقتي تبغى تنتحر
صديقي قال يبي ينهي حياته
صديقي يريد ان يموت
اخوي يريد ان يموت
اختي تريد ان تموت
واحد اعرفه يريد ينهي حياته
صديقتي قالت تريد تجرح نفسها
اخوي يتكلم عن الانتحار
اختي تتكلم عن الانتحار
رفيقتي ذكرت انها تريد الموت
صاحبي قال ما يبي يكمل
```

**Clinical review questions:**
- Are these third-party patterns distinct enough from self-referential SI? (The `third_party_crisis` action marks `is_safe=True` for the speaker — the system does not enter crisis response for the user, but surfaces concern for the named person.)
- Is the cultural phrasing appropriate for the UAE/Gulf pilot population?
- Is there a risk that users reporting their own crisis use third-person framing (dissociation, narrative distance)?

---

## Rule 3: SK-AR-006 — Arabic Escape/Non-Return Ideation (DRAFT)

**File:** `src/sage_poc/rules/data/safety/passive_si_patterns.json`  
**Status:** Authored 2026-06-05 (commit `286db2b`), `active: false`. Currently in the file but will not fire until sign-off.  
**Mirrors:** SK-EN-005  
**Action:** `crisis_flag: si_passive`  
**Language:** `ar`  
**Modifiers:** none

**Patterns (11):**
```
ودي امشي ولا ارجع
ابي امشي ولا ارجع
ابغى امشي ولا ارجع
ودي اروح ولا ارجع
ابي اروح ولا ارجع
ابغى اروح ولا ارجع
امشي من الدنيا ولا ارجع
اروح ولا ارجع من الدنيا
ابي امشي في الصحراء ولا ارجع
راح ولا راجع للحياة
مو راجع للحياة هذي
```

**Clinical review questions:**
- Do these patterns capture the Gulf cultural expression of passive SI (departure, non-return) accurately?
- Is `مو راجع للحياة هذي` ("not returning to this life") specific enough to distinguish from travel/relocation metaphor?
- Is the pattern set specific enough to avoid matching non-clinical expressions like `مو راجع اليوم` (not coming back today)?
- Desert imagery note: `ابي امشي في الصحراء ولا ارجع` specifically targets the Gulf cultural motif of walking into the desert. Clinician confirmation that this is a recognised passive-SI presentation in the UAE/Gulf context is required.

---

## What "Live Coverage" Means for Each

| Rule | Live today | After sign-off |
|---|---|---|
| SK-AR-004 | **NONE** (reverted) | si_method crisis flag on Arabic method phrasing |
| SK-AR-005 | **NONE** (reverted) | third_party_crisis path activated for Arabic |
| SK-AR-006 | **NONE** (active=false) | si_passive flag on Gulf escape/non-return phrasing |

**Gulf Arabic escape/non-return has zero coverage at any tier today:**
- S1: no rule (SK-AR-006 not yet active)
- S3: S3 is advisory, adds 0 recall (see CRADLE sweep 2026-06-05)

This is the concrete gap. The sign-off unblocks all three in one action.

---

## Arabic Eval Gap

There is no Arabic-language crisis recall benchmark. CRADLE is English-only. Validation for SK-AR-004/005/006 relies on:
- Clinical pattern review (what this package provides)
- Specificity: verified no FPs against CRADLE safe set (186 English cases — incomplete proxy for Arabic)
- Known gap: no Arabic recall measurement exists

The revert commit required an Arabic eval signal before re-activation. If that criterion is maintained, these rules wait until an Arabic eval instrument is built. If the clinical reviewer accepts the measurement gap as documented above, the sign-off proceeds with that caveat noted.

---

## Test Evidence

SK-AR-006 has no activation tests (active=false by design). When sign-off completes and `active` is flipped, add:
- `test_rules_safety.py`: At least 3 positive examples (escape+non-return) → `si_passive`
- `test_rules_safety.py`: At least 3 negative examples (departure without non-return) → not flagged
- Re-run `scripts/calibrate_s3_threshold.py` to confirm threshold gap unaffected
- Re-run `pytest -m "cradle and not slow"` to confirm specificity ≥ 95% holds

SK-AR-004 and SK-AR-005 had tests that were deleted in the revert commit (`c9f9526`). Those tests must be re-added alongside the re-introduction.

---

## Sign-Off Field

When approved, fill `approved_by` in each rule and set `active: true`:

```json
"approved_by": "[Clinician Name]",
"effective_date": "[YYYY-MM-DD]",
"active": true,
```

Commit with: `feat(safety): activate SK-AR-004/005/006 — [Clinician Name] sign-off [date]`
