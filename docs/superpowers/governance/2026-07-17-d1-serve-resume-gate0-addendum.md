# D1 serve/resume — GATE 0 addendum (#338)

## ⚠️ CORRECTION 2026-07-20 — this addendum OVERCLAIMED; read this first
The claims below of "DRIVEN" and "proven" for the serve→answer path were **WRONG when written**, and the
2026-07-20 enforce-flip incident proved it (`2026-07-17-d1-enforce-flip-incident.md` — filed 2026-07-20).
What was actually driven at the time: the mechanism in UNIT tests (state constructed inline) and ONE graph
test that drove *crisis-mid-hold* — a deterministic bypass. **The serve→answer path was NEVER driven on the
compiled graph.** `screen_question_text` was undeclared, LangGraph dropped it skill_select→router, and the
screen never served — invisible to every test here because each bypassed the channel-transport layer (the
test-harness/runtime boundary rule, now in `docs/ARCHITECTURE_BOUNDARIES.md`).

**Corrected status (2026-07-20 fix):** `screen_question_text` declared; the answer-turn seam closed;
`check_state_channels` hardened to catch helper-module writes (this class now fails CI); and
`test_flip_probe_branches_on_compiled_graph` added — serve→answer for the flip probe's exact branches on the
COMPILED graph via the real `_build_state` contract (it fails without the fix). "Proven" below now means what
that test and the live re-probe assert. The word carries the project's weight only if corrected when it was
wrong; this is that correction, on the record, not a supplement.

---

Evidence against the pre-registered acceptance list (2026-07-17-d1-serve-resume-gate0-acceptance.md). Every
branch driven by a named fixture. Flag-gated behind SAGE_D1_SCREEN (enforce), default-OFF; shadow/off paths
byte-identical (the enforce router branch is unreachable with the flag off — screen_question_text is never
set). 80 D1 tests green, all gates (state-channels/signed/parity/reads-raw), zero new regression.

## Constraint 1 — held-skill re-entry treatment (DRIVEN)
- **held + resume:** `test_ask_screen_stores_held_skill` (ask stores dbt_tipp), `..resume_clear_no_reenters_
  held_skill` (clear_no → active_skill_id=dbt_tipp), `..contraindication_disclosed_reroutes_grounding`,
  `..topic_change_releases_hold_no_reask` (evaded → grounding, no re-ask).
- **THE PROPERTY (no path leaves screen_pending set after the answer turn):** mechanism-level
  `test_pending_never_survives_more_than_one_turn` over {clear_no, disclosure, yes, unclear, topic-change,
  empty}; graph-entry `test_safety_check_consumes_pending_into_answering_signal`; and the LOAD-BEARING
  end-to-end `test_crisis_mid_hold_releases_in_one_turn` — driven through the REAL compiled graph: turn 1
  emits the screen, turn 2 is a crisis, and screen_pending is False after turn 2 (crisis supremacy AND hold
  released, because safety_check's consume_pending_screen runs at graph entry BEFORE the crisis short-circuit).
- **Structural guarantee:** consume_pending_screen wired into safety_check (every turn) makes screen_pending
  True for EXACTLY the emit turn, regardless of turn N+1's route (crisis bypass, veto, or answer).

## Constraint 2 — terminal emit serves the SIGNED bytes verbatim (DRIVEN)
- `screen_response_node` emits `SCREEN_QUESTION_EN` verbatim (`test_emits_signed_question_verbatim`), writes
  its own audit, → END, and PRESERVES the hold for the answer turn (`test_preserves_hold_for_next_turn`).
- `test_served_bytes_hash_match_manifest`: served bytes reproduce the pinned `d1_screen_question_en` sha256.
- Vee's comma-swap confirm is IN (2026-07-17-d1-vee-two-line-confirm.md, both lines ✅) — the bytes are
  clinician-confirmed, so the flip's byte-dependency is cleared.
- Router edge deterministic: `test_router_sends_served_question_to_screen_terminal` (served question →
  screen_response; containment still wins above it; flag-off unreachable).

## Constraint 3 — enforce migration + #160 alert-or-fail in ONE unit (DRIVEN)
- Migration 015 adds the enforce audit columns (screen_asked / screen_answer_class / screen_branch_taken) —
  the enforce-flip deploy gate. SHADOW columns shipped separately (014).
- `test_enforce_audit_row_failure_is_loud`: an induced write failure on the enforce audit row raises
  ScreenAuditError (never swallowed). Schema + loudness guarantee land together.

## Standing (carried, re-asserted)
- Supremacy chain intact end-to-end (crisis_mid_hold graph test); fail-safe proceed-only-from-clear_no
  unchanged; AR grounding-only (no enforce emit for AR — question unsigned); new channels
  (screen_held_skill, answering_screen) declared + seam-clean (state-channels gate green).

## Deferred, DOCUMENTED (not silently dropped)
- **veto/containment-mid-hold "layer wins its OWN routing":** currently a veto-matching utterance ON the
  pending turn is classified as an evaded answer → grounding fail-safe. This RELEASES the hold and routes
  AWAY from the contraindicated skill (SAFE, property holds), but it resolves to grounding rather than the
  veto's own outcome (e.g. OCD-veto abstain → low_confidence). Making the veto's specific routing win
  requires a veto-marker signal into apply_screen_at_route; tracked as a follow-up increment. The current
  behaviour is safe-by-construction, not a gap in the property or the fail-safe.

## Verdict
serve/resume is driven and green against all three constraints; the property is proven live through the
graph. Enforce path remains flag-OFF/dark. Next: this branch's PR + CI; enforce-flip is gated on the shadow
window closing (N=40 / 14-day) + migration 015 applied + this addendum on the record.
