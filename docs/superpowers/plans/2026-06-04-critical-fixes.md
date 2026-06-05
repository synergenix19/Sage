# Critical Fixes — 4 Blockers (2026-06-04 Audit) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the four critical blockers identified in the 2026-06-04 full-system audit before any user-facing exposure.

**Architecture:** Four independent fixes touching four separate subsystems — safety rules JSON + test, skill JSON + rules JSON, skill_executor node, and audit.py + output_gate. All four can be implemented in the same branch. Each task produces a passing test before the fix is applied. Treat each task as atomic: commit it, then move to the next.

**Tech Stack:** Python 3.12 (via uv), pytest, asyncio, httpx, Supabase PostgREST REST API. No model changes, no migrations unless noted.

**Two tracks:**
- **Pure engineering (no gate):** Tasks 3 and 4. Fix and merge immediately.
- **Engineering + clinical sign-off required:** Tasks 1 and 2. Engineering work can land; PR must not merge until a named clinician has reviewed and `approved_by` is non-null.

**What this plan does NOT cover:**
- H-1 systemic fix (CI guard for `approved_by`/`active` — see `2026-06-04-approved-by-ci-guard.md`)
- SK-EN-002 full re-measurement against held-out corpus (must happen before clinical handoff)
- `_VETTED_FALLBACK_RESPONSE` content review (clinician-owned, part of the clinical package)
- CF-006 activation (explicitly excluded — see Task 2 framing below)

**CF-006 activation framing:** The danger with CRITICAL-2 is NOT the dead code (a user saying "I hear voices" gets generic handling today — poor but not harmful). The danger is the ACTIVATION MOMENT: flipping CF-006 live also activates `psychotic_referral.json`. If the skill is incomplete at that moment, the activation causes harm. Task 2 completes the skill content (engineering, safe to land now). CF-006 activation is a SEPARATE, GATED motion that requires: (1) skill fully signed off, (2) CF-006 patterns reviewed and `approved_by` set, (3) full safety test suite green. These three must happen TOGETHER, not incrementally.

---

## Files changed

| File | Task | Change |
|---|---|---|
| `src/sage_poc/rules/data/safety/passive_si_patterns.json` | 1 | Add honest `change_note` documenting FP + recall gap trade-off; no pattern changes (clinical decision) |
| `tests/test_rules_safety.py` | 1 | Add 3 intentionally-failing FP boundary tests + 2 held-out phrases for recall gap; forces clinical decision |
| `src/sage_poc/skills/psychotic_referral.json` | 2 | Add L2/L3/L4 escalation levels + cultural_overrides block |
| `src/sage_poc/rules/data/safety/clinical_flag_patterns.json` | 2 | Add `sign_off_required` annotation; do NOT flip `active` to true yet |
| `src/sage_poc/nodes/skill_executor.py` | 3 | Add `p1_result = result` after LLM-confirmed re-run (one line) |
| `tests/test_skill_executor.py` | 3 | Add regression test for stale-p1_result precedence path |
| `src/sage_poc/audit.py` | 4 | Extract `_build_session_audit_row`; add `write_session_audit_initial` |
| `src/sage_poc/nodes/output_gate.py` | 4 | Use `write_session_audit_initial` for retry-path write; set `banned_opener_violation=True` on fallback |
| `tests/test_output_gate_banned_opener.py` | 4 | Add test for `banned_opener_violation=True` in final state |

---

## Task 1 — SK-EN-002: document the confirmed FP + recall gap, prepare clinical review package

**Context:** The plan at `docs/superpowers/plans/2026-06-04-passive-si-s1-recall-fix.md` specified exactly 8 patterns: `"do better without me"` plus 7 `"relieved if/when i..."` variants. The implementer added 3 extras (`"relieved if i was dead"`, `"relieved if i were dead"`, `"relieved when i'm dead"`) without FP review.

**Confirmed facts (verified by direct engine evaluation):**

- `"relieved if i were dead"` fires on `"She would be relieved if I were dead serious about this"` → **confirmed FP**. Pattern matched at span (13,36).
- `"relieved if i was dead"` has the same FP risk ("dead serious" / "dead tired" idiom constructions).
- `"relieved if i were dead"` is ALSO the pattern catching `"I would be relieved if I were dead"` → **confirmed genuine SI construction**. After removal, this phrase is a MISS against all remaining patterns.
- `"relieved if i was dead"` catches `"I would be relieved if I was dead"` — same recall gap.
- `"Everyone would be relieved when I am dead"` is ALREADY a miss with current patterns.

**This is a clinical trade-off, not an engineering decision.** Removing the 3 extras:
- Kills the "dead serious" FP (a concrete harm: an innocent user gets routed to crisis)
- Creates a recall gap on `"I would be relieved if I were dead"` (a concrete harm: a user in crisis is not caught)

Neither a previous plan's statement of "SK-EN-001 covers it" (false — confirmed by engine.evaluate) nor any engineering rationale resolves this. The clinical lead must make this call with the full picture. Engineering's job here is to document the trade-off precisely and not paper it over.

**What engineering does in this task:**
1. Add the confirmed FP (`"dead serious"` variants) to the FP boundary test — so the FP is formally documented regardless of what the clinical lead decides about the patterns themselves
2. Add the genuine SI construction (`"I would be relieved if I were dead"`) to the held-out corpus test — so both sides of the trade-off are in the test suite
3. Update the `change_note` in SK-EN-002 to state the trade-off honestly (no false safety-net claim)
4. Do NOT remove the patterns yet — removal is a clinical decision and belongs in the sign-off commit

**Process framing:** v1.2.0 is already live on master with `approved_by: null`. The "do not merge until signed off" language from a previous draft was contradictory — we're already past that gate. The honest state is: v1.2.0 is unsigned and live. This task documents the known FPs as tests (making the problem visible and regressions detectable), and the CI guard from `2026-06-04-approved-by-ci-guard.md` will make `approved_by: null` a red build. Clearning the build requires the clinical sign-off. That is the real gate, and it already covers all 17 ungoverned rules, not just this one.

**Files:**
- Modify: `src/sage_poc/rules/data/safety/passive_si_patterns.json`
- Modify: `tests/test_rules_safety.py`

- [ ] **Step 1.1: Add the confirmed FP phrases to the FP boundary test**

Open `tests/test_rules_safety.py`. Find `test_sk_en_002_v1_2_0_fp_boundary` and add the three "dead [adjective]" idiom variants to its parametrize list. These tests will **fail** immediately (the patterns still exist in the JSON — that's correct, documenting the current state before any clinical decision):

```python
@pytest.mark.parametrize("text", [
    # Self-criticism / self-improvement — NOT passive-SI ideation
    "I want to be better without me being so hard on myself",
    # Other-directed relief — about someone else leaving, not speaker's absence
    "Honestly I am relieved that you are finally gone from that toxic job",
    # Practical meeting context
    "Things would run smoother without me in this particular meeting",
    # --- "dead [adjective]" idiom FPs confirmed 2026-06-04: ---
    # 'dead serious' idiom — "dead" means "very", not death.
    # Fires on pattern 'relieved if i were dead' (SK-EN-002 v1.2.0).
    # CLINICAL DECISION REQUIRED: remove pattern (accepts recall gap on
    # 'I would be relieved if I were dead') vs. keep pattern (accepts this FP).
    "She would be relieved if I were dead serious about this",
    "They would be relieved if I was dead serious for once",
    # 'dead tired' variant — same 'relieved when i'm dead' pattern
    "She will be relieved when I'm dead tired and stop talking",
])
def test_sk_en_002_v1_2_0_fp_boundary(text):
    """FP guard for SK-EN-002 v1.2.0 patterns.

    CURRENTLY FAILING for the three 'dead [adjective]' phrases: these are confirmed
    FPs on SK-EN-002 v1.2.0's undocumented extra patterns. The tests are failing
    intentionally — they document the current state and force a clinical decision.

    To clear the three failing tests the clinical lead must choose one of:
      A) Remove the 'relieved if i was/were dead' patterns — accepts recall gap on
         'I would be relieved if I were dead' (no other pattern catches this phrase).
      B) Keep the patterns — accepts the 'dead serious' FP as a documented over-trigger
         (move the 3 phrases to test_sk_en_002_v1_2_0_documented_over_triggers).
    Do NOT clear the test by changing the assert — document the clinical decision first.
    """
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert not crisis_actions, (
        f"FP boundary phrase should not trigger crisis: {text!r}\n"
        f"Got: {result.actions}\n"
        f"CLINICAL DECISION REQUIRED — see test docstring."
    )
```

- [ ] **Step 1.2: Add the genuine SI construction to the held-out corpus test**

Find the `SF1_PASSIVE_MISS_HELD_OUT` dict (or the held-out generalization test) in `tests/test_rules_safety.py`. Add these two phrases so both sides of the trade-off are visible in the test suite:

```python
# In SF1_PASSIVE_MISS_HELD_OUT or the held-out test parametrize list, add:
# Genuine SI construction caught by SK-EN-002 v1.2.0 'relieved if i were dead' pattern.
# WILL BECOME A MISS if that pattern is removed. Clinical lead must acknowledge this.
"I would be relieved if I were dead":      True,   # currently CATCH; miss if pattern removed
"I would be relieved if I was dead":       True,   # currently CATCH; miss if pattern removed
```

If `SF1_PASSIVE_MISS_HELD_OUT` uses a different structure, adapt to match the existing pattern. The key requirement: these phrases are asserted with their CURRENT expected value (`True` = expected to catch), so if the pattern is removed later without updating this test, the test fails — forcing the clinical decision to be made explicitly.

- [ ] **Step 1.3: Run the FP boundary tests to confirm the new ones fail (expected)**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_rules_safety.py::test_sk_en_002_v1_2_0_fp_boundary -v 2>&1 | tail -20
```

Expected: The 3 existing phrases PASS, the 3 new "dead [adjective]" phrases FAIL. This is the correct state — we're documenting confirmed FPs, not fixing them yet.

- [ ] **Step 1.4: Update the change_note in SK-EN-002 to state the trade-off honestly**

Open `src/sage_poc/rules/data/safety/passive_si_patterns.json`. Find the `SK-EN-002` rule. Add/update the `"change_note"` field to state what was found and what decision is pending:

```json
    "change_note": "v1.2.0: Added 10 relieved-family patterns (8 from plan spec + 3 extra 'dead' variants not in spec). FP CONFIRMED 2026-06-04: 'relieved if i were dead' fires on 'dead serious' idiom. RECALL GAP CONFIRMED: this pattern also catches 'I would be relieved if I were dead' — no other active pattern covers this construction. CLINICAL DECISION PENDING: see test_sk_en_002_v1_2_0_fp_boundary for the trade-off. Remove pattern = accept recall gap. Keep pattern = accept FP as documented over-trigger.",
```

- [ ] **Step 1.5: Run the full safety test suite to confirm no regressions (the 3 new FP tests will fail — that's correct)**

```bash
uv run pytest tests/test_rules_safety.py -v 2>&1 | tail -20
```

Expected: All existing tests still pass. 3 new `test_sk_en_002_v1_2_0_fp_boundary` parametrize cases fail — this is intentional and correct. Do not treat these as a build failure to suppress; treat them as a clinical review trigger.

- [ ] **Step 1.6: Commit**

```bash
git add src/sage_poc/rules/data/safety/passive_si_patterns.json tests/test_rules_safety.py
git commit -m "$(cat <<'EOF'
test(safety): document SK-EN-002 FP vs recall gap trade-off for clinical review

Adds 3 failing FP boundary tests for 'dead serious' idiom variants — confirmed to fire
on SK-EN-002 v1.2.0's undocumented 'relieved if i were dead' pattern (added beyond spec).
Adds 2 held-out phrases to document the recall gap: 'I would be relieved if I were dead'
is currently caught by the same pattern; removing it creates a miss on genuine SI.

Both sides of the trade-off are now in the test suite. Tests fail intentionally to force
a clinical decision (remove pattern = accept recall gap; keep = accept FP as over-trigger).
No pattern changes yet — that is a clinical call, not an engineering one.

Updates SK-EN-002 change_note with the honest trade-off statement.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 1.7: Assemble the clinical review package**

The clinical lead needs to see one package, not scattered files. Prepare:

1. The trade-off in plain language: "Pattern `'relieved if i were dead'` catches both genuine SI ('I would be relieved if I were dead') AND the idiom 'dead serious'. Removing it kills the FP but creates a miss on genuine SI. No other pattern catches 'I would be relieved if I were dead'."
2. Run the full re-measurement of all 11 patterns against the held-out corpus:
   ```bash
   uv run pytest tests/test_rules_safety.py -k "sk_en_002 or f_s05_001a or held_out" -v 2>&1
   ```
3. The 3 failing FP boundary tests (they're the visual proof of the FP)
4. The 2 new held-out phrases (they're the visual proof of the recall gap)

Clinical lead resolves by either:
- **Option A (remove pattern):** Remove `"relieved if i was dead"` and `"relieved if i were dead"` from patterns, bump to v1.2.1, set `approved_by`, update the FP boundary tests to PASS, update the held-out phrases to `False` (expected miss). Commit.
- **Option B (accept FP as over-trigger):** Move the 3 "dead serious" phrases from `test_sk_en_002_v1_2_0_fp_boundary` to `test_sk_en_002_v1_2_0_documented_over_triggers` (assert they DO fire), bump version, set `approved_by`. Commit.

The CI guard (from `2026-06-04-approved-by-ci-guard.md`) will keep the build red until `approved_by` is set, regardless of which option is chosen.

---

## Task 2 — Psychotic referral: complete the skill + annotate CF-006 sign-off requirement

**Context:** `psychotic_referral.json` has an incomplete `escalation_matrix` (only L1, missing L2/L3/L4) and empty `cultural_overrides`. CF-006 in `clinical_flag_patterns.json` has `"active": false` pending clinician sign-off. The engineering work (completing the skill content) can land now. CF-006 activation is a clinical governance step that must NOT be done without sign-off.

**Files:**
- Modify: `src/sage_poc/skills/psychotic_referral.json`
- Modify: `src/sage_poc/rules/data/safety/clinical_flag_patterns.json`

- [ ] **Step 2.1: Add L2, L3, L4 to the escalation_matrix in psychotic_referral.json**

The current `escalation_matrix` in `src/sage_poc/skills/psychotic_referral.json`:

```json
  "escalation_matrix": {
    "L1": "If the user indicates any risk to themselves or others, stop the referral and respond with the crisis line immediately: emergency services 999 or MoHAP Counselling Line 800 46342 (free, 24/7). Do not continue the referral step."
  }
```

Replace with:

```json
  "escalation_matrix": {
    "L1": "If the user indicates any risk to themselves or others, stop the referral and respond with the crisis line immediately: emergency services 999 or MoHAP Counselling Line 800 46342 (free, 24/7). Do not continue the referral step.",
    "L2": "If the user discloses command hallucinations (voices telling them to harm themselves or others), treat as active crisis: route to crisis_response. Flag for clinician review regardless of whether the user accepts the referral.",
    "L3": "If the user becomes distressed, agitated, or frightened during the referral step, de-escalate using calm, brief, non-diagnostic language. Do not probe further. Provide 800 46342 and end the interaction warmly. Do not attempt to continue the referral.",
    "L4": "If the user explicitly requests to speak to a human or expresses that they cannot wait, respond: 'Please call 800 46342 now. They are available 24 hours a day and can connect you to the right support immediately.' Do not substitute any other response."
  }
```

- [ ] **Step 2.2: Add cultural_overrides to psychotic_referral.json**

The current `cultural_overrides` in `src/sage_poc/skills/psychotic_referral.json`:

```json
  "cultural_overrides": {},
```

Replace with:

```json
  "cultural_overrides": {
    "stigma_language": "In Gulf Arab culture, psychotic experiences carry profound stigma often linked to family honour. Never use clinical terms (psychosis, schizophrenia, hallucinations, delusions) or terms associated with 'madness' (جنون). Frame as 'something important that needs specialist attention' not as an illness label.",
    "jinn_and_evil_eye": "Some users or their families may interpret these experiences through a religious or supernatural lens (evil eye, jinn possession). Do not contradict or challenge this framing. Acknowledge respectfully and redirect to professional support: 'Whatever the source of this, a mental health specialist can help you understand and navigate it.'",
    "family_involvement": "The user may be reluctant to seek help without family knowledge, or may fear family reaction. Do not push for independent action. Validate the complexity: 'This is something worth getting support for, in whatever way feels right for you and your family.' The referral line 800 46342 can advise on family involvement.",
    "non_alarming_tone": "The referral must not communicate alarm, urgency, or severity in a way that increases distress or confirms the user's worst fears. Use calm, matter-of-fact language that normalises seeking specialist input without catastrophising."
  },
```

- [ ] **Step 2.3: Verify the skill loads cleanly against the schema**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_skill_schema.py -k "psychotic_referral" -v 2>&1 | tail -15
```

If no test exists for psychotic_referral, run the full schema test:

```bash
uv run pytest tests/test_skill_schema.py -v 2>&1 | tail -10
```

Expected: All schema tests pass. If any fail, the JSON is malformed — check trailing commas and quote escaping.

- [ ] **Step 2.4: Add a sign-off annotation to CF-006 in clinical_flag_patterns.json**

Open `src/sage_poc/rules/data/safety/clinical_flag_patterns.json`. In the CF-006 rule block (currently at the end of the file), update the `description` field to document the sign-off requirement explicitly:

Current:
```json
      "description": "Psychotic symptom disclosure — auditory/visual hallucinations, paranoid ideation. INACTIVE pending clinician sign-off (schema change: 6th clinical flag). Known limitation: keyword-only detection; MARBERT/semantic tier deferred.",
```

Replace with:
```json
      "description": "Psychotic symptom disclosure — auditory/visual hallucinations, paranoid ideation. INACTIVE pending clinician sign-off. To activate: (1) clinician reviews CF-006 patterns and sets approved_by, (2) set active=true, (3) run full safety test suite. Known limitation: keyword-only detection; MARBERT/semantic tier deferred.",
      "activation_checklist": ["clinician_reviews_cf006_patterns", "approved_by_set", "active_set_true", "full_test_suite_passes"],
```

Do **not** change `"active": false`. The rule must remain inactive until the checklist is complete.

- [ ] **Step 2.5: Run the full skill and schema test suite to confirm no regressions**

```bash
uv run pytest tests/test_skill_schema.py tests/test_skill_ids.py tests/test_rules_schemas.py -v 2>&1 | tail -15
```

Expected: All pass.

- [ ] **Step 2.6: Commit**

```bash
git add src/sage_poc/skills/psychotic_referral.json src/sage_poc/rules/data/safety/clinical_flag_patterns.json
git commit -m "$(cat <<'EOF'
fix(skills): complete psychotic_referral escalation_matrix + cultural_overrides

Adds L2 (command hallucination crisis route), L3 (distress de-escalation), L4 (human
handoff) to escalation_matrix. Adds cultural_overrides covering Gulf stigma framing,
jinn/evil-eye respectful redirect, family involvement sensitivity, and non-alarming tone.
Annotates CF-006 with activation checklist; CF-006 remains inactive pending sign-off.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 2.7: Clinical sign-off gate — CF-006 activation (BLOCKS CF-006 ACTIVATION, NOT MERGE)**

The PR containing Task 2 can merge. But CF-006 must not be activated until:
1. A named clinician reviews the CF-006 keyword patterns in `clinical_flag_patterns.json`
2. `"approved_by"` is set to `"<clinician-name>_<date>"`
3. `"active"` is flipped to `true`
4. The full safety test suite passes (run: `uv run pytest tests/test_rules_safety.py tests/test_safety_node_integration.py -v`)
5. A dedicated commit records this activation with a clinical review reference

---

## Task 3 — skill_executor: fix stale p1_result in precedence resolver

**Context:** In `skill_executor.py`, when Phase 1 returns `_criteria_blocked=True` and the LLM evaluator confirms `criteria_met=True`, the code updates `result` and `_p1_action` (lines 430-433) but does NOT update `p1_result` (assigned at line 405). When Phase 2 resistance scoring subsequently fires a non-safety hold, the precedence resolver at lines 455-461 restores `p1_result` — which is the original `action='stay'`, not the LLM-confirmed `action='advance'`. This silently stalls users who have genuinely completed a step when resistance is simultaneously elevated.

**Files:**
- Modify: `src/sage_poc/nodes/skill_executor.py:432`
- Modify: `tests/test_skill_executor.py`

- [ ] **Step 3.1: Write the failing regression test**

Add this test to `tests/test_skill_executor.py`, after the existing `test_post_crisis_check_in_llm_yes_advances_step` test (around line 609):

```python
@pytest.mark.asyncio
async def test_llm_criteria_advance_beats_phase2_resistance_hold():
    """Regression: LLM-confirmed advance must beat a non-safety Phase 2 resistance hold.

    Scenario: Phase 1 returns _criteria_blocked (heuristic blocks). LLM evaluator
    confirms criteria_met=True, so Phase 1 re-runs and returns action='advance'.
    Phase 2 resistance scoring subsequently fires a non-safety hold (action='stay').
    The precedence resolver must restore the LLM-confirmed advance, not the original
    criteria-blocked stay.

    Bug: p1_result was never updated after the LLM-confirmed re-run, so the resolver
    restored action='stay' instead of the confirmed action='advance'.
    Fix: add 'p1_result = result' immediately after the LLM-confirmed re-run.
    """
    from sage_poc.nodes.skill_executor import skill_executor_node

    state = {
        "active_skill_id":   "post_crisis_check_in",
        "active_step_id":    "acknowledge_and_check",
        "message_en":        "ok",   # single word — heuristic blocks Phase 1
        "emotional_intensity": 6,    # above advance threshold (<=4) — no Phase 1 rule fires
        "engagement":          7,
        "new_clinical_flags_turn": [],
        "resistance_history":  [],
        "engagement_trajectory": [],
        "s7_result":           None,
        "therapeutic_profile": {},
        "path":                [],
        "crisis_state":        "monitoring",
    }

    call_count = 0

    def mock_evaluate_step_policy(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Phase 1 (no resistance, no criteria_met): heuristic blocks
            return {"action": "stay", "_criteria_blocked": True}
        elif call_count == 2:
            # Phase 1 re-run after LLM confirms criteria_met=True
            return {"action": "advance", "next_step_id": "bridge_or_close"}
        else:
            # Phase 2 (resistance scoring): non-safety hold
            return {"action": "stay"}

    with patch(
        "sage_poc.nodes.skill_executor.evaluate_step_policy",
        side_effect=mock_evaluate_step_policy,
    ), patch(
        "sage_poc.nodes.criteria_eval._call_llm",
        new_callable=AsyncMock,
        return_value="yes",          # LLM confirms criteria met
    ), patch(
        "sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
        new_callable=AsyncMock,
        return_value=8,              # High resistance — Phase 2 fires
    ):
        result = await skill_executor_node(state)

    assert result.get("active_step_id") == "bridge_or_close", (
        "LLM-confirmed advance must beat Phase 2 non-safety hold.\n"
        f"Got active_step_id={result.get('active_step_id')!r}.\n"
        "Fix: add 'p1_result = result' after the LLM-confirmed re-run in skill_executor.py."
    )
```

- [ ] **Step 3.2: Run the new test to confirm it fails (before the fix)**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_skill_executor.py::test_llm_criteria_advance_beats_phase2_resistance_hold -v 2>&1 | tail -15
```

Expected: FAILED — `active_step_id` is `"acknowledge_and_check"` (step did not advance).

- [ ] **Step 3.3: Apply the one-line fix in skill_executor.py**

Open `src/sage_poc/nodes/skill_executor.py`. Find lines 429-433 (the LLM-confirmed re-run block):

```python
            if llm_criteria_met:
                result = _clean_policy_result(evaluate_step_policy(
                    **_base_policy_kwargs, resistance_score=None, criteria_met=True,
                ))
                _p1_action = result.get("action")  # update after LLM-confirmed advance
```

Change to:

```python
            if llm_criteria_met:
                result = _clean_policy_result(evaluate_step_policy(
                    **_base_policy_kwargs, resistance_score=None, criteria_met=True,
                ))
                _p1_action = result.get("action")  # update after LLM-confirmed advance
                p1_result = result  # keep p1_result in sync so precedence resolver restores correct action
```

- [ ] **Step 3.4: Run the new test — must now pass**

```bash
uv run pytest tests/test_skill_executor.py::test_llm_criteria_advance_beats_phase2_resistance_hold -v 2>&1 | tail -10
```

Expected: PASSED.

- [ ] **Step 3.5: Run the full skill_executor test suite to confirm no regressions**

```bash
uv run pytest tests/test_skill_executor.py -v 2>&1 | tail -15
```

Expected: All existing tests pass (the new test also passes). Confirm `test_post_crisis_check_in_llm_yes_advances_step` and `test_post_crisis_check_in_uses_llm_evaluator_when_heuristic_fails` both still pass — these are the nearest neighbours.

- [ ] **Step 3.6: Commit**

```bash
git add src/sage_poc/nodes/skill_executor.py tests/test_skill_executor.py
git commit -m "$(cat <<'EOF'
fix(skill_executor): update p1_result after LLM criteria confirmation

The precedence resolver at lines 455-461 restores p1_result when Phase 1 (criteria-met)
should beat Phase 2 (resistance hold). p1_result was not updated after the LLM-confirmed
re-run, so the resolver restored action='stay' instead of the confirmed action='advance'.

Fix: add 'p1_result = result' after the LLM-confirmed re-run. Affects all 11
_LLM_CRITERIA_SKILLS when resistance is simultaneously elevated on the same turn.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4 — audit.py + output_gate: fix 409 race condition and banned_opener_violation always-False

**Context:** Two bugs in the same area, one of which requires a deliberate PDPL schema decision.

**PDPL schema decision (document this before touching code):**

The question: should one turn produce ONE audit row (updated to reflect final state) or MULTIPLE rows (one per intermediate event)?

**Decision: one row per turn, updated to reflect final state.** Reasoning:
- The `node_path` array already accumulates all markers in order (`["...", "output_gate_banned_opener_retry", "output_gate_fallback_substituted"]`). A PDPL reviewer querying for `"output_gate_fallback_substituted"` in node_path finds the row. No information is lost.
- Multiple rows per turn would require dropping the unique constraint on `(session_id, turn_number)` — a schema migration — and would complicate every downstream query that assumes one row = one turn.
- "Last write wins" (merge-duplicates) is the correct semantic: the final state of a turn is the authoritative record.

**Why the current code fails:** The retry early-return write (task 2, `path=[..., "retry_marker"]`) is created as an `asyncio.create_task` BEFORE the final write (task 4, `path=[..., "retry_marker", "fallback_marker"]`). Both use `merge-duplicates`. Whichever commits LAST wins. If task 2 commits last — which happens in tests with a mocked LLM because no real I/O yields the event loop between task creation — it overwrites task 4's `node_path` with the shorter path, stripping the fallback marker.

**The fix:** Task 2 (intermediate/retry write) uses `resolution=ignore-duplicates`. This makes the fix sound regardless of commit order:
- If task 4 commits first (final state is already in the row): task 2 is a silent no-op. ✓
- If task 2 commits first (row doesn't exist yet): task 2 inserts the intermediate state, then task 4 upserts over it with the complete final path. ✓

The `ignore-duplicates`/`merge-duplicates` split is the robustness guarantee, not scheduling order. Do not rely on "the LLM call yields the event loop" — that assumption breaks when the LLM is stubbed, cached, or replaced. The test must assert the final `node_path` CONTAINS the fallback marker, not that a specific commit order was observed.

**Bug B:** `banned_opener_violation` is initialized to `False` at line 228 and never set to `True`, so the audit log always records zero violations even when the fallback is substituted.

**Files:**
- Modify: `src/sage_poc/audit.py`
- Modify: `src/sage_poc/nodes/output_gate.py`
- Modify: `tests/test_output_gate_banned_opener.py`

- [ ] **Step 4.1: Write a failing unit test for banned_opener_violation always-False**

Add to `tests/test_output_gate_banned_opener.py`. First check what's already there:

```bash
grep -n "banned_opener_violation\|fallback_substituted\|fallback_used" tests/test_output_gate_banned_opener.py | head -20
```

Add this test at the end of the file:

```python
@pytest.mark.asyncio
async def test_banned_opener_violation_true_when_fallback_substituted():
    """When fallback is substituted on retry-exhausted banned opener,
    banned_opener_violation must be True in the returned state dict.

    Bug: banned_opener_violation was initialised to False at line 228 and
    never set to True, so the audit log always recorded zero violations.
    """
    from sage_poc.nodes.output_gate import output_gate_node, _VETTED_FALLBACK_RESPONSE
    from tests.conftest import make_mock_llm

    # Second banned opener response (retry already exhausted)
    second_banned = "That sounds really difficult. Have you tried something different?"

    state = _make_base_state(
        response_en=second_banned,
        banned_opener_retry_count=1,   # retry already used
    )

    result = await output_gate_node(state)

    assert result["banned_opener_violation"] is True, (
        "banned_opener_violation must be True when fallback is substituted. "
        f"Got: {result['banned_opener_violation']}"
    )
    assert result["banned_opener_fallback_used"] is True
    assert result["response"] == _VETTED_FALLBACK_RESPONSE
```

Note: `_make_base_state` is a helper that already exists in the test file. Check its signature with:
```bash
grep -n "_make_base_state\|def make_base" tests/test_output_gate_banned_opener.py | head -5
```

If the helper takes different parameters, adjust the call to match the existing pattern.

- [ ] **Step 4.2: Run the new test to confirm it fails**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_output_gate_banned_opener.py::test_banned_opener_violation_true_when_fallback_substituted -v 2>&1 | tail -15
```

Expected: FAILED — `banned_opener_violation` is `False` when it should be `True`.

- [ ] **Step 4.3: Refactor audit.py to extract _build_session_audit_row and add write_session_audit_initial**

Open `src/sage_poc/audit.py`. Replace the entire `write_session_audit` function with:

```python
def _build_session_audit_row(state: "SageState") -> dict:
    return {
        "session_id":             state.get("session_id", ""),
        "turn_number":            state.get("turn_number", 0),
        "node_path":              state.get("path") or [],
        "primary_intent":         state.get("primary_intent"),
        "secondary_intent":       state.get("secondary_intent"),
        "intent_confidence":      state.get("intent_confidence"),
        "active_skill_id":        state.get("active_skill_id") or None,
        "active_step_id":         state.get("active_step_id") or None,
        "skill_match_method":     state.get("skill_match_method") or None,
        "knowledge_source":       state.get("knowledge_source") or None,
        "knowledge_passage_ids":  [p.get("source_id", "") for p in state.get("knowledge_passages") or []],
        "knowledge_abstain":      bool(state.get("knowledge_abstain", False)),
        "crisis_state":           state.get("crisis_state"),
        "crisis_flags":           state.get("crisis_flags") or [],
        "clinical_flags":         state.get("clinical_flags") or [],
        "engagement":             state.get("engagement"),
        "emotional_intensity":    state.get("emotional_intensity"),
        "model_version":          state.get("model_version"),
        "latency_ms":             state.get("latency_ms"),
        "user_id":                state.get("user_id") or None,
        "re_escalation_within_monitoring": state.get("re_escalation_within_monitoring"),
    }


async def write_session_audit(state: "SageState") -> None:
    """Write or update a session audit row. Uses merge-duplicates (last write wins).

    Called for the final state of each output_gate pass and for the fallback
    substitution path, where we want the complete final state to overwrite any
    earlier intermediate write.
    """
    if not _URL or not _KEY:
        return
    row = _build_session_audit_row(state)
    try:
        upsert_headers = {**_HEADERS, "Prefer": "resolution=merge-duplicates"}
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{_URL}/rest/v1/session_audit",
                headers=upsert_headers,
                json=row,
            )
            r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("session_audit write failed: %s — body: %s", exc, exc.response.text)
    except Exception as exc:
        logger.error("session_audit write failed: %s", exc)


async def write_session_audit_initial(state: "SageState") -> None:
    """Write a session audit row only if the row does not already exist.

    Uses ignore-duplicates so this write is silently dropped if a later
    write_session_audit call has already committed the row. Used for the
    retry-detection intermediate write so that the final write (which carries
    the complete path including fallback markers) always wins the race.
    """
    if not _URL or not _KEY:
        return
    row = _build_session_audit_row(state)
    try:
        ignore_headers = {**_HEADERS, "Prefer": "resolution=ignore-duplicates"}
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{_URL}/rest/v1/session_audit",
                headers=ignore_headers,
                json=row,
            )
            r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("session_audit initial write failed: %s — body: %s", exc, exc.response.text)
    except Exception as exc:
        logger.error("session_audit initial write failed: %s", exc)
```

Also update the import at the top of the file — the type hint on `state` parameter needs the SageState type. Add a `TYPE_CHECKING` guard if it's not already imported:

```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sage_poc.state import SageState
```

If `SageState` is already imported directly (not under TYPE_CHECKING), leave it as is.

- [ ] **Step 4.4: Update output_gate.py — use write_session_audit_initial for retry write, set banned_opener_violation=True on fallback**

Open `src/sage_poc/nodes/output_gate.py`. Make three changes:

**Change 1** — Update the import at the top of the file:

Current:
```python
from sage_poc.audit import write_session_audit, write_identity_substitution_audit
```

Replace with:
```python
from sage_poc.audit import write_session_audit, write_session_audit_initial, write_identity_substitution_audit
```

**Change 2** — In the retry early-return block (around line 262), change `write_session_audit` to `write_session_audit_initial`:

Current:
```python
                if session_id:
                    _retry_audit = asyncio.create_task(
                        write_session_audit({**state, "path": retry_path, "gate_path": gate_path or "standard"})
                    )
                    _retry_audit.add_done_callback(
                        lambda t: _log.warning("[output_gate] retry audit error: %s", t.exception())
                        if not t.cancelled() and t.exception() else None
                    )
```

Replace with:
```python
                if session_id:
                    _retry_audit = asyncio.create_task(
                        write_session_audit_initial({**state, "path": retry_path, "gate_path": gate_path or "standard"})
                    )
                    _retry_audit.add_done_callback(
                        lambda t: _log.warning("[output_gate] retry audit error: %s", t.exception())
                        if not t.cancelled() and t.exception() else None
                    )
```

**Change 3** — In the fallback substitution block (around line 286-288), add `banned_opener_violation = True`:

Current:
```python
                response_en = _VETTED_FALLBACK_RESPONSE
                banned_opener_fallback_used = True
                path = path + ["output_gate_fallback_substituted"]
```

Replace with:
```python
                response_en = _VETTED_FALLBACK_RESPONSE
                banned_opener_violation = True
                banned_opener_fallback_used = True
                path = path + ["output_gate_fallback_substituted"]
```

- [ ] **Step 4.5: Run the new test — must now pass**

```bash
uv run pytest tests/test_output_gate_banned_opener.py::test_banned_opener_violation_true_when_fallback_substituted -v 2>&1 | tail -10
```

Expected: PASSED — `banned_opener_violation` is now `True`.

- [ ] **Step 4.6: Run the full banned opener test suite**

```bash
uv run pytest tests/test_output_gate_banned_opener.py -v 2>&1 | tail -15
```

Expected: All pass. Confirm all existing C-1/C-2/C-3/C-4 tests still pass (they test the retry and fallback paths).

- [ ] **Step 4.7: Run the output gate loop mechanics test**

```bash
uv run pytest tests/test_output_gate_loop_mechanics.py -v 2>&1 | tail -10
```

Expected: All pass.

- [ ] **Step 4.8: Run the retry path integration test (requires SUPABASE_URL)**

This test hits real Supabase — skip if credentials not available in your current environment:

```bash
uv run pytest tests/test_retry_path_integration.py -m integration -v 2>&1 | tail -20
```

If `SUPABASE_URL` is not set, this skips gracefully. If it is set, expected: `test_fallback_substitution_audit_row_written` now passes (the fallback marker persists in the audit row).

- [ ] **Step 4.9: Commit**

```bash
git add src/sage_poc/audit.py src/sage_poc/nodes/output_gate.py tests/test_output_gate_banned_opener.py
git commit -m "$(cat <<'EOF'
fix(audit): prevent retry-path 409 race; fix banned_opener_violation always-False

audit.py: Extract _build_session_audit_row helper. Add write_session_audit_initial
(ignore-duplicates) for intermediate writes so a later write_session_audit (merge-
duplicates) always wins the race. Prevents the early-return retry write from
overwriting the fallback marker when both tasks queue simultaneously in tests.

output_gate.py: Use write_session_audit_initial for retry early-return write.
Set banned_opener_violation=True on fallback substitution so the audit log
correctly records violation frequency (was always False).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Final verification

After all four tasks are committed, run the combined suite:

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_rules_safety.py tests/test_skill_executor.py tests/test_output_gate_banned_opener.py tests/test_output_gate_loop_mechanics.py tests/test_skill_schema.py -v 2>&1 | tail -20
```

Expected: All pass, no new failures.

**Merge checklist:**
- [ ] Task 1: `SK-EN-002 approved_by` field updated by clinical lead
- [ ] Tasks 2, 3, 4: can merge without waiting for clinical sign-off
- [ ] Task 2 CF-006 activation: separate PR, separate clinical sign-off ceremony
