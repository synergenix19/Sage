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
