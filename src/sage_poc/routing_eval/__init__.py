"""Phase 0 routing-eval harness (Track B).

Measurement core for the SKILL_ROUTING_V2 gate-6 baseline: eval-record schema,
multi-threshold per-stratum AUGRC sweep, and the four blocking checks
(BC1 crisis-path-invariance, BC2 referral-exclusion, BC3 per-stratum parity,
BC4 split-reporting). Operates on records carrying synthetic or real router
output; §1 is exercised against deterministic adversarial fixtures.

Spec: docs/superpowers/plans/2026-06-20-phase0-harness-spec.md
"""
