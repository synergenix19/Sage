# Skill Routing Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 21 dead step_policy signals, harden the signals contract to raise RuntimeError at startup, add Arabic Tier 1 keyword routing stopgap, fix language-aware example selection in skill_executor, and fix 9 content bugs — all gated by clinical safety review.

**Architecture:** All changes are confined to Node 4 (`skill_select.py`), Node 5 (`skill_executor.py`), skill JSON files under `src/sage_poc/skills/`, `safety/crisis_phrases.json`, and `tests/test_corpus_integrity.py`. No schema changes, no new nodes, no DB migrations.

**CI baseline:** `test_dead_step_policy_signal_count_is_pinned` is currently **PASSING** at exactly 21.

---

## Gated Execution Order

| Batch | Criteria | Tasks |
|-------|----------|-------|
| **Batch 1 — GREEN** | Land immediately, no clinical review | 1, 2, 3, 4a, 5a, 7 (deletions only), 8, 9, 10, 11, 12, 13, 14, 15 |
| **Batch 2 — AMBER** | Clinical sign-off required before merging | 5b, 6, 7 (contraindication strings), 4b |
| **RED pre-checks** | Must resolve before Batch 1 can land in full | psychotic_referral safety regression on `feat/arabic-kb-skills-expansion`; confirm crisis line number |

### What "GREEN" means here

The dead-signal deletions are safe because those rules were already silently inert (providing zero runtime protection). Deleting them does not remove any working safety mechanism — it removes the false impression of one. Task 8's RuntimeError gate then prevents this class from recurring.

### What "AMBER" means here

The contraindication strings in Task 7 (DV, trauma, dissociation, SI, OCD) are new clinical content being authored outside the clinical draft→review→approve workflow (v7 §5.5). The structure (move-to-contraindication) is correct; the wording is clinician content. **The Node 1 verification below must also complete before Batch 2 ships.**

### Batch 2 Node 1 pre-check (do before any AMBER contraindication merges)

For each safety-critical contraindication being added, the deterministic Node 1 clinical-flag wiring must exist FIRST. Contraindications are the secondary (LLM-discretionary) layer, not the primary safety mechanism:

| Task | Node 1 clinical flag to verify |
|------|-------------------------------|
| 7a, 7h (DV) | `domestic_situation` flag in `clinical_flag_patterns.json` |
| 7c, 7d (trauma) | `trauma_indicator` flag in `clinical_flag_patterns.json` |
| 7i, 7n (dissociation) | **No deterministic backstop.** Dissociation is not in the v7 §5.1 clinical flag set (the five flags are substance, trauma, eating, domestic, medication). The contraindication is LLM-discretionary only — parity with DV/trauma does NOT exist. Mark 7i/7n as requiring explicit clinical sign-off that LLM-only protection is acceptable for POC. Log "dissociation detection at Node 1 (6th clinical flag)" as a post-Gitex backlog item. |
| 7l (SI during psychoed) | Already handled by `safety_check` / `crisis_phrases.json` |
| 7j (pain/injury in PMR) | `physical_condition_mention` or equivalent flag |

---

## Branch Status (read before starting)

| Branch | Ahead of master | Conflict | Action |
|--------|-----------------|----------|--------|
| `feat/crisis-phrases-corpus-expansion` | 4 commits | None | Merge first |
| `feat/arabic-kb-skills-expansion` | 9 commits | **SAFETY REGRESSION** — removed psychotic_referral auto-select from `skill_select.py`. No other node provides this route. Must restore before merging | Do NOT merge until psychotic_referral block is restored |
| `test/cultural-overrides-condensation` | 1 commit | Task 10 idempotent | Can merge before Task 10 |
| `feat/clinical-flag-lifecycle` | 0 (behind master) | None | Clean |

---

## Dead Signal Count Progression

| After task | Count | CI state | Note |
|-----------|-------|----------|------|
| Baseline | 21 | PASS | |
| Task 3 (clarity) | 20 | PASS | |
| Task 4a (crisis_financial) | 19 | PASS | |
| Task 5a (mood_score + 9 keywords) | 18 | PASS | 5a deletes BOTH keywords AND mood_score rule |
| Task 6 deletion (obsessive_theme) | 17 | PASS | |
| Task 7 all deletions (17 signals) | 0 | PASS (empty set) | 17 + Task 6 = 18 total bulk deletions |
| Task 8 | 0 | Test replaced | RuntimeError gate now live |
| Task 5b (Batch 2) | 0 | PASS | Adds new emotional_intensity <= 3 rule (no signal increase — it's a live signal) |

---

# BATCH 1 — GREEN

**Audit trail reminder (verify during execution):** Tasks 9 (Arabic Tier 1), 10 (language-aware example selection), and 5a (keyword set changes) all change runtime routing behaviour. Before each lands, confirm that Node 8's audit log still captures `skill_id`, `step_id`, `skill_match_method`, and `detected_language` on the affected paths. These fields are the post-Gitex traceability record for every behavioural change shipped here. This is a verification step, not a code change — unless the fields are found to be absent, in which that is an independent bug.

---

## Task 1: Fix post_crisis_check_in L1 exit

**Files:** `src/sage_poc/skills/post_crisis_check_in.json`, `tests/test_corpus_integrity.py`

Current `L1`: `"Exit skill gracefully if user explicitly requests to stop"`. Missing: crisis line, door-open, anti-assumption guard.

**Pre-check:** Verify the crisis line number (800 46342) against the canonical crisis-resources source and the clinical lead before committing. A single source of truth for this number should exist — if it does not, create `src/sage_poc/config.py::CRISIS_LINE_UAE = "800 46342"` and reference it from skill prose generation rather than hardcoding into the JSON string.

- [ ] **Step 1: Write a failing test**

Add to `tests/test_corpus_integrity.py`:

```python
def test_post_crisis_check_in_l1_includes_crisis_line():
    import json, pathlib
    skill = json.loads(
        (pathlib.Path(__file__).parent.parent / "src/sage_poc/skills/post_crisis_check_in.json")
        .read_text()
    )
    l1 = skill["escalation_matrix"]["L1"]
    assert "800 46342" in l1, f"post_crisis_check_in L1 missing crisis line. Current: {l1!r}"
    assert any(w in l1.lower() for w in ("door", "return", "come back", "whenever")), \
        "L1 must leave the door open explicitly."
```

- [ ] **Step 2: Run to confirm fails**

```bash
cd sage-poc && pytest tests/test_corpus_integrity.py::test_post_crisis_check_in_l1_includes_crisis_line -v
```

- [ ] **Step 3: Update `escalation_matrix.L1`**

Replace:
```json
"L1": "Exit skill gracefully if user explicitly requests to stop"
```
with:
```json
"L1": "Exit the skill immediately and warmly when the user asks to stop. Do all three without exception: (1) mention the crisis support line before closing, for example: 'If things ever feel too heavy, you can call or WhatsApp 800 46342, it is free and available any time.' (2) Leave the door open explicitly, for example: 'You can come back whenever you are ready, I will be here.' (3) Do NOT assume they are better because they asked to stop. A stop request is not a signal of resolution."
```

- [ ] **Step 4: Run test — expect PASSED**

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/skills/post_crisis_check_in.json tests/test_corpus_integrity.py
git commit -m "fix(post_crisis): L1 exit now includes crisis line, door-open, anti-assumption guard"
```

---

## Task 2: Remove authoring meta-note from stop_technique cultural_overrides

**Files:** `src/sage_poc/skills/stop_technique.json`, `tests/test_corpus_integrity.py`

`consult_before_examples` is a governance reminder being injected verbatim into the live LLM system prompt via `build_cultural_override_block`.

- [ ] **Step 1: Write a failing test**

```python
def test_no_authoring_notes_in_cultural_overrides():
    import json, pathlib
    FORBIDDEN = {"consult_before_examples", "review_required", "authoring_note", "todo"}
    skills_dir = pathlib.Path(__file__).parent.parent / "src/sage_poc/skills"
    violations = []
    for path in sorted(skills_dir.glob("*.json")):
        co = json.loads(path.read_text()).get("cultural_overrides", {})
        if isinstance(co, dict):
            bad = FORBIDDEN & set(co.keys())
            if bad:
                violations.append((path.stem, sorted(bad)))
    assert not violations, f"Authoring keys in live LLM cultural_overrides: {violations}"
```

- [ ] **Step 2: Run — expect FAILED: `[('stop_technique', ['consult_before_examples'])]`**

- [ ] **Step 3: Delete `consult_before_examples` from `stop_technique.json` `cultural_overrides`**

- [ ] **Step 4: Run — expect PASSED. Commit**

```bash
git add src/sage_poc/skills/stop_technique.json tests/test_corpus_integrity.py
git commit -m "fix(stop_technique): remove consult_before_examples from cultural_overrides (live LLM prompt)"
```

---

## Task 3: Clean up box_breathing dead signal and wrong keyword

**Files:** `src/sage_poc/skills/box_breathing.json`, `tests/test_corpus_integrity.py`

Confirmed in source: `clarity` dead signal rule (not in `_KNOWN_STEP_POLICY_SIGNALS`) and `"4-7-8 breathing"` incorrectly added in the 612ddbc inhale+hold merge. CI currently passes at 21.

- [ ] **Step 1: Delete the `clarity` rule from `step_policy`**

Remove the rule with `"signal": "clarity"`. Remaining rules: `emotional_intensity`, `resistance`, `engagement`, `user_stop_request`.

- [ ] **Step 2: Remove `"4-7-8 breathing"` from `target_presentations`**

- [ ] **Step 3: Remove `("box_breathing", "clarity")` from `_KNOWN_DEAD_SIGNALS` in `tests/test_corpus_integrity.py`**

- [ ] **Step 4: Verify count = 20**

```bash
cd sage-poc && python3 -c "
from sage_poc.nodes.skill_executor import _get_dead_step_policy_signals
print('Total dead:', len(_get_dead_step_policy_signals()))
"
pytest tests/test_corpus_integrity.py::test_dead_step_policy_signal_count_is_pinned -v
```

Expected: total = 20, test PASSED.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/skills/box_breathing.json tests/test_corpus_integrity.py
git commit -m "fix(box_breathing): remove clarity dead signal and 4-7-8 routing error (dead count 21->20)"
```

---

## Task 4a: Delete financial_anxiety dead signal only

**Files:** `src/sage_poc/skills/financial_anxiety.json`, `tests/test_corpus_integrity.py`

**Scope:** Deletion only. The `crisis_phrases.json` additions (Task 4b) are in Batch 2 pending clinical review of the exact strings against C-SSRS/TD3 and SF-6 false-positive criteria.

- [ ] **Step 1: Write a failing test**

```python
def test_financial_anxiety_no_crisis_detection_in_step_policy():
    import json, pathlib
    skill = json.loads(
        (pathlib.Path(__file__).parent.parent / "src/sage_poc/skills/financial_anxiety.json")
        .read_text()
    )
    CRISIS_SIGNALS = {"crisis_financial_hopelessness_detected", "crisis_detected", "si_detected"}
    violations = [
        rule["condition"]["signal"]
        for rule in skill.get("step_policy", [])
        if rule.get("condition", {}).get("signal") in CRISIS_SIGNALS
    ]
    assert not violations, f"financial_anxiety step_policy has crisis signals {violations} — belongs in Node 1."
```

- [ ] **Step 2: Run — expect FAILED**

- [ ] **Step 3: Delete the `crisis_financial_hopelessness_detected` rule from `financial_anxiety.json`**

The `emotional_intensity > 7 → validate_only` rule stays (it covers pacing, not crisis detection).

- [ ] **Step 4: Remove `("financial_anxiety", "crisis_financial_hopelessness_detected")` from `_KNOWN_DEAD_SIGNALS`**

- [ ] **Step 5: Run — both tests PASSED. Dead count = 19. Commit**

```bash
git add src/sage_poc/skills/financial_anxiety.json tests/test_corpus_integrity.py
git commit -m "fix(financial_anxiety): delete dead crisis-detection rule from step_policy (dead count 20->19)

Deletion only. crisis_financial_hopelessness_detected was silently inert.
Financial-hopelessness phrases for Node 1 (crisis_phrases.json) pending clinical
review against C-SSRS/TD3 and SF-6 false-positive criteria — see Task 4b."
```

---

## Task 5a: Remove mood_check_in overbroad keywords only

**Files:** `src/sage_poc/skills/mood_check_in.json`, `tests/test_corpus_integrity.py`

**Scope:** Remove the 9 overbroad keywords AND delete the `mood_score` dead signal rule in the same task. Both are safe to ship without clinical review — the keywords were causing false routing, and the `mood_score` rule was silently inert (providing zero protection). Task 5b in Batch 2 adds a NEW `emotional_intensity <= 3` replacement rule after clinical confirmation — the two-construct substitution (user's 1–10 self-report vs. system distress signal) is the part that needs clinical approval. Between batches, there is no "hold on low mood" rule at `score_mood` — which accurately describes the pre-existing runtime state anyway.

- [ ] **Step 1: Write two failing tests**

```python
def test_mood_check_in_no_overbroad_keywords():
    import json, pathlib
    skill = json.loads(
        (pathlib.Path(__file__).parent.parent / "src/sage_poc/skills/mood_check_in.json")
        .read_text()
    )
    OVERBROAD = {
        "feeling low", "feeling down", "not feeling great", "not doing well",
        "having a bad day", "bad day", "rough day", "rough week", "struggling today",
    }
    found = OVERBROAD & set(skill.get("target_presentations", []))
    assert not found, f"mood_check_in has overbroad keywords forcing 1-10 rating protocol: {found}"


def test_mood_check_in_no_dead_mood_score_rule():
    import json, pathlib
    skill = json.loads(
        (pathlib.Path(__file__).parent.parent / "src/sage_poc/skills/mood_check_in.json")
        .read_text()
    )
    signals = [r["condition"]["signal"] for r in skill.get("step_policy", [])]
    assert "mood_score" not in signals, (
        "mood_score is a dead signal (never resolved at runtime). Rule must be deleted. "
        "Add an emotional_intensity <= 3 replacement in Task 5b after clinical confirmation."
    )
```

- [ ] **Step 2: Run — expect both FAILED**

- [ ] **Step 3: Remove these 9 strings from `target_presentations`**

```
"feeling low", "feeling down", "not feeling great", "not doing well",
"having a bad day", "bad day", "rough day", "rough week", "struggling today"
```

- [ ] **Step 4: Delete the `mood_score` rule from `step_policy`**

Find the rule whose `condition.signal` is `"mood_score"` and delete it from the `step_policy` array.

- [ ] **Step 5: Remove `("mood_check_in", "mood_score")` from `_KNOWN_DEAD_SIGNALS` in `tests/test_corpus_integrity.py`**

- [ ] **Step 6: Run — expect both tests PASSED. Verify dead count = 18**

```bash
python3 -c "from sage_poc.nodes.skill_executor import _get_dead_step_policy_signals; print(len(_get_dead_step_policy_signals()))"
```

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/skills/mood_check_in.json tests/test_corpus_integrity.py
git commit -m "fix(mood_check_in): remove 9 overbroad keywords + delete dead mood_score rule (dead count 19->18)

mood_score was silently inert — deletes nothing working. Keyword removals reduce
false routing. Task 5b (Batch 2) adds emotional_intensity <= 3 replacement after
clinical confirmation of the construct substitution."
```

---

## Task 7 (Batch 1): Delete all remaining dead signal rules — no contraindications yet

**Files:** 17 skill JSON files, `tests/test_corpus_integrity.py`

**Scope:** For each skill below, delete the dead step_policy rule and remove its entry from `_KNOWN_DEAD_SIGNALS`. Do NOT add contraindications yet — those are Batch 2 (clinical sign-off required). Make one commit per skill.

The safety-critical rules (DV 7a/7h, trauma 7c/7d, dissociation 7i/7n, SI 7l) were already silently inert. Deleting them does not remove working protection. The Batch 2 contraindications will add probabilistic secondary protection once clinically reviewed, backed by deterministic Node 1 wiring (see Batch 2 Node 1 pre-check).

For each sub-task: delete rule → remove from `_KNOWN_DEAD_SIGNALS` → verify count decrements → commit.

| Sub-task | Skill | Signal | Clinical note |
|----------|-------|--------|---------------|
| 7a | `assertive_communication` | `coercive_relationship_indicators_detected` | DV — Node 1 `domestic_situation` flag must be primary |
| 7b | `behavioral_activation` | `hopelessness` | — |
| 7c | `cbt_thought_record` | `trauma_disclosure_detected` | Trauma — Node 1 `trauma_indicator` must be primary |
| 7d | `cognitive_restructuring` | `trauma_disclosure_detected` | Same as 7c |
| 7e | `dbt_tipp` | `physical_contraindication_disclosed` | — |
| 7f | `grief_loss` | `prolonged_grief_indicators_detected` | — |
| 7g | `grounding_5_4_3_2_1` | `sensory_limitation_disclosed` | — |
| 7h | `interpersonal_effectiveness` | `coercive_relationship_indicators_detected` | DV — same as 7a |
| 7i | `mindfulness_body_scan` | `dissociation_or_dizziness_reported` | Dissociation — verify Node 1 handling |
| 7j | `progressive_muscle_relaxation` | `pain_or_injury_mention` | — |
| 7k | `psychoed_anxiety` | `existing_anxiety_diagnosis_disclosed` | — |
| 7l | `psychoed_depression` | `active_suicidal_ideation_disclosed` | SI — `safety_check`/`crisis_phrases.json` is primary |
| 7m | `psychoed_stress` | `burnout_exhaustion_with_functional_impairment` | — |
| 7n | `safe_place_visualization` | `dissociation_signal` | Same as 7i |
| 7o | `self_compassion_break` | `self_kindness_rejection_detected` | — |
| 7p | `sleep_hygiene` | `medication_or_substance_mention` | — |
| 7q | `values_clarification` | `family_values_conflict_detected` | — |

- [ ] **After all 17 deletions: verify count = 0 and `_KNOWN_DEAD_SIGNALS` is `frozenset()`**

```bash
python3 -c "from sage_poc.nodes.skill_executor import _get_dead_step_policy_signals; print(len(_get_dead_step_policy_signals()))"
pytest tests/test_corpus_integrity.py::test_dead_step_policy_signal_count_is_pinned -v
```

Also delete the worry_time `obsessive_theme_detected` rule (Task 6 deletion) here — its contraindication wording is Batch 2 (Task 6b), but the deletion itself is safe to include in this batch. Dead count lands at 0 after all 18 deletions (17 + worry_time).

---

## Task 6 (Batch 1 deletion only): Delete worry_time obsessive_theme_detected

**Files:** `src/sage_poc/skills/worry_time.json`, `tests/test_corpus_integrity.py`

- [ ] Delete the rule whose `condition.signal` is `"obsessive_theme_detected"` from `worry_time.json` step_policy
- [ ] Remove `("worry_time", "obsessive_theme_detected")` from `_KNOWN_DEAD_SIGNALS`
- [ ] Commit (can batch with Task 7 deletions or separate)

The OCD contraindication string for `sort_and_act.contraindications` is Task 6b in Batch 2.

---

## Task 8: Flip signals contract gate to RuntimeError

**Files:** `src/sage_poc/nodes/skill_executor.py`, `tests/test_corpus_integrity.py`

Run after Tasks 3–7 bring dead count to 0.

**Forward note:** This gate is correct while skills are repo JSON caught by CI. When the live CMS hot-loads skills, this gate must move to publish-time validation so a clinician edit cannot crash the running service. File as post-Gitex backlog.

- [ ] **Step 1: Replace `_KNOWN_DEAD_SIGNALS` and pinned test with zero-tolerance assertion**

Delete `_KNOWN_DEAD_SIGNALS` (the frozenset constant) and `test_dead_step_policy_signal_count_is_pinned`. Add:

```python
def test_no_dead_step_policy_signals():
    from sage_poc.nodes.skill_executor import _get_dead_step_policy_signals
    dead = _get_dead_step_policy_signals()
    assert not dead, (
        f"step_policy rules reference signals that never resolve at runtime: {sorted(dead)}. "
        "Wire the signal into evaluate_step_policy or remove the rule."
    )
```

- [ ] **Step 2: Run — expect PASSED (count = 0)**

- [ ] **Step 3: Flip `_validate_step_policy_signal_coverage` to raise RuntimeError**

In `skill_executor.py`, replace the function body:

```python
def _validate_step_policy_signal_coverage() -> None:
    dead = _get_dead_step_policy_signals()
    if dead:
        raise RuntimeError(
            f"[skill_executor] Step-policy rules reference signals that never resolve "
            f"at runtime: {dead}. Wire the signal into evaluate_step_policy or remove the rule."
        )
```

Remove the "Upgrade path" comment block above `_KNOWN_STEP_POLICY_SIGNALS` — it no longer applies.

- [ ] **Step 4: Verify startup**

```bash
python3 -c "import sage_poc.nodes.skill_executor; print('OK')"
```

- [ ] **Step 5: Run full suite — expect all pass. Commit**

```bash
git add src/sage_poc/nodes/skill_executor.py tests/test_corpus_integrity.py
git commit -m "feat(skill_executor): flip signals contract gate to RuntimeError (dead count = 0)"
```

---

## Task 9: Arabic Tier 1 stopgap in skill_select.py

**Files:** `src/sage_poc/nodes/skill_select.py`, `tests/test_skill_select.py`

**RED pre-check (do before implementing):** Confirm that `feat/arabic-kb-skills-expansion` has NOT been merged. That branch removed the psychotic_referral auto-select block from `skill_select.py`. If it was merged, restore the block first — it is the sole routing path for `psychotic_disclosure → psychotic_referral`. This is a safety fix independent of this plan.

Confirmed bug at line 128: `message = state["message_en"].lower()` — Arabic-script keywords in `target_presentations` cannot match the translated English string and are dead code.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_skill_select.py`:

```python
import pytest

@pytest.mark.asyncio
async def test_arabic_keyword_routes_via_tier1():
    from sage_poc.nodes.skill_select import skill_select_node
    state = {
        "primary_intent": "new_skill", "crisis_state": None,
        "active_skill_id": None, "active_step_id": None,
        "clinical_flags": [], "psychotic_referral_delivered": False, "path": [],
        "raw_message": "تنفس معي", "message_en": "breathe with me", "detected_language": "ar",
    }
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "box_breathing"
    assert result["skill_match_method"] == "keyword"


@pytest.mark.asyncio
async def test_arabic_keyword_fires_when_translation_is_ambiguous():
    from sage_poc.nodes.skill_select import skill_select_node
    state = {
        "primary_intent": "new_skill", "crisis_state": None,
        "active_skill_id": None, "active_step_id": None,
        "clinical_flags": [], "psychotic_referral_delivered": False, "path": [],
        "raw_message": "أبي تمرين تنفس",
        "message_en": "I want some exercise",  # ambiguous — would miss keyword
        "detected_language": "ar",
    }
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "box_breathing"
    assert result["skill_match_method"] == "keyword"
```

- [ ] **Step 2: Run — expect both FAILED**

- [ ] **Step 3: Add Arabic raw-message pass in `skill_select.py`**

Find the Tier 1 section (line 128). Replace:

```python
message = state["message_en"].lower()

# Tier 1: Keyword matching...
for skill_id, skill in _SKILLS.items():
    if skill_id in KEYWORD_SEMANTIC_SKIP:
        continue
    for keyword in skill.target_presentations:
        if keyword.lower() in message:
            return {
                "active_skill_id": skill_id,
                ...
```

with:

```python
message_en = state["message_en"].lower()
raw_message = (state.get("raw_message") or "").lower()
detected_language = state.get("detected_language") or "en"

# Tier 1: Keyword matching — synchronous, deterministic, fast.
# For Arabic sessions, also match against raw_message: Arabic-script keywords
# cannot match a translated English string.
# Stopgap: proper fix is language-tagged rules in Rules Service (backlog R1).
for skill_id, skill in _SKILLS.items():
    if skill_id in KEYWORD_SEMANTIC_SKIP:
        continue
    for keyword in skill.target_presentations:
        kw_lower = keyword.lower()
        if kw_lower in message_en or (detected_language == "ar" and kw_lower in raw_message):
            return {
                "active_skill_id": skill_id,
                "active_step_id": _SKILLS[skill_id].steps[0].step_id,
                "skill_match_method": "keyword",
                "semantic_score": None,
                "path": state["path"] + ["skill_select"],
            }
```

- [ ] **Step 4: Run — both tests PASSED. Run full `test_skill_select.py` and `test_skill_select_psychotic.py` suites**

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/nodes/skill_select.py tests/test_skill_select.py
git commit -m "fix(skill_select): add Arabic raw-message Tier 1 keyword pass (stopgap, backlog R1)"
```

---

## Task 10: Fix language-aware example selection in skill_executor

**Files:** `src/sage_poc/nodes/skill_executor.py`, `tests/test_skill_executor.py`

**Why this replaces the original Task 10 (reordering):** The root cause is `step.examples[:2]` in `evaluate_step_policy` (line 400) — a language-blind slice. Moving Arabic examples to position [0] in the JSON would fix the problem for Arabic users but simultaneously introduces English-session contamination: English users would receive an Arabic example as their primary few-shot exemplar, which strongly steers output language. The correct fix is language-aware selection: pick examples matching `detected_language`, then fall back.

After this task lands, the Arabic example position in JSON is cosmetically irrelevant for correctness. The original reorder (Task 10 from the first plan) is downgraded to a post-Gitex cosmetic.

- [ ] **Step 1: Write regression tests first (required before any code change)**

Add to `tests/test_skill_executor.py`:

```python
def test_english_session_receives_english_examples_only():
    """English-session LLM context must not contain Arabic few-shot examples.
    Language-blind examples[:2] caused EN→AR contamination when Arabic was at [0].
    """
    from sage_poc.nodes.skill_executor import evaluate_step_policy
    from sage_poc.skills.loader import load_skill

    skill = load_skill("box_breathing")
    step = next(s for s in skill.steps if s.step_id == "inhale_hold")
    
    # Verify box_breathing inhale_hold has mixed-language examples (test precondition)
    def has_arabic(t): return any(0x0600 <= ord(c) <= 0x06FF for c in t)
    assert any(has_arabic(ex) for ex in step.examples), "test precondition: need Arabic examples"
    assert any(not has_arabic(ex) for ex in step.examples), "test precondition: need English examples"

    result = evaluate_step_policy(
        skill=skill,
        current_step_id="inhale_hold",
        emotional_intensity=3,
        engagement=5,
        message_en="ok I did that",
        detected_language="en",
    )
    instruction = result.get("instruction", "")
    assert not has_arabic(instruction), (
        "English session instruction must not contain Arabic text. "
        "Language-aware example selection is broken."
    )


def test_arabic_session_receives_arabic_examples():
    from sage_poc.nodes.skill_executor import evaluate_step_policy
    from sage_poc.skills.loader import load_skill

    skill = load_skill("box_breathing")
    result = evaluate_step_policy(
        skill=skill,
        current_step_id="inhale_hold",
        emotional_intensity=3,
        engagement=5,
        message_en="ok I did that",
        detected_language="ar",
    )
    instruction = result.get("instruction", "")
    def has_arabic(t): return any(0x0600 <= ord(c) <= 0x06FF for c in t)
    assert has_arabic(instruction), (
        "Arabic session instruction must contain Arabic example text."
    )


def test_arabic_session_with_single_arabic_example_does_not_revert_to_all_english():
    """Step with only 1 Arabic example must not fall back to 2 English examples.

    The all-or-nothing fallback (len(matched) >= n else examples[:n]) would return
    2 English examples for an Arabic session when a step has only 1 Arabic example,
    re-introducing EN→AR contamination. The top-up approach returns [arabic, english1]
    instead — Arabic is still first and the session stays Arabic-primary.
    """
    from sage_poc.nodes.skill_executor import _select_examples
    examples = [
        "في وسعك تتنفس معي الحين",   # Arabic — only 1
        "Let's breathe together now",
        "OK let's try this together",
        "Breathe in with me",
    ]
    selected = _select_examples(examples, detected_language="ar", n=2)
    assert len(selected) == 2
    def has_arabic(t): return any(0x0600 <= ord(c) <= 0x06FF for c in t)
    assert has_arabic(selected[0]), "First selected example must be Arabic for Arabic session"
    assert not has_arabic(selected[1]), "Top-up example can be English when only 1 Arabic exists"
```

- [ ] **Step 2: Run — expect both FAILED (the language-blind slice is the bug)**

```bash
pytest tests/test_skill_executor.py::test_english_session_receives_english_examples_only tests/test_skill_executor.py::test_arabic_session_receives_arabic_examples -v
```

- [ ] **Step 3: Add `_select_examples` helper and `detected_language` parameter to `evaluate_step_policy`**

In `skill_executor.py`, add this helper before `evaluate_step_policy`:

```python
def _select_examples(examples: list[str], detected_language: str, n: int = 2) -> list[str]:
    """Select n examples preferring detected_language, topping up from the rest if needed.

    Uses matched-first then remainder, so a step with 1 Arabic + 4 English examples
    returns [arabic, english1] for ar sessions instead of falling back to [english1, english2].
    This avoids re-introducing EN→AR contamination on steps with only 1 Arabic example
    (§9.1 requires ≥3 but this handles non-conforming steps defensively).
    """
    def has_arabic(text: str) -> bool:
        return any(0x0600 <= ord(c) <= 0x06FF for c in text)

    want_arabic = detected_language == "ar"
    matched = [ex for ex in examples if has_arabic(ex) == want_arabic]
    # Use index-based remainder (not value-identity) to survive duplicate example strings
    # across languages without silently dropping copies from the top-up pool.
    matched_set = set(id(e) for e in matched)
    remainder = [ex for ex in examples if id(ex) not in matched_set]
    return (matched + remainder)[:n]
```

In the `evaluate_step_policy` signature, add `detected_language: str = "en"` as a keyword argument:

```python
def evaluate_step_policy(
    skill: Skill,
    current_step_id: str,
    emotional_intensity: int,
    engagement: int,
    message_en: str = "",
    detected_language: str = "en",       # <-- add this
    resistance_history: list[int] | None = None,
    ...
```

At line 400, replace:

```python
f"Example approaches: {'; '.join(step.examples[:2])}"
```

with:

```python
f"Example approaches: {'; '.join(_select_examples(step.examples, detected_language))}"
```

- [ ] **Step 4: Pass `detected_language` from `skill_executor_node` via `_base_policy_kwargs`**

In `skill_executor_node`, add to `_base_policy_kwargs`:

```python
_base_policy_kwargs = {
    ...
    "detected_language": state.get("detected_language") or "en",
    ...
}
```

- [ ] **Step 5: Run regression tests — expect both PASSED**

```bash
pytest tests/test_skill_executor.py::test_english_session_receives_english_examples_only tests/test_skill_executor.py::test_arabic_session_receives_arabic_examples -v
```

- [ ] **Step 6: Run full test suite**

```bash
pytest tests/ -x -q 2>&1 | tail -10
```

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/nodes/skill_executor.py tests/test_skill_executor.py
git commit -m "fix(skill_executor): language-aware example selection (replaces position-based approach)

examples[:2] was a language-blind slice. For Arabic sessions, English examples
were injected as few-shot context. For English sessions, moving Arabic to [0]
in JSON would have inverted the contamination.

Fix: _select_examples() filters by detected_language, then takes 2. Falls back
to first 2 if no language-matched examples exist.

Detected_language passed via _base_policy_kwargs from skill_executor_node."
```

---

## Task 11: Fix sleep_hygiene overbroad keywords

**Files:** `src/sage_poc/skills/sleep_hygiene.json`, `tests/test_corpus_integrity.py`

Confirmed: bare `"waking up"`, `"mind won't stop"`, `"mind wont stop"` all present.

- [ ] **Write failing test:**

```python
def test_sleep_hygiene_no_overbroad_keywords():
    import json, pathlib
    tp = set(json.loads(
        (pathlib.Path(__file__).parent.parent / "src/sage_poc/skills/sleep_hygiene.json")
        .read_text()
    ).get("target_presentations", []))
    assert "waking up" not in tp
    assert "mind wont stop" not in tp
    assert "mind won't stop" not in tp
```

- [ ] **Remove from `target_presentations`:** `"waking up"`, `"mind wont stop"`, `"mind won't stop"`

- [ ] **Add anchored replacements for `"waking up"`:**

```json
"waking up at night",
"waking up too early",
"waking up and can't go back to sleep"
```

Do NOT add replacements for the mind-racing variants — those belong to `worry_time`.

- [ ] **Run test — PASSED. Commit**

```bash
git add src/sage_poc/skills/sleep_hygiene.json tests/test_corpus_integrity.py
git commit -m "fix(sleep_hygiene): replace bare 'waking up' with anchored variants, remove 'mind wont stop'"
```

---

## Task 12: Trim cbt_thought_record semantic_description

**Files:** `src/sage_poc/skills/cbt_thought_record.json`, `tests/test_corpus_integrity.py`

Current: 1644 chars. Contains passive-SI-adjacent language that expands the embedding footprint into SI territory.

- [ ] **Write CI guard test:**

```python
def test_semantic_descriptions_under_600_chars():
    import json, pathlib
    LIMIT = 600
    skills_dir = pathlib.Path(__file__).parent.parent / "src/sage_poc/skills"
    violations = [
        f"{p.stem}: {len(json.loads(p.read_text()).get('semantic_description', ''))}"
        for p in sorted(skills_dir.glob("*.json"))
        if len(json.loads(p.read_text()).get("semantic_description", "")) > LIMIT
    ]
    assert not violations, f"semantic_description > {LIMIT} chars: {violations}"
```

- [ ] **Run — expect FAILED (cbt_thought_record: 1644, interpersonal_effectiveness: 3011)**

- [ ] **Replace `semantic_description` in `cbt_thought_record.json` with:**

```
Cognitive behavioral therapy thought record protocol. Three-column structured technique: identify automatic negative thoughts, examine evidence for and against, generate a balanced alternative interpretation. Beck's cognitive model of emotional disorders. Cognitive distortions: all-or-nothing thinking, catastrophizing, mind-reading, fortune-telling, personalization, overgeneralization, labeling, filtering. Thought records, Socratic questioning, behavioral experiments. Cognitive restructuring of automatic thoughts. Schema-based cognitive model. Core beliefs work.
```

Verify length < 600: `python3 -c "s='...'; print(len(s))"`

---

## Task 13: Trim interpersonal_effectiveness semantic_description

**Files:** `src/sage_poc/skills/interpersonal_effectiveness.json`

Current: 3011 chars. The last ~2500 chars are scenario prose about family conflicts that expands embedding footprint into grief and family-stress territory.

- [ ] **Replace `semantic_description` with:**

```
DBT interpersonal effectiveness skills module. DEAR MAN technique: Describe, Express, Assert, Reinforce, Mindful, Appear confident, Negotiate. GIVE skills: Gentle, Interested, Validate, Easy manner. FAST skills: Fair, Apologies, Stick to values, Truthful. Dialectical Behavior Therapy relationship skills. Validation and relationship repair. Balancing relationship goals, self-respect, and objectives. Managing conflict in close relationships.
```

- [ ] **Run test from Task 12 — expect PASSED. Commit Tasks 12 + 13 together:**

```bash
git add src/sage_poc/skills/cbt_thought_record.json src/sage_poc/skills/interpersonal_effectiveness.json tests/test_corpus_integrity.py
git commit -m "fix(skills): trim semantic_descriptions (cbt_thought_record 1644->~560, ie 3011->~440) — MUST recalibrate (Task 14)"
```

---

## Task 14: Recalibrate threshold

```bash
cd sage-poc && python3 scripts/calibrate_threshold.py
```

**Gap must be >= 0.03.** If below, do not merge Tasks 12–13.

```bash
git add scripts/calibration_results/ 2>/dev/null || true
git commit -m "chore: recalibrate threshold post-semantic-description trimming — gap verified healthy"
```

---

## Task 15: Fix grief_loss ambiguous keywords

**Files:** `src/sage_poc/skills/grief_loss.json`

Confirmed in source: `"مفقود إنسان عزيز"` (missing/unaccounted-for, not deceased), `"مبتدر العزاء"` (obscure MSA), `"I miss them so much"`, `"they're gone"`.

- [ ] **Remove from `target_presentations`:** `"مفقود إنسان عزيز"`, `"مبتدر العزاء"`, `"I miss them so much"`, `"they're gone"`

- [ ] **Add:**

```json
"فقدت شخص عزيز علي",
"الله يرحمه",
"الله يرحمها",
"passed away"
```

- [ ] **Validate JSON and commit:**

```bash
python3 -c "import json; json.load(open('src/sage_poc/skills/grief_loss.json')); print('valid')"
git add src/sage_poc/skills/grief_loss.json
git commit -m "fix(grief_loss): replace ambiguous Arabic keyword and non-bereavement English triggers"
```

---

# BATCH 2 — AMBER (clinical sign-off required)

## Task 5b: mood_check_in — add emotional_intensity proxy rule

**Sequencing:** Task 5b runs AFTER Task 8. Task 8 replaces the count-pinned test with `test_no_dead_step_policy_signals`. Task 5b adds a rule using `emotional_intensity` (a live signal), so it does not increase the dead count — but a worker must not reorder 5b before 8.

**Gate:** Clinical lead confirms: "holding on emotional_intensity <= 3 at step score_mood is the intended behaviour for low-rating presentations, and acute-distress low-mood is caught elsewhere (e.g. Node 1 or the emotional_intensity > 7 rule)."

The `mood_score` dead signal rule was already deleted in Task 5a (Batch 1). Task 5b ADD a new live rule using a reviewed substitute signal. Between batches, there is no hold-on-low-mood rule at all — this accurately reflects what was happening at runtime anyway (the rule was silently inert).

Once confirmed, add a new entry to `mood_check_in.json` `step_policy`:

```json
{
  "condition": {
    "signal": "emotional_intensity",
    "operator": "<=",
    "value": 3,
    "step": "score_mood"
  },
  "action": "hold_and_explore",
  "instruction": "User rated their mood low and is showing low emotional activation. Do not advance. Gently explore: 'What's been making things feel heavy lately?' Hold here until there is a clearer picture of what is driving the low mood.",
  "next_step_id": "current"
}
```

`emotional_intensity` is a live signal — this rule will fire at runtime. `("mood_check_in", "mood_score")` is already gone from `_KNOWN_DEAD_SIGNALS` (removed in Task 5a). Task 8 is complete by this point; no _KNOWN_DEAD_SIGNALS update needed.

---

## Task 6b: worry_time OCD contraindication string

**Gate:** Clinical lead reviews and approves the following contraindication text (structure already applied by Task 6 deletion — this is just the wording):

Proposed addition to `sort_and_act.contraindications`:

> "If the user describes thoughts as intrusive, unwanted, not-me, or distressing in themselves rather than about a real-world concern — do not proceed. OCD-type intrusive thoughts are worsened by deliberate scheduling and categorisation. Exit the skill, validate that their experience sounds different from ordinary worry, and suggest this kind of thinking usually benefits from a different approach with a professional."

---

## Task 7 contraindications: clinically-reviewed wording for each safety-critical rule

**Gate:** Clinical lead reviews and approves each contraindication string. Node 1 wiring verified per the Batch 2 Node 1 pre-check table at the top of this plan.

For each of the 17 skills from Task 7 (Batch 1), a contraindication may be added to the relevant step. The structure is already determined (which step, which field); the wording is the clinical artefact requiring review.

High-priority strings for clinical review (safety-critical):

**7a/7h — DV (assertive_communication, interpersonal_effectiveness):**
> "If the user describes a situation where the other person's response to assertiveness carries a risk of escalation, threat, or control — for example a partner who monitors their messages, controls their finances, or responds to boundary-setting with anger or punishment — do not proceed with skills training. Name what you are noticing and ask gently about their safety instead."

**7c/7d — Trauma (cbt_thought_record, cognitive_restructuring):**
> "If the user discloses a traumatic event (assault, abuse, significant loss, life-threatening experience), do not proceed with challenging the thoughts associated with that event. Thought challenging is not designed for trauma-anchored cognitions and can feel invalidating or destabilising. Validate the disclosure and let them lead."

**7i/7n — Dissociation (mindfulness_body_scan, safe_place_visualization):**
> "If the user reports feeling detached, unreal, floating, or like they are watching themselves from outside their body — pause immediately. Do not continue directing attention to body sensations. Gently orient them to the room. Let them lead whether to continue or stop."

**7l — SI during psychoeducation (psychoed_depression):**
> "CRITICAL: If the user discloses any suicidal ideation during this skill, exit immediately. Acknowledge what they said with care. Ask whether they are safe right now. Mention the crisis line (800 46342, free, 24/7). Psychoeducation is not appropriate when someone is expressing a wish to die."

---

## Task 4b: Financial hopelessness crisis phrases

**Gate:** Clinical lead reviews proposed phrases against C-SSRS/TD3 and SF-6 false-positive criteria. Specific concerns flagged:

- `"my family will lose everything if I lose this job"` — ordinary financial stress; high false-positive risk
- `"أفضل أرجع بلدي ميت من اشتغل هنا وأنا ذليل"` — Gulf idiom; needs dialect-specific clinical review for frustration vs crisis intent

Proposed flag level: `si_passive` (financial hopelessness as a passive SI risk factor, not explicit). Exact strings, flag assignments, and source codes (SK-FIN-001) subject to clinical review.

---

# Architecture Backlog (post-Gitex)

**Contraindication firing tests (CMS/Full Build gate) — 2026-06-06**
The Batch 1 RuntimeError gate catches dead step_policy signals — rules that reference signals never resolved at runtime. It does NOT catch the parallel class of safety gap: a clinician-authored contraindication string whose detection is entirely LLM-discretionary, with no behavioural test proving it fires on the presentations it targets.

All contraindication strings shipped in Batch 2 (DV, trauma, SI, dissociation, physical condition, OCD) have this gap. There is no test asserting that, given a message describing a coercive relationship or a trauma disclosure, the LLM actually reads the contraindication and pauses the skill. For POC this is an accepted gap — the contraindications are new secondary layer content, not replacements for deterministic gates. For CMS/Full Build, this is the verification closure the whole audit chain opened: §5.5 requires "does the rule fire when expected?" and the contraindication strings are rules that have never been tested against that criterion.

Fix shape: a behavioural harness that injects a target presentation for each contraindication (e.g. "my husband controls my bank account" for the DV contraindication in assertive_communication), runs the skill executor with the LLM, and asserts the output contains a pause, a safety inquiry, or an exit signal rather than advancing the step. Requires a Judge LLM or a structured output assertion. This is the same harness design as the MindEval multi-turn test plan — the contraindication test is a single-turn subset of it.

**S15 — Rules Service priority field for Tier 1 disambiguation**
Tier 1 is first-match-wins by `SKILL_REGISTRY` list order — a code constant, not a clinician-editable rule (violates Cardinal Rule 2). Proper fix: `tier1_priority: int` in Rules Service.

**R1 — Language-tagged matching rules in Rules Service**
Task 9 hardcodes `detected_language == "ar"`. Proper fix: tag each keyword with a `language` field in Rules Service.

**mood_score signal extraction**
Task 5b uses `emotional_intensity <= 3` proxy. Proper fix: extract the integer from the user's message when active step is `score_mood`; wire `mood_score` into `_KNOWN_STEP_POLICY_SIGNALS`.

**Task 8 / CMS gate**
RuntimeError-at-startup is correct while skills are repo JSON caught by CI. When the live CMS hot-loads skills, move validation to publish-time so a clinician edit cannot crash the running service.

**Dissociation at Node 1 (6th clinical flag)**
v7 §5.1 defines five clinical flags: substance, trauma, eating, domestic, medication. Dissociation is absent. The contraindications for 7i/7n (body scan, safe place) are LLM-discretionary only — no deterministic backstop exists. Add `dissociation_indicator` as a 6th clinical flag in `clinical_flag_patterns.json`, matching signals like "I feel detached", "I'm watching myself", "nothing feels real". Requires clinical review of detection patterns and downstream routing logic.

**Crisis line canonical source**
`CRISIS_LINE_UAE = "800 46342"` in `src/sage_poc/config.py` governs Python-generated prose. The literal also appears in clinician-authored JSON (post_crisis L1, 7l contraindication). Add a corpus-integrity test asserting every occurrence of a helpline number in skill JSON matches the canonical value.

**Implementation note:** Scope the regex to known fields (`escalation_matrix`, `contraindications`) rather than the whole serialised document. Running it against `json.dumps(..., ensure_ascii=False)` of the full skill will false-trip on any long digit sequence in Arabic few-shot examples or count strings. Confirm the test passes clean against the current corpus before wiring into CI.

```python
def test_crisis_line_literals_match_canonical():
    import json, pathlib, re
    from sage_poc.config import CRISIS_LINE_UAE
    HELPLINE_RE = re.compile(r'\b[89]\d{2}[\s\d]{5,}\d\b')
    CHECKED_FIELDS = {"escalation_matrix", "contraindications"}
    skills_dir = pathlib.Path(__file__).parent.parent / "src/sage_poc/skills"
    violations = []
    for path in sorted(skills_dir.glob("*.json")):
        skill = json.loads(path.read_text())
        # Scope to known clinician-authored fields only — not full JSON dump
        text = json.dumps({k: v for k, v in skill.items() if k in CHECKED_FIELDS}, ensure_ascii=False)
        for match in HELPLINE_RE.finditer(text):
            number = re.sub(r'\s+', ' ', match.group()).strip()
            if number != CRISIS_LINE_UAE:
                violations.append(f"{path.stem}: found '{number}', expected '{CRISIS_LINE_UAE}'")
    assert not violations, f"Crisis line mismatch in skill JSON: {violations}"
```
