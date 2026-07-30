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
