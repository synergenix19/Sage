# Known-Red Ledger — Full-Suite Baseline Failures (2026-07-29)

Owner rider on the instrument-branch approval: the known-red count moved from 6
(2026-07-28, pins branch verification) to 15 (2026-07-29, this branch's
verification) "and nobody decided that either." This ledger makes the number a
tracked fact instead of an ambient one.

## The 15, by family (all reproduce on clean origin/master or are known races)

- retrieval-contract x4 (pre-existing on master)
- crisis-templating byte-identical x3 (pre-existing on master; was 2 on 07-28 — DELTA UNEXPLAINED, needs an owner)
- test_health_ready routing-mode/reranker x1 (pre-existing)
- composer overflow w/ large cultural override x1 (pre-existing)
- rules dialectical secondary-intent x1 (pre-existing)
- tier1 body-scan snapshot x1 (pre-existing)
- test_server_offer_voiding x4 — BGE-warmup race, passes 6/6 with SAGE_WARMUP_BGE=0 in both worktrees (environment, not code)
(+2 code-switching tests flaked on clean master only, not in this branch's failing set)

## Disposition

None caused by the pins or instrument branches (verified on clean-master
worktrees both dates). The 6→15 growth is master drift in test health with no
decision attached. Action: this ledger is the tracking artifact; each family
needs an owner or an explicit wontfix at the next conformance checkpoint; the
crisis-templating 2→3 delta is the highest-priority row (safety-surface test).
