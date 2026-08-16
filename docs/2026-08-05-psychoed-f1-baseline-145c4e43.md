# Psychoeducation F1 naturalistic baseline — CI tier (patched-intent)

- **sha**: 145c4e43
- **tier**: CI (deterministic, patched-intent) — see mandatory caveat block below
- **corpus**: `tests/fixtures/psychoed/f1_naturalistic.jsonl` (blind-authored, Task 3; 61 rows, `baseline_only: true`, `set: "authored"`, `source: "blind-author-2026-07-30"`)
- **runner**: Task 1's CI driver (`tests/test_psychoed_fixtures_ci.py`), unmodified

## Mandatory caveat block (verbatim, packet requirement)

> CI-tier baseline (patched-intent). The flip-gate number comes from the flip-tier runner at prod parity with real intent_route and will differ. Neither number is quotable as system recall without its tier label. Clinician bar (packet ask 11) applies to the flip-tier number.

## Wiring-set exclusion note

The wiring set (`tests/fixtures/psychoed/f1_wiring.jsonl`, 133 rows, drawn from the trigger tables themselves) is a **verify-data-read** fixture set, not a recall measurement — it is never quoted as recall, at either tier. Its own numbers (133/133 CI-tier, 81/133 flip-tier) measure whether the resolver correctly reads back its own declared trigger data, not whether it recognizes naturalistic user phrasing. Only the independently-authored naturalistic set (`f1_naturalistic.jsonl`, this doc) is a recall-quotable set, per the fixture-independence rule (`docs/ARCHITECTURE_BOUNDARIES.md`, "detection recall … independent of the detector's pattern source", PR#361; spec §7.1 F1 row).

## Cross-reference — flip-tier record

`docs/2026-08-05-psychoed-families-fliptier-145c4e43.md` records the same set measured at the flip tier (real `intent_route`, real LLM, prod parity on every flag except the declared psychoed-arming delta): **F1-naturalistic FLIP-TIER: 0/61 (0.0%)**. The CI-tier number below is identical in aggregate. That agreement is expected, not incidental — see "Mechanism explanation" below.

## How this was measured

`test_psychoed_fixtures_ci.py`'s own `test_psychoed_baseline_only` runs every `baseline_only` row full-graph and calls `assert_expectations`, but is wrapped `xfail(strict=False)` by design (spec §7.1: F1-naturalistic is a tracked baseline, never a hard gate) — so pytest's own summary line reports an aggregate xfail/xpass count, not a per-category breakdown. To get recall-by-category, this baseline pass drove the **same driver functions** (`load_family("F1")` filtered to `baseline_only` rows, `_arm_psychoed`, `run_fixture`, `assert_expectations` — all imported unmodified from `tests/test_psychoed_fixtures_ci.py`, same patched-intent context: mocked `intent_route_node`, stubbed freeflow LLM, monkeypatch-only flag arming) from a small ad hoc pytest test function (`monkeypatch` fixture, `pytest.MonkeyPatch.context()` per row), catching `assert_expectations`'s `AssertionError` per row instead of letting it propagate to an xfail marker, and recording `{fixture_id, category, hit, observed_disposition, psychoed_serve, psychoed_active_category}` per row to JSON. That script was run once (`.venv/bin/python -m pytest`, 61/61 rows executed, 1 passed), the JSON collated by category, and the script deleted afterward — it is not part of the permanent suite and is not committed. Reproduction: write the same ~20-line pytest function (import `load_family`/`run_fixture`/`assert_expectations`/`_arm_psychoed` from `tests.test_psychoed_fixtures_ci`, iterate `[r for r in load_family("F1") if r.get("baseline_only")]`) and run it under `.venv/bin/python -m pytest`.

## Recall by category (CI tier)

| category | hit/total | recall |
|---|---|---|
| 1f (anxiety) | 0/10 | 0.0% |
| 3c (depression) | 0/10 | 0.0% |
| 4b (emotions) | 0/10 | 0.0% |
| 6d (assertiveness) | 0/10 | 0.0% |
| 7c (connection) | 0/10 | 0.0% |
| s2c (grief) | 0/11 | 0.0% |
| **overall** | **0/61** | **0.0%** |

Every row's observed disposition was a non-psychoed route (`presence_only`/`standard` gate paths were typical; `psychoed_serve` was never set, `psychoed_active_category` stayed `None` on all 61 rows) — a uniform miss, not a category-specific artifact. Full per-row detail (fixture_id, observed disposition, psychoed_serve, psychoed_active_category) is reproducible via the method above; not pasted here to keep this doc to the measurement, not a row dump.

## Mechanism explanation (on record, not a harness artifact)

The v1 resolver (`src/sage_poc/psychoed/resolver.py`) is **exact-match + declared-subsumption only** — there is no substring-sweep or semantic path in the resolve() call chain:
- `resolve()`'s primary path is a normalized exact-phrase match against the trigger tables' own registered phrases.
- The only non-exact path is `_subsumption_winner`, and it fires **only** when the message contains a *declared* long-form phrase (`collision_table.json`'s `subsumption_collisions` list) as a substring — not any arbitrary paraphrase.
- Menu-label matching (`_match_menu_label`) is a separate, later-turn mechanism (substring-then-token-subset against `menu_label` strings), not a first-turn recognition path, and is deliberately conservative (ambiguous substring hits fail closed to `None`, per the module's own "undeclared_first" avoidance).

`f1_naturalistic.jsonl` was blind-authored (Task 3) specifically to be **phrase-independent** of the trigger tables — the author never saw resolver.py, the trigger tables, or any fixture file, and a standing CI no-reuse test (added Task 3 fix round 1) mechanically enforces zero trigger-phrase-material leakage into the corpus (8 sanctioned title-only coincidences, verified zero prose reuse). Given a resolver whose only matching primitives are exact-phrase and declared-subsumption, and a corpus mechanically guaranteed not to reuse those phrases, **0/61 is the designed-honest baseline pre-block-hints** — the expected outcome of running a phrase-independent naturalistic set through an exact-match mechanism, not a harness bug, a fixture-authoring defect, or a driver wiring gap. (Independent corroboration: Task 5's own terrain finding recorded the identical property from a different angle — the plan's canonical mixed-pull utterance "what is anxiety? I can't breathe right now" produces no resolver hit on master for the same reason.)

The deviations register's item 12 (spec §10) already names the forward path: a clinician-ratified phrase→block-hint column on the trigger tables (packet addendum) is the mechanism this baseline is measured *against* — `f1_naturalistic.jsonl`'s `repin_on: "packet-addendum-block-hints"` marker (6 rows: F1N-008/010/030/039/048/055) exists for exactly this re-measurement once that addendum lands. This baseline is the honest "before" number for that future comparison, not a verdict on the mechanism's eventual ceiling.
