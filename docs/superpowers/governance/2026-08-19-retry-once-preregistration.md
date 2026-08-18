# Pre-registered decision — embed-timeout residual fix = RETRY-ONCE (owner F-1, 2026-08-19)

**Context:** the warm-instance embed-timeout class (2 smoke turns, 2026-08-18; watch #474)
is CPU contention beating `EMBEDDING_TIMEOUT_SECONDS=10.0` on the single shared instance —
NOT a warmup gap (warmup-blocks-readiness exists and worked; characterization in the
2026-08-18 session record). Fix is FROZEN until after 2026-08-25 signatures.

**Pre-registered pick: retry-once on embed timeout.** Rationale: raising the deadline
trades the p95 <3s latency budget against the same contention; capacity is the expensive
answer to a problem retry-once likely absorbs.

**Binding condition:** the retry MUST be visible in the audit row (`embedding_retried:
true`, same conditional-key discipline as `embedding_timeout`) so the #474 watchdog can
distinguish recovered-on-retry from clean-first-pass. A retry that hides the signal #474
exists to surface is rejected by construction.

**Reopen clause:** if watchdog data before execution shows retry-once would not have
saved the observed events (e.g. contention windows longer than a retry survives), the
decision reopens with that evidence. Otherwise post-08-25 execution proceeds on this
record without further deliberation.
