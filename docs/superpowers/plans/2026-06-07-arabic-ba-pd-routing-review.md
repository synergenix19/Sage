# Arabic Phrase Routing Review — BA vs psychoed_depression

**Date:** 2026-06-07  
**Status:** AWAITING NATIVE-SPEAKER CLINICAL REVIEW  
**Reviewer required:** Native Khaleeji Arabic speaker with clinical background  
**Prepared by:** engineering (skill-routing audit)

---

## Context

As part of the BA/psychoed_depression Tier 1 keyword re-bucketing (commit cab4725, 2026-06-07), three Arabic phrases were held from the English change pending Arabic-specific review. The English equivalent phrases ("lost interest", "I can't be happy/enjoy anything", "my life feels empty/meaningless") were moved from `psychoed_depression` to `behavioral_activation` because they describe a behavioral withdrawal state that BA addresses directly — not an educational inquiry about depression that PD addresses.

The three Arabic phrases below are currently in `psychoed_depression.target_presentations`. The question for the reviewer is whether each phrase, as used by a Khaleeji Arabic speaker in a mental health context, signals:

**(A) Behavioral withdrawal needing activation scheduling** → move to `behavioral_activation`  
**(B) An educational inquiry about what depression is** → remain in `psychoed_depression`  
**(C) Ambiguous — could be either; requires routing based on full message context**

This is a clinical routing judgment. The reviewer's decision determines which therapeutic skill a vulnerable user enters when they use one of these phrases.

---

## Phrases for Review

### 1. فاقد الاهتمام

**Transliteration:** faaqid al-ihtimaam  
**Literal meaning:** "Lacking interest" / "having lost interest"  
**Usage context:** A user who says this is typically expressing that they have lost interest in things, not asking what loss of interest means or why it happens.

**Engineering assessment:** This reads as a symptom description (BA-intent), not an educational inquiry. It is the Khaleeji Arabic equivalent of "I've lost interest in things" — which is now in BA after the English change. However, confirm with native-speaker review: does this phrase in Gulf colloquial usage ever carry an educational/inquiry meaning, or is it exclusively a self-description of behavioral withdrawal?

**Current routing:** `psychoed_depression`  
**Proposed routing if confirmed BA-intent:** `behavioral_activation`

---

### 2. ما أقدر أفرح

**Transliteration:** maa agdar afrah  
**Literal meaning:** "I can't be happy" / "I'm unable to feel joy"  
**Usage context:** Expresses an inability to experience positive affect — the functional definition of anhedonia. A user saying this is describing a symptom, not asking about anhedonia as a concept.

**Engineering assessment:** This is closer to a symptom description than an educational request. However, it could also be the starting point of a conversation that benefits from psychoeducation about anhedonia ("you can't be happy — let me explain why that happens in depression"). The routing decision here has more clinical nuance than phrase 1. Reviewer should assess: does routing this to BA (activity scheduling) serve the user, or does PD (explaining the anhedonia mechanism) serve them better as a first response?

**Current routing:** `psychoed_depression`  
**Proposed routing:** Reviewer decision required

---

### 3. حياتي فاضية

**Transliteration:** hayaati faadiya  
**Literal meaning:** "My life is empty" / "My life feels meaningless/hollow"  
**Usage context:** Expresses a sense of emptiness or lack of meaning in daily life.

**Engineering assessment:** In Khaleeji Arabic, "فاضية" (faadiya/fadhiya) carries connotations of both "empty" (nothing to fill it) and "meaningless/hollow." This phrase is notably more existential than the others — it may reflect behavioral withdrawal (nothing I do matters, so I've stopped doing things — BA territory) or it may reflect the cognitive triad's view of the future as hopeless (PD territory). This is the most ambiguous of the three.

**Important:** The English equivalent "nothing feels meaningful" was removed from PD and is NOT being added to BA in the English change — it was removed to prevent PD over-grabbing but not moved to BA because the meaning is ambiguous. The Arabic phrase حياتي فاضية carries similar ambiguity and may warrant the same treatment: removed from PD if it prevents over-grabbing, but not added to BA unless the reviewer is confident it signals behavioral withdrawal specifically.

**Current routing:** `psychoed_depression`  
**Proposed routing:** Reviewer decision required — and if uncertain, the safe default is to leave in PD (educational response to an existential disclosure is less harmful than misdirecting a BA-intent user)

---

## What the Reviewer Needs to Know

**The routing mechanism:** These phrases are used for Tier 1 deterministic routing — the first skill whose keyword list contains a substring match of the user's message is selected, with no LLM involvement. The decision is permanent for that message: BA starts activity scheduling; PD delivers psychoeducation about depression mechanisms.

**The consequence of each option:**
- If روuted to BA: user immediately enters a behavioral activation protocol (activity audit, identify a small step, commitment). If they were actually asking "what is anhedonia?", they get task planning instead of explanation.
- If routed to PD: user immediately enters a psychoeducation session explaining depression biology and mechanisms. If they were actually saying "I've stopped doing everything", they get education instead of activation.

**Both are clinically valid responses to depression presentations.** The question is which is the better first door for a user who opens with one of these specific phrases.

**The English precedent:** "lost interest in things I used to", "no longer interested in anything", "activities I used to enjoy" → all moved to BA in the English change. "Why do I feel flat", "what is anhedonia", "explain depression" → all retained in PD.

---

## Action

For each phrase, the reviewer should indicate:
- Route to `behavioral_activation` / Keep in `psychoed_depression` / Leave in neither (remove from PD, do not add to BA)
- If there is a nativity or colloquial usage concern (i.e., the phrase means something different in Emirati/Gulf Arabic than the engineering interpretation), note it

Once approved, engineering will apply the changes in a single atomic commit following the same disjointness protocol used for the English fix (verified BA ∩ PD = empty post-change, approved_by stamped on both files).
