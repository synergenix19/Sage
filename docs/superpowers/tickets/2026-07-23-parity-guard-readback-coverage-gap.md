# Ticket — flag-parity guard asserts parity on only the vars `/health` exposes (readback-coverage hole)

**Priority: high (instrument correctness). Found 2026-07-23 by the v5 reconciliation.** The #360 flag-parity
guard is the instrument that makes conformance reproducible from master — but its "VERIFIED" verdict covers
less than it appears to, and that gap already hid a real confound.

## The defect
`measure_layer1_fullgraph.py::_flag_parity` compares the run env against `prod_env`, where
`prod_env = serving or desired` — it PREFERS the `/health/version` serving readback. That readback exposes only
**8 `*_raw_env` flags** (crisis_tiering, skill_media, route_precedence, medical_redflag_guard,
venting_suppression, ipv_preemption, d1_screen, d1_screen_shadow). `config.py` reads **~27** SAGE_ vars. The
~19 not in the readback — including `SAGE_COSINE_ABSTAIN_THRESHOLD`, `SAGE_KNOWLEDGE_ABSTAIN_THRESHOLD`,
`SAGE_SKILL_RUNNER_UP_MARGIN/MIN`, model names — are **not compared** (line: `reported = {k: prod_env[k] for k
in mapping if k in prod_env}` — a var absent from `prod_env` is simply never asserted). So when serving is
available, the guard silently checks 8 of 27 and passes VERIFIED on the rest.

## Proof it matters (already bit us)
Two v5 runs of prod `1f687c57` BOTH passed the guard as VERIFIED while differing on
`SAGE_COSINE_ABSTAIN_THRESHOLD` (one run 0.42 = prod, the other 0.0 = fail-open KB-abstain, off-prod). That flag
changes routing; the two runs scored 8/36 and 6/36. The guard's whole purpose is "measurement parity = config
parity," and it certified two different configs as parity-equal. See
`2026-07-23-bot-behaviour-conformance-v5-reconciled-baseline-1f687c57.md`.

## The fix
Assert EVERY config var `config.py` reads, not just the readback subset:
1. For vars present in the serving readback → compare against serving (authoritative, as today).
2. For vars ABSENT from the readback → fall back to railway **DESIRED** (`_fetch_prod_env`, already fetched)
   and compare against that.
3. If a config var is matched by **neither** serving nor desired → the run is **UNVERIFIED for that var**,
   surfaced loudly and stamped; do not report a bare VERIFIED. Optionally FAIL closed for routing-relevant vars.
4. Add the six-test-suite a case: "a config var absent from the /health readback is still asserted (via desired)
   or explicitly flagged unverified — never silently passed."

## Secondary (product): widen the `/health/version` readback
The readback is the authoritative serving-state source; it should expose ALL routing-relevant config vars as
`*_raw_env`, not just the 8 booleans. Then serving-vs-desired parity is total and the guard needs no
desired-fallback for coverage. Tracked separately from the guard fix above (which should land regardless).

## Owner / links
Guard = PR #360 (`measure_layer1_fullgraph.py`, `tests/test_conformance_flag_parity.py`). This gap is the
confound #4 cited in the ARCHITECTURE_BOUNDARIES "noise floor" rule. The variance-characterization run must NOT
proceed until the run env mirrors ALL config vars at prod values (cosine 0.42 included), so this fix and that
run are coupled.
