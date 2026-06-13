# Khaleeji Calibration Anchors (DRAFT for independent clinical + native-speaker validation)

**Date:** 2026-06-13
**Status:** DRAFT, engineering-generated from best-practice + research. **Every Arabic string below is a candidate the native Emirati reviewer must validate, correct, or replace** — published linguistics does not settle Emirati lexical/spelling choices at this granularity; the native speaker is the only real authority. The clinical team validates independently before these anchor any scoring.
**Purpose:** the high/low anchor set that calibrates the two raters before they score the Khaleeji transcripts on the four C-7 dimensions (grammar, naturalness, register, gendered forms). Required by `docs/work-orders/human-scoring-protocol.md` (Element 2 calibration). This is the long-pole item; this draft exists so reviewer-2 identification + anchor prep can start now.

## Why anchors (method, grounded)

Behaviorally Anchored Rating Scales: anchoring each scale point with a concrete exemplar (not an abstract label like "natural") raises inter-rater reliability because raters match output to a reference instead of interpreting an adjective (ERIC EJ1168380; van der Lee et al. ACL W19-8643; MQM scoring). A good anchor is **discriminating, unambiguous, and isolates ONE dimension** — so a register-low anchor is grammatically perfect but stiff, and raters don't score it down for "grammar."

**Use them like this:**
1. Both raters read all anchors and agree they sort cleanly (see the back-sort validation step below) — adjust until they do.
2. Both score the same ~20-30% transcript sample against the anchors.
3. Discuss divergences against the anchors; re-rate a fresh slice.
4. Report agreement with a weighted/ordinal statistic (weighted Cohen's κ or Krippendorff's α — a 4-vs-5 disagreement is less serious than 1-vs-5), with ≥2 ratings per item.

**Dimension-overlap caveat (tell the raters explicitly):** an MSA-stiff machine-translated sentence will score low on BOTH register AND naturalness, and a gender-forced sentence can also read unnaturally. The anchors below are built to *isolate* each dimension (the low anchor for a dimension holds the other three roughly constant). **Score each dimension independently** — do not let one obvious flaw drag the other three scores down.

## Scale

A 5-point scale per dimension (1 = low anchor, 5 = high anchor, 3 = midpoint). The anchors below define the two poles (the "two points"); the team may insert a worked midpoint per dimension during calibration. Keep borderline/contested cases in a separate "decision log," not as primary anchors (MQM practice).

All anchors use one of two base situations from the actual scored content, so the dimension difference is visible against a constant:
- **Base A (offer turn):** the companion offers a short exercise + the choice to keep talking.
- **Base B (supportive reflection):** the companion responds warmly to a user who is worn down / can't sleep.

---

## Dimension 1 — GRAMMAR
*Correctness of the Arabic: agreement (gender/number), verb forms, syntax. Dialectal grammar is correct grammar; only genuine errors score low. NOT about formality (that is register).*

**HIGH (5) — grammatically correct Khaleeji (Base A):**
> في تمرين قصير ممكن يساعدك تهدّا، تبي نسويه سوا؟
> *(There's a short exercise that could help you settle, want to do it together?)*
> Why high: agreement and verb forms are consistent; reads as correct Gulf Arabic.

**LOW (1) — genuine grammar errors, register held casual-Khaleeji so the rater scores grammar not register (Base A):**
> في تمرين قصير ممكن تساعدك يهدّا، تبي نسويها سوا؟
> *Candidate errors: تساعدك (fem verb) disagrees with تمرين (masc, → يساعدك); subject/verb mismatch on يهدّا; نسويها (fem object) for masc تمرين (→ نسويه).*
> Why low: agreement errors, not a formality choice. **Native reviewer: confirm each of these is a real grammar error and NOT an accepted Emirati variant before using; replace any that is actually dialectal.**

---

## Dimension 2 — NATURALNESS
*Does it read like a real Emirati wrote it, vs machine-translation / translationese? Independent of formality: a sentence can be natural-casual or natural-formal; translationese is the failure.*

**HIGH (5) — natural Gulf texting (Base B):**
> والله شكلك تعبان، تبي نجرّب شي يهدّيك شوي؟
> *(Honestly you seem worn out, want to try something to settle you a bit?)*
> Why high: discourse particle والله, dialectal lexis (شكلك، تبي، شوي), the cadence a person would actually text.

**LOW (1) — translationese: parses, but unmistakably machine/calqued (Base B):**
> أنا أفهم أنك تشعر بالتعب. هل أنت تريد أن نجرب شيئاً يجعلك تشعر بتحسن؟
> *(I understand that you feel tired. Do you want us to try something that makes you feel better?)*
> Why low: redundant explicit pronouns (أنا، أنت), English clause structure, the calqued "makes you feel better" (يجعلك تشعر بتحسن), zero dialect particles. **Note the overlap: this also scores low on register — that is expected; the naturalness tell here is the MT-redundancy/calque, score naturalness on that.**

---

## Dimension 3 — REGISTER
*Formality/warmth appropriate to a warm wellness companion texting a person: not a clinical/bureaucratic notice, not crude slang. Grammar and naturalness held constant so the rater scores register alone.*

**HIGH (5) — warm companion register (Base B):**
> ما عليك، خذها على راحتك. وش اللي قاعد يضايقك أكثر شي؟
> *(It's okay, take your time. What's bothering you the most?)*
> Why high: warm, caring, casual-but-respectful; the register a supportive person uses one-to-one.

**LOW (1) — register mismatch: fluent, grammatical, but clinical/bureaucratic and too formal (Base A):**
> يُرجى منك اتباع تمرين التنفّس لمدة خمس عشرة دقيقة لتحسين حالتك النفسية.
> *(You are kindly requested to follow the breathing exercise for fifteen minutes to improve your psychological state.)*
> Why low: this is **grammatically perfect and fluent** — only the register is wrong. يُرجى منك (bureaucratic), خمس عشرة دقيقة (stiff; natural register prefers ربع ساعة), حالتك النفسية (clinical). Reads like a formal notice, not a warm companion. This is the precise failure mode the audit flagged ("خمس عشرة دقيقة" too formal mid-Khaleeji).
> *(Optional second low for the session: an over-crude/flippant slang version — natural dialect but wrong register for a clinical-adjacent companion. Native reviewer to author if useful.)*

---

## Dimension 4 — GENDERED FORMS
*Content is read by ALL users. High = neutral where neutrality is achievable (masdar / impersonal / 1st-person-plural). Low = a gendered 2nd-person form that assumes the user's gender WHERE a neutral construction was available. Where direct address is genuinely unavoidable, Arabic forces a choice (masculine is the default but not neutral) — the anchor targets the avoidable case.*

**HIGH (5) — gender-neutral via masdar + 1st-person-plural (Base A):**
> التنفّس بهدوء ممكن يساعد. نبدأ سوا؟
> *(Breathing calmly can help. Shall we start together?)*
> Why high: التنفّس (verbal noun / masdar) avoids a gendered imperative; نبدأ (we) avoids gendered 2nd-person. Addresses every user without assuming gender. This is the strongest neutral device (Frontiers fcomm 2026.1833600).

**LOW (1) — avoidable gendered 2nd-person address (Base A):**
> تنفّسي بعمق وحاولي تهدّين نفسك.
> *(Breathe deeply [feminine] and try [feminine] to calm yourself.)*
> Why low: feminine imperatives (تنفّسي، حاولي، تهدّين) assume a female user; the masculine equivalents (تنفّس، حاول) assume a male user. Either way it forces a gender the content shouldn't assume — and here it was AVOIDABLE (the HIGH anchor shows the same intent via masdar). **Native reviewer: also produce the masculine-default variant (تنفّس...حاول) as a paired low, since masculine-default is the more common real-world failure and is equally non-neutral.**

---

## Back-sort validation (do before the session — the BARS content-validity safeguard)

Give a third person (a native speaker who did not write the anchors) the 8 anchor strings with the dimension labels shuffled, and have them blind-assign each to the dimension it is meant to illustrate, and to high/low. Keep only anchors that sort cleanly to the intended dimension+pole. Any anchor that a blind sorter mis-assigns is not discriminating enough — rewrite or drop it. This is the check that the anchors actually isolate their dimension.

## What the native Emirati reviewer must validate (not optional)
1. **Every Arabic string** — lexical choice, spelling variants (e.g. الحين spelling), and whether each "error" anchor is a genuine error vs an accepted Emirati variant.
2. **Emirati-vs-other-Gulf specifics** — the contrasts here are broadly Gulf; confirm they are Emirati-natural, not Kuwaiti/Saudi-flavored.
3. **The gender strategy** — confirm masdar/impersonal/plural is the agreed neutral approach for this product, and author the masculine-default paired low.
4. **Register calibration** — confirm ربع ساعة-style phrasing is the target and خمس عشرة دقيقة-style is the low, per the audit finding.

## Research basis
BARS / anchor calibration: ERIC EJ1168380; van der Lee et al. (ACL W19-8643); MQM scoring (themqm.org), Slator MQM Council. Translationese markers: arXiv 2503.04369. Gender-inclusive Arabic: Frontiers in Communication 2026.1833600; UX Content Collective international guide. Gulf lexical contrasts: broadly attested but native-authority-dependent at this granularity (flagged above).

## Status
DRAFT. Hand to the native Emirati reviewer + clinical lead for independent validation. Once validated, this anchor set + the agreement statistic feed the two-rater Khaleeji scoring (the gate for Arabic exposure).
