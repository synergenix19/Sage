# test_server.py — Module-Fixture Contamination Bug

**Date:** 2026-06-07  
**Discovered during:** BA/PD keyword routing fix (cab4725) test verification  
**Severity:** CI signal reliability — not a user-facing bug  
**Status:** OPEN — fix needed before CI gates are trusted for clinical routing changes

---

## Finding

`tests/test_server.py` has a `scope="module"` `client` fixture that is contaminated by earlier test modules in the full suite run. The symptom: different tests within `test_server.py` fail non-deterministically depending on test execution order. The same test passes in isolation every time but fails in the full suite.

**Observed failure pattern across 4 full-suite runs (2026-06-07):**

| Run | Tree state | test_server.py failures |
|---|---|---|
| Pre-change run 1 | bfbada4 | none |
| Pre-change run 2 | bfbada4 | `test_all_audit_headers_present` |
| Post-change run 1 | cab4725 | `test_chat_returns_text_for_valid_message` |
| Post-change run 2 | cab4725 | `test_chat_returns_text_for_valid_message` |
| Post-change run 3 | cab4725 | none |

Each of these tests asserts `res.status_code == 200` plus basic response structure — server-health assertions, not routing content. A routing or keyword change cannot cause them to fail; the failure mechanism is the server returning 500 or an empty body due to contaminated app state.

## Root Cause

Two compounding issues:

**1. `scope="module"` client picks up dirty global state.** The `client` fixture in `test_server.py` creates a `TestClient(app)` once per module via lifespan. Some test module that runs before `test_server.py` (alphabetically: test_resilience.py, test_rules_integration.py, test_rules_safety.py) modifies module-level state on `sage_poc` components — likely the circuit breaker, app.state, or LangGraph's in-memory structures — that persists into `test_server.py`'s fixture initialization.

**2. Shared `"test-session"` session_id.** All tests in `test_server.py` use `"session_id": "test-session"`. LangGraph's AsyncPostgresSaver persists checkpoint state to the database. By the time `test_chat_returns_text_for_valid_message` runs, the checkpoint for `"test-session"` may carry state from earlier tests in the module (crisis flags, active skill, error state) that alters routing or triggers an error on the next request.

## Why This Matters

This is a Gitex-quality-of-signal issue. A test suite with non-deterministic order-dependent failures means:

- A real regression can be dismissed as "probably the flaky module"
- A clean change can be blocked (as nearly happened here)
- The 12 routing-gate tests just added in cab4725 are only trustworthy if the surrounding suite signal is reliable

## Affected Tests

`test_server.py` member tests that have been observed failing in full-suite ordering runs:
- `test_chat_returns_text_for_valid_message` (2 of 3 post-change runs)
- `test_all_audit_headers_present` (1 of 2 pre-change runs)

Note: `test_entry_screen_integration.py` has a separate `test_az_general_stress_advances_body_scan` ordering failure (also confirmed pre-existing, different mechanism — likely BGE-M3 model state from a preceding test module affecting semantic scoring).

## Fix

**Immediate (CI noise reduction):** Change `scope="module"` to `scope="function"` in the `client` fixture in `test_server.py`. This creates a fresh `TestClient(app)` per test, eliminating cross-test fixture contamination within the module.

**Session isolation:** Change all `"session_id": "test-session"` to per-test unique session IDs (e.g., `f"test-{uuid4()}"`) so LangGraph checkpoints don't accumulate across tests.

**Prerequisite:** Identify which preceding test module(s) corrupt the shared state — add a targeted binary-search run (`pytest tests/test_resilience.py tests/test_server.py::test_chat_returns_text_for_valid_message -v`) to isolate the contaminator, then apply the fixture-scope fix.

## Classification Evidence

This was confirmed as pre-existing fixture contamination (not a regression from cab4725) by:
1. `test_server.py` member test failing on the pre-change tree (`test_all_audit_headers_present`, pre-change run 2)
2. The floating failure pattern across 4 runs — different members each time
3. Assertion content: all failing tests assert server-health (`status_code == 200`, headers present, response non-empty) — assertions that routing or keyword changes cannot trigger
4. All failing tests pass in isolation every time — isolation removes the ordering dependency, confirming the root cause is cross-test state, not the test's own logic
