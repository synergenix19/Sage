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
