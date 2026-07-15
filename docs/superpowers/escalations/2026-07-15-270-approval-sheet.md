# GOV-270 — per-rule approval sheet for clinical lead (ratify / amend / deactivate)

**Companion to** `2026-07-15-270-unsigned-active-safety-rules.md`. **All 16 are `active` in prod without sign-off.**
**Headline recommendation: RATIFY all 16** — every one implements a BOT BEHAVIOUR-mandated safety detection; **deactivating any opens a live safety gap** (do-not-bulk-deactivate applies to the *deactivate* option, not the review). The clinician's actual task is confirming the trigger *patterns* per rule (pattern lists provided separately); the *disposition* is ratify. **3 caveats flagged below need attention during that review.**

---

## ★ FINAL RECOMMENDATION (approve / reject / edit this)

> **RATIFY and sign all 16 rules as active. Deactivate none.**
>
> **Why (BOT BEHAVIOUR + best practice):** all 16 are *detection* rules for behaviors the doc mandates a response to — suicidal ideation, self-harm/means, harm-to-others, command-hallucination (the doc's High-Risk presentation), third-party crisis, and clinical flags. The doc requires detecting these; the rules do it. The #270 problem is **not that they run — it's that they run *unsigned***. The fix is to **sign them**, not remove them. Deactivating any of these removes live safety detection and creates the exact gap the doc forbids. So the correct disposition is uniform: **ratify.**
>
> **Two of the sixteen carry a real clinical judgment (not a rubber-stamp) — weigh these, don't just approve:**
> - **SK-EN-006** deliberately **over-detects** self-harm variants (no negation check). Over-detection means some benign users get routed to the crisis path — a real (if fail-safe) trade-off. **Confirm the false-positive tolerance is clinically acceptable**, or amend the threshold.
> - **SK-AR-001/003, SK-AZ-001/002, CK-CH-002** are **unsigned Arabic/Arabizi safety in the language we cannot yet measure** (0 AR corpus). Ratify the patterns now (they are the *only* AR safety detection — deactivating leaves Arabic users with none), but **their end-to-end validation is owed and routes into the AR probe.**
>
> **One rider (not a blocker to signing):** **SK-EN-001** has a known negation-recall gap (misses ~5/6 SI-with-negation). **Ratify it now** (it catches the rest) **and open an amendment** to add negation handling — signing it records the known limitation rather than leaving it silent.
>
> **Everything else (SK-EN-003/004/005/HTO-001, CK-CH-001, CF-001..004) is a clean ratify** — sign as-is.
>
> **Clinician action:** approve this recommendation in one pass (ratify all 16 + the SK-EN-001 amendment + the AR-validation follow-up), or edit any single row. **Do not defer** — every day these run unsigned is a day live safety routing has no clinical authority behind it.

---

| Rule | Detects | BOT BEHAVIOUR requirement it implements | Recommendation | Note for the clinician |
|---|---|---|---|---|
| **SK-EN-001** | Core English explicit SI | Crisis protocol (Suicidal Ideation) | **RATIFY** | ⚠️ **Known negation-recall gap** (5/6 SI-with-negation missed). Ratify the rule (load-bearing) **and open an amend**: add negation handling. Do not deactivate. |
| **SK-EN-003** | Self-harm method / planning | Crisis (self-harm, means/planning) | **RATIFY** | Confirm method-reference patterns. |
| **SK-EN-005** | Metaphorical escape / non-return (Gulf desert imagery + universal) | Crisis (passive SI) | **RATIFY** | Confirm the Gulf-cultural passive-SI idioms. |
| **SK-EN-006** | Progressive/variant self-harm forms | Crisis (self-harm) | **RATIFY** | ⚠️ **Deliberately carries NO negation_check — over-detection by design.** Confirm the FP tolerance is clinically acceptable for self-harm variants. |
| **SK-EN-HTO-001** | Harm-to-others explicit intent (Node-1 backstop) | Harm-to-others protocol | **RATIFY** | Group A (explicit intent) only; confirm scope. |
| **SK-EN-004** | Third-party crisis (someone else) | Third-party handling (does NOT flag the speaker) | **RATIFY** | Correctly scoped: does not set is_safe=False for the speaker. Confirm. |
| **CK-CH-001** | Command hallucination (EN) → crisis_response | High-Risk protocol (psychosis / command hallucinations) | **RATIFY** | Top-tier: command hallucination is exactly the HR presentation. Confirm patterns. |
| **CK-CH-002** | Command hallucination (Arabic) | High-Risk (psychosis), Arabic | **RATIFY** | ⚠️ AR-unvalidated (see below). |
| **SK-AR-001** | Arabic MSA + Gulf explicit SI | Crisis (SI), Arabic | **RATIFY** | ⚠️ **Unsigned Arabic safety in the UNMEASURED language.** Ratify the patterns; flag for the AR probe to validate end-to-end (no AR corpus yet). |
| **SK-AR-003** | Gulf emotional-exhaustion idioms (passive SI) | Crisis (passive SI), Arabic | **RATIFY** | ⚠️ Same AR caveat. Confirm the passive-vs-explicit call (flags si_passive). |
| **SK-AZ-001** | Arabizi explicit SI | Crisis (SI), Arabizi/code-switch | **RATIFY** | ⚠️ Same AR/Arabizi caveat. |
| **SK-AZ-002** | Arabizi passive SI | Crisis (passive SI) | **RATIFY** | ⚠️ Same caveat. Routes to text_raw so lang-misdetection can't silence it — confirm. |
| **CF-001** | Substance-use disclosure → clinical flag | Clinical-flag handling | **RATIFY** | ⚠️ Keyword-only (#65 recall gap: naturalistic disclosures missed). Ratify; semantic tier is a future improvement, not a reason to deactivate. |
| **CF-002** | Trauma indicator → clinical flag | Clinical-flag handling | **RATIFY** | ⚠️ Same #65 recall note. |
| **CF-003** | Eating-concern → clinical flag | Clinical-flag handling (+ ED contraindication for TIPP etc.) | **RATIFY** | ⚠️ Same #65 note. ED flag also feeds skill contraindications. |
| **CF-004** | Medication mention → clinical flag | Clinical-flag handling (scope/diagnosis boundary) | **RATIFY** | ⚠️ Same #65 note. |

## The 3 caveats, consolidated (the review's real content)
1. **AR / Arabizi rules (SK-AR-001/003, SK-AZ-001/002, CK-CH-002)** — unsigned safety in the language we cannot yet measure. Ratify the patterns now (they're load-bearing), and route the *end-to-end validation* into the AR probe. This is the tightest tie between #270 and the AR corpus worklist.
2. **SK-EN-001 negation gap** — ratify + amend (add negation handling); the doc mandates SI detection and this under-detects negated SI.
3. **SK-EN-006 deliberate over-detection** and **CF-* keyword-only recall (#65)** — confirm the FP tolerance (SK-EN-006) and accept the recall limitation (CF-*) as ratify-with-known-limitation, not deactivate.

## What the clinician does NOT need to decide here
The trigger *patterns'* clinical correctness needs the pattern lists (provided separately). This sheet fixes the *disposition* (ratify) and the doc-alignment; the pattern review is the follow-on.
