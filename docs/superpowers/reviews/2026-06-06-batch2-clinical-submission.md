# Batch 2 Clinical Sign-off Request — SageAI Skill Content

**Submitted:** 2026-06-06  
**Submitted by:** Engineering  
**Decision authority:** Clinical Lead  
**Scope:** Batch 2 skill content — mood_check_in proxy rule and contraindication strings for 17 skills cleared of dead routing rules in Batch 1  

---

## Background

Batch 1 (complete, merged to master) removed 21 step_policy rules that referenced signals the system could never observe at runtime, meaning they provided no real protection. They looked like safety rules but were silently inert.

Batch 2 replaces the clinically significant ones with correctly-placed contraindication instructions and, where applicable, adds a new rule using a live signal. Nothing in Batch 2 merges until this submission is returned with decisions.

This document contains four decision types. They are labelled explicitly because they require different things from the clinical lead: two are content judgements, one is a risk-acceptance decision, and one is an attestation of an existing production state.

---

## Item 1 — Wording Review

**Decision type:** Clinical content approval — is this wording appropriate?  
**What it gates:** Merge of contraindication strings for DV (7a/7h), trauma (7c/7d), and SI (7l) scenarios  
**Node 1 status:** All three have deterministic Node 1 backing. The contraindication text is a secondary, LLM-discretionary layer added on top of an already-active signal. Approving the wording does not change the primary detection mechanism.

### 7a/7h — Domestic violence / coercive relationship (assertive_communication, interpersonal_effectiveness)

**Context:** These skills teach assertiveness and boundary-setting. In a coercive relationship, practising assertiveness without safety screening can increase risk.

**Node 1 backing:** CF-005 (`domestic_situation` flag) — active, triggers on disclosure of controlling or abusive relationship dynamics. See Item 4 regarding the approval status of CF-005.

**Proposed contraindication text (to be added to the entry step of each skill):**

> If the user describes a situation where the other person's response to assertiveness carries a risk of escalation, threat, or control, for example a partner who monitors their messages, controls their finances, or responds to boundary-setting with anger or punishment, do not proceed with skills training. Name what you are noticing and ask gently about their safety instead.

**Decision requested:** Is this wording appropriate for a Gulf/UAE-context deployment?

---

### 7c/7d — Trauma-anchored cognitions (cbt_thought_record, cognitive_restructuring)

**Context:** Both skills involve challenging automatic negative thoughts by examining evidence for and against them. When the thought is anchored in a real traumatic event rather than a general cognitive pattern, evidence-challenging can feel invalidating and may worsen the therapeutic relationship.

**Node 1 backing:** CF-002 (`trauma_indicator` flag) — active, triggers on disclosure of trauma. See also: the `explore_distortion.contraindications` placement in `cbt_thought_record` — the pause instruction is at the step where thought-challenging begins, not at skill entry.

**Proposed contraindication text (to be added to the evidence-exploration step of each skill):**

> If the user discloses a traumatic event such as assault, abuse, significant loss, or a life-threatening experience, do not proceed with challenging the thoughts associated with that event. Thought challenging is not designed for trauma-anchored cognitions and can feel invalidating or destabilising. Validate the disclosure and let them lead.

**Decision requested:** Is this wording appropriate? Is the placement at the evidence-exploration step correct, or should the pause trigger earlier (at skill entry)?

---

### 7l — Suicidal ideation during psychoeducation (psychoed_depression)

**Context:** Psychoeducation about depression is informational. If a user discloses suicidal ideation mid-skill, the psychoeducation frame must be abandoned and the crisis pathway must take over.

**Node 1 backing:** `safety_check` / `crisis_phrases.json` — already the primary deterministic gate for SI. This contraindication is a belt-and-suspenders instruction for the LLM in case the user's disclosure is oblique or mid-sentence.

**Proposed contraindication text (to be added to the skill's contraindications field):**

> If the user discloses any suicidal ideation during this skill, exit immediately. Acknowledge what they said with care. Ask whether they are safe right now. Mention the crisis line (800 46342, free, 24/7). Psychoeducation is not appropriate when someone is expressing a wish to die.

**Decision requested:** Is this wording appropriate? Does the instruction to exit and check safety before mentioning the crisis line reflect the correct clinical sequence?

---

## Item 2 — Risk Acceptance

**Decision type:** Risk-acceptance — is LLM-discretionary protection alone acceptable for POC?  
**What it gates:** Merge of contraindication strings for physical condition (7e/7j) and dissociation (7i/7n) scenarios  
**Node 1 status:** No deterministic Node 1 flag exists for either physical conditions or dissociation. The contraindication text below would be the **only** guard. Engineering will not present this as equivalent to Item 1 — the clinical lead should decide with that gap stated plainly.

Post-Gitex backlog items to create Node 1 flags for both clusters exist, but they require clinical review of detection patterns and downstream routing, and are not in scope for the current POC.

### 7e/7j — Physical condition contraindications (dbt_tipp, progressive_muscle_relaxation)

**Context:** `dbt_tipp` includes a cold-water/temperature technique and paced intense breathing. `progressive_muscle_relaxation` involves tensing individual muscle groups. Both techniques carry a physical-harm pathway if used with an undisclosed contraindicated condition.

**No Node 1 flag exists.** There is no `physical_condition_mention` flag in the clinical flag set. The LLM is the only guard.

**Proposed contraindication text — dbt_tipp (temperature step):**

> If the user mentions a heart condition, Raynaud's syndrome, cold sensitivity, recent surgery, or any physical condition affecting their tolerance of cold or intense physical exertion, do not proceed with the temperature component. Offer paced breathing as the alternative within the skill.

**Proposed contraindication text — progressive_muscle_relaxation (any tensing step):**

> If the user mentions pain, a physical injury, or any condition affecting a muscle group being worked, do not instruct them to tense that area. Adapt the sequence to skip the affected area. If the user describes significant or widespread pain, gently note that muscle-tensing techniques may be worth checking with a healthcare provider before attempting.

**Decision requested:** Is LLM-discretionary protection alone acceptable on this physical-harm pathway for the POC? If yes, please note this is a time-limited risk-acceptance pending the post-Gitex Node 1 flag.

---

### 7i/7n — Dissociation (mindfulness_body_scan, safe_place_visualization)

**Context:** Body-focused and visualisation techniques can deepen dissociative states in users who are already experiencing detachment or derealisation. The existing dead rule was the only current guard; its removal (Batch 1) accurately removed a false impression of protection that was providing none at runtime.

**No Node 1 flag exists.** There is no `dissociation_indicator` flag in the clinical flag set (v7 defines five flags: substance, trauma, eating, domestic, medication). Post-Gitex backlog item exists to add dissociation as a sixth flag. Until then, the LLM is the only guard.

**Proposed contraindication text (to be added to both skills):**

> If the user reports feeling detached, unreal, floating, or like they are watching themselves from outside their body, pause immediately. Do not continue directing attention to body sensations or internal imagery. Gently orient them to the room and their immediate surroundings. Let them lead whether to continue or stop.

**Decision requested:** Is LLM-discretionary protection alone acceptable on this pathway for the POC? If yes, please note this is a time-limited risk-acceptance pending the post-Gitex dissociation flag (sixth clinical flag).

---

## Item 3 — Construct Validity

**Decision type:** Clinical construct question — is this signal an acceptable proxy for what the step is measuring?  
**What it gates:** Merge of the `mood_check_in` low-mood hold rule (Task 5b)  

**Background:** `mood_check_in` prompts the user to rate their mood on a 1–10 scale at the `score_mood` step. The previous rule held on a low self-report using a signal called `mood_score` — but that signal was never extracted from the user's message, so the rule was silently inert from the beginning. Batch 1 deleted the inert rule. Batch 2 proposes a replacement using `emotional_intensity`, which is a live system signal estimated from the user's message tone and language.

**The proposed Batch 2 rule:**

Hold and explore when `emotional_intensity <= 3` at the `score_mood` step.

**Why this is not a clean substitute — the limitation must be stated:**

The two constructs do not fully overlap:

- **Low-activation low-mood** (flat affect, anhedonia, low energy): the user rates their mood 2/10, the message is subdued. `emotional_intensity <= 3` fires. The proxy aligns.
- **High-activation low-mood** (agitated depression, dysphoric distress): the user rates their mood 2/10, but the message is distressed or pressured. `emotional_intensity` reads higher than 3 and the hold rule does not fire, even though the self-report is low.

The `emotional_intensity > 7` rule (already in the skill, a live rule that was correctly active) catches high-activation distress from the other direction. So the two rules together cover both ends — but the mid-range agitated-low-mood presentation (intensity 4–6, self-report low) is not caught by either.

**The honest framing for the clinical lead:**

This proxy catches low-activation low-mood and defers to the `> 7` rule for high-activation distress. It is explicitly interim — the correct fix is to extract the integer from the user's score response and wire a real `mood_score` signal (post-Gitex backlog). The question for the clinical lead is:

1. Is holding-and-exploring when the system reads low emotional activation at the mood-rating step the intended clinical behaviour?
2. Is the split approach — `<= 3` catches low-activation; `> 7` catches high-activation distress; mid-range agitated presentations are not held — acceptable for POC, with the proxy explicitly marked interim?

If yes to both, Task 5b can proceed. If the answer to (2) is that score_mood needs a real self-report extraction, that becomes a pre-Batch 2 engineering gate rather than a post-Gitex item.

**Proposed rule text (for reference):**

> User rated their mood low and is showing low emotional activation. Do not advance. Gently explore: 'What has been making things feel heavy lately?' Hold here until there is a clearer picture of what is driving the low mood.

---

## Item 4 — Attestation (Narrow, Immediate)

**Decision type:** Formal approval of a flag already live in production  
**What it gates:** CF-005 `approved_by` field can be stamped; required before DV contraindications (Item 1, 7a/7h) reference CF-005 as their primary detection mechanism in any clinical documentation

**The situation:** Clinical flag CF-005 (`domestic_situation`) has been active in production since May 2026. The `approved_by` field in `clinical_flag_patterns.json` is `null`. This means a live detection rule that affects routing for disclosed domestic situations has no recorded clinical sign-off. Engineering is not able to stamp this field — it requires clinical authority.

**CF-005 detection scope (for reference):**

CF-005 fires on disclosures of controlling, abusive, or coercive relationship dynamics in the user's message. It raises a clinical flag visible in the audit log and intended to inform downstream handling. It does not route to a crisis pathway on its own — it is a flag, not an exit trigger.

**Decision requested:** Does the clinical lead attest that CF-005 (`domestic_situation`) is approved for production use as currently specified? If yes, engineering will update `approved_by` to reflect this attestation and the date.

---

## Summary of decisions

| Item | Decision type | Gate |
|------|--------------|------|
| 1a — DV wording (7a/7h) | Wording review | DV contraindications merge |
| 1b — Trauma wording (7c/7d) | Wording review | Trauma contraindications merge; confirm step placement |
| 1c — SI wording (7l) | Wording review | SI exit instruction merge |
| 2a — Physical condition (7e/7j) | Risk acceptance | Physical contraindications merge; LLM-only guard acknowledged |
| 2b — Dissociation (7i/7n) | Risk acceptance | Dissociation contraindications merge; LLM-only guard acknowledged |
| 3 — mood_check_in proxy (5b) | Construct validity | mood_check_in low-activation hold rule merge |
| 4 — CF-005 attestation | Production attestation | `approved_by` field update in `clinical_flag_patterns.json` |

Items 1 and 4 are linked — 7a/7h reference CF-005 as primary detection. If Item 4 is not attested, Item 1a cannot be framed as "backed by deterministic Node 1 detection" and the risk profile changes.

Items 2a and 2b may be returned as partial approvals — risk acceptance for one pathway but not the other is a valid outcome and would unblock whichever cluster is approved.

Item 3 may return "proxy acceptable" or "extract the integer first" — both are clear gates for engineering.

**No code changes will merge on any item until written confirmation is received.**
