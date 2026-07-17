# D1 — medical screening question build spec + clinician deliverable (#338)

**Approved in principle by V (2026-07-16, "implement"); shape refined 2026-07-17.** This doc is the
build spec AND the clinician deliverable: the **rendered question** and **branch table** below are the
signed content for V's tick; the mechanism around them is engineering. Closes #338 (spec L58/L101
quality-check unimplemented). Fires the C1/A3 revisit-trigger (once D1 ships+verifies, TIPP-leads for
acute-overwhelm becomes reconsiderable — `2026-07-17-324-a3-ruling-V.md`).

## Architecture (V's signed shape): conversational surface, deterministic consequence
- **Trigger — LAYERED, recall-biased** (like Node 1): physical-symptom keyword **OR** semantic match
  against physical-symptom anchor descriptions, on RAW input (`safety_text`, the language-contract rule).
  Cost asymmetry is kind — a false trigger only asks one gentle question — so cast wide. Fires ONLY when
  a physical symptom is mentioned WITHOUT an already-firing red-flag keyword (the ambiguous middle;
  explicit red-flags already go straight to the medical guard).
- **Question — conversational, Falcon-rendered in flow** (NOT a bolted-in questionnaire; bot-behaviour
  register: woven naturally, never led-with, one step, no clinical-terminology dump). Wording is SIGNED
  content (below). The harness requires Falcon's rendering to carry the discriminating *markers*, not a
  bare echo (#338 lesson applied forward).
- **Consequence — STRICTLY DETERMINISTIC.** Answer-classification + branch table are rules; **no LLM
  discretion in the safety consequence.**

## SIGNED CONTENT #1 — the question (V to tick / edit)
> *"Before we try this one — quick check first: does anything about how this feels seem different from
> your usual anxiety? Like a sharp or crushing pain rather than tightness, pain spreading to your arm,
> jaw, or back, real trouble breathing rather than shallow breathing, or numbness or weakness on one
> side?"*  (spec L101 verbatim discriminating markers, warm framing)

▢ **V: question wording correct** ▢ edit: ______

## SIGNED CONTENT #2 — the branch table (V to tick / edit)
Answer-classification → route. **The screen routes AWAY, never CLEARS** — its only outputs are
"proceed" (a clear no) or "route to safety" (everything else).

| answer class | example | route |
|---|---|---|
| **clear NO** | "no, it's the same as always" | proceed with the offered skill |
| **red-flag quality** | "yeah, it's spreading to my arm" / "real trouble breathing" | **medical guard** (998 prompt) |
| **YES (unspecified)** | "kind of?" / "maybe different" | **grounding** (fail-safe) |
| **unclear / evaded** | "it's kind of both" / "لا بس شوي مختلف" | **grounding** (fail-safe — unclear discriminator → treat as red-flag-quality-adjacent, route to the contraindication-free skill) |
| **no-answer / topic-change** | (ignores, changes subject) | **grounding** (fail-safe) |

**FAIL-SAFE ROW (invariant):** anything that is NOT a clear "no" routes to **grounding — silently and
warmly**, without announcing the reroute or demanding a clinical explanation. The user experiences a
gentle pivot, not an interrogation.

▢ **V: branch table + fail-safe correct** ▢ edit: ______

## Per-language fail-safe (bilingual-parity, from the ADR)
The **AR question is dual-clinician-gated** (SIGNED CONTENT #1 above is EN). **Until the AR question is
signed, AR users get grounding-only for acute-overwhelm** — no screen in a language = the
contraindication-free default in that language. A half-built screen must never run in a language whose
answers it cannot classify.

▢ **V: AR question** (to be drafted for a later tick) — grounding-only holds for AR until then.

## Acceptance (in the list NOW, not retrofitted)
1. **Audit row is part of acceptance, not garnish:** every screen fires an audit record of
   `screen_asked` / `answer_class` / `branch_taken`. A contraindication decision that isn't traceable to
   its rule and answer is one the PDPL right-to-object story can't defend.
2. **Signed-fields manifest:** the question wording + the branch table join `signed_clinical_fields.json`
   on V's tick — CI fails on an unsigned change (same class as the caveat texts).
3. Trigger reads RAW (`safety_text`); response is deterministic; fail-safe defaults to grounding;
   red-flag-quality answer → medical guard; harness asserts markers present (not echo) + no-skill-offer.

## TDD build plan (mechanism — engineering, post-tick)
1. RED: `is_physical_symptom_ambiguous(safety_text)` layered detector (keyword + semantic anchor).
2. RED: `classify_screen_answer(text) -> {clear_no, red_flag, yes, unclear, no_answer}` deterministic.
3. RED: branch table routes each class (fail-safe → grounding; red_flag → medical guard).
4. Wire: skill_select injects the screen before a contraindicated acute skill; output_gate audits the row.
5. Bilingual/flow-aware harness probe (both languages; AR held to grounding-only until #1-AR signed).

Refs #338 #324 #329 #330. Deploys only after V ticks SIGNED CONTENT #1 + #2; AR follows on its own tick.
