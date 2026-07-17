# D1 (#338) — GATE 0 evidence pack (isolated drive)

**First instance of the GATE 0 standing step** (`prod-deploy-control.md`). Evidence, not assertion — every
branch driven by a named fixture. Scope: everything provable **without signed content**; the end-to-end
ask→answer→route completes in shadow post-Vee-sign-off (the placeholder guard makes it structurally
impossible before her bytes exist — the guard doing its job, not a sequencing compromise).

## GATE 0 step → evidence

**1. Code-review the deterministic consequence** — `medical_screen.py`: the fail-safe branch table
(`{clear_no:proceed, red_flag:medical_guard}.get(cls,'grounding')`) and classifier are the safety
consequence; reviewable, no LLM discretion.

**2. Drive every branch** (38 tests green):
- classifier → all 5 classes incl. red-flag-quality winning over surface no/yeah: `classify_screen_answer[...]` ×10
- branch table + FAIL-SAFE: `route_screen_answer[...]` ×5, `test_failsafe_unknown_class_routes_grounding`, `test_screen_only_clears_on_clear_no` (proceed reachable ONLY from clear_no — the invariant as a property)
- trigger (recall-biased, raw): fires ambiguous / vague-no-keyword; NOT non-physical; NOT when red-flag present
- **re-entry (note 1)**: `test_reentry_after_clear_no_proceeds_without_reasking`, `..._after_yes_reroutes_grounding_without_reasking`, `..._after_redflag_never_reoffers_tipp`, `test_non_contraindicated_skill_never_screens`
- answer-turn classify→route→store: `test_answer_turn_routes_and_stores[...]` ×5

**3. Markers asserted, not echoes** (#338/#342 lesson): the classifier asserts the actual *class*, the
trigger asserts symptom markers, the answer-turn asserts `screen_branch_taken` — no green on a surface token.

**4. Audit written-and-read-back / alert-or-fail (#160)** — `test_audit_write_failure_is_loud`: an induced
write failure raises `ScreenAuditError`, never silent (the PDPL exposure the D-item closes).

**5. Bilingual + flow-aware** — trigger carries AR terms; the veto-order fixture drives an AR utterance;
**per-language fail-safe**: unsigned question → grounding (AR holds grounding-only until its own tick).

**6. FLAG BOUNDARY (note 1)** — `test_flag_off_is_byte_identical`: flag-off, `decide_screen` spy asserts
**0 invocations**, result returned unchanged, **no `screen_*` channel touched**. Corroborated: **92
existing skill_select / veto / offer tests pass byte-for-byte** with the wrap in place.

**7. VETO ORDER (note 2)** — `test_veto_result_never_screens`: a veto result (active_skill_id=None) is
never a screen situation, no state written. Supremacy chain intact: crisis > vetoes > screen > routing.

**8. Crisis supremacy over the screen (note 2)** — `test_crisis_in_screen_answer_abandons_screen`:
crisis-in-answer → `abandon_crisis`, audited as `abandoned_crisis`, never filed as unclear→grounding.

## Not driven here (honest scope)
- **End-to-end ask→answer→route**: needs Vee's signed question (A1) + the multi-turn held-skill resume;
  completes in **shadow, post-sign-off**. Until then flag-on + TIPP → grounding fail-safe (verified).
- **Recall-biased semantic trigger tier** (BGE-M3 anchors): keyword net covers the core; anchor tier is a
  follow-up (cast wider still). Shadow's fire-rate read-out is where it's tuned.

## Verdict
Every branch provable without signed content is driven and green (38 + 92 regression). GATE 0's isolated
drive is **complete**. Next: A1/A2 → Vee; flag-dark deploy through the lock chain; shadow with pre-registered
flip criteria + PDPL line closed before the first prod row; end-to-end drive in shadow; flip.
