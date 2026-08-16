# Ticket: grief context needs a deterministic state source, not offered_skill_ids inference

**Filed:** 2026-08-11 (ruled adjudication, PR #414 merge cycle) · **Status:** open
**Type:** mechanism fix (small, safety-adjacent input) · **Gates:** S2c flip evaluation — lands BEFORE it
**Urgency:** low ONLY because S2c is itself P0-gated (reunification lexicon); do not let the gate ordering hide the dependency.

## The finding (F2-002, flip-tier record 2026-08-05 at 145c4e43)

F2-002 pins "numb" WITH grief context → s2c via `psychoed_collision_path='context_winner'`.
At CI tier (patched intent) it holds. At flip tier it missed: `context_winner` expected,
`default_winner` observed — the grief-context signal did not survive real classification.
Root shape: the resolver's `grief_context` input is INFERRED from `offered_skill_ids`
(a prior grief_loss offer turn), and under live intent_route the offer-turn shape that
seeds that inference is not reliably produced. Cross-referenced in
`docs/superpowers/tickets/2026-08-06-cross-category-collision-all-armed.md` as same-class
but explicitly OUTSIDE that ticket's DoD (different mechanism: signal loss, not arming).

## Ruled fix direction

Grief context gets a deterministic source: a grief disclosure recorded IN STATE at Node 4
when it occurs (declared channel + reset semantics + check_state_channels + graph test per
the state-channel seam discipline), consumed by the resolver as an explicit input — never
re-inferred from offer bookkeeping. Inference from `offered_skill_ids` is retired at the
same change.

## DoD

- Deterministic channel written at Node 4 on grief disclosure; resolver reads it.
- F2-002 passes at flip tier (context_winner under real classification) — the flip-tier
  runner is the acceptance instrument.
- Existing CI F2 rows stay green; collision-table `context_winner` semantics unchanged.
- Lands before S2c's flip evaluation regardless of the P0/lexicon clock.
