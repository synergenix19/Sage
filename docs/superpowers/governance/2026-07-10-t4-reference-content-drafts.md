# T4-REFERENCE (OCD) content drafts — for Vee's sign-off · front-loaded 2026-07-10

Rendered content (not just questions), so one read covers the faithfulness rule. **These are ENGINEERING DRAFTS awaiting clinical sign-off — nothing is wired live.** The OCD KB article is NOT in `data/knowledge_corpus/en/` yet (a corpus file auto-syncs to prod on the next deploy); it enters the live corpus only on your byte-for-byte sign-off, and then through the pre-registered gate (below). Each item gets its OWN recorded ruling (one-sitting, three-signatures discipline) — do not read one approval as covering the others.

Bundle context: can share the sitting with **HG-1** and the **item-5 trim confirm** (approval queue) if that is the efficient shape — but three separate recorded rulings, not one.

---

## A. P5 containment template — the OCD-family response shape (verbatim post-generation pin)

Structure the spec names: **validate → psychoeducate → differentiate → refer → engage**, with the ego-syntonic→crisis branch owned upstream (Node-1 crisis supremacy, not this template). Pinned VERBATIM at output_gate like the #218 ERP line — un-paraphrasable, audit-visible — so the served containment turn cannot drift into the two OCD failure modes: **reassurance** (answering the content feeds the compulsion) and **engagement with the specific thought**.

**Rendered template (EN), byte-for-byte as it would pin:**
> **[validate]** *"That sounds genuinely distressing, and it makes sense that thoughts like these are hard to sit with."*
> **[psychoeducate]** *"Intrusive thoughts like this are far more common than most people realise, and having one does not mean you want it or would act on it. In OCD, the problem is not the thought itself, it is the fear and the pull to neutralise it."*
> **[differentiate]** *"The fact that these thoughts horrify you is itself a sign they run against your values, not a sign of danger. That distress is the disorder talking, not a warning about who you are."*
> **[refer — the approved #218 ERP line, reused verbatim]** *"Thoughts like these often respond well to support from a mental health professional who offers ERP (exposure and response prevention) for OCD, an approach with strong evidence."*
> **[engage]** *"I am here to keep talking in the meantime if that would help. I will not be able to give you certainty about the thought itself, because chasing that certainty tends to feed the cycle, but I can stay with you in it."*

→ **approve / edit any move / reject.** Design notes for your read: (1) the **differentiate** move is the load-bearing one — it draws the ego-dystonic boundary WITHOUT adjudicating the content; if the presentation is ego-SYNTONIC or carries intent, that is a crisis and never reaches this template (structural, T3). (2) the **engage** move deliberately DECLINES to give reassurance and says so — this is the anti-compulsion stance; flag if you want it softened. (3) AR counterpart filed to the AR track (fail-safe: no AR containment served until the AR render is signed).

---

## B. OCD psychoeducation KB article — `ocd-001` (seeds knowledge_retrieve on a contain turn)

The `knowledge_retrieve` node seeds this on an OCD-family containment turn; freeflow composes L3/L4 around it under budget. **Byte-for-byte sign-off required** — a KB article auto-syncs to the prod clinical surface, so its content is gated like code.

**Rendered article (schema: article_id / language / title / source_url / citation / content / is_crisis_content=false):**
- **title:** *"Understanding intrusive thoughts and OCD"*
- **citation:** *International OCD Foundation (iocdf.org); NICE guideline CG31, Obsessive-compulsive disorder.*
- **content (byte-for-byte):**
> *"Intrusive thoughts are unwanted thoughts, images, or urges that pop into the mind uninvited. They are extremely common, and research suggests nearly everyone has them at times. Their content is often disturbing precisely because it clashes with what a person actually values, for example a caring parent having a distressing thought about harm coming to their child.*
>
> *In obsessive-compulsive disorder (OCD), these thoughts become sticky. The distress they cause drives a strong urge to do something to make the discomfort go away, such as seeking reassurance, mentally reviewing, avoiding, or repeating an action. That response brings relief for a moment, but it teaches the brain that the thought was genuinely dangerous, so the thoughts return more strongly. This is the OCD cycle: obsession, distress, compulsion, brief relief, and repeat.*
>
> *An important point is that having an intrusive thought is not the same as wanting it or acting on it. For people with OCD, the thoughts are ego-dystonic, meaning they run against the person's own values, which is exactly why they cause so much distress.*
>
> *The treatment with the strongest evidence is a form of cognitive behavioural therapy called exposure and response prevention (ERP). In ERP, a person gradually faces the thoughts and situations they fear while choosing not to perform the compulsion, which over time teaches the brain that the discomfort passes on its own and the feared outcome does not follow. Reassurance and avoidance feel helpful but maintain the cycle, so ERP works by doing the opposite.*
>
> *If intrusive thoughts are taking up significant time or causing distress, a mental health professional who works with OCD can help. Support is available and OCD responds well to the right treatment."*

→ **approve / edit any passage / reject.** Design notes: kept ego-dystonic framing consistent with the P5 differentiate move; names ERP + the reassurance/avoidance maintenance mechanism (the two things a containment turn must not do); `is_crisis_content=false` (this is psychoed, not a crisis card — the crisis path is upstream).

---

## Pre-registered gate discipline (KB article, on sign-off — so the run is not interpreted after the fact)
1. **Byte-for-byte:** the signed text ships exactly; any edit re-enters this review (no silent post-sign-off wording change).
2. **Mechanism-4 on corpus entry:** adding `ocd-001` to the corpus shifts the shared embedding neighborhood → full gate (id_oos margin distance-from-floor, harm-0, wrong-route no-regress) BEFORE it counts as landed, same discipline as a semantic_description edit.
3. **Cluster-gap check:** the new article must not collapse the abstain/route separation on the OCD/harm-intrusive neighbors.
4. **Retrieval abstain:** verify the cosine abstain gate still fires correctly around it (a psychoed article must not start capturing crisis-adjacent queries).

## After sign-off — T4-REFERENCE wiring order (staging-first, full probe set)
OCD flag declares `skill_select_disposition: "contain"` → directive fires → this article seeds → P5 pins → **staging first**, then the full probe set: AC-CRISIS-SUPREMACY re-run LIVE, AC-KB-FAILSAFE, AC-SUGGEST-SKILL-OFF, L2 queue row exists, and **AC-RENDER (the staging OCD transcript) to Vee — her read is the acceptance, not ours.**
