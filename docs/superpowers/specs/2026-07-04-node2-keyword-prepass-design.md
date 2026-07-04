# Design Spec — Node-2 deterministic keyword pre-pass (v7.2 amendment)

**Status:** Phase-1 design (no code). **Approved direction:** 2026-07-04 (architecture ruling — keyword pre-pass over classifier calibration). **Maps to:** v7 §Rules Service, Node 2 (intent_route) / Node 4 (skill_select) interaction, Cardinal Rule 5 (rules before LLM).

## 1. Motivation (measured)
The W6 measured pass (`scripts/w6_routing_diagnostic.py`) showed **deterministic** (temp-0, 5/5 stable) `intent_route` misclassifications of skill-worthy phrasings:
- "how are you tracking my mood today" → `info_request` (→ knowledge_retrieve, mood offered but answered as info)
- "كيف مزاجي اليوم؟" → `general_chat` (→ freeflow)
- "i have no motivation to do anything" → `general_chat` (→ freeflow)

Because it is deterministic and reproducible, this is a systematic classifier limitation, not noise — exactly the case Cardinal Rule 5 prescribes a rules tier for. Classifier prompt calibration is **rejected as primary** (probabilistic tuning to approximate what a rules tier does exactly; every future phrasing gap reopens it) — retained as a later supplement, not an alternative.

**This single fix also unblocks W4's prod confirmation** (EN/AR mood would reach skill_select → offer → accept → `score_mood`) **and gives G5-b's Option C its first live exposure.**

## 2. v7.2 amendment framing (Constraint 1) — NOT silent conformance
The Rules Service spec enumerates rules at **Nodes 1, 4, 5, 8**. Node 2 is **not** a rules node in v7. A pre-classifier rules tier is squarely within Cardinal Rule 5's spirit but **extends the Rules Service's letter to a new node.** Treated like the tiering change: a small **amendment record**, spec text updated on merge, human sign-off on the extension (not just the code). This doc is that record's design half.

## 3. Where it slots — rules-first STAGE inside Node 2 (argued)
**Decision: a rules-first stage INSIDE `intent_route_node`, run before the LLM classifier call — NOT a new graph node.**

Rejected alternative — a new node between Node 1 and Node 2: it would rewire the `safety_check → intent_route` conditional edge (`graph.py:274`), touching the crisis-adjacent routing topology for no benefit. The pre-pass needs no independent node; it is literally "rules before the LLM" *within* the node that owns the LLM call.

Why rules-first stage:
- **Cardinal Rule 5 is literally satisfied** — the deterministic tier runs first, inside Node 2, before the classifier.
- **Zero graph-topology change** — no new node, no edge rewiring; `_route_after_safety` (crisis routing) is untouched.
- **Node 1 safety stays first, always** — the pre-pass is in Node 2, strictly after `safety_check`. Order invariant preserved.
- **The classifier still runs** (Constraint 3) — the pre-pass sets a hint; `intent_route` then calls the classifier as today for blended intent + engagement/intensity scoring (state components 4/5 keep populating). The pre-pass never replaces classification.

## 4. Mechanism

### 4.1 Trigger source — single-sourced (Constraint 2)
The pre-pass matches against the **same `target_presentations` the skill JSONs already carry** — compiled once at load from the existing `_SKILLS = {sid: load_skill(sid) …}` registry (`skill_select.py:26`) into a match structure (trie or longest-match table). **No duplicated keyword list, ever.** A clinician editing triggers in the CMS updates one source; the pre-pass recompiles from it. (Avoids the two-names/two-numbers divergence class.) Honors the existing `KEYWORD_SEMANTIC_SKIP` exclusions so `post_crisis_check_in`/`psychotic_referral` are not pre-matched.

### 4.2 Match logic — reuse Node 4's
Same substring, case-insensitive, longest-match-wins rule as `skill_select.py:444-451` (EN against `message_en`; AR against `raw_message`). Factor the matcher into one shared helper so Node 2 pre-pass and Node 4 keyword tier can never diverge.

### 4.3 Hint, don't hijack (Constraint 3)
On a match the pre-pass emits a **routing hint only**:
- `prepass_matched: list[str]` — matched skill_id(s), ranked by longest match.
- `prepass_rule_id: str` — provenance for the audit trail.

It does **not** set `active_skill_id`, does **not** overwrite `primary_intent`, does **not** force-enter a skill. `_route_after_intent` gains ONE branch — mirroring the existing **Routing-SF-2** precedent (which already redirects acute `general_chat` to skill_select): *if `prepass_matched` and no `active_skill_id` and intent ∉ {crisis, scope_refusal, jailbreak} → route to `skill_select`*. Placed AFTER the safety/monitoring/psychotic-referral redirects, BEFORE the confidence gate — same slot and precedence as Routing-SF-2. Node 4 then runs its **normal** match → R1 offer / entry / accept-flow logic. The pre-pass only guarantees the turn **reaches** Node 4; Node 4 decides what happens there.

### 4.4 The `info_request` interaction — specified design decision
"how are you tracking my mood today" classifies `info_request`, which today routes skill_select → `knowledge_retrieve` (`_route_after_skill_select`, graph.py:239). **Decision:** the pre-pass branch routes the turn to skill_select so the **offer is surfaced** (`offered_skill_ids` set), while `info_request` is **preserved** — so the turn still answers the info question via knowledge_retrieve AND the skill offer is now pending for the next turn's accept. This satisfies "hint don't hijack" (intent not overwritten) and surfaces the skill without hijacking the info answer. **Open decision for review:** whether an EN mood phrasing should instead be re-intented to `new_skill` (stronger, but hijacks the classifier) — recommend the offer-preserving form above; flag for owner.

## 5. State + audit (Constraint 4 — the bug-#2 lesson)
- `prepass_matched: list[str]` and `prepass_rule_id: Optional[str]` declared as **SageState channels on day one** (LangGraph drops undeclared keys — bug #2). 
- `prepass_rule_id` written to the `session_audit` row alongside the existing routing trail.
- **One compiled-graph test** (`graph.compile().ainvoke`) proving both fields survive the reducer — not just the node's return dict.

## 6. Regression battery = the W6 harness (Constraint 5)
`scripts/w6_routing_diagnostic.py` is the acceptance suite:
- **Acceptance (must flip to reach skill_select):** the three measured misses — mood EN, mood AR, BA "no motivation".
- **Unchanged (must not regress):** canonical triggers (overwhelm→dbt_tipp, panic→grounding, worry→worry_time) still enter/offer as today; the two **ambiguous anecdotes** are explicitly NOT the pre-pass's job — `financial_anxiety` vs worry_time (semantic ambiguity) and infidelity→mood (questionable expectation) must assert **unchanged** behavior.
- **Latency:** trie/regex compile at load, per-turn match **sub-5ms, no model call** — assert in the test.

## 7. Invariants (restated)
1. Node 1 safety first — pre-pass is strictly after `safety_check`.
2. Classifier still runs — blended intent + engagement/intensity keep populating.
3. Offer semantics preserved — pre-pass routes to Node 4; never force-enters.
4. Single-sourced triggers — compiled from skill JSONs, never duplicated.
5. `_route_after_safety` (crisis routing) untouched — the new branch is in `_route_after_intent` only.

## 8. Open decisions for the owner
- **§4.4** EN mood: offer-preserving (recommended) vs re-intent to new_skill.
- **v7.2 amendment record** sign-off (the Node-2 rules-tier extension).
- Fixes #2 (semantic precision) and #3 (infidelity clinician one-liner) remain separate, lower priority.

## 9. Phase plan
- **Phase 1 (this doc):** design + amendment framing. ← you are here.
- **Phase 2 (on approval):** TDD implement — shared matcher helper, pre-pass stage, `_route_after_intent` branch, state channels + audit + reducer test, W6 harness as acceptance. One PR, spec text updated on merge (v7.2). Then prod verify the three misses reach skill_select + the EN mood accept-flow reaches `score_mood` (closes W4 prod confirmation).
