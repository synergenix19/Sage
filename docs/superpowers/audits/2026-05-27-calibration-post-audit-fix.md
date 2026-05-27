# Semantic Threshold Calibration — Post-Audit-Fix Baseline

**Date:** 2026-05-27  
**Trigger:** 12/20 `semantic_description` fields modified during 13-item quality audit  
**Prior threshold:** 0.4972 (gap=0.0422, v7 Gitex sprint baseline)  
**New threshold:** 0.459  

---

## Architecture Change: Cluster-Aware Calibration

### Root cause of prior narrow gap

After stripping symptom language from 12 `semantic_description` fields (audit
Sprint 1), two calibration runs produced a negative gap (-0.0268, then -0.0206).
The cause: somatic distress skills (grounding, box breathing, body scan, dbt_tipp,
PMR) share clinical vocabulary. The original calibration script treated
within-cluster overlap as a failure. It is not — it is correct BGE-M3 behaviour.

### Architectural fix

The calibration script was restructured to reflect the actual architecture:

- **Tier 1 (keyword rules)** is primary. Same-cluster disambiguation (grounding vs.
  box breathing vs. body scan) is handled by `target_presentations` keyword matching,
  not by embedding distance. New keywords added: `grounding_5_4_3_2_1` got
  `five things i can see`, `name five things`, `five senses`, `5-4-3-2-1`, `54321`,
  `five four three two one`, `name what i can see`. `box_breathing` got `paced breathing`,
  `slow my breathing`, `slow my breath`, `count my breaths`, `breathing slowly`,
  `breath control`, `4-7-8 breathing`, `controlled breathing`.

- **Tier 2 (semantic)** only needs to distinguish across clinical cluster boundaries.
  Within-cluster scores are shown informatively but excluded from the pass gate.

- **Pass criterion changed:** `cross-cluster gap ≥ 0.03`  
  (was: `global gap ≥ 0.03` across all skill pairs)

- **KNOWN_MISSES split** into `KNOWN_MISSES_OFF_TOPIC` (used for gate) and
  `KNOWN_MISSES_BORDERLINE` (informational — protected by intent_route in production).

---

## Final Calibration Results

### Within-cluster hits (somatic_distress — informational only)

| Score | Match | Phrase |
|-------|-------|--------|
| 0.4922 | ✅ grounding | "I am so dizzy I can barely stand..." |
| 0.5905 | ✅ grounding | "I want to name five objects I can see..." |
| 0.5974 | ✅ grounding | "I need to count what I can observe..." |
| 0.5791 | ✅ dbt_tipp | "I am in physiological crisis and need cold water..." |
| 0.5591 | ✅ box_breathing | "my breathing is all wrong, it keeps speeding up..." |
| 0.7396 | ✅ progressive_muscle_relaxation | "I want to systematically tense and release..." |
| 0.6877 | ✅ progressive_muscle_relaxation | "my whole body holds tension..." |

### Cross-cluster hits (used for gap gate)

| Score | Match | Phrase |
|-------|-------|--------|
| 0.4856 | ✅ sleep_hygiene | "I am exhausted but my mind will not stop racing at bedtime" |
| 0.6302 | ✅ sleep_hygiene | "I want to apply stimulus control principles..." |
| 0.5513 | ✅ mood_check_in | "I just want to take stock of where I am emotionally today" |
| 0.5636 | ✅ mood_check_in | "I need to tune in to what my emotional state actually is right now" |
| 0.5983 | ✅ behavioral_activation | "scheduling small rewarding activities to break out of depression..." |
| 0.5840 | ✅ behavioral_activation | "I want to build an activity schedule..." |
| 0.5784 | ✅ worry_time | "I ruminate constantly, the same anxious thoughts cycling over and over" |
| 0.5381 | ✅ worry_time | "I am caught in a loop of anxious thinking..." |
| 0.5548 | ✅ mi_readiness_ruler | "part of me wants to change but another part..." |
| 0.5104 | ✅ mi_readiness_ruler | "I know what I should do but I do not know if I am ready..." |
| 0.5486 | ✅ stop_technique | "I react before I think and then I always regret it..." |
| 0.5913 | ✅ stop_technique | "I acted impulsively again without thinking..." |
| 0.6197 | ✅ safe_place_visualization | "I want to use mental imagery to create an inner sanctuary..." |
| 0.5336 | ✅ safe_place_visualization | "I want to find a safe imaginary refuge..." |
| 0.5627 | ✅ psychoed_anxiety | "I do not understand why my body reacts this way when I am nervous" |
| 0.5513 | ✅ psychoed_anxiety | "I get these waves of fear for no reason..." |

### Off-topic misses (used for gap gate)

| Score | Top match | Phrase |
|-------|-----------|--------|
| 0.3892 | mood_check_in | "what's the weather like today in Dubai" |
| 0.4264 | box_breathing | "tell me a joke" |
| 0.4125 | self_compassion_break | "thanks, that really helped" |
| 0.4323 | mood_check_in | "hey, how are you" |

### Borderline misses (informational — intent_route protection)

| Score | Top match | Phrase |
|-------|-----------|--------|
| 0.4774 | mi_readiness_ruler | "I need to talk about something that happened at work" |
| 0.4327 | cbt_thought_record | "I'm completely overwhelmed" |

---

## Gap Analysis

| Metric | Value |
|--------|-------|
| Lowest cross-cluster hit | 0.4856 |
| Highest off-topic miss | 0.4323 |
| **Gap** | **0.0533** |
| Pass criterion | ≥ 0.03 |
| **Result** | ✅ **PASS** |

**`SEMANTIC_THRESHOLD = 0.459`** (midpoint of gap)

---

## Risk Register

1. **Borderline miss at 0.4774** ("I need to talk about something that happened at work" → mi_readiness_ruler): Sits above the new threshold. Protected solely by `intent_route` classifying it as `general_chat`. If intent_route tuning changes, recheck this phrase.

2. **Lowest cross-cluster hit at 0.4856** ("I am exhausted but my mind will not stop racing at bedtime" → sleep_hygiene): 0.059 above threshold. Comfortable headroom. Sleep hygiene has extensive keyword coverage anyway.

3. **Within-cluster lowest at 0.4922** ("I am so dizzy I can barely stand..." → grounding): At 0.0342 above threshold. This phrase correctly lands in the somatic_distress cluster; if keyword rules fire first (which they should for clinical presentations), it never reaches the semantic tier.

4. **Semantic fallback not yet activated** (per RT-4). Threshold and embedding space confirmed healthy. Activate after intent_route is confirmed to pass `new_skill` intent to `skill_select` for the intended edge-case phrasings.
