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
