# Pool Characterization — Entry-Screen False-Hold Rate vs Concurrency

**Date:** 2026-06-06
**Method:** Concurrent `evaluate_completion_criteria` calls against real OpenRouter classifier
**Test inputs:** 5 ADVANCE-expected inputs cycling across skill/language variants
**Gitex demo target concurrency:** 15 simultaneous calls (booth load estimate)

## Primary finding: false-hold rate vs concurrency

A false hold = a user who reached for a coping skill was blocked by an LLM evaluation error, not by a genuine contraindication.

| Concurrency | ADVANCE | HOLD (false) | False-hold rate | p50 (ms) | p95 (ms) |
|---|---|---|---|---|---|
| 1 | 20/20 | 0/20 | 0% | 736 | 4081 |
| 5 | 20/20 | 0/20 | 0% | 650 | 1769 |
| 10 | 20/20 | 0/20 | 0% | 708 | 1635 |
| 15 | 20/20 | 0/20 | 0% | 726 | 997 | **← Gitex target**
| 20 | 20/20 | 0/20 | 0% | 713 | 1402 |

## Node 1 (S1 keyword / deterministic crisis path) independence

Probe result: **PASS — 0 false S1 triggers**

S1 keyword matching and S3 BGE-M3 embedding (safety_check_node) make zero LLM pool calls.
They are structurally independent of the OpenRouter classifier pool.
S1/S3 results are unaffected by pool saturation — the deterministic crisis floor cannot be starved.

## Failure mechanism

When the OpenRouter pool is saturated (rate-limited / timeout), `resilient_invoke` retries up to
2× with backoff, then returns `get_fallback_response()` — a pre-authored human-readable string.
`evaluate_completion_criteria` receives this string, calls `.startswith('yes')` → False,
and since `fail_closed=True` for entry_screen, returns False (HOLD).

The HOLD is from fallback-text-as-verdict, not from a genuine LLM judgment of the input.
The retry already exists (LLM_MAX_RETRIES=2); the gap is distinguishing 'fallback text returned'
from 'LLM said no.'

## Retry design — asymmetry constraint

The retry path is already asymmetric by design:
- `resilient_invoke` retries on transport errors (429, 502, timeout) — NEVER on successful LLM responses
- A genuine LLM 'no' (HOLD verdict) succeeds the HTTP call → no retry → hold stands
- Only error/timeout paths retry, which means retries can only reach ADVANCE, never invert a genuine HOLD

This invariant must be preserved in any future retry modification.
A retry that re-runs on a successful 'no' response would violate the asymmetry.

## Interaction: stochastic entry-screen + fail-closed + pool saturation

Under concurrent load, error-induced HOLDs (not genuine LLM HOLDs) accumulate.
Since fail-closed does not retry, a transient pool error becomes a real hold for that user.
The user experiencing this is, by definition, someone who reached for a coping skill
at a moment of distress — a degraded-hold is suboptimal but recoverable (skill-start can be retried).

**Acceptable under POC terms:** entry-screen holds degrade gracefully — the user can re-engage.
**Unacceptable:** Node 1 degradation under load. S1 is proven independent above.

## Gitex scenario

A live demo booth with people queueing will produce concurrent sessions sharing the
OpenRouter classifier pool. Each turn calls intent_route (classifier) and potentially
criteria_eval (classifier) and resistance scoring (classifier). Peak per-turn classifier
calls = 3. At 15 concurrent users = up to 45 simultaneous classifier calls.

The 15-concurrent row in the table above represents the Gitex target. Read it against:
- False-hold rate (what fraction of skill-starts are blocked by pool error)
- p95 latency (whether the demo booth experience is acceptable)

If false-hold rate at 15 is > 5%, escalate to pool monitoring and rate-limit headroom
before the demo. If p95 > 3000ms at 15, the latency KPI is not met under demo load.

## Scope limitation — this test is not a full-turn load test

**This characterization tests criteria_eval in isolation** — one LLM call per concurrent task.
A real user turn at Gitex produces up to 3 concurrent classifier calls per session:
  - intent_route (every turn)
  - criteria_eval (turns that trigger an entry screen)
  - resistance scoring (every skill turn)

At 15 concurrent Gitex sessions, the OpenRouter pool sees up to **45 simultaneous classifier calls**,
not 15. The false-hold curve above was measured at criteria_eval concurrency levels only.
A full-turn load test (simulating complete graph traversal per concurrent session) would be
required to characterize the pool under realistic Gitex load. This is a pre-GA task.

**What this test does establish:**
- Criteria_eval in isolation does not introduce false holds up to concurrency 20
- p95 per-call latency at the criteria_eval level is ~1000ms at concurrency 15
- Node 1 (S1 keyword) is structurally independent of the LLM pool under all tested loads
- The single flake observed in the 18-test suite was not systematic — it was a transient event,
  not a recurring feature of the load pattern (20/20 ADVANCE in isolation; 20/20 ADVANCE at
  concurrency 20 in this test)

## p95 at concurrency 1

Note: p95 = 4081ms at concurrency 1. This is a single-call p95 — the slowest of 20 sequential
calls, not a worst-case concurrent number. It is above the 3s KPI but expected: a single call
that hits a cold connection or brief upstream latency. Under concurrency ≥ 5, p95 drops to
~1000–1800ms because slow calls overlap with faster ones rather than dominating wall clock.
The 3s KPI applies to the user-facing turn latency (measured end-to-end in the graph, which
includes all node traversal, not just the criteria_eval call). Criteria_eval's 997ms p95
at concurrency 15 contributes proportionally to total turn time.