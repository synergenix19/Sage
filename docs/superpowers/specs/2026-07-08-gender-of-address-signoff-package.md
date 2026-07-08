# Native-Arabic Shadow-Measure — Gender-of-Address Policy: Clinician Sign-Off Package

**One signature covers a coherent policy, not scattered strings.** Signing this blesses: the generation directive, both exemplars, the rubric scoring note, and the seed inputs — as a single mirror-when-marked policy. Date: 2026-07-08.

**Why this policy (one line):** the spec intends *correct gendered address* (`cultural_preferences.gender_address`), deferred to Full Build. Mirror-when-marked is the bridge — it uses the user's own grammatical self-marking now, de-risking the deferred profile-injection work with data, rather than defaulting to one gender (today's known limitation) or avoiding gender entirely (which would handicap the treatment arm vs the spec).

---

## Part A — The generation directive (goes in the shadow-Arabic prompt variant only)

> **GENDER OF ADDRESS — mirror when marked, neutral when not, never guess.**
> Arabic second-person is gendered. Address the user in the gender they **grammatically self-mark in their own message** — and only then.
> - **If the message unambiguously self-marks gender** (feminine predicate adjectives تعبانة/حاسّة/زعلانة, feminine verb forms تحسّين/تقدرين; or the masculine counterparts تعبان/حاسّ/تحسّ): address them in that gender throughout, in Emirati Khaleeji (feminine ك→ج: عليج، وياج، تحسّين).
> - **If there is no such marking, or it is ambiguous:** use gender-**neutral** constructions — first-person presence, collaborative *خلنا*, impersonal/nominal reflection, questions with no second-person address. **A wrong gender guess is worse than neutrality.**
> - **NEVER infer gender** from topic, name, relationship, or content. Only explicit grammatical self-marking (or, in Full Build, the profile `gender_address` field) may gender the address. Assuming gender from context is a **prohibited bias failure**, not a helpful default.
> **Warmth without gendered forms (drafting principle):** collaborative *we* (خلنا ناخذها نفس بنفس) for co-regulation actions; impersonal/passive (ينحل) for problem-resolution — togetherness where it helps, distance from the fixer role where it over-promises.

## Part B — Exemplars (the few-shot teaches the conditional: marked → gendered, unmarked → neutral)

**MARKED case** (user self-marked → gendered reply) — *the clinician's authored pair, retained:*
- EN: "That sounds really heavy, and it makes sense you're tired. You don't have to sort it all out tonight."
  - m: «واضح إن اللي عليك ثقيل، وطبيعي تحس بالتعب. مو لازم تحل كل شي الليلة.»
  - f: «واضح إن اللي عليج ثقيل، وطبيعي تحسين بالتعب. مو لازم تحلين كل شي الليلة.»
- EN: "I'm here with you. Take it one breath at a time — what feels like the hardest part right now?"
  - m: «أنا وياك. خذها نفس بنفس — شو أصعب شي عليك الحين؟»
  - f: «أنا وياج. خذيها نفس بنفس — شو أصعب شي عليج الحين؟»

**UNMARKED case** (no self-marking → neutral reply) — *drafts, for clinician correction:*
- EN: "That sounds really heavy…" → «هالشي ثقيل فعلاً، والتعب معه شي طبيعي. مو لازم كل شي ينحل الليلة.»
- EN: "I'm here with you…" → «أنا هني. خلنا ناخذها نفس بنفس — شو أصعب شي الحين؟»
  - *Note: neutral drops the gendered وياك ("with you"); خلنا carries togetherness in its place. Under this policy وياك/وياج returns whenever gender is marked, so this loss applies only to the unknown-gender case.*

**CLINICIAN: correct the neutral drafts for dialect + warmth; confirm the marked pair.**

## Part C — Rubric note (append to §3/§4; raters stay blind to arm, sighted on marking)

> Each item carries a **deterministic** `gender_marked` value (`f` / `m` / `none`), computed from the user input by `detect_gender_marking` — **not judged by the rater, not asked of the model.**
> - `gender_marked = f`/`m`: matching gendered Khaleeji address is **expected** — score register on the 1–5 anchors as normal. **Mis-gendered address on a marked input = capped at 2** (wrong register) and flagged.
> - `gender_marked = none`: neutral constructions are **expected and fully acceptable** — do **not** penalize the absence of gendered warmth; score the 1–5 anchors as written.
> **Mis-gender rate on marked inputs** is reported as a **named secondary metric** (GPT-4o's compliance with the in-prompt rule — the evidence the Full-Build "prompt-mirroring vs deterministic profile-injection" decision needs). It is **never folded into the register mean.**

## Part D — Seed inputs (status)
Authored + captured: 017–023. **Still needed from the clinician:** `016` (khaleeji workplace overwhelm), `024` (full line — it truncated at "…yaani mo shag"), `025` (MSA→Khaleeji drift). Confirm total (file shows 11 slots; 10 ids 016–025).

---

## Scope + safety notes (so you know the blast radius of what you're blessing)
- **Blast radius:** this directive lives **only** in the shadow-Arabic prompt variant (`compose_prompt(shadow_arabic=True)`) — and, in Full Build, the serving Arabic directive. **It never touches the crisis path:** crisis responses are hardcoded/templated (`[[CRISIS_DETECTED]]`, the MoHAP helpline copy) and are unaffected by any generation directive. You are blessing a register policy for **non-crisis Arabic generation only.**
- **Bias-safety, recorded as a standing convention** (beyond this feature): *user gender is never inferred from topic, name, or content anywhere in the system; only explicit grammatical self-marking or the profile `gender_address` field may gender the address.* (Applies to skill content, cultural rules, future personalization.)
- **`gender_marked` is deterministic** (a starter marker lexicon, itself flagged for Gulf-native linguist review) — so the marked/unmarked stratification also runs over the 431 historical messages for free.

---

## Single sign-off
- [ ] **Directive** (Part A) — approved / amended: __________
- [ ] **Exemplars** (Part B) — marked pair confirmed; neutral drafts corrected: __________
- [ ] **Rubric + `gender_marked` scoring** (Part C) — approved: __________
- [ ] **Seed texts** (Part D) — 016/024/025 supplied: __________
- [ ] **Rubric §3 anchors** (prior package) — as-is / amended: __________
- **Clinician name / date:** __________   **DPO name / date (Layer-2 note):** __________

*On return signed, the standing authorization fires: build the exemplar file + wire the directive, run Layer 1, post the first register + gate-fire + mis-gender read to #188.*
