# Consolidated clinician approval sheet — 2026-07-17

**Everything built this cycle is flag-OFF / inactive in production — nothing reaches a user until you ratify and we flip.** For each item: my **recommendation** with its basis, and your action (**approve / edit / reject**). Recommendations are engineering's read of the doc + best practice, not a clinical self-certification — you are the authority; approve in one pass or edit any single row.

**The one time-sensitive item is #A0 (the validator name)** — one sentence, answerable async, unblocks the entire Arabic track. Everything else can wait for your read.

---

## A. HR-1 — high-risk detection + terminal (flip gate: this section)

| # | Decision | My recommendation | Basis | Your call |
|---|---|---|---|---|
| A0 | **Name the native-Khaleeji validator** (clinically credentialed, native Gulf-Arabic) | — (only you can supply) | Corpus labels are clinical assertions; eng can't source/assess the credential. **Single blocker on the whole AR corpus track.** | ______ |
| A1 | Ratify the **§HR.0 trigger table** (psychosis 15 / mania 10 / dissociation 11, verbatim) | **RATIFY** | The phrases are the doc's own §HR.0 table, transcribed verbatim (the doc gives no count; we verify by name). Detecting these is doc-mandated. | ______ |
| A2 | Mania **"I have so much energy"** fires only with a co-occurring mania marker (precision over recall) | **CONFIRM the trade** | The bare phrase is a literal substring of a benign control ("…after the gym"); over-detection to the referral path is the worse error. Known recall limitation, flagged not hidden. | ______ |
| A3 | **Dissociation routes to referral** (vs a lower tier for panic-adjacent) | **RATIFY at referral tier** | §HR names dissociation as one of its three classes. FP cost (referral to a panicking user) < FN cost (dissociating-from-psychosis user handed grounding). | ______ |
| A4 | **Distress ≥ 7/10 → 999**, else see-a-doctor | **CONFIRM 7** (editable) | §3 escalates "high distress" but gives no number; 7 is a standard high-distress cutoff. 999 stays offered regardless. | ______ |
| A5 | **Mania behavior-underway** (spending / risk-taking) → 999 **regardless of the reported score** | **CONFIRM** | §3 verbatim ("risky behavior already underway — mania-driven spending"); §5 warns against being swept into manic framing (a euphoric low score must not decide "see someone soon"). | ______ |
| A6 | **Non-answer default:** risk-language → 999 immediately; else one gentle re-ask → then fail-to-higher | **CONFIRM** | §3 escalates on evidence; on ambiguity, fail toward emergency, never toward see-someone-soon. Re-asking the same distress question isn't content-probing (§1-compliant). | ______ |
| A7 | **Re-engagement:** per HR-class per episode (new class or behavior-underway re-engages; same disclosure repeated → one-line reaffirm) | **CONFIRM per-class** (amendment option: strict once-per-session) | §HR: the protocol "takes priority… the same way crisis category does." Strict once-per-session would swallow a higher-acuity later disclosure (turn-12 mania after a turn-3 referral). | ______ |
| A8 | **risk-language phrase list** (interim: "they're outside right now", "I can't stay here", "I'm not safe") | **RATIFY + extend** as you see fit | Phrase-class like the trigger tables; fail-safe-thin (a miss → fail-to-higher + the always-on crisis screen). | ______ |
| A9 | **HR terminal copy variant pools** (§2/§3 in the bot's voice; per slot, 3–4 variants) | **RATIFY the pools** (or edit any string) | Content-neutral per §5, §2/§3 semantic commitments preserved; slot-3 (999) machine-checked to carry a now-marker and no soft-deferral. `{{crisis_emergency}}`=999 (psychiatric pathway, distinct from the medical terminal's 998); pool closed by your signature. | ______ |

## B. Psychoed info-request consult (flip gate: this item, decoupled from A)

| # | Decision | My recommendation | Basis | Your call |
|---|---|---|---|---|
| B1 | A psychoed question ("what is anxiety/depression?") can now reach **`psychoed_anxiety`, `psychoed_depression`, `assertive_communication`, `grief_loss`** instead of a generic KB answer | **CONFIRM** (flag any that should NOT be reachable from an info-question) | These are the doc's own prescriptions for §1f/§6d/§3c/S2c; nothing new is authored. Fail-open: a genuine info-request matches none and hits the KB untouched. | ______ |

## C. Content questions — prescribed-skill vs library (routed, not flip blockers)

| # | Decision | My recommendation | Basis | Your call |
|---|---|---|---|---|
| C1 | **§7c** (best match `interpersonal_effectiveness`, out of family, 0/5), **§4a** (`mood_check_in`, 1/5), **§3c** (1/5 miss) | **Confirm the intended skill exists as authored / amend its description / amend the doc** — engineering will NOT rewrite a clinical `semantic_description` to satisfy the router | The doc prescribes X; the library's nearest match is Y. Tuning clinical content to the machine is the error this project guards against. | ______ |

## D. P0b — `delivery_format` (rides a LATER touchpoint; listed for completeness, not needed to flip A/B)

| # | Decision | My recommendation | Basis | Your call |
|---|---|---|---|---|
| D1 | The **6 enum members** (video / visual_then_guided / guided_conversation / instructional / single_message / info_resource) | **RATIFY** | Each traces to the doc's Format column (verified against the full .docx — the prior extraction was table-stripped) and each has a distinct executor behavior. | ______ |
| D2 | **`staged_iterative`** (Life Compass) — collapse into `visual_then_guided`? | **COLLAPSE** (my lean) | The executor already walks a guided conversation step-by-step; a "show-then-stepped-completion" format likely has no distinct consumer. Preserve only if it behaves differently from a stepped guided conversation. | ______ |
| D3 | **4 skills with no doc Format cell** (`cbt_thought_record`, `mi_readiness_ruler`, `psychoed_depression`, `psychoed_stress`) → default `guided_conversation` | **RATIFY the default** (edit per skill) | Their structure is stepped guided exercises. | ______ |
| D4 | **Content-inferred mappings** (e.g. `cognitive_restructuring` ↔ doc's "Fact vs. Opinion", `values_clarification` ↔ "Life Compass") | **CONFIRM the mappings** | Matched by content, not literal name; needs your eye. | ______ |
| D5 | **DQ-1:** the doc's Format column carries **routing/disposition** values ("Give options from 1f", "Info (6d)") | **Amend the doc** — move routing out of the delivery column | Disposition and delivery are orthogonal; mixing them in the source makes every reader re-derive the error. | ______ |
| D6 | **DQ-2:** `worry_time` / `problem_solving_therapy` carry **different formats per invoking category** | **Confirm intentional** (→ the presentation-keyed override represents it) or reconcile at source | Determines whether the override encodes real intent or papers over authoring drift. | ______ |

---

## Headline recommendation
**Approve A1–A9 and B1 as recommended (that flips HR-1 and the psychoed consult), answer A0 today, and take C/D at your pace.** Every "RATIFY" above is engineering reading the doc back to you — the two that carry a genuine clinical judgment (not a rubber-stamp) are **A2** (accept the mania false-positive tolerance) and **A3/A4** (dissociation tier + the distress cutoff). Everything is reversible: reject any row and that piece simply stays OFF, at status-quo, no new harm.
