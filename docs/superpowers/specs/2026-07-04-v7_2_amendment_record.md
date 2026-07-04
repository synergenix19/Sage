# v7.2 Amendment Record — Node-2 keyword pre-pass (2026-07-04)

**Status:** spec artifact riding `feat/node2-keyword-prepass`. **Direction approved + product-owner sign-off:** 2026-07-04 (architecture ruling; both open decisions ruled — §4.4 offer-preserving, v7.2 approved). Design: `specs/2026-07-04-node2-keyword-prepass-design.md`.

## §Rules Service — amended (new rules-bearing node)
v7 enumerated Rules-Service rules at Nodes 1, 4, 5, 8. **v7.2 adds a deterministic rules-first STAGE at Node 2 (`intent_route`)** — a keyword pre-pass that runs before the LLM classifier (Cardinal Rule 5, rules before LLM). It is a stage inside Node 2, not a new graph node: `safety_check → intent_route` topology and `_route_after_safety` (crisis routing) are unchanged.

## What it does
- Deterministically matches the message against the **same `target_presentations` the skill JSONs carry** (single-sourced via the shared `skills/keyword_matcher.py`; Node 4 now uses the identical helper — the two can't diverge).
- Emits a routing HINT (`prepass_matched`, `prepass_rule_id`) — **hint, not hijack**: `primary_intent` is preserved, the classifier still runs (blended intent + engagement/intensity keep populating), Node 4's R1 offer/enter logic still governs. `_route_after_intent` gains ONE branch (mirroring the Routing-SF-2 precedent — after the safety/monitoring/psychotic redirects, before the confidence gate, guarded on `active_skill_id`): a general_chat turn with a pre-pass match reaches `skill_select` instead of freeflow.

## Why (measured)
Temp-0, 5/5-stable `intent_route` misclassifications sent skill-worthy phrasings to freeflow/knowledge_retrieve: AR mood + "no motivation" → general_chat; EN mood → info_request. Deterministic ⇒ a rules tier fixes it exactly (classifier calibration rejected as primary; retained as later supplement). Unblocks W4's prod confirmation + gives G5-b its first live exposure.

## Governance-clean
No new clinical sign-off: the pre-pass consumes the already clinician-authored `target_presentations` verbatim — no clinical content changes hands. Product-owner go recorded as the amendment sign-off. `prepass_matched`/`prepass_rule_id` declared as SageState channels (bug-#2 lesson) + a compiled-graph reducer test; `prepass_rule_id` on the audit trail. W6 harness (`scripts/w6_routing_diagnostic.py`) is the acceptance battery; sub-5ms, no model call.

## Scope invariants (held)
Node 1 safety first (pre-pass is strictly after `safety_check`); `_route_after_safety` untouched; classifier still runs; offer semantics preserved; triggers single-sourced. `safety_check.py` not modified.
