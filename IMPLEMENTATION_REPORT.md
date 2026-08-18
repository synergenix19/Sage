# Ticket A implementation report — psychoed resolver intent-reachability

**Branch:** `fix/psychoed-resolver-reachability` off master `9c762759`
**Status:** COMPLETE, green. Awaiting the human-run live flip-tier re-run (the DoD acceptance test).

## Commits

| sha | scope |
|---|---|
| `62a84ec9` | routing delta (`src/sage_poc/graph.py`, `src/sage_poc/nodes/skill_select.py`) |
| `3035a2a2` | pins (`tests/test_psychoed_reachability.py`, `.github/workflows/unit-gate.yml` CANDIDATES) |
| `4b699466` | assessment evidence (`docs/2026-08-12-reachability-jailbreak-exit-skill-assessment.md`) |

## The delta (Direction 1, as ruled)

Three edits, all flag-gated on `PSYCHOED_PATHWAYS_ENABLED`:

1. `_route_after_intent` becomes a two-line wrapper over the **unmodified** ladder, renamed
   `_route_after_intent_base`. New helper `psychoed_transit_destination(state)` returns the
   turn's master destination when it is a transit turn (`general_chat`/`scope_refusal` whose
   base destination is `freeflow`/`gate`), else `None`. Transit turns route to `skill_select`.
2. `skill_select_node`: after the resolver block, a transit turn with no psychoed outcome
   returns the **empty delta** — no state written, `"skill_select"` deliberately not appended
   to `path`. That is spec §2.1 step 5's null case, and it is what makes the audit row
   byte-identical.
3. `_route_after_skill_select`: below every psychoed-outcome branch (escalation, containment,
   serve/menu) and above the rest of the ladder, re-derive the transit destination and return
   it. New edge `"gate": "output_gate"` in the skill_select edge map so a `scope_refusal`
   transit lands back on its master terminal.

**No new state channel.** The transit is a pure re-derivation from state; the no-hit node
return is empty, so the state the second reader derives from is byte-identically the state the
first derived from. `scripts/check_state_channels.py`: `OK: all 116 written+read state keys are
declared SageState channels.`

**Crisis precedence:** untouched by construction — Node 1's short-circuit never reaches
`intent_route`, and `intent == "crisis"` returns above the widening. Pinned twice.

**Finding handled in-branch:** `skill_select` has a *second* in-edge — the EMR surface-1
rehand (`skill_executor → skill_select`, `exit_with_rehand`). Without a guard, a rehand turn
labeled `general_chat` could have been misread as a transit turn and short-circuited past the
EMR delivery body. Excluded on the executor's own `path` stamp; pinned by
`test_executor_rehand_into_skill_select_is_not_a_transit_turn`.

## Verification

| run | result |
|---|---|
| unit-gate CANDIDATES (79 files), `-m "not slow"` — gate-exact | **2025 passed, 5 skipped, 38 deselected, 73 xfailed** |
| unit-gate CANDIDATES, full incl. slow | **2062 passed, 5 skipped, 74 xfailed** |
| `tests/test_psychoed_reachability.py` (new) | **66 passed** |
| `scripts/check_state_channels.py` | OK, 116 keys |
| whole `tests/` tree vs. a base-commit worktree at `9c762759`, failure-set diff | **zero new failures** |

Env: `OPENROUTER_API_KEY=dummy-ci HF_HUB_OFFLINE=1`, files passed via python subprocess argv.
No live-LLM run attempted.

**Strict xfails — none flipped.** `F4-002` (all 8 swept labels, incl. `general_chat` and
`scope_refusal`) still xfails: its cause is the menu-label substring tier, not reachability, as
predicted. Both all-armed collision rows (`F1-1f-t2-02-all-armed`, `F1-s2c-t5-01-all-armed`)
still xfail: arming-topology, not reachability. `F10-004` still xfails. Psychoed fixture xfail
count is 72 before and after.

**Pre-existing, not mine:** `tests/test_server_offer_voiding.py` (4 tests) fails on the base
commit both in isolation and in the whole-suite run; it happens to pass in the whole-suite run
with this branch's new test file present (order/global-state sensitivity). Not in the gate
CANDIDATES set. Flagged, not touched.

## Rider outcomes

- **Weave-pending refusal path:** verified, and it already held before this change — HIGH-1's
  `psychoed_weave_pending` redirect sits *above* the `scope_refusal`/`jailbreak` gate branches,
  so the reply already reached the evaluator (confirmed by driving master code directly). It is
  now pinned explicitly, because the ladder changed around it and the class was previously only
  covered implicitly as one label of F4's nine-label sweep. Asserted on escalation markers
  (`skill_match_method`, path, `gate_path`, audit `psychoed_weave_state == "escalated"`), since
  the crisis pathway-clear resets `psychoed_weave_escalation` before final state.
- **Byte-identical no-hit transit:** pinned for both labels against a flag-off run of the same
  turn (the widening is entirely flag-gated, so flag-off *is* master routing here), comparing
  response, whole final state, `path`, and the audit row, with wall-clock fields excluded by
  name. Also pinned for the mid-skill (active-skill suppression) and non-English (EN-only
  entry) sub-cases.
- **jailbreak / exit_skill:** assessed, NOT widened. See the assessment doc.

## Extra pin worth knowing about

`test_taxonomy_intercepted_row_reaches_the_resolver` re-drives all **51** intent-interception
rows from the committed taxonomy, each under the label the live classifier actually assigned
it, and requires the F1-expected serve. The row set is parsed from the taxonomy doc and
count-guarded (48 general_chat + 3 scope_refusal); a doc or corpus drift fails collection
rather than silently gating fewer rows. This is the CI-tier analogue of the DoD's live test —
it is not a substitute for it (CI pins the label; the live run measures what the classifier
does).

## Open / for the human

- The live flip-tier re-run at prod parity (51 interception rows serving; register 16 flips) is
  the DoD and was not attempted here.
- Ticket status flip and the spec §10 register/entry-16 restatement are governance edits and
  were deliberately left alone.
