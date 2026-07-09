# A1 Boundary Freeze — DRAFT for clinical approval

**Date:** 2026-06-22 · **rev 2026-06-23** (coordinator + clinical-lead review folded in).
**Status:** DRAFT. The *structure* is endorsed by coordinator review (2026-06-23). Three clinical affirmations remain genuinely open and are **not** settled here: §3a (crisis-adjacent dialect line — needs a native-dialect clinician), §4 (whether `psychotic_referral` is ever free-entry — population/deployment-specific clinical call), and the §2a/§5a confirmations. Not frozen until those are answered and the clinical lead signs.
**Produces:** the frozen `boundary.md` that gates all A2 labeling.
**Source of truth:** `src/sage_poc/skill_ids.py` (27 skills) and no other.

---

## Decision ledger

| Item | Status (2026-06-23) | Set by |
|---|---|---|
| §1 skill edge | structure endorsed | clinical lead confirms |
| §2 domain edge | structure endorsed; examples **pending confirm** | clinical lead |
| §3 crisis-exclusion (3 rules) | endorsed | clinical lead |
| **§3a crisis-adjacent dialect line** | **deferred — native-dialect clinician + task #21 cross-check** | native-speaker clinician |
| **§4 psychotic_referral / post_crisis exclusion** | **structure endorsed as default**; free-entry-guard affirmation **pending** | clinical lead |
| §5 flag-free ID-OOS exemplar | proposed; **pending confirm** | clinical lead |

---

## 1. Skill edge (in-scope envelope)

In-scope = a non-crisis user presentation that maps to the technique construct of a clinician-authored skill. The 27 skills by construct family (the envelope is these constructs, not phrase lists):

| Family | Skills |
|---|---|
| Cognitive / CBT | `cbt_thought_record`, `cognitive_restructuring` |
| Behavioral activation | `behavioral_activation` |
| Distress tolerance (acute) | `grounding_5_4_3_2_1`, `dbt_tipp`, `stop_technique` |
| Relaxation / somatic regulation | `box_breathing`, `progressive_muscle_relaxation`, `safe_place_visualization`, `mindfulness_body_scan` |
| Worry / rumination | `worry_time` |
| Sleep | `sleep_hygiene` |
| Mood monitoring | `mood_check_in` |
| Motivation / ambivalence | `mi_readiness_ruler` |
| ACT / values / self-compassion | `values_clarification`, `act_psychological_flexibility`, `self_compassion_break` |
| Interpersonal | `assertive_communication`, `interpersonal_effectiveness` |
| Psychoeducation | `psychoed_anxiety`, `psychoed_depression`, `psychoed_stress` |
| Grief | `grief_loss` |
| Domain-specific anxiety | `financial_anxiety` |
| Referral / after-care (see §4) | `psychotic_referral`, `post_crisis_check_in` |

**Proposed envelope:** in-scope = subjective psychological/emotional distress and coping in a non-crisis user, addressable by one of the above technique constructs.

## 2. Domain edge (mental-health-support boundary)

Separates *in-domain-out-of-scope* (ID-OOS → ABSTAIN, a support concern with no skill) from *far-out-of-scope* (far-OOS → ABSTAIN, outside support).

- **In-domain:** subjective emotional/psychological distress, mood, anxiety, stress, sleep, grief, relationships, motivation, self-worth, coping.
- **Far-OOS:** medical/diagnostic questions, medication advice (Node-1 flag territory), legal/financial *transactions*, general factual/info requests, off-topic chit-chat. Crisis is not in this taxonomy — Node 1 intercepts (§3).
- **ID-OOS:** a genuine wellbeing concern the 27 skills don't cover — e.g. body-image distress, anger management, OCD-specific protocols, specific phobias, perfectionism, parenting stress.

⚠ **§2a (clinical, pending):** confirm the in-domain / far-OOS line, and confirm the ID-OOS examples are genuinely uncovered (not actually served by an existing skill).

## 3. Crisis-exclusion ruling (three rules) — endorsed

Follows v7 Layer-1 OR-fusion (any crisis signal → `crisis_protocol`; `skill_select` never sees a crisis turn):

1. **Crisis is never a routing target.**
2. **Crisis-adjacent Khaleeji dialect → task #21** (Arabic crisis bench), not this routing slice.
3. **Any crisis utterance present asserts path-invariance only**, never a route-to-skill label.

### ⚠ §3a — crisis-adjacent dialect line — DEFERRED to a native-dialect clinician

This is the highest-stakes boundary in the system, the under-escalation direction is the dangerous one, and the cases are Khaleeji-dialect — so it is **not decidable from English glosses** and is explicitly deferred. **Methodological guidance recorded (coordinator), not a clinical decision:**
- Draw the line **conservatively toward escalation.** OR-fusion already biases that way, so the residual judgment is narrow: *which dialectal phrasings count as a crisis signal at all.*
- That residual is a **native-speaker labeling/clinical question**, ideally **cross-checked against the task #21 bench** rather than decided in this doc.

## 4. `psychotic_referral` / `post_crisis_check_in` — structure endorsed as default

**Endorsed as the conservative default (coordinator review):** EXCLUDE both as `skill_select` targets; reach them via deterministic/clinical-state paths only; **measure** the exclusion adversarially (A2.8) rather than declare it. Reasoning held to: gating escalation/screening-result delivery through deterministic auditable logic — not a cosine-similarity threshold — is standard for safety-critical paths; a false-positive psychosis referral is iatrogenic and a false-negative should not be owned by an embedding threshold; `post_crisis_check_in` is state-gated by definition.

⚠ **§4a (clinical, pending the lead):** *should `psychotic_referral` ever be free-entry, and under what guard?* This is population- and deployment-specific and must be the clinical lead's affirmation, not engineering's or the coordinator's. Default stands (excluded) unless the lead rules otherwise with a stated guard.

## 5. Flag-free ID-OOS exemplar (F3)

**Proposed:** *"Lately I keep comparing my body to others and feel bad about how I look"* (body-image distress — in-domain, unmatched by the 27, fires no Node-1 flag).

⚠ **§5a (clinical, pending):** approve or substitute (must be in-domain, uncovered, flag-free).

## 6. Sign-off

`boundary.md` is a Test Content Guardrails clinical artifact. Freezes on the clinical lead's **name + date** below, after §2a/§3a/§4a/§5a are answered.

```
Approved (with edits as marked): ____________________   Date: __________
§3a resolved by native-dialect clinician:  ____________   Date: __________
```
