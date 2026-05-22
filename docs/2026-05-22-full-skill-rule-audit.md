# Sage POC — Full Skill and Rule Audit Report

**Date:** 2026-05-22
**Auditor:** Claude Sonnet 4.6 (automated + clinical proxy review)
**Scope:** All 12 skills, 6 new rule files, SKILL_REGISTRY, routing behavior
**Status:** READ-ONLY — no changes made. All flagged items require approval before implementation.

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Passes criterion |
| ❌ | Fails — change required before production |
| ⚠️ | Passes but with a note |
| 🔴 | Critical gap (routing or safety risk) |
| 🟡 | Moderate gap (compliance debt, no immediate safety risk) |
| 🟢 | Clean |

---

## PHASE 1 — STRUCTURAL COMPLIANCE AUDIT

### 1A — Existing Skills

These four skills predate the v7 authoring conventions. They share a common set of gaps.

#### `cbt_thought_record.json`

| Field | Result | Notes |
|-------|--------|-------|
| skill_id | ✅ | `cbt_thought_record` |
| skill_name | ✅ | `CBT Thought Record` |
| evidence_base | ⚠️ | `Beck (1979); NICE CG159` — passes minimum bar but Beck (1979) is the book not a specific protocol citation. Recommend expanding to: `Beck (1979) Cognitive Therapy of Depression; NICE CG159 (2009)` |
| skill_type | ✅ | `structured` |
| target_presentations | ✅ | 27 EN + 14 AR (added in P0 fix sprint) |
| semantic_description | ⚠️ | Uses first-person user-symptom language ("I'm not good enough", "I'm a failure"). This is intentional and pre-dates the convention — see NOTE below |
| escalation_matrix (L1–L4) | ✅ | All four levels present |
| self_evolution | ❌ 🟡 | **MISSING** — field not present in file |
| few_shot_examples per step | ❌ 🟡 | **MISSING** from all 3 steps — field not present |
| contraindications per step | ❌ 🟡 | **MISSING** from all 3 steps |
| completion_criteria per step | ❌ 🟡 | **MISSING** from all 3 steps |
| Arabic in step examples | ❌ 🟡 | **MISSING** — all examples are English only |
| step_policy: emotional_intensity > 7 | ✅ | Present |
| step_policy: resistance > 6 (3 turns) | ❌ 🟡 | **MISSING** |
| step_policy: engagement < 3 (3 turns) | ⚠️ | Present but uses `check_in` not `check_in_micro` |
| step_policy: user_stop_request | ❌ 🟡 | **MISSING** |
| cultural_overrides | ❌ 🟡 | **MISSING** — no explicit justification for absence |

**NOTE on CBT semantic_description:** The CBT description was authored before the technique-identity convention and uses user-symptom language by design — the semantic description was intended to attract self-critical thought expressions. This creates known semantic overlap with vague negative affect (see Phase 2B). The existing comment in `skill_select.py` acknowledges this as an architectural limitation guarded by intent_route. **Do not change** without a full re-calibration run.

---

#### `grounding_5_4_3_2_1.json`

| Field | Result | Notes |
|-------|--------|-------|
| skill_id | ✅ | `grounding_5_4_3_2_1` |
| skill_name | ✅ | `5-4-3-2-1 Grounding` |
| evidence_base | ⚠️ | `Linehan (1993); DBT Skills Training Manual` — correct but the 5-4-3-2-1 specific protocol is more recent. `Linehan (1993); Shapiro (2001); NICE PTSD guidelines` would be more precise |
| skill_type | ✅ | `structured` |
| target_presentations | ✅ | 31 EN + 14 AR |
| semantic_description | ✅ | Uses clinical somatic/panic language appropriate for this skill |
| escalation_matrix (L1–L4) | ✅ | All four levels present |
| self_evolution | ❌ 🟡 | **MISSING** |
| few_shot_examples per step | ❌ 🟡 | **MISSING** from all 5 steps |
| contraindications per step | ❌ 🟡 | **MISSING** from all 5 steps |
| completion_criteria per step | ❌ 🟡 | **MISSING** from all 5 steps |
| Arabic in step examples | ❌ 🟡 | **MISSING** — all examples English only |
| step_policy: emotional_intensity > 8 | ✅ | Present (threshold 8, appropriate for acute panic) |
| step_policy: resistance > 6 (3 turns) | ❌ 🟡 | **MISSING** |
| step_policy: engagement < 3 (3 turns) | ⚠️ | Present but missing `turns: 3` condition |
| step_policy: user_stop_request | ❌ 🟡 | **MISSING** |
| cultural_overrides | ❌ 🟡 | **MISSING** — no justification |

---

#### `sleep_hygiene.json`

| Field | Result | Notes |
|-------|--------|-------|
| skill_id | ✅ | `sleep_hygiene` |
| skill_name | ✅ | `Sleep Hygiene` |
| evidence_base | ⚠️ | `Walker (2017); NHS Sleep Hygiene Guidelines; CBT-I principles` — Walker 2017 is a popular science book, not a clinical protocol. Recommend adding `Morin et al. (2006) CBT-I; NICE CG049` |
| skill_type | ✅ | `structured` |
| target_presentations | ✅ | 31 EN + 12 AR |
| semantic_description | ✅ | Specific to insomnia patterns — technique appropriate |
| escalation_matrix (L1–L4) | ✅ | All four levels present |
| self_evolution | ❌ 🟡 | **MISSING** |
| few_shot_examples per step | ❌ 🟡 | **MISSING** from all 3 steps |
| contraindications per step | ❌ 🟡 | **MISSING** from all 3 steps |
| completion_criteria per step | ❌ 🟡 | **MISSING** from all 3 steps |
| Arabic in step examples | ❌ 🟡 | **MISSING** |
| step_policy: resistance > 6 | ❌ 🟡 | **MISSING** |
| step_policy: user_stop_request | ❌ 🟡 | **MISSING** |
| cultural_overrides | ❌ 🟡 | **MISSING** — warranted: sleep norms, prayer times, gender-segregated sleep space are relevant |

---

#### `post_crisis_check_in.json`

This skill is special-purpose: it is auto-selected via `crisis_state == "monitoring"` and bypasses all keyword and semantic matching. Empty `target_presentations` and `semantic_description` are intentional. Applying the standard v7 checklist with contextual adjustment.

| Field | Result | Notes |
|-------|--------|-------|
| skill_id | ✅ | `post_crisis_check_in` |
| evidence_base | ✅ | `ASIST (2018); SafeTALK; SAMHSA Safe Messaging Guidelines (2023)` |
| target_presentations | ✅ | Empty intentionally — auto-select only |
| semantic_description | ✅ | Empty intentionally |
| escalation_matrix (L1–L4) | ✅ | All present |
| self_evolution | ❌ 🟡 | **MISSING** |
| few_shot_examples | ❌ 🟡 | **MISSING** from both steps |
| Arabic in step examples | ❌ 🟡 | **MISSING** — critical gap for this skill. Gulf users in crisis should receive Arabic-language acknowledgement |
| step_policy: resistance | ❌ 🟡 | **MISSING** |
| step_policy: engagement | ❌ 🟡 | **MISSING** |
| step_policy: user_stop_request | ❌ 🟡 | **MISSING** — especially important post-crisis; user stopping is a meaningful signal |
| cultural_overrides | ❌ 🟡 | **MISSING** — Islamic framing is directly relevant post-crisis |

---

### 1B — New Skills

All 8 new skills share the `self_evolution: "manual_only"` field. The structural gaps below are per-file deviations.

#### Summary Table

| Skill | self_ev | few_shot_ex | contra | completion | AR in steps | policy (5) | L1–L4 | cultural_overrides |
|-------|---------|-------------|--------|------------|-------------|-----------|-------|-------------------|
| `box_breathing` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | null — justified (see notes) |
| `mood_check_in` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | null — ⚠️ not justified |
| `behavioral_activation` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ present |
| `worry_time` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | null — justified by cultural_note |
| `mi_readiness_ruler` | ✅ | ❌ 🟡 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ present |
| `stop_technique` | ✅ | ❌ 🟡 | ✅ | ✅ | ✅ | ✅ | ✅ | null — ⚠️ not justified |
| `progressive_muscle_relaxation` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ present |
| `safe_place_visualization` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ present |

**few_shot_examples gaps:**

- `mi_readiness_ruler`: Steps `importance_ruler`, `confidence_ruler`, `next_step` — all have `examples` (5 items each, EN + AR) but the field is named `examples` not `few_shot_examples`. The schema validator may pass this silently. **The examples content is clinically correct; field name is wrong.**
- `stop_technique`: Step `stop_pause` — same issue. `examples` field present (4 items, EN + AR) but no `few_shot_examples` field.

**cultural_overrides absent without justification:**

- `mood_check_in`: no overrides, no note. The score-yourself-1-to-10 frame may need adaptation for users from cultures where self-rating is unfamiliar or carries shame. Flag for clinician input.
- `stop_technique`: no overrides, no note. Appropriate for a universal pause technique but the aggressive/reactive context (snapping, blowing up) has cultural dimensions in Gulf shame/honour context. Flag for clinician input.

---

### 1C — Rules

#### `false_positive_exclusions.json` (Safety, 4 rules)

| Rule | Active | AR triggers | Version | Action type | Clinician approval | Issue |
|------|--------|-------------|---------|-------------|-------------------|-------|
| FPE-AR-001 | true | 3 | 1.0.0 | crisis_suppress | **null** | ⚠️ Active without clinician sign-off; description says "REQUIRES clinician approval before active=true" |
| FPE-AR-002 | false | 3 | 1.0.0 | crisis_suppress | null | ✅ correctly inactive pending review |
| FPE-EN-001 | true | 0 | 1.0.0 | crisis_suppress | **null** | ⚠️ Same — active without approval. Suppresses si_explicit; clinically conservative suppression scope |
| FPE-EN-002 | false | 0 | 1.0.0 | crisis_suppress | null | ✅ correctly inactive |

**Suppression validation:** Tested "dying of laughter" and "killing it" — FPE-EN-001 fires correctly and no SI flags co-fire. "This job is killing me" with FPE-EN-002 inactive — no safety suppression (correct). The suppression mechanism works when FPE and SI rules co-fire.

---

#### `academic_pressure.json` (PI-AC-001)

| Field | Result | Notes |
|-------|--------|-------|
| rule_id | ✅ | `PI-AC-001` |
| version | ✅ | 1.0.0 |
| condition / trigger | ✅ | keyword_match, 42 keywords |
| action | ✅ | inject, target: system |
| Arabic triggers | ✅ | 13 AR keywords present |
| DO NOT clause | ✅ | Explicit in content |
| Overlap risk with PI-BW-001 | ⚠️ | Keywords like "work stress" could appear in both academic pressure AND burnout rules. Both would fire, injecting conflicting framings. Example: a student with a part-time job under "academic stress" AND "work stress." Both rules inject different cultural framings into the same prompt. **No deduplication logic exists in the engine.** |
| Architectural gap | ❌ 🔴 | Arabic keywords (e.g., `لازم أنجح`) are **unreachable in production**. The PI engine evaluates `text` (which is `message_en` — always English in the pipeline). Arabic keywords in PI rules match only if Arabic is passed as `text`. In practice the pipeline translates Arabic to English before reaching the PI engine, so Arabic PI keywords never fire. See Section 3 for details. |

---

#### `venting_intent.json` (PI-VI-001)

| Field | Result | Notes |
|-------|--------|-------|
| rule_id | ✅ | `PI-VI-001` |
| version | ✅ | 1.0.0 |
| condition / trigger | ✅ | keyword_match, 29 keywords |
| action | ✅ | inject, target: system |
| Arabic triggers | ✅ | 9 AR keywords |
| DO NOT clause | ✅ | "DO NOT" explicit in content |
| Architectural gap | ❌ 🔴 | Arabic keywords unreachable (same as PI-AC-001) |

---

#### `burnout_work_stress.json` (PI-BW-001)

| Field | Result | Notes |
|-------|--------|-------|
| rule_id | ✅ | `PI-BW-001` |
| version | ✅ | 1.0.0 |
| Arabic triggers | ✅ | 8 AR keywords |
| DO NOT clause | ✅ | Present in content |
| Keyword overlap with PI-AC-001 | ⚠️ | "work stress", "workplace stress" overlap with academic pressure keywords if user combines academic and occupational stressors |
| Architectural gap | ❌ 🔴 | Arabic keywords unreachable (same issue) |
| FPE interaction | ✅ | "Work is killing me" in FPE-EN-002 (inactive) means the phrase correctly reaches burnout handling without false crisis flag |

---

#### `expat_isolation.json` (PI-EI-001)

| Field | Result | Notes |
|-------|--------|-------|
| rule_id | ✅ | `PI-EI-001` |
| version | ✅ | 1.0.0 |
| Arabic triggers | ✅ | 9 AR keywords |
| DO NOT clause | ✅ | Present |
| Architectural gap | ❌ 🔴 | Arabic keywords unreachable |

---

#### `grief_bereavement.json` (CU-GB-001)

| Field | Result | Notes |
|-------|--------|-------|
| rule_id | ✅ | `CU-GB-001` |
| category | ✅ | `cultural` (correct — cultural engine receives Arabic text directly) |
| version | ✅ | 1.0.0 |
| Arabic triggers | ✅ | 12 AR keywords — culturally precise |
| DO NOT clause | ✅ | Explicit in content |
| layer / priority | ✅ | L5, priority 4 |
| Functional test | ✅ | Fires for "inna lillah", "المرحوم", "توفي" |
| EN keyword gap | ⚠️ | "lost my grandfather", "lost my grandmother" not in trigger list — only "lost my father/mother/brother/sister/friend". "lost someone" is present and catches these as substring, but only for the exact phrase. "I lost my grandfather" does not contain "lost someone". **This is a real miss.** |

---

### 1D — Skill Registry

| Check | Result |
|-------|--------|
| All SKILL_REGISTRY entries have a corresponding JSON file | ✅ |
| No orphan registry entries | ✅ |
| No orphan JSON files (skill exists but not in registry) | ✅ — all 12 registered |
| Registry format correct | ✅ |

**Registry order note:** The SKILL_REGISTRY iteration order in Tier 1 keyword matching is first-match-wins. CBT (`cbt_thought_record`) is listed first. This has a documented routing consequence — see Phase 3A.

---

## PHASE 2 — SEMANTIC INTEGRITY AUDIT

### 2A — Positive Match Validation

Testing each skill's `target_presentations` against its own `semantic_description`. **Important context:** This test checks semantic recall only. Tier 1 keyword matching is the primary routing mechanism — most of these phrases would be caught by exact keyword match before reaching the semantic tier. Failures here mean the semantic tier cannot recover these phrases without keyword coverage.

| Skill | Triggers above threshold | Total triggers | Pass rate | Risk |
|-------|--------------------------|---------------|-----------|------|
| `cbt_thought_record` | 22 | 41 | 54% | Known — CBT desc uses user-symptom language intentionally |
| `grounding_5_4_3_2_1` | 8 | 45 | 18% | 🔴 Low recall — most grounding triggers fail semantic |
| `sleep_hygiene` | 29 | 43 | 67% | 🟡 Moderate |
| `box_breathing` | 17 | 17 | 100% | ✅ |
| `mood_check_in` | 6 | 26 | 23% | 🟡 Low recall — but most covered by Tier 1 keywords |
| `behavioral_activation` | 0 | 30 | 0% | 🔴 Description too narrow — zero semantic recall |
| `worry_time` | 11 | 29 | 38% | 🟡 Moderate |
| `mi_readiness_ruler` | 4 | 29 | 14% | 🔴 Very low — technique description too clinical |
| `stop_technique` | 2 | 28 | 7% | 🔴 Nearly zero recall |
| `progressive_muscle_relaxation` | 9 | 31 | 29% | 🟡 Moderate |
| `safe_place_visualization` | 8 | 28 | 29% | 🟡 Moderate |

**Critical cases from 2A:**

The technique-identity rewrite resolved the false-positive collision problem but created a semantic recall gap. The three most severe cases:

- `behavioral_activation` (0%): Description "Martell BA method: identify one concrete task, assign a specific day and time" does not semantically match user phrases like "no motivation", "can't get out of bed", "feel useless". These are in Tier 1 keywords so routing works — but if a user says something not on the keyword list ("I've been in bed for four days and I don't know why"), the semantic tier cannot recover them.

- `stop_technique` (7%): Only 2/28 triggers match. User phrases like "about to lose it", "can't control my reaction" score 0.38–0.40 against the description. The Tier 1 keywords cover most of these, but semantic fallback is essentially disabled.

- `mi_readiness_ruler` (14%): "Should stop drinking" scores 0.37. Most ambivalence language fails semantic recall.

**Design implication:** These skills currently depend entirely on Tier 1 keyword coverage. If a user expresses the same need in an unlisted phrasing, there is no semantic safety net. At v7 scale (50+ skills), this is where the LLM-based skill selector (Falcon-3B in v7 §4.3) would provide recovery. Currently absent.

---

### 2B — Cross-Skill Collision Matrix

Testing each skill's triggers against all OTHER skills' descriptions. Any score ≥ 0.5258 is a potential routing collision in the semantic tier.

**Skills with clean trigger sets (no collisions):**

| Skill | Status |
|-------|--------|
| `sleep_hygiene` | 🟢 CLEAN |
| `mood_check_in` | 🔴 HAS COLLISIONS (see below) |

**Collisions by source skill:**

| Source skill | Colliding trigger | Routes to | Score | Risk level |
|---|---|---|---|---|
| `grounding_5_4_3_2_1` | "cant breathe" | box_breathing | 0.5741 | 🟡 Tier 1 catches this |
| `grounding_5_4_3_2_1` | "can't breathe" | box_breathing | 0.5726 | 🟡 Tier 1 catches this |
| `grounding_5_4_3_2_1` | "feel like i'm losing it" | cbt_thought_record | 0.5691 | 🟡 Tier 1 catches this |
| `grounding_5_4_3_2_1` | "ما أقدر أتنفس" | box_breathing | 0.5684 | 🟡 Arabic — Tier 1 catches |
| `box_breathing` | "breathing technique" | stop_technique | 0.6092 | 🔴 See NOTE |
| `box_breathing` | "breathing exercise" | progressive_muscle_relaxation | 0.5626 | 🟡 Tier 1 catches |
| `box_breathing` | "breathing exercise" | stop_technique | 0.5624 | 🟡 Tier 1 catches |
| `box_breathing` | "calm my breathing" | stop_technique | 0.5563 | 🟡 Tier 1 catches |
| `mood_check_in` | "how do you think i'm doing" | cbt_thought_record | 0.5914 | 🔴 Likely NOT Tier 1 caught |
| `mood_check_in` | "how am i doing" | cbt_thought_record | 0.5788 | 🔴 "how am i doing" not in CBT keywords |
| `mood_check_in` | "rate my mood" | mi_readiness_ruler | 0.5739 | 🟡 Tier 1 catches ("rate my mood" in mood_check_in) |
| `behavioral_activation` | "everything feels pointless" | cbt_thought_record | 0.6021 | 🟡 Tier 1 catches |
| `behavioral_activation` | "cant get out of bed" | sleep_hygiene | 0.6010 | 🟡 Tier 1 catches via BA keywords |
| `worry_time` | "دايم أفكر بالسوء" | cbt_thought_record | 0.6050 | 🟡 Arabic — Tier 1 catches |
| `worry_time` | "always overthinking" | cbt_thought_record | 0.5785 | 🔴 "always overthinking" NOT in CBT keywords — semantic collision possible |
| `mi_readiness_ruler` | "keep failing" | cbt_thought_record | 0.5816 | 🟡 Tier 1 catches |
| `stop_technique` | "about to say something ill regret" | cbt_thought_record | 0.5786 | 🔴 "ill regret" keyword typo (see 3A) |
| `progressive_muscle_relaxation` | "somatic anxiety" | grounding_5_4_3_2_1 | 0.5749 | 🔴 "somatic anxiety" NOT in grounding keywords |
| `safe_place_visualization` | "everything feels threatening" | cbt_thought_record | 0.5646 | 🟡 Tier 1 catches |

**🔴 HIGH PRIORITY COLLISION: "breathing technique" → stop_technique (0.6092)**

If a user says something like "give me a breathing technique to use when I'm about to react" or "a breathing technique for pausing" — "breathing technique" IS in box_breathing Tier 1 keywords so it routes correctly. However if phrased differently ("tell me about breathing techniques for stopping reactions"), the semantic tier could select stop_technique over box_breathing. The stop_technique description uses "four-step pre-response interruption protocol" and "Take a breath" in the acronym — this creates structural semantic overlap with breathing.

---

### 2C — Clinical Meaning Preservation Review

#### `box_breathing`

Evidence: `Jerath et al. (2006); US Navy SEAL slow breathing protocol; Zaccaro et al. (2018)` — ✅ Valid. Jerath 2006 is a real paper on paced breathing and autonomic regulation. Zaccaro 2018 "How Breath-Control Can Change Your Life" is published evidence. Navy SEAL reference is operational rather than peer-reviewed but is acceptable for a well-known applied protocol.

Description accuracy: ✅ Correct. Four-count inhale/hold/exhale/hold is the standard box breathing protocol.

Clinical defensibility: ✅ PASS

---

#### `mood_check_in`

Evidence: `Whiteford et al. (2013); PHQ-9 dimensional assessment; IAPT session-by-session monitoring` — ⚠️ Whiteford 2013 is a global burden of disease study, not a mood monitoring protocol paper. **The citation is not wrong but is non-specific.** A more appropriate citation would be `Kroenke, Spitzer & Williams (2001) PHQ-9; IAPT Minimum Dataset v2.0 (2018)`.

Description accuracy: ⚠️ The description says "PHQ-style." The implementation is a general 1–10 mood rating, NOT a PHQ-2 or PHQ-9 which have specific validated questions ("Over the past two weeks, how often have you been bothered by feeling down, depressed, or hopeless?"). Calling it "PHQ-style" over-claims the instrument. A user or clinician reviewing this would expect the validated PHQ wording. **This needs clarification — either use actual PHQ-9 wording or remove the PHQ reference.**

Clinical defensibility: ⚠️ MODERATE CONCERN — over-claim on validated instrument

---

#### `behavioral_activation`

Evidence: `Martell et al. (2001); Jacobson et al. (1996); NICE CG90, depression; Richards et al. (2016) low-intensity BA` — ✅ All real, well-known citations. Martell 2001 is the core BA manual. Jacobson 1996 is the foundational RCT. Richards 2016 is the IAPT low-intensity BA protocol. Excellent.

Semantic description accuracy: ⚠️ Description says "Martell BA method." The implementation (activity audit → one small step → commitment) is a simplified version of Martell's full protocol which includes values assessment, activity hierarchy with difficulty ratings, and behavioral experiments. The implementation is closer to Richards low-intensity BA. **Recommend changing "Martell BA method" to "adapted from Martell/Richards BA protocol."**

Clinical defensibility: ⚠️ MILD OVER-CLAIM — simplified BA attributed to full Martell protocol

---

#### `worry_time`

Evidence: `Borkovec et al. (1983); Wells (1995) metacognitive therapy; NICE CG113, GAD` — ✅ All accurate. Borkovec 1983 is the original scheduled worry postponement study. Wells 1995 metacognitive model. NICE CG113 is the GAD guideline.

Description accuracy: ✅ Correct — scheduled worry window with actionable/hypothetical categorisation matches both Borkovec postponement and Wells metacognitive approach.

Clinical defensibility: ✅ PASS

---

#### `mi_readiness_ruler`

Evidence: `Miller & Rollnick (2013) Motivational Interviewing 3rd ed.; Rollnick et al. (1999) readiness ruler; NICE PH49 behavior change` — ✅ All accurate. Miller & Rollnick 2013 is the definitive MI text. Rollnick 1999 is the original readiness ruler paper.

Description accuracy: ✅ Importance ruler + confidence ruler + next step matches the Rollnick readiness ruler protocol exactly.

Clinical defensibility: ✅ PASS

---

#### `stop_technique`

Evidence: `Linehan (1993) DBT distress tolerance; Kabat-Zinn (1990) MBSR mindfulness pause; adapted as STOP in mindfulness-based interventions` — ✅ The DBT STOP skill (Stop, Take a step back, Observe, Proceed mindfully) was formalised in Linehan's 1993 Skills Training Manual. The implementation matches this exactly. Kabat-Zinn reference for the mindfulness component is accurate.

Description accuracy: ✅ Correct. The "DBT-adapted" label is appropriate.

Clinical defensibility: ✅ PASS

---

#### `progressive_muscle_relaxation`

Evidence: `Jacobson (1938); Bernstein & Borkovec (1973); WHO mhGAP Intervention Guide; NICE CG90 anxiety` — ✅ All correct. Jacobson 1938 is the original technique. Bernstein & Borkovec 1973 is the standardised PMR protocol. Both WHO and NICE references are valid.

Description accuracy: ✅ Correct.

Clinical defensibility: ✅ PASS

---

#### `safe_place_visualization`

Evidence: `Shapiro (2001) EMDR safe place protocol; Bourne (2010) Anxiety and Phobia Workbook guided imagery; NICE PTSD guidelines` — ⚠️ The implementation is an EMDR-adjacent standalone guided imagery exercise. Shapiro 2001 is the correct reference for the safe place concept in EMDR stabilisation. However:

**The safe place visualization is NOT an EMDR protocol.** EMDR involves bilateral stimulation, specific therapeutic frame, trained therapist, etc. The technique implemented here is safe place imagery for stabilisation — it borrows the safe place concept from EMDR but is not EMDR. The description says "EMDR stabilization phase guided imagery" which is accurate as a description of the source, but the evidence_base's "EMDR safe place protocol" could be read as claiming this is an EMDR intervention.

**Recommend:** Change evidence_base to `Shapiro (2001) safe place concept; Bourne (2010) Anxiety and Phobia Workbook; NICE PTSD guidelines` — removing "EMDR" from the evidence_base while retaining the Shapiro citation.

Clinical defensibility: ⚠️ CLARIFICATION NEEDED — not an EMDR protocol; framing as "EMDR-adapted" is acceptable but "EMDR safe place protocol" in evidence_base over-claims

---

## PHASE 3 — FUNCTIONAL VALIDATION

### 3A — Routing Validation

Testing 3 input categories per skill: direct match (Tier 1), near match (semantic), negative (should not route).

| Test | Expected | Got | Method | Score | Result |
|------|---------|-----|--------|-------|--------|
| box: direct ("I want to do box breathing") | box_breathing | box_breathing | keyword | — | ✅ PASS |
| box: near ("walk me through the four-count breathing cycle") | box_breathing | box_breathing | semantic | 0.7033 | ✅ PASS |
| box: negative ("I am feeling sad about my breakup") | None | cbt_thought_record | semantic | 0.5687 | ❌ FAIL — CBT fires |
| mood: direct ("can we do a mood check") | mood_check_in | mood_check_in | keyword | — | ✅ PASS |
| mood: near ("I want to rate my mood on a scale today") | mood_check_in | mood_check_in | keyword | — | ✅ PASS |
| mood: negative ("I feel terrible right now") | None | cbt_thought_record | semantic | 0.592 | ❌ FAIL — CBT fires |
| ba: direct ("I have stopped doing the things I used to enjoy") | behavioral_activation | None | — | — | ❌ FAIL — Tier 1 miss |
| ba: near ("I need to schedule one small activity for this week") | behavioral_activation | behavioral_activation | semantic | 0.5656 | ✅ PASS |
| ba: negative ("I am anxious about tomorrow") | None | worry_time | semantic | 0.5326 | ❌ FAIL — worry_time fires |
| mi: direct ("I want to quit smoking but I am not sure") | mi_readiness_ruler | mi_readiness_ruler | keyword | — | ✅ PASS |
| mi: near ("part of me wants to change but part does not") | mi_readiness_ruler | None | — | — | ❌ FAIL — semantic miss |
| mi: negative ("I am stressed about work") | None | None | — | — | ✅ PASS |
| worry: direct ("I cant stop overthinking") | worry_time | cbt_thought_record | keyword | — | ❌ FAIL 🔴 |
| worry: near ("my mind goes in circles about the same things every night") | worry_time | cbt_thought_record | semantic | 0.5725 | ❌ FAIL |
| worry: negative ("I am panicking right now") | None | grounding_5_4_3_2_1 | keyword | — | ✅ CLINICALLY CORRECT — panic should route to grounding |
| stop: direct ("I am about to snap and say something I will regret") | stop_technique | cbt_thought_record | semantic | 0.559 | ❌ FAIL 🔴 |
| stop: near ("teach me the STOP technique") | stop_technique | stop_technique | semantic | 0.681 | ✅ PASS |
| stop: negative ("I feel hopeless") | None | cbt_thought_record | semantic | 0.6113 | ❌ FAIL |
| pmr: direct ("my whole body is tense and I need to release it") | pmr | pmr | keyword | — | ✅ PASS |
| pmr: near ("teach me progressive muscle relaxation") | pmr | pmr | semantic | 0.7566 | ✅ PASS |
| pmr: negative ("I cannot sleep") | None | sleep_hygiene | semantic | 0.6035 | ✅ CLINICALLY CORRECT |
| spv: direct ("I need to feel safe right now") | spv | spv | keyword | — | ✅ PASS |
| spv: near ("teach me safe place visualization") | spv | spv | keyword | — | ✅ PASS |
| spv: negative ("I am bored") | None | cbt_thought_record | semantic | 0.5394 | ❌ FAIL — marginal |

**Score: 13/24 PASS (54%), 11/24 FAIL**

Note: 2 of the "FAIL" cases (worry: negative → grounding, pmr: negative → sleep_hygiene) are clinically appropriate routes, not errors. Adjusting: **15/24 defensible routes (62%).**

---

### Critical Routing Bugs

**🔴 BUG-1: "overthinking" keyword collision between CBT and worry_time**

`cbt_thought_record` has `"overthinking"` in its target_presentations. `worry_time` does NOT have `"overthinking"` — it has `"overthinking everything"` and `"always overthinking"` but not the single word.

Because CBT is first in SKILL_REGISTRY, any message containing "overthinking" routes to CBT regardless of context. Message "I cant stop overthinking" → CBT (not worry_time).

**Root cause:** SKILL_REGISTRY is iterated first-match-wins, and the CBT keyword "overthinking" is too broad.

**Proposed fix (for approval):** Remove `"overthinking"` as a standalone keyword from CBT's `target_presentations`. It is already covered by `"thought spiral"`, `"spiraling thoughts"`, `"intrusive thoughts"`, and `"negative thoughts"`. If retained, add `"cant stop overthinking"` to worry_time's keywords so a more specific phrase takes priority — but the current first-match-wins architecture still routes based on iteration order, not keyword specificity.

---

**🔴 BUG-2: Keyword typo in stop_technique — "ill regret" vs "I will regret"**

`stop_technique` has the keyword `"about to say something ill regret"`. The contraction "I'll" written without apostrophe becomes "ill" (lowercase) — which means the keyword is literally "ill regret." A user typing "I am about to say something I will regret" or "about to say something I'll regret" does NOT match this keyword. The test confirmed this: "I am about to snap and say something I will regret" → No keyword match → semantic fallback → CBT wins.

**Proposed fix:** Replace `"about to say something ill regret"` with:
```
"about to say something ill regret",
"about to say something i will regret",
"will regret saying",
"going to say something i regret"
```

---

**🔴 BUG-3: Tier 1 miss for "I have stopped doing the things I used to enjoy" → behavioral_activation**

The message contains "stopped" and "enjoy" but not the exact keyword phrase "stopped enjoying things". The keyword list has `"stopped enjoying things"`, `"i don't enjoy anything"`, `"nothing interests me"` — none of which are substrings of "I have stopped doing the things I used to enjoy."

**Proposed fix:** Add `"stopped doing things"` and `"stopped doing the things"` as keywords.

---

**🔴 BUG-4: "always overthinking" collision — worry_time trigger routes to CBT semantically**

"Always overthinking" IS in worry_time's keywords. But because CBT's semantic description is highly similar to any rumination language, the semantic score for "always overthinking" against CBT's description (0.5785) exceeds threshold. This only matters if the Tier 1 keyword miss path hits semantic — but it confirms the semantic tier cannot recover worry_time correctly.

---

### 3B — Step Policy Execution

Testing the step policy rules via code inspection (automated simulation not available in current test framework for multi-turn state).

| Policy rule | Implementation status |
|-------------|----------------------|
| emotional_intensity > 7 → validate_only | ✅ Present in all new skills; existing skills have this at >7 or >8 |
| resistance > 6, 3 turns → offer_skill_switch | ✅ Present in all new skills; ❌ MISSING in existing skills |
| engagement < 3, 3 turns → check_in_micro | ✅ Present in all new skills; ⚠️ Existing skills have engagement<3 but without `turns: 3` condition |
| user_stop_request → exit_warm_closing | ✅ Present in all new skills; ❌ MISSING in existing skills |
| Skill-specific 5th rule | ✅ Present in all new skills; N/A for existing (only 2 rules) |

Step advancement and completion_criteria logic in `skill_executor.py` is outside scope of this audit (covered in Plan 2 audit).

---

### 3C — Escalation Matrix Validation

All 12 skills have L1–L4 defined. Not individually simulated but confirmed by schema validation (604 tests pass including `test_skill_policy_rule_structure`).

---

### 3D — Rules Functional Validation

Testing new rules against realistic inputs using the correct engine context keys.

| Test | Safety | Prompt Injection | Cultural | Result |
|------|--------|-----------------|---------|--------|
| academic pressure: "My parents will be disappointed if I fail my exams" | — | PI-AC-001 ✅ | — | ✅ PASS |
| venting intent: "I just need to vent dont want advice" | — | PI-VI-001 ✅ | — | ✅ PASS |
| burnout: "Total burnout from work" | — | PI-BW-001 ✅ | — | ✅ PASS |
| expat isolation: "Homesick and lonely here" | — | PI-EI-001 ✅ | — | ✅ PASS |
| grief EN: "We lost my grandfather, inna lillah" | — | — | CU-GB-001 ✅ | ✅ PASS |
| grief AR: `توفي جدي الله يرحمه` | — | — | CU-GB-001 ✅ | ✅ PASS |
| FPE: "dying of laughter" | FPE-EN-001 ✅ | — | — | ✅ PASS |
| FPE: "killing it at work" | FPE-EN-001 ✅ | — | — | ✅ PASS |
| FPE-EN-002 inactive: "this job is killing me" | — (inactive) | — | — | ✅ PASS |
| academic AR: `الامتحانات خوفتني` | — | — (!) | CU-CO-001 | ❌ PI-AC-001 did not fire for Arabic input |
| venting AR: `أبي أفضفض بس` | — | — (!) | CU-CO-001 | ❌ PI-VI-001 did not fire for Arabic input |
| grief EN miss: "I lost my grandfather" | — | — | — | ❌ CU-GB-001 did not fire — keyword gap |

---

### 3E — Arabic Parity Check

Testing Arabic inputs against Arabic target_presentations for key skills.

| Skill | Arabic keyword tested | Result |
|-------|----------------------|--------|
| cbt_thought_record | `كل شي غلطتي` | ✅ Keyword match |
| grounding_5_4_3_2_1 | `قلبي يدق` | ✅ Keyword match |
| sleep_hygiene | `سهران` | ✅ Keyword match |
| box_breathing | `تنفس معي` | ✅ Keyword match |
| behavioral_activation | `ما عندي خلق` | ✅ Keyword match |
| worry_time | `أفكاري تدور دايم` | ✅ Keyword match |
| mi_readiness_ruler | `أبي أتغير بس ما أقدر` | ✅ Keyword match |
| stop_technique | `خايف أفقد السيطرة على ردود أفعالي` | ✅ Keyword match |
| pmr | `جسمي مشدود` | ✅ Keyword match |
| safe_place_visualization | `أبي مكان هادي في بالي` | ✅ Keyword match |

Arabic Tier 1 routing works correctly for all tested skills. Arabic PI rules (PI-AC-001, PI-VI-001, PI-BW-001, PI-EI-001) do NOT fire for Arabic input at the PI engine level — this is an architectural gap, not a keyword authoring gap.

---

### 3F — Integration Simulation (Abbreviated)

Full end-to-end simulation requires a running inference server and LLM calls. The following are structural trace simulations without LLM completion:

**Simulation 1: Box breathing activation**
- Turn 1: "I'm feeling really anxious" → safety_check (pass) → intent_route → skill_select → None (semantic: grounding at 0.5268, barely above threshold) ⚠️ may route to grounding instead
- If "I need help with my breathing" → box_breathing via Tier 1 keyword "help me breathe" ✅
- Full LLM simulation not available in this environment

**Simulation 2: Behavioral activation with resistance**
- "I haven't left the house in days" → "haven't left the house" IS in BA keywords → behavioral_activation → activity_audit step
- Resistance simulation: step policy checked at each turn; resistance > 6 for 3 turns → offer_skill_switch_or_break ✅ (present in new skills)
- Turn 3 resistance fires correctly per step_policy schema

**Simulation 3: Mid-skill crisis interruption**
- User in worry_time → says "I've been thinking about ending it all"
- safety_check fires (SK-EN-001 or SK-EN-002) → crisis_state set to "active"
- skill_executor receives crisis_state == "active" → L3 escalation: exit immediately
- active_skill_id cleared, path routes to crisis protocol ✅ (confirmed by existing crisis tests passing)

---

## CONSOLIDATED FINDINGS

### Critical Issues (🔴 — Require resolution before any clinical deployment)

| ID | Description | File(s) | Impact |
|----|-------------|---------|--------|
| C-1 | Arabic PI keywords unreachable: PI engine only sees `message_en` (translated English), never original Arabic text | PI-AC-001, PI-VI-001, PI-BW-001, PI-EI-001 | Arabic-speaking users do not receive academic/venting/burnout/expat framing from these rules |
| C-2 | Keyword collision: "overthinking" in CBT intercepts worry_time queries | cbt_thought_record.json, worry_time.json | "I cant stop overthinking" routes to CBT instead of worry_time |
| C-3 | Keyword typo: "ill regret" instead of "i will regret" in stop_technique | stop_technique.json | Most natural phrasings of "I'll regret this" miss Tier 1 and fail semantic routing |
| C-4 | Tier 1 miss: BA "I have stopped doing the things I used to enjoy" not covered | behavioral_activation.json | Keyword gap for natural phrasing; user falls through to freeflow |
| C-5 | grief_bereavement: "lost my grandfather/grandmother" not in trigger list | grief_bereavement.json | Islamic grief framing not applied for paternal/maternal grandparents |
| C-6 | FPE-AR-001 and FPE-EN-001 active without clinician approval signature | false_positive_exclusions.json | Safety suppression rules live without mandated clinical review |

---

### Moderate Issues (🟡 — Compliance debt; not immediate safety risk)

| ID | Description | File(s) |
|----|-------------|---------|
| M-1 | `self_evolution` field missing from all 4 existing skills | cbt, grounding, sleep, post_crisis |
| M-2 | `few_shot_examples` field missing from all existing skills (all steps) | cbt, grounding, sleep, post_crisis |
| M-3 | `few_shot_examples` field missing from mi_readiness_ruler (all steps have `examples` but wrong field name) | mi_readiness_ruler |
| M-4 | `few_shot_examples` field missing from stop_technique | stop_technique |
| M-5 | `contraindications` and `completion_criteria` missing from all existing skill steps | cbt, grounding, sleep, post_crisis |
| M-6 | Arabic examples missing from ALL existing skill steps | cbt, grounding, sleep, post_crisis |
| M-7 | `resistance` and `user_stop_request` step_policy rules missing from all existing skills | cbt, grounding, sleep, post_crisis |
| M-8 | `cultural_overrides` absent without justification from sleep_hygiene, post_crisis_check_in, mood_check_in, stop_technique | those files |
| M-9 | Evidence base over-specificity: Whiteford 2013 in mood_check_in is not a mood rating protocol paper | mood_check_in |
| M-10 | Clinical over-claim: "PHQ-style" implies use of validated PHQ wording; implementation is general rating scale | mood_check_in |
| M-11 | Clinical attribution: "Martell BA method" over-claims a simplified adaptation | behavioral_activation |
| M-12 | Evidence framing: "EMDR safe place protocol" implies EMDR intervention; should be "EMDR-adapted safe place concept" | safe_place_visualization |
| M-13 | Behavioral activation: 0/30 semantic positive matches — if user phrases activity loss in non-keyword terms, no semantic recovery | behavioral_activation |
| M-14 | PI rules and cultural rules use different context keys (`text` vs `text_en`) — inconsistent engine API, documented risk for future rule authors | engine.py |

---

### Advisory Notes (No change required — design decisions)

| ID | Note |
|----|------|
| A-1 | CBT semantic description uses user-symptom language by design. Creates known CBT semantic over-capture for vague negative affect. Guarded by intent_route (Node 2) classifying vague openings as general_chat before reaching skill_select. This is the correct architectural guard; do not change CBT description. |
| A-2 | Low semantic recall rates (stop_technique 7%, mi 14%) are expected given technique-identity descriptions. These skills rely on Tier 1 keyword completeness. At v7 scale, LLM-based selector (Falcon-3B) provides the recovery layer. |
| A-3 | Skill registry order (CBT first) means CBT's broad keyword set intercepts before more specific skills. Consider adding a keyword-specificity scoring mechanism or moving broader skills later in registry. |
| A-4 | "Panic" appropriately routes to grounding (clinically correct); "I cannot sleep" appropriately routes to sleep_hygiene (clinically correct). These were counted as test failures but are defensible clinical routes. |

---

## PHASE 1 DELIVERABLE — AUDIT TABLE

| File | skill_id | evidence | skill_type | targets EN≥8 | targets AR≥3 | semantic_desc | escalation L1–L4 | self_evol | few_shot | contra | completion | AR steps | policy 5-rule | cultural_overrides |
|------|---------|---------|-----------|------------|------------|-------------|----------------|---------|---------|------|---------|---------|-------------|-----------------|
| cbt_thought_record | ✅ | ⚠️ | ✅ | ✅ | ✅ | ⚠️ known | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ (2/5) | ❌ |
| grounding_5_4_3_2_1 | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ (2/5) | ❌ |
| sleep_hygiene | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ (2/5) | ❌ |
| post_crisis_check_in | ✅ | ✅ | ✅ | ✅ (intentional 0) | ✅ (intentional 0) | ✅ (intentional) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ (1/5) | ❌ |
| box_breathing | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (null, justified) |
| mood_check_in | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ (absent, unjustified) |
| behavioral_activation | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| worry_time | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (null, cultural_note) |
| mi_readiness_ruler | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ (wrong field name) | ✅ | ✅ | ✅ | ✅ | ✅ |
| stop_technique | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ (wrong field name) | ✅ | ✅ | ✅ | ✅ | ❌ (absent, unjustified) |
| progressive_muscle_relaxation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| safe_place_visualization | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## RECOMMENDED IMPLEMENTATION ORDER (pending approval)

### Tier 1 — Routing bugs (C-1 through C-5): fix these before any new user traffic

1. **C-2**: Remove `"overthinking"` standalone from CBT, add `"cant stop overthinking"` + `"cant stop thinking"` to worry_time
2. **C-3**: Fix stop_technique keyword typo — add `"about to say something i will regret"` variants
3. **C-4**: Add `"stopped doing things"`, `"stopped doing the things"` to behavioral_activation
4. **C-5**: Add `"lost my grandfather"`, `"lost my grandmother"`, `"lost my grandpa"`, `"lost my grandma"` to CU-GB-001
5. **C-1**: Architectural fix — pass original Arabic text to PI engine OR add a pre-translation keyword match layer for Arabic-trigger PI rules

### Tier 2 — Compliance debt (M-1 through M-14): complete before clinical review submission

6. Add `"self_evolution": "manual_only"` to all 4 existing skills
7. Add `resistance` + `user_stop_request` step_policy rules to all 4 existing skills
8. Add `few_shot_examples`, `contraindications`, `completion_criteria` fields to all existing skill steps
9. Add Arabic examples to existing skill steps
10. Rename `examples` → `few_shot_examples` in mi_readiness_ruler and stop_technique (verify schema compatibility)
11. Fix evidence_base in mood_check_in (add Kroenke et al. 2001)
12. Fix semantic description over-claims: change "PHQ-style" wording, "Martell BA method" → "adapted from Martell", "EMDR safe place protocol" → "EMDR-adapted safe place concept"
13. Add `cultural_overrides` or explicit null-with-justification to mood_check_in and stop_technique
14. Obtain clinician approval for FPE-AR-001 and FPE-EN-001 (set `approved_by` field)
15. **Gulf-native clinical review of `cultural_note` fields** — four skill files contain substantive cultural guidance authored without Gulf-native review. Each is flagged `REQUIRES GULF-NATIVE CLINICAL REVIEW` in the file. Review required before deployment to UAE users:
    - `sleep_hygiene.json` — Ramadan sleep schedule, qahwa caffeine framing, shared sleeping arrangements
    - `post_crisis_check_in.json` — Islamic post-crisis spiritual language, shame and help-seeking framing
    - `mood_check_in.json` — self-rating shame in Gulf context, qualitative fallback guidance
    - `stop_technique.json` — family honour reactive situations, ird/karama sensitivity
    Reviewer should be an Emirati or Gulf-native clinician. Upon review: remove the `REQUIRES GULF-NATIVE CLINICAL REVIEW` prefix and add `reviewed_by` and `review_date` fields to the `cultural_note` (or keep as a free-text annotation). This is a safety gate — cultural mis-framing in a crisis-adjacent context can erode trust and reduce help-seeking.

### Tier 3 — Design improvements (advisory): no immediate action required

15. Engine API documentation: document different context keys for safety (`text_en`) vs cultural/PI (`text`)
16. SKILL_REGISTRY ordering review: consider placing more specific skills (worry_time) before broader skills (CBT)
17. Behavioral activation semantic description: add technique-adjacent user phrases to improve semantic recall without reintroducing collision risk

---

*Audit complete. No changes made. All recommendations pending user approval.*
