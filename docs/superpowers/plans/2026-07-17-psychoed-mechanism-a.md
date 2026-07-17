# Psychoed Mechanism-A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** psychoed presentations correctly classified as `info_request` that match an *instructional* skill get that skill delivered, instead of being force-routed to the KB-then-freeflow path. Fail-open: no instructional match → KB path exactly as today.

**Architecture:** a skill-matching *consult* at the `info_request` short-circuit (skill_select.py:586-595), scoped to a doc-derived `INSTRUCTIONAL_SKILLS` set, plus a routing condition in `_route_after_skill_select`. `intent_route` is NOT touched (the classifier is right). Design: `docs/superpowers/specs/2026-07-17-psychoed-mechanism-a-design.md`.

## Global Constraints
- **Fail-open:** no instructional match ⇒ byte-identical to today's `info_request → knowledge_retrieve` path.
- **Instructional set = doc Format cell marked `Instructional`, VERBATIM only.** Exclude `single_message` (Worry Time) and `info_resource`/link-handoff items (§1f factsheets, `sleep-001` — which carries the S1b timing suppression the consult must NOT bypass).
- **Do not touch `intent_route`.** No experiential skill is ever imposed on an info_request.
- Assert on routing/selection behavior, never on copy strings.

## Task 1: Derive `INSTRUCTIONAL_SKILLS` from the doc + pin its P0b convergence
**Files:** Create `src/sage_poc/skills/instructional_set.py`; Test `tests/test_instructional_set.py`.

- [ ] **Step 1: Derive the set from the doc.** Read the BOT BEHAVIOUR Format column (scratchpad `bot_behaviour.txt`, and/or `BOT_BEHAVIOUR_conformance_matrix.md`) for every pathway whose Format cell is **`Instructional`** verbatim. Map each to its skill_id in `skill_ids.py` / `src/sage_poc/skills/*.json`. Sleep Hygiene is the doc's clean exemplar. Build the candidate list and **write the derivation table** (doc pathway → Format cell → skill_id) into the test file as a comment so the provenance is auditable.
- [ ] **Step 2: Apply the exclusions (write them as failing assertions first).** Assert `worry_time` NOT in the set (it is `single_message`), assert `sleep-001` / info_resource items NOT in the set (link handoffs; `sleep-001` owns S1b timing suppression). Confirm each excluded id's actual Format value from the doc in a comment.
- [ ] **Step 3: Implement** `INSTRUCTIONAL_SKILLS: frozenset[str]` = the verbatim-Instructional skill_ids, with an in-file docstring naming it a STOPGAP for P0b's `delivery_format` field. Every member cross-checked to exist in `SKILL_REGISTRY`.
- [ ] **Step 4: Pin convergence (xfail-until-P0b).** Add `@pytest.mark.xfail(reason="until P0b delivery_format field lands", strict=False)` test asserting `INSTRUCTIONAL_SKILLS == frozenset(s.id for s in _all_skills if getattr(s, "delivery_format", None) == "instructional")`. Today it xfails (field absent); the day P0b lands it flips to a real pass-or-fail, forcing reconciliation. Comment names it the guard against a 3rd dormant-divergent artifact.
- [ ] **Step 5: Run + Commit** `feat(psychoed): doc-derived INSTRUCTIONAL_SKILLS stopgap + P0b convergence test`.

## Task 2: Instructional consult at the info_request short-circuit
**Files:** Modify `src/sage_poc/nodes/skill_select.py` (info_request branch, 586-595); Test `tests/test_psychoed_mechanism_a.py`.

**Interfaces — Consumes:** `INSTRUCTIONAL_SKILLS`, the existing keyword/semantic matching helpers the node already uses for the normal path.

- [ ] **Step 1: Write failing unit tests.** For an `info_request` state whose message matches an instructional skill (use a §1f/§6d drive), `skill_select_node` returns `active_skill_id` = that instructional skill + `skill_match_method == "info_request_instructional_match"`. For an `info_request` matching only an experiential skill OR nothing ("what's the crisis helpline number?"), it returns the KB-bound result unchanged (no active_skill_id set, `skill_match_method None`). A pre-existing `active_skill_id` is preserved untouched.
- [ ] **Step 2: Run — expect FAIL.**
- [ ] **Step 3: Implement.** In the info_request branch, before returning the KB-bound result, run the SAME keyword/semantic matching the normal path uses; if the top match is in `INSTRUCTIONAL_SKILLS`, select it (set `active_skill_id`, `active_step_id` = its first step, `skill_match_method = "info_request_instructional_match"`). Otherwise return today's KB-bound result verbatim. Do not run matching for experiential skills into selection — only accept an instructional top match.
- [ ] **Step 4: Run — expect PASS.** Regression: `tests/test_skill_select.py`, `tests/test_skill_select_offer.py` green.
- [ ] **Step 5: Commit** `feat(psychoed): instructional consult before info_request KB short-circuit`.

## Task 3: Route the selected instructional skill to the executor
**Files:** Modify `src/sage_poc/graph.py` (`_route_after_skill_select`, 345-346); Test `tests/test_psychoed_mechanism_a.py`.

- [ ] **Step 1: Write failing tests.** Full-graph (mirror an existing full-graph test's LLM handling): a §1f/§6d drive (info_request + instructional match) → routes to `skill_executor` and delivers the psychoed skill (NOT knowledge_retrieve/freeflow). A genuine info_request with no instructional match → `knowledge_retrieve` exactly as today.
- [ ] **Step 2: Run — expect FAIL** (currently the `info_request → knowledge_retrieve` line at 345-346 diverts even a selected skill).
- [ ] **Step 3: Implement.** Condition the `if primary_intent == "info_request": return "knowledge_retrieve"` so it fires only when NO instructional skill was selected this turn — key on `skill_match_method == "info_request_instructional_match"` (route to `skill_executor`), else keep the KB return. Do NOT key on `active_skill_id` alone (a pre-existing active skill must not change the KB routing).
- [ ] **Step 4: Run — expect PASS.** Regression: `tests/test_routing.py` green; `python scripts/check_state_channels.py` clean.
- [ ] **Step 5: Commit** `feat(psychoed): route info_request instructional matches to skill_executor`.

## Task 4: Red-drive corpus + must-stay-KB guard fixtures
**Files:** Test `tests/test_psychoed_mechanism_a.py`.

- [ ] **Step 1: Red drives — the 23 Mechanism-A utterances verbatim** (filter the corpus to §1f/§3c/§6d/S2c/§7c info_request drives; §4a is Mechanism B, exclude). Assert: with the fix, each **reaches skill_select matching** (no longer KB-short-circuited) — for §1f/§6d assert the instructional skill is delivered; for §7c (matching gap, per the packet) assert the *routing* now reaches matching even though the match itself is the packet's content question (separate the routing win from the content gap in the assertion + comment).
- [ ] **Step 2: Must-stay-KB/freeflow controls (the over-pull guard — REQUIRED, not afterthought).** The 4 characterization controls (topic-mention-without-request, e.g. "I'm so tired today" as chat) + genuine info-requests ("what's the crisis helpline number?", "how does this app work?") → route to KB/freeflow exactly as today. Red before the fix would over-pull; green after proves fail-open holds.
- [ ] **Step 3: Run — expect PASS.** Any red drive that doesn't reach matching = a real gap → back to Task 2/3, not a test edit.
- [ ] **Step 4: Commit** `test(psychoed): 23 red drives + must-stay-KB over-pull guard`.

## Post-tasks
- Final whole-branch review. Confirm: fail-open byte-identical; instructional set doc-verbatim + convergence-pinned; S1b timing suppression not bypassed; over-pull guard covers the controls; §4a/§7c matching gap stays the packet's (not code-worked-around).
- Note recoverable slice: §1f/§6d clean; §3c/S2c partial; §4a (Mechanism B) + §7c (matching gap) NOT recovered here.
