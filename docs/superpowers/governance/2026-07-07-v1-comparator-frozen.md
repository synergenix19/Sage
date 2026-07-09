# FROZEN — V1 routing comparator for the V1→V2 measurement (Task 2, Option A)

**Frozen 2026-07-07.** This is the V1 baseline the V2 flip is judged against (plan `make-v2-semantic-routing-live.md` Task 2 / Task 12). **Option A:** the existing signed V1 measurement is adopted as the comparator of record; it is NOT re-measured (re-implementing a scorer for a safety-relevant number risks a non-comparable figure).

## The comparator (EN, held-out, flag-OFF pure V1, decontaminated, positive-control-gated)

| stratum | V1 | note |
|---|---|---|
| in_scope | **66%** (144/217) | Tier-1 keyword caught 0; all correct routes are Tier-2 semantic; 21% wrong-skill |
| id_oos (should ABSTAIN) | **35%** (25/71) | over-offers a skill on 65% that should abstain (OCD→cbt_thought_record, substance→dbt_tipp, ADHD-dx→psychoed_depression) |
| far_oos | **100%** (36/36) | |

Source: `docs/superpowers/plans/2026-06-24-v2-calibrated-retrieval-core-build-scope.md` §"The bar V2 must clear (V1 held-out baseline, 2026-06-24)".

## The provenance bridge — "this measures what prod at 1c9dfeb does" (three links)

1. **The measurement (link i).** 2026-06-24 build-scope benchmark: full Tier-1+Tier-2 pipeline, **flag OFF = pure V1**, EN, decontaminated (5 provenance-shared cases excluded), **pooled-OOF real models** (each case scored by the model that excluded it), positive-control-gated. Fixture set: `tests/fixtures/routing_eval/` at git `5e6b86e` (2026-06-24, last change to that dir).
   ⚠️ **SOFT LINK, labeled honestly:** the exact **tree SHA** the 2026-06-24 measurement ran on is **not stated in the build-scope record**. The method and date are cited; the commit is not recoverable from the doc. Do not imply a pinned tree here.
2. **The byte-identical guard (link ii).** `tests/test_v2_flag_off_byte_identical.py` — **7/7 green on worktree `e906770`** (2026-07-07), including the "has teeth" cases (flag-ON demonstrably differs). Proves **flags-off == V1 byte-identical** on the V2 tree, bridging link-i's tree and prod's tree.
3. **Prod (link iii).** Prod pinned at master **`1c9dfeb`**, flags-off (`SKILL_ROUTING_V2=0`/`SKILL_RERANK_ENABLED=0`, `SAGE_BUILD_SHA=1c9dfeb`), `/health/ready` → `routing_mode:"v1"` verified 2026-07-07. See `2026-07-07-deploy-provenance-trail.md`.

**Chain strength:** links (ii) and (iii) are pinned and verified; link (i)'s tree SHA is unrecovered (method/date only). The comparator is therefore method-anchored, not commit-anchored, on the measurement end.

## #139 caveat — pre-surface vs post-surface

The 66/35/100 was measured **before** `mindfulness_meditation` registration. Prod's routing surface at `1c9dfeb` **now includes** `mindfulness_meditation` (`skill_ids.py:10` + `clinical_clusters.py` membership → touches **cluster-argmax** routing). So this comparator is a **pre-#139-surface** measurement used against a **post-#139 prod**. Tied to the pending clinical ruling (`2026-07-07-mm-registration-live-in-prod-escalation.md`):
- If the ruling is **"not intended" and #139 rolls back** → the caveat dissolves (surface returns to the measured one).
- If **"intended and stays"** → a **bounded delta-check is owed** (byte-identical guard tree with `mindfulness_meditation` registered, same fixtures) **before Task 12 treats this comparator as exact rather than approximate.**

## DO NOT RE-MEASURE

This comparator is frozen precisely so nobody "refreshes" the V1 numbers **after** the V2 flags flip — a post-flip V1 re-measurement is not a clean baseline. The V1→V2 delta (Task 12) is judged against THIS frozen artifact.

## Instrument note (carried to Task 5 / Task 12)

`gate_runner` and `cross_validation` are abstract over routing (injected `routed_of`); no committed turnkey driver supplies a **real-model** `routed_of` over the bulk fixtures, and no `gate_runner --target prod` live path exists. **Task 5 (re-gate) and Task 12 (prod measurement) require that real-model routing driver to be built/located** — Option B's live-routing driver is a prerequisite there. Flagged before Phase 1 wiring per the instrument review.
