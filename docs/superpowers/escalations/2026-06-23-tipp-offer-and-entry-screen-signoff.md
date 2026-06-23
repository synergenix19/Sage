# Clinical Sign-off — DBT TIPP offer eligibility (F3) + TIPP entry-screen consent & hold-ceiling (F4)

**Date:** 2026-06-23
**Severity:** Sign-off blocker. F3/F4 code is HELD pending this decision.
**Owner / action required:** Clinical lead — confirm or correct the three encoded thresholds below. Engineering implements only the affirmed values.
**Source:** Nabala Hamdan prod RCA, 2026-06-22 (session `aa0a9256`): a frustrated parent ("trying to get my kids to calm down") was offered DBT TIPP — cold-water immersion + intense exercise — via a sub-threshold semantic match (0.4791), and the cold-water safety screen then re-asked on every "okay sure" / "lets start".
**Relationship to prior decision:** extends the [2026-06-13 acute-substitution decision](./2026-06-13-acute-substitution-redecision.md), which already excluded `dbt_tipp` from the acute `substitute_pool` for its temperature/intense-exercise cautions. F3 carries that same caution principle to the **offer** path; F4 fixes the safety screen's advancement and adds a re-ask ceiling.

**Why this needs your signature and the other RCA fixes did not:** the already-shipped fixes (dropped-summary, picks-A-gets-B) had no defensible clinical reading — they were determinism/assembly bugs. These two encode clinical judgements: *when is TIPP appropriate to offer*, and *what counts as valid consent to proceed on a physical-safety screen*. Your signature is what makes the encoded thresholds conformant, not a checkbox on top of them.

---

## What is being signed — three decisions

### Decision 1 (F3) — DBT TIPP is not offered via semantic ranking; only on explicit request
**Today:** the `default_offer` rule offers the top-2 semantically-ranked skills with no clinical-appropriateness filter, so general overwhelm vocabulary can surface TIPP. In the RCA it was offered to a parent who never asked for a physical reset.
**Proposed:** `dbt_tipp` is **excluded from the semantic-offer candidate set**. It remains offerable only on an **explicit keyword match** against its own `target_presentations` (e.g. "can't calm down", "breathing isn't working", "need an intense physical reset") — the same caution principle already signed for the acute `substitute_pool`.
**Assumption to affirm:** TIPP's temperature/intense-exercise profile means it should be a **user-requested / explicitly-matched** intervention, not a system-suggested default for non-specific overwhelm.

- [ ] Affirm as stated
- [ ] Affirm, and also gate keyword-matched TIPP offers below an intensity floor (offer only at `emotional_intensity ≥ ____`)
- [ ] Modify: ________________________________________

### Decision 2 (F4a) — Valid consent to proceed past the TIPP safety screen
**Today:** the `entry_screen` criterion correctly says "if nothing concerning is disclosed, advance" — but the shared criteria evaluator rejects short affirmatives ("okay sure", "lets start") as vague non-engagement, so the screen **holds even when no contraindication was disclosed**. That is the loop the user hit.
**Proposed:** on the TIPP `entry_screen`, an **unambiguous proceed-signal** ("lets start", "okay let's do it", "yes") with **no disclosed contraindication ADVANCES**. We do **not** require the user to explicitly deny each contraindication — they have already been shown "cold water + brief intense movement", and proceeding without disclosing a condition is consent to advance. A disclosed contraindication still redirects to the no-physical-requirement alternative (box breathing), unchanged.
**Assumption to affirm:** "saw the cold-water/intense-movement description, chose to proceed, disclosed no condition" is sufficient consent — explicit denial of each contraindication is **not** required.

- [ ] Affirm as stated
- [ ] Require explicit confirmation of absence (user must affirmatively deny contraindications before advancing)
- [ ] Modify: ________________________________________

### Decision 3 (F4b) — Hold-ceiling on the safety screen
**Today:** if consent is not cleanly parsed, the screen can re-ask **indefinitely** (the RCA showed it re-asking the cold-water question twice, with no stopping condition).
**Proposed:** after **N = 2** consecutive holds without a clear proceed-signal or a disclosed contraindication, the screen **stops re-asking and redirects to the no-physical-requirement alternative (box breathing)** with a brief acknowledgement — it never silently loops.

- [ ] Affirm N = 2, redirect to `box_breathing`
- [ ] Set N = ____
- [ ] Different exit (return to free conversation / re-offer menu): ________________________________________

---

## Reassurances — what these decisions do NOT change
- **Contraindication safety is not weakened.** A disclosed cardiac condition, pacemaker, arrhythmia, injury, physical disability, or disordered eating still **blocks** TIPP and redirects to box breathing. Decision 2 leaves that path intact; the cold-water / disordered-eating bradycardia caution stays exactly as written.
- These decisions change **when** TIPP is offered (Decision 1) and **how the screen advances / when it exits** (Decisions 2–3) — never **whether** the safety screen runs.

---

## Sign-off

**Clinical lead:** ________________________________   **Date:** ______________

- [ ] Approved as proposed
- [ ] Approved with the modifications marked above
- [ ] Rejected — reasoning: ________________________________________

**Engineering note:** implements only the affirmed values; the F3/F4 rule/skill commits are tagged `clinical-signoff: 2026-06-23-tipp-offer-entry` and must not merge until this file records *Approved*. The substitute/offer eligibility and the hold-ceiling N live in data (`skill_matching_rules.json` / `dbt_tipp.json`), so any value you set here is changed in data, not code.

---

# Clinical review and resolution — 2026-06-23

**Grounding fact (all three decisions orbit this):** cold-water facial immersion triggers the mammalian dive reflex, with an estimated **up to ~40% heart-rate reduction** — a large, fast physiological intervention. In individuals with preexisting cardiac pathology, sudden cold-water exposure can precipitate **arrhythmias, including atrial or ventricular fibrillation**. This is not a low-stakes "splash water" feature; the contraindicated subgroups face real physical risk. That is precisely why TIPP is the one skill in the set whose mis-indication has physical stakes. (Sources: dive-reflex physiology, US PTO/NIH; DBT TIPP self-help guidance naming heart conditions, eating disorders, beta-blockers, cold allergy/sensitivity — Kind Mind Psychology, Stevenson School, dbtselfhelp.)

## Decision 1 (F3) — APPROVED, with a REQUIRED match-tightening
Affirmed: `dbt_tipp` is excluded from the semantic-offer set. The cold-water piece is a crisis-survival tool for extreme arousal, not a default for non-specific overwhelm; a moderately frustrated parent is not the indicated population.
**Required, not optional:** the explicit-keyword gate must require **self-directed physical-reset intent**, not topical overlap with distress vocabulary — otherwise the false-positive simply moves from the semantic path to the keyword path. The current `target_presentations` reproduce the incident: they include topical terms ("overwhelmed", "can't calm down", "cant calm down", "losing control", "I can't handle this", "I'm losing it") that match the original parent phrasing. These must be removed/demoted; keep only intent-bearing requests ("need an intense physical reset", "need something stronger than breathing", "breathing isn't working", "TIPP", "cold water technique").
**Intensity:** NOT a hard floor — inferred `emotional_intensity` is noisy and must not deny a genuine request. Low inferred intensity plus context ("my kids") may act only as a **secondary guard that downgrades a loose keyword hit**, never as the sole gate.

## Decision 2 (F4a) — RESOLVED to bundled named-contraindication attestation (contingency verified)
Parser fix: AFFIRMED — a clear proceed-signal ("okay sure", "lets start") must be recognised as consent; rejecting it as vague is a defect.
**Contingency check (clinician's instruction, now verified in code):** the current entry screen shows the user only the ACTIVITY — *"anything physical worth mentioning? This technique involves cold water and some brief intense movement"* — and the step instruction explicitly says **"Do not list contraindications."** The at-risk conditions are named only in the model-facing instruction, never to the user.
**Therefore:** passive non-disclosure is too weak. The at-risk users (arrhythmia, disordered eating, on beta-blockers) will not connect their condition to "cold water on the face" unless told. The screen must **surface the named contraindications** (heart condition / arrhythmia / pacemaker / on beta-blockers / eating disorder / cold sensitivity) and require a **single bundled acknowledgment** to advance: *"None of these apply — start"* vs *"One applies — show me box breathing."* One tap; not a per-condition interrogation; does not reintroduce the loop.
**This consciously reverses an existing design choice.** The current "Do not list contraindications" instruction (cognitive-load protection) is overridden in favour of legibility, because the tool is unsupervised and the at-risk users are exactly those who will not self-identify. A reasonable clinician could hold the opposite (prominent warning + non-disclosure) as a crisis-friction tradeoff; the signer is choosing attestation.

## Decision 3 (F4b) — APPROVED (N=2 + box breathing), with two constraints
Affirmed: after **N=2** holds without clear consent or a disclosed condition, stop and redirect to `box_breathing`.
1. Redirect tone is **non-punitive** ("Let's try box breathing instead — no equipment needed"); the user must not feel they failed a test.
2. A **disclosed contraindication exits immediately on the first turn** and does **not** count toward N. The ceiling governs ambiguous/unparsed consent only, never someone who named a condition.

## Cross-cutting (signer should be comfortable with this)
All three gates lean on inferred `emotional_intensity` and text matching against distress vocabulary — and the original failure WAS a matching/threshold artifact (a 0.4791 sub-threshold semantic match surfacing a high-risk skill). Tightening rules on top of an unreliable intensity signal can relocate the false-positive rather than close it. The package fails safe at each step only as the sequence: **explicit intent-bearing request to reach TIPP at all (D1) → named-contraindication attestation to start (D2) → bounded, graceful exit if consent is unclear (D3).**

## Recorded outcome
- [x] Approved with the modifications recorded above (D1 + required match-tightening; D2 resolved to bundled attestation, reversing "do not list contraindications"; D3 N=2 with the two constraints).

**Reviewing clinician (name):** Rohan   **Date:** 2026-06-23

*Audit-trail transparency note:* "Rohan" is also the git-commit identity and the product owner who relayed this review (`rohan@synergenix.ai`). This signature stands as an independent clinical sign-off **iff Rohan is the credentialed clinical lead**. If signed in a product-owner capacity, it is a dual-hat self-approval and should be countersigned by an independent clinician before external pilot exposure — flagged here per the project's admin/self-approval disclosure convention, not to question the review (the relayed clinical content — dive-reflex physiology, DBT contraindication norms, BETA/trauma-informed/bioethics reasoning — was clinical-grade).
