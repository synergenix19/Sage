# D1 serve/resume — GATE 0 acceptance list (#338, pre-code)

The enforce-time render path: emit the signed question via a terminal node, HOLD the contraindicated skill,
RESUME it on a clear_no answer. Built TDD against this list. Flag-gated behind SAGE_D1_SCREEN (enforce),
default-OFF; shadow and off paths unchanged. Every item red-verified before implementation.

## Constraint 1 — the held-skill state gets the re-entry treatment (the new subtle surface)
screen_pending is a mid-conversation SUSPENDED OBLIGATION — a state no prior mechanism had. The next turn may
not be an answer. Acceptance (every branch a fixture, both directions):
- **crisis-in-pending-turn** → crisis path wins, hold abandoned, audited `abandoned_crisis`. Extends the
  already-ruled answer-turn crisis supremacy to NON-answer turns. Must hold even though crisis bypasses
  skill_select (the clear happens on the bypass path, not only in decide_screen).
- **new clinical disclosure mid-hold** (veto-matching or containment-matching utterance) → that layer wins
  (its own routing), hold abandoned, per the supremacy chain (crisis > vetoes > containment > screen).
- **topic-change / non-answer** → classified `evaded` → grounding fail-safe, hold RELEASED, **no re-ask
  nagging** (the don't-force register).
- **PROPERTY (the load-bearing assertion):** *no path exists where screen_pending survives more than one
  user turn.* One turn pending, then the fail-safe resolves it — the hold can never become a gate the
  conversation cannot leave. Asserted as a property over {answer, crisis, veto, containment, topic-change,
  silence, second question} next-turns.

## Constraint 2 — the terminal-node emit serves the SIGNED bytes, verbatim (bench ruling)
- The screen_response terminal node emits `SCREEN_QUESTION_EN` byte-for-byte; **test asserts the served text
  hash-matches the manifest entry** `d1_screen_question_en` (sha256 in signed_clinical_fields.json). A drift
  between served bytes and signed bytes fails the test.
- Falcon-rendered / LLM-paraphrase mode is a SEPARATELY-gated future increment — not this build.
- Consequence, stated: this makes **Vee's comma-swap confirm HARD-BLOCKING for the flip** (flip is the moment
  those bytes first reach a user). Vee's two lines are out today (2026-07-17-d1-vee-two-line-confirm.md).
- Terminal node mirrors medical_response: writes its OWN session audit (bypasses output_gate), clears
  active-skill fields appropriately, sets screen_pending=True + screen_held_skill, → END.

## Constraint 3 — enforce-flip audit migration + its #160 alert-or-fail test ride THIS PR
- Migration 015: adds enforce audit columns (screen_asked / screen_answer_class / screen_branch_taken) to
  session_audit — the enforce-flip deploy gate (deferred from 014 by design).
- **In the SAME PR:** the #160 induced-failure fixture — an induced audit-write failure on the enforce path
  raises ScreenAuditError (never swallowed). Migration and its loudness guarantee land as ONE gated unit, so
  the schema and the alert-or-fail arrive together, not schema-now-guarantee-later.

## Standing (carried from the mechanism's GATE 0)
- Supremacy chain intact: crisis > vetoes > containment > screen > routing (property test).
- Fail-safe: proceed reachable ONLY from clear_no (unchanged; re-asserted end-to-end through the graph).
- Bilingual: AR holds grounding-only (unsigned question) — serve/resume must NOT emit for AR.
- Seam: any new SageState channel (screen_held_skill) declared + per-turn/​per-session-correct + graph-driven,
  not just unit-green (the SG-2 lesson; screen_shadow proved this live 2026-07-17).
- GATE 0 addendum lands BEFORE serve/resume rides any deploy.
