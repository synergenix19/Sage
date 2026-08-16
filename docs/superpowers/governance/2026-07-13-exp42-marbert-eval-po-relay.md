# Exp 4.2 (MARBERT bilingual eval) — pull ahead of Week 8–9 · PO relay 2026-07-13

**Ask:** move **Exp 4.2 (MARBERT fine-tune + bilingual safety-recall eval)** ahead of its scheduled Week 8–9 slot. This is a schedule decision, not new scope. **The case is now complete, not "strengthening."**

## Why now — four safety-recall classes rest on one unmeasured model
Every one of these depends on the LLM/MARBERT intent layer for detection, and that layer's recall on them has **never been evaluated**:

| # | Recall class | Deterministic coverage | Evidence |
|---|---|---|---|
| 1 | Passive-SI / veiled ideation | partial (S1 lexicon misses naturalistic phrasing) | `project_passive_si_detection_gap`; safety fixture veiled-miss cases |
| 2 | SI-with-negation | 5/6 missed by the lexicon | `project_negation_gap` (SK-EN-001) |
| 3 | Cross-turn escalating-intent | none (beyond single-message reach) | ticket `2026-07-10-node1-lexicon-coverage`; `harm_intent_escalation_crossturn.jsonl` |
| 4 | **Harm-to-others** | deterministic backstop existed but was **silently reverted in prod for ~3d 15½h** | incident `2026-07-13-harm-to-others-clobber-incident.md` |

## The sharpest exhibit (class 4)
For **~3 days 15½ hours** (2026-07-09 22:25 → 07-13 13:58) the deterministic harm-to-others backstop was silently reverted in production by a bypass deploy. During that window, **harm-to-others detection rested ENTIRELY on the unmeasured LLM/MARBERT layer** — by accident, undetected. And the exposure question for that window is **formally unanswerable from the audit trail**: a disarmed deterministic control leaves no signature (the flag that tags its turns is the flag that was off), so the covering layer's recall over the window is **unmeasured and un-measurable after the fact**. The only instrument that can measure it is Exp 4.2. **Measuring it requires the eval, not the trail** — which is the bridge from the incident to this relay.

## The one sentence
Four safety-recall classes depend on a model we have not evaluated; one of them was, for 3½ days, the *only* coverage without our knowing, and its exposure is unmeasurable without the eval. That is the case for pulling Exp 4.2 forward.

## Scope (unchanged, for reference)
MARBERT fine-tune + a bilingual (EN + Gulf-Arabic) safety-recall eval set covering the four classes above. Gated deliverable; no production change until it clears. Owner: Lane-1 / Safety-ML.
