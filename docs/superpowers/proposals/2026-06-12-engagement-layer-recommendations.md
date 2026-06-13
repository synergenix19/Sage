# Engagement Layer Recommendations — Research Synthesis and Proposal

**Date:** 2026-06-12
**Status:** Proposal — pending product + clinical review
**Trigger:** Stakeholder feedback: "If it is therapeutic style, it may not be engaging, and our competition is ChatGPT and Claude... It should always feel natural before it goes into a therapeutic dialogue. Maybe we give some agency of choice to the users... should our approach be to layer just certain guardrails on untrained models and not use therapeutic dialogue as a basis?"
**Method:** Codebase audit (L0–L5 templates, intent_route, skill_select, skill_executor, output_gate) + multi-source web research with adversarial claim verification (24 claims confirmed 3-0, 1 refuted; plus 3 targeted follow-up sweeps on mental-health chatbots, autonomy-support evidence, and 2025–26 regulation).

---

## 1. The architecture question, answered first

**Recommendation: keep the structured therapeutic core. Do not replace it with a generalist model plus guardrails. The engagement problem is real, but it lives in three specific conversational-layer design choices, all fixable without touching the graph.**

Evidence for keeping the structure:

1. **The best clinical result in the field is NOT "guardrails on an untrained model."** Dartmouth Therabot (NEJM AI 2025, the first RCT of a generative therapy chatbot: d=0.84–0.90 on depression) is a QLoRA **fine-tuned** model (Falcon-7B + LLaMA-2-70B) trained on 6 years / 100,000+ human-hours of clinician-written CBT dialogues — *plus* a crisis classifier, *plus* every response reviewed by clinicians post-transmission. Even then it required 15 suicidal-ideation interventions and 13 response corrections in a 4-week trial. The lead author's own conclusion: "no generative AI agent is ready to operate fully autonomously in mental health." [NEJM AI AIoa2400802]
2. **Regulation is moving against the generalist posture.** Illinois WOPR Act (Aug 2025) bans AI that "make[s] independent therapeutic decisions" or "directly interact[s] with clients in any form of therapeutic communication" without a licensed professional; Nevada and New York followed; Utah HB 452 mandates non-human disclosure. The World Psychiatry systematic review (Hua et al. 2025, 160 studies) found 65% of clinical-efficacy-tested systems are structured/rule-based vs only 16% of LLM systems reaching efficacy testing, and calls for transparent architecture reporting and certification-style evaluation. Sage's deterministic crisis layer, auditable graph, clinician review queue, and PDPL audit trail are exactly what this direction rewards. [DLA Piper Aug 2025; wps.21352]
3. **Engagement-optimized generalists are the documented failure mode.** Replika (CHI 2025, 35,390 excerpts): 29.3% contained harmful behaviors; "algorithmic conformity" — uncritical affirmation of harmful ideation — attributed to engagement-driven design. Character.AI/Google settled the teen-suicide lawsuits (Jan 2026); blamed design features were anthropomorphic bonding, sustained engagement, and memory-driven attachment. Harvard/HBS audit: 37% of companion-app farewells contain emotional manipulation; the tactics boost engagement up to 14× but via anger/reactance, raising churn intent and perceived legal liability. The single wellness-positioned app audited (Flourish) showed 0% manipulation. [arXiv 2410.20130; arXiv 2508.19258; Fortune 2026-01-08]
4. **The generalists are converging toward Sage's architecture, not away from it.** OpenAI's October 2025 sensitive-conversations work added taxonomies, 170+ clinician-authored ideal responses across 60 countries, a real-time distress router to a safer model, and break reminders — i.e., they are retrofitting a deterministic safety/routing layer into a generalist. Sage already has one.

**However** — the same evidence shows the *conversational* bar is set by the generalists, and three things in Sage's current prompt layer genuinely fail that bar. Competing with ChatGPT/Claude means adopting their conversation grammar, not their architecture.

---

## 2. Diagnosis: where Sage's engagement actually leaks

### 2.1 Covert steering into skills (the biggest one — and the stakeholder's instinct is evidence-backed)

Today: a Tier-1 keyword substring ("heart racing" anywhere in a message) instantly activates a skill at step 1. `L2_new_skill` v1.0.0 instructs: *"Introduce the approach naturally, without announcing it as a technique."* The user is never offered a choice; entry screens (5 skills) are contraindication safety checks, not consent. Completion-criteria holds (word-count heuristic for ~16 of 20 skills) re-ask until the user complies.

What the evidence says:

- **Self-determination theory applied to conversational agents** (Yang & Aurisicchio, CHI 2021): autonomy = "whether they had control over their conversation"; lack of it produces "a feeling of powerlessness" and "decreased engagement"; the design remedy is explicit options and user control. SDT's general claim: autonomy is supported "by providing users with sufficient choices and options."
- **Motivational interviewing** — already in Sage's own skill stack (`mi_readiness_ruler`) — formalizes this as the "menu of options" and "ask permission before advising" conventions. A 2024 systematic review (Computers in Human Behavior: AI) found MI-style chatbots produce higher engagement, reuse motivation, and effectiveness than low-technique ones.
- **Caveat honestly stated:** no RCT directly tests "named technique menu vs seamless steering" in a mental-health chatbot. The evidence is convergent (SDT theory, qualitative powerlessness data, MI literature, review-level findings) but indirect. This argues for shipping the offer construct **instrumented**, so Sage generates its own evidence (offer→acceptance rate).
- **Regulatory bonus:** an explicit, named, user-accepted coping exercise looks like a wellness tool the user chose. Silent auto-routing into a multi-step protocol looks like the AI "making independent therapeutic decisions" (the exact Illinois WOPR phrase). Consent-gating strengthens the wellness-not-therapy posture for any future market, and aligns with the spirit of UAE DoH transparency requirements (Abu Dhabi Responsible AI Standard 2025).

### 2.2 A persona defined almost entirely by prohibitions

`L0_persona` v1.4.0 is ~80% negative constraints: banned openers, banned "It sounds like / That sounds", banned "share", banned markdown/emoji/em-dash, WRONG/RIGHT pairs. The positive identity is two short paragraphs. The industry leaders do the opposite:

- **Claude** (published system prompts, Opus 4.5–4.8): personality is specified positively and at training depth ("character training" since Claude 3 — curiosity, warmth-with-pushback, anti-sycophancy as identity, not rules). Prompt-level pacing rules are few and positive: max one question per response; questions not every turn; "warm tone… still willing to push back… constructively."
- **ChatGPT Model Spec** (2025-12-18): warmth = "frank, genuine friendliness, rather than veering saccharine or lapsing into therapy speak"; "have conversational sense" = modulate length to the moment; advice must be "concrete, actionable, and pragmatic"; follow-up questions only when they serve the user's goal, "not merely to keep the conversation going."

You cannot out-ban your way to warmth. The banned-opener whack-a-mole (6 regex patterns, retry, vetted fallback) treats symptoms of a persona that has no positive register to fall back into. Each new ban (em dash, "share", reflective openers) removes a formula without supplying the voice that replaces it.

### 2.3 The scope wall and the interrogation rhythm

`L2_general_chat`: *"If the user raises a concern that is not about their own wellbeing, explore how they feel about it rather than engaging with the topic itself."* Next to ChatGPT — which the Model Spec explicitly forbids from deflecting ("I'm not a therapist" + hotline is a rated Violation; never quit the conversation) — this reads as evasive within two turns. Users compare directly; they will ask Sage the same things they ask ChatGPT.

Separately, nearly every Sage turn ends in a question (the L0 "just ask" guidance + skill steps that each probe). Claude's rule — don't ask questions every turn, never more than one — exists because relentless questioning reads as interrogation, not interest. Sage computes an `engagement` score (1–10) every turn and tracks `engagement_trajectory`, but only step_policy holds consume it; freeflow never adapts to it.

---

## 3. Recommendations

### R1 — Consent-gated skill entry: the "guided with optionality" construct (highest impact)

When `skill_select` matches (either tier), do not start step 1. Insert an **offer turn**:

> "What you're describing, the racing thoughts before bed, is something there's a specific short exercise for. We could try it together, takes about five minutes. Or we can just keep talking. What would you prefer?"

Mechanics:
- New graph behaviour: skill match sets `offered_skill_id` instead of `active_skill_id`; a lightweight offer template (new L2 variant) names what was noticed + the technique in plain words + 2–3 options (try it / keep talking / something else). Acceptance (classified by intent_route next turn — natural-language yes, not buttons-only) promotes `offered_skill_id` → `active_skill_id` at step 1.
- Decline → freeflow, with a **no-re-pitch cooldown** (e.g., don't re-offer the same skill for N turns) so declining doesn't trigger nagging — the Harvard manipulation findings make re-pitching after a "no" the single most brand-damaging move available.
- **Exceptions where direct entry stays:** crisis path (unchanged, deterministic), `post_crisis_check_in` auto-select (clinical protocol), and arguably acute-distress somatic skills at high intensity (box_breathing at intensity ≥8) where MI itself supports being more directive — clinical call.
- Frontend can render the options as quick-reply chips later; the construct must work in pure text first.
- **Instrument it:** offer→acceptance rate per skill, completion rate of accepted vs (historical) auto-entered skills, decline→retention. This converts the unmeasurable "did the user want this?" into Sage's own evidence base — and is exactly the engagement-tracking the feedback asks for on the Chat pillar.

This also dissolves the L2_new_skill "without announcing it as a technique" directive, which should be retired — covert technique delivery is both the engagement leak and the regulatory liability.

### R2 — Rewrite L0 as a positive conversation grammar; demote bans to output_gate enforcement

Adopt the verified Claude/Model-Spec grammar as the spine of a new L0:

1. At most one question per response; some turns end with none (a statement, an observation, an offer).
2. Match length and energy to the user's message — short for short, never a paragraph for "I'm fine."
3. When asked for advice or input, be concrete, actionable, pragmatic (this is Option B `advice_request` — promote it; it is independently validated by the Model Spec).
4. Warmth with honesty: willing to gently push back; never pure validation (the GPT-4o sycophancy rollback and Replika "algorithmic conformity" findings are the two documented disasters of pure validation — for a wellness product this is a safety property, not just a style one).
5. Respect endings: when the user winds down, close warmly; never ask a question to prolong the conversation (verbatim Claude position, new in Opus 4.8 — the industry is strengthening this, not weakening it).
6. A short positive register description (the calm-attentive-person paragraph, expanded with 3–4 few-shot exemplar exchanges showing the voice, including one Khaleeji-register Arabic exemplar).

Keep the banned-opener regexes in output_gate as the enforcement backstop, but they stop being the persona's main content. Expect the banned-opener retry rate itself to drop — a model given a voice reaches for formulas less.

### R3 — Replace the scope wall with engage-then-bridge

Two substantive sentences on the actual topic, then a natural bridge to the person. Sage doesn't need ChatGPT's breadth, but it must not deflect. Edit `L2_general_chat`'s deflection clause; bound it (no multi-turn technical Q&A) rather than walling it. This is the cheapest fix on the list and probably the most visible in a Gitex demo, where visitors will absolutely test off-topic questions first.

### R4 — Close the engagement-signal loop in freeflow

`engagement_trajectory` is computed and unused outside step_policy. Add to the L2 composition (like `intensity_guidance`): if engagement is declining over 2+ turns or the user gives one-word answers — stop probing, shorten replies, offer concrete options or a graceful close. This is the "tracked" half of the feedback: the signal exists; wire it.

### R5 — Soften step-holding

Max one hold per step, then advance or offer an exit ("we can leave it there, or keep going — up to you"). Word-count completion criteria re-asking for elaboration reads as a form refusing to submit. Post-Gitex: extend LLM criteria eval beyond the current 4 skills, or relax holds to advisory for low-risk skills.

### R6 — Measurement guardrails (the GPT-4o lesson, codified)

- **Never** tune, train, or gate releases on thumbs/engagement signals. OpenAI shipped the April 2025 sycophancy regression because quantitative user-approval signals looked good while expert testers said the model felt "off"; they now call it "the wrong call" and class sycophancy as a mental-health safety concern.
- Engagement metrics (return rate, session depth, offer-acceptance, voluntary skill completion) are *diagnostics* reviewed alongside clinical-quality review — the clinical gate always wins.
- Add a sycophancy/over-validation eval to the quality-log review (OpenAI's stated post-incident fix: they had no deployment eval tracking it). Sage's L0 anti-validation stance helps but is unmeasured.
- North-star candidate: **voluntary return + offer-acceptance rate**, not session length. Session-length maximization is the companion-app trap with documented legal-liability perception attached.

### R7 — Bilingual calibration caveat

Every verified finding is English/Western-market. One-question-per-turn pacing, directness norms, and hospitality language may calibrate differently in Khaleeji Arabic. The offer construct (R1) needs its own Arabic phrasing review (the existing cultural_overrides + Arabic-example-first conventions cover the mechanism); treat conversational-grammar transfer as an open item for the clinical/cultural reviewers.

---

## 4. What explicitly stays

- The deterministic crisis layer, S1/S3 OR-fusion, S7, crisis_response bypassing the LLM — every failure case studied (Replika SI conformity, Character.AI, GPT-4o) argues for it, and the generalists are building their own versions of it.
- The 20+ skill library and clinician sign-off pipeline — this is the moat; Illinois-style regulation makes un-overseen therapeutic content the liability, and clinician-reviewed structured content the defensible asset.
- output_gate audit, PDPL trail, clinician review queue.
- Long-term: Therabot and Slingshot Ash (Qwen3-235B backbone, clinician-comparison reward model weighted above user feedback, explicit anti-dependency tuning, "trained to push back") both show the end-state is **model-level** character for therapeutic dialogue. That is a post-POC consideration (fine-tune/character-train the responder on Sage's clinician-approved dialogues), not a Gitex one. Notably Ash's design philosophy — push back, end long sessions, direct users toward real-world relationships — matches the direction of R2/R6.

## 5. Suggested sequencing

| Priority | Item | Surface | Risk |
|---|---|---|---|
| Pre-Gitex | R3 scope-wall softening | L2_general_chat edit | Low; clinical review of wording |
| Pre-Gitex | R2 L0 rewrite | L0_persona v2.0.0 | Medium; needs banned-opener regression run + clinical review |
| Pre-Gitex | R1 offer gate (Tier-2 matches first, Tier-1 acute skills exempt) | skill_select + new L2 offer template + intent_route acceptance handling | Medium; Rule 1 control-layer change, two sign-offs like Option B |
| Pre-Gitex | advice_request Option B promotion (already specced) | intent_route + L2 | Already pending two sign-offs |
| Post-Gitex | R4 engagement-adaptive freeflow, R5 hold softening, R6 sycophancy eval | composer, skill_executor, eval harness | Low–medium |
| Post-POC | Model-level character (fine-tune on approved dialogues) | training | High; major effort |

All control-layer changes (R1, R2, R3) follow the existing governance path: Rule 1 engineering approval + clinical review, same as `advice_request` Option B.

---

## Appendix: key verified sources

- Anthropic published system prompts (Opus 4.5–4.8): docs.anthropic.com/en/release-notes/system-prompts — one-question rule, anti-over-reliance, never-prolong, warmth-with-pushback, crisis behaviour (no safety-assessment questioning; express concern + resources).
- Anthropic, "Claude's Character" — character training at alignment-finetune stage since Claude 3.
- OpenAI Model Spec 2025-12-18 — warmth definition, conversational sense, mental-health repertoire (deflection = Violation), follow-up-question rule. Note: one widely-repeated anti-sycophancy "firm sounding board" claim was REFUTED 0-3 against the live spec; re-verify any Model Spec quote before reuse.
- OpenAI sycophancy postmortems (Apr–May 2025): sycophancy-in-gpt-4o; expanding-on-sycophancy.
- OpenAI Oct 2025: strengthening-chatgpt-responses-in-sensitive-conversations (170+ clinicians, 60 countries, 65–80% non-compliance reduction, distress router).
- De Freitas et al., HBS WP 26-005 (arXiv 2508.19258) — companion-app manipulation audit; 14× engagement via reactance; Flourish 0%.
- Zhang et al., CHI 2025 (arXiv 2410.20130) — Replika harms, algorithmic conformity.
- Heinz et al., NEJM AI 2025 (AIoa2400802) — Therabot RCT.
- Hua et al., World Psychiatry 2025 (wps.21352) — rule-based vs LLM evidence base.
- Im & Woo, JMIR Mental Health 2025 (e78340) — scripted/hybrid/generative taxonomy + retention data (Wysa 33% at 2 weeks; Woebot-SUD ~50% attrition; Limbic Care NHS dropout −23%).
- Yang & Aurisicchio, CHI 2021 (SDT for conversational agents); Beatty et al. 2022 (Wysa alliance); Farzan et al. 2025 (PMC11904749, alliance review).
- Darcy et al. 2021 (Woebot bond, n=36,070); telehealth.org Woebot shutdown analysis (regulatory + business model, not clinical failure).
- DLA Piper Aug 2025 (Illinois WOPR, Utah HB 452, Nevada, NY); Fortune 2026-01-08 (Character.AI/Google settlements).
- Slingshot AI/Ash: nebius.com customer story (architecture, reward stack — vendor-channel, flagged), Hemingway Report (anti-dependency design).

Known gaps: no direct RCT of choice-menus vs seamless steering in mental-health chatbots; Ash retention numbers vendor-reported; conversational-grammar transfer to Khaleeji Arabic unvalidated.
