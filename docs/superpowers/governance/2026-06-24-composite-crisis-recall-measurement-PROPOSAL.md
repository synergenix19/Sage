# Composite Crisis-Recall Measurement — Proposed Next Safety-Track Cut

**Status:** PROPOSED (safety track, parallel to the routing freeze). **Gates:** the G2 pilot-graduation crisis bar, and how crisis recall is reported to leadership.

## The finding that triggers this
A live probe (2026-06-24, AR first-cut review) showed crisis escalation firing via **three different layers** — S1 lexicon, S3 semantic, **and the LLM `intent_route`** (Node 2). The established **~38% figure was characterized as "essentially S1's own recall"** (S2/MARBERT unbuilt, S3 advisory-adds-zero on CRADLE). But if `intent_route` catches presentations S1's keyword floor misses — plausible, since the LLM generalizes where keywords can't — then **~38% may be measuring one layer, not the composite path a real user traverses.**

> **This is a HYPOTHESIS, not evidence.** The probe shows the composite *can* exceed S1 on individual cases; it does not establish the composite recall. The point of this cut is to **measure**, not to assume the better number.

## Why it matters (and why it must be measured, not assumed)
1. **If composite recall is meaningfully > 38%:** the G2 bar shouldn't be set against a one-layer number, and the live pilot's net is less alarming than the S1 figure implied. *Good — but only if true.*
2. **If composite ≈ 38%** (the LLM adds little on the oblique-Gulf presentations specifically): ~38% stands, now *confirmed* rather than assumed. *Equally valuable.*
3. **The trap to avoid:** do NOT let "the LLM might catch more" soften the G2 bar or the G5 backstop urgency before it's measured. Relaxing a safety bar on an optimistic assumption is the exact inverse of the harm-weighting / fail-closed discipline. The finding **increases the value of measuring; it does not license assuming.**

## Measurement design — three things to get right
1. **Measure the PATH, not the layer.** Run crisis cases through the full graph entry (S1 → intent_route → S3) as a real message flows; score whether **the system escalated** (gate_path=crisis), not whether S1's lexicon fired. That is the number that describes the live pilot.
2. **Stratify by language × directness.** Composite may be much better on explicit English and barely better on **oblique Khaleeji** — the population the pilot actually serves and where S1 already struggles. A composite of 70% overall but 40% on oblique-Gulf is still a 40%-for-the-real-users problem. **Don't let an aggregate hide the cell that matters (the F8 discipline, again).**
3. **Use the assets this review just produced.** The 3 new AR passive-SI crisis cases (burdensomeness + 2 life-weariness) and the precision-FP case (`أبي أختفي`) are the first task-#21 Arabic-crisis material — exactly the inputs to measure composite **Arabic** crisis recall (and FP precision). The sign-off produced the data that lets this run.

## Hard guardrails
- **No posture relaxation until measured.** The G2 bar and the G5 backstop urgency stay as-is until the composite number (stratified) exists.
- **G5 backstop does NOT become unnecessary even if composite recall is better.** It catches what all three layers miss; a higher composite shrinks how often it fires, never to zero — there is no recall short of 100% where "missed crisis still gets a helpline" stops being worth having.
- **The LLM layer is non-deterministic.** Even if it adds recall, a deterministic floor gap remains (cf. the Arabic-script `تعبت من الحياة`/`ما لي خلق أعيش` absent from S1) — composite recall via an LLM is not the same safety guarantee as lexicon coverage.

## Immediate action (before any bar-setting or reporting)
**Caveat the ~38% wherever it's currently used:** it is **S1-layer recall; the composite path is unmeasured.** Do not report it to leadership as "the system's crisis recall," and do not set the G2 bar against it, until this measurement is done. (Recorded in the sign-off sheet G2 entry.)

## Owner / next step
Engineering runs the composite-vs-CRADLE measurement (stratified, full-graph scoring); clinical/PO set the G2 bar *after* the stratified number exists. Read-only-ish (run cases through the graph, score escalation). **Put to the team as:** *"Before we set or report the crisis-recall bar, confirm whether 38% is the system or just S1 — stratified by language and directness, with no relaxation of the posture until it's measured."*
