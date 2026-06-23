# Case-29 — Cardiac-Somatic Presentation: Routing Decision

> ## DECIDED 2026-06-23 — **Stratified C + red-flag MEDICAL_REFERRAL escalation**
> Clinical lead's call (relayed, clinician present). Not pure C and not pure B — **defense in depth**:
> - **Default (C):** a cardiac-somatic message with *no* explicit red flag routes to `psychoed_anxiety`, but the skill opens with an **action-first medical rule-out caveat** (named red flags; branches first-time vs recognized-recurrent). Lead with the rule-out, never with reassurance.
> - **Escalation (B-style):** a message carrying *any* explicit acute red flag does **not** reach a therapeutic skill — it returns a non-skill **`MEDICAL_REFERRAL`** ("seek urgent medical evaluation now"), exactly like the crisis-escalate path but for medical.
> - **Two layers cover each other:** a missed red flag still hits the C-path caveat and can self-escalate.
>
> **Clinical principle for leadership:** anxiety is a *diagnosis of exclusion*. The router must never assert "this is anxiety." Recommending evaluation for new/unexplained chest symptoms is **standard of care, not over-caution** — the genuine over-referral cost lands only on users with established, evaluated, recognized panic, and the recurrent-vs-new branch in the caveat spares exactly that group.
>
> **Red flags that trip MEDICAL_REFERRAL** (from cardiology sources): pain radiating to arm/jaw/neck/back/shoulder · shortness of breath · sweating/cold sweat · nausea/vomiting · lightheadedness or near-syncope · exertional onset (eased by rest) · pain lasting >a few minutes / worsening / not easing with calming · stated sense of impending doom · known cardiac disease or age + risk factors.
>
> **Case 29 itself stays C** (no stated red flag) → `psychoed_anxiety` + caveat. The hybrid does not move case 29; what it forces us to build is the destination for the red-flag *variants*.
>
> **Conditions (binding):**
> 1. `MEDICAL_REFERRAL` outcome is built **now** (schema add) so the held-out eval can't false-pass on benign-only somatic cases. ✅ DONE — eval schema + harm gate + red-flag dataset (this branch).
> 2. Eval includes **red-flag test cases in both directions**. ✅ DONE — `redflag_somatic.jsonl`: radiation / dyspnea / exertional / syncope / autonomic-doom → MEDICAL_REFERRAL, plus a cardiology-cleared recurrent case → psychoed_anxiety.
> 3. Caveat language + Gulf-Arabic red-flag idioms reviewed by the clinical lead + **native reviewer** (Gulf populations somatize distress, so this boundary fires disproportionately for Arabic users). — OPEN (native-reviewer worklist). **Clinician wording principle 2026-06-24:** the caveat must be a medical rule-out **signpost, not diagnostic reassurance** — "this is probably just anxiety" is the exact failure mode (LLMs demonstrably accept a user's self-assessment that chest tightness is anxiety even with cardiac history + new symptoms). Even a true panic presentation cannot be cleared conversationally, and panic can itself trigger myocardial ischemia, so chest pain in a panic context is **not** assumed benign. Red-flag clinical floor (idioms are the native reviewer's; these signals are the floor): pain radiating to arm/jaw/neck/back, exertional onset, cold sweat/diaphoresis, **pain not relieved by rest or reassurance**, associated shortness of breath or nausea, and **any cardiac history**.
> 4. **Regulatory:** confirm DHA/MOH digital-health + medical-disclaimer obligations on the referral wording before any real-data go-live. — OPEN (owner: leadership/compliance).
>
> **Residual (accepted):** the production red-flag *detector* (the runtime trigger) is a separate build; until it ships, a clearly-red-flag presentation receives skill+caveat rather than a hard referral. Push against shipping that state past pilot.
>
> Scope: applied current triage/cardiology best-practice; not a licensed-clinician sign-off — clinical lead owns and signs.

---

**For:** clinical lead + leadership · **Decision recorded above; rationale + options below.**
**Why now:** this was the last open *boundary* question. Option B is a boundary change that would re-label other somatic-adjacent cases, so it had to be settled **before** the dataset is assembled and reviewed — otherwise the clinician reviews against a boundary that then moves.

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
