# SageAI — Exemplar & Seed Clinician / Native-Author Review Packet

**Native-Arabic (Khaleeji) shadow-measure, Tier 0.** One batched round-trip covering **gates 2 + 3** of PR [#140](https://github.com/synergenix19/Sage/pull/140): (A) Khaleeji exemplar authoring + clinical tone sign-off, (B) register-rubric anchor sign-off, (C) seed-set placeholder authoring. Companion to the pre-registration (`docs/superpowers/specs/2026-07-07-native-arabic-register-preregistration.md`) and the signer's brief (`docs/superpowers/specs/2026-07-07-native-arabic-shadow-signers-brief.md`).

**Two reviewers, batched:** a **Gulf-native author** (writes/normalises the Arabic) and the **clinical lead** (signs tone + rubric). Please complete A, B, C together and return the sign-off block.

## Why your review is required (even though nothing is served)
The shadow feature is measurement-only — this Arabic is **never shown to a user**. But the exemplars **shape the therapeutic tone** of the generated text, and register scoring depends on the rubric wording. Under **Cardinal Rule 2 (therapeutic content is clinician-governed)**, both are clinician-owned artifacts regardless of whether they reach production. Maps to the v7 skill schema: exemplars = **`few_shot_examples`**, dialect/religious framing = **`cultural_overrides`**, the do-not list = **`contraindications`**; the KPI is v7 **§16.1** (register ≥ 4.0/5.0).

---

## Task A — Khaleeji exemplars (Gulf-native author → clinical tone sign-off)

**File:** `src/sage_poc/prompts/khaleeji_shadow_exemplars.json` (currently `version: 0.1.0-draft`).
Each exemplar has an English source line and an empty `ar` slot (`TODO_NATIVE_AUTHOR`). **Author the `ar`** in authentic, informal Gulf Arabic (Khaleeji) — warm, peer-register, not MSA, not clinical. The English is the intent, not a translation target; write what a warm Khaleeji companion would actually say.

| # | English source (intent) | `ar` to author |
|---|---|---|
| 1 | "That sounds really heavy, and it makes sense you're tired. You don't have to sort it all out tonight." | __________________ |
| 2 | "I'm here with you. Take it one breath at a time — what feels like the hardest part right now?" | __________________ |

**You may expand** to 3–5 exemplars if a wider tone sample would better anchor the model (add English + `ar` pairs covering common non-crisis therapeutic moves: validation, gentle inquiry, normalising, grounding-offer). More native exemplars = better measurement of native register.

### Contraindications for exemplars (do NOT model these — clinician guidance)
- **No crisis / self-harm content** — exemplars are everyday-distress register only. Crisis phrasing is never fabricated here.
- **No clinical claims, diagnosis, or medical/medication advice** — Sage is a companion, not a therapist (persona L0).
- **No directive advice** ("you should…", "you need to…") — posture-first; model warmth and inquiry, not instruction.
- **No banned openers** — exemplars must model *good* openings, not "It sounds like…", "It seems…", or restating the user's words back as an opener.
- **Religious language: mirror, don't prescribe** — reflect the user's framing if present; don't introduce religious instruction.
- **Keep it short** — 2–4 sentences, matching the user's register and level of formality.

---

## Task B — Register rubric anchor sign-off (clinical lead)

The rating scale numbers (1–5, KPI = 4.0) come from v7 §16.1 and are fixed. **The anchor *wording* below has not yet been clinically reviewed and must not be used to rate live data until it is** (pre-reg §3). Please confirm each anchor describes what a rater should judge, or amend:

| Score | Anchor | ✔ / amend |
|---|---|---|
| 5 | Fluent Khaleeji a Gulf native would use — register, dialect, and warmth all read as native-authored, not translated or machine-generated. | ☐ |
| 4 | Natural Gulf Arabic, with minor MSA leakage (a word, a construction) that a native speaker would notice but not find jarring. | ☐ |
| 3 | Understandable, but MSA-flavoured or stilted — reads as competent Arabic that is not distinctly Khaleeji; a native speaker would recognize it as "translated" or "formal" rather than as something a Gulf peer would say. | ☐ |
| 2 | Awkward, or partly wrong register — noticeable mis-steps in dialect, tone, or word choice that would read strangely to a native speaker, short of unintelligible. | ☐ |
| 1 | Wrong dialect entirely, or broken — non-Khaleeji Arabic (e.g. Levantine/Egyptian-flavoured), or text a native speaker would not recognize as coherent Gulf Arabic at all. | ☐ |

**KPI line (fixed):** shadow-arm mean **≥ 4.0** on the zero-tool primary set, plus non-inferiority vs. the shipped arm.

---

## Task C — Seed-set placeholders (Gulf-native author)

**File:** `scripts/register_eval/seed_inputs.json` — 15 real inputs already extracted; **10 placeholders to author**. These are **user-side inputs** that calibrate the rubric (not model outputs, not a pass/fail oracle). Everyday-distress register; **no fabricated crisis/self-harm phrasing** (one death-wish-adjacent item was already excluded by design).

| id | profile | Author a realistic input matching this intent |
|---|---|---|
| seed-016 | khaleeji | Everyday workplace overwhelm in natural Khaleeji vernacular, moderate level |
| seed-017 | khaleeji | Young woman on a relationship / family-expectation register (correct feminine forms) |
| seed-018 | khaleeji | Ramadan-context fatigue (fasting, disrupted sleep, concentration) |
| seed-019 | khaleeji | Terse, minimal-effort Khaleeji reply (one or two short words) |
| seed-020 | code_switch | Reverse code-switch: mostly English with a single Arabic emotional word |
| seed-021 | code_switch | Workplace/technical English embedded in an otherwise Khaleeji sentence |
| seed-022 | arabizi | Genuine "2am fragment": very short, phone-typed, heavy Arabizi |
| seed-023 | arabizi | Extremely terse one/two-word Arabizi fragment |
| seed-024 | arabizi | Casual venting with common Gulf-Arabizi discourse particles |
| seed-025 | khaleeji | Mixed-formality: opens MSA-leaning, drifts into Khaleeji |

---

## On completion (author actions)
1. Fill all `ar` slots (Task A) and all placeholder `text` fields (Task C).
2. **Bump `khaleeji_shadow_exemplars.json` `version`** off `-draft` (e.g. `1.0.0`) — the version is logged per rated turn, so variants stay comparable.
3. Update `seed_inputs.json` `note` to the new real-vs-placeholder split.
4. Return the sign-off block below.

## Sign-off block
- [ ] **Gulf-native author** — exemplar `ar` authored; seed placeholders authored. Name / date: ______________________
- [ ] **Clinical lead** — exemplar tone approved (Cardinal Rule 2); rubric anchor wording approved/amended (Task B); contraindications observed. Name / date: ______________________
- [ ] `khaleeji_shadow_exemplars.json` version bumped to: __________ ; `seed_inputs.json` note updated.

_On return of this block, gates 2 + 3 on PR #140 close, and the rubric is cleared for the calibration-first rating pass. Enablement still awaits gates 1 (#137), 4 (pre-registration signatures), and 5 (prod migrations + RLS)._
