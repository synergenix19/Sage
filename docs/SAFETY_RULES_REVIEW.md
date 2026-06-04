# Safety Rules Clinical Review Document

**Status:** Draft — awaiting Sage Clinics sign-off  
**Reviewer:** [Name, Role, Date]  
**Arabic reviewer:** [Native Khaleeji clinician — Name, Date]

---

## Review Protocol

For each rule: mark **Approved**, **Modified** (with specific changes), or **Rejected** (with reason).
Arabic patterns must be reviewed by a native Khaleeji speaker.

**False positive exclusions (FPE-*) require EXTRA scrutiny** — each is a decision not to trigger safety.

---

## Accepted Sensitivity Decisions

The following precision/recall trade-offs have been reviewed and accepted. Each entry documents patterns that will occasionally match benign speech and the clinical rationale for accepting that cost.

### SK-EN-002: Passive SI patterns — 4 known edge-case matches

**Decision date:** 2026-05-21  
**Decision:** Accept current sensitivity. Do not narrow patterns.

The following phrases trigger `si_passive` in non-crisis contexts:

| Triggering phrase | Benign reading | Pattern responsible | Clinical decision |
|---|---|---|---|
| "I just want it to stop raining" | Weather complaint | `i just want it to stop` | **Accept.** "I just want it to stop" catches genuine passive ideation ("I just want the pain to stop"). Benign readings are rare edge cases that require conversational context the keyword engine cannot assess. |
| "I make everything worse when I cook" | Self-deprecating humour | `i make everything worse` | **Accept.** Clinically relevant for burden-related ideation ("I make everything worse for everyone"). Kitchen-specific readings add trivial false positive rate. |
| "there's no way out of this traffic" | Situational frustration | `there's no way out` | **Accept.** "There's no way out" is a primary passive SI marker (C-SSRS hopelessness cluster). Traffic-specific context is resolvable in the Full Build via MARBERT contextual classification. |
| "I have no future in this company" | Career frustration | `i have no future` | **Accept.** "I have no future" is a core hopelessness indicator. Company-qualified variants are uncommon enough that the recall gain outweighs the precision cost. |

**Rationale:** These four patterns are drawn from the C-SSRS hopelessness and burden subscales. In a mental health support context, erring toward sensitivity is the correct clinical default — a missed passive SI detection is a more serious failure than a false trigger that the LLM resolves conversationally. When MARBERT replaces keyword matching in the Full Build, contextual classification will resolve these naturally.

**Reviewer sign-off required:** The clinical team must explicitly confirm this sensitivity level is acceptable before production deployment.

- [ ] **Clinical team accepts SK-EN-002 sensitivity as-is** — _[Reviewer name, Date]_
- [ ] **Clinical team requests pattern narrowing** — _[specify which patterns and constraints]_

---

## CF-001: Substance use detection

**File:** `sage_poc/rules/data/safety/clinical_flag_patterns.json`)  
**Language:** `any`  
**Action:** `{"type": "clinical_flag", "flag_id": "substance_use"}`  
**Active:** `True`

### Patterns

- `drinking`
- `drunk`
- `alcohol`
- `alcoholism`
- `liquor`
- `beer`
- `wine`
- `drugs`
- `drug use`
- `cocaine`
- `heroin`
- `marijuana`
- `weed`
- `using pills`
- `numb the pain`
- `cope with drink`
- `كحول`
- `مخدرات`
- `حبوب مخدرة`
- `مدمن`

### Clinical Rationale

_[To be completed by clinical team]_

### Trigger Examples

_Should trigger (≥2 examples):_

1. 
2. 

_Should NOT trigger (≥1 example):_

1. 

### Sign-off

- [ ] **Approved as-is**
- [ ] **Approved with modifications:** _[specify]_
- [ ] **Rejected:** _[reason]_

---

## CF-002: Trauma indicator detection

**File:** `sage_poc/rules/data/safety/clinical_flag_patterns.json`)  
**Language:** `any`  
**Action:** `{"type": "clinical_flag", "flag_id": "trauma_indicator"}`  
**Active:** `True`

### Patterns

- `abuse`
- `abused`
- `assault`
- `assaulted`
- `attacked`
- `violence`
- `hurt me`
- `hit me`
- `rape`
- `molested`
- `trauma`
- `إساءة`
- `اعتداء`
- `عنف`

### Clinical Rationale

_[To be completed by clinical team]_

### Trigger Examples

_Should trigger (≥2 examples):_

1. 
2. 

_Should NOT trigger (≥1 example):_

1. 

### Sign-off

- [ ] **Approved as-is**
- [ ] **Approved with modifications:** _[specify]_
- [ ] **Rejected:** _[reason]_

---

## CF-003: Eating concern detection

**File:** `sage_poc/rules/data/safety/clinical_flag_patterns.json`)  
**Language:** `any`  
**Action:** `{"type": "clinical_flag", "flag_id": "eating_concern"}`  
**Active:** `True`

### Patterns

- `purging`
- `binge eating`
- `starving myself`
- `not eating`
- `eating disorder`
- `anorexia`
- `bulimia`
- `لا اكل`
- `اتجوع`

### Clinical Rationale

_[To be completed by clinical team]_

### Trigger Examples

_Should trigger (≥2 examples):_

1. 
2. 

_Should NOT trigger (≥1 example):_

1. 

### Sign-off

- [ ] **Approved as-is**
- [ ] **Approved with modifications:** _[specify]_
- [ ] **Rejected:** _[reason]_

---

## CF-004: Medication mention detection

**File:** `sage_poc/rules/data/safety/clinical_flag_patterns.json`)  
**Language:** `any`  
**Action:** `{"type": "clinical_flag", "flag_id": "medication_mention"}`  
**Active:** `True`

### Patterns

- `medication`
- `antidepressant`
- `dosage`
- `prescribed`
- `prescription`
- `دواء`
- `مضادات الاكتئاب`
- `جرعة`

### Clinical Rationale

_[To be completed by clinical team]_

### Trigger Examples

_Should trigger (≥2 examples):_

1. 
2. 

_Should NOT trigger (≥1 example):_

1. 

### Sign-off

- [ ] **Approved as-is**
- [ ] **Approved with modifications:** _[specify]_
- [ ] **Rejected:** _[reason]_

---

## CF-005: Domestic situation safety flag — physical safety concerns in intimate/household context

**File:** `sage_poc/rules/data/safety/clinical_flag_patterns.json`)  
**Language:** `any`  
**Action:** `{"type": "clinical_flag", "flag_id": "domestic_situation"}`  
**Active:** `True`

### Patterns

- `hits me`
- `hit me`
- `abusive relationship`
- `domestic violence`
- `my partner hurts me`
- `my husband hurts me`
- `my wife hurts me`
- `he won't let me leave`
- `she won't let me leave`
- `won't let me go`
- `controlling relationship`
- `controls everything`
- `physically abused`
- `being beaten`
- `يضربني`
- `علاقة مسيئة`
- `عنف اسري`
- `عنف منزلي`
- `ما يخليني اطلع`
- `يؤذيني`
- `يحبسني`

### Clinical Rationale

_[To be completed by clinical team]_

### Trigger Examples

_Should trigger (≥2 examples):_

1. 
2. 

_Should NOT trigger (≥1 example):_

1. 

### Sign-off

- [ ] **Approved as-is**
- [ ] **Approved with modifications:** _[specify]_
- [ ] **Rejected:** _[reason]_

---

## SK-EN-001: Core English explicit SI keywords

**File:** `sage_poc/rules/data/safety/crisis_keywords.json`)  
**Language:** `en`  
**Action:** `{"type": "crisis_flag", "flag_id": "si_explicit"}`  
**Active:** `True`

### Patterns

- `kill myself`
- `want to die`
- `end my life`
- `suicide`
- `suicidal`
- `hurt myself`
- `self-harm`
- `cut myself`
- `overdose`
- `better off dead`
- `can't go on`
- `not worth living`
- `want to disappear`
- `don't want to be here`
- `thinking of ending it`
- `i'm a burden`
- `don't want to be alive`
- `end it all`
- `no reason to live`
- `ending it`
- `ending my life`

### Clinical Rationale

_[To be completed by clinical team]_

### Trigger Examples

_Should trigger (≥2 examples):_

1. 
2. 

_Should NOT trigger (≥1 example):_

1. 

### Sign-off

- [ ] **Approved as-is**
- [ ] **Approved with modifications:** _[specify]_
- [ ] **Rejected:** _[reason]_

---

## SK-AZ-001: Arabizi / code-switching explicit SI

**File:** `sage_poc/rules/data/safety/crisis_keywords.json`)  
**Language:** `en`  
**Action:** `{"type": "crisis_flag", "flag_id": "si_explicit"}`  
**Active:** `True`

### Patterns

- `want to mat`
- `wallah i want to die`
- `abi amoot`
- `aby amoot`
- `abi amwt`
- `aby amwt`
- `khalas i give up`
- `bidi amoot`
- `bedi amoot`
- `mabi akoon`
- `ma abgha akamil`
- `ta3abt mn el7ayat`
- `ta3abt mn alhayat`

### Clinical Rationale

_[To be completed by clinical team]_

### Trigger Examples

_Should trigger (≥2 examples):_

1. 
2. 

_Should NOT trigger (≥1 example):_

1. 

### Sign-off

- [ ] **Approved as-is**
- [ ] **Approved with modifications:** _[specify]_
- [ ] **Rejected:** _[reason]_

---

## SK-AR-001: Arabic MSA and Gulf explicit SI (alef-normalized patterns)

**File:** `sage_poc/rules/data/safety/crisis_keywords.json`)  
**Language:** `ar`  
**Action:** `{"type": "crisis_flag", "flag_id": "si_explicit"}`  
**Active:** `True`

### Patterns

- `اريد الموت`
- `اريد ان اموت`
- `انتحار`
- `انهي حياتي`
- `اوذي نفسي`
- `افكر في الانتحار`
- `اريد ان اقتل نفسي`
- `اتمنى الموت`
- `ابي اموت`
- `ابغى اموت`
- `ودي اموت`
- `ابي انهي حياتي`
- `ابغى انهي حياتي`
- `ابي اخلص من حياتي`
- `ابغى اختفي`
- `ابي اجرح نفسي`
- `ابغى اجرح نفسي`
- `بدي اقتل حالي`
- `بدي اموت`
- `عايز اموت`
- `عاوز اموت`
- `نفسي اموت`
- `انهاء حياتي`
- `ما ابي اعيش`
- `ما ابغى اعيش`

### Clinical Rationale

_[To be completed by clinical team]_

### Trigger Examples

_Should trigger (≥2 examples):_

1. 
2. 

_Should NOT trigger (≥1 example):_

1. 

### Sign-off

- [ ] **Approved as-is**
- [ ] **Approved with modifications:** _[specify]_
- [ ] **Rejected:** _[reason]_

---

## SK-EN-003: Self-harm method references indicating planning beyond ideation

**File:** `sage_poc/rules/data/safety/crisis_keywords.json`)  
**Language:** `en`  
**Action:** `{"type": "crisis_flag", "flag_id": "si_method"}`  
**Active:** `True`

### Patterns

- `how to overdose`
- `how many pills to take`
- `jumping off a bridge`
- `cutting my wrists`
- `cutting deep`
- `where to cut myself`
- `pills to kill myself`
- `ways to end my life`
- `how to hurt myself badly`
- `methods to die`

### Clinical Rationale

_[To be completed by clinical team]_

### Trigger Examples

_Should trigger (≥2 examples):_

1. 
2. 

_Should NOT trigger (≥1 example):_

1. 

### Sign-off

- [ ] **Approved as-is**
- [ ] **Approved with modifications:** _[specify]_
- [ ] **Rejected:** _[reason]_

---

## SK-EN-004: Third-party crisis reports — user describing someone else in crisis; does NOT set is_safe=False for speaker

**File:** `sage_poc/rules/data/safety/crisis_keywords.json`)  
**Language:** `en`  
**Action:** `{"type": "third_party_crisis", "flag_id": "third_party_si"}`  
**Active:** `True`

### Patterns

- `my friend told me she wants to die`
- `my friend told me he wants to die`
- `my friend wants to die`
- `my friend wants to kill herself`
- `my friend wants to kill himself`
- `my sister is suicidal`
- `my brother is suicidal`
- `someone i know wants to end their life`
- `my friend said she wants to kill herself`
- `my friend said he wants to kill himself`
- `my colleague mentioned wanting to die`
- `my brother wants to hurt himself`
- `my sister wants to hurt herself`
- `my friend is thinking of ending it`

### Clinical Rationale

_[To be completed by clinical team]_

### Trigger Examples

_Should trigger (≥2 examples):_

1. 
2. 

_Should NOT trigger (≥1 example):_

1. 

### Sign-off

- [ ] **Approved as-is**
- [ ] **Approved with modifications:** _[specify]_
- [ ] **Rejected:** _[reason]_

---

## FPE-AR-001: Arabic laughter idioms — 'dying of laughter' expressions; suppresses si_explicit. REQUIRES clinician approval before active=true.

**File:** `sage_poc/rules/data/safety/false_positive_exclusions.json`)  
**Language:** `ar`  
**Action:** `{"type": "crisis_suppress", "suppresses": ["si_explicit", "si_passive"]}`  
**Active:** `True`

### Patterns

- `اموت من الضحك`
- `بموت من الضحك`
- `يموت من الضحك`

### Clinical Rationale

_[To be completed by clinical team]_

### Trigger Examples

_Should trigger (≥2 examples):_

1. 
2. 

_Should NOT trigger (≥1 example):_

1. 

### Sign-off

- [ ] **Approved as-is**
- [ ] **Approved with modifications:** _[specify]_
- [ ] **Rejected:** _[reason]_

---

## FPE-AR-002: Gulf frustration supplication idioms — INACTIVE pending clinician review. Candidate patterns: 'الله ياخذني من هالدنيا', 'يا الله خلصنا'. Must be reviewed by native Khaleeji clinician before activation.

**File:** `sage_poc/rules/data/safety/false_positive_exclusions.json`)  
**Language:** `ar`  
**Action:** `{"type": "crisis_suppress", "suppresses": ["si_passive"]}`  
**Active:** `False`

### Patterns

- `الله ياخذني من هالدنيا`
- `يا الله خلصنا`
- `الله يرحمني يا ناس`

### Clinical Rationale

_[To be completed by clinical team]_

### Trigger Examples

_Should trigger (≥2 examples):_

1. 
2. 

_Should NOT trigger (≥1 example):_

1. 

### Sign-off

- [ ] **Approved as-is**
- [ ] **Approved with modifications:** _[specify]_
- [ ] **Rejected:** _[reason]_

---

## SK-EN-002: English passive SI and veiled ideation

**File:** `sage_poc/rules/data/safety/passive_si_patterns.json`)  
**Language:** `en`  
**Action:** `{"type": "crisis_flag", "flag_id": "si_passive"}`  
**Active:** `True`

### Patterns

- `nothing matters anymore`
- `better off without me`
- `everyone would be better off`
- `no point in living`
- `wish i could disappear`
- `no reason to live`
- `i'm a burden`
- `there's no point in living`
- `i have no reason to live`
- `i wish i could disappear`
- `wish i were dead`
- `wish i was dead`
- `wish to be dead`
- `want to go to sleep and not wake up`
- `wish i could fall asleep and not wake up`
- `life is not worth living`
- `nothing will ever get better`
- `there's no way out`
- `i make everything worse`
- `they'd be happier without me`
- `i just want it to stop`
- `i don't care about anything anymore`
- `stopped caring what happens to me`
- `i have no future`
- `nothing brings me joy anymore`
- `i've given up on everything`
- `what is the point of anything`
- `can't see a future for myself`

### Clinical Rationale

Patterns sourced from C-SSRS hopelessness, burden, and anhedonia subscales. These expressions represent veiled suicidal ideation that does not use explicit death language — exactly the register most likely to be missed in production. The set is intentionally broad to maximise recall in a mental health support context, where a missed detection is a more serious failure than a false positive that the LLM resolves conversationally.

**Known sensitivity trade-off (see Accepted Sensitivity Decisions section):** Four patterns (`i just want it to stop`, `i make everything worse`, `there's no way out`, `i have no future`) will occasionally match benign speech in non-crisis contexts. Clinical team has reviewed this trade-off; see sign-off below.

### Trigger Examples

_Should trigger (≥2 examples):_

1. "I've just given up on everything — I don't see the point anymore."
2. "They'd honestly be better off without me around. I make everything worse."

_Should NOT trigger (≥1 example):_

1. "I killed it in that presentation." _(figurative — correctly excluded by negation and keyword-tier checks)_

### Sign-off

- [ ] **Approved as-is** — _including accepted sensitivity trade-off for the 4 edge-case patterns (see Accepted Sensitivity Decisions section)_
- [ ] **Approved with modifications:** _[specify]_
- [ ] **Rejected:** _[reason]_

### SK-EN-002 v1.2.0 — New patterns pending clinical sign-off

**Status:** `approved_by: null` — DO NOT merge until clinical lead has reviewed and signed off.

**Added 2026-06-04 (F-S05-001A fix):** 11 new keyword patterns added to the existing 76 patterns in SK-EN-002.

#### MISS-1 construction: dispensability ideation

| Pattern | Catches | Known FP risk |
|---------|---------|---------------|
| `"do better without me"` | "they'd do better without me in it" | "I need to do better without me getting in my own way" — OVER-TRIGGERS (si_passive fires). See documented over-trigger test. |

#### MISS-2 construction: relief-at-absence ideation

| Pattern | Catches |
|---------|---------|
| `"relieved if i were gone"` | "my loved ones would be relieved if I were gone" |
| `"relieved if i was gone"` | past indicative variant |
| `"relieved if i'm gone"` | present tense variant |
| `"relieved if i died"` | explicit death reference |
| `"relieved if i disappeared"` | disappearance variant — **OVER-TRIGGERS** on "she said she'd be relieved if I disappeared from her social media" (third-party subject). See documented over-trigger test. |
| `"relieved if i was dead"` | past state variant |
| `"relieved if i were dead"` | subjunctive state variant |
| `"relieved when i'm gone"` | temporal future framing |
| `"relieved when i die"` | temporal explicit |
| `"relieved when i'm dead"` | temporal dead-state framing |

#### Clinical decisions required

- [ ] **Accept "do better without me" over-trigger:** The phrase "I need to do better without me getting in my own way" fires `si_passive`. In this mental health context, is routing this to crisis_response acceptable? If not, narrow the pattern (e.g., to "they do better without me"). _[Reviewer name, Date]_

- [ ] **Accept "relieved if i disappeared" over-trigger:** The phrase "she said she'd be relieved if I disappeared from her social media" fires `si_passive` (third-party subject). Is this acceptable for POC? _[Reviewer name, Date]_

- [ ] **Clinical lead sign-off on all 11 v1.2.0 patterns:** Patterns are medically appropriate passive-SI constructions and acceptable for routing to crisis_response. _[Reviewer name, Date]_

---

## SK-AR-002: Arabic passive SI and escape ideation (Gulf dialect, alef-normalized)

**File:** `sage_poc/rules/data/safety/passive_si_patterns.json`)  
**Language:** `ar`  
**Action:** `{"type": "crisis_flag", "flag_id": "si_passive"}`  
**Active:** `True`

### Patterns

- `ياريت انام ولا اصحى`
- `نفسي تعبت`
- `ما اقدر اكمل`
- `ما عندي سبب اعيش`
- `مافي فايدة`
- `ما في فايدة من اي شي`
- `حياتي خلصت`
- `الحياة ما تسوى`
- `ما عاد قادر`
- `الحياة ما لها معنى`
- `وش الفايدة من الحياة`
- `انا عبء على الكل`
- `ودي اختفي من الدنيا`
- `ما في مستقبل لي`
- `الحياة ما تستاهل`
- `ما شايف فايدة`
- `روحي تعبت`

### Clinical Rationale

_[To be completed by clinical team]_

### Trigger Examples

_Should trigger (≥2 examples):_

1. 
2. 

_Should NOT trigger (≥1 example):_

1. 

### Sign-off

- [ ] **Approved as-is**
- [ ] **Approved with modifications:** _[specify]_
- [ ] **Rejected:** _[reason]_

---

## SK-AZ-002: Arabizi passive SI — Gulf Arabic transliterated despair and hopelessness expressions

**File:** `sage_poc/rules/data/safety/passive_si_patterns.json`)  
**Language:** `en`  
**Action:** `{"type": "crisis_flag", "flag_id": "si_passive"}`  
**Active:** `True`

### Patterns

- `ma7ad y7tajni`
- `kolhum a7san bdooni`
- `ma fee amal`
- `ma fi amal`
- `ta3abt mn nafsy`
- `hayati khalsa`
- `hayati 5alsa`
- `ma7ad ra7 yef2adni`
- `mafi fayda`

### Clinical Rationale

_[To be completed by clinical team]_

### Trigger Examples

_Should trigger (≥2 examples):_

1. 
2. 

_Should NOT trigger (≥1 example):_

1. 

### Sign-off

- [ ] **Approved as-is**
- [ ] **Approved with modifications:** _[specify]_
- [ ] **Rejected:** _[reason]_

---

## SK-AR-003: Gulf Arabic emotional exhaustion idioms — straddle passive SI, flag as si_passive not si_explicit

**File:** `sage_poc/rules/data/safety/passive_si_patterns.json`)  
**Language:** `ar`  
**Action:** `{"type": "crisis_flag", "flag_id": "si_passive"}`  
**Active:** `True`

### Patterns

- `روحي طايرة`
- `قلبي ميت`
- `انا تعبت من كل شي`
- `ما عاد في قلبي حياة`
- `نفسي مريضة`
- `روحي ما تحتمل`
- `انكسرت من الداخل`
- `ما في شي يسعدني`

### Clinical Rationale

_[To be completed by clinical team]_

### Trigger Examples

_Should trigger (≥2 examples):_

1. 
2. 

_Should NOT trigger (≥1 example):_

1. 

### Sign-off

- [ ] **Approved as-is**
- [ ] **Approved with modifications:** _[specify]_
- [ ] **Rejected:** _[reason]_

---

## IR-001: Intent route crisis override in post-crisis monitoring state

**Date logged:** 2026-05-22  
**Status:** Pending clinical sign-off — DO NOT IMPLEMENT until approved  
**Logged by:** Engineering (post-crisis state management integration)  
**Relevant nodes:** Node 1 (safety_check), Node 2 (intent_route), Node 4 (skill_select)  
**Relevant spec sections:** v7 §4 (Node 2 definition), v7 §5.3 (post-crisis monitoring)

---

### Finding

During end-to-end verification of the post-crisis state management implementation (2026-05-22), the following routing trace was observed:

**Session:**
- Turn 1: `"I feel like I want to hurt myself"` → `safety_check → crisis_response`, `crisis_state` set to `monitoring`
- Turn 2: `"nothing has changed, still the same"` (sent with `crisis_state: monitoring`)

**Observed routing for Turn 2:**
```
safety_check → intent_route → crisis_response
```
**Node path:** `["safety_check", "intent_route", "crisis_response"]`

**Expected routing for Turn 2:**
```
safety_check → intent_route → skill_select → skill_executor (post_crisis_check_in)
```

**What happened:**

Node 1 (`safety_check`) evaluated `"nothing has changed, still the same"` against S1–S6 crisis rules. No keywords matched. S7 ran because `crisis_state == "monitoring"` and classified the message as `STILL_DISTRESSED` via keyword match. `safety_check_node` returned `is_safe: True`, passing the message to `intent_route`.

Node 2 (`intent_route`) classified the message as `intent: crisis`. The LLM read the conversation history — which included the prior crisis turn — and inferred continued risk from context. `_route_after_intent` routed to `crisis_response` before reaching the monitoring-state guard:

```python
if intent == "crisis":                           # fires here
    return "crisis"
# ...
if state.get("crisis_state") == "monitoring":    # never reached
    return "skill_select"
```

The user received a second crisis response instead of the `post_crisis_check_in` skill the monitoring layer was designed to deliver.

---

### The architectural conflict

Per v7 §4, Node 2's crisis classification is described as a "redundant safety net" for messages that pass Node 1. The Task B fix earlier in this sprint narrowed intent_route's crisis definition to "explicit harm language only — safety_check already ran before this node and is the authoritative crisis detector."

`"Nothing has changed, still the same"` contains no explicit harm language. Node 1 evaluated it and passed it as safe. S7 evaluated it in post-crisis context and classified it `STILL_DISTRESSED` — correctly, by design. Node 2 overrode both decisions by reading conversational context and inferring ongoing risk. This violates architectural precedence: intent_route should not re-escalate what safety_check has already classified as safe in a monitoring context.

---

### The clinical question

**Should a user who expressed suicidal ideation on Turn 1 and says "nothing has changed, still the same" on Turn 2 receive:**

**Option A — Conservative (re-escalate):** A second crisis response with crisis line numbers and "you are not alone" framing.

**Option B — Sophisticated (hold in check-in flow):** The `post_crisis_check_in` skill, which validates current state, asks directly about safety, and can re-escalate if the user expresses new explicit harm language.

Engineering recommendation is Option B:

1. `post_crisis_check_in` exists precisely for this moment. Bypassing it with a repeat crisis response breaks the therapeutic continuity the skill is designed to provide.
2. A repeat crisis response for "nothing has changed" — with no new harm language — may feel scripted to a user in a fragile state.
3. Option B is not clinically unsafe provided the check-in skill's escalation_matrix covers new harm language (see open question below).
4. S7 classified this correctly as `STILL_DISTRESSED`. The architecture should honour that classification.

**This is a clinical safety decision. Clinical sign-off is required before any change is made.**

---

### Genuine re-escalation case (unaffected by any fix)

`"I still want to die, nothing has changed"` with `crisis_state: monitoring` — Node 1 matches `want to die` via `si_explicit`, sets `is_safe: False`, and `_route_after_safety` sends directly to `crisis_response` before intent_route runs. This path is unaffected by any change to intent_route's monitoring-state behaviour.

---

### Proposed implementation (pending clinical approval)

If Option B is approved: add one guidance line to `INTENT_SYSTEM` in `intent_route.py` and pass `crisis_state` into the prompt context:

> "When crisis_state is 'monitoring', the user is in post-crisis follow-up. Do NOT classify as crisis unless the message contains NEW explicit harm language (suicidal intent, self-harm intent, plans to hurt others). Continued distress, hopelessness, or statements like 'nothing has changed' are expected in post-crisis follow-up and should be classified as skill_continuation, not crisis."

**Tests to add after implementation:**

| Message | crisis_state | Expected intent | Rationale |
|---|---|---|---|
| `"nothing has changed, still the same"` | `monitoring` | `skill_continuation` | STILL_DISTRESSED — monitoring flow absorbs it |
| `"I still want to die, nothing has changed"` | `monitoring` | `crisis` (via safety_check, not intent_route) | Explicit harm language — Node 1 catches it before intent_route |
| `"nothing has changed"` | `none` | unconstrained | Standard flow — monitoring guard inactive |

---

### Open question for clinical reviewer — RESOLVED (2026-05-22)

**Confirmed at the JSON level:** `post_crisis_check_in.json` already contains the required escalation entry:

```json
"escalation_matrix": {
  "L3": "Exit immediately to crisis protocol if any new crisis signal"
}
```

The engineering prerequisite for Option B is satisfied. The skill can re-escalate from within the check-in flow if the user expresses new explicit harm language. No additional skill changes are required before Option B can be approved.

**The clinical reviewer's decision is now a single question:** should `intent_route` respect `crisis_state == "monitoring"` and defer to S7's classification, or should it retain the right to re-escalate independently? There is no open engineering dependency on either answer.

---

### Sign-off

- [ ] **Option A — re-escalate on continued distress in monitoring state** — intent_route retains current behaviour — _[Reviewer name, Date]_
- [ ] **Option B — hold in check-in flow** — implement INTENT_SYSTEM guidance line — _[Reviewer name, Date]_
- [ ] **Neither — alternative approach:** _[specify]_

---
