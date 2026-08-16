# F1 Wiring Flip-Tier Divergence — Taxonomy (ruled 2026-08-06)

- **sha**: 20485a20 (branch `feat/psychoed-phase3-fixtures`)
- **source**: `docs/2026-08-05-psychoed-families-fliptier-145c4e43-console.log` (the flip-tier
  record run's raw console output, committed verbatim alongside this doc — every row line
  below is a direct `grep`/parse of that file, not a re-derivation or a summary of a
  summary)
- **companions**: `docs/2026-08-05-psychoed-families-fliptier-145c4e43.md` (the record doc
  this taxonomy explains), `docs/superpowers/tickets/2026-08-06-psychoed-resolver-intent-reachability.md`
  (Ticket A), `docs/superpowers/tickets/2026-08-06-cross-category-collision-all-armed.md`
  (Ticket B), `docs/superpowers/specs/2026-07-23-psychoeducation-pathways-design.md` §10
  entry 16

## 1. What this doc is

The 2026-08-05 flip-tier record (`docs/2026-08-05-psychoed-families-fliptier-145c4e43.md`)
reported F1 wiring at 81/133, "vs. 133/133 CI-tier — real-intent divergence data", without
breaking the 52 misses down by cause. A human ruling on 2026-08-06 required the misses be
taxonomized from the run's own per-row log before any register text characterizing the
number could ship. This doc is that taxonomy: every one of the 52 `F1-*` `MISS` rows in
the committed console log, classified by cause, with the classification verified against
the log text itself (not inferred from the summary table).

**Extraction method:** the console log's per-row F1 lines match
`^\[\d+s\] F1-\S+ real_label='[a-z_]+' .* MISS$` (turn-level lines; every row in this
family runs a single turn, so one line = one row). A mechanical parse
(`re.match(r"^\[(\d+)s\] (F1-\S+) real_label='([a-z_]+)' (.*) MISS$", line)`) against the
committed log yields exactly **52 matches** — the same 52 the record's `81/133` implies
(133 − 81 = 52). No row was hand-selected or summarized before classification.

## 2. Classes

Three classes, defined by what `real_label` (the LIVE `intent_route` classification the
flip-tier run observed) did to the turn, and — for the one exception — by what the
resolver actually matched instead of what was expected:

- **`intent_interception_general_chat`** (48 rows) — the live classifier labeled the turn
  `general_chat`. `_route_after_intent` sends `general_chat` to `freeflow_respond` directly;
  it never reaches `skill_select` (Node 4), so the psychoed resolver — which runs
  unconditionally *inside* Node 4 (spec §2.1) — never executes at all for these turns. Every
  row here shows `psychoed_matched_row_id: expected '<row>', got None` and
  `psychoed_active_category: expected '<cat>', got None`: a clean absence, not a wrong
  answer — the resolver was never called.
- **`intent_interception_scope_refusal`** (3 rows) — same mechanism, different label: the
  live classifier routed the turn to `scope_refusal` instead. Same absence signature
  (`got None` on both audit and state fields) for the same topological reason.
- **`cross_category_collision`** (1 row, `F1-s2c-t5-01`) — the ONLY row where the resolver
  *did* run (real_label was `info_request`, which does reach `skill_select`) and *did*
  produce a `psychoed_serve` (`disposition=OK`), but matched the wrong row:
  `psychoed_matched_row_id: expected 's2c-t5', got '3c-t3'` /
  `psychoed_active_category: expected 's2c', got '3c'`. This is a different bug class
  entirely (Ticket B, not Ticket A) — a genuine cross-category collision the CI driver
  cannot see because it never arms more than one category's collision partner at once for
  an unrelated row (see Ticket B, and the all-armed CI mode this task adds, which
  reproduces this exact divergence deterministically: `F1-s2c-t5-01-all-armed` xfails on
  the identical `3c-t3`/`3c` observed values).

**Zero rows show crisis-precedence involvement.** No row's `real_label` is `crisis`,
`high_risk`, or any safety-route label; no row's audit trace shows a safety route firing
ahead of the psychoed resolver. The pre-written taxonomy category this ruling retracts —
"by-design precedence" (crisis/safety correctly outranking psychoed) — accounted for zero
of the 52 misses. Register entry 16 (spec §10) records the retraction explicitly.

## 3. Full classification table (52 rows)

| fixture_id | real_label | expected `matched_row_id` | observed `matched_row_id` | class |
|---|---|---|---|---|
| F1-1f-t2-01 | general_chat | 1f-t2 | None | intent_interception_general_chat |
| F1-1f-t2-02 | general_chat | 1f-t2 | None | intent_interception_general_chat |
| F1-1f-t3-01 | scope_refusal | 1f-t3 | None | intent_interception_scope_refusal |
| F1-1f-t3-02 | scope_refusal | 1f-t3 | None | intent_interception_scope_refusal |
| F1-3c-t1-01 | general_chat | 3c-t1 | None | intent_interception_general_chat |
| F1-3c-t3-01 | general_chat | 3c-t3 | None | intent_interception_general_chat |
| F1-3c-t3-02 | general_chat | 3c-t3 | None | intent_interception_general_chat |
| F1-3c-t3-04 | general_chat | 3c-t3 | None | intent_interception_general_chat |
| F1-3c-t3-06 | general_chat | 3c-t3 | None | intent_interception_general_chat |
| F1-3c-t3-10 | general_chat | 3c-t3 | None | intent_interception_general_chat |
| F1-3c-t3-11 | general_chat | 3c-t3 | None | intent_interception_general_chat |
| F1-3c-t3-12 | general_chat | 3c-t3 | None | intent_interception_general_chat |
| F1-3c-t4-03 | general_chat | 3c-t4 | None | intent_interception_general_chat |
| F1-3c-t5-01 | scope_refusal | 3c-t5 | None | intent_interception_scope_refusal |
| F1-4b-t1-01 | general_chat | 4b-t1 | None | intent_interception_general_chat |
| F1-4b-t1-03 | general_chat | 4b-t1 | None | intent_interception_general_chat |
| F1-4b-t1-04 | general_chat | 4b-t1 | None | intent_interception_general_chat |
| F1-4b-t1-05 | general_chat | 4b-t1 | None | intent_interception_general_chat |
| F1-4b-t2-01 | general_chat | 4b-t2 | None | intent_interception_general_chat |
| F1-4b-t2-04 | general_chat | 4b-t2 | None | intent_interception_general_chat |
| F1-4b-t3-05 | general_chat | 4b-t3 | None | intent_interception_general_chat |
| F1-4b-t4-02 | general_chat | 4b-t4 | None | intent_interception_general_chat |
| F1-4b-t5-02 | general_chat | 4b-t5 | None | intent_interception_general_chat |
| F1-6d-t2-01 | general_chat | 6d-t2 | None | intent_interception_general_chat |
| F1-6d-t2-02 | general_chat | 6d-t2 | None | intent_interception_general_chat |
| F1-6d-t2-03 | general_chat | 6d-t2 | None | intent_interception_general_chat |
| F1-6d-t4-04 | general_chat | 6d-t4 | None | intent_interception_general_chat |
| F1-6d-t4-06 | general_chat | 6d-t4 | None | intent_interception_general_chat |
| F1-6d-t6-02 | general_chat | 6d-t6 | None | intent_interception_general_chat |
| F1-7c-t1-02 | general_chat | 7c-t1 | None | intent_interception_general_chat |
| F1-7c-t2-01 | general_chat | 7c-t2 | None | intent_interception_general_chat |
| F1-7c-t2-02 | general_chat | 7c-t2 | None | intent_interception_general_chat |
| F1-7c-t2-03 | general_chat | 7c-t2 | None | intent_interception_general_chat |
| F1-7c-t2-04 | general_chat | 7c-t2 | None | intent_interception_general_chat |
| F1-7c-t2-06 | general_chat | 7c-t2 | None | intent_interception_general_chat |
| F1-7c-t2-09 | general_chat | 7c-t2 | None | intent_interception_general_chat |
| F1-7c-t2-10 | general_chat | 7c-t2 | None | intent_interception_general_chat |
| F1-7c-t3-01 | general_chat | 7c-t3 | None | intent_interception_general_chat |
| F1-7c-t3-04 | general_chat | 7c-t3 | None | intent_interception_general_chat |
| F1-7c-t3-05 | general_chat | 7c-t3 | None | intent_interception_general_chat |
| F1-7c-t3-06 | general_chat | 7c-t3 | None | intent_interception_general_chat |
| F1-7c-t3-07 | general_chat | 7c-t3 | None | intent_interception_general_chat |
| F1-s2c-t2-03 | general_chat | s2c-t2 | None | intent_interception_general_chat |
| F1-s2c-t3-03 | general_chat | s2c-t3 | None | intent_interception_general_chat |
| F1-s2c-t4-01 | general_chat | s2c-t4 | None | intent_interception_general_chat |
| F1-s2c-t4-02 | general_chat | s2c-t4 | None | intent_interception_general_chat |
| F1-s2c-t4-04 | general_chat | s2c-t4 | None | intent_interception_general_chat |
| F1-s2c-t4-05 | general_chat | s2c-t4 | None | intent_interception_general_chat |
| F1-s2c-t4-07 | general_chat | s2c-t4 | None | intent_interception_general_chat |
| F1-s2c-t7-01 | general_chat | s2c-t7 | None | intent_interception_general_chat |
| F1-s2c-t8-02 | general_chat | s2c-t8 | None | intent_interception_general_chat |
| **F1-s2c-t5-01** | info_request | s2c-t5 | **3c-t3** | **cross_category_collision** |

## 4. Class totals

| class | count |
|---|---|
| `intent_interception_general_chat` | 48 |
| `intent_interception_scope_refusal` | 3 |
| `cross_category_collision` | 1 |
| **total F1 wiring misses** | **52** |
| crisis-precedence-involved | **0** |

51/52 misses (all but the collision row) are the identical mechanism: **reaching
`skill_select` (Node 4) at all is conditional on `intent_route`'s classification** — a
turn labeled `general_chat` or `scope_refusal` by the live classifier never gets a chance
to hit the trigger tables the resolver runs unconditionally *once inside* Node 4. Put
plainly: **51/133 doc-verbatim trigger phrases are invisible to the trigger tables in the
real graph**, not because the tables or the resolver are wrong, but because the graph edge
that would carry the turn to Node 4 doesn't exist for these two intent labels. This is
Ticket A's finding.

The 52nd row is a different, narrower defect (Ticket B): a genuine cross-category
exact-phrase collision (`s2c-t5` / `3c-t3`, both spelled `"Why do I feel numb?"`) that the
CI driver's per-row single-category arming structurally cannot expose, and which the
flip-tier run's real all-six-armed topology did expose. This task's all-armed CI mode
(`tests/test_psychoed_fixtures_ci.py::test_psychoed_fixture_all_armed`) now reproduces it
deterministically in CI (`F1-s2c-t5-01-all-armed`, strict xfail citing Ticket B).

## 5. What this taxonomy does NOT show

- No F1 wiring miss is attributable to a wrong trigger-table phrase, a wrong resolver
  match under favorable topology, or a content/serve-composition defect — every miss is
  either "resolver never ran" (51/52) or "resolver ran and hit a genuine, separately-fixable
  collision" (1/52).
- No F1 wiring miss shows crisis, high-risk, or medical precedence firing ahead of the
  resolver. The record's own framing of "real-intent divergence data" is accurate as far as
  it goes, but a pre-written taxonomy category assuming some of that divergence would be
  correct-by-design crisis/safety precedence was retracted once this table was built — see
  spec §10 entry 16.
