# Fast-Follow Ledger — `classifier_degraded` Positive Path Marker

Date: 2026-07-28. Status: LEDGERED, not started (fast-follow behind the pins deploy).
Origin: item-1 review, Q-a. Ordered by reviewer in the deploy sequence.

## What

When the pinned classifier chain exhausts (primary + pinned fallback fail) and the
static neutral fallback serves the turn, append a POSITIVE path marker
`classifier_degraded` to `state["path"]` (and thus `session_audit.path`), in
`intent_route` where the static-fallback shape is detected (the same detection the
Q-a end-to-end test exercises: no-JSON → general_chat @ 0.5).

## Why (and why it must not slip)

Today the degraded route is distinguishable only by inference (empty `meta_out`,
confidence exactly 0.5, general_chat). C3 discipline: guards assert the positive
path; silence-shaped inference is how gaps hide. Two ledgered dependencies:

1. **Matrix re-baseline:** distributional runs must be able to EXCLUDE (or count)
   degraded-classifier turns per fixture — a provider outage during a baseline
   window would otherwise contaminate frequencies invisibly. The marker is the
   exclusion key; the baseline header should report degraded-turn count (expected
   0).
2. **RT-1 closure:** Node-3 reachability measurement needs to distinguish
   "low_confidence via genuine boundary uncertainty" from "low_confidence via
   classifier unavailability" — the marker separates the two populations.

## Shape

One marker append + behavior-anchored tests (marker present on the degraded route,
absent on healthy turns and on genuine low-confidence classifications). No flag
needed (pure additive path marker, same class as existing lifecycle markers) unless
review rules otherwise.
