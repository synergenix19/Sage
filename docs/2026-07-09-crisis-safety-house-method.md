# The crisis-safety house method — three moves that resolved #191, #205, and the copy-gate catches

**Status:** Adopted as engineering policy 2026-07-09. Short, deliberately. This codifies a pattern that
recurred three times in one week and worked every time — so the next contributor inherits it as method,
not folklore.

## The three moves

Every safety-critical fix this week composed the same three moves. Apply them in order.

1. **Put the invariant at the boundary the data actually crosses — not where the spec says a boundary
   *should* be.** #191's crisis state was fixed by making the render decision follow an out-of-band flag
   at the render boundary; #205's crisis affordance was fixed by making the card/role follow the routing
   path at the `server.py` emit boundary (because `crisis_response → END` bypasses `output_gate` — the
   spec's nominal gate). The rule: find the point that *every* relevant turn provably passes through, and
   enforce there. If that isn't where the spec drew the gate, record the deviation (see the ADR
   `2026-07-08-crisis-emit-boundary-invariant.md`) rather than pretending the graph matches the doc.

2. **Put a permanent, deterministic backstop behind the probabilistic layer.** A classifier with ≥95%
   recall still misses ≤5%. The architecture's answer is never "make the classifier perfect" — it's a
   deterministic layer that catches the miss (Cardinal Rule 4). #205's backstop fires when a crisis
   response ships without crisis affordances; it is a pure structural check (path vs emitted metadata,
   zero text heuristics), so it has no false-positive surface, and it stays in the architecture forever —
   it should approach never-firing as the classifier improves, which is the correct steady state for a
   backstop, not a reason to remove it.

3. **Run a driven verification before relying on green suites.** A green unit suite proves the code does
   what the test says; it does not prove the *system* does the right thing on the path a real turn takes.
   Every incident this week was caught or confirmed by a driven run (a real request through the deployed
   stack, asserted against the real DB), not by the suite. #205's continuation miss was invisible to unit
   tests and visible immediately in the audit trail. Drive the exact failing scenario, on the real
   artifact, and assert on the durable record — before you call it done.

## The flywheel — backstop misses feed the fix

The deterministic backstop (move 2) writes an L2 clinical-review flag on every catch. Each flag is also a
**labelled miss**: the exact input the classifier should have caught. Those flags are the collection
mechanism for the continuation-context retraining set (the TD3 / Component-2 work). So the backstop is not
only a safety net — it is the data pipeline that eventually shrinks its own firing rate. Wire the two
together deliberately: a backstop whose catches are not harvested is a net with no feedback loop.

## When to apply

Any change on a safety-critical path (crisis, clinical-flag, safety routing). For ordinary feature work,
moves 1 and 3 still pay off; move 2 is reserved for paths where a silent miss reaches a user as harm.

## Evidence

- #191 — in-band crisis-signalling render fix (move 1 + move 3).
- #205 — crisis affordance follows routing path + path-consistency backstop (all three) + ADR for the
  boundary deviation.
- Copy-gate catches — driven review surfaced defects the aggregate suite hid (move 3).
