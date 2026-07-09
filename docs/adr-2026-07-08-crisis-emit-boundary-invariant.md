# ADR 2026-07-08 — The emit boundary is the universal invariant point; crisis bypasses output_gate

**Status:** Accepted (pending clinical/PO sign-off on PR #210). **Absolute Rule 1 deviation flag — recorded, not silently accepted.**

## Context

v7 specifies **Node 8 (`output_gate`)** as the point where, for *every* response, the system (a) runs the probabilistic safety post-check, (b) applies deterministic output guardrails, and (c) assembles the audit trail. The spec reads as "a gate every response passes through."

The graph does **not** do that. `crisis_response → END` **bypasses `output_gate`** (confirmed in `graph.py` and by every crisis turn's `node_path = [safety_check, crisis_response]`, no output_gate). #205 exposed the consequence: there was no universal chokepoint guaranteeing structural invariants (crisis affordances, audit completeness) on the crisis path — the affordance (card + `role='crisis'`) was derived from the initial tier at the `server.py` emit boundary, and a monitoring-continuation turn (`crisis_response` at `crisis_tier='none'`) lost its card.

Placement of the #205 fix (the path-consistency rule) at the `server.py` emit boundary was forced by this bypass. That placement is correct — but the **bypass itself** is a v7 deviation that needs a conscious decision, not silent acceptance (the #191 docs-drift lesson: a spec that says "gate every response" over a graph that doesn't is exactly how drift starts).

## Decision — (b) Bless the emit boundary as the universal invariant point

1. **The probabilistic safety post-check (Falcon-3B / LLM re-check) is FORMALLY WAIVED for deterministic crisis scripts.** The crisis response is a clinician-authored `crisis_content` script, validated at authoring time (the skills model). There is nothing probabilistic to re-check, and re-checking it would add LLM latency to the one path with a sub-second budget — architecturally pointless. This waiver honors the dual-guardrail *intent*: the LLM's output is post-checked; a deterministic script is not.

2. **Audit-trail assembly and structural invariants are GUARANTEED at the emit boundary** (`server.py`, post-`ainvoke`), which **every** turn — including `crisis_response → END` — provably passes. The emit boundary is now the formal home for:
   - crisis affordance derivation (card + `role='crisis'` **follow the routing path**, not the initial tier — #205, Cardinal Rule 4);
   - the path-consistency backstop (`crisis_response` ran but affordance absent → force + L2 clinical-review flag);
   - any future structural, non-probabilistic invariant that must hold for **all** paths.
   Probabilistic re-checks stay in `output_gate` (the freeflow path); they do **not** move to the emit boundary.

3. **`output_gate` remains the probabilistic post-check + guardrail node for every NON-crisis path.** This ADR does not remove it; it clarifies that it is not universal and names what is.

## Verification — audit completeness (no per-path exception; PDPL)

The condition on this decision: confirm crisis turns get a **complete, structural** audit record (path, tier, script/skill, latency) — traceability admits no per-path exception.

Result (2026-07-08, prod `session_audit`):
- **Structural:** `crisis_response` writes `write_session_audit({**state, path, gate_path='crisis', crisis_state, ...})` on every invocation before END (`graph.py`) — not incidental.
- `path` ✓, `crisis_tier` ✓, `tier_rule_id` ✓, `crisis_flags` ✓, `node_path` ✓.
- **GAP FOUND + FIXED:** `latency_ms` was **NULL on crisis turns (0/18)** vs 56/56 non-crisis, because `output_gate` stamps `latency_ms` and crisis bypasses it. A per-path traceability exception — the exact thing PDPL forbids. **Fixed in PR #210:** `crisis_response` now stamps `latency_ms` from `turn_started_at`, matching `output_gate`. The staging repro asserts crisis turns record latency.
- Crisis uses a `crisis_content` rule, not a skill, so `active_skill_id` is empty by design; the tiering provenance (`tier_rule_id`) is recorded. (Open nicety for a later PR: record the crisis-response script/rule id explicitly, not just the tier rule.)

## Alternatives considered

**(a) Route crisis through `output_gate` like every other turn.** Rejected: adds the Falcon-3B post-check latency to the sub-second crisis path, to re-check a deterministic clinician-authored script that was validated at authoring — architecturally pointless, and a latency regression on the most time-sensitive path.

## Consequences

- The living architecture doc (`docs/SageAI_architecture_current.md`) and any v7 amendment record should reflect that Node 8 is **not** universal; the emit boundary is the universal structural-invariant + audit-completeness point. (Amendment note to follow the same sign-off path as other v7 amendments.)
- New structural invariants that must hold for all paths belong at the emit boundary, tested as pure functions (e.g. `_crisis_affordance_decision`), not assumed to run in `output_gate`.

## References

#205 (the incident + audit trace), PR #210 (this fix), #191 (the in-band-signaling render fix + the docs-drift lesson), Cardinal Rule 4 (deterministic layers catch the probabilistic miss), v7 §Node 8, `docs/v7.1-post-crisis-state-addendum.md`.
