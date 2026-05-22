# Sage — Clinician Review Package

**Prepared for:** Gulf-native clinical reviewer  
**Date:** 2026-05-22  
**Prepared by:** Sage technical team  
**Action required by:** Clinical reviewer prior to deployment

---

## How to Use This Document

This document requires your clinical judgement on two sets of questions. No technical knowledge is required.

**Section A** asks you to review phrases that Sage currently flags as possible self-harm signals. Some of these phrases are ordinary colloquial expressions — "dying of laughter," for example — that happen to use death or harm language. We need you to confirm whether it is safe to stop flagging them.

**Section B** asks you to review notes that guide how Sage talks with Gulf users about culturally sensitive topics: sleep during Ramadan, shame after a mental health crisis, and similar matters. We need you to confirm whether the guidance is clinically sound or whether it needs adjustment.

For each item, your options are shown. Please add your name or initials and a brief note where you have concerns.

---

---

# SECTION A — Phrase Suppression Review

## What is this?

When Sage detects certain words or phrases in a message, it treats the message as a potential self-harm signal and immediately pauses the conversation to check in with the user. This is the correct response for genuine distress signals.

The problem is that some ordinary, non-distressed phrases happen to contain words like "dying," "kill," or "dead" — and the system currently flags these as crisis signals. This means Sage would interrupt an ordinary conversation with a crisis check-in when none is needed.

We have identified four categories of these phrases. Each is currently **inactive** — meaning Sage still flags them as crisis signals today. We are asking you to review each category and tell us whether it is safe to stop flagging them.

**If you approve a category:** Sage will recognise these phrases as non-crisis and respond normally.  
**If you reject a category:** The phrase continues to trigger a crisis check-in.  
**If you want to modify:** You can cross out individual phrases, and we will remove only those.

---

## FPE-AR-001 — Arabic "dying of laughter" expressions

**Language:** Arabic (Gulf dialect)

**Phrases in question:**

| Phrase (Arabic) | Meaning in ordinary use |
|---|---|
| اموت من الضحك | I'm dying of laughter |
| بموت من الضحك | I'm going to die laughing |
| يموت من الضحك | He/she is dying of laughter |

**What Sage currently does with these phrases:**  
Treats them as a possible direct self-harm signal ("si_explicit") and a passive self-harm signal ("si_passive") — meaning the conversation is paused for a crisis check-in.

**What approving this change would do:**  
Sage recognises these as laughter idioms and does not trigger a crisis check-in.

**Clinical concern to address:**  
Is there any clinical context in which a Gulf user might use these phrases in genuine distress rather than as a laughter idiom? For example, could a user in a dissociative or manic state use this language non-idiomatically?

---

**REVIEWER DECISION — FPE-AR-001**

- [ ] **APPROVE** — These are safe to exclude from crisis detection  
- [ ] **REJECT** — Sage should continue flagging these  
- [ ] **MODIFY** — Remove only the phrases I have crossed out above

**Reviewer name/initials:** _______________  
**Notes:**  
&nbsp;  
&nbsp;  
&nbsp;

---

## FPE-AR-002 — Gulf frustration and supplication expressions

**Language:** Arabic (Gulf dialect)

**Phrases in question:**

| Phrase (Arabic) | Meaning in ordinary use |
|---|---|
| الله ياخذني من هالدنيا | God, take me from this world (expression of exhaustion/frustration) |
| يا الله خلصنا | God, relieve us / God, get us out of this |
| الله يرحمني يا ناس | God have mercy on me, people (expression of exasperation) |

**What Sage currently does with these phrases:**  
Treats them as a passive self-harm signal — meaning the conversation is paused for a check-in about whether the user is safe.

**What approving this change would do:**  
Sage recognises these as frustration and supplication idioms common in Gulf Arabic speech and does not trigger a check-in.

**Clinical concern to address:**  
These phrases are higher-stakes than the laughter idioms above. "الله ياخذني من هالدنيا" can be a genuine passive wish for death in a distressed person, even though it is also used as an ordinary frustration expression. We need your clinical judgement on two questions:

1. Given the conversational context Sage has available (the user's current session, their mood, the topic being discussed), is it appropriate to suppress this signal?  
2. Are there specific phrases in this list that carry more genuine clinical risk than others, and should remain active even if others are approved?

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

**What Sage currently does with these phrases:**  
Treats them as passive self-harm signals, triggering a safety check-in.

**What approving this change would do:**  
Sage recognises these as work-context or boredom idioms and responds normally.

**A specific concern for this category:**  
Some of these phrases — particularly "work is killing me" and "this job is killing me" — can sometimes reflect genuine occupational burnout distress, not just casual hyperbole. We have flagged this category as lower-confidence than FPE-EN-001. Your guidance on whether any of these phrases should remain active signals would be particularly valuable here.

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

---

## Return Instructions

When you have completed your review:

1. Save this document with your name added to the filename (e.g., `clinician_review_package_DrAlMansouri.md`).
2. For any REVISE decisions, please write the revised guidance text in the space provided. We will implement exactly what you write — we will not paraphrase.
3. Return the completed document to the Sage technical team at: synergenix.global@gmail.com

**If any item raises a concern that is not captured by the APPROVE / REJECT / REVISE options above, please add a note and flag it for a call.** The review decisions in Section A have direct patient safety implications, and we would rather pause deployment than proceed with uncertainty.

Thank you for your time on this review.
