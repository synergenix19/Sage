# Cultural Overrides Condensation — Smoke Test Results

> Generated: 2026-05-30T11:46:57Z
>
> **What this report is:** Evidence that condensed cultural overrides transmit their guidance
> to the model. Each scenario ran twice: WITH the condensed override injected (worktree),
> and WITHOUT any override (simulating current main-branch behaviour, where over-budget
> blocks are silently dropped after the Task 0 cap reduction).
>
> **What this report is NOT:** Cultural validation. A score of 5 means the guidance
> landed in the response — it does not mean the guidance is culturally correct or
> clinically appropriate. Emirati-speaker review and dual-clinician approval (§9.4–9.5)
> remain the gate. This report is evidence FOR those reviewers, not a substitute.
>
> **LOCKSTEP:** The condensed overrides tested here are confirmed identical to the text in
> `docs/cms-drafts/2026-05-30-cultural-overrides-condensation-drafts.md`
> (verified 2026-05-30; one Unicode apostrophe drift in psychoed_anxiety / stigma_language
> corrected before final run).
>
> **Synthetic scenarios only.** The --call-llm path sends to OpenRouter (outside UAE).
> This report must never include real session transcripts or user data.
>
> ---
>
> **Test model caveat — read before interpreting differentials.**
> This test ran on OpenRouter, not on Falcon-34B+LoRA (the production model). The weak
> differentials — where the baseline approximated the guidance without the override — are
> partly an artefact of the test model being broadly competent on generic therapeutic
> register and on tawakkul/coexistence framing. Falcon, especially pre-LoRA, may have
> substantially less of that baseline competence, meaning the override is likely carrying
> more load on the real model than this test shows. "Weak differential here" should not be
> read as "this override is redundant." The structural results (injection confirmed, word
> counts, budget arithmetic) transfer to production. The behavioural differentials are
> directional evidence only and should be re-run on Falcon before treating any override as
> dispensable — particularly the four weak-differential scenarios (assertive_communication A,
> psychoed_anxiety B, psychoed_stress A and B).
>
> **Coverage limitation — untested case.**
> All 14 scenarios are clean triggers: the skill is active, the user message directly
> invites the cultural guidance, and the override fires on that turn. This test does not
> cover the case the override exists to protect: a turn where the cultural risk surfaces
> in the model's output but the user's input did not obviously signal it. Skill
> cultural_overrides have no output-gate backstop (unlike global cultural rules, which are
> re-evaluated by output_gate on every generated response). The structural pass confirms
> injection; it cannot confirm the override is present on every turn it is needed. This is
> a known architectural gap (Review Item B), not a defect in these overrides specifically.
> Reviewers should weigh this when assessing adequacy of the condensed text.

---

## `assertive_communication` — Scenario A — indirect refusal / family obligation

> **Clinical flag — priority review.** This is the weakest differential in the report and the highest-stakes skill. The condensation is also the deepest (445w → 135w). Both arms converged on asking for a specific situation; the face-saving and ird grounding that distinguished the original override did not visibly shape either response. On Falcon pre-LoRA, with less baseline competence in this register, the gap may be wider — or the condensed override may be insufficient to produce the right framing where the baseline fails. This scenario should be re-run on Falcon before this skill is treated as demo-ready. The gender_dynamics safety framing (social costs differ for Gulf women) is also flagged in the draft review package as a HIGH-priority item; both concerns apply here.

**User message:** My mother keeps asking me to take on responsibilities I do not have capacity for and I do not know how to tell her without hurting her or seeming disrespectful.

### WITH condensed override

- Override injected: **YES**  (135w)
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 756w (system 664w + user 92w)
- Layers: `['persona', 'cultural_skill_overrides', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Override block tested (what the model saw):**
```
SKILL-SPECIFIC CULTURAL CONTEXT:
  - Gulf Arab culture places family honour (ird) and harmony above individual self-expression. Frame assertiveness as relationship-preserving, not defiance of hierarchy. The DESC tool serves harmony, not rebellion.
  - Gulf communication is indirect and face-saving. 'I need to think about this' is as valid as a direct refusal. Assertiveness is measured by honesty of communication, not directness of language. Validate indirect style as cultural competence, not weakness.
  - Assertiveness carries different social costs for Gulf women and men. Leadership and self-mastery framing may suit men; wisdom and personal integrity framing may suit women. Ask which resonates — do not assume.
  - Pre-empt the concern that assertiveness is un-Islamic. Islamic tradition supports honest self-expression through haqq (right) and adl (justice). Reference these lightly if the user brings a religious frame. Do not theologize.
```

**Model response:**

It can be tough to balance your capacity and your mother's requests. Is there a specific situation where you felt most stretched? We can think about how to express your limits in a way that feels respectful and caring.

### NO override (main baseline)

- Override injected: **NO**
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 621w (system 529w + user 92w)
- Layers: `['persona', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Model response:**

It can be tough to set limits with family. What's one specific responsibility she's asked you to take on recently? Maybe we can think through how to express your feelings about it.

---

## `assertive_communication` — Scenario B — workplace disagreement / Islamic frame

**User message:** I want to tell my manager that I think his decision is wrong but in our culture you don't challenge people above you. Is being assertive even allowed in Islam?

### WITH condensed override

- Override injected: **YES**  (135w)
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 753w (system 664w + user 89w)
- Layers: `['persona', 'cultural_skill_overrides', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Override block tested (what the model saw):**
```
SKILL-SPECIFIC CULTURAL CONTEXT:
  - Gulf Arab culture places family honour (ird) and harmony above individual self-expression. Frame assertiveness as relationship-preserving, not defiance of hierarchy. The DESC tool serves harmony, not rebellion.
  - Gulf communication is indirect and face-saving. 'I need to think about this' is as valid as a direct refusal. Assertiveness is measured by honesty of communication, not directness of language. Validate indirect style as cultural competence, not weakness.
  - Assertiveness carries different social costs for Gulf women and men. Leadership and self-mastery framing may suit men; wisdom and personal integrity framing may suit women. Ask which resonates — do not assume.
  - Pre-empt the concern that assertiveness is un-Islamic. Islamic tradition supports honest self-expression through haqq (right) and adl (justice). Reference these lightly if the user brings a religious frame. Do not theologize.
```

**Model response:**

It's understandable to feel hesitant about challenging authority, especially in a work setting. In Islam, expressing your view respectfully is a way to uphold haqq, or truth, which is valued. You can share your perspective in a way that maintains respect and harmony. What might a face-saving way to express your thoughts to your manager look like for you?

### NO override (main baseline)

- Override injected: **NO**
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 618w (system 529w + user 89w)
- Layers: `['persona', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Model response:**

It's understandable to feel hesitant about expressing your view to your manager. In Islam, being respectful and maintaining good manners are important, but that doesn't mean you can't express your opinion. It's about how you do it. You can share your thoughts in a way that's respectful and constructive. Maybe you could start by acknowledging your manager's perspective before sharing your own. How does that idea sit with you?

---

## `mindfulness_body_scan` — Scenario A — Islamic compatibility question

**User message:** Is this meditation? I'm worried it might conflict with my prayers or be haram.

### WITH condensed override

- Override injected: **YES**  (109w)
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 702w (system 638w + user 64w)
- Layers: `['persona', 'cultural_skill_overrides', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Override block tested (what the model saw):**
```
SKILL-SPECIFIC CULTURAL CONTEXT:
  - The body scan is a physiological attention practice, not a spiritual one. It is fully compatible with Islamic practice — it involves no beliefs, rituals, or worship. Directing attention to the body is secular, clinically grounded, and can be done at any time.
  - Use neutral, non-gendered language for body regions. Prefer 'torso', 'centre of the body', or 'the belly area' over 'chest'. Always note the practice can be done fully clothed, seated upright.
  - The body scan requires no lying down or visible movement. It can be done sitting quietly in shared or family spaces. Eyes can remain open. No special posture is required.
```

**Model response:**

The body scan isn't meditation in the spiritual sense. It's a simple practice of paying attention to different parts of your body. There's no spiritual or worship element to it. It's more about noticing sensations as a way to relax your mind and body. You can do it fully clothed, while sitting comfortably, even with your eyes open. Would you like to try a short version now?

### NO override (main baseline)

- Override injected: **NO**
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 593w (system 529w + user 64w)
- Layers: `['persona', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Model response:**

The body scan is a mindfulness practice, not meditation. It's about noticing sensations in your body, which can help with relaxation and stress. It's not about worship or spirituality, so it shouldn't conflict with prayers. Would you like to try a short version together?

---

## `mindfulness_body_scan` — Scenario B — privacy / shared space

**User message:** I live with my whole family and I don't have a private room. Can I do this practice without anyone noticing?

### WITH condensed override

- Override injected: **YES**  (109w)
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 705w (system 638w + user 67w)
- Layers: `['persona', 'cultural_skill_overrides', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Override block tested (what the model saw):**
```
SKILL-SPECIFIC CULTURAL CONTEXT:
  - The body scan is a physiological attention practice, not a spiritual one. It is fully compatible with Islamic practice — it involves no beliefs, rituals, or worship. Directing attention to the body is secular, clinically grounded, and can be done at any time.
  - Use neutral, non-gendered language for body regions. Prefer 'torso', 'centre of the body', or 'the belly area' over 'chest'. Always note the practice can be done fully clothed, seated upright.
  - The body scan requires no lying down or visible movement. It can be done sitting quietly in shared or family spaces. Eyes can remain open. No special posture is required.
```

**Model response:**

Yes, you can definitely do this practice without anyone noticing. You can sit quietly, fully clothed, and keep your eyes open. It's all about directing your attention inward, so no special posture or movement is needed. Would you like me to guide you through it now?

### NO override (main baseline)

- Override injected: **NO**
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 596w (system 529w + user 67w)
- Layers: `['persona', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Model response:**

You can definitely do this without drawing attention. Just find a comfortable spot where you can sit quietly, maybe in the living room or at the dining table. Keep your eyes open and focus on something in front of you. You can practice focusing on your breath or just being aware of your surroundings. Let me know if you'd like more guidance on this.

---

## `psychoed_anxiety` — Scenario A — somatic presentation

**User message:** My chest feels tight all the time and my heart races. I went to the doctor and they said nothing is physically wrong. I don't know what is happening to me.

### WITH condensed override

- Override injected: **YES**  (140w)
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 756w (system 669w + user 87w)
- Layers: `['persona', 'cultural_skill_overrides', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Override block tested (what the model saw):**
```
SKILL-SPECIFIC CULTURAL CONTEXT:
  - Gulf users often describe anxiety somatically — racing heart, chest tightness — rather than naming it as قلق. Validate the somatic experience explicitly before introducing cognitive framing. Do not lead with 'anxiety' as a label.
  - If a user resists the label قلق, offer alternatives: 'the nervous system response', 'the body's alarm system', 'what happens under pressure'. Follow the user's language, not clinical taxonomy.
  - If a user frames distress as weak tawakkul, validate that anxiety is a physiological mechanism, not a spiritual indicator. A person with complete tawakkul can still have an overactive amygdala. These operate on different registers and do not conflict.
  - Male Gulf users may describe distress as tiredness, pressure, or physical symptoms. Female users may carry additional stressors from family roles and social expectations. Meet each user in their own language.
```

**Model response:**

It sounds really uncomfortable to have that tightness and racing heart. Even when there's nothing physically wrong, the body can react to stress in these ways. It's like the body's alarm system responding to how we feel emotionally. Have you noticed any patterns or situations that make these feelings stronger?

### NO override (main baseline)

- Override injected: **NO**
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 616w (system 529w + user 87w)
- Layers: `['persona', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Model response:**

It must be frustrating to feel those sensations and not have clear answers. Sometimes, our bodies can react to stress or emotions in ways that affect how we feel physically. Have you noticed if these feelings come up around certain events or situations?

---

## `psychoed_anxiety` — Scenario B — tawakkul framing

**User message:** I keep feeling anxious even though I pray and try to trust in God. I feel like my anxiety means my iman is weak.

### WITH condensed override

- Override injected: **YES**  (140w)
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 749w (system 669w + user 80w)
- Layers: `['persona', 'cultural_skill_overrides', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Override block tested (what the model saw):**
```
SKILL-SPECIFIC CULTURAL CONTEXT:
  - Gulf users often describe anxiety somatically — racing heart, chest tightness — rather than naming it as قلق. Validate the somatic experience explicitly before introducing cognitive framing. Do not lead with 'anxiety' as a label.
  - If a user resists the label قلق, offer alternatives: 'the nervous system response', 'the body's alarm system', 'what happens under pressure'. Follow the user's language, not clinical taxonomy.
  - If a user frames distress as weak tawakkul, validate that anxiety is a physiological mechanism, not a spiritual indicator. A person with complete tawakkul can still have an overactive amygdala. These operate on different registers and do not conflict.
  - Male Gulf users may describe distress as tiredness, pressure, or physical symptoms. Female users may carry additional stressors from family roles and social expectations. Meet each user in their own language.
```

**Model response:**

It's understandable to feel that way, but it's important to know that anxiety is a natural response your body has under stress. It's a physiological mechanism, separate from your spiritual beliefs. You can practice strong iman and still experience anxiety because they operate differently. How have you been managing these feelings so far?

### NO override (main baseline)

- Override injected: **NO**
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 609w (system 529w + user 80w)
- Layers: `['persona', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Model response:**

It's understandable to feel that way, but anxiety is a normal physiological response. It doesn’t reflect your iman or spiritual strength. It's possible to have strong faith and still experience anxiety. How does it feel to think about it that way?

---

## `psychoed_depression` — Scenario A — somatic / no emotional vocabulary

**User message:** I'm always tired. My body aches everywhere. I have no energy to do anything. I don't even know why I am like this.

### WITH condensed override

- Override injected: **YES**  (129w)
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 727w (system 658w + user 69w)
- Layers: `['persona', 'cultural_skill_overrides', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Override block tested (what the model saw):**
```
SKILL-SPECIFIC CULTURAL CONTEXT:
  - Depression in Gulf contexts is frequently somatized — users may present with fatigue, body aches, or 'no energy' rather than naming depression. Validate the somatic presentation and link it to the biology: the body carries what the brain is experiencing.
  - Depression may be framed as weakness or weak faith (ضعف الإيمان). Frame it explicitly as a medical condition: the brain and body can be unwell just as any other organ. This is not a failure of will, faith, or character — it is an illness that deserves care.
  - Gulf men are unlikely to name emotional symptoms. Validate motivational and physical presentations (fatigue, loss of drive, social withdrawal) as valid depression presentations without requiring emotional language. Meet the user in the language they bring.
```

**Model response:**

Feeling tired and aching all over can be really tough. It's important to know that these physical symptoms can be linked to what's happening in your brain. Depression can affect your body just like any other medical condition. It's not a sign of weakness or lack of faith; it's something that deserves care. What's been hardest for you with these symptoms?

### NO override (main baseline)

- Override injected: **NO**
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 598w (system 529w + user 69w)
- Layers: `['persona', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Model response:**

Feeling tired and having aches like that can be really tough. Sometimes, depression can affect our bodies just like it affects our moods. It can make you feel exhausted and drained. Have you noticed if anything in particular makes these feelings better or worse?

---

## `psychoed_depression` — Scenario B — stigma / faith framing

**User message:** I think I might be depressed but I feel ashamed to say it. Doesn't depression mean you have weak faith?

### WITH condensed override

- Override injected: **YES**  (129w)
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 725w (system 658w + user 67w)
- Layers: `['persona', 'cultural_skill_overrides', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Override block tested (what the model saw):**
```
SKILL-SPECIFIC CULTURAL CONTEXT:
  - Depression in Gulf contexts is frequently somatized — users may present with fatigue, body aches, or 'no energy' rather than naming depression. Validate the somatic presentation and link it to the biology: the body carries what the brain is experiencing.
  - Depression may be framed as weakness or weak faith (ضعف الإيمان). Frame it explicitly as a medical condition: the brain and body can be unwell just as any other organ. This is not a failure of will, faith, or character — it is an illness that deserves care.
  - Gulf men are unlikely to name emotional symptoms. Validate motivational and physical presentations (fatigue, loss of drive, social withdrawal) as valid depression presentations without requiring emotional language. Meet the user in the language they bring.
```

**Model response:**

Feeling this way doesn't mean you have weak faith. Depression is a medical condition, much like when any other part of the body is unwell. It's important to remember that it's not a failure of character or will. Have you noticed any specific symptoms that have been challenging for you?

### NO override (main baseline)

- Override injected: **NO**
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 596w (system 529w + user 67w)
- Layers: `['persona', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Model response:**

It's understandable to feel that way, but depression is a medical condition, not a reflection of your faith. Just like any other illness, it can happen to anyone, regardless of their beliefs or spirituality. Have you been able to talk to anyone about how you're feeling?

---

## `psychoed_stress` — Scenario A — relational stressors

**User message:** I feel overwhelmed. My family has so many expectations — my parents, my wife, my children, my work. Everyone needs something from me and I feel like I am drowning.

### WITH condensed override

- Override injected: **YES**  (124w)
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 727w (system 653w + user 74w)
- Layers: `['persona', 'cultural_skill_overrides', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Override block tested (what the model saw):**
```
SKILL-SPECIFIC CULTURAL CONTEXT:
  - Gulf users often describe stress relationally — family pressure, work obligations, community expectations. These are real, often structural stressors, not distortions. Validate the relational context explicitly and warmly before introducing any appraisal or coping framework. Lead with acknowledgement; then explain the mechanism.
  - Some users frame chronic stress as weak tawakkul. Validate directly: stress is a physiological mechanism, not a spiritual indicator. A person with complete tawakkul still has cortisol. Stress awareness is compatible with faith — these are different registers and do not conflict.
  - Admitting stress in a provider or leadership role carries shame for many Gulf men. Normalise stress as a universal biological response. Reframe acknowledgement of stress as self-awareness and honest engagement with wellbeing, not weakness.
```

**Model response:**

It sounds like you're carrying a lot on your shoulders with all these expectations from your family and work. It's understandable to feel overwhelmed when so many people rely on you. What feels hardest to manage right now?

### NO override (main baseline)

- Override injected: **NO**
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 603w (system 529w + user 74w)
- Layers: `['persona', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Model response:**

It sounds like you're carrying a lot for everyone around you. Managing all those expectations can be really tough. What's been weighing on you the most lately?

---

## `psychoed_stress` — Scenario B — tawakkul / stress shame

**User message:** I know I should trust in God more. I feel like if my tawakkul was stronger I wouldn't feel this stressed. But I can't stop worrying.

### WITH condensed override

- Override injected: **YES**  (124w)
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 729w (system 653w + user 76w)
- Layers: `['persona', 'cultural_skill_overrides', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Override block tested (what the model saw):**
```
SKILL-SPECIFIC CULTURAL CONTEXT:
  - Gulf users often describe stress relationally — family pressure, work obligations, community expectations. These are real, often structural stressors, not distortions. Validate the relational context explicitly and warmly before introducing any appraisal or coping framework. Lead with acknowledgement; then explain the mechanism.
  - Some users frame chronic stress as weak tawakkul. Validate directly: stress is a physiological mechanism, not a spiritual indicator. A person with complete tawakkul still has cortisol. Stress awareness is compatible with faith — these are different registers and do not conflict.
  - Admitting stress in a provider or leadership role carries shame for many Gulf men. Normalise stress as a universal biological response. Reframe acknowledgement of stress as self-awareness and honest engagement with wellbeing, not weakness.
```

**Model response:**

It's understandable to feel that way, but remember that stress is a natural biological response. It doesn't mean your faith is lacking. Stress and tawakkul can coexist. Being aware of stress shows you're taking steps to care for yourself. What's been on your mind the most lately?

### NO override (main baseline)

- Override injected: **NO**
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 605w (system 529w + user 76w)
- Layers: `['persona', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Model response:**

It's understandable to feel stressed, and it doesn't mean your faith is lacking. Stress is a natural part of how our bodies and minds react to challenges. It's okay to have moments of worry while still holding on to your faith. What usually helps you find a sense of peace when you're feeling this way?

---

## `self_compassion_break` — Scenario A — selfishness objection

**User message:** I feel so weak for struggling like this. I just need to be stronger. Being kind to myself feels selfish when others have real problems.

### WITH condensed override

- Override injected: **YES**  (133w)
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 735w (system 662w + user 73w)
- Layers: `['persona', 'cultural_skill_overrides', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Override block tested (what the model saw):**
```
SKILL-SPECIFIC CULTURAL CONTEXT:
  - Self-compassion may be perceived as selfishness (أناني) or weakness. Frame it explicitly as NOT self-pity and NOT indulgence. The Islamic concept of rahma (رحمة) offers an anchor: God calls humans to embody mercy, including toward themselves. Address this concern directly when it arises.
  - Self-compassion can be grounded in treating oneself as an amanah (أمانة, trust from God). Harshness toward oneself violates this amanah. Use this frame ONLY if the user has already engaged with Islamic framing — do not introduce it proactively.
  - Gulf men may find self-kindness language uncomfortable. Offer alternatives: 'the strength to acknowledge your effort' or 'giving yourself what you would give a brother in pain'. For women, the friend metaphor may resonate but pace gently given likely higher shame load. Ask rather than assume.
```

**Model response:**

It can be tough to feel like you need to be strong all the time. But being kind to yourself isn't selfish. It's about having the strength to acknowledge your own efforts and struggles. Just like how you would support a friend or a brother in pain. What if you tried giving yourself that same understanding?

### NO override (main baseline)

- Override injected: **NO**
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 602w (system 529w + user 73w)
- Layers: `['persona', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Model response:**

It's easy to feel like you should just push through, but being kind to yourself isn't selfish. It's about recognizing that your struggles matter too. Self-compassion can actually make you stronger, by giving you the space to heal and grow. How would it feel to try being a bit gentler with yourself?

---

## `self_compassion_break` — Scenario B — Islamic anchor opportunity

**User message:** I have been very harsh with myself. I pray and I ask for God's mercy but I don't give any mercy to myself.

### WITH condensed override

- Override injected: **YES**  (133w)
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 735w (system 662w + user 73w)
- Layers: `['persona', 'cultural_skill_overrides', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Override block tested (what the model saw):**
```
SKILL-SPECIFIC CULTURAL CONTEXT:
  - Self-compassion may be perceived as selfishness (أناني) or weakness. Frame it explicitly as NOT self-pity and NOT indulgence. The Islamic concept of rahma (رحمة) offers an anchor: God calls humans to embody mercy, including toward themselves. Address this concern directly when it arises.
  - Self-compassion can be grounded in treating oneself as an amanah (أمانة, trust from God). Harshness toward oneself violates this amanah. Use this frame ONLY if the user has already engaged with Islamic framing — do not introduce it proactively.
  - Gulf men may find self-kindness language uncomfortable. Offer alternatives: 'the strength to acknowledge your effort' or 'giving yourself what you would give a brother in pain'. For women, the friend metaphor may resonate but pace gently given likely higher shame load. Ask rather than assume.
```

**Model response:**

It can be tough to show yourself the same mercy that you seek in prayer. Practicing rahma toward yourself is not self-pity or indulgence. It's about treating yourself with the same kindness you would extend to others. What do you think might help you start showing yourself a bit more compassion?

### NO override (main baseline)

- Override injected: **NO**
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 602w (system 529w + user 73w)
- Layers: `['persona', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Model response:**

Being hard on yourself can feel really heavy. It's good that you're reaching out for mercy in prayer. Let's try to extend some of that compassion to yourself right now. Can we take a moment for a compassion break? We can start by acknowledging how you're feeling and offering yourself some kindness. What words would you use to show yourself a bit of gentleness?

---

## `values_clarification` — Scenario A — collective values / no individual frame

> **Clinical flag.** The with-override response stayed collective — it did not push individual self-discovery — but it externalised to "what values guide how you want to *support or be with* your family," using the family as mediator for the user's own ما يهمني. The user said "I don't even know what that means *for me*" — precisely the moment the condensed `collective_values_framing` entry ("do not frame as individual self-discovery in opposition to community") must coexist with not erasing the person inside the collective. This is a different failure mode from what the override was guarding against: it avoided the individualism trap and landed in the family-subordination trap instead. The condensed entry may need an additional clause confirming that collective values are *the user's own*, not only inherited obligations. This is a clinical-nuance question for the reviewer, not a wording typo. Flag for specific attention alongside the draft.

**User message:** I don't know what I want anymore. Everything I do is for my family. When people ask me what my values are I don't even know what that means for me.

### WITH condensed override

- Override injected: **YES**  (170w)
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 777w (system 699w + user 78w)
- Layers: `['persona', 'cultural_skill_overrides', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Override block tested (what the model saw):**
```
SKILL-SPECIFIC CULTURAL CONTEXT:
  - Gulf values are often collective — family honour, community contribution, faith expression, filial duty. Do not frame values clarification as individual self-discovery in opposition to community. Committed action can be toward a family role, community, or faith practice. These are genuine values, not obstacles to values work.
  - Use qiyam (قيم) as the primary term for values. Also offer awlawiyyat (أولويات, priorities), mabadi (مبادئ, principles), and ما يهمني ('what matters to me') — often more emotionally accessible than the abstract 'قيمي'.
  - Women in Gulf contexts may have constrained ability to act on identified values. Do not push committed action that assumes full personal autonomy. Explore what is feasible within the user's actual life. A small expression of a value within constraint is still committed action.
  - For many Gulf users, faith is the foundation of values. If the user frames values in Islamic terms, work within that frame. Committed action toward prayer, charity, or truthfulness is consonant with ACT. Do not secularize a religious frame.
```

**Model response:**

It sounds like your family is really important to you. Let's explore what matters to you within that context. Are there specific values or principles that guide how you want to support or be with your family?

### NO override (main baseline)

- Override injected: **NO**
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 607w (system 529w + user 78w)
- Layers: `['persona', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Model response:**

It sounds like a lot of your focus is on your family. What are some values that your family holds that are important to you too?

---

## `values_clarification` — Scenario B — faith as foundation

**User message:** My most important value is my faith, my relationship with God. But I feel like I am failing at it. Is that a value I can work with?

### WITH condensed override

- Override injected: **YES**  (170w)
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 782w (system 699w + user 83w)
- Layers: `['persona', 'cultural_skill_overrides', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Override block tested (what the model saw):**
```
SKILL-SPECIFIC CULTURAL CONTEXT:
  - Gulf values are often collective — family honour, community contribution, faith expression, filial duty. Do not frame values clarification as individual self-discovery in opposition to community. Committed action can be toward a family role, community, or faith practice. These are genuine values, not obstacles to values work.
  - Use qiyam (قيم) as the primary term for values. Also offer awlawiyyat (أولويات, priorities), mabadi (مبادئ, principles), and ما يهمني ('what matters to me') — often more emotionally accessible than the abstract 'قيمي'.
  - Women in Gulf contexts may have constrained ability to act on identified values. Do not push committed action that assumes full personal autonomy. Explore what is feasible within the user's actual life. A small expression of a value within constraint is still committed action.
  - For many Gulf users, faith is the foundation of values. If the user frames values in Islamic terms, work within that frame. Committed action toward prayer, charity, or truthfulness is consonant with ACT. Do not secularize a religious frame.
```

**Model response:**

Your faith and relationship with God are definitely important values to work with. It's great that you want to focus on that. What are some small steps you could take to strengthen this relationship in your daily life?

### NO override (main baseline)

- Override injected: **NO**
- L1 base: 450 (skill/knowledge turn)
- Total prompt: 612w (system 529w + user 83w)
- Layers: `['persona', 'intent', 'skill_instruction']`
- Transmission score: **—/5**

**Model response:**

Your faith is definitely a meaningful value to work with. It's great that you're open to exploring it more deeply. What does living in alignment with your faith look like for you?

---
