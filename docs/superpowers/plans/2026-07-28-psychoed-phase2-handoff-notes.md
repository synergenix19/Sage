# Psychoed Phase 2 Handoff Notes

**Phase 1 content complete.** These notes carry forward the binding requirements for Phase 2 implementation, adding execution-discovered refinements from the Phase 1 controller review.

**Filename note:** the Phase 1 content plan (`2026-07-23-psychoed-phase1-content-plan.md`, Task 14) named this file `2026-07-23-psychoed-phase2-handoff-notes.md`. It was actually authored 2026-07-28, so it is filed under that date; the file is not renamed to match the earlier reference.

---

## I. Binding Requirements (Spec-Referenced)

### 1. Rule-6 Carry-Forward Evaluation Mechanic (§4.4 + Schema Extension 7)

The step-policy rule 6 evaluates per-skill against a family-level carry-forward counter. **Critical:** the evaluation condition must read:

```
prior_exposure[family_of(skill.kb_ref)] >= threshold
```

NOT `prior_exposure[skill_id]`.

**Why:** carry-forward writes per-article-family `prior_exposure`. If rule 6 evaluates against `skill_id`, the counter never increments (always reads zero). The skip condition only works if rule 6 resolves the skill's `kb_ref` to its family and reads that family's counter.

**Implementation gate:** Verify in Phase 2 resolver that rule-6 conditions read `skill.kb_ref` and pass family-level counters. Query: does the evaluation gate ever skip a rule-6 skip?


### 2. Mechanism-A Retirement File (§0 Carry-Forward)

Each category flip retires its consult-set entry in **the same change**. The consult set lives in:

```
info_request_consult_set.py
```

Refer to go-live record PR#362 for the current consult-set structure and per-category retirement pattern. When a category transitions from phase-1 (dev/demo) to phase-2 (live), its entry in `info_request_consult_set.py` is removed in the flip commit.


### 3. F1 Naturalistic-Set Seed (§3c Go-Live Record)

The §3c paraphrase variant that routed to `presence_only` (identified in the Phase 1 go-live record as a single-variant near-miss) is a **mandatory F1 fixture**. This phrasing was observed live and must be caught by the trigger tables.

**F1 commitment:** Include this as a naturalistic test case asserting that the phrase is CAUGHT by the trigger tables and routes to the 3c psychoed serve, not to `presence_only` — `presence_only` is the near-miss failure this seed exists to prevent.


### 4. State Channel Keys — Exact List (§4.2)

Declare the full set of SageState keys before build. Spec §4.2 enumerates 10 keys across two lifetimes, verbatim:

- **Per-turn (reset every turn):** `psychoed_serve`
- **Pathway-scoped (persist while active):** `psychoed_active_category`, `psychoed_delivery_shape`, `psychoed_blocks_served`, `psychoed_menu_offered`, `psychoed_weave_fired`, `psychoed_weave_pending`, `psychoed_matched_row_id`, `psychoed_collision_path`, `psychoed_framing`

**Audit-before-clear:** pathway-scoped keys clear on exit (new skill activation, safety-route firing, explicit close) — audit-feeding facts persist to `session_audit` BEFORE clearing.

**Never-disarm:** nothing in this channel is readable by upstream safety nodes; one-way dependency by construction.

- In code: `check_state_channels.py`
- In graph test suite: assert state shape at each node transition

Do not ship a build with undeclared state keys. The graph test must validate state-channel shape before the first handler runs.


### 5. PSY-WEAVE-1 Precedence (§2.1 Step 1)

The PSY-WEAVE-1 evaluator runs **before resolver matching on weave-pending turns**. When a turn is marked weave-pending (Phase 1 entry gate), PSY-WEAVE-1 evaluation occurs first; only if weave clears (or fails closed to crisis) does the turn proceed to block resolver.


### 6. Node-8 Hash-Mismatch Failure Path (§6.2)

When Node-8 (`output_gate`) cannot verify block fetch:

```
block → re-serve pinned signed artifact → neutral referral on fetch-fail
```

Never emit an unverified block to the user. The failure path is deterministic: re-serve the pinned SIGNED ARTIFACT (spec §6.2) plus a neutral referral template (no unverified block content). This is unrelated to the crisis pinned-card UI — Node-8 is `output_gate`, not a card-rendering node.


### 7. Shared-Scripts Constants Module (Task 9 Interface)

The Phase 2 constants module loads all four keys from `shared_scripts.en.json` verbatim: `diagnosis_guard_stage1`, `diagnosis_guard_stage2`, `safety_weave_script`, `human_referral_close`. This is the interface boundary: import the scripts as declared in the data file, do not synthesize or override.

---

## II. Execution-Discovered Refinements (Controller Additions)

### Addition 1: Mechanism-A Retirement Location & Pattern

**Source:** go-live record PR#362.

The retirement file is `info_request_consult_set.py`. Per-category retirement happens **in the same commit** as each category's flip. When a category transitions to Phase 2 live:

- Identify its entry in `info_request_consult_set.py`
- Remove that entry in the flip commit
- No separate retirement commit; single change for both category enable + consult-set remove


### Addition 2: PSY-WEAVE-1 Evaluator Implementation

**Source:** `data/psychoed/weave/psy_weave_1.en.json` → `evaluation_semantics` field.

**Do NOT implement from prose.** The data file's `evaluation_semantics` field is the source of truth. Implement exactly what that field specifies.

**Evaluation order (mandatory):**

1. **Contradiction markers first** — substring normalized match against contradiction markers in `evaluation_semantics`
2. **Then clear-negative regex** — fullmatch against the clear-negative regex (if present)
3. **Default fail-closed-to-crisis** — any ambiguity or evaluation error routes to crisis-path referral

This ordering ensures the most specific (contradiction) signals override general negation patterns.


### Addition 3: human_referral_close Pending-Script Gate

**Source:** `data/psychoed/shared/shared_scripts.en.json`.

**Status:** `human_referral_close` is currently marked `PENDING-CLINICIAN`.

**Phase 2 requirement:** The constants module must load the four script keys verbatim — `diagnosis_guard_stage1`, `diagnosis_guard_stage2`, `safety_weave_script`, `human_referral_close` — but **MUST fail loudly (build-time check)** if any script value still starts with `"PENDING-CLINICIAN"` when its consuming template is enabled.

- No template may ship rendering a pending script.
- If a template references `human_referral_close` and its value is pending, the build fails with a clear error.
- Pending entries are not a blocker to other category flips (Phase 2 may gate only templates that consume pending scripts).


### Addition 4: Collision Handling — Subsumption-Aware Resolver

**Source:** `data/psychoed/collisions/collision_table.json`.

The Node-4 resolver must implement **subsumption-aware** collision handling. The declared winners in `collision_table.json` define precedence, including:

- The weave-dominance rule for the two subsumption pairs
- The interim fail-toward-weave default for *"What's happening to me?"* while pending

**Pending entries (unresolved collisions):**

- **BLOCK** the owning categories' flips (do not enable a category whose collisions are unresolved)
- Do NOT block the build itself; pending entries in the table are acceptable for Phase 2 planning

**Implementation:** Node-4's resolver references `collision_table.json` to determine winner precedence on ambiguous routing.


### Addition 5: Bridge Schema — Three Forms Phase 2 Must Consume

**Source:** `data/psychoed/manifests/4b.json`, `1f.json`, `7c.json`; identified in Phase 1 trigger-table audits.

The bridge schema has **THREE consumable forms**, distinguished by which of `block_id` / `skill_id` is set:

1. **Block-level, with `skill_id` set** (primary/ordinary case)
   - `block_id` is set AND `skill_id` is set
   - Example: `4b-b6` carries two such entries — `box_breathing` and `grounding_5_4_3_2_1` (both `doc_route: "1a"`)

2. **Block-level, with `skill_id` NULL** (missing-skill case, not condition-level)
   - `block_id` is set (the block itself exists and resolves fine) but `skill_id` is null
   - Example: `1f-b4` → `doc_target: "Worry Tree"`, `skill_id: null`, `status: "pending_clinician_no_registry_skill"` — the block resolves; there is simply no `worry_tree` skill in the registry to bridge to (`worry_time` is a different technique)
   - **Render NO offer** until either a `worry_tree` skill exists or clinical designates an existing alternative (packet ask 12-a). The remediation here is a **missing SKILL**, not a missing block — do not treat this as an incomplete-block problem.

3. **Condition-level** (interim/pending, no block at all)
   - `block_id` is null; a `condition` string stands in for a block reference
   - The only instance in the current manifests: `7c`'s bridge — `block_id: null`, `condition: "specific_person_or_message"`, `skill_id: "assertive_communication"` (`doc_route: "6c"`)
   - Represents a pending capability, not yet resolvable to a block

**Phase 2 continuation template must consume all three.** Do not conflate form 2 and form 3: 1f-b4 is a block-level bridge with a missing skill (`block_id` present), NOT a condition-level bridge — only 7c's entry is condition-level.

---

### Addition 6: block_guard Single-Sourcing Discipline

**Source:** spec §6.1 delivery; Single-sourcing rule #321.

**Case: s2c-b8** (prolonged_grief_support_note, behavior `append_support_note_no_diagnosis_naming`)

The serve template appends the note sentence. **Critical:** that sentence ALSO exists as the block's final content sentence.

- The append behavior must **NOT duplicate** the sentence.
- Gate reads the guard; template reads the block content.
- Do NOT copy the sentence into the append logic (violates single-sourcing #321).
- Implementation: template checks `block_guard` on s2c-b8; if true, appends the note. The note text comes from the block's final sentence only.


### Addition 7: F1 Naturalistic-Set Seeds (Multi-Form)

**Source:** Phase 1 go-live record; subsumption analysis.

**Mandatory F1 fixtures:**

1. The **§3c paraphrase variant** that routed to `presence_only` live (the near-miss from Phase 1 go-live record)
   - Confirms trigger tables catch real-world phrasings
   
2. **Two subsumption long-forms** as F1 cases
   - Assert the declared winners from `collision_table.json`
   - One case for each subsumption pair — the two real pairs in the table:
     - *"Why do I feel like this?"* (short) subsumed by *"Why do I feel like this for no reason?"* (long) — categories `3c`/`4b`, declared winner **3c** (weave-carrying category wins, fail-toward-weave)
     - *"I want to become more confident."* (short) subsumed by *"I want to become more confident socially."* (long) — categories `6d`/`7c`, declared winner **7c** (long-form wins; both weave-less)
   - Include both members of each pair as F1 cases asserting the winner behavior

These seeds ensure the F1 fixture suite covers both observed naturalistic variants and declared subsumption precedence.


### Addition 8: Test-Suite Note for Phase 3 — Block-Disk Cross-Check

**Source:** Phase 1 architecture review.

**Current:** The block-disk cross-check is **subset-only** — a block existing only on disk (rogue block, not in manifest) is tolerated.

**Phase 3 action:** Tighten to **set-equality** when the fixture harness lands.

- Phase 2: Keep subset-only (data files may advance faster than fixtures)
- Phase 3: Assert that blocks in manifest and blocks on disk are identical sets
- This prevents silent data drift (blocks indexed but not on disk, or vice versa)


### Addition 9: Weave Contradiction-Marker Matching is Substring, Not Word-Boundary

**Source:** `data/psychoed/weave/psy_weave_1.en.json` (`contradiction_markers`) + final-review pass.

The current evaluator semantics match contradiction markers (`but`, `sometimes`, `kind of`, `maybe`, `a little`, `not really`) as **raw substrings** against the normalized reply. This means `"but"` also hits inside `"doubt"` and `"nobody"` — a false-positive contradiction hit that fails the turn closed to crisis. This is **safe** (fail-closed-to-crisis is the correct direction on ambiguity) **but noisy** (more crisis-path escalations than the marker list intends).

**Phase 2 action:** Move to word-boundary matching (e.g. `\bbut\b`) for the contradiction markers. Because this changes matching behavior on live data, **clinician re-ratifies the marker patterns at the point of that change** — this is not a silent engineering tightening.


### Addition 10: Phase-3 Test — Guards↔`safety_weave` Implication is Unpinned

**Source:** manifest audit across all 6 categories, final-review pass.

Today, every category where `safety_weave: true` (3c, s2c) also carries `safety_weave_script`-consuming guards in its `guards` list, and this holds consistently across all 6 manifests — but **nothing asserts it**. The relationship (weave-on categories carry the weave guard) is currently true by inspection only, not by test.

**Phase 3 action:** Add a test asserting the implication `safety_weave: true → guards` includes the weave-consuming guard, for every manifest. This pins a currently-true-but-unenforced invariant before Phase 3's fixture harness lands, so a future category addition or edit can't silently decouple weave scope from its guard.

---

## III. Implementation Checkpoints

### Phase 2 Startup Checklist

- [ ] Rule-6 evaluation: confirm `skill.kb_ref` family-level counter reads
- [ ] `info_request_consult_set.py` reviewed; retirement pattern understood
- [ ] `check_state_channels.py` lists all SageState keys; graph test validates shape
- [ ] PSY-WEAVE-1 evaluator implemented from `evaluation_semantics` (not prose)
- [ ] Build gate: pending `human_referral_close` scripts fail the build if template is enabled
- [ ] Node-4 resolver: subsumption-aware, references `collision_table.json`
- [ ] Bridge schema: continuation template consumes all three forms (block-level+skill, block-level+null-skill, condition-level)
- [ ] Null-skill_id bridges (e.g. 1f-b4): template renders no offer (blocks Phase 2 category enables)
- [ ] s2c-b8 block_guard: append behavior uses single-sourced note text (no duplication)
- [ ] F1 fixtures: includes §3c paraphrase + two subsumption long-forms
- [ ] Test suite: block-disk cross-check is subset-only (Phase 3 will tighten)
- [ ] Contradiction markers noted as substring (not word-boundary) matching; Phase 2 tightens with clinician re-ratification
- [ ] Phase-3 test noted for guards↔safety_weave implication (unpinned invariant)

### Open Questions for Phase 2 Owner

1. **PSY-WEAVE-1 threshold vs. binary:** Does the evaluator return pass/fail (binary) or a confidence score? The `evaluation_semantics` field should clarify.
2. **Collision-table pending entries:** Which subsumption pairs are still marked pending? These block category flips until resolved.
3. **Null-skill_id bridges:** Is 1f-b4 `worry_tree` the only null-skill_id case, or are there others?

---

## IV. Cross-References

- **Spec sections:** §0, §2.1, §3c, §4.2, §4.4, §6.1, §6.2, §7c
- **Go-live record:** PR#362 (consult-set pattern)
- **Data files:**
  - `data/psychoed/weave/psy_weave_1.en.json` (evaluator source)
  - `data/psychoed/shared/shared_scripts.en.json` (pending scripts)
  - `data/psychoed/collisions/collision_table.json` (subsumption winners)
- **Code gates:**
  - `check_state_channels.py` (state validation)
  - Graph test suite (state shape assertion)
  - Build gate for pending scripts
- **Retired from Phase 1:**
  - Mechanism-A consult-set entries (per PR#362)
  - §3c paraphrase moved to F1 fixtures

---

## V. Notes for Future Phases

- **Phase 2:** Remain subset-only on block-disk cross-check (data files move faster than fixtures).
- **Phase 3:** Tighten cross-check to set-equality; add fixture harness for comprehensive block coverage.
- **Arabic (Phase 4):** Ensure PSY-WEAVE-1 `evaluation_semantics` supports Arabic contradiction markers (language-neutral if possible, or per-language overrides).

---

## VI. As-built deltas (Phase 2 execution, 2026-07-29)

Phase 2 (Tasks 1–13) is now built. The following are execution-discovered facts that
diverge from, or refine, the plan above — surfaced here for the Phase 3/4 owner, not
re-litigated against the binding requirements in Section I.

1. **`psychoed_family_exposures` channel replaces the dead `techniques_used` read.**
   `therapeutic_profile["techniques_used"]` has no writer anywhere in the codebase and no
   DB column (`postgres_repository.py:16-40`) — `prior_exposure` via that path was always
   0, everywhere, not just for psychoed. Task 9 added `_psychoed_family_exposure(state,
   skill)` (`skill_executor.py`), folded in additively via `max()` so the dead read stays
   harmless while the live family-carry-forward channel takes over. This is a seam finding
   that reaches beyond psychoed's own scope.

2. **`psychoed_weave_escalation` channel + the `skill_select`→`crisis_response` edge-map
   delta.** A PSY-WEAVE-1 escalation (`skill_select_node` finds `psychoed_weave_pending`
   True and the reply is not a clear negative) sets `psychoed_weave_escalation=True` and is
   the ONE new edge Phase 2 added to the graph: `graph.py`'s
   `_route_after_skill_select` checks this flag as its top-priority branch —
   before containment, screen, abstain, info_request, or active-skill — and routes straight
   to `crisis_response`, wired via `graph.add_conditional_edges("skill_select", ...,
   {"crisis_response": "crisis_response", ...})`. No other node in the graph gained a new
   edge for Phase 2.

3. **§6.2 corruption fallback chain:** payload's own `category` field → `psychoed_active_category`
   → (both absent, unreachable by construction but held mechanically, not by convention) CRITICAL
   log + first-enabled-category `check_in` (`sorted(config.PSYCHOED_CATEGORIES)[0]`, hardcoded
   `"1f"` tertiary default if no category is enabled at all). Implemented in
   `output_gate.py`'s psychoed verbatim hash gate (~L961-981).

4. **Mechanism-A coexistence is per-category**, not global: a category can be live under
   Phase-2 psychoed pathways while Mechanism-A's `info_request_consult_set.py` still carries
   OTHER categories' consult entries. Retirement of a category's consult-set entry happens
   at flip-time — in the same commit that enables the category — never as a separate pass.

5. **Grief-context is 2 live signals, not 3.** `_psychoed_grief_context` (`skill_select.py`)
   checks (a) `grief_loss` recently offered/active (`active_skill_id` or
   `offered_skill_ids`) and (b) `psychoed_active_category == "s2c"`. A third,
   clinical-flag-based signal was considered per the amended plan but no grief-coded
   `flag_id` exists in `rules/data/safety/clinical_flag_patterns.json` — wiring a
   nonexistent flag would be a disarmed-alarm shape, so it ships with only the two live
   signals; add the third only once the safety lane declares one.

6. **Outcome-2 (semantic backstop) is gated by the same two things outcome-1 is:**
   active-skill suppression (skipped when a skill is already active) and Classifier A's
   acute-distress veto (spec §2.1/§2.2). The Task-10 section of the mechanism plan
   under-specified this — the gap was caught by spec-anchored review, not by a failing
   test, and fixed before Task 10 closed (`knowledge_retrieve.py`'s outcome-2 branch).

7. **EN-only pathway entry is enforced at two constructors, with an AR fall-through at a
   third path (spec §3.7):** the resolver entry (`skill_select_node`) and the outcome-2
   backstop (`knowledge_retrieve_node`) both gate on `detected_language == "en"` — a
   psychoed_serve payload cannot be CREATED on a non-English turn. The third path,
   menu-after-weave, is deliberately language-UNgated (PSY-WEAVE-1 evaluates a live safety
   reply regardless of language) but its own composition
   (`freeflow_respond_node`) falls through to the normal LLM freeflow path on a
   non-English turn rather than serving the EN-ratified verbatim `menu_offer` — three
   EN-ratified-copy leak paths, all closed.

8. **Pathway-clear-on-exit fires at 9 explicit call sites**, all in `skill_select.py`
   (`_psychoed_pathway_clear(state)` at the non-psychoed-skill-activation, HR-referral, and
   offer-accept exits). The 10th call site, in `graph.py`'s `_crisis_response_node`, is
   scoped to the PSY-WEAVE-1 escalation case only. An **ordinary** (non-weave) crisis
   intercept does not call `_psychoed_pathway_clear` at all — it clears on the *next* turn
   via the normal per-turn state spread (accepted at Task 8 review: path-accumulation and
   escalation-scoped clear are both fine, since an ordinary crisis turn was never mid-serve
   in the first place).

9. **menu_first + weave is data-guarded, not code-guarded.** No category with
   `delivery_shape: "menu_first"` also declares `safety_weave: true` in its manifest today,
   so the "weave fires on a menu-first serve" combination is currently unreachable — by
   content, not by a code assertion. If a future category ships both, the interaction is
   unverified.

10. **`compose_turn1`'s exception path is caught by the server's blanket handler, not a
    psychoed-specific one** — a malformed payload or missing shared script fails the turn
    closed (hard failure, no partial/garbled response reaches the user), but there is no
    graceful psychoed-specific fallback. Triaged as a graceful-fallback candidate, non-blocking
    for Phase 2 go-live.

11. **Ambiguous menu-label multi-match fails closed at both resolution tiers.** In
    `resolver._match_menu_label`, if the substring-containment tier yields more than one
    match, the stopword-filtered token-subset tier is never consulted as a tiebreaker — the
    whole lookup returns `None` (falls through to the global trigger-table match, or the
    category's first block on the answer-first default). This was a post-review fix (see
    `resolver.py`'s module docstring): the original code resolved multi-match ambiguity by
    manifest array position, which is the same "undeclared winner" pattern the cross-category
    collision tier explicitly refuses.

12. **L2 template status strings (e.g. `human_referral_close`'s `PENDING-CLINICIAN` marker)
    are ADVISORY ONLY — there is no loader-level enforcement gate today.** Nothing fails
    the build if a pending script is wired into a live template; `psychoed_continuation`
    carrying a pending-tone-confirm script is a Phase-4 flip precondition to be enforced by
    process, not by code, until a build-time check is added (Addition 3, Section II, is
    still open).

13. **Outcome-2's return dict omits `skill_match_method`.** This is cosmetic — the audit
    trail does not lose signal because `psychoed_collision_path == "semantic_backstop"` is
    the field that actually carries "this was a backstop serve, not a resolver hit" forward
    into the Node-8 audit row.

14. **Answer-first block selection is a v1 limitation: label-containment else first-block,
    not a specific-question mapping.** `resolver._pick_block` matches the *trigger phrase
    itself* against each block's `menu_label` (substring, then stopword-filtered token
    subset); on zero matches it falls back to the category's first manifest block. For
    example, "Why do I feel numb?" (row `3c-t3`) serves `3c-b1` ("What is depression?"),
    not the anhedonia-specific block `3c-b4` — even though `3c-b4`'s own label is "Why
    things can feel numb or empty (anhedonia)" — because the phrase and the label don't
    share a matching substring/token-subset under the current containment rules. True
    specific-question→block mapping is a clinical judgment call, not one engineering should
    invent by tuning string-matching heuristics: it requires a clinician-ratified
    per-phrase block-hint column on the trigger tables. **Packet addendum required** (new
    ask: ratify phrase→block hints per category); Phase-3 F1 fixtures then re-pin the
    specific-block expectation. Until that lands, block selection stays deterministic
    containment-or-first-block only — no similarity/embedding fallback is permitted here,
    consistent with the resolver's "never similarity" invariant. Surfaced by
    `tests/test_psychoed_graph.py`'s Task 13 graph test, which pins the v1 behavior
    (`3c-b1`) with an explicit forward-reference comment to this delta.

---

*Document created: 2026-07-28*
*Phase 1 content handoff complete; Phase 2 implementation to commence.*
*Section VI (as-built deltas) added: 2026-07-29, Phase 2 Task 13.*
