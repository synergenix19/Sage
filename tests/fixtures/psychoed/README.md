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
