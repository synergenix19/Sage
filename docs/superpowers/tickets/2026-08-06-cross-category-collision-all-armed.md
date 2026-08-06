# Ticket: cross-category exact-phrase collision resolves to the wrong category under all-six-armed topology — a CI blind spot, not a fixture bug

**Filed:** 2026-08-06 · **Source:** Psychoeducation Phase 3, human adjudication of the
2026-08-05 flip-tier record; the one F1 wiring miss NOT explained by Ticket A's
intent-reachability finding (`docs/2026-08-06-f1-wiring-flip-divergence-taxonomy.md` §2,
class `cross_category_collision`), cross-referenced against F2-002's own flip-tier miss
(same close-out doc, §7) and confirmed reproducible in CI via this task's own all-armed
driver extension
**Status:** open — fix is resolver-side, own branch + normal review (collision-table data
is safety-adjacent per spec §5.2/§5.4 governance); NOT fixed here
**Type:** BUG, mechanism gap in `data/psychoed/collisions/collision_table.json`'s
declared-winner coverage, exposed by a CI measurement blind spot in
`tests/test_psychoed_fixtures_ci.py`'s pre-existing single/declared-category arming
**Links:** `docs/2026-08-06-f1-wiring-flip-divergence-taxonomy.md`,
`docs/2026-08-05-psychoed-families-fliptier-145c4e43.md` (§7, F2 3/7),
`docs/2026-08-05-psychoed-families-fliptier-145c4e43-console.log`,
`data/psychoed/collisions/collision_table.json`, `src/sage_poc/psychoed/resolver.py`
(`_flat_collision_winner`, `_phrase_index`), `tests/test_psychoed_fixtures_ci.py`
(`test_psychoed_fixture_all_armed` — this task's new all-armed CI mode, added to close the
blind spot named below), `docs/superpowers/specs/2026-07-23-psychoeducation-pathways-design.md`
§5.2 (collision policy)

## The finding

`F1-s2c-t5-01` (fixture id, wiring row `s2c-t5`, phrase `"Why do I feel numb?"`) is pinned
to expect category `s2c` — correct under the CI driver's single-category arming, since
`f1_wiring.jsonl` rows only ever arm the row's own generating category
(`tests/fixtures/psychoed/regen_wiring.py`). But `"Why do I feel numb?"` (normalized) is
ALSO `3c-t3`'s exact phrase — a declared collision in
`data/psychoed/collisions/collision_table.json`'s `collisions` list, with `default_winner:
"3c"` when no grief context is present. At the 2026-08-05 flip-tier run — real graph, all
six psychoed categories armed simultaneously (the declared delta this run measures under;
see that doc's header) — this row resolved to `3c-t3`/`3c`, not `s2c-t5`/`s2c`:
`psychoed_matched_row_id: expected 's2c-t5', got '3c-t3'` /
`psychoed_active_category: expected 's2c', got '3c'`. `disposition=OK` (a `psychoed_serve`
did fire) — this is a wrong-category match, not an intent-reachability miss (Ticket A's
class); it is the ONE F1 wiring miss Ticket A's taxonomy attributes elsewhere.

**The CI driver cannot see this by construction.** `tests/test_psychoed_fixtures_ci.py`'s
`_arm_psychoed` arms only the row's own `category` (or, for F2 rows, the row's declared
`categories` — always the exact pair the row exists to test, never all six). F1 wiring's
`s2c-t5` row arms only `s2c`; `3c` is never simultaneously enabled, so `_flat_collision_winner`
never runs for this row in CI — `resolver.py`'s `_phrase_index` only indexes rows from
`enabled_categories`, so with `3c` disabled, the phrase index has exactly one entry for this
normalized phrase (`s2c-t5`) and resolves trivially, correctly, uninterestingly. **The CI
driver arms one category (or one declared pair) per row, so cross-category winners outside
that row's own declared set are structurally invisible** — not because the collision table
is wrong, but because no CI-tier row before this task ever ran with a topology resembling
prod's (every flipped category live together).

## F2-002 is the same class, via a different mechanism

`docs/2026-08-05-psychoed-families-fliptier-145c4e43.md` §7 reports F2 at 3/7 at flip tier
(vs. green-required at CI tier). F2-002's own fixture (`tests/fixtures/psychoed/f2_collisions.jsonl`)
seeds grief context on turn 1 (a real keyword-matched `grief_loss` skill offer from "My
father died last month.") and expects turn 2's `"Why do I feel numb?"` to resolve via
`context_winner` to `s2c-t5`/`s2c`. At CI tier (pinned intent), this holds — confirmed
directly against `resolver.resolve()` with the row's real inputs, and confirmed empirically
by this task's own `test_psychoed_fixture_all_armed[F2-002-all-armed]`, which passes. At
flip tier (real `intent_route`), it misses: the live classifier's handling of "My father
died last month." does not reproduce the same deterministic `grief_loss` offer the CI
driver's pinned-intent turn 1 produces, so `offered_skill_ids` never carries the signal
`skill_select._psychoed_grief_context` reads, `context_winner` never fires, and the
collision falls through to `default_winner: "3c"` instead — the SAME collision-table entry
Ticket A's `F1-s2c-t5-01` finding hits, reached by a different path (context-signal loss
under real classification, not all-armed exposure). **Both are the collision table's
`3c`-favoring default winning over `s2c` when the disambiguating signal isn't present** —
one because the signal was never armed to compete (Ticket A/`F1-s2c-t5-01`, CI blind spot),
the other because the signal was lost under real classification (F2-002, a live-graph
property this CI-tier driver cannot reproduce without a live classifier — out of this
ticket's fix scope, noted here for the cross-reference the taxonomy doc promises).

## Fix (resolver-side, own branch — NOT fixed here)

The declared-winner table (`data/psychoed/collisions/collision_table.json`) must cover
cross-category collisions under full arming, not just the row's own declared pair. Two
non-exclusive directions, neither decided here:

1. **Widen the collision table's disambiguation signal set** so `default_winner` is a
   safer / more clinically-considered choice under all-six-armed topology specifically
   (today's `3c`-favoring default was set with only the phrase's home category and its one
   known collision partner in mind — under all-six-armed, this same phrase's default now
   silently wins for EVERY category it happens to overlap, which may not have been
   evaluated when the winner was chosen).
2. **Make the CI driver's arming topology prod-shaped by default** for collision-sensitive
   rows (this task's own `test_psychoed_fixture_all_armed` does exactly this, and is the
   permanent regression instrument for this class going forward — see Definition of Done).

## Definition of Done

1. `F1-s2c-t5-01-all-armed`'s strict xfail
   (`tests/test_psychoed_fixtures_ci.py::_ALL_ARMED_KNOWN_DIVERGENCES`, citing this ticket)
   turns XPASS when the resolver-side fix lands — `strict=True` makes that XPASS a loud CI
   failure, forcing the re-pin below rather than letting the fix land unnoticed.
2. Re-pin `_ALL_ARMED_KNOWN_DIVERGENCES` to drop `F1-s2c-t5-01` once its all-armed
   resolution matches the row's declared contract (`s2c`/`s2c-t5`), or — if the ratified fix
   changes what the row SHOULD expect under all-six-armed topology — re-pin the row's
   `expect` block to the new declared contract directly, whichever the fix shape turns out
   to require.
3. F2-002's flip-tier-only miss is NOT closed by this ticket's DoD (it requires a live
   classifier / real grief-context signal fix, a different surface) — tracked here for the
   cross-reference only; do not conflate closing this ticket with F2-002 going green at
   flip tier.
