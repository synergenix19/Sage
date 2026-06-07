# test_server.py — Module-Fixture Contamination Bug

**Date:** 2026-06-07  
**Discovered during:** BA/PD keyword routing fix (cab4725) test verification  
**Severity:** CI signal reliability — not a user-facing bug  
**Status:** FIXED — per-test `session_id` fixture applied to all 12 real-graph call sites; causal proof and shuffle verification pending (see Verification section)

---

## Root Cause

`test_server.py` uses a `scope="module"` `client` fixture where all tests share `"session_id": "test-session"`. LangGraph's `AsyncPostgresSaver` persists checkpoint state keyed by `thread_id`. Earlier tests in the module send crisis and therapeutic messages to `"test-session"` (e.g., `"I want to end it all"`, `"أريد الموت"`); the polluted checkpoint bleeds into whichever test runs next. That test sees unexpected session state — a stale crisis flag, an active skill, an error condition — and fails. Because the contamination lands on different module members depending on the execution timing of the full suite, failures float non-deterministically across tests within the module.

This is a shared-mutable-state-across-tests bug. The shared mutable state is the LangGraph checkpoint for `"test-session"` in the database, and the sharing point is the `scope="module"` fixture that reuses it across all tests in the module without teardown.

---

## Evidence

**Observed failure pattern across 4 full-suite runs (2026-06-07, `--ignore=tests/test_skill_routing_ba_pd.py`):**

| Run | Tree state | test_server.py failures |
|---|---|---|
| Pre-change run 1 | bfbada4 | none |
| Pre-change run 2 | bfbada4 | `test_all_audit_headers_present` |
| Post-change run 1 | cab4725 | `test_chat_returns_text_for_valid_message` |
| Post-change run 2 | cab4725 | `test_chat_returns_text_for_valid_message` |
| Post-change run 3 | cab4725 | none |

**All failing tests assert server-health, not routing content:**

- `test_chat_returns_text_for_valid_message`: `assert res.status_code == 200`, `assert len(res.text.strip()) > 10`
- `test_all_audit_headers_present`: `assert res.status_code == 200` + 8 specific headers present

These assertions fail only when the server returns 500 or an empty body — contaminated session state symptoms. A routing or keyword change cannot produce these failures; any routing outcome returns 200 with a non-trivial body. The module is the unit of contamination; which member gets caught is order-dependent.

**All affected tests pass in isolation every time.** Isolation removes the ordering dependency, confirming root cause is cross-test state, not each test's own logic.

---

## Why This Matters

A suite with non-deterministic order-dependent failures is unreliable as a CI signal in both directions:

- A genuine regression can hide behind "probably the flaky module"
- A clean change can be blocked by noise (as nearly happened with cab4725)

This directly undercuts the 12 routing gate tests and two invariant tests added in cab4725 — their value depends on a green run meaning something. **This is not test-hygiene polish; it is a pre-Gitex CI-trust requirement.** Rank it above cosmetic test work.

---

## Fix Options (Priority Order)

**1. Per-test unique `session_id` — recommended (smallest change, directly targets root cause)**

The state is keyed by `thread_id` in LangGraph. Giving each test a unique session_id means no test can inherit state from a sibling:

```python
import uuid

@pytest.fixture
def session_id():
    return f"test-{uuid.uuid4()}"

def test_chat_returns_text_for_valid_message(client, session_id):
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "..."}],
        "session_id": session_id,
    })
    ...
```

**2. `scope="function"` client fixture**

Creates a fresh `TestClient(app)` per test, reinitializing the lifespan and clearing all module-level state. More expensive (lifespan runs per test) but completely isolating — eliminates both the checkpoint-bleed and any other module-level state contamination:

```python
@pytest.fixture  # remove scope="module"
def client():
    from server import app
    with TestClient(app) as c:
        yield c
```

**3. Explicit checkpoint teardown**

Delete the `"test-session"` checkpoint from the database after each test. Fragile: if a test fails before teardown, contamination persists. Use only as a last resort if the other options are infeasible.

**Acceptance criterion:** Same failure set (zero non-skipped failures) across N ≥ 3 consecutive full-suite runs in the same order. Determinism is what's being restored.

---

## Scope Boundary

**Do not absorb this finding:** During a contaminated run, a `[FALSE HOLD] body_scan held on general stress in Arabizi: 'ana muta3ab w mtwatr'` routing assertion was observed in `test_entry_screen_integration.py`. This is a routing-content assertion, not fixture-state bleed — `body_scan` being held on Arabizi general stress could be a genuine routing issue. It may itself be a victim of contamination, or it may be a real finding that only surfaced during a noisy run.

Do not classify it as harness noise by association. Once the fixture is isolated and full-suite runs are deterministic, re-run and check whether this reproduces. If it does, it is a separate clinical-review routing item for the Arabic track and should be treated with the same care as any Arabic routing finding on this platform.

---

## Cross-Reference

This is the first documented write-up of Python pytest ordering contamination in the `sage_poc` test suite. It is **not** the same class as the Playwright E2E suite failures documented in `project_playwright_suite_status.md` (that document covers Playwright frontend flakiness from `supabase.auth.signOut()` invalidating shared JWTs — a different harness, different mechanism, different fix).
