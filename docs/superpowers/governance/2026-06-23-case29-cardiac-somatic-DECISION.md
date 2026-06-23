# Case-29 — Cardiac-Somatic Presentation: Routing Decision

**For:** clinical lead + leadership · **Decide:** one of A / B / C below.
**Why now:** this is the last open *boundary* question. Option B is a boundary change that would re-label other somatic-adjacent cases, so it must be settled **before** the dataset is assembled and reviewed — otherwise the clinician reviews against a boundary that then moves.

## The question
When a user's message is **led by cardiac-type somatic symptoms** — chest tightness/pain, racing or pounding heart, palpitations — how should the router behave? These are extremely common in anxiety/panic, **but can also signal a cardiac event**, so a confident "anxiety" route can mask a medical emergency. Example (seed case 29): *"I feel tightness in my chest and my heart is racing and I don't know why."*

## The three options

**A — Treat as anxiety** → route to `psychoed_anxiety` (current default).
Simplest, no change. **Risk:** a genuine cardiac event receives an anxiety/psychoeducation response with no medical prompt. Not recommended.

**B — Hard medical rule-out at the routing layer** (NEW boundary outcome).
Cardiac-somatic-led presentations get a `MEDICAL_REFERRAL` outcome — the router does **not** send them to a therapeutic skill; it returns a "seek medical evaluation" response (like the crisis escalate path, but for medical). **Safest** on cardiac-miss. **Cost:** a boundary + schema change, re-labels the 7 parked somatic cases AND any somatic-adjacent in-scope cases; over-refers (anxious users with benign palpitations get a medical prompt).

**C — Route to `psychoed_anxiety` WITH a content-level medical rule-out caveat.**
Routing unchanged (somatic cases stay `in_scope → psychoed_anxiety`); the skill content (or a pre-skill check) opens with *"if these symptoms are new, severe, or unexplained, please seek medical evaluation"* then provides anxiety support. Rule-out **without** over-escalating; **no routing-boundary change**; the caveat is skill-content authoring, separate from routing.

## Best-practice note (for context, not a decision)
Triage/chatbot safety guidance for chest pain is: **don't diagnose, prompt medical evaluation for new/severe/unexplained symptoms, while still offering support** — i.e. a rule-out caveat, not a blanket refusal. Anxiety very commonly presents this way, so blanket medical-referral over-refers; but missing a cardiac event is the high-harm error. The usual proportionate answer is a rule-out caveat (C), reserving a hard rule (B) for clearly acute/red-flag presentations.

## Implications at a glance
| | A treat-as-anxiety | B hard medical rule-out | C route + caveat |
|---|---|---|---|
| Cardiac-miss safety | weakest | strongest | strong |
| Over-referral | none | highest | low |
| **Boundary change?** | no | **YES (ripples to other somatic cases)** | no |
| Schema change? | no | YES (`MEDICAL_REFERRAL` outcome) | no |
| Somatic case labels | in_scope → psychoed_anxiety | MEDICAL_REFERRAL (not a skill) | in_scope → psychoed_anxiety |
| Extra work | none | boundary + schema + relabel | skill-content caveat (separate task) |

**Engineering recommendation (deferring to you):** **C** is the proportionate middle — routing stays stable, the safety rule-out lives where it belongs (content), somatic cases label normally, and assembly isn't blocked by a boundary edit. Choose **B** if leadership wants maximum cardiac-miss protection and accepts the boundary change + over-referral. **A** is not recommended (no safety rule-out).

## Decision
```
Choice (A / B / C): ______    Decided by: ______________   Date: ______
If C: who authors the psychoed_anxiety medical rule-out caveat: ______________
If B: confirm MEDICAL_REFERRAL becomes a routing outcome + re-label somatic-adjacent cases: ______________
```
On decision: the 7 parked somatic cases resolve accordingly, the dataset assembles boundary-stable, and the clinician reviews one consolidated set.
