# Psychoeducation Phase 3 — fixture-families close-out

- **sha**: 145c4e43 (branch `feat/psychoed-phase3-fixtures`)
- **plan**: `docs/superpowers/plans/2026-07-30-psychoed-phase3-fixtures-plan.md`
- **spec**: `docs/superpowers/specs/2026-07-23-psychoeducation-pathways-design.md` (§10 register amended this task — entries 13–15)

## 1. Fixture inventory as-built (per-family row counts)

Counts derived directly from `tests/fixtures/psychoed/f*_*.jsonl` (one `jsonl` line = one row):

| family | file | rows | notes |
|---|---|---|---|
| F1 (wiring) | `f1_wiring.jsonl` | 133 | verify-data-read set; never quoted as recall |
| F1 (naturalistic) | `f1_naturalistic.jsonl` | 61 | blind-authored (Task 3), `baseline_only:true`, the only recall-quotable F1 set |
| F2 | `f2_collisions.jsonl` | 7 | |
| F3 | `f3_classifiers.jsonl` | 8 | |
| F4 | `f4_weave.jsonl` | 16 | 13 hard-required + 3 AR draft-pending-validator (skipped) |
| F6 | `f6_precedence.jsonl` | 5 | |
| F8 | `f8_regression.jsonl` | 27 | |
| F9 | `f9_backstop.jsonl` | 7 | all 7 CI-tier-only (skipped at flip tier, per register entry 13) |
| F10 | `f10_diagnosis.jsonl` | 5 | F10-001/002/004 hard; F10-003 flip_tier_only (observed-only); F10-004b rag_top CI-tier-only |
| F5 | none (procedural, no corpus rows — `tests/test_psychoed_f5_flow.py`) | 0 | 9 procedural tests, not corpus-driven |
| F7 | none (procedural, no corpus rows — `tests/test_psychoed_f7_integrity.py`) | 0 | included in the same 9-test procedural run as F5 |

**Total corpus rows: 269** (across `f1_wiring`, `f1_naturalistic`, `f2`–`f4`, `f6`, `f8`–`f10`).

## 2. Skip counts (spec §7.2 no-silent-caps — every skip logged, never a silent filter)

| skip class | count | reason |
|---|---|---|
| `ar_draft_pending_validator` | 3 | F4's AR rows (`lang:"ar"`, `status:"draft-pending-validator"`) — nothing AR-labeled is quotable as coverage until the faithfulness-graded validator chain lands (spec §3.7) |
| `f9_ci_tier_only` | 7 | all of F9 — repo-patch (DB-boundary fake) dependence makes it CI-only by design; register entry 13 (this task) rules the CI tier as the correct, sufficient instrument |
| `rag_top_ci_tier_only` | 1 | F10-004b — uses the same DB-boundary retrieval-faking hook as F9, for the same CI-tier-only reason |

Source of record: `docs/2026-08-05-psychoed-families-fliptier-145c4e43.md`'s own "Skip counts" section (flip-tier runner); counts match the corpus-level tagging above row for row.

## 3. Named-exclusion pins (handoff-notes deltas 15/16 — observed, not fixed)

These are pins against **`docs/superpowers/plans/2026-07-28-psychoed-phase2-handoff-notes.md` §VI**'s own as-built delta register (a separate, earlier numbering from the spec §10 register above — not to be confused with it):

- **Delta 15 — served-topics context injection.** Deferred to Phase 3 with no template-variable mechanism; Task 7's F5 multi-turn flow tests assert loop-back via deterministic surfaces only (state keys + re-serve behavior), never LLM topic-memory. Named exclusion is prominent in `tests/test_psychoed_f5_flow.py`'s module docstring, citing delta 15 directly.
- **Delta 16 — the Node-8 integrity gate rewrites `final_response` only.** `response_en`/history retention diverge from the corrected text on both the pass and the mismatch/re-serve branches. Task 8's F7 integrity tests pin this as a NAMED EXCLUSION on both branches (citing delta 16 verbatim); no ticket exists for delta 16 (confirmed absent in `docs/superpowers/tickets/` at task time) — it is documented as an observed, as-built property, not filed as an open defect.

## 4. Re-pin markers

`f1_naturalistic.jsonl` carries a `repin_on: "packet-addendum-block-hints"` marker on rows whose expected block would change once the clinician-ratified phrase→block-hint column (spec §10 entry 12) lands. **Count: 6** — `F1N-008`, `F1N-010`, `F1N-030`, `F1N-039`, `F1N-048`, `F1N-055`. These rows currently pin category-only expectations (v1's answer-first block selection is label-containment-else-first-block, per §10 entry 12); once the packet addendum ratifies block hints, these 6 rows are the re-measurement set for block-level (not just category-level) recall.

## 5. CI-gate wiring delta

Fact-sheet §7 gap (Phase-2 psychoed suites existed, were green, and were CI-invoked by their own dedicated test files, but sat **outside** the required `unit-gate` CANDIDATES list — a suite that exists and passes but isn't watched by the hard gate provides the same false assurance as the #15 blind spot the gate's own header comment names) — **closed 2026-08-04 (Task 9)**. `.github/workflows/unit-gate.yml`'s `CANDIDATES` list gained 16 suites:

Newly wired (Phase-2 suites, previously unwatched):
- `tests/test_psychoed_graph.py`
- `tests/test_psychoed_gate.py`
- `tests/test_psychoed_skill_select.py`
- `tests/test_psychoed_knowledge_retrieve.py`
- `tests/test_psychoed_flag_off.py`
- `tests/test_psychoed_mechanism_a.py`
- `tests/test_psychoed_store.py`
- `tests/test_psychoed_weave_eval.py`
- `tests/test_psychoed_classifiers.py`
- `tests/test_psychoed_resolver.py`
- `tests/test_psychoed_serve.py`
- `tests/test_psychoed_carry_forward.py`

Newly wired (Phase-3 suites, this plan's own output):
- `tests/test_psychoed_fixtures_ci.py` (Tasks 1–8's CI-tier driver: F1–F4/F6/F8–F10 corpus families)
- `tests/test_psychoed_f5_flow.py` (F5 procedural, no corpus rows)
- `tests/test_psychoed_f7_integrity.py` (F7 procedural, no corpus rows)
- `tests/test_measure_psychoed_families_safety.py` (added same day, Task 9 fix round 1 — permanent regression guard for the flip-tier runner itself: the undefeatable `--live` + pre-import key-snapshot gate, and the six-site `write_session_audit` patch-coverage static guard)

All 16 verified green in the exact CANDIDATES set before wiring (Task 9); the gate's change-detection paths list was also verified to include `tests/fixtures/psychoed/`. The CANDIDATES set is now 77 files.

## 6. Tickets filed (Tasks 6 and 8), by path

- `docs/superpowers/tickets/2026-07-30-menu-label-short-token-substring-collision.md` — **[Task 6]** mechanism gap: bare "no" collides with `3c-b6`'s own menu-label substring, re-serving a block instead of the deferred PSY-WEAVE-1 menu (F4-002's finding; §10 register entry 14).
- `docs/superpowers/tickets/2026-07-31-diagnosis-guard-consent-to-serve-unbuilt.md` — **[Task 8]** BUILD: the diagnosis-guard consent-to-serve yes-branch (spec §5.5) has no deterministic implementation anywhere in `src/` (F10-004's finding; §10 register entry 15).
- `docs/superpowers/tickets/2026-07-31-resolver-pick-block-unconditional-false-mismatch.md` — **[Task 8]** BUG, HIGH-2 class: `resolver._pick_block` runs unconditionally regardless of route, producing a phantom `block_id` on `formal_diagnosis` (answer-first + weave categories) and a false integrity-gate mismatch.
- `docs/superpowers/tickets/2026-07-31-weave-vs-guard-consent-precedence.md` — **[Task 8]** DESIGN RULING NEEDED (framed as a question, not a bug): PSY-WEAVE-1 precedence makes the diagnosis guard's push-further/consent turn structurally unreachable on weave-enabled categories; current behavior may be correct fail-closed precedence. **Status update (2026-08-04 controller ruling, recorded in the plan ledger, not yet reflected in the ticket file itself):** disposed as "precedence correct; composition must stop creating two-question turns" — the fix is a composition change (segment the single-sourced stage-1 script into body/close fields so the guard's consent close defers behind the weave question, mirroring how the menu already defers), not an evaluation-order change. The data-schema segmentation touches signed clinical copy and rides the packet round for ratification.
- `docs/superpowers/tickets/2026-07-31-framing-question-clips-guard-consent-question.md` — **[Task 8]** BUG: Node-8's one-question-cap (MIND-SAFE question discipline) silently drops the diagnosis guard's own trailing consent question whenever the category's `framing_statement` also ends in a question (e.g. `1f`). **Status update:** resolves under the same body/close segmentation ruled for the precedence ticket above.

Four Task-8 tickets + one Task-6 ticket = five total, all filed under `docs/superpowers/tickets/` with the standard house ticket format (class, file:line trace, live-repro evidence, fix shape or explicit non-fix for the design-ruling ticket).

## 7. Flip-tier record reference — headline numbers

**`docs/2026-08-05-psychoed-families-fliptier-145c4e43.md`** (full-graph `app.ainvoke`, REAL `intent_route` + REAL LLM, no node patches; flag parity VERIFIED vs. desired(railway) with the psychoed-arming vars carved out as the declared delta — every other `SAGE_` var hard-parity; retrieval ACTIVE via a read-only Postgres pool; 0 instrument faults):

| family | conform/total |
|---|---|
| F1 (wiring) | 81/133 (vs. 133/133 CI-tier — real-intent divergence data) |
| F1 (naturalistic) | 0/61 (both tiers — see `docs/2026-08-05-psychoed-f1-baseline-145c4e43.md`) |
| F2 | 3/7 |
| F3 | 6/8 |
| F4 | 12/13 (sole miss: F4-002, expected xfail reproduced at parity) |
| F6 | 5/5 |
| F8 | 6/6 (21 observed-only rows, no pinned disposition) |
| F5/F7 (procedural) | 9/9 passed |

Xfail reproduction at prod parity: **F4-002** and **F10-004** both REPRODUCED (field-level divergence identical in kind to the CI-tier xfail — see spec §10 entries 14/15). Register-amendment-8 rider (a) real-retrieval smoke: did not fire this run (retrieval genuinely active, non-deterministic outcome; five nearest passages logged).

## 8. Flip-tier caveats that must ride any quotation of these numbers

- **Session-identity absent at flip tier.** `session_id`/`user_id` are deliberately not exercised, so any prod behavior keyed on real session identity (summary persistence, profile lookup) is unexercised by this record. This matches CI tier and predates this closing round, but the record must state it, not imply parity on it.
- **Reset-VALUE divergence pins (`message_en`/`is_safe`).** The per-turn prod-reset mirror (Task 9, fix round 5) reproduces all 62 real prod per-turn-reset channels structurally, but `message_en`/`is_safe` still diverge in *value* from what a live prod turn would carry — harmless today because `safety_check_node` overwrites both before any other node reads them. If a future change makes any node read either channel before `safety_check`, this divergence becomes a real artifact risk; the pin makes it visible, it does not close it.

## 9. Instrument lineage

The flip-tier runner (`scripts/bot_behaviour_audit/measure_psychoed_families.py`, extended by Task 9) went through **5 fix rounds** before producing a quotable record:
1. Undefeatable `--live` opt-in + full audit-site capture (closed a defeatable no-key-refusal + 4/6 unpatched `write_session_audit` call sites).
2. Psychoed-arming carve-out in the flag-parity guard (the declared-delta mechanism; all other flags stayed hard-parity).
3. Per-row `thread_id` config on the live invoke path (a bare `app.ainvoke` with no config crashed the checkpointer on the very first live attempt).
4. Four **live-checkpoint-only findings** — issues that only a genuine live run could surface, none reproducible via dry-run or CI tier: (a) flip-tier assertion semantics were disposition-only, silently never asserting `expect.audit`/`expect.state` on any row without a pinned disposition (all F10, F3-001..004, all 27 F8 matrix rows); (b) the label-class split from the CI driver was missing at flip tier, so real crisis-label routing (which legitimately bypasses `skill_select`) reported false CI-tier-shaped misses; (c) F6-002's apparent divergence was reproduced as a genuine, real artifact in both directions (HR routing fired pre-fix; stale `psychoed_serve` misreported it) — not a fixture bug; (d) retrieval was structurally absent (the pool is server-hosted, not available to the standalone runner process), making the "REAL retrieval" provenance claim false and the amendment-8 smoke case structurally incapable of ever firing — fixed via a read-only bootstrap pool from `DATABASE_URL`.
5. Complete per-turn reset mirror (this sha, 145c4e43) — the prior round's reset mirror covered only `psychoed_serve` of ~30+ real prod per-turn resets; this round live-imports the actual `_build_state` reset dict (62 prod channels, 37 of them leak-prone) with an AST shape-guard and negative controls proving the drift class is now structurally impossible, not merely tested against today's corpus.

**Superseded/removed:** an earlier "attempt 5" flip-tier doc (`docs/2026-08-04-psychoed-families-fliptier-37935fda.md`) completed cleanly (0 faults, exit 0) but was flagged stale by the fix-round-4/5 findings above (specifically: disposition-only assertions silently under-measured every F10/F3/F8 row, and retrieval was not actually active) and was never committed — it does not exist in this worktree or in git history. Live attempts 1–3 (this task) deadlocked on the flag-parity guard before the carve-out landed; attempt 4 crashed pre-thread_id-fix with zero rows driven and no output doc. **`docs/2026-08-05-psychoed-families-fliptier-145c4e43.md` (attempt 6, this sha) is the sole quotable flip-tier record** — every number in this close-out doc, and every field-level xfail-reproduction claim in spec §10 entries 14/15, is cited from it directly.

## 10. CI evidence (this task, fresh at HEAD 145c4e43)

- `scripts/check_state_channels.py`: **OK: all 112 written+read state keys are declared SageState channels.**
- Full unit-gate CANDIDATES set (77 files, `.github/workflows/unit-gate.yml`'s exact list, same env as CI: `OPENROUTER_API_KEY=dummy-ci`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `pytest -m "not slow" -p no:randomly`): **1804 passed, 4 skipped, 38 deselected, 71 xfailed, 0 failed**, in 77.97s.
