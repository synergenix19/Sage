# Skill Entry-Screen Criteria — Clinician Sign-Off Package

**Date:** 2026-06-05 / 2026-06-06  
**Author:** Engineering (criteria rewrite — see context below)  
**Status:** PENDING CLINICAL SIGN-OFF  
**Signer:** [Clinical Lead — same as SK-AR-002/003 and Arabic rules package]  
**Bundled because:** Four skills, same authoring failure class, one clinical action clears all.

---

## Context: Why engineering rewrote clinician-authored criteria

Entry-screen `completion_criteria` fields are clinician-authored content that drive a Node 5 LLM evaluator. All four original criteria contained only exclusion lists ("hold if X, Y, Z") with no affirmative statement of what the target population looks like.

In FP-arm adversarial testing (June 2026), this structure caused **4/4 false holds** on the exact target populations the skills are designed for:

- TIPP held on panic symptoms (racing heart from anxiety) — TIPP's primary target
- PMR held on stress-induced muscle tension — PMR's primary target
- Body scan held on emotional depletion / being "tired and stressed" — body scan's primary target
- Safe place held on visualization uncertainty — skill is designed to help find a safe place

The fix was adding an IMPORTANT affirmative clause to each completion_criteria: explicitly stating that the target-population symptom is NOT the contraindicated condition. This is a **clinically substantive claim** — it asserts what is safe to proceed on, not merely what to hold on. Engineering authority + a green integration test is insufficient basis for these statements. Clinical review is required.

**What was NOT changed:** contraindications fields, hold conditions, escalation logic. Only the completion_criteria field in each entry_screen step was modified.

---

## Skill 1: DBT TIPP — `dbt_tipp.json` entry_screen

**Original criteria (abbreviated):**  
"User has not disclosed cardiac conditions, pacemaker use, arrhythmia, physical disability, injury, disordered eating. Safe to advance."

**Added IMPORTANT clause:**  
"IMPORTANT: Anxiety and distress symptoms — racing heart from panic, rapid breathing, chest tightness from anxiety, feeling overwhelmed, shaking — are NOT cardiac conditions and should advance. TIPP is specifically designed for acute emotional distress including physical anxiety symptoms. Only hold for diagnosed cardiac conditions (pacemaker, arrhythmia, heart disease) or physical injury."

**Clinical review questions:**
- Is the statement "racing heart from panic is NOT a cardiac condition" correctly scoped? The edge case is a panic presentation that is actually a cardiac event (MI, arrhythmia presenting as panic). The carve-out says "only hold for diagnosed cardiac conditions" — does "diagnosed" do enough work to protect this edge?
- Is "physical injury" a sufficient hold condition without specifying severity? Could a user with a minor strain who should still ADVANCE be over-held?
- The dive-reflex mechanism (cold water → rapid bradycardia) is a clinical fact. Does the criteria wording adequately convey when cold-water exposure is contraindicated vs. when the anxiety symptom cluster is the target?

---

## Skill 2: Progressive Muscle Relaxation — `progressive_muscle_relaxation.json` entry_screen

**Original criteria (abbreviated):**  
"User has not disclosed current injury, significant chronic pain, arthritis, deep vein conditions, or any condition where systematic muscle tensing would be harmful or painful. Safe to advance."

**Added IMPORTANT clause:**  
"IMPORTANT: Muscle tension, tightness, or soreness from stress or anxiety is NOT a contraindication — it is the primary target condition for PMR. Only hold when tensing muscles risks physical harm (acute injury, recent surgery, joint disease, DVT), not when the user reports being tense or sore from stress."

**Clinical review questions:**
- "Significant chronic pain" is in the hold condition. Chronic pain patients often carry stress-related muscle tension that IS a valid PMR target. Does "when tensing muscles risks physical harm" adequately protect the population with chronic pain that would benefit vs. chronic pain that tensing could exacerbate?
- Is "recent surgery" a time-bounded concept that needs specificity (e.g., within X weeks)? Or is clinical judgment sufficient here?
- Is DVT called out in the IMPORTANT clause as required, or is the generic "physical harm" language sufficient?

---

## Skill 3: Mindfulness Body Scan — `mindfulness_body_scan.json` entry_screen

**Original criteria (abbreviated):**  
"User has not disclosed current dissociation, derealization, history of dissociation triggered by body awareness exercises, or significant dizziness. Safe to advance."

**Added IMPORTANT clause:**  
"IMPORTANT: Feeling tired, stressed, anxious, or emotionally depleted does NOT indicate dissociation risk — these are the primary target presentations for body scan. Only hold when the user specifically describes depersonalization (feeling unreal or detached from their body) or derealization (the world feeling unreal), or when body awareness exercises have previously triggered these states."

**Clinical review questions:**
- "Feeling tired, stressed, anxious, or emotionally depleted" as ADVANCE conditions — is this exhaustive? Is there a class of emotional depletion (e.g., post-acute trauma state, dissociation from chronic stress) that should hold even without explicit dissociation language?
- The criteria now distinguish "general emotional fatigue" (ADVANCE) from "depersonalization/derealization" (HOLD). Is this distinction clear enough for a non-clinical LLM evaluator, or does the clinical edge (trauma-adjacent emotional depletion that precedes dissociation) require more nuanced language?
- Significant dizziness is in the original hold conditions but not mentioned in the IMPORTANT clause. Is dizziness from anxiety (vestibular anxiety) a target vs. a hold?

---

## Skill 4: Safe Place Visualization — `safe_place_visualization.json` entry_screen

**Original criteria (abbreviated):**  
"User has not disclosed an inability to imagine any safe place, a history of visualization triggering dissociation or threatening imagery, or active dissociation. The user's response indicates visualization work is accessible to them. Safe to advance."

**Added IMPORTANT clause:**  
"IMPORTANT: Uncertainty about what a safe place would look like, or never having tried visualization before, does NOT indicate inability — part of the skill's purpose is to help the user find or construct one. Only hold when the user explicitly states no place has ever felt safe to them, or that visualization reliably brings up threatening imagery or dissociation. Openness to trying, first-time use, or not yet having an image in mind are all ADVANCE conditions."

**Clinical review questions:**
- "No place has ever felt safe" is the primary hold condition for safe place. In a trauma population, some users may express this as a chronic background state ("I never really feel safe anywhere") that is distinct from the acute hold condition ("I cannot imagine a safe place, visualization makes it worse"). Is the current language adequate to distinguish these, or does it need to specify that trauma-related safety deficits are exactly the population for whom this skill should be carefully adapted rather than blocked?
- The IMPORTANT clause says "openness to trying" is ADVANCE. If a severely traumatized user says "I'll try anything, I'm desperate" and proceeds into safe place and encounters distress, the entry screen would have correctly advanced. Is the pass-through criterion aligned with clinical practice for this population?

---

## What the integration tests verify (and do not verify)

**Verify:** The LLM evaluator, with the updated criteria, distinguishes the target-population presentations from the contraindicated presentations across English, Arabic, and Arabizi phrasings.

**Do not verify:** Whether the clinical judgments embedded in the IMPORTANT clauses are correct. Passing tests confirm the LLM behaves as the text intends; they do not confirm the text is medically correct.

**Sample size caveat:** 1–3 cases per skill × language cell. The gate is "fires correctly, isn't trivially over-holding." This is not a sensitivity/specificity estimate. Widen per-skill test coverage before GA.

---

## Test evidence

Run: `.venv/bin/python -m pytest tests/test_entry_screen_integration.py -m slow -v`

| Arm | Cases | Pass bar | Result |
|---|---|---|---|
| Arm 1: Explicit contraindication | 4 (EN×2, AR×1, AZ×1) | 4/4 HOLD | **4/4 ✅** |
| Arm 2: Oblique contraindication | 6 (EN×3, AR×2, AZ×1) | ≥4/6 HOLD | **6/6 ✅** |
| Arm 3: FP arm — somatic target conditions | 4 (EN×2, AR×1, AZ×1) | 0/4 false holds | **0/4 ✅** |
| Arm 4: FP arm — ACT + safe_place | 4 (EN×2, AR×2) | 0/4 false holds | **0/4 ✅** |

Note: LLM-evaluated tests have known temperature stochasticity (~5% flake observed on Arabizi body scan under concurrent load). Results above are from isolated runs.

---

## Sign-Off Field

When approved, the clinical lead should confirm each IMPORTANT clause is medically defensible. Engineering will document the approval in each skill file header and in the governance table.

If any clause requires rewording: provide replacement text and engineering will update + re-run the FP arm before deployment.

Commit message format after approval:  
`feat(skills): activate criteria carve-outs — [Clinician Name] sign-off [date]`
