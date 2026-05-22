# Sage — Clinician Review Package

**Prepared for:** Gulf-native clinical reviewer  
**Date:** 2026-05-22  
**Prepared by:** Sage technical team  
**Action required by:** Clinical reviewer prior to deployment

---

## How to Use This Document

This document requires your clinical judgement on two sets of questions. No technical knowledge is required.

**Section A** covers phrases that Sage might flag as self-harm signals. It is split into three parts:

- **Part 1 (A1)** presents two categories of phrases we have already stopped flagging because they are unambiguous idioms — "dying of laughter," for example. We are asking you to confirm these decisions or flag any disagreement.
- **Part 2 (A2)** presents two categories where the phrases are genuinely ambiguous — the same words can be idiomatic in one context and a real distress signal in another. These are still flagged. We need your clinical judgement on what to do with them.
- **Part 3 (A3)** presents Gulf Arabic metaphorical despair expressions that vary significantly in clinical weight, and asks you to classify each as crisis-grade, clinical-flag-only, or remove.

**Section B** asks you to review notes that guide how Sage talks with Gulf users about culturally sensitive topics: sleep during Ramadan, shame after a mental health crisis, and similar matters. We need you to confirm whether the guidance is clinically sound or whether it needs adjustment.

For each item, your options are shown. Please add your name or initials and a brief note where you have concerns.

---

---

# SECTION A — Phrase Suppression Review

## Background

When Sage detects certain words or phrases in a message, it treats the message as a potential self-harm signal and pauses the conversation to check in with the user. This is the correct response for genuine distress signals.

The problem is that some ordinary, non-distressed phrases happen to contain words like "dying," "kill," or "dead." Flagging these as crisis signals means Sage interrupts a normal conversation with a crisis check-in — which is clinically counterproductive. It breaks rapport, signals that Sage does not understand basic language, and — importantly — teaches the user to dismiss future crisis check-ins as false alarms. Alarm fatigue in a clinical system is a real safety risk.

We have identified four categories of phrases in this situation. We have handled them in two different ways, described below.

---

## A1 — Already Activated: Please Confirm

The following two categories have been **activated** by the Sage team. Sage will no longer flag these phrases as crisis signals.

We made this decision because these are structurally unambiguous idioms — there is no clinical context in which they constitute a genuine distress signal. Every Arabic speaker recognises "اموت من الضحك" as a laughter expression, not a suicidal statement. The same applies to the English equivalents.

**We are asking you to confirm you agree, or to flag any phrase you believe should remain active.**

If you believe any specific phrase on either list should still be flagged, cross it out and note why. We will reactivate only the phrases you flag.

---

## FPE-AR-001 — Arabic "dying of laughter" expressions

**Language:** Arabic (Gulf dialect)  
**Status: ACTIVE — Sage does not flag these phrases**

| Phrase (Arabic) | Meaning in ordinary use |
|---|---|
| اموت من الضحك | I'm dying of laughter |
| بموت من الضحك | I'm going to die laughing |
| يموت من الضحك | He/she is dying of laughter |

---

**REVIEWER CONFIRMATION — FPE-AR-001**

- [ ] **CONFIRMED** — I agree these should not be flagged as crisis signals  
- [ ] **PARTIAL CONCERN** — Please reactivate the phrase(s) I have crossed out above  
- [ ] **REACTIVATE ALL** — I believe these should still be flagged

**Reviewer name/initials:** _______________  
**Notes:**  
&nbsp;  
&nbsp;  
&nbsp;

---

## FPE-EN-001 — English hyperbolic idioms

**Language:** English  
**Status: ACTIVE — Sage does not flag these phrases**

| Phrase | Meaning in ordinary use |
|---|---|
| dying of laughter | finding something very funny |
| dying to try / see / meet / go | very eager to do something |
| kill for a [coffee] | would really love something |
| killing it | performing very well |
| killing me softly | affecting me emotionally (often used of music) |
| dead tired | very tired |
| dead on my feet | extremely fatigued |
| i'm dead / literally dead | informal: something is very funny |
| i could kill for [something] | I really want something |
| this is killing me with laughter | finding something very funny |
| my heart is killing me from laughter | laughing very hard |

---

**REVIEWER CONFIRMATION — FPE-EN-001**

- [ ] **CONFIRMED** — I agree these should not be flagged as crisis signals  
- [ ] **PARTIAL CONCERN** — Please reactivate the phrase(s) I have crossed out above  
- [ ] **REACTIVATE ALL** — I believe these should still be flagged

**Reviewer name/initials:** _______________  
**Notes:**  
&nbsp;  
&nbsp;  
&nbsp;

---

## A2 — Needs Your Clinical Judgment

The following two categories are **still active** — Sage flags them as crisis signals today, and will continue to do so until you make a decision. We kept these active because, unlike the phrases above, these can carry genuine clinical meaning in some contexts.

**We are asking you to decide whether any or all of these phrases are safe to stop flagging.**

Your options for each category are: approve all, reject all, or specify which individual phrases to remove. You can also set a condition ("approve only outside of contexts involving work stress").

---

## FPE-AR-002 — Gulf frustration and supplication expressions

**Language:** Arabic (Gulf dialect)  
**Status: ACTIVE — Sage flags these phrases as passive self-harm signals**

**Phrases in question:**

| Phrase (Arabic) | Meaning in ordinary use |
|---|---|
| الله ياخذني من هالدنيا | God, take me from this world (expression of exhaustion/frustration) |
| يا الله خلصنا | God, relieve us / God, get us out of this |
| الله يرحمني يا ناس | God have mercy on me, people (expression of exasperation) |

**Why we kept these active:**  
"الله ياخذني من هالدنيا" is genuinely ambiguous. The same phrase, in the same dialect, by the same demographic, can be an ordinary frustration expression or a passive wish for death — depending on tone, context, and the user's mental state. This is a clinical judgment call, not a linguistic one.

**Clinical questions for your decision:**

1. Is it appropriate to stop flagging these phrases in a mental health app context, given that Sage has access to the current conversation and session mood as context?
2. Are there specific phrases in this list that carry more clinical risk than others — for example, should "الله ياخذني من هالدنيا" remain active even if "يا الله خلصنا" is approved?

---

**REVIEWER DECISION — FPE-AR-002**

- [ ] **APPROVE** — These are safe to exclude from crisis detection  
- [ ] **REJECT** — Sage should continue flagging these  
- [ ] **MODIFY** — Remove only the phrases I have crossed out above  
- [ ] **CONDITIONAL APPROVE** — Approve only in contexts where: _______________

**Reviewer name/initials:** _______________  
**Notes:**  
&nbsp;  
&nbsp;  
&nbsp;

---

## FPE-EN-001 — English hyperbolic idioms

**Language:** English

**Phrases in question:**

| Phrase | Meaning in ordinary use |
|---|---|
| dying of laughter | finding something very funny |
| dying to try / see / meet / go | very eager to do something |
| kill for a [coffee] | would really love something |
| killing it | performing very well |
| killing me softly | affecting me emotionally (often used of music) |
| dead tired | very tired |
| dead on my feet | extremely fatigued |
| i'm dead / literally dead | informal: something is very funny |
| i could kill for [something] | I really want something |
| this is killing me with laughter | finding something very funny |
| my heart is killing me from laughter | laughing very hard |

**What Sage currently does with these phrases:**  
Treats them as possible direct or passive self-harm signals, triggering a crisis check-in.

**What approving this change would do:**  
Sage recognises these as English hyperbolic idioms and responds normally.

**Clinical concern to address:**  
Is there any phrase on this list that could, in your clinical experience, be used by a genuinely distressed person in a way that warrants keeping it as an active signal?

---

**REVIEWER DECISION — FPE-EN-001**

- [ ] **APPROVE** — These are safe to exclude from crisis detection  
- [ ] **REJECT** — Sage should continue flagging these  
- [ ] **MODIFY** — Remove only the phrases I have crossed out above

**Reviewer name/initials:** _______________  
**Notes:**  
&nbsp;  
&nbsp;  
&nbsp;

---

## FPE-EN-002 — English work and boredom expressions

**Language:** English  
**Status: ACTIVE — Sage flags these phrases as passive self-harm signals**

**Phrases in question:**

| Phrase | Meaning in ordinary use |
|---|---|
| work is killing me | work is very stressful or demanding |
| this job is killing me | same as above |
| this place is killing me | this environment is very difficult |
| bored to death | extremely bored |
| bored out of my mind | extremely bored |
| i'm dying here | this is very dull or very difficult |
| dying of boredom | extremely bored |
| scared to death | very frightened |
| tickled to death | very pleased |
| worried to death | very anxious about something |
| talked to death | something has been discussed too much |

**Why we kept these active:**  
This list is more clinically ambiguous than the English idioms in A1. "Work is killing me" and "this job is killing me" can sometimes reflect genuine occupational overwhelm or burnout distress — particularly in a mental health app where users come specifically because something is wrong. "Scared to death" and "worried to death" express real anxiety even if the phrasing is idiomatic. In a clinical conversation, these phrases carry more signal than in casual chat.

**A specific note:**  
Some of these ("tickled to death," "talked to death") carry no clinical ambiguity at all and could be individually approved even if the rest remain active. You may find it useful to go phrase by phrase rather than approving the whole category.

---

**REVIEWER DECISION — FPE-EN-002**

- [ ] **APPROVE** — These are safe to exclude from crisis detection  
- [ ] **REJECT** — Sage should continue flagging these  
- [ ] **MODIFY** — Remove only the phrases I have crossed out above  
- [ ] **CONDITIONAL APPROVE** — Approve, but only outside of contexts involving: _______________

**Reviewer name/initials:** _______________  
**Notes:**  
&nbsp;  
&nbsp;  
&nbsp;

---

# SECTION A3 — SK-AR-003: Gulf Arabic Metaphorical Despair — Crisis Grade vs. Clinical Flag

## Background

Sage currently flags 8 Gulf Arabic metaphorical expressions as passive suicidal ideation (rule SK-AR-003), treating all of them as crisis signals. A technical review has identified that these phrases vary significantly in their specificity and clinical weight. Two have been assessed as unambiguously crisis-grade and are already tested. The remaining six are genuinely ambiguous — they can represent profound despair or common fatigue depending on context, and applying the crisis protocol to all of them risks the alarm-fatigue problem described in Section A of this package.

We need your clinical guidance on how to handle each phrase.

**Your options for each phrase:**
- **CRISIS** — This phrase should trigger the full crisis protocol (user gets hotline numbers, session pauses). Keep in SK-AR-003.
- **FLAG** — This phrase should set a clinical flag for follow-up but not trigger the crisis protocol. We will move it to a new clinical-flag rule.
- **REMOVE** — This phrase is too common or too ambiguous to flag at all. We will remove it from crisis and flag rules.

---

## A3-01 — "انا تعبت من كل شي"

**Literal translation:** "I am exhausted/tired of everything"

**Technical assessment:** This is one of the most common expressions of overwhelm in Gulf Arabic. It is used by people describing a stressful day at work, a difficult week, or general life fatigue. It is also used in contexts of genuine despair. The technical team assesses this as **flag-grade, not crisis-grade** — triggering the full crisis protocol for this phrase would produce frequent false positives that undermine user trust.

**Questions for the reviewer:**
1. Is "انا تعبت من كل شي" in isolation sufficient to trigger a crisis response, or does it require additional context signals (e.g. previous passive SI statements, high distress score)?
2. If flag-grade: what is the appropriate clinical follow-up — a gentle check-in the same turn, a clinician note for the next session, or something else?

**REVIEWER DECISION — A3-01:**
- [ ] **CRISIS** — Keep as crisis-grade in SK-AR-003
- [ ] **FLAG** — Move to clinical flag; specify follow-up: _______________
- [ ] **REMOVE** — Too ambiguous to flag

**Reviewer name/initials:** _______________ **Notes:** &nbsp;

---

## A3-02 — "روحي طايرة"

**Literal translation:** "My soul is floating/flying away"

**Technical assessment:** This phrase is used in Gulf Arabic to describe dissociation, spiritual distress, or feeling unmoored. It can be figurative (said during an overwhelming moment) or a genuine signal of severe dissociative distress. Technical assessment: **flag-grade candidate**, pending clinical guidance.

**REVIEWER DECISION — A3-02:**
- [ ] **CRISIS** — Keep as crisis-grade in SK-AR-003
- [ ] **FLAG** — Move to clinical flag
- [ ] **REMOVE** — Too ambiguous to flag

**Reviewer name/initials:** _______________ **Notes:** &nbsp;

---

## A3-03 — "قلبي ميت"

**Literal translation:** "My heart is dead"

**Technical assessment:** Used to describe profound emotional numbness, grief, or disconnection. Also used figuratively after disappointment (similar to "heartbroken" in English). Technical assessment: **flag-grade candidate**, but the phrase's specificity makes it a stronger signal than "انا تعبت من كل شي."

**REVIEWER DECISION — A3-03:**
- [ ] **CRISIS** — Keep as crisis-grade in SK-AR-003
- [ ] **FLAG** — Move to clinical flag
- [ ] **REMOVE** — Too ambiguous to flag

**Reviewer name/initials:** _______________ **Notes:** &nbsp;

---

## A3-04 — "نفسي مريضة"

**Literal translation:** "My soul/self is sick"

**Technical assessment:** Highly ambiguous. Can mean spiritually unwell, emotionally exhausted, or literally physically ill depending on dialect and context. Gulf Arabic uses "نفس" for both soul and self. Technical assessment: **remove or flag-grade only** — this phrase does not reliably distinguish distress from ordinary illness.

**REVIEWER DECISION — A3-04:**
- [ ] **CRISIS** — Keep as crisis-grade in SK-AR-003
- [ ] **FLAG** — Move to clinical flag
- [ ] **REMOVE** — Too ambiguous to flag

**Reviewer name/initials:** _______________ **Notes:** &nbsp;

---

## A3-05 — "انكسرت من الداخل"

**Literal translation:** "I'm broken inside"

**Technical assessment:** Commonly used after significant loss, betrayal, or trauma. Carries significant distress weight but is also used figuratively after disappointment. Technical assessment: **flag-grade candidate** — the phrase signals significant emotional pain but is not specific enough to trigger the full crisis protocol without additional context.

**REVIEWER DECISION — A3-05:**
- [ ] **CRISIS** — Keep as crisis-grade in SK-AR-003
- [ ] **FLAG** — Move to clinical flag
- [ ] **REMOVE** — Too ambiguous to flag

**Reviewer name/initials:** _______________ **Notes:** &nbsp;

---

## A3-06 — "ما في شي يسعدني"

**Literal translation:** "Nothing makes me happy anymore"

**Technical assessment:** Classic anhedonia expression. Clinically significant as a depression indicator but not passive SI on its own. Technical assessment: **flag-grade** — this is a clinical flag for follow-up, not a crisis trigger. The v7 architecture's intent is that Layer 1 catches explicit crisis signals; anhedonia belongs in the clinical flag tier.

**REVIEWER DECISION — A3-06:**
- [ ] **CRISIS** — Keep as crisis-grade in SK-AR-003
- [ ] **FLAG** — Move to clinical flag
- [ ] **REMOVE** — Too ambiguous to flag

**Reviewer name/initials:** _______________ **Notes:** &nbsp;

---

**After completing A3:** Please return with your decisions. The technical team will:
1. Keep CRISIS decisions in SK-AR-003 unchanged
2. Move FLAG decisions to a new rule SK-AR-004 with `clinical_flag` action instead of `crisis_flag`
3. Remove REMOVE decisions from all rules
4. Add graph-level tests for each decision

**If any phrase raises a concern not captured above, add a note and request a call. These decisions have direct patient safety implications.**

---

# SECTION B — Cultural Guidance Review

## What is this?

Sage uses cultural guidance notes to adapt its responses for Gulf users. These notes direct how the system handles culturally specific situations — for example, how to talk about sleep during Ramadan, or how to respond when a user expresses shame after a mental health crisis.

Each note was drafted by the Sage team with reference to Gulf cultural context, but none has been reviewed by a Gulf-native clinician. We are asking you to confirm that each note is clinically accurate and appropriate before Sage goes live.

**If you approve:** The guidance is used as written.  
**If you revise:** Please write the corrected version in the space provided. We will update the system exactly as you specify.

---

## CG-01 — Sleep guidance during Ramadan

**Applies to:** Sage's sleep support conversations  
**When this guidance is used:** When a user mentions Ramadan during a sleep-related conversation

**The guidance Sage currently follows:**

> During Ramadan, sleep timing shifts to a culturally normal polyphasic pattern — late sleep after Tarawih prayers, waking before Fajr for Suhoor, then returning to sleep. This is not a disorder. Standard advice about fixed wake times or nocturnal sleep windows does not apply during Ramadan without modification. If the user mentions Ramadan, acknowledge the context explicitly and adapt advice to the Ramadan schedule rather than correcting it.

**Questions for the reviewer:**

1. Is this an accurate description of the Ramadan sleep pattern as you observe it clinically?  
2. Is there any nuance missing — for example, how to handle a user who is struggling with Ramadan sleep beyond what is culturally normal?  
3. Does the instruction to "adapt advice to the Ramadan schedule rather than correcting it" reflect the right clinical stance, or should Sage still be able to raise concerns about sleep health within a Ramadan context?

---

**REVIEWER DECISION — CG-01**

- [ ] **APPROVE** — Guidance is accurate and appropriate as written  
- [ ] **REVISE** — Please use my revised version below

**Revised guidance (if applicable):**  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;

**Reviewer name/initials:** _______________

---

## CG-02 — Qahwa (Arabic coffee) and caffeine advice

**Applies to:** Sage's sleep support conversations  
**When this guidance is used:** When Sage advises about caffeine as part of a sleep conversation

**The guidance Sage currently follows:**

> Arabic coffee (qahwa, cardamom-spiced) is a ceremonial and social drink consumed throughout the day and evening in Gulf households. Caffeine advice must name qahwa specifically, not just "coffee," and must be framed as a practical option rather than a prohibition. Qahwa has deep cultural significance and a blunt "stop drinking coffee" instruction is culturally tone-deaf.

**Questions for the reviewer:**

1. Is this framing of qahwa's cultural significance accurate?  
2. Is the instruction to avoid a "stop drinking coffee" framing clinically appropriate, or are there cases where a firmer caffeine reduction recommendation would be warranted even with qahwa?  
3. Should the guidance also name other common Gulf caffeine sources (Karak chai, energy drinks) or is qahwa the primary focus?

---

**REVIEWER DECISION — CG-02**

- [ ] **APPROVE** — Guidance is accurate and appropriate as written  
- [ ] **REVISE** — Please use my revised version below

**Revised guidance (if applicable):**  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;

**Reviewer name/initials:** _______________

---

## CG-03 — Shared sleeping environments

**Applies to:** Sage's sleep support conversations  
**When this guidance is used:** When giving practical sleep advice that assumes environmental control

**The guidance Sage currently follows:**

> Extended-family households are common. Users may share a bedroom with a spouse, child, parent, or sibling and have no independent control over light, noise, or temperature. Advice assuming a private sleep environment must be adapted to shared-room realities. Do not suggest changes the user structurally cannot make.

**Questions for the reviewer:**

1. Does this accurately reflect the household realities of the Sage user population?  
2. Is there any additional guidance needed — for example, how to handle situations where sharing a sleep environment with a particular person is itself a source of distress?

---

**REVIEWER DECISION — CG-03**

- [ ] **APPROVE** — Guidance is accurate and appropriate as written  
- [ ] **REVISE** — Please use my revised version below

**Revised guidance (if applicable):**  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;

**Reviewer name/initials:** _______________

---

## CG-04 — Islamic framing after a mental health crisis

**Applies to:** Sage's post-crisis check-in conversations  
**When this guidance is used:** After a user has come through a crisis moment, during the check-in that follows

**The guidance Sage currently follows:**

> After a crisis, Islamic expression of relief is appropriate and meaningful. If the user says "الحمد لله على السلامة" (praise be to Allah for your safety) or uses similar language, mirror it warmly rather than treating it as avoidance. "إن شاء الله" in the context of "I will be okay, inshallah" is not denial — it is trust in God's plan while accepting the present. Spiritual language is a genuine coping resource in this cultural context. Do not redirect away from it.

**Questions for the reviewer:**

1. Is the instruction to "mirror" Islamic expressions of relief clinically appropriate, or does it risk Sage appearing to make religious statements it has no basis to make?  
2. Is the characterisation of "inshallah" in a post-crisis context accurate — particularly the distinction between inshallah as denial versus inshallah as genuine trust?  
3. Are there Islamic expressions that should prompt clinical concern rather than warm mirroring — for example, if a user expresses that the crisis was "God's will" in a way that suggests fatalistic resignation rather than acceptance?

---

**REVIEWER DECISION — CG-04**

- [ ] **APPROVE** — Guidance is accurate and appropriate as written  
- [ ] **REVISE** — Please use my revised version below

**Revised guidance (if applicable):**  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;

**Reviewer name/initials:** _______________

---

## CG-05 — Shame and help-seeking after a crisis

**Applies to:** Sage's post-crisis check-in conversations  
**When this guidance is used:** When a user appears to be minimising or withdrawing after a crisis

**The guidance Sage currently follows:**

> In Gulf culture, mental health crises may carry significant shame, particularly for male users and in contexts involving family honour. Post-crisis, a user may feel ashamed that they reached a crisis point at all or that they sought help. The check-in should actively counter this: acknowledge courage explicitly, frame reaching out as strength not weakness, and do not treat the check-in as a clinical debrief — treat it as one person genuinely caring about another.

**Questions for the reviewer:**

1. Is the characterisation of shame around mental health help-seeking accurate for the Sage user population?  
2. Is the instruction to "acknowledge courage explicitly" the right approach, or could this land as patronising for some users?  
3. Is there a risk that framing "reaching out as strength" conflicts with how some male Gulf users understand strength — and if so, how should Sage navigate this?

---

**REVIEWER DECISION — CG-05**

- [ ] **APPROVE** — Guidance is accurate and appropriate as written  
- [ ] **REVISE** — Please use my revised version below

**Revised guidance (if applicable):**  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;

**Reviewer name/initials:** _______________

---

## CG-06 — Mood self-rating shame

**Applies to:** Sage's mood check-in conversations  
**When this guidance is used:** When asking a user to rate their mood on a 1–10 scale

**The guidance Sage currently follows:**

> Assigning a number to one's emotional state may feel uncomfortable or invasive for Gulf users for whom emotional disclosure is culturally private, particularly for male users. Framing the scale as a formal self-assessment or score may trigger shame or reluctance to report accurately. Preferred framing: use "how are you tracking" or "kif inta el youm, give me a number" rather than "rate your mood on a scale of 1 to 10." If the user resists the numerical format, accept qualitative responses ("not great," "better than yesterday," "hamdulillah okay") and estimate an approximate equivalent rather than pushing for a number. The data is for continuity, not clinical scoring — user comfort matters more than format compliance.

**Questions for the reviewer:**

1. Is the characterisation of emotional disclosure as culturally private for Gulf users accurate, and does it apply more broadly than just male users?  
2. Is "kif inta el youm" the right dialect framing, or is there a more natural Khaleeji phrasing?  
3. Is the instruction to "estimate an approximate equivalent" for qualitative responses (converting "hamdulillah okay" to a number) clinically acceptable, or does it introduce inaccuracy that matters for continuity tracking?

---

**REVIEWER DECISION — CG-06**

- [ ] **APPROVE** — Guidance is accurate and appropriate as written  
- [ ] **REVISE** — Please use my revised version below

**Revised guidance (if applicable):**  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;

**Reviewer name/initials:** _______________

---

## CG-07 — Family honour (ird/karama) in reactive situations

**Applies to:** Sage's STOP technique conversations (impulse and anger management)  
**When this guidance is used:** When a user is working on managing reactive behaviour in a family honour context

**The guidance Sage currently follows:**

> Reactive behaviour including verbal outbursts or impulsive actions may occur in the context of family honour (ird, karama) — situations involving perceived slights to family reputation, a relative's behaviour, or perceived public shame. These situations carry real social and relational weight and are not comparable to ordinary frustration. When the STOP technique is delivered in a family honour context, the pause-and-choose framing is clinically appropriate, but the instruction must acknowledge the real pressure the user is experiencing, not minimise it. Do not frame the impulse as irrational — acknowledge that the situation is genuinely difficult, and then invite reflection on what action would best serve the user's own values.

**Questions for the reviewer:**

1. Is this characterisation of ird and karama accurate for the clinical population Sage will serve?  
2. Is the instruction to "not frame the impulse as irrational" the right clinical stance, or does it risk validating genuinely harmful reactive patterns?  
3. Are there example scenarios or phrasings you would recommend for this guidance that the technical team could use to improve the STOP technique examples?

---

**REVIEWER DECISION — CG-07**

- [ ] **APPROVE** — Guidance is accurate and appropriate as written  
- [ ] **REVISE** — Please use my revised version below

**Revised guidance (if applicable):**  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;

**Reviewer name/initials:** _______________

---

## Return Instructions

When you have completed your review:

1. Save this document with your name added to the filename (e.g., `clinician_review_package_DrAlMansouri.md`).
2. For any REVISE decisions, please write the revised guidance text in the space provided. We will implement exactly what you write — we will not paraphrase.
3. Return the completed document to the Sage technical team at: synergenix.global@gmail.com

**If any item raises a concern that is not captured by the APPROVE / REJECT / REVISE options above, please add a note and flag it for a call.** The review decisions in Section A have direct patient safety implications, and we would rather pause deployment than proceed with uncertainty.

Thank you for your time on this review.
