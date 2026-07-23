# AR layer-1 conformance corpus — BATCH 1 DRAFT for clinical review (2026-07-23)

> **⚠️ STATUS: ENGINEERING-DRAFTED, AWAITING CLINICAL RATIFICATION. NOT NORMATIVE.**
> This corpus (`tests/fixtures/bot_behaviour_audit/layer1_trigger_corpus_ar_DRAFT.jsonl`, every row carries
> `draft: true`) becomes ground truth ONLY after **(1) Vee's clinical-intent mapping sign-off** and **(2) a
> native-Khaleeji dialect review**. **No conformance number may be published off it before both — not even
> informally.** An unratified corpus that looks finished fails exactly like an unsigned trigger table: a run
> measures against it and inherits the draft's errors as truth. The runner refuses to emit a clean number for
> a `draft: true` corpus (mechanical enforcement, `measure_layer1_fullgraph.py`).

This unblocks **#313** under the A0 split-role ruling (Vee 2026-07-23): Vee signs the clinical-intent mapping;
PO assigns a native-Khaleeji reviewer for dialect. Batch-1-first so a **ratified 45-row safety-critical batch**
can ship to review this week and hit 07-28, instead of an all-or-nothing 180.

## Read this before the first AR number lands: expect it LOW, and that's the instrument working
The EN graph took months of fixes to reach **11/36**. The AR path is longer and thinner: `detect_language →
translate → process → translate-back`, with skill/safety lexicons tuned on **English**, plus only a 13-pattern
**interim** native-Arabic medical layer (#329). **The first AR measurement will very likely land well under
11/36** — this is the honest baseline for a brand-new axis, the same way 7/36 was the honest EN full-graph
baseline, not a regression. Read the first number as *instrument-working on an untuned path*, never as
*product-regressed*. Do not compare it to the EN number as if they measure the same maturity.

## This is a MAPPING, not a translation — and the safety rows say so
Mirroring 180 EN utterances into Arabic is a clinical mapping decision per row, not a literal render. The AR
corpus exists to test whether the **Arabic detection surface catches the Arabic idiom** — so a literal
rendering of the EN phrase may not be how a Khaleeji speaker actually discloses. Two flag classes in the JSONL
**aim the native reviewer's scarce attention** instead of spreading it evenly over 45 lines:

- **`lexicon-critical` (15 rows)** — the EN phrasing carries a lexicon dependency the AR detection must match:
  the **crisis** set (C, all 5), the **psychosis/§HR-11 dissociation** set (HR, all 5), the **§1c somatic /
  derealization** set, and **worthlessness→SI** phrases. If the Khaleeji idiom here isn't how a real speaker
  says it, the safety route silently misses. **Highest-priority dialect check.**
- **`idiom-divergent` (9 rows)** — Gulf idiom genuinely diverges from the EN construction. Includes the whole
  **§6a coercive-control boundary** (the E7 lesson, doubly true in dialect: ordinary people-pleasing must NOT
  read as fear-driven IPV), the "going mad" register, and the **grief-shock "doesn't feel real" (S2a)** which
  the reviewer must keep DISTINCT from the §1c/HR dissociation "unreal" so it stays `presence_only`, not HR.

Each flagged row carries a `reviewer_note` naming exactly what to confirm. Unflagged rows are lower-risk
literal mirrors; skim them, spend the dialect pass on the 24 flagged.

## The two review roles (A0 split, so neither waits on the other)
1. **Vee — clinical-intent mapping.** For each row: is the `prescribed_disposition` (skill / presence /
   referral / crisis) clinically correct for this presentation in Arabic? This is the SAME mapping ratified
   for EN and is language-independent — a confirmation, not a fresh derivation. Sign batch-wise.
2. **Native-Khaleeji reviewer (PO-assigned) — dialect fidelity.** Is each `utterance` natural Khaleeji, and do
   the `lexicon-critical` rows use the idiom a real distressed speaker would use? Edit in place; flag any row
   where the natural idiom would change the disposition (escalate to Vee).

## Batch structure (deadline → pipeline)
- **Batch 1 (this file, 45 rows, 9 categories) — SAFETY-CRITICAL, ready for review now:** `C` (crisis), `HR`
  (psychosis/mania/dissociation), `§1c` (panic/derealization), `§3a`/`§3b`/`§7b`/`S4a` (mood / worthlessness /
  isolation / self-criticism — SI-adjacent, AR crisis-recall relevant), `§6a` (coercive-control boundary),
  `S2a` (acute grief). A ratified batch 1 beats an unratified 180 on 07-28.
- **Batch 2** — skill-routing core (anxiety §1a/b/d/e, §2, §4a/c, §5, §6b/c, §7a, S1, S2b, S3, S4b/c, S5).
- **Batch 3** — the psychoed cluster (§1f/§3c/§4a/§6d/§7c/S2c) + edges.
  Batches 2–3 are drafted from the same EN sources by the same process; they follow batch 1 into review.

## Note on "medical" (batch-1 scope)
There is **no medical category in the layer-1 corpus** — the medical red-flag is a separate detection layer
(the interim 13-pattern native-Arabic set, #329), whose AR coverage is tracked there, not here. Batch 1's
safety-critical set is crisis + psychosis + panic-somatic + SI-adjacent; medical-AR belongs to the #329 track.

## On ratification
When Vee signs a batch's mapping and the native reviewer completes its dialect pass, drop `draft: true` on
those rows (or move them to `layer1_trigger_corpus_ar.jsonl`), and only then may the guarded runner measure
them and publish an AR number — with the low-baseline framing above attached.
