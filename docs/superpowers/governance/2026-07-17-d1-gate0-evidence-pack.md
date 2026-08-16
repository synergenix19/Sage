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

## ADDENDUM 2026-07-17 — L194 contraindication half (the second beat)

**Finding (eng-caught pre-issue):** the first cut screened only the L101 acute symptom-QUALITY. But D1 exists
for TIPP's **L194 contraindications** (heart condition / pregnancy). A known-cardiac user on an ordinary panic
day answers the quality question truthfully → `clear_no` → `proceed` → ice-water. Fail-safe intact
mechanically, defeated clinically, because `clear_no` answered the wrong question. Fixed: one new answer class
`contraindication_disclosed`, ordered **above clear_no** (a disclosure beats a symptom-quality no) and
**below red_flag** (an acute emergency still wins → 998); its branch is **grounding, NOT 998** — a stable
condition is a routing fact, not an emergency.

**Driven (12 new tests, both directions; total 50 green):**
- disclosure beats clear_no: `test_classify_contraindication_disclosed["no, it feels the same as always, but
  I do have a heart condition" → contraindication_disclosed]` — **the exact failure case, as an executable test**
- pregnancy, cardiac, pacemaker, "12 weeks pregnant", + AR (`عندي مرض في القلب`, `أنا حامل`) → the class
- red_flag precedence preserved: `["...heart condition and now crushing pain spreading to my arm" → red_flag]`
- NO over-match (both directions): plain clear_no, `"my heart is racing"` (a symptom), `"anxious about my
  heart rate"` → **not** the class (`test_contraindication_class_does_not_overmatch`)
- routes AWAY not to guard: `test_contraindication_disclosed_routes_grounding_not_guard`
- fail-safe property extended: `test_screen_only_clears_on_clear_no` enumerates the new class — `proceed`
  still reachable ONLY from clear_no
- **session-persistence falls out for free** (no code change): `decide_screen`'s "prior not None and not
  clear_no → reroute_grounding" reroutes a disclosed condition on every future TIPP routing, no re-ask
- **zero regression:** baseline-vs-change diff on the exact non-slow set = only the 12 new tests flip
  RED→GREEN; 7 pre-existing failures (parallel-landed: async server-offer mocks, SK-EN-002 FP-boundary,
  redflag honesty_notes) present in BOTH runs, none in the classifier

**Editable-install `.pth` guard honoured** (process note): venv `sage_poc` resolves to the *other* checkout;
tests run with `PYTHONPATH=$PWD/src` and a pre-flight assert that `sage_poc.__file__` starts with the worktree
`src/` before any result is trusted.

## ADDENDUM 2026-07-17 (2) — SILENT shadow surface (the driveable dark-deploy artifact)

**Why silent, not serve-but-don't-enforce:** a safety screen cannot be shadowed by letting the harm through.
Serving-without-enforcing would knowingly route a heart-condition discloser to TIPP ice-water during the
window — the exact harm D1 exists to prevent. So shadow is **route-identity by construction**: it observes the
would-be decision and writes it to the audit, and does **not** move the served route.

**The invariant, driven both directions (7 shadow tests, 65 total green):**
- **ROUTE-IDENTITY, byte-for-byte** — `test_shadow_route_identity_on_contraindicated`: strip the
  `screen_shadow_*` observation keys and what remains is **identical to the flag-off output**; TIPP is still
  the routed skill; `screen_pending` / `screen_question_text` never set. Even with a session prior that would
  reroute (`test_shadow_observation_matches_decide_screen`), the served `active_skill_id` stays `dbt_tipp`
  while `screen_shadow_action == reroute_grounding` is recorded.
- **PRECEDENCE** — `test_enforce_wins_over_shadow`: both flags on → enforce path (route moves), and the enforce
  path writes **no** shadow observation.
- **BOTH-OFF IDENTITY preserved** — `test_both_off_is_identity_no_shadow_keys`: neither flag → byte-identical,
  no shadow keys leak. (The original `test_flag_off_is_byte_identical` still holds — enforce-off + shadow-off.)
- **NOT-A-SCREEN cases** — veto result and non-contraindicated skill in shadow → identity, no observation.

**Seam wired, not just unit-green (the SG-2 lesson):** the `screen_shadow_*` keys are **declared SageState
channels** (else LangGraph drops them between skill_select and output_gate), **per-turn reset** in
`_build_state` (else a prior screen turn's observation leaks onto a later non-screen audit row — the same seam
on the audit surface; the existing `screen_asked` group was reset in the same pass), and **read by
`_build_session_audit_row`** so the observation actually persists. The audit block is flag-gated exactly like
tiering/precedence/medical/HR: a non-screen row stays byte-identical to master, and the `screen_shadow_*`
column migration is the `SAGE_D1_SCREEN_SHADOW` flip deploy gate. Red-verified both directions
(`test_medical_screen_audit.py`, block-disabled → shadow rows fail; restored → green). `check_state_channels`,
`check_signed_fields`, parity, reads-raw all green.

**HONEST RULING 3 SPLIT (named, not a silent cut):** silent shadow measures **FIRE-VOLUME** only. The
answer-class distribution criteria (`unclear < 20%`, `contraindication_disclosed` rate) require the question
*served and answered*, which silent shadow by definition does not do. Therefore:
- **Shadow-window gate:** trigger fire-rate / would-fire volume (measurable now, route-identity).
- **Post-flip monitored-enforce gate:** the answer-class distribution criteria (measurable only once serving
  is live, with the fail-safe actually protecting users). This is where the user's "post-flip monitoring
  against the [criteria]" lands. RULING 3's thresholds are unchanged; only *which gate reads which row* is
  made explicit.

**Not built here (honest scope):** the **serve/resume render path** (enforce-time: emit the signed question
via a terminal node, hold the skill, resume it on a clear_no answer). It is needed for the FLIP, not for the
shadow window — silent shadow never serves. It is the next increment before flip.

## Verdict
Every branch provable without signed content is driven and green (**65** + regression, zero delta). Both
clinical halves covered; EN question signed & pinned; silent-shadow surface is route-identity byte-for-byte
with its seam declared+reset+persisted. GATE 0's isolated drive is **complete** through the dark-deploy
artifact. Next: build serve/resume (for flip) → dark deploy (flag-dark) through the lock chain → shadow window
(fire-volume gate) → flip → post-flip monitored-enforce (answer-distribution gate). PDPL line **closed**
(approved 2026-07-17, anonymised class+route).
