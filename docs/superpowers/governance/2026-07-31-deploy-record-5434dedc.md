# Deploy record — 5434dedc (2026-07-31): Vee sheet execution live

**Authorization:** PO in-session 2026-07-31 ("vee filled the sheet — all as recommended,
execute it"); the deploy is the sheet's execution vehicle — item 3 (MM deroute) and the
7c/7d keyword reverts are serving changes. Read as authorizing exactly this one governed
cycle.

**Payload (`2ab5d9a3..5434dedc`):** PR #403 (sheet execution: register clinical column
signed, MM deroute + regime-aware smoke check, 7c/7d reverts, execution record) + PR #400
(instrument DB-pool parity — instrument-only) + PR #399/#401 records. Serving-behavior
delta = exactly the sheet's three changes: MM unroutable, two box_breathing keywords and
one IE fragment removed.

## Cycle

1. Pre-verify: watchdog CLEAN (51 flags, three-way).
2. `deploy_prod.sh production 5434dedc…`: lock, ancestry, cache-bust, step-5 apply
   `already converged` (register delta was signature metadata only — values unchanged, so
   idempotent no-op, as expected).
3. `railway up` → converged; readback truthful (`build_sha 5434dedc`, consult `true`, C1
   `true`, crisis templated).
4. Drift probe: CLEAN (51 flags).
5. Smoke `--tier all`: **all must-pass green.** The regime-aware MM check made its first
   live assertion in the deroute regime: explicit mm request did NOT enter
   mindfulness_meditation. Tier-B skip carried explicitly (storage-state still a pending
   human step).
6. Lock released (`railway variable delete`), post-release readback stable.

## Finding surfaced by the first live deroute assertion (NEW, for Vee — urgent)

The explicit meditation request ("I want to try mindfulness meditation…") was absorbed by
**`mindfulness_body_scan`** (`skill-id=mindfulness_body_scan` on the accept turn) — which
is **also unsigned** (`approved_by: null`) and carries **no contraindications field**,
in the same §1a section-6 technique family (grounding/mindfulness can intensify
dissociation, derealization, flashback, psychosis-like states). Item 3's rationale applies
to it verbatim, and it now absorbs the derouted demand. This is the
regression-by-improvement class: the fix re-opened the same risk one skill over.
**Not acted on unilaterally** (the sheet's item 3 named MM only); queued as an urgent
decision item for Vee: deroute mindfulness_body_scan on the same one-line mechanism, or
sign it. Until ruled, the demand-absorption path is live.

## Rollback

Redeploy `2ab5d9a3` (restores MM routability and the three keywords — i.e., reverts the
clinically-directed changes; only under a superseding ruling).
