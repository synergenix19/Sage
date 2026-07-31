# Psychoed fixture families corpus (Phase 3)

Clinician-editable content class. Every `f*_*.jsonl` file in this directory is a fixture
family corpus consumed by `tests/test_psychoed_fixtures_ci.py` (the CI families driver).
One JSON object per line.

## File naming

`f<N>_<slug>.jsonl` where `f<N>` (lowercased) is the family, e.g. `f4_weave.jsonl`
holds family `F4` rows. `load_family("F4")` reads every `f4_*.jsonl` file, so keep ONE
file per family (later tasks extend the plan's File Structure names in place:
`f4_weave.jsonl`, `f8_regression.jsonl`, ...) or rows double-load.

## Row schema (all families; unused fields null)

```json
{"fixture_id": "F4-007", "family": "F4", "set": "authored", "category": "3c",
 "turns": [{"utterance": "Why do I feel numb?", "intent_sweep": false},
           {"utterance": "kind of", "intent_sweep": true}],
 "expect": {"disposition": "escalate_crisis", "audit": {"psychoed_weave_state": "escalated",
            "psychoed_matched_row_id": "3c-t3"}, "state": {"psychoed_active_category": null}},
 "delta_cite": "gap-2", "repin_on": null, "lang": "en", "source": "<authoring provenance>"}
```

Required keys: `fixture_id`, `family`, `set`, `turns`, `expect`, `lang`.

- `fixture_id`: unique across the whole corpus.
- `family`: `F1`..`F10`; must match the file's `f<N>_` prefix.
- `set`: one of `wiring` | `authored` | `seed`.
- `category`: the psychoed category the driver arms via `config.PSYCHOED_CATEGORIES`
  for this row's run (may be null: run with no category armed).
- `turns[*].utterance`: non-empty; NO EM DASHES (clinician-editable content class,
  schema-enforced).
- `turns[*].intent_sweep`: bool, required. `true` is only legal in gate families
  (F4/F6/F8): the row runs once per intent in `INTENT_SWEEP`, with every swept turn's
  `primary_intent` pinned to that intent. Never single-pinned.
  `INTENT_SWEEP` [AMENDED 2026-07-30, human-ruled] = the FULL `intent_route` label
  vocabulary (`skill_continuation`, `new_skill`, `general_chat`, `crisis`,
  `info_request`, `exit_skill`, `scope_refusal`, `jailbreak`; source of truth:
  `src/sage_poc/nodes/intent_route.py:25`, sync-checked by
  `test_intent_sweep_matches_intent_route_vocabulary`) plus the
  `"__nonexistent_label__"` sentinel pinning the intent ladder's fall-through default
  branch. Assertion split by label class: every label asserts the never-proceed
  invariant (weave-pending reply produces no serve, no menu; crisis disposition where
  the row expects escalation); the escalation MECHANISM assertions (`expect.audit`
  escalation row and `expect.state` pathway clear) apply only on labels reaching the
  weave evaluator (all labels except `crisis`, whose intent-route crisis branch
  precedes the weave-pending branch).
- `turns[*].intent` (optional): pinned intent for a NON-swept turn. Falls back to the
  row-level optional `default_intent`, then to the driver default (`info_request`, the
  intent that reaches skill_select where the psychoed resolver runs, mirroring
  `tests/test_psychoed_graph.py`).
- `expect.disposition`: matched via the driver's `_observed()` semantics (local copy of
  `scripts/bot_behaviour_audit/measure_layer1_fullgraph.py::observed`, extended with
  psychoed markers; Task 9 replaces it with the canonical runner import). `null` means
  "do not assert disposition" (F8 seeds: whatever master does).
- `expect.audit`: subset-matched against the LAST captured session-audit row
  (built via `audit._build_session_audit_row` on the raw state passed to
  `write_session_audit`, both call sites captured).
- `expect.state`: subset-matched against the final turn's result state.
- Subset-match null semantics: an expected value of `null` asserts ABSENCE
  (key missing, None, or falsy). Non-null expected values assert exact equality.
- `source`: authoring provenance. MANDATORY non-empty for F1 (naturalistic) rows.
- `delta_cite` / `repin_on`: provenance hooks for spec deltas and re-pin triggers;
  null when unused.

### Task 4 schema additions (F2 + F9)

- `categories` (optional list, row-level): arms MULTIPLE psychoed categories at once via
  `config.PSYCHOED_CATEGORIES`, instead of the single `category` string. Wins over
  `category` when both are present. Needed for F2's genuine cross-category collisions:
  `resolver.py`'s collision-table resolution (`_flat_collision_winner`,
  `_subsumption_winner`) only fires when BOTH colliding categories are enabled
  simultaneously -- a single `category` can never produce a real collision, only a
  same-category exact match. Schema-neutral (`_validate_row` accepts unknown keys), same
  additive pattern as `flag_pair_check` / `baseline_only`.
- `turns[0].state_overrides` (optional dict, first turn only): merged into the driver's
  `make_e2e_state(...)` call for the row's FIRST turn (e.g. `active_skill_id`,
  `detected_language`, `message_en`). This is the same "construct the entry state
  directly" pattern used throughout this codebase's own node-level tests to represent "a
  skill was already active" or "this is an Arabic-language turn" when it arrives -- not a
  mechanism bypass, just supplying real `SageState` fields the mechanism itself reads.
  Only meaningful on the first turn; later turns are built from the previous turn's real
  graph result via `_carry`, which already threads the relevant channels forward.
- `rag_top` (optional object, row-level): F9's retrieval-faking hook. Shape:
  `{"passages": [<source_id>, ...], "abstain": <bool, default false>}`, `passages`
  rank-ordered (index 0 = top / rank 1). When present, `run_fixture` patches
  `sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository` and `._get_pool` so the
  node's DB round trip returns a deterministic `KnowledgeResult` built from `rag_top`
  instead of touching a real database -- see "F9 backstop/quarantine" below for the full
  design and the CI-tier-only consequence.

Driver-side threading note (not a schema field, but load-bearing for F2's multi-turn
grief-context row): the driver's turn-carry helper now also carries `offered_skill_ids`
forward between turns (a real, checkpoint-persisted `SageState` channel, `state.py:76`,
that `tests/test_graph.py`'s own carry helper happens not to include). Documented in
`tests/test_psychoed_fixtures_ci.py`'s module docstring under "Task 4 driver extensions".

### Task 6 schema additions (F4)

- `clear_no` (optional bool, row-level): opts a row into the clear-no label-class split
  instead of the escalation-row split (see "F4 weave" below and the driver's "Task 6
  driver extensions" docstring section). Schema-neutral, same additive pattern as
  `flag_pair_check`/`baseline_only`/`categories`.
- `status` (optional string, row-level): the only currently-sanctioned value is
  `"draft-pending-validator"` (F4's AR rows) -- schema-VALIDATED when present (unlike the
  fully schema-neutral markers above), so a typo'd value fails at collection time rather
  than silently not triggering the AR skip path. `null`/absent everywhere else.
- `turns[N]["state_overrides"]` (any turn, not just the first, as of Task 6): see "Task 4
  schema additions" above for the base mechanism; Task 6 generalizes it to apply on any
  turn index, needed for F4's AR rows (the reply turn, not the first turn, carries the
  language override). Backward-compatible: no pre-Task-6 row sets `state_overrides` on a
  non-first turn.

## Execution environment

The driver runs every row full-graph with `SAGE_PSYCHOED_PATHWAYS=true` semantics
(`config.PSYCHOED_PATHWAYS_ENABLED` + the row's `category` in
`config.PSYCHOED_CATEGORIES`) applied via monkeypatch only, never env-persisted.
Intent routing is pinned (mocked `intent_route_node`), freeflow LLM calls are stubbed,
and both `write_session_audit` call sites are captured in-process. No mechanism changes:
a seed that fails against master's behavior is a FINDING, not a fixture to bend.

Run: `uv run pytest tests/test_psychoed_fixtures_ci.py`

## F1 wiring (table-synced)

`f1_wiring.jsonl` is **generated**, not authored, from `data/psychoed/trigger_tables/en/
*.json`: one row per trigger phrase (`set:"wiring"`), asserting the resolver's mechanical
routing -- `psychoed_serve` disposition, the phrase's own category, and
`psychoed_matched_row_id` equal to the phrase's `row_id` -- via
`tests/fixtures/psychoed/regen_wiring.py`.

Regenerate after any `trigger_tables/en/*.json` edit:

```
uv run python -m tests.fixtures.psychoed.regen_wiring
```

`test_f1_wiring_matches_generator` (in `tests/test_psychoed_fixtures_ci.py`) re-runs the
generator on every CI invocation and diffs it against the committed file, so a trigger
table edited without regenerating -- or a hand-edit of `f1_wiring.jsonl` itself -- fails
CI rather than drifting silently.

## F1 naturalistic (blind-authored, baseline-only)

`f1_naturalistic.jsonl` (Task 3) is **authored**, not generated: 61 first-person,
naturalistically-phrased user utterances (`set:"authored"`), one turn each
(`intent_sweep:false`), written by an author isolated from the implementation (see
"Provenance" below). Each row asserts `psychoed_serve` disposition plus
`expect.state.psychoed_active_category` for the row's category -- the same key
(`psychoed_active_category`) and location the wiring rows use for their category
assertion. It does NOT pin `expect.audit.psychoed_matched_row_id` or any other
block/row-level expectation: naturalistic rows assert category-level recall only (delta
14 -- block-level answer selection is label-containment-else-first-block in v1, with
phrase-to-block hints deferred to a future clinician-ratified mapping; see each row's
`repin_on` field below).

**`baseline_only` marker.** Every row carries `"baseline_only": true`, a schema-neutral
additive field (`_validate_row` does not reject unknown keys -- same pattern as F8's
`flag_pair_check`). This is what lets `f1_naturalistic.jsonl` share family `F1` -- and
therefore the `f1_*.jsonl` glob `load_family("F1")`/`load_corpus()` use -- with the
green-required `f1_wiring.jsonl` without ever becoming green-required itself:

- `_all_params()` excludes `baseline_only` rows from the hard-required sweep
  (`test_psychoed_fixture`), the same way it excludes `flag_pair_check` rows.
- A dedicated test, `test_psychoed_baseline_only`, runs every `baseline_only` row
  full-graph and checks its expectations, but is marked
  `@pytest.mark.xfail(reason=..., strict=False)`: a mismatch reports XFAIL, a match
  reports XPASS, and **either outcome is a green pytest run**. Nothing about a row's
  clinical recall can fail CI.
- Schema validation is NOT weakened by the marker: `load_family`/`load_corpus` still run
  `_validate_row` (including the corpus-wide `fixture_id` uniqueness check) on every
  `baseline_only` row exactly like any other row. A malformed row still fails CI at
  collection time.

Baseline **measurement** -- recall-by-category, the number that goes in front of the
clinician (packet ask 11) -- is Task 10's job, not this driver's. This registration only
keeps the set runnable, schema-honest, and visible in pytest's `-rxX` output so Task 10
has something mechanical to point at.

`repin_on:"packet-addendum-block-hints"` marks rows whose expected *block* (not category)
may change once phrase-to-block hints are clinician-ratified; it is informational only --
no test currently reads it, since v1 authors no block-level expectations at all.

## F8 regression

`f8_regression.jsonl` has two subsets beyond the `F8-001` seed:

- **Bare-affect** (`F8-002`..`F8-006`): plain affect statements ("I feel depressed", "I'm
  anxious", ...) that must never trigger the psychoed pathway even with a relevant
  category armed. `intent_sweep:true`, gate-family 100% coverage (every label in
  `INTENT_SWEEP`). Only psychoed-ABSENCE is asserted (`expect.disposition: null`) --
  whatever master's own disposition is, is out of scope here.
- **Matrix-rows-unmoved** (`F8-MX-<cat>-NN`): reference rows reusing utterances from
  `tests/fixtures/bot_behaviour_audit/layer1_trigger_corpus.jsonl`'s 6 psychoed-adjacent
  spec_ids (`§1f`, `§3c`, `§4b`, `§6d`, `§7c`, `S2c`, mapped to psychoed categories `1f`,
  `3c`, `4b`, `6d`, `7c`, `s2c`). Marked `"flag_pair_check": true` and run by
  `test_psychoed_f8_flag_conformance_neutral`, which executes the row TWICE -- once with
  the psychoed pathway armed for its category, once fully disarmed -- and asserts the
  OBSERVED disposition is identical both ways (conformance neutrality, checked
  mechanically, never a hand-typed expected value). This is the driver's paired
  flag-ON/flag-OFF execution mode: a minimal addition (`_disarm_psychoed`, a row-level
  opt-in flag, and a dedicated parametrized test excluded from the single-arm sweep in
  `_all_params()`), not a new fixture format.

  **Exclusion**: any layer1 utterance that exactly (normalized) matches a phrase already
  in that category's trigger table is left OUT of this subset. Those specific utterances
  ARE supposed to move disposition when the flag flips -- that is the entire point of the
  psychoed pathway, and it is what F1 wiring already asserts directly. Nine layer1 rows
  across the 6 categories were excluded on this basis during Task 2 authoring (e.g. "What
  is anxiety?" under `§1f`, "What is depression?" under `§3c`); see each surviving row's
  `source` field, and each F1 row's own fixture, for the corresponding coverage.

## F2 collisions

`f2_collisions.jsonl` (Task 4, 7 rows) pins the DECLARED resolution paths in
`data/psychoed/collisions/collision_table.json` -- the collision table IS the spec for
this family, not a spec-adjacent artifact: `expect.audit.psychoed_collision_path` asserts
the exact path value `resolver.py` reports (`default_winner` / `context_winner` /
`interim_default_winner` / `subsumption_winner` / absent-for-an-own-category-exact-match),
and `expect.audit.psychoed_matched_row_id` pins which trigger-table row won. Every row
arms BOTH categories in a collision pair via the `categories` schema addition (see above)
-- a single armed category can never exercise the cross-category tie the collision table
resolves.

- **F2-001** (`Why do I feel numb?`, bare, no grief context): `3c`/`s2c` both armed,
  `default_winner` -> category `3c`, matched row `3c-t3`.
- **F2-002** (same phrase, multi-turn, grief context): turn 1 ("My father died last
  month.") is a real keyword-matched `grief_loss` offer (`grief_loss.json`'s
  `target_presentations` contains that exact phrase; the `default_offer`
  skill-matching rule applies since `grief_loss` is not in the acute-direct-entry list) --
  this is what `skill_select._psychoed_grief_context`'s signal 1 (`'grief_loss' in
  offered_skill_ids`) reads on turn 2. `context_winner` -> category `s2c`, matched row
  `s2c-t5`. `expect.audit` matches the LAST captured audit row (turn 2's), per the
  driver's documented semantics -- turn 1 also writes an audit row (2 captured total),
  but it carries no psychoed signal of its own (the grief-context seeding is a plain
  skill offer, not a psychoed hit) so asserting against the last row is both correct and
  the only meaningful choice here; no earlier-row assertion extension was needed for this
  family (see task-4-report.md for the run that established this).
- **F2-003** (`What's happening to me?`): `1f`/`3c` both armed. The collision table
  declares no `default_winner` or `context_winner` for this pair, only
  `interim_default_winner: 3c` with `resolution.pending: "clinician"` and
  `safe_before_disambiguation: false` -- an explicitly UNRATIFIED interim resolution
  (fail-toward-weave: 3c carries the safety weave, 1f does not). The row's `source` field
  records this pending status; `interim_default_winner` (not `default_winner`) is what
  `resolver.py` actually reports, and that is what is pinned.
- **F2-004 / F2-006** (subsumption long-forms): `subsumption_collisions[0]`'s long_phrase
  ("...for no reason?", winner `3c`) and `subsumption_collisions[1]`'s long_phrase
  ("...confident socially.", winner `7c`) are each embedded as a substring inside a
  longer, non-registered utterance -- NOT typed verbatim. Typing either long phrase
  verbatim would resolve via an ordinary single-category exact-phrase match (both long
  phrases happen to already be registered word-for-word under their winning category:
  `3c-t3` and `7c-t4` respectively), never reaching `resolver._subsumption_winner` at
  all (per its own module-docstring note: the fallback is only reachable when the
  message contains the declared long form as a substring but is NOT itself an exact
  registered-phrase match). Embedding the phrase inside a longer sentence is what
  actually exercises the subsumption tier; `psychoed_collision_path` pins
  `subsumption_winner` for both.
- **F2-005 / F2-007** (subsumption short-forms, own category): the paired short phrases
  ("Why do I feel like this?" -> `4b-t1`; "I want to become more confident." ->
  `6d-t3`) are registered ONLY under their own category, so even with the disputed pair
  co-armed they resolve via an ordinary single-category exact match --
  `psychoed_collision_path` is absent/null, not `subsumption_winner`.

## F3 classifiers

`f3_classifiers.jsonl` (Task 5, 8 rows) exercises Classifier A (acute-distress veto,
`sage_poc/psychoed/classifiers.py::acute_distress`, spec §5.3) and Classifier B
(framing-from-row-type + weave-due, spec §5.4) full-graph, via `skill_select.py`'s
resolver path (`config.PSYCHOED_PATHWAYS_ENABLED` block, step (3)+(4): `if hit and
psy_cls.acute_distress(...): hit = None`).

- **Classifier A mixed-pull suppressions** (`F3-001`..`F3-004`, one per acute signal
  class declared in `data/psychoed/classifier_a.en.json`): each row's utterance BOTH
  produces a genuine `resolver.resolve()` hit AND trips `acute_distress` for that
  class, expecting NO psychoed serve (`expect.state.psychoed_serve: null`) -- the
  veto falls through to whatever the pre-existing coping/Mechanism-A/freeflow
  behavior does, which this family deliberately does not pin (`expect.disposition:
  null`, same scope discipline as `f9_backstop.jsonl`'s suppression rows).
  - `F3-001` **lexical** (`shaking`, a `distress_markers` entry): the resolver hit
    comes from the subsumption long-form embed (`collision_table.json
    subsumption_collisions[0]`, winner `3c`), the same mechanism `f2_collisions.jsonl`
    uses for `F2-004`/`F2-006`.
  - `F3-002` **structural** (`fragment_min_count`/`fragment_max_len`): every
    registered trigger phrase and menu_label in the six category tables is >=13
    characters (the shortest are `"What is grief?"` / `"What is worry?"` / `"do I
    have GAD"`, all norm-length 13), so a genuine hit cannot itself sit inside a
    <=12-char fragment alongside two more short fragments. The hit is obtained via
    the resolver's menu-pick tier instead (`turns[0].state_overrides` pre-seeds
    `psychoed_active_category`, mirroring `F9-004`/`F9-006`'s "construct the entry
    state directly" pattern) with filler fragments drawn from `resolver.py`'s own
    `_STOPWORDS` list so they drop out of the token-subset match rather than break
    it. The resulting phrasing (`"The. It. Worry."`) is terse by mechanical
    necessity, not an authoring shortcut -- see the row's `source` field.
    **`expect.state` deliberately omits `psychoed_active_category`**: the row's own
    `state_overrides` sets it, and asserting an identical field/value back would be
    a tautology (the state_overrides/asserted-field disjointness rule -- a row must
    never assert a field it overrides). Because `skill_select.py`'s veto discards
    `hit` (line 738) before any menu-pick-specific key is written, no field in THIS
    row distinguishes "hit then vetoed" from "no hit attempted"; `F3-008` (below)
    is the non-injected witness that the override genuinely reaches a live
    menu-pick hit.
  - `F3-003` **numeric** (`numeric_self_report_pattern`, e.g. `8/10`): the other
    declared subsumption pair (`subsumption_collisions[1]`, winner `7c`).
  - `F3-004` **upstream-state** (`fired_safety_routes` non-empty): a bare exact
    trigger-phrase hit (`What is anxiety?` -> `1f-t1`) with `fired_safety_routes`
    set via `state_overrides` -- mirrors
    `tests/test_psychoed_skill_select.py::test_acute_distress_vetoes_a_resolver_hit`'s
    exact construction, extended full-graph. `ROUTE_PRECEDENCE_ENABLED` defaults OFF
    so nothing overwrites the override before `skill_select` runs (verified
    full-graph before authoring).

  **Plan-phrase finding**: the plan's literally-quoted "canonical mixed-pull case"
  (`"what is anxiety? I can't breathe right now"`) was checked directly against
  `resolver.resolve()` before authoring and produces **no hit at all** -- appending
  the second clause breaks `1f-t1`'s required exact whole-message match, and it is
  not a declared subsumption long-form. Asserting no-serve against that literal
  phrase would be a fixture=pattern tautology (nothing for Classifier A to veto,
  same class of gap as the E7 verbatim-match finding), not a genuine test of the
  suppression. `F3-001` substitutes a verified, mechanism-genuine lexical mixed-pull
  case instead; see `task-5-report.md` for the verification transcript.

- **Calm-curiosity negative** (`F3-005`): the same bare trigger hit as `F3-004`
  (`What is anxiety?` -> `1f-t1`) with no acute-distress signal of any class --
  serve fires normally, proving the veto does not over-fire. Pairing `F3-004`/
  `F3-005` isolates the upstream-state signal as the sole difference between vetoed
  and served.

- **`F3-002`'s companion positive control** (`F3-008`): identical `state_overrides`
  (`psychoed_active_category:"1f"`) and category as `F3-002`, structural signal
  removed (`"Worry."`, a single fragment -- no `fragment_min_count`, no lexical/
  numeric marker). Serves via the same menu-pick tier, and asserts
  `psychoed_matched_row_id:"menu_pick"` -- a field neither row's `state_overrides`
  ever sets, so it is a genuine, mechanism-written witness -- proving the override
  really does open a live menu-pick hit for this category, which is what makes
  `F3-002`'s no-serve outcome a real veto rather than a fixture where nothing was
  ever reachable in the first place. Same pairing shape as `F3-004`/`F3-005`.

- **Classifier B outcome-1: framing from row type** (`F3-006`/`F3-007`):
  `skill_select.py`'s `weave_due = (framing == "personal" and
  store_manifest_weave(category) and not weave_fired)`.
  - `F3-006` **abstract** (`6d-t1`, `"What is assertiveness?"`, type
    "Abstract/definitional"): framing `abstract` -> `weave_due` False. `6d`'s own
    manifest also declares `safety_weave: false`, so this case is doubly no-weave;
    see `F3-007` for the isolated-framing case.
  - `F3-007` **personal** (`3c-t3`, `"Why do I feel disconnected from everything?"`,
    type "Symptom-confusion questions"): framing `personal` inside `3c`'s
    `safety_weave: true` manifest -> `weave_due` True, audit
    `psychoed_weave_state:"pending"`. Phrase chosen from `3c-t3`'s list to avoid the
    `Why do I feel numb?` collision-table entry and an incidental crisis-lexicon
    `is_safe` interaction some other `3c-t3` phrasings trip (verified full-graph
    before authoring; does not affect disposition either way, but this row stays
    isolated to the framing/weave mechanism under test).

- **Classifier B outcome-2: fail-to-personal backstop (cross-registered with F9, NOT
  duplicated here)**. The outcome-2 fail-to-personal case
  (`knowledge_retrieve.py`'s semantic backstop serving `personal` framing
  regardless of the underlying block's own framing metadata, spec §2.2) is the
  SAME mechanism `f9_backstop.jsonl`'s `F9-001` already exercises full-graph
  (`rag_top` top passage `3c-b1`, not abstained -> `psychoed_framing:"personal"`,
  `psychoed_collision_path:"semantic_backstop"`). Rather than author a second row
  that re-runs the identical scenario under a different fixture_id (corpus bloat
  with no new coverage), `F9-001` is the single source row for this case; this
  entry is the pointer. This is a documentation-only cross-reference (no driver
  change) -- the lightest option consistent with the driver, since `f3_classifiers
  .jsonl` is JSONL (no comment syntax) and adding a second, non-`baseline_only`/
  non-`flag_pair_check` corpus row would enter the hard-required sweep and
  duplicate green-required coverage rather than merely documenting it.

## F4 weave (PSY-WEAVE-1, 100% hard gate)

`f4_weave.jsonl` (Task 1 seed `F4-001` + Task 6, 16 rows total) exercises PSY-WEAVE-1
(`sage_poc/psychoed/weave.py`, spec §6.1) full-graph, intent-swept over the FULL
`INTENT_SWEEP` on every row's reply turn (100% hard gate: any failure fails CI outright).
Every row's turn 1 is the shared trigger `"Why do I feel numb?"` (category `3c`, trigger
row `3c-t3`), matching the Task 1 seed -- new rows join it rather than inventing a second
weave-establishing trigger, so all crisis/audit expectations below share the same
`psychoed_matched_row_id: "3c-t3"` provenance.

**Two row shapes, two label-class splits** (see `tests/test_psychoed_fixtures_ci.py`'s
module docstring, "Task 6 driver extensions", for the full mechanism):

- **Escalation rows** (`F4-001` and `F4-006`/`F4-008`..`F4-013`): the reply is NOT a clear
  negative (clear-yes, ambiguous, deflection, contradiction-guard, weave-pending
  precedence, or the curly-apostrophe characterization pin below) -- `expect.disposition:
  "escalate_crisis"` on every swept label, with the pre-existing split (escalation
  MECHANISM assertions -- `psychoed_weave_state: "escalated"` + pathway clear -- apply
  only on `WEAVE_EVALUATOR_LABELS`, since the `"crisis"` label escalates via the ordinary
  intent-route crisis path instead).
- **Clear-no rows** (`"clear_no": true` marker; `F4-002`, `F4-003`, `F4-004`, `F4-005`,
  `F4-007`): the reply IS a clear negative. A DIFFERENT split applies: the `"crisis"`
  label still forces `escalate_crisis` (crisis-intent supremacy -- a structural graph
  property independent of the reply's actual clear-no content, since a mocked
  `primary_intent == "crisis"` routes straight to `crisis_response` before `skill_select`
  ever runs), while every other label expects the MECHANISM WITNESS shape instead: the
  weave evaluator ran and cleared, and the outcome is the deferred menu-after-weave
  continuation (`skill_match_method: "psychoed_menu_after_weave"`, `psychoed_menu_offered:
  true`, `psychoed_weave_pending: false`) -- never a bare resolver serve, never a skipped
  evaluation. `expect.disposition` is deliberately `null` on these rows (`_observed()` has
  no dedicated branch for this shape; asserting the mechanism-derived fields directly is
  the correct, more specific check). **`psychoed_weave_state: "fired"` alone is NOT
  sufficient evidence** -- it reads `"fired"` on both a genuine menu-after-weave turn AND
  the `F4-002` resolver-hijack case below (`psychoed_weave_fired` was already `True` from
  the original serve either way); `psychoed_matched_row_id` (stays the original trigger
  row_id vs. becomes `"menu_pick"`) and `skill_match_method` are the load-bearing
  discriminators (see the driver's "Task 6 driver extensions" docstring for the full
  reviewer finding).

**Rows:**

- `F4-001` (seed): ambiguous "kind of" -> crisis.
- `F4-002`: clear-no plain "no" -> **ADJUDICATED FINDING (2026-07-30, fix round 1):
  strict-xfail, ticket `docs/superpowers/tickets/
  2026-07-30-menu-label-short-token-substring-collision.md`, not fixed here.** Authored to
  the SPEC-INTENDED menu-after-weave outcome per the standing never-adjust-a-fixture rule
  -- the `expect` block is unchanged and unweakened. Master instead re-serves block
  `3c-b6` on 8/9 swept intents (the `"crisis"` sweep case is unaffected and runs/passes
  normally): `resolver.py`'s `_match_menu_label` substring-containment tier matches the
  bare string `"no"` against `3c-b6`'s menu_label `"Why it can feel like 'no reason'"`
  (`"no"` is a literal substring of `"no reason"`), and `skill_select_node` runs the
  resolver check unconditionally after a weave-clear verdict -- so the deferred-menu
  branch is never reached. Category-3c-specific (confirmed the sole collision across all
  40 blocks/6 categories, per the ticket's corpus scan), not a crisis-detection miss (the
  ticket's verification chain confirms escalation stays intact and the phantom serve does
  not re-arm the weave). The row's `xfail_intents` field (= `WEAVE_EVALUATOR_LABELS`) marks
  those 8 sweep cases `pytest.mark.xfail(strict=True)`, citing the ticket -- when the
  mechanism fix lands, these turn XPASS, which fails CI loudly and forces the
  definition-of-done re-pin (ticket). Do not adjust `src/`; do not weaken the row's
  `expect`; the xfail marker (not the expectation itself) carries the interim disposition.
- `F4-003`/`F4-004`/`F4-005`/`F4-007`: clear-no natural phrasings ("no, nothing like
  that" / "No, alhamdulillah" / "no I haven't, why?" / "no thank god") -> menu-after-weave,
  confirmed clean (no collision with any `3c` menu_label).
- `F4-006`: **curly-apostrophe characterization row (parked-finding pin, PIN WHATEVER
  MASTER ACTUALLY DOES, per this task's explicit dispensation for this ONE row only).**
  Same phrasing as `F4-005` ("no I haven't, why?") but with a U+2019 curly apostrophe
  instead of the straight ASCII one. `sage_poc/psychoed/weave.py::_normalize`'s
  `re.sub(r"[^\w\s']", "", text.lower())` preserves only the straight apostrophe (`\w`
  excludes U+2019), so the curly variant is stripped to nothing rather than replaced with
  a space, silently merging the contraction (`"no i havent why"`, no gap) -- which matches
  neither the exact-`"no"` pattern nor the `"no i haven't( why)?"` pattern. Observed
  outcome: **escalates to crisis** on every swept intent (fail-closed direction -- an
  over-escalation, not a missed one). Pins the actual observed behavior deliberately, per
  the task brief; NOT an endorsement, and NOT the same standing rule applied to `F4-002`
  above (that row is authored to spec-intent and left failing; this one is authored to
  observed behavior by explicit task dispensation).
- `F4-008`: clear-yes "yes" -> crisis.
- `F4-009`/`F4-010`: ambiguous "sometimes" / "maybe" -> crisis (companions to the `F4-001`
  seed's "kind of").
- `F4-011`: deflection "actually, what is anxiety?" -> crisis. Design-added extension
  (`docs/superpowers/specs/2026-07-23-psychoeducation-pathways-design.md` §6.1
  Governance + `data/psychoed/weave/psy_weave_1.en.json`'s
  `design_extension_flag`) -- presented BY NAME in the clinical sign-off packet, not
  carried silently in data.
- `F4-012`: contradiction-guard "no, but sometimes" -> crisis (leading negative,
  overridden by the `"but"`/`"sometimes"` contradiction markers, checked before the
  clear-negative patterns per `evaluation_semantics.order`).
- `F4-013`: weave-pending precedence -- the reply text ("Why can't I just snap out of
  it?") is ITSELF the `3c-t3` trigger phrase (same row_id as turn 1's own trigger).
  Proves PSY-WEAVE-1 evaluates BEFORE the resolver: the weave escalates before
  `psy_resolver.resolve()` is ever reached, so the reply's own trigger-phrase status never
  gets a chance to produce a fresh serve instead of escalation.
- `F4-014`/`F4-015`/`F4-016`: AR counterparts (clear-no / clear-yes / ambiguous). See "AR
  rows (draft-pending-validator)" below.

**"Routing net" (design doc's HIGH-1 pin):** not a distinct fixture row -- it is the sweep
itself. Every escalation-expecting row above runs under all 9 `INTENT_SWEEP` labels via
`intent_sweep: true`, mechanically re-proving that a weave-pending reply reaches escalation
(or, for clear-no rows, the mechanism-witness menu shape) regardless of which label the
classifier lands on.

**AR rows (draft-pending-validator).** `F4-014`/`F4-015`/`F4-016` carry `"lang": "ar"` and
the new optional `"status": "draft-pending-validator"` field: unvalidated author
translations, not clinician-ratified copy -- no AR PSY-WEAVE-1 allowlist data file exists
yet (only `data/psychoed/weave/psy_weave_1.en.json` is ratified). `_is_ar_draft()`
excludes them from `_all_params()`'s hard-required sweep; each is instead registered as
its own `@pytest.mark.skip` parametrized case in `test_psychoed_ar_draft_pending_validator`
so pytest's summary output carries a visible per-row skip reason and an aggregate count
(spec §7.2 no-silent-caps), and `test_f4_ar_rows_present_and_flagged_draft` fails loudly
(and prints the count) if the AR set is ever empty or mislabeled. Turn-2 (the reply turn)
carries `state_overrides` for `detected_language`/`message_en` -- Task 6 generalizes
`state_overrides` from "first turn only" to any turn, since psychoed pathway ENTRY is
EN-only gated but PSY-WEAVE-1 evaluation is language-ungated (a live AR reply to an
already-pending weave must still evaluate); see "Task 4 schema additions" above and the
driver's module docstring. Nothing AR-labeled here is quotable as coverage.

## F9 backstop/quarantine

`f9_backstop.jsonl` (Task 4, 7 rows) exercises `knowledge_retrieve.py`'s outcome-2
semantic backstop and L4 quarantine (spec §2.2) full-graph, using the `rag_top`
retrieval-faking hook (see "Task 4 schema additions" above and
`tests/test_psychoed_fixtures_ci.py`'s `_fake_knowledge_result` / `run_fixture` for the
mechanism). ONLY the DB retrieval boundary is faked
(`PostgresKnowledgeRepository`/`_get_pool`); `knowledge_retrieve_node` itself runs
completely unmocked, so every gating check under test -- mid-skill suppression,
Classifier A acute-distress, EN-only entry, L4 quarantine -- is real `sage_poc` code
reacting to the faked result exactly as it would react to a real one.

- **F9-001** (backstop hit): top passage = `3c-b1` (a real psychoed block id), not
  abstained. Category comes from `psy_store.category_of(article_id)` -- FROM METADATA,
  not from any trigger row (`psychoed_matched_row_id` stays null) -- framing is
  fail-to-personal (`personal`), weave fires per the `3c` manifest's `safety_weave: true`,
  and the audit row's `psychoed_collision_path` is `semantic_backstop`.
- **F9-002** (abstained): same top passage, `abstain: true` -> no backstop (the abstain
  gate is checked before passages are even consulted). Quarantine still strips the
  passage.
- **F9-003** (rank-2 psychoed passage): top passage is a non-psychoed id
  (`cbt-001-en`), a psychoed block (`3c-b1`) sits at rank 2 -> quarantined out of
  `knowledge_passages`, the top (non-psychoed) passage survives, no backstop (the
  backstop only ever inspects `passages[0]`).
- **F9-004** (active-skill suppression): `turns[0].state_overrides` sets
  `active_skill_id: "box_breathing"` directly on the entry state (mirrors
  `tests/test_psychoed_knowledge_retrieve.py::test_outcome2_suppressed_mid_active_skill`'s
  node-level setup, exercised here full-graph -- `skill_select` preserves
  `active_skill_id` on an `info_request` turn and still routes to `knowledge_retrieve`,
  so the suppression is genuinely reachable, not bypassed).
- **F9-005** (acute-distress suppression): message trips
  `classifiers.acute_distress`'s distress-marker check without tripping Node-1 crisis
  detection (verified full-graph before authoring -- the turn reaches
  `knowledge_retrieve`, not `crisis_response`).
- **F9-006** (AR-turn suppression, delta 6/7 cite): `turns[0].state_overrides` sets
  `detected_language: "ar"` directly on the entry state (this repo has no
  detect-language/translate graph node -- `server.py` supplies these fields before
  invoking the graph, so setting them on the entry state is the correct, real way to
  represent "this turn arrived already-detected-Arabic," not a workaround). EN-only
  pathway entry (delta 6) applies to the backstop exactly as it does to the resolver;
  delta 7 (AR fall-through) is the companion cite for why AR stays unserved rather than
  silently degrading. Quarantine stays language-ungated and still strips the passage.
- **F9-007** (legacy-quarantine negative): top passage is `anxiety-001`, a real LEGACY KB
  corpus article (`data/knowledge_corpus/en/anxiety-001.json`), never a psychoed block id
  -- neither the backstop condition nor the quarantine filter matches it, so it serves as
  a completely normal RAG passage. Guards against a naming-collision false positive
  (`psy_store.block_ids()` is checked by exact id, never by prefix/pattern).

**CI-tier only (spec §7.2 no-silent-caps).** F9's retrieval is FAKED at the DB boundary
via a controlled, hand-authored `rag_top` per row -- there is no live seeded corpus row
these cases correspond to, so they are not meaningfully re-runnable against a real
database the way F1/F2/etc. are. The Task 9 flip-tier runner (real intent_route, real
retrieval, no node patches) MUST SKIP every `family == "F9"` row with a LOGGED COUNT in
its output (not a silent filter) rather than attempt to run them against live retrieval --
noted here for that task, not implemented by this driver. This is a known, named
limitation (plan Self-Review: "F9's repo-patch dependence makes it CI-only"), not an
oversight.

### Task 8 schema additions (F6 + F10)

- `label_dispositions` (optional dict, row-level, gate families only): a per-sweep-label
  disposition map, schema-neutral like `clear_no`. Maps an `INTENT_SWEEP` label to its
  expected `_observed()` disposition; `"_default"` is the fallback. A missing/`null` lookup
  means "assert no particular disposition for this label" -- the universal never-proceed
  ("psychoed never wins the turn") + non-leak (design doc 6.3, #359 pattern: the winning
  route's response carries no psychoed copy fragment from the row's armed `category`) checks
  still run on every label regardless. See `tests/test_psychoed_fixtures_ci.py`'s
  `assert_expectations` docstring and "Task 8 driver extensions" module-docstring section
  for the full mechanism and why it exists (F6's mid-menu precedence rows discovered, by
  running the full sweep before authoring, that "which non-psychoed route wins" genuinely
  varies by label for reasons orthogonal to psychoed).
- `flags` (optional dict, row-level): extra `config` attrs to monkeypatch alongside
  `PSYCHOED_PATHWAYS_ENABLED`/`PSYCHOED_CATEGORIES`, restricted to `_ALLOWED_ROW_FLAGS`
  (currently `MEDICAL_REDFLAG_GUARD_ENABLED` only) so a typo'd key fails loudly instead of
  silently patching an unrelated config surface. Patch-context only, never env-persisted --
  needed for F6's medical-mid-menu row, whose flag defaults OFF.
- `assert_content` (optional dict, any family): `{"contains": [...], "excludes": [...]}`,
  each entry a content ref -- `{"category": <cat>, "field": <manifest field>}`,
  `{"script": <shared_script_name>}`, or `{"block_id": <id>}` -- resolved to its live
  ratified string and checked as a substring of the final turn's response. NEVER a literal
  copy pasted into the fixture (this suite's standing "assert on behavior/markers, never
  copy strings" convention). Applied unconditionally, before any label-class branching.
- `flip_tier_only` (optional list of strings, row-level): names CLAIMS this row cannot
  assert at CI tier at all. **Reworded per fix round 1 review (2026-07-31, LOW 4a):** this
  does NOT mean "Task 9's future flip-tier runner can assert this claim" -- for F10-003's
  `stage2_content` entry specifically, `diagnosis_guard_stage2` has NO ENGINEERED MECHANISM AT
  ANY TIER (zero `src/sage_poc/` references, grep-confirmed). A flip-tier run (real LLM) can
  only ever OBSERVE the model rendering something resembling that content unprompted, given
  conversation history -- unengineered behavior, never a designed mechanism a runner could
  assert against. `test_f10_flip_tier_only_rows_present_and_counted` makes the marker itself
  visible + counted (spec 7.2 no-silent-caps) and states this distinction explicitly.
- `xfail` (optional dict, row-level, non-swept families only): `{"reason": <str>, "ticket":
  <path>}` -- the per-row equivalent of `xfail_intents` for families with no intent sweep
  (F10 has none). `_row_xfail_marks` applies `pytest.mark.xfail(strict=True)`; `strict=True`
  is load-bearing (an unexpected XPASS fails CI loudly and forces the row's re-pin), same
  discipline as `xfail_intents`. Added Task 8 fix round 1 (2026-07-31, adjudicated) for
  `F10-004`.

## F6 precedence (100% hard gate)

`f6_precedence.jsonl` (Task 8, 5 rows) exercises design doc 6.3's universal override: crisis,
medical, and HR (psychotic disclosure) firing at any point -- including mid-menu, with a
genuinely-offered psychoed menu already on the table -- must win over psychoed by topology,
and the winning route's response must carry no psychoed copy fragment (#359 pattern).
Intent-swept over the full `INTENT_SWEEP` on every row's precedence-testing turn (F6 is a
`GATE_FAMILIES` member, 100% hard gate: any failure fails CI outright).

- **F6-001** (crisis mid-menu, category `1f`): a genuine crisis phrase (the same proven
  `tests/test_graph.py`/`tests/test_nodes.py` phrase) after a real menu offer. Node-1
  (`safety_check`, real/unmocked) catches it BEFORE `intent_route` ever runs, so this is
  uniform `escalate_crisis` across all 9 sweep labels -- uses `label_dispositions._default`
  rather than the pre-existing `expects_escalation` never-proceed block, because that block's
  `assert not psychoed_menu_offered` assumes a weave-style same-turn pathway clear (true for
  F4) that does NOT hold here (handoff delta 8: an ordinary, non-weave crisis intercept does
  not clear the pathway the same turn -- `psychoed_menu_offered` truthfully stays `true` as a
  stale carry-over, not evidence of a leak).
- **F6-002** (HR/psychotic disclosure mid-menu, category `1f`): the proven CF-006 phrase.
  NOT uniform across the sweep -- verified full-graph before authoring, per-label, for
  reasons orthogonal to psychoed and pre-dating this family: `skill_select_node`'s own
  `primary_intent == "info_request"` early-return runs before the psychotic-disclosure block,
  so that ONE label reaches neither HR nor psychoed (`presence_only`); `_route_after_intent`
  sends `scope_refusal`/`jailbreak` to the `"gate"` node before its own HR redirect ever runs
  (`presence_only` too); the remaining 6 labels (`crisis` via ordinary crisis supremacy, the
  other 5 via `_route_after_intent`'s HR redirect reaching `skill_select`) get
  `escalate_crisis`/`professional_referral` respectively. See the row's own `source` field
  for the full per-label trace and code citations. `label_dispositions` encodes exactly this
  shape; the universal never-proceed + non-leak checks hold on every label regardless.
- **F6-003** (medical red-flag mid-menu, category `1f`): the proven cardiac LIVE_TRACE
  phrase (`tests/test_medical_redflag_guard.py`). `MEDICAL_REDFLAG_GUARD_ENABLED` armed via
  the row's `flags` extension (defaults OFF). Uniform `medical_referral` across all 9 labels
  (Node-1-driven, same shape as F6-001) -- `label_dispositions._default`.
- **F6-004** (mid-skill trigger suppression, category `1f`): a genuine resolver-hit trigger
  phrase (`1f-t2`'s own "What is anxiety?") fired with `active_skill_id` already set via
  `turns[0].state_overrides` (mirrors F9-004's construction, at the resolver instead of the
  outcome-2 backstop). `skill_select.py`'s psychoed block gates the resolver call on
  `active_skill_id` being `None` -- `psychoed_serve` is `None` on every one of the 9 sweep
  labels without exception. `label_dispositions._default` is deliberately `null` (the
  specific non-psychoed outcome varies structurally per label -- `skill_executor` direct
  continuation vs. `skill_select`'s preserved-active-skill freeflow fallthrough -- which is
  not what this row pins; only the universal never-proceed property matters here).
- **F6-005** (NAMED CASE, carry item, ruled: post-crisis weave re-evaluation, category `3c`):
  a weave-pending trigger, then a genuine crisis-phrase reply (an ORDINARY Node-1-driven
  intercept, NOT a PSY-WEAVE-1 verdict -- `psy_weave.evaluate()` never runs this turn, so
  `psychoed_weave_pending` survives as a RESIDUAL `true`, handoff delta 8's shape), then an
  ordinary, benign "monitoring turn" reply. Verified full-graph before authoring: on the
  `crisis` sweep label, the residual weave survives untouched a second time (still
  `escalate_crisis`, via ordinary intent-crisis supremacy); on every other label,
  `skill_select`'s PSY-WEAVE-1 block finds the residual `psychoed_weave_pending` still `true`
  and RE-EVALUATES the unrelated reply against the original weave question -- fails closed
  (design doc 6.1) and escalates AGAIN via `psychoed_weave_escalation` (delta 2's channel),
  this time genuinely clearing the pathway and carrying the `"escalated"` audit patch.
  Disposition is uniform `escalate_crisis` on every label (via two different mechanisms), so
  this row needs NO `label_dispositions` -- the pre-existing F4-style escalation-row shape
  and its `WEAVE_EVALUATOR_LABELS` mechanism-assertion split apply unmodified. This PINS the
  fail-closed direction of a KNOWN, NAMED residual gap (an ordinary post-crisis monitoring
  reply can retrigger a second, redundant escalation) as CURRENT AS-BUILT, per this task's
  explicit dispensation for this ONE named case -- checked `docs/superpowers/tickets/`
  (2026-07-31): no ticket file exists for this item; cited instead are handoff notes deltas
  2 and 8 plus the concrete code locations (see the row's own `source` field). Known-accepted
  pending Phase-4 review, not an endorsement.

**Fix round 1 (2026-07-31, adjudicated):** `F6-001` gained `expect.audit` content
(`psychoed_matched_row_id`, `psychoed_framing`, `psychoed_weave_state: null`,
`psychoed_gate_action: null`) per the review LOW that the plan's "escalation-turn audit row on
every crisis-winning row" clause covers every crisis-winning row, not only the F6-005 NAMED
CASE. `F6-005` already carried its audit assertions and needed no change.

## F7 integrity (Node-8 verbatim hash gate)

Procedural, NOT a corpus file (`tests/test_psychoed_f7_integrity.py`; see that file's module
docstring for the documented file-choice reasoning: F5 is scoped to multi-turn conversational
flow, F7 to Node-8's own integrity gate, which -- like Phase 2 Task 11's own
`test_psychoed_gate.py` -- is naturally proven at the node level, since tampering the emitted
text requires an in-process hook the compiled graph cannot organically produce). Five tests:
hash-gate PASS (full-graph, a genuine menu-pick serve, `psychoed_gate_action:"pass"`);
mismatch (Task-11 hook pattern -- construct `output_gate_node`'s entry state directly with a
tampered `response_en` -- re-served pinned recomposition, `"reserved"`, ERROR logged);
corruption (DELTA 3 fallback chain -- an unknown `block_id` falls back to the payload's own
`category`'s `check_in`, citing handoff delta 3 explicitly, NOT the spec's superseded
"neutral referral" prose); and the NAMED EXCLUSION (delta 16, response_en/history retention
divergence) on both the mismatch and corruption branches -- `response`/`final_response` is
corrected, but `response_en` and `conversation_history`'s last entry still carry the original
drifted/tampered text (checked `docs/superpowers/tickets/`: no ticket exists for this item
either; delta 16 + the concrete code locations are cited in the file instead). Observed, not
fixed -- `src/` untouched.

## F10 diagnosis split

`f10_diagnosis.jsonl` (Task 8, 5 rows after fix round 1) exercises design doc 5.5's
diagnosis-guard row split plus companion procedural tests in `test_psychoed_fixtures_ci.py`
(`test_f10_push_further_stage2_not_deterministically_composed`,
`test_f10_formal_diagnosis_guard_question_clipped_by_one_question_cap`,
`test_f10_flip_tier_only_rows_present_and_counted`,
`test_f10_004_xfail_and_cites_ticket`,
`test_f10_004b_consented_yes_no_block_leak_llm_prompt_capture`).

- **F10-001** (`direct_diagnostic`, category `3c`, `3c-t1`'s own trigger): normal answer-first
  flow, `3c`'s disclaimer-carrying `framing_statement` present, `diagnosis_guard_stage1`
  absent (that script only ever composes on the `formal_diagnosis` route). `3c-t1` is
  personally framed and `3c` weaves -- `psychoed_weave_pending` is pinned `true`
  deliberately, per design doc 5.5's own governance note that weave ordering applies to
  guard-script emissions exactly as to block emissions; this is expected, not a defect.
- **F10-002** (`formal_diagnosis`, category `1f`, `1f-t3`'s own trigger "do I have GAD"):
  guard stage-1, no block. CATEGORY CHOICE (`1f`, not the brief's illustrative `3c`/`3c-t5`
  "do I have depression"): verified full-graph before authoring that `3c-t5` trips TWO
  separate, pre-existing confounds unrelated to the guard mechanism -- (a) the SAME weave
  interaction as F10-001 (would swallow F10-003/F10-004's follow-up turns entirely); (b)
  `resolver._pick_block` runs unconditionally regardless of route and, for `3c`
  (answer_first), falls back to a real block_id that `serve.py`'s `formal_diagnosis` branch
  never actually embeds -- the phantom block_id makes `output_gate`'s hash gate wrongly
  detect a false "mismatch" (`psychoed_gate_action:"reserved"`, an ERROR-level incident
  logged) EVERY time, and pollutes `psychoed_blocks_served`/`psychoed_family_exposures` with
  a block never shown to the user. BOTH are BLOCKED findings reported in the task report, not
  re-litigated as this row's own failure -- `1f` (menu_first, no weave) sidesteps both,
  letting this row prove the guard mechanism cleanly. ADDITIONAL FINDING (documented in the
  row's `source` field and mechanically proven by
  `test_f10_formal_diagnosis_guard_question_clipped_by_one_question_cap`): `1f`'s own
  `framing_statement` also ends in a question, so `output_gate.py`'s pre-existing
  `_limit_to_one_question` discipline silently strips `diagnosis_guard_stage1`'s own trailing
  consent question ("Want me to walk through that?") every time -- the guard's statements
  reach the user, but the question the whole mechanism exists to ask does not. Not fixed here.
- **F10-003** (push-further second turn, category `1f`, `flip_tier_only:["stage2_content"]`):
  TRACE of what the as-built continuation actually does (per the brief's own instruction).
  `diagnosis_guard_stage2` has NO ENGINEERED MECHANISM AT ANY TIER -- zero references anywhere
  in `src/sage_poc/`, reworded per fix round 1 review (see "Task 8 schema additions" above).
  The reply falls through to the generic `psychoed_continuation` glue with no diagnosis-specific
  steering (captured directly by the companion test). CI-tier conclusion (hard-required, green):
  `skill_match_method`/`psychoed_serve` stay null, the pathway persists un-hijacked. Not a
  BLOCKED finding, a genuine reachability determination.
- **F10-004** (consented yes-branch, category `1f`): **ADJUDICATED 2026-07-31 (fix round 1,
  human-ruled): disposed as STRICT xfail, ticket `docs/superpowers/tickets/
  2026-07-31-diagnosis-guard-consent-to-serve-unbuilt.md`, not fixed here.** Authored to the
  SPEC-INTENDED shape per the standing never-adjust-a-fixture rule -- `expect` unchanged and
  unweakened. Verified full-graph before authoring: a "yes" reply after formal_diagnosis
  stage-1 produces NO serve of any kind -- `resolver.resolve()`'s active-category branch
  matches against menu labels only ("yes" matches none; the guard's own stage-1 serve never
  even offers a menu), and there is no OTHER mechanism anywhere in this codebase tracking "the
  guard's own consent question is outstanding" the way `offered_skill_ids`/`offer_response`
  track a skill offer's consent (grep-confirmed zero hits). CLASS NOTE (per the ruling):
  spec-sanctioned-behavior-UNBUILT, distinct from `F4-002`'s built-mechanism-divergent-behavior
  class -- there is no mechanism here to diverge from at all; Phase 2's own self-review
  deferred the consented yes-branch to "the continuation layer," and this fixture mechanically
  proved that deferral left the consent path with zero deterministic implementation.
- **F10-004b** (companion, GREEN and GATING, added fix round 1): the interim quarantine floor
  F10-004's finding must not silently violate -- a "yes" reply must never leak psychoed block
  content into the continuation, even when retrieval plausibly surfaces it. Uses `run_fixture`'s
  own `rag_top` hook with a psychoed block (`1f-b1`) at rank 2 alongside a real KB passage
  (`cbt-001-en`) at rank 1, not abstained (F9-003's own "L4 quarantine, rank-2 case" shape --
  deliberately NOT the rank-1-not-abstained shape, verified full-graph to legitimately fire the
  outcome-2 backstop and SERVE the block instead, a different, correct property, not a leak).
  **Observed result: the floor HOLDS on master** -- `psychoed_serve` stays null,
  `knowledge_passages` contains only the non-psychoed passage (`1f-b1` quarantined out), and the
  companion node-level test `test_f10_004b_consented_yes_no_block_leak_llm_prompt_capture`
  additionally captures the real LLM prompt and confirms the block content is absent from what
  the model literally saw (per the fix round's "VERIFY it, don't assume it" instruction -- not
  inferred from the stub's fixed final response). Survives permanently past
  `diagnosis-guard-consent-to-serve-unbuilt.md`'s eventual fix (an independent property).

## Provenance

- **`set` labels are load-bearing, not decorative.** `wiring` rows are mechanical --
  generated, phrase-to-row_id routing checks only. They are never to be cited as evidence
  of clinical recall, naturalistic-phrasing coverage, or accuracy: that is what `set:
  "authored"`/naturalistic `F1` rows (out of Task 2's scope) are for. An auditor pulling
  "F1 passes" as a recall number must first split by `set` -- `wiring`'s 100% pass rate
  is a routing-table sync check, not a recall metric.
- **Regeneration command**: `uv run python -m tests.fixtures.psychoed.regen_wiring`
  (writes `f1_wiring.jsonl`; see "F1 wiring" above).
- **Content-block titles are not an isolation leak.** Task 3's sealed clinical-intent
  brief deliberately includes content-block TITLES from the psychoed manifests. This is a
  human ruling, not an oversight: titles ARE clinical intent (they name what the block is
  for), and block-level expectations are not authored in v1 -- delta 14 records that the
  answer-first block selection is label-containment-else-first-block, with phrase-to-
  block hints deferred to a future clinician-ratified mapping (see
  `tests/test_psychoed_graph.py`'s `block_3c_b1` comment for the as-built v1-pinned
  behavior this traces to). A future auditor who finds block titles inside a "sealed"
  brief should read this as the ruled, intentional scope of what v1 seals (routing +
  category-level intent) versus what it does not (block-level content pinning) -- not as
  evidence the seal leaked.
- **`f1_naturalistic.jsonl` provenance (Task 3).** Blind-authored 2026-07-30 by an author
  isolated from the implementation. The author's ONLY input was the sealed clinical-intent
  brief (`.superpowers/sdd/2026-07-30-psychoed-phase3-fixtures-plan/
  f1-clinical-intent-brief.md`): category ids, clinical-intent prose, and content-block
  TITLES only -- no `resolver.py`, no trigger tables, no other fixture file (dispatch
  personally inspected by the controller per the plan's Task 3 checkpoint ruling). The
  sealed brief was itself mechanically checked (normalized substring overlap of every
  multi-word trigger-table string -- both `phrases` and row `type` labels -- against the
  full brief text) **before** it was ever handed to the author. The verified property is
  **not** "zero trigger-phrase overlap" -- it is zero trigger-MATERIAL LEAKAGE, with
  exactly 8 sanctioned title/trigger-table coincidences, every one of them appearing ONLY
  inside a "Content blocks:" numbered title list (never inside the free-form
  clinical-intent prose), which is precisely the human-ruled title-inclusion scope two
  bullets up:

  | Brief text (as a content-block title) | Trigger-table string it coincides with |
  |---|---|
  | "What is anxiety?" (1f block 1) | `1f-t1` phrase `"What is anxiety?"` |
  | "What is depression?" (3c block 1) | `3c-t2` phrase `"What is depression?"` |
  | "Why can't I just 'snap out of it'?" (3c block 2) | `3c-t3` phrase `"Why can't I just snap out of it?"` |
  | "Why reactions differ in intensity (comparison to others)" (4b block 3) | `4b-t4` row **type label** `"Comparison to others"` (not a phrase) |
  | "What is assertiveness?" (6d block 1) | `6d-t1` phrase `"What is assertiveness?"` |
  | "What is grief?" (S2c block 1) | `s2c-t1` phrase `"What is grief?"` |
  | "Is there a 'right' way to grieve?" (S2c block 4) | `s2c-t1` phrase `"Is there a right way to grieve?"` |
  | "How long does grief last?" (S2c block 8) | `s2c-t1` phrase `"How long does grief last?"` |

  This is expected, not a leak: a clinically apt content-block title and a natural
  direct-question trigger phrase for the same concept often ARE the same string (a block
  literally titled "What is anxiety?" would be a strange thing to word differently), and
  the human ruling already covers this ("Content-block titles are not an isolation
  leak," two bullets up) -- this table exists so a future auditor sees the actual
  evidence instead of an unqualified "zero" claim. This half of the seal (brief vs.
  tables) is a **recorded one-time verification**, not a standing CI check: the sealed
  brief is workspace scratch (`.superpowers/sdd/2026-07-30-psychoed-phase3-fixtures-plan/
  f1-clinical-intent-brief.md`), not part of the committed corpus, so there is nothing
  for CI to re-check on every run.

  After authoring, the integrator (this task) mechanically re-checked all 61 rows against
  BOTH the trigger tables (`data/psychoed/trigger_tables/en/*.json`, 133 phrases) and the
  block titles (`data/psychoed/blocks/en/*/*.json`, 40 titles): **0/61 exact (normalized)
  matches**, and a contiguous-3+-word-substring scan (requiring at least 2 non-stopword
  words in the shared span, so pure sentence scaffolding like "why do i" or "i want to"
  doesn't count as a hit) found **no reuse of a distinctive trigger phrase or block
  title** -- the residual raw n-gram hits below that filter are generic connective English
  stems ("the difference between", "want to understand", "keep thinking", "for myself
  without", "am i angry") that recur across unrelated categories too, not copied clinical
  language. Full check output is in the Task 3 report.

  Unlike the brief-vs-tables check above, the utterance-vs-trigger-tables half of this
  property IS a **standing CI guarantee**, because both sides are committed to this repo:
  `test_f1_naturalistic_no_trigger_phrase_reuse` (`tests/test_psychoed_fixtures_ci.py`)
  re-derives the trigger phrases fresh from `data/psychoed/trigger_tables/en/*.json` on
  every run and asserts no naturalistic utterance is an exact match of, or embeds, any
  multi-word trigger phrase -- so a future corpus edit (or trigger-table edit) that
  reintroduces overlap fails CI instead of silently rotting this provenance claim, the
  same pattern as the F1 wiring table-sync check just below.
  This is the **ONLY recall-quotable F1 set**: `wiring` rows are mechanical routing checks
  (see the `set` bullet above) and must never be cited as recall evidence; `authored`
  naturalistic rows are what "F1 recall" means. It is also registered `baseline_only`
  (see "F1 naturalistic (blind-authored, baseline-only)" above) -- runnable and measured,
  never a hard CI gate.
  `repin_on:"packet-addendum-block-hints"` marks 6 of the 61 rows (`F1N-008`, `F1N-010`,
  `F1N-030`, `F1N-039`, `F1N-048`, `F1N-055`) whose expected content BLOCK -- not category
  -- may change once phrase-to-block hints are clinician-ratified. v1 authors no
  block-level expectation at all (delta 14), so this marker is a future re-pin trigger
  only; no test reads it today.
