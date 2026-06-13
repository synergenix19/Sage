# Work Order — Per-Session Concurrency: the Offer Lifecycle Is Now the Sensitive Surface

**Date opened:** 2026-06-13 (reviewer-mandated promotion of a PR #4 audit addendum note to a tracked item)
**Owner:** Engineering (production-path); ties into the pre-prod pool-characterization blocker
**Severity framing:** POC-acceptable as-is; **production needs the lock**

## The defect class (pre-existing, system-wide)

The server has no per-session serialization: two simultaneous in-flight requests on the same `session_id` (multi-tab, double-send, retry-after-timeout-while-original-completes) interleave their LangGraph checkpoint reads/writes. This predates the engagement feature — concurrent requests could always corrupt conversational state (history, skill step position, trajectories).

## Why the risk profile changed with R1 (PR #4)

The same defect now races the **consent invariant** specifically: offer creation, accept-promotion, decline-recording, and the S1-1 unseen-offer void are all read-modify-write sequences on `offered_skill_ids`/`declined_skills`. Interleavings can produce: a promotion racing a void (user "accepts" an offer the other request just voided), double-recorded declines, or an offer created by one request and silently clobbered by the other's stale write. Same defect, higher-stakes surface: this is consent state for a clinical feature, not just conversation flow.

The S1-1b serialization analysis (audit addendum 2) holds for the single-client case only: the void is awaited inline before the error response returns, so a follow-up sent after the client receives the error is strictly ordered. Nothing orders two requests that are in flight at once.

## Production-path fix

Lightweight per-session serialization at the server boundary: an in-process `asyncio.Lock` keyed by `session_id` around the graph invocation (+ the S1-1b void) for single-instance deployments; a Postgres advisory lock on `hashtext(session_id)` if/when the service scales to multiple replicas (Railway). Reject-or-queue policy for the second request is a product decision (suggest: queue with a short timeout; never run concurrently).

## Verification

- A two-concurrent-requests-same-session test (the pool-characterization harness is the natural home) asserting: offers never promote after a void, declines never double-record, the second request observes the first's completed state.
- Re-run the pool characterization with the lock in place (the prior LLM-path concurrency ceiling test is documented as contaminated; this supersedes it for the engagement surface).

## Status

OPEN. Not started. Linked items: pre-prod blockers (pool characterization), PR #4 audit addendum 2 (S1-1b residual).
