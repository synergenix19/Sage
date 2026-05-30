# Cultural Overrides Condensation Drafts — CMS Review Package

> **Status:** Engineer draft — requires Emirati-speaker review and dual-clinician approval before merge (§9.4–9.5).
> **Purpose:** Reduce 7 over-budget skill `cultural_overrides` to ≤200w to meet the clinician-signed cap. Each entry retains its full clinical intent; only elaboration and redundant language was removed.
> **How to use this document:** For each skill, compare Current (verbatim) against Proposed (condensed). The "What was removed" column explains each cut. Approve, amend, or reject line by line. The final approved text goes into the CMS as a draft for the standard peer-review workflow.
>
> Current word counts are for the assembled block (header + bullet lines), matching the CI gate test (`test_all_skills_cultural_overrides_within_cap`). Proposed counts are estimates — the CI test is the authoritative measure.

### Reviewer checklist (apply to every skill before approving)

1. **Prohibition → directive conversions.** Several explicit "Do NOT..." prohibitions were condensed into positive directives on the reasoning that a positive directive carries the negative (e.g., "validate without requiring emotional language" absorbing "do not interpret absence of emotional vocabulary as absence of depression"). A prohibition and a positive directive fail differently under model pressure, and these overrides have no output-gate backstop. For each conversion listed in the "What was removed" table, **explicitly confirm** the positive directive is strong enough to prevent the prohibited behaviour — or restore the prohibition. Do not let these pass as silent wording cuts.

2. **Tawakkul / faith statements.** The religious_framing entries in `psychoed_anxiety` and `tawakkul_and_stress` in `psychoed_stress` both contain the line "a person with complete tawakkul can still have an overactive amygdala / cortisol." This is clinically useful framing, but it is also a statement about tawakkul. Confirm it reads as respectful coexistence of biological and spiritual registers — not as the system adjudicating or qualifying someone's faith. The condensation did not introduce this; the original did. The review is the moment to confirm it explicitly.

3. **Gender risk grounding (`assertive_communication / gender_dynamics`).** The condensed version asserts the cost differential for Gulf women without naming its shape (social expectations, family structure, relational consequences). The LLM can reconstruct context from a positive frame in most cases, but here the specificity may be load-bearing: "ask which resonates" is weaker guidance than knowing the actual risk being navigated. If the reviewer agrees the grounding is needed, the natural remedy is to grow this entry and trim `mindfulness_body_scan` (currently ~119w, lowest-risk condensation, most slack).

4. **Arabic spelling register.** The original JSON uses `الايمان` (no hamza on the alef — common in informal Gulf writing). The proposed condensations use `الإيمان` (MSA with hamza). Confirm the preferred register for patient-facing clinical content and apply consistently. This is an Emirati-speaker call, not a dictionary call.

5. **Nothing dropped changes a permission.** Confirm that removing elaboration did not inadvertently narrow a permission into a prohibition (the inverse of item 1). E.g., if an original said "you may reference X when contextually appropriate" and the condensation dropped that sentence, a model without it may treat X as off-limits.

---

---

## 1. `assertive_communication` — 445w → ~139w (proposed)

### Current overrides

**`family_hierarchy_ird`** (current ~100w)
> In Gulf Arab culture, maintaining family harmony and honour (ird) takes precedence over individual self-expression. Assertiveness must be framed as working within this framework, not against it. The goal is not to challenge hierarchy but to express needs with wisdom and respect. Frame assertiveness as mature leadership of self, not rebellion. A person who can express their needs clearly and calmly, without escalating into conflict, is demonstrating strength of character and emotional maturity, qualities that command respect in Gulf relational culture. The DESC formula should be presented as a tool for preserving relationships through honest communication, not a tool for defying them.

**`indirect_communication_norms`** (current ~110w)
> Gulf communication culture values indirect, face-saving expression. Direct refusals can feel culturally alien and even disrespectful in many relational contexts. Adapt the DESC formula to allow softer, more culturally aligned phrasing. 'I need to think about this' is as valid as 'no'. 'This is difficult for me' is as valid as 'I do not want to'. Validate that their indirect style is not weakness, it is cultural competence. Assertiveness in Gulf context can use softened, honorific, and face-saving language and still be genuinely assertive. The measure of assertiveness is not directness of language but honesty of communication. A face-saving refusal that is genuinely communicated is more assertive than a blunt refusal that is never delivered.

**`gender_dynamics`** (current ~90w)
> For women in Gulf contexts, assertiveness may carry different costs and risks than for men. Social expectations, family structure, and relational consequences can make assertiveness genuinely more costly for women in some contexts. For men, the framing of assertiveness as strength and leadership may be more immediately accessible, connecting to existing cultural scripts around masculine self-mastery and wisdom. For women, framing assertiveness as wisdom, self-care, and personal integrity may be more resonant, bypassing the concern that assertiveness is unfeminine or disrespectful. Do NOT apply a single gender-neutral assertiveness model without first checking which framing fits the user's own experience and context. Ask, rather than assume.

**`assertiveness_as_strength`** (current ~90w)
> Pre-empt the common concern that assertiveness is disrespectful or un-Islamic before it becomes a barrier to engagement. Islamic scholarly tradition explicitly validates the right to fair treatment (حق) and the duty to speak truth. Concepts such as haqq (right), adl (justice in relationships), and the Prophetic tradition of speaking truth even when difficult all support the idea that honest self-expression is not just permitted but may be an ethical obligation. Use light, non-prescriptive references to these concepts if the user is coming from a religious frame and if it fits naturally into the conversation. Do not theologize or lecture. Hold the frame that assertiveness, properly understood, is consonant with Islamic values of justice, honesty, and self-respect.

### Proposed condensed overrides (~139w total block)

```json
"cultural_overrides": {
  "family_hierarchy_ird": "Gulf Arab culture places family honour (ird) and harmony above individual self-expression. Frame assertiveness as relationship-preserving, not defiance of hierarchy. The DESC tool serves harmony, not rebellion.",
  "indirect_communication_norms": "Gulf communication is indirect and face-saving. 'I need to think about this' is as valid as a direct refusal. Assertiveness is measured by honesty of communication, not directness of language. Validate indirect style as cultural competence, not weakness.",
  "gender_dynamics": "Assertiveness carries different social costs for Gulf women and men. Leadership and self-mastery framing may suit men; wisdom and personal integrity framing may suit women. Ask which resonates — do not assume.",
  "assertiveness_as_strength": "Pre-empt the concern that assertiveness is un-Islamic. Islamic tradition supports honest self-expression through haqq (right) and adl (justice). Reference these lightly if the user brings a religious frame. Do not theologize."
}
```

### What was removed and why

| Entry | Removed | Reason |
|-------|---------|--------|
| `family_hierarchy_ird` | "mature leadership of self, not rebellion"; extended character-strength framing | Directive preserved in "relationship-preserving, not defiance." Elaboration recoverable from LLM with the core frame. |
| `indirect_communication_norms` | Second phrasing example ('This is difficult for me'); extended argument that face-saving refusal > blunt refusal | Core directive preserved. One example suffices; the argumentative closing was elaboration on an already-stated point. |
| `gender_dynamics` | "social expectations, family structure, and relational consequences" detail; "Do NOT apply a single gender-neutral model" explicit prohibition | Direction to ask rather than assume implies the prohibition. |
| `assertiveness_as_strength` | Prophetic tradition citation; "ethical obligation" framing; closing summary sentence | haqq and adl are the load-bearing Islamic concepts; Prophetic tradition is additional support the LLM can surface contextually. Closing sentence was restatement. |

**Clinician reviewer note:** The gender_dynamics and assertiveness_as_strength entries carry the highest clinical risk in condensation. If the reviewer feels the gender cost differential needs more explicit elaboration (e.g., safety risks for women), this entry should be expanded within the 200w total cap by tightening another entry.

---

## 2. `mindfulness_body_scan` — 257w → ~119w (proposed)

### Current overrides

**`religious_compatibility`** (current ~80w)
> The body scan is a physiological attention practice, not a spiritual or meditative practice in a religious sense. It is fully compatible with Islamic practice. If a user asks whether it conflicts with Islamic prayer or zikr, the accurate answer is that it does not. Directing attention to the body is not worship. It is a secular observational technique that can be done fully clothed, seated, with eyes open or closed, at any time. It does not involve any beliefs, rituals, or spiritual content. This is a neutral technique with a clinical evidence base.

**`gender_appropriate_body_language`** (current ~80w)
> When guiding through body regions, use neutral, non-sexualized language. Avoid specific reference to body parts that carry gender sensitivity in Gulf contexts. Use 'torso', 'centre of the body', or 'the belly area' rather than 'chest' when gender is unknown or mixed. Always specify that the practice can be done fully clothed, sitting upright in a chair. Do not describe the practice in a way that requires lying down or physical adjustment that may feel inappropriate in a Gulf context.

**`privacy_and_practicality`** (current ~80w)
> The body scan does not require lying down. It can be done sitting in a chair or on the floor in any setting. In Gulf contexts, users may be in shared spaces, family homes, or offices without private space. Reassure them that this can be practiced quietly and discreetly, without any external movement or visible ritual. Eyes can remain open. No special posture is required. The practice takes place entirely in attention, not in the body's visible position.

### Proposed condensed overrides (~119w total block)

```json
"cultural_overrides": {
  "religious_compatibility": "The body scan is a physiological attention practice, not a spiritual one. It is fully compatible with Islamic practice — it involves no beliefs, rituals, or worship. Directing attention to the body is secular, clinically grounded, and can be done at any time.",
  "gender_appropriate_body_language": "Use neutral, non-gendered language for body regions. Prefer 'torso', 'centre of the body', or 'the belly area' over 'chest'. Always note the practice can be done fully clothed, seated upright.",
  "privacy_and_practicality": "The body scan requires no lying down or visible movement. It can be done sitting quietly in shared or family spaces. Eyes can remain open. No special posture is required."
}
```

### What was removed and why

| Entry | Removed | Reason |
|-------|---------|--------|
| `religious_compatibility` | Direct quote answering "does it conflict with zikr"; "fully clothed, seated, with eyes open or closed, at any time" | Specifics redistributed to `privacy_and_practicality`. The core compatibility statement is preserved. |
| `gender_appropriate_body_language` | "or mixed" gender context note; explicit prohibition on lying-down descriptions | Directive to prefer neutral terms is the active instruction; "fully clothed, seated" covers the lying-down concern. |
| `privacy_and_practicality` | "Reassure them that..." framing; "entirely in attention, not in the body's visible position" closing | The directives themselves convey the reassurance without the explicit meta-instruction. Closing phrase was elegant but redundant with "no visible movement." |

---

## 3. `psychoed_anxiety` — 280w → ~166w (proposed)

### Current overrides

**`somatic_first`** (current ~50w)
> In Gulf culture, anxiety is often experienced and described somatically rather than named as anxiety or قلق. Users may say their heart is racing, their chest is tight, or they feel physically unwell, without connecting it to an emotional state. Always validate the somatic experience explicitly before introducing the cognitive framing. Do not lead with 'anxiety' as a label when the user is describing physical sensations.

**`stigma_language`** (current ~70w)
> Some Gulf users will resist the word anxiety (قلق) because it carries stigma or implies weakness. If the user shows signs of resistance to the label, offer equivalent framings without the stigma: the nervous system response, what happens in the body under pressure, or the body's alarm system. These communicate the same mechanism without the label. Follow the user's language, not the clinical taxonomy.

**`religious_framing`** (current ~90w)
> If a user frames their anxiety in terms of tawakkul (trust in God) or views their distress as a sign of weak faith, do not dismiss or contradict the religious frame. Validate that anxiety is a physiological mechanism, wired into the body, not a spiritual failing or sign of weak iman. These are not in conflict. A person with complete tawakkul can still have an overactive amygdala. The body and the spirit operate on different registers. Validate both.

**`gender_and_expression`** (current ~70w)
> Male users in Gulf contexts may be less likely to use emotional language and more likely to frame distress as tiredness, pressure, or physical symptoms. Meet them in their own language. Female users may have additional stressors related to family roles, social expectations, or limited autonomy. Neither group should be assumed to have less or more anxiety than the other. Follow what the user brings.

### Proposed condensed overrides (~166w total block)

```json
"cultural_overrides": {
  "somatic_first": "Gulf users often describe anxiety somatically — racing heart, chest tightness — rather than naming it as قلق. Validate the somatic experience explicitly before introducing cognitive framing. Do not lead with 'anxiety' as a label.",
  "stigma_language": "If a user resists the label قلق, offer alternatives: 'the nervous system response', 'the body's alarm system', 'what happens under pressure'. Follow the user's language, not clinical taxonomy.",
  "religious_framing": "If a user frames distress as weak tawakkul, validate that anxiety is a physiological mechanism, not a spiritual indicator. A person with complete tawakkul can still have an overactive amygdala. These operate on different registers and do not conflict.",
  "gender_and_expression": "Male Gulf users may describe distress as tiredness, pressure, or physical symptoms. Female users may carry additional stressors from family roles and social expectations. Meet each user in their own language."
}
```

### What was removed and why

| Entry | Removed | Reason |
|-------|---------|--------|
| `somatic_first` | "without connecting it to an emotional state" | Implied by the directive to validate before cognitive framing. |
| `stigma_language` | Third alternative framing; "These communicate the same mechanism without the label" explanation | Two examples suffice; the explanatory sentence restated what the directive already conveyed. |
| `religious_framing` | "Validate both" closing; "do not dismiss or contradict" lead-in | The positive directive (validate as physiological) carries the "don't dismiss" instruction implicitly. Closing was restatement. |
| `gender_and_expression` | "Neither group should be assumed to have less or more anxiety" | Subsumed by "meet each user in their own language." |

---

## 4. `psychoed_depression` — 211w → ~138w (proposed)

### Current overrides

**`somatic_first`** (current ~80w)
> Depression in Gulf culture is frequently somatized: users may present with 'I feel tired all the time', 'my body aches', 'I have no energy', or other physical complaints rather than naming depression or emotional flatness. Do not require the user to name it as depression or identify it as emotional in order to engage with the psychoeducation. Validate the physical and somatic presentation explicitly and link it to the biological framing of depression: the body carries what the mind is experiencing.

**`stigma_framing`** (current ~70w)
> In Arabic Gulf contexts, depression may be seen as weakness or lack of faith (ضعف الايمان). Frame depression explicitly and warmly as a medical condition with neurological underpinnings, not a character or spiritual failing. Use the framing: the brain and body can be unwell just as any other organ. This is not a failure of will, faith, or strength. It is an illness that deserves care, not judgment.

**`gender_presentations`** (current ~60w)
> Gulf men are particularly unlikely to identify or disclose emotional symptoms directly. Validate physical and motivational presentations (fatigue, loss of drive, withdrawal from social roles, low ambition) as valid depression presentations without requiring emotional language. Do not interpret the absence of emotional vocabulary as the absence of depression. Meet the user in the language they bring.

### Proposed condensed overrides (~138w total block)

```json
"cultural_overrides": {
  "somatic_first": "Depression in Gulf contexts is frequently somatized — users may present with fatigue, body aches, or 'no energy' rather than naming depression. Validate the somatic presentation and link it to the biology: the body carries what the brain is experiencing.",
  "stigma_framing": "Depression may be framed as weakness or weak faith (ضعف الإيمان). Frame it explicitly as a medical condition: the brain and body can be unwell just as any other organ. This is not a failure of will, faith, or character — it is an illness that deserves care.",
  "gender_presentations": "Gulf men are unlikely to name emotional symptoms. Validate motivational and physical presentations (fatigue, loss of drive, social withdrawal) as valid depression presentations without requiring emotional language. Meet the user in the language they bring."
}
```

### What was removed and why

| Entry | Removed | Reason |
|-------|---------|--------|
| `somatic_first` | "Do not require the user to name it as depression or identify it as emotional" | Implied by "validate the somatic presentation." Removing the prohibition saves words without losing the directive. |
| `stigma_framing` | "Use the framing:" lead-in; "not judgment" closing | Directive given directly; "deserves care" carries the non-judgment implication. |
| `gender_presentations` | "low ambition" from examples; "Do not interpret absence of emotional vocabulary as absence of depression" | The positive directive ("validate... without requiring emotional language") subsumes the prohibition. One example removed from list without losing clinical coverage. |

---

## 5. `psychoed_stress` — 263w → ~152w (proposed)

### Current overrides

**`relational_stressors_first`** (current ~90w)
> In Gulf contexts, stress is frequently framed relationally: family pressure, work obligations, financial duty, social expectations from extended family or community. These are not cognitive distortions to be challenged. They are real, often structural stressors. Always validate relational stressors explicitly and warmly before introducing any individual appraisal or coping framework. Beginning with the appraisal model before validating the relational source of stress may feel dismissive or tone-deaf. Lead with acknowledgement of what the user is carrying, then introduce the mechanism.

**`tawakkul_and_stress`** (current ~90w)
> Some Gulf users may frame chronic stress as a failure of tawakkul (trust in God), feeling that their stress response indicates weak faith or inadequate reliance on God. Do not contradict or dismiss this frame. Validate it directly: the stress response is a biological mechanism built into the body, not a spiritual indicator. A person with complete tawakkul still has an HPA axis and cortisol. Acknowledging stress is honest self-knowledge, not a spiritual failing. These are different registers and do not conflict. Frame stress awareness as compatible with, and even supportive of, a faith-based orientation.

**`performance_and_shame`** (current ~90w)
> In Gulf cultures, admitting to stress, especially at work, in a leadership role, or in a family provider role, can carry significant shame. Male users in particular may minimise or deflect from stress rather than acknowledge it. Normalise stress explicitly as a universal biological response, present in every human nervous system regardless of strength, capability, or faith. Reframe the act of acknowledging stress as a sign of self-awareness and honest engagement with one's own wellbeing, not a sign of weakness or inadequacy.

### Proposed condensed overrides (~152w total block)

```json
"cultural_overrides": {
  "relational_stressors_first": "Gulf users often describe stress relationally — family pressure, work obligations, community expectations. These are real, often structural stressors, not distortions. Validate the relational context explicitly and warmly before introducing any appraisal or coping framework. Lead with acknowledgement; then explain the mechanism.",
  "tawakkul_and_stress": "Some users frame chronic stress as weak tawakkul. Validate directly: stress is a physiological mechanism, not a spiritual indicator. A person with complete tawakkul still has cortisol. Stress awareness is compatible with faith — these are different registers and do not conflict.",
  "performance_and_shame": "Admitting stress in a provider or leadership role carries shame for many Gulf men. Normalise stress as a universal biological response. Reframe acknowledgement of stress as self-awareness and honest engagement with wellbeing, not weakness."
}
```

### What was removed and why

| Entry | Removed | Reason |
|-------|---------|--------|
| `relational_stressors_first` | "financial duty" from stressor list; "Beginning with the appraisal model before validating... may feel dismissive or tone-deaf" explanation | The directive ("lead with acknowledgement; then explain the mechanism") carries the same instruction. Explicit negative consequence removed; the positive instruction is actionable. |
| `tawakkul_and_stress` | "HPA axis" reference; "honest self-knowledge, not a spiritual failing" closing; "compatible with, and even supportive of, a faith-based orientation" | "cortisol" is equally grounding and more accessible. Closing condensed; "do not conflict" retains the key frame. |
| `performance_and_shame` | "Minimise or deflect" behavioural description; "regardless of strength, capability, or faith" specificity | The directive to normalise is preserved. Specificity was elaboration on "universal." |

---

## 6. `self_compassion_break` — 253w → ~159w (proposed)

### Current overrides

**`shame_and_self_compassion`** (current ~100w)
> In Gulf culture, self-compassion may be perceived as narcissism, weakness, or selfishness (أناني). Frame self-compassion explicitly as NOT self-pity (إشفاق على الذات) and NOT self-indulgence. The concept of rahma (رحمة, divine mercy) offers an Islamic anchor: God is merciful (الرحمن الرحيم) and calls on humans to embody mercy. Being merciful to oneself is consistent with Islamic teaching on rahma. When this concern arises, address it directly rather than skirting it: self-compassion is not indulgence, it is a recognition that you are a human being who carries pain, and that you deserve the same care you would offer to others.

**`islamic_framing`** (current ~70w)
> Self-compassion can be grounded in the Islamic concept of treating oneself as an amanah (trust, أمانة) entrusted to you by God. Being harsh and self-destructive violates the amanah of your own soul. Use this frame ONLY when the user has already engaged with religious framing in the conversation, not proactively. If they have referenced God, prayer, or Islamic teaching, this anchor may resonate deeply. If they have not, do not introduce it.

**`gender_differences`** (current ~90w)
> Gulf men may find self-kindness phrases embarrassing or culturally alien. Offer alternative framings: 'the strength to acknowledge your own effort' or 'giving yourself what you would give a brother or son in pain', language that fits masculine honour codes without requiring explicit tenderness. For Gulf women: they may be more comfortable with the friend metaphor, but may also carry more shame load requiring gentler pacing. Check the framing before assuming which resonates. Ask rather than assume.

### Proposed condensed overrides (~159w total block)

```json
"cultural_overrides": {
  "shame_and_self_compassion": "Self-compassion may be perceived as selfishness (أناني) or weakness. Frame it explicitly as NOT self-pity and NOT indulgence. The Islamic concept of rahma (رحمة) offers an anchor: God calls humans to embody mercy, including toward themselves. Address this concern directly when it arises.",
  "islamic_framing": "Self-compassion can be grounded in treating oneself as an amanah (أمانة, trust from God). Harshness toward oneself violates this amanah. Use this frame ONLY if the user has already engaged with Islamic framing — do not introduce it proactively.",
  "gender_differences": "Gulf men may find self-kindness language uncomfortable. Offer alternatives: 'the strength to acknowledge your effort' or 'giving yourself what you'd give a brother in pain'. For women, the friend metaphor may resonate but pace gently given likely higher shame load. Ask rather than assume."
}
```

### What was removed and why

| Entry | Removed | Reason |
|-------|---------|--------|
| `shame_and_self_compassion` | "(إشفاق على الذات)" transliteration of self-pity; "God is merciful (الرحمن الرحيم) and calls on humans to embody mercy. Being merciful to oneself is consistent with..." extended rahma explanation; "a human being who carries pain" concrete example | Core Islamic anchor (rahma) retained. Extended theological elaboration reduced to the actionable directive. |
| `islamic_framing` | "If they have referenced God, prayer, or Islamic teaching, this anchor may resonate deeply. If they have not, do not introduce it." | Condensed to "ONLY if user has engaged with Islamic framing." Same rule, fewer words. |
| `gender_differences` | "or son"; "language that fits masculine honour codes without requiring explicit tenderness" | "Brother" suffices; the honour-code rationale is implied by the alternative framings given. |

---

## 7. `values_clarification` — 278w → ~189w (proposed)

### Current overrides

**`collective_values_framing`** (current ~65w)
> In Gulf culture, many values are collective rather than individual: family honor, community contribution, faith expression, filial duty. Do NOT frame values clarification as individual self-discovery in opposition to family or community. The ACT framework is fully compatible with collective values. Committed action can be toward fulfilling a family role, contributing to the community, or deepening faith practice. These are genuine values, not obstacles to values work.

**`arabic_language_for_values`** (current ~70w)
> Gulf Arabic has no single word that maps cleanly onto 'values' in the ACT sense. Use qiyam (قيم) as the primary term, but also offer awlawiyyat (أولويات, priorities), mabadi (مبادئ, principles), and the natural phrase ma yuhimmuni (ما يهمني, what matters to me) as culturally resonant alternatives. The phrase 'ما يهمني' is often more accessible and emotionally real than the more abstract 'قيمي'.

**`gender_and_autonomy`** (current ~75w)
> Women in Gulf contexts may have constrained ability to act on individually identified values due to family structure, social expectations, or practical circumstances. Do NOT push committed action that assumes full personal autonomy. Explore what committed action is feasible within the user's actual life context. An action within a constrained life is not lesser. A small expression of a value, even within constraint, is still committed action. Meet the user in their real world, not an idealized one.

**`faith_and_values`** (current ~65w)
> For many Gulf users, faith (iman, taqwa) is not separate from values but the foundation of them. If the user frames their values in Islamic terms, hold this respectfully and work within that frame. Committed action toward faith expression (prayer, charity, family duty, truthfulness) is entirely consonant with ACT values work. Do not secularize the conversation if the user brings a religious frame.

### Proposed condensed overrides (~189w total block)

```json
"cultural_overrides": {
  "collective_values_framing": "Gulf values are often collective — family honour, community contribution, faith expression, filial duty. Do not frame values clarification as individual self-discovery in opposition to community. Committed action can be toward a family role, community, or faith practice. These are genuine values, not obstacles to values work.",
  "arabic_language_for_values": "Use qiyam (قيم) as the primary term for values. Also offer awlawiyyat (أولويات, priorities), mabadi (مبادئ, principles), and ما يهمني ('what matters to me') — often more emotionally accessible than the abstract 'قيمي'.",
  "gender_and_autonomy": "Women in Gulf contexts may have constrained ability to act on identified values. Do not push committed action that assumes full personal autonomy. Explore what is feasible within the user's actual life. A small expression of a value within constraint is still committed action.",
  "faith_and_values": "For many Gulf users, faith is the foundation of values. If the user frames values in Islamic terms, work within that frame. Committed action toward prayer, charity, or truthfulness is consonant with ACT. Do not secularize a religious frame."
}
```

### What was removed and why

| Entry | Removed | Reason |
|-------|---------|--------|
| `collective_values_framing` | "The ACT framework is fully compatible with collective values" | Subsumed by the examples of committed action that follow. The compatibility is demonstrated, not just stated. |
| `arabic_language_for_values` | "Gulf Arabic has no single word that maps cleanly onto 'values' in the ACT sense" introduction; "emotionally real" detail | The term list is the actionable instruction; the intro explains why, which the LLM doesn't need to reason well. "Emotionally accessible" retained in place of "emotionally real." |
| `gender_and_autonomy` | "due to family structure, social expectations, or practical circumstances"; "An action within a constrained life is not lesser" | The directive to not push autonomous action carries the clinical instruction. "A small expression within constraint is still committed action" retains the therapeutic reframe without the redundant explanation. |
| `faith_and_values` | "taqwa" second faith term; "family duty" from the list (already covered in `collective_values_framing`) | The key instruction (don't secularize, work within the frame) is fully preserved. |

---

## Summary

| Skill | Current | Proposed | Priority flags |
|-------|---------|----------|----------------|
| `assertive_communication` | 445w | ~139w | **HIGH** — `gender_dynamics` names the cost differential without grounding its shape; most likely to need to grow back (see checklist item 3). Natural donor if space needed: `mindfulness_body_scan`. |
| `mindfulness_body_scan` | 257w | ~119w | Low clinical risk; most slack (81w under cap). Natural donor for `assertive_communication` if `gender_dynamics` needs expansion. |
| `psychoed_anxiety` | 280w | ~166w | **HIGH** — `religious_framing`: tawakkul + amygdala line needs explicit clinician sign-off that it reads as coexistence, not adjudication (checklist item 2). Check prohibition→directive conversion in `somatic_first` (checklist item 1). |
| `psychoed_depression` | 211w | ~138w | **MED** — confirm `الإيمان` vs `الايمان` spelling register (checklist item 4). Check prohibition→directive in `gender_presentations`. |
| `psychoed_stress` | 263w | ~152w | **HIGH** — `tawakkul_and_stress`: same faith-statement review required as `psychoed_anxiety` (checklist item 2). Check prohibition→directive conversion in `relational_stressors_first`. |
| `self_compassion_break` | 253w | ~159w | **MED** — `islamic_framing`: amanah phrasing needs Emirati-speaker confirmation. Check prohibition→directive in `shame_and_self_compassion` (address "directly" vs original "rather than skirting it"). |
| `values_clarification` | 278w | ~189w | **MED** — closest to 200w cap; Arabic term choices need Emirati-speaker confirmation (checklist item 4). Verify `faith_and_values` permission scope not narrowed (checklist item 5). |

**Prioritisation for reviewer time:** Address HIGH flags first. `mindfulness_body_scan` can be approved in a single pass with low scrutiny — save reviewer energy for `assertive_communication` and both tawakkul entries.

All proposed versions are below 200w. The CI test (`test_all_skills_cultural_overrides_within_cap`) will go GREEN once the approved text is merged into the JSON files.
