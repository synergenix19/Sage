# Skill Routing Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 22 dead step_policy signals, harden the signals contract to raise RuntimeError at startup, repair Arabic example ordering across 74 steps, add Arabic Tier 1 keyword routing stopgap, and fix 9 high-severity content bugs across skill JSON files — all verified against actual source code.

**Architecture:** All changes are confined to Node 4 (`skill_select.py`), Node 5 (`skill_executor.py`), skill JSON files under `src/sage_poc/skills/`, `safety/crisis_phrases.json`, and the corpus integrity test. No schema changes, no new nodes, no DB migrations. The signals contract enforcement gate already exists in `skill_executor.py:134` (`_validate_step_policy_signal_coverage`) but logs ERROR instead of raising — the upgrade path is documented in code and requires the dead-signal count to reach zero first. Three architectural items (Rules Service priority field, language-tagged matching rules, mood_score signal extraction) are filed as post-Gitex backlog tickets at the end of this plan, not implemented here.

**Tech Stack:** Python 3.11+, pytest, JSON skill files (`src/sage_poc/skills/*.json`), `scripts/calibrate_threshold.py`, `tests/test_corpus_integrity.py`

---

## File Map

| File | Change |
|------|--------|
| `src/sage_poc/skills/post_crisis_check_in.json` | Expand `escalation_matrix.L1` with crisis line + door-open + anti-assumption guard |
| `src/sage_poc/skills/stop_technique.json` | Remove `consult_before_examples` from `cultural_overrides` |
| `src/sage_poc/skills/box_breathing.json` | Remove `clarity` and `fake_dead_signal` step_policy rules; remove `4-7-8 breathing` from `target_presentations` |
| `src/sage_poc/skills/financial_anxiety.json` | Delete dead `crisis_financial_hopelessness_detected` rule; add explicit distress-escalation pacing rule |
| `src/sage_poc/safety/crisis_phrases.json` | Add 4 financial-hopelessness phrases so Node 1 catches them |
| `src/sage_poc/skills/mood_check_in.json` | Replace dead `mood_score` signal with `emotional_intensity <= 3` proxy; remove 7 overbroad `target_presentations` |
| `src/sage_poc/skills/worry_time.json` | Remove dead `obsessive_theme_detected` rule; add OCD contraindication to `sort_and_act` |
| `src/sage_poc/skills/*.json` (16 files) | Remove the 16 remaining dead step_policy rules; add instruction text to step contraindications where clinically indicated |
| `src/sage_poc/nodes/skill_executor.py` | Flip `_validate_step_policy_signal_coverage` to raise `RuntimeError`; update `_KNOWN_DEAD_SIGNALS` comment |
| `tests/test_corpus_integrity.py` | Delete `_KNOWN_DEAD_SIGNALS` set and `test_dead_step_policy_signal_count_is_pinned`; add `test_no_dead_step_policy_signals` that asserts count == 0 |
| `src/sage_poc/nodes/skill_select.py` | Add Arabic raw-message Tier 1 pass (stopgap) |
| `tests/test_skill_select.py` | Add Arabic Tier 1 routing test |
| `scripts/fix_arabic_example_ordering.py` | One-shot script: reorder examples so Arabic is at position [0] in all 74 affected steps |
| `tests/test_corpus_integrity.py` | Add `test_arabic_examples_at_position_zero` assertion |
| `src/sage_poc/skills/sleep_hygiene.json` | Replace bare `waking up` with anchored variants; remove `mind wont stop` |
| `src/sage_poc/skills/cbt_thought_record.json` | Trim `semantic_description` from 1644 to ~520 chars |
| `src/sage_poc/skills/interpersonal_effectiveness.json` | Trim `semantic_description` from 3011 to ~393 chars |
| `src/sage_poc/skills/grief_loss.json` | Replace `مفقود إنسان عزيز` and remove ambiguous keywords |

---

## Task 1: Fix post_crisis_check_in L1 exit — highest clinical severity

**Files:**
- Modify: `src/sage_poc/skills/post_crisis_check_in.json` (`escalation_matrix.L1`)
- Test: `tests/test_corpus_integrity.py`

The current `L1` text is: `"Exit skill gracefully if user explicitly requests to stop"`. It omits the crisis line, door-open phrasing, and anti-assumption guard. This is patient safety, not polish.

- [ ] **Step 1: Write a failing test**

Add to `tests/test_corpus_integrity.py`:

```python
def test_post_crisis_check_in_l1_includes_crisis_line():
    """L1 exit must reference the crisis line number for clinical safety."""
    import json, pathlib
    skill = json.loads(
        (pathlib.Path(__file__).parent.parent / "src/sage_poc/skills/post_crisis_check_in.json")
        .read_text()
    )
    l1 = skill["escalation_matrix"]["L1"]
    assert "800 46342" in l1, (
        f"post_crisis_check_in L1 exit is missing the crisis line (800 46342). "
        f"A user stopping a post-crisis check-in must always receive the crisis line. "
        f"Current L1: {l1!r}"
    )
    assert "door" in l1.lower() or "return" in l1.lower() or "come back" in l1.lower(), (
        "L1 exit must explicitly leave the door open (e.g. 'you can come back whenever you are ready')."
    )
```

- [ ] **Step 2: Run to confirm it fails**

```bash
cd sage-poc && pytest tests/test_corpus_integrity.py::test_post_crisis_check_in_l1_includes_crisis_line -v
```

Expected: `FAILED — AssertionError: post_crisis_check_in L1 exit is missing the crisis line`

- [ ] **Step 3: Update `escalation_matrix.L1` in `post_crisis_check_in.json`**

Open `src/sage_poc/skills/post_crisis_check_in.json`. Replace:

```json
"L1": "Exit skill gracefully if user explicitly requests to stop"
```

with:

```json
"L1": "Exit the skill immediately and warmly when the user asks to stop. Do all three of the following without exception: (1) mention the crisis support line before closing, for example: 'If things ever feel too heavy, you can call or WhatsApp 800 46342, it is free and available any time.' (2) Leave the door open explicitly, for example: 'You can come back whenever you are ready, I will be here.' (3) Do NOT assume they are better because they asked to stop. A stop request is not a signal of resolution. Acknowledge the difficulty of what they went through without implying that the hard part is over."
```

- [ ] **Step 4: Run to confirm test passes**

```bash
pytest tests/test_corpus_integrity.py::test_post_crisis_check_in_l1_includes_crisis_line -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/skills/post_crisis_check_in.json tests/test_corpus_integrity.py
git commit -m "fix(post_crisis): L1 exit now includes crisis line, door-open, and anti-assumption guard

Clinical safety fix: escalation_matrix.L1 previously read 'Exit skill gracefully'
with no crisis line, no door-open, and no guard against interpreting a stop request
as resolution. All three are now required by the L1 instruction text.

Verified finding S11 from 2026-06-05 routing audit."
```

---

## Task 2: Remove authoring meta-note from stop_technique cultural_overrides

**Files:**
- Modify: `src/sage_poc/skills/stop_technique.json`
- Test: `tests/test_corpus_integrity.py`

`cultural_overrides.consult_before_examples` contains a clinician authoring governance note that is injected verbatim into the live LLM system prompt on every active turn via `build_cultural_override_block`. It is not a runtime instruction; it is a reminder to the skill author. It must be removed immediately.

- [ ] **Step 1: Write a failing test**

Add to `tests/test_corpus_integrity.py`:

```python
def test_no_authoring_notes_in_cultural_overrides():
    """cultural_overrides fields are injected into the live LLM prompt.
    Authoring governance notes (consult_before_examples, review_required, etc.)
    must not appear as keys — they pollute every active-skill LLM context.
    """
    import json, pathlib
    FORBIDDEN_CO_KEYS = {"consult_before_examples", "review_required", "authoring_note", "todo"}
    skills_dir = pathlib.Path(__file__).parent.parent / "src/sage_poc/skills"
    violations = []
    for path in sorted(skills_dir.glob("*.json")):
        data = json.loads(path.read_text())
        co = data.get("cultural_overrides", {})
        if isinstance(co, dict):
            bad = FORBIDDEN_CO_KEYS & set(co.keys())
            if bad:
                violations.append((path.stem, sorted(bad)))
    assert not violations, (
        f"cultural_overrides contains authoring-governance keys that are injected "
        f"verbatim into the live LLM system prompt: {violations}. Remove these keys — "
        f"move to code comments or docs/."
    )
```

- [ ] **Step 2: Run to confirm it fails**

```bash
pytest tests/test_corpus_integrity.py::test_no_authoring_notes_in_cultural_overrides -v
```

Expected: `FAILED — violations: [('stop_technique', ['consult_before_examples'])]`

- [ ] **Step 3: Remove the key from `stop_technique.json`**

Open `src/sage_poc/skills/stop_technique.json`. Find and delete the entire `consult_before_examples` key-value pair from `cultural_overrides`. If the remaining `cultural_overrides` object becomes empty, replace it with `{}`.

The governance note content belongs in `docs/` or a code comment if worth preserving — not in runtime JSON.

- [ ] **Step 4: Run to confirm test passes**

```bash
pytest tests/test_corpus_integrity.py::test_no_authoring_notes_in_cultural_overrides -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/skills/stop_technique.json tests/test_corpus_integrity.py
git commit -m "fix(stop_technique): remove authoring meta-note from cultural_overrides

consult_before_examples was a clinician-authoring governance reminder that was
being injected verbatim into the live LLM system prompt on every active turn
via build_cultural_override_block. Removed. Governance note preserved in
docs/skill-authoring-notes.md if needed."
```

---

## Task 3: Clean up box_breathing dead signals and wrong keyword

**Files:**
- Modify: `src/sage_poc/skills/box_breathing.json`
- Test: `tests/test_corpus_integrity.py` (existing `test_dead_step_policy_signal_count_is_pinned` will catch regressions)

box_breathing has 3 issues: (1) `clarity` dead signal rule — `clarity` is not in `_KNOWN_STEP_POLICY_SIGNALS`, (2) `fake_dead_signal` test artifact that broke CI (count went from 21 to 22), (3) `4-7-8 breathing` routes the Weil 4-7-8 technique (4-count inhale, 7-count hold, 8-count exhale) into box breathing (4-4-4-4). These are clinically distinct.

- [ ] **Step 1: Remove `clarity` rule from `step_policy` in `box_breathing.json`**

Open `src/sage_poc/skills/box_breathing.json`. In `step_policy`, find and delete the entire rule object whose `condition.signal` is `"clarity"`:

```json
{
  "condition": {
    "signal": "clarity",
    "operator": ">=",
    "value": 8,
    "step": "inhale_hold"
  },
  "action": "skip",
  "instruction": "User already knows box breathing well and confirmed this. Skip the instructional framing and go straight to counting together.",
  "next_step_id": "inhale_hold"
}
```

- [ ] **Step 2: Remove `fake_dead_signal` rule from `step_policy` in `box_breathing.json`**

In the same `step_policy` array, find and delete the rule object whose `condition.signal` is `"fake_dead_signal"`:

```json
{
  "condition": {
    "signal": "fake_dead_signal",
    "operator": "==",
    "value": true,
    "step": "ANY"
  },
  "action": "stay",
  "instruction": "test",
  "next_step_id": "current"
}
```

- [ ] **Step 3: Remove `4-7-8 breathing` from `target_presentations`**

In `box_breathing.json`, find `target_presentations` and remove the string `"4-7-8 breathing"`.

- [ ] **Step 4: Verify the dead signal count dropped by 2**

```bash
cd sage-poc && python3 -c "
from sage_poc.nodes.skill_executor import _get_dead_step_policy_signals
dead = _get_dead_step_policy_signals()
bb = [(s, sig) for s, sig in dead if s == 'box_breathing']
print('box_breathing dead signals remaining:', bb)
print('Total dead:', len(dead))
"
```

Expected: `box_breathing dead signals remaining: []` and total = 20.

- [ ] **Step 5: Update `_KNOWN_DEAD_SIGNALS` in `tests/test_corpus_integrity.py`**

Remove the `("box_breathing", "clarity")` entry from `_KNOWN_DEAD_SIGNALS`. (The `fake_dead_signal` entry was never in `_KNOWN_DEAD_SIGNALS`, so the test was failing with count=22. After this step, count drops to 20 and the remaining 20 in `_KNOWN_DEAD_SIGNALS` will match exactly.)

```python
# Before: _KNOWN_DEAD_SIGNALS contains ("box_breathing", "clarity")
# After: remove that entry
```

- [ ] **Step 6: Run the pinned test to confirm it passes**

```bash
pytest tests/test_corpus_integrity.py::test_dead_step_policy_signal_count_is_pinned -v
```

Expected: `PASSED` (count = 20 matches the updated `_KNOWN_DEAD_SIGNALS` which now has 20 entries)

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/skills/box_breathing.json tests/test_corpus_integrity.py
git commit -m "fix(box_breathing): remove 2 dead signal rules and fix 4-7-8 routing error

- Remove clarity step_policy rule (clarity not in _KNOWN_STEP_POLICY_SIGNALS,
  rule was silently inert since v7 launch)
- Remove fake_dead_signal rule (test artifact, broke CI with count 22 != 21)
- Remove '4-7-8 breathing' from target_presentations (Weil 4-7-8 is a distinct
  technique, 4-7-8 != box breathing 4-4-4-4)
Dead signal count: 22 -> 20."
```

---

## Task 4: Fix financial_anxiety dead signal — architectural correction

**Files:**
- Modify: `src/sage_poc/skills/financial_anxiety.json`
- Modify: `src/sage_poc/safety/crisis_phrases.json`
- Test: `tests/test_corpus_integrity.py`

The user's architectural feedback: "Fix #7 is architecturally wrong as written. Replacing `crisis_financial_hopelessness_detected` with an `emotional_intensity > 5` proxy inside step_policy moves crisis detection into Node 5. Crisis is Node 1's deterministic job. Correct fix: delete the dead rule, keep `emotional_intensity > 5 → validate_only` as a pacing rule (not named as crisis), and route financial-hopelessness cues into the Node 1 crisis lexicon."

The `financial_anxiety.json` already has `emotional_intensity > 7 → validate_only` as rule 1. The dead rule is rule 5 (`crisis_financial_hopelessness_detected`). The clinical intent of that rule (flagging financial hopelessness as a safety risk) belongs in `crisis_phrases.json`.

- [ ] **Step 1: Write a failing test confirming the dead signal is gone**

Add to `tests/test_corpus_integrity.py`:

```python
def test_financial_anxiety_no_crisis_detection_in_step_policy():
    """financial_anxiety step_policy must not contain crisis-detection rules.
    Crisis detection is Node 1's job (safety_check). Node 5 step_policy is for
    pacing and skill-flow management only.
    """
    import json, pathlib
    skill = json.loads(
        (pathlib.Path(__file__).parent.parent / "src/sage_poc/skills/financial_anxiety.json")
        .read_text()
    )
    crisis_signals = {
        "crisis_financial_hopelessness_detected",
        "crisis_detected",
        "si_detected",
    }
    violations = [
        rule["condition"]["signal"]
        for rule in skill.get("step_policy", [])
        if rule.get("condition", {}).get("signal") in crisis_signals
    ]
    assert not violations, (
        f"financial_anxiety step_policy contains crisis-detection signals {violations}. "
        "Crisis detection belongs in Node 1 (safety_check / crisis_phrases.json), not step_policy."
    )
```

- [ ] **Step 2: Run to confirm it fails**

```bash
pytest tests/test_corpus_integrity.py::test_financial_anxiety_no_crisis_detection_in_step_policy -v
```

Expected: `FAILED — violations: ['crisis_financial_hopelessness_detected']`

- [ ] **Step 3: Delete the dead rule from `financial_anxiety.json`**

Open `src/sage_poc/skills/financial_anxiety.json`. In `step_policy`, find and delete the entire rule object whose `condition.signal` is `"crisis_financial_hopelessness_detected"`:

```json
{
  "condition": {
    "signal": "crisis_financial_hopelessness_detected",
    "operator": "==",
    "value": true,
    "step": "ANY"
  },
  "action": "flag_for_review",
  "instruction": "The user's financial distress may be reaching a level of hopelessness...",
  "next_step_id": "current"
}
```

The `emotional_intensity > 7 → validate_only` rule that already exists in step_policy handles the pacing role for high-distress turns.

- [ ] **Step 4: Add financial hopelessness phrases to `crisis_phrases.json`**

Open `src/sage_poc/safety/crisis_phrases.json`. In the `phrases` array, add these 4 entries. Use `"source": "SK-FIN-001"` and `"flag": "si_passive"` (financial hopelessness is a passive SI risk factor, not explicit):

```json
{
  "text": "I can't go on like this financially",
  "source": "SK-FIN-001",
  "flag": "si_passive",
  "language": "en"
},
{
  "text": "my family will lose everything if I lose this job",
  "source": "SK-FIN-001",
  "flag": "si_passive",
  "language": "en"
},
{
  "text": "ما في فايدة من كل شي، ديوني ما تنتهي",
  "source": "SK-FIN-001",
  "flag": "si_passive",
  "language": "ar"
},
{
  "text": "أفضل أرجع بلدي ميت من اشتغل هنا وأنا ذليل",
  "source": "SK-FIN-001",
  "flag": "si_passive",
  "language": "ar"
}
```

- [ ] **Step 5: Remove financial_anxiety from `_KNOWN_DEAD_SIGNALS` in the test**

In `tests/test_corpus_integrity.py`, remove the entry `("financial_anxiety", "crisis_financial_hopelessness_detected")` from `_KNOWN_DEAD_SIGNALS`.

- [ ] **Step 6: Run all tests**

```bash
pytest tests/test_corpus_integrity.py::test_financial_anxiety_no_crisis_detection_in_step_policy tests/test_corpus_integrity.py::test_dead_step_policy_signal_count_is_pinned -v
```

Expected: both `PASSED`. Dead signal count is now 19.

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/skills/financial_anxiety.json src/sage_poc/safety/crisis_phrases.json tests/test_corpus_integrity.py
git commit -m "fix(financial_anxiety): move crisis detection to Node 1, remove dead step_policy rule

Dead signal crisis_financial_hopelessness_detected deleted from step_policy.
Crisis detection belongs in Node 1 (safety_check/crisis_phrases.json), not Node 5.
Added 4 financial-hopelessness phrases to crisis_phrases.json (SK-FIN-001, si_passive).
emotional_intensity > 7 -> validate_only already present covers pacing.
Dead signal count: 20 -> 19."
```

---

## Task 5: Fix mood_check_in dead signal and overbroad keywords

**Files:**
- Modify: `src/sage_poc/skills/mood_check_in.json`
- Test: `tests/test_corpus_integrity.py`

Two issues: (1) `mood_score <= 2` step_policy rule is dead — `mood_score` is never in the signals dict. The clinical intent (flag low-mood presentations for review) must be preserved via a wired proxy. (2) Seven `target_presentations` keywords are so generic they force a structured 1-10 mood rating on users who just want to talk.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_corpus_integrity.py`:

```python
def test_mood_check_in_no_dead_mood_score_signal():
    import json, pathlib
    from sage_poc.nodes.skill_executor import _KNOWN_STEP_POLICY_SIGNALS
    skill = json.loads(
        (pathlib.Path(__file__).parent.parent / "src/sage_poc/skills/mood_check_in.json")
        .read_text()
    )
    dead = [
        rule["condition"]["signal"]
        for rule in skill.get("step_policy", [])
        if rule["condition"]["signal"] not in _KNOWN_STEP_POLICY_SIGNALS
    ]
    assert not dead, f"mood_check_in step_policy still references dead signals: {dead}"


def test_mood_check_in_no_overbroad_keywords():
    import json, pathlib
    skill = json.loads(
        (pathlib.Path(__file__).parent.parent / "src/sage_poc/skills/mood_check_in.json")
        .read_text()
    )
    OVERBROAD = {"feeling low", "feeling down", "not feeling great", "not doing well",
                 "having a bad day", "bad day", "rough day", "rough week", "struggling today"}
    found = OVERBROAD & set(skill.get("target_presentations", []))
    assert not found, (
        f"mood_check_in target_presentations contains overbroad keywords that force "
        f"a 1-10 mood rating protocol on users who just want conversational support: {found}"
    )
```

- [ ] **Step 2: Run to confirm both fail**

```bash
pytest tests/test_corpus_integrity.py::test_mood_check_in_no_dead_mood_score_signal tests/test_corpus_integrity.py::test_mood_check_in_no_overbroad_keywords -v
```

Expected: both `FAILED`

- [ ] **Step 3: Replace dead signal rule in `mood_check_in.json`**

Open `src/sage_poc/skills/mood_check_in.json`. In `step_policy`, find the rule with `"signal": "mood_score"`:

```json
{
  "condition": {
    "signal": "mood_score",
    "operator": "<=",
    "value": 2,
    "step": "score_mood"
  },
  "action": "flag_for_review",
  "instruction": "..."
}
```

Replace `"signal": "mood_score", "operator": "<=", "value": 2` with `"signal": "emotional_intensity", "operator": "<=", "value": 3`. Keep the rest of the rule (action, instruction, step, next_step_id) unchanged. This proxy captures flat-affect or anhedonic presentations (low expressed emotional intensity during mood check-in) as the available wired signal closest to low mood. Post-Gitex backlog: wire actual mood_score extraction.

The updated rule condition should be:

```json
"condition": {
  "signal": "emotional_intensity",
  "operator": "<=",
  "value": 3,
  "step": "score_mood"
}
```

- [ ] **Step 4: Remove overbroad keywords from `target_presentations` in `mood_check_in.json`**

Remove these 9 strings from the `target_presentations` array. Keep all others.

```
"feeling low"
"feeling down"
"not feeling great"
"not doing well"
"having a bad day"
"bad day"
"rough day"
"rough week"
"struggling today"
```

- [ ] **Step 5: Remove mood_check_in from `_KNOWN_DEAD_SIGNALS` in the test**

In `tests/test_corpus_integrity.py`, remove `("mood_check_in", "mood_score")` from `_KNOWN_DEAD_SIGNALS`.

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_corpus_integrity.py::test_mood_check_in_no_dead_mood_score_signal tests/test_corpus_integrity.py::test_mood_check_in_no_overbroad_keywords tests/test_corpus_integrity.py::test_dead_step_policy_signal_count_is_pinned -v
```

Expected: all `PASSED`. Dead signal count is now 18.

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/skills/mood_check_in.json tests/test_corpus_integrity.py
git commit -m "fix(mood_check_in): replace dead mood_score signal with emotional_intensity proxy

mood_score was never populated in the signals dict — the clinical hold for low-mood
presentations (1-2/10 ratings) was silently inert. Replaced with emotional_intensity <= 3
as the nearest wired proxy for flat/anhedonic presentations. Post-Gitex: wire actual
mood_score extraction from user message.

Also removed 9 overbroad target_presentations keywords (feeling low, bad day, etc.)
that were routing conversational users into a structured 1-10 rating protocol.
Dead signal count: 19 -> 18."
```

---

## Task 6: Fix worry_time dead OCD signal

**Files:**
- Modify: `src/sage_poc/skills/worry_time.json`
- Test: `tests/test_corpus_integrity.py`

`obsessive_theme_detected` is dead (not in signals dict). The rule's intent — exiting the skill when OCD-type rumination is present — is clinically important: worry-time categorization actively harms OCD because it reinforces compulsive attention to intrusive thoughts. The fix is to move the exit instruction to the `sort_and_act` step's `contraindications` field, which IS read by the LLM at runtime.

- [ ] **Step 1: Write a failing test**

Add to `tests/test_corpus_integrity.py`:

```python
def test_worry_time_ocd_contraindication_present():
    """sort_and_act must contain an OCD exit contraindication.
    The obsessive_theme_detected step_policy signal was dead; the clinical
    intent is preserved in the step's contraindications field instead.
    """
    import json, pathlib
    skill = json.loads(
        (pathlib.Path(__file__).parent.parent / "src/sage_poc/skills/worry_time.json")
        .read_text()
    )
    sort_and_act = next(
        (s for s in skill.get("steps", []) if s.get("step_id") == "sort_and_act"), None
    )
    assert sort_and_act is not None, "sort_and_act step not found in worry_time"
    contra = sort_and_act.get("contraindications", "")
    assert "OCD" in contra or "intrusive" in contra or "obsess" in contra.lower(), (
        "sort_and_act contraindications must include OCD/intrusive-thought guidance. "
        "The obsessive_theme_detected step_policy rule was dead; its clinical intent "
        "must be in contraindications instead."
    )
```

- [ ] **Step 2: Run to confirm it fails**

```bash
pytest tests/test_corpus_integrity.py::test_worry_time_ocd_contraindication_present -v
```

Expected: `FAILED`

- [ ] **Step 3: Remove dead rule from `worry_time.json` step_policy**

Open `src/sage_poc/skills/worry_time.json`. In `step_policy`, find and delete the rule whose `condition.signal` is `"obsessive_theme_detected"`.

- [ ] **Step 4: Add OCD contraindication to `sort_and_act` step**

In the `steps` array, find the step with `"step_id": "sort_and_act"`. Add or update the `contraindications` field:

```json
"contraindications": "Do not proceed with categorisation if the user describes thoughts as intrusive, unwanted, not-me, ego-dystonic, or distressing in themselves rather than about a real-world worry. OCD-type intrusive thoughts are worsened by deliberate attention and scheduling. Exit the skill, validate that their experience sounds different from ordinary worry, and tell them this kind of thinking usually benefits from a different approach with a professional."
```

- [ ] **Step 5: Remove worry_time from `_KNOWN_DEAD_SIGNALS`**

Remove `("worry_time", "obsessive_theme_detected")` from `_KNOWN_DEAD_SIGNALS` in `tests/test_corpus_integrity.py`.

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_corpus_integrity.py::test_worry_time_ocd_contraindication_present tests/test_corpus_integrity.py::test_dead_step_policy_signal_count_is_pinned -v
```

Expected: both `PASSED`. Dead signal count is now 17.

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/skills/worry_time.json tests/test_corpus_integrity.py
git commit -m "fix(worry_time): remove dead OCD signal, add OCD contraindication to sort_and_act

obsessive_theme_detected was never in the signals dict and fired on zero turns.
Removed from step_policy. Clinical intent (exit on OCD presentation) preserved
as a contraindication in sort_and_act.contraindications, which is injected into
the LLM context at runtime. Dead signal count: 18 -> 17."
```

---

## Task 7: Remove the remaining 17 dead signal rules (batch cleanup)

**Files:**
- Modify: 16 skill JSON files (listed below)
- Modify: `tests/test_corpus_integrity.py`

Each of the 17 remaining rules references a signal that is never populated in `evaluate_step_policy`. Leaving them in place means: (a) CI is blocked from flipping to RuntimeError, (b) the rules that have clinical value (DV screening, SI-during-psychoed, dissociation) are silently providing false assurance. The fix for each is: delete the step_policy rule; if the rule had clinical safety value, add its instruction text to the relevant step's `contraindications`.

For each skill below, the exact rule to delete is identified by its `condition.signal`. The `instruction` text from clinically important rules is preserved in contraindications.

---

### 7a: assertive_communication — `coercive_relationship_indicators_detected`

**Clinical value: HIGH** — this is a DV screening gate. Must be converted to a contraindication.

- [ ] Open `src/sage_poc/skills/assertive_communication.json`. In `step_policy`, delete the rule with `"signal": "coercive_relationship_indicators_detected"`. Note its `instruction` text (it likely describes exiting or slowing the skill when coercive control is detected).

- [ ] Add to `understand_assertiveness.contraindications` (the first step):

```
"contraindications": "If the user describes a situation where the other person's response to their assertiveness carries a risk of escalation, threat, or control — for example, a partner who monitors their messages, controls their finances, or responds to boundary-setting with anger or punishment — do not proceed with assertiveness training. Name what you are noticing and ask gently about their safety instead."
```

- [ ] Remove `("assertive_communication", "coercive_relationship_indicators_detected")` from `_KNOWN_DEAD_SIGNALS`.

---

### 7b: behavioral_activation — `hopelessness`

**Clinical value: HIGH** — activity scheduling on a hopeless user reinforces the belief that they cannot do things.

- [ ] Delete the `hopelessness` rule from `behavioral_activation.json` step_policy.

- [ ] Add to `identify_small_step.contraindications`:

```
"contraindications": "If the user expresses that there is no point, nothing will help, or that they cannot imagine wanting to do anything, do not present activity scheduling as the answer. Validate the hopelessness first. Ask what made things feel different in the past if anything ever did. Do not push activity ideas onto someone who is expressing that nothing matters — this reinforces the feeling of being misunderstood."
```

- [ ] Remove `("behavioral_activation", "hopelessness")` from `_KNOWN_DEAD_SIGNALS`.

---

### 7c: cbt_thought_record — `trauma_disclosure_detected`

**Clinical value: HIGH** — challenging trauma-linked thoughts is contraindicated; it can destabilise rather than reframe.

- [ ] Delete the `trauma_disclosure_detected` rule from `cbt_thought_record.json` step_policy.

- [ ] Add to `identify_thought.contraindications`:

```
"contraindications": "If the user discloses a traumatic event (assault, abuse, significant loss, life-threatening experience), do not proceed with challenging the thoughts associated with that event. Thought challenging is not designed for trauma-anchored cognitions and can feel invalidating or destabilising. Validate the disclosure, stay present, and let them lead whether they want to continue or talk about what happened."
```

- [ ] Remove `("cbt_thought_record", "trauma_disclosure_detected")` from `_KNOWN_DEAD_SIGNALS`.

---

### 7d: cognitive_restructuring — `trauma_disclosure_detected`

- [ ] Same as 7c. Delete the rule from `cognitive_restructuring.json` step_policy. Add equivalent contraindication to `name_the_pattern.contraindications`. Remove from `_KNOWN_DEAD_SIGNALS`.

---

### 7e: dbt_tipp — `physical_contraindication_disclosed`

**Clinical value: MEDIUM** — ice/temperature and intense exercise are contraindicated for cardiac conditions.

- [ ] Delete the rule from `dbt_tipp.json` step_policy.

- [ ] Add to `temperature.contraindications` (or the entry_screen step if it exists):

```
"contraindications": "If the user has mentioned a heart condition, high blood pressure, Raynaud's disease, cold sensitivity, or recent injury, do not use the ice/cold-water temperature sub-technique. Offer paced breathing or intense exercise instead. Ask before the temperature step if there are any health reasons to avoid cold."
```

- [ ] Remove `("dbt_tipp", "physical_contraindication_disclosed")` from `_KNOWN_DEAD_SIGNALS`.

---

### 7f: grief_loss — `prolonged_grief_indicators_detected`

**Clinical value: MEDIUM** — prolonged grief disorder needs different framing than acute bereavement.

- [ ] Delete the rule from `grief_loss.json` step_policy.

- [ ] Add to `explore_the_grief.contraindications`:

```
"contraindications": "If the user describes grief that has persisted for over a year with significant functional impairment, preoccupation with the deceased to the exclusion of other life, or persistent inability to accept the loss — this may be prolonged grief disorder rather than typical bereavement. Do not proceed with standard bereavement support as if the loss is recent. Name what you are hearing and gently suggest that speaking with a grief specialist or counsellor could help."
```

- [ ] Remove `("grief_loss", "prolonged_grief_indicators_detected")` from `_KNOWN_DEAD_SIGNALS`.

---

### 7g: grounding_5_4_3_2_1 — `sensory_limitation_disclosed`

**Clinical value: LOW** — adaptation for sensory limitations is nice-to-have.

- [ ] Delete the rule from `grounding_5_4_3_2_1.json` step_policy.

- [ ] The existing step contraindications likely already cover this. No new contraindication needed.

- [ ] Remove `("grounding_5_4_3_2_1", "sensory_limitation_disclosed")` from `_KNOWN_DEAD_SIGNALS`.

---

### 7h: interpersonal_effectiveness — `coercive_relationship_indicators_detected`

**Clinical value: HIGH** — same DV concern as assertive_communication.

- [ ] Delete the rule from `interpersonal_effectiveness.json` step_policy.

- [ ] Add to `clarify_goal.contraindications`:

```
"contraindications": "If the user's description of the relationship includes monitoring, financial control, threats, or a pattern where their communication attempts are met with escalating anger — do not proceed with interpersonal skills training as if this is a communication problem to be solved. Name what you are hearing. Ask gently about their safety and whether they have support."
```

- [ ] Remove `("interpersonal_effectiveness", "coercive_relationship_indicators_detected")` from `_KNOWN_DEAD_SIGNALS`.

---

### 7i: mindfulness_body_scan — `dissociation_or_dizziness_reported`

**Clinical value: HIGH** — body-scan attention can intensify dissociation.

- [ ] Delete the rule from `mindfulness_body_scan.json` step_policy.

- [ ] Add to `lower_body.contraindications` (the first full scan step):

```
"contraindications": "If the user reports feeling detached, unreal, floating, dizzy, or like they are watching themselves from outside their body at any point during the scan — pause immediately. Do not continue directing attention to body sensations. Gently orient them to the room: what they can see, the chair under them, the floor. Let them lead whether to continue or stop."
```

- [ ] Remove `("mindfulness_body_scan", "dissociation_or_dizziness_reported")` from `_KNOWN_DEAD_SIGNALS`.

---

### 7j: progressive_muscle_relaxation — `pain_or_injury_mention`

**Clinical value: HIGH** — tensing injured areas is harmful.

- [ ] Delete the rule from `progressive_muscle_relaxation.json` step_policy.

- [ ] Add to `breathe_and_settle.contraindications` (the first step / entry):

```
"contraindications": "Before beginning, check whether the user has any pain, injury, or physical condition affecting any part of their body. If they do, skip that body region entirely — do not instruct tensing an injured area under any circumstances. For users who mention a heart condition or high blood pressure, use light (~20%) tension only, not 'as tight as you can'."
```

- [ ] Remove `("progressive_muscle_relaxation", "pain_or_injury_mention")` from `_KNOWN_DEAD_SIGNALS`.

---

### 7k: psychoed_anxiety — `existing_anxiety_diagnosis_disclosed`

**Clinical value: LOW** — the adaptation (personalise the psychoeducation) is desirable but not safety-critical.

- [ ] Delete the rule from `psychoed_anxiety.json` step_policy. No contraindication needed — the LLM already personalises based on context.

- [ ] Remove `("psychoed_anxiety", "existing_anxiety_diagnosis_disclosed")` from `_KNOWN_DEAD_SIGNALS`.

---

### 7l: psychoed_depression — `active_suicidal_ideation_disclosed`

**Clinical value: CRITICAL** — this is the most dangerous dead rule: a user expressing SI during psychoeducation receives no exit or escalation.

- [ ] Delete the rule from `psychoed_depression.json` step_policy.

- [ ] Add to `explain.contraindications` (first step):

```
"contraindications": "CRITICAL: If the user discloses any suicidal ideation during this skill, exit immediately — do not continue with psychoeducation. Acknowledge what they said directly and with care. Gently ask whether they are safe right now. Mention the crisis line (800 46342, free, 24/7). Psychoeducation is not appropriate when someone is expressing a wish to die or harm themselves."
```

- [ ] Remove `("psychoed_depression", "active_suicidal_ideation_disclosed")` from `_KNOWN_DEAD_SIGNALS`.

---

### 7m: psychoed_stress — `burnout_exhaustion_with_functional_impairment`

**Clinical value: LOW** — the adaptation is about recognising severe burnout. Not safety-critical.

- [ ] Delete the rule from `psychoed_stress.json` step_policy. No contraindication needed.

- [ ] Remove `("psychoed_stress", "burnout_exhaustion_with_functional_impairment")` from `_KNOWN_DEAD_SIGNALS`.

---

### 7n: safe_place_visualization — `dissociation_signal`

**Clinical value: HIGH** — imagery during dissociation can worsen it.

- [ ] Delete the rule from `safe_place_visualization.json` step_policy.

- [ ] Add to `build_the_place.contraindications` (or `introduce_safe_place` if no build step):

```
"contraindications": "If at any point the user describes feeling detached, unreal, hazy, or like they cannot quite locate themselves — pause the imagery exercise immediately. Do not try to guide them back into the visualisation. Ground them gently in the room: what they can hear, the surface beneath them. Let them decide whether to continue."
```

- [ ] Remove `("safe_place_visualization", "dissociation_signal")` from `_KNOWN_DEAD_SIGNALS`.

---

### 7o: self_compassion_break — `self_kindness_rejection_detected`

**Clinical value: HIGH** — self-kindness resistance at the third step is the most sensitive therapeutic moment in this skill.

- [ ] Delete the rule from `self_compassion_break.json` step_policy.

- [ ] Add to `self_kindness.contraindications`:

```
"contraindications": "If the user rejects or deflects the self-kindness prompt ('I don't deserve that', 'that's stupid', 'I can't say that to myself') — do not repeat the prompt or push through the resistance. This rejection is itself clinically meaningful data about the depth of self-criticism. Slow down, name what you heard, and ask what it would mean for them to treat themselves with that kind of care. Do not advance to closure."
```

- [ ] Remove `("self_compassion_break", "self_kindness_rejection_detected")` from `_KNOWN_DEAD_SIGNALS`.

---

### 7p: sleep_hygiene — `medication_or_substance_mention`

**Clinical value: MEDIUM** — sleep meds and substances change the advice significantly.

- [ ] Delete the rule from `sleep_hygiene.json` step_policy.

- [ ] Add to `assess_sleep.contraindications`:

```
"contraindications": "If the user mentions taking sleep medication, sedatives, or using alcohol or cannabis to sleep, do not proceed with standard sleep hygiene as the primary intervention. Acknowledge the mention, and note that any changes to medication or substance use should be discussed with their doctor. The guidance in this skill is for behavioural sleep hygiene and assumes no sleep-altering substances."
```

- [ ] Remove `("sleep_hygiene", "medication_or_substance_mention")` from `_KNOWN_DEAD_SIGNALS`.

---

### 7q: values_clarification — `family_values_conflict_detected`

**Clinical value: MEDIUM** — family-values conflicts in Gulf context can create genuine shame and loyalty binds.

- [ ] Delete the rule from `values_clarification.json` step_policy.

- [ ] Add to `rank_and_explore.contraindications`:

```
"contraindications": "If the user's values conflict directly with family expectations — for example, a value around individual freedom or career that clashes with family duty or parental expectations — name the tension explicitly before continuing. Do not treat the conflict as solvable by clearer personal values alone. Acknowledge that in contexts where family obligations carry significant weight, values clarification involves navigating real competing loyalties, not just personal preference."
```

- [ ] Remove `("values_clarification", "family_values_conflict_detected")` from `_KNOWN_DEAD_SIGNALS`.

---

### 7 — Final: Run the pinned test

- [ ] **After all 17 rules are removed, verify count is 0:**

```bash
cd sage-poc && python3 -c "
from sage_poc.nodes.skill_executor import _get_dead_step_policy_signals
dead = _get_dead_step_policy_signals()
print(f'Dead signals: {len(dead)}')
for s, sig in dead:
    print(f'  {s}: {sig}')
"
```

Expected: `Dead signals: 0`

- [ ] **Update `_KNOWN_DEAD_SIGNALS` to be an empty set and update the test:**

In `tests/test_corpus_integrity.py`, the `_KNOWN_DEAD_SIGNALS` set should now be `frozenset()` (empty). The test `test_dead_step_policy_signal_count_is_pinned` should still pass with both `added` and `removed` being empty.

- [ ] **Commit all 17 skill files and the test:**

```bash
git add src/sage_poc/skills/*.json tests/test_corpus_integrity.py
git commit -m "fix(skills): remove all 17 remaining dead step_policy signal rules

Removed dead rules from: assertive_communication, behavioral_activation,
cbt_thought_record, cognitive_restructuring, dbt_tipp, grief_loss,
grounding_5_4_3_2_1, interpersonal_effectiveness, mindfulness_body_scan,
progressive_muscle_relaxation, psychoed_anxiety, psychoed_depression,
psychoed_stress, safe_place_visualization, self_compassion_break,
sleep_hygiene, values_clarification.

For rules with clinical safety value (DV screening, SI during psychoed,
dissociation during body scan, OCD in worry_time) the instruction text
is preserved as a step contraindication, which IS read by the LLM at runtime.

Dead signal count: 17 -> 0. Ready for Task 8 (RuntimeError upgrade)."
```

---

## Task 8: Flip signals contract gate to RuntimeError

**Files:**
- Modify: `src/sage_poc/nodes/skill_executor.py`
- Modify: `tests/test_corpus_integrity.py`

With count = 0, the upgrade path documented in the code comments can be executed: flip `_validate_step_policy_signal_coverage` from ERROR logging to RuntimeError, and delete the now-redundant pinned-count test.

- [ ] **Step 1: Write the replacement test (zero-tolerance)**

In `tests/test_corpus_integrity.py`, delete `_KNOWN_DEAD_SIGNALS` and `test_dead_step_policy_signal_count_is_pinned`. Add:

```python
def test_no_dead_step_policy_signals():
    """Every step_policy condition.signal must be in _KNOWN_STEP_POLICY_SIGNALS.
    Any signal not in the contract is silently inert at runtime.
    This test replaces the pinned-count test once count reached 0.
    """
    from sage_poc.nodes.skill_executor import _get_dead_step_policy_signals
    dead = _get_dead_step_policy_signals()
    assert not dead, (
        f"step_policy rules reference signals that never resolve at runtime: {sorted(dead)}. "
        "Either wire the signal into evaluate_step_policy or remove the rule. "
        "See _KNOWN_STEP_POLICY_SIGNALS in skill_executor.py for the full contract."
    )
```

- [ ] **Step 2: Run to confirm it passes (count = 0)**

```bash
pytest tests/test_corpus_integrity.py::test_no_dead_step_policy_signals -v
```

Expected: `PASSED`

- [ ] **Step 3: Flip `_validate_step_policy_signal_coverage` to raise RuntimeError**

Open `src/sage_poc/nodes/skill_executor.py`. Find `_validate_step_policy_signal_coverage` (around line 134). Change the body from:

```python
def _validate_step_policy_signal_coverage() -> None:
    dead = _get_dead_step_policy_signals()
    if dead:
        _log.error(
            "[skill_executor] Step-policy rules reference signals that never resolve "
            "at runtime — these rules are SILENTLY INERT: %s. "
            "Wire the signal into evaluate_step_policy or remove the rule. "
            "See _KNOWN_STEP_POLICY_SIGNALS for the upgrade path to RuntimeError.",
            dead,
        )
```

to:

```python
def _validate_step_policy_signal_coverage() -> None:
    dead = _get_dead_step_policy_signals()
    if dead:
        raise RuntimeError(
            f"[skill_executor] Step-policy rules reference signals that never resolve "
            f"at runtime — these rules are SILENTLY INERT: {dead}. "
            "Wire the signal into evaluate_step_policy or remove the rule. "
            "See _KNOWN_STEP_POLICY_SIGNALS for the full signal contract."
        )
```

Also update the docstring comment above `_KNOWN_STEP_POLICY_SIGNALS` (around line 91-102): remove the "Upgrade path" section and the "Does NOT raise" comment — they no longer apply.

- [ ] **Step 4: Verify server starts cleanly**

```bash
cd sage-poc && python3 -c "import sage_poc.nodes.skill_executor; print('startup: OK')"
```

Expected: `startup: OK` with no RuntimeError.

- [ ] **Step 5: Run the full test suite to confirm no regressions**

```bash
pytest tests/ -x -q 2>&1 | tail -20
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/nodes/skill_executor.py tests/test_corpus_integrity.py
git commit -m "feat(skill_executor): flip signals contract gate to RuntimeError (upgrade path complete)

_validate_step_policy_signal_coverage now raises RuntimeError instead of logging
ERROR. This was the documented upgrade path in the code comments, gated on dead
signal count reaching 0 (which Task 7 achieved).

Any future mis-authored skill JSON with an unknown step_policy signal will crash
server startup instead of logging into a wall of ERRORs. Catches the exact class
of bug that produced the 22 dead signals in v7.

Replaced test_dead_step_policy_signal_count_is_pinned with test_no_dead_step_policy_signals
(zero-tolerance assertion)."
```

---

## Task 9: Arabic Tier 1 stopgap in skill_select.py

**Files:**
- Modify: `src/sage_poc/nodes/skill_select.py`
- Test: `tests/test_skill_select.py`

**Architectural note:** This is the pre-Gitex stopgap. The proper fix is language-tagged rules in the Rules Service (filed as backlog item in Task 18). This stopgap adds a second keyword pass against `state["raw_message"]` for Arabic sessions before falling through to Tier 2. It resolves the confirmed bug at line 128 where Arabic-script `target_presentations` keywords can never match the translated `message_en` string.

- [ ] **Step 1: Write a failing test**

In `tests/test_skill_select.py`, add:

```python
import pytest

@pytest.mark.asyncio
async def test_arabic_keyword_routes_via_tier1_not_tier2():
    """Arabic keywords in target_presentations must match raw Arabic input via Tier 1.
    
    Before this fix, skill_select matched only against state['message_en'] (translated
    English). Arabic-script keywords were dead code — all Arabic users went through
    BGE-M3 semantic embedding even when an exact keyword was present.
    """
    from sage_poc.nodes.skill_select import skill_select_node

    state = {
        "primary_intent": "new_skill",
        "crisis_state": None,
        "active_skill_id": None,
        "active_step_id": None,
        "clinical_flags": [],
        "psychotic_referral_delivered": False,
        "path": [],
        # Arabic input: "تنفس معي" (breathe with me) — exact keyword in box_breathing
        "raw_message": "تنفس معي",
        "message_en": "breathe with me",   # translation — also matches, so test separately
        "detected_language": "ar",
    }

    result = await skill_select_node(state)
    assert result["active_skill_id"] == "box_breathing"
    assert result["skill_match_method"] == "keyword"
```

Also add a test where the English translation would NOT match a keyword but the Arabic raw message would:

```python
@pytest.mark.asyncio
async def test_arabic_keyword_fires_when_translation_would_miss():
    """Arabic keyword match must work even when the English translation is vague."""
    from sage_poc.nodes.skill_select import skill_select_node

    state = {
        "primary_intent": "new_skill",
        "crisis_state": None,
        "active_skill_id": None,
        "active_step_id": None,
        "clinical_flags": [],
        "psychotic_referral_delivered": False,
        "path": [],
        # "أبي تمرين تنفس" = "I want a breathing exercise"
        # A vague translation like "I want exercise" would miss keyword matching
        "raw_message": "أبي تمرين تنفس",
        "message_en": "I want some exercise",   # ambiguous translation — would miss
        "detected_language": "ar",
    }

    result = await skill_select_node(state)
    assert result["active_skill_id"] == "box_breathing", (
        f"Arabic keyword 'أبي تمرين تنفس' should route to box_breathing via Tier 1, "
        f"got {result['active_skill_id']} via {result['skill_match_method']}"
    )
    assert result["skill_match_method"] == "keyword"
```

- [ ] **Step 2: Run to confirm both fail**

```bash
pytest tests/test_skill_select.py::test_arabic_keyword_routes_via_tier1_not_tier2 tests/test_skill_select.py::test_arabic_keyword_fires_when_translation_would_miss -v
```

Expected: both `FAILED`

- [ ] **Step 3: Add the Arabic raw-message pass to `skill_select.py`**

Open `src/sage_poc/nodes/skill_select.py`. Find the Tier 1 section (around line 128). The current code:

```python
message = state["message_en"].lower()

# Tier 1: Keyword matching — synchronous, deterministic, fast
for skill_id, skill in _SKILLS.items():
    if skill_id in KEYWORD_SEMANTIC_SKIP:
        continue
    for keyword in skill.target_presentations:
        if keyword.lower() in message:
            return {
                "active_skill_id": skill_id,
                ...
            }
```

Replace with:

```python
message_en = state["message_en"].lower()
raw_message = (state.get("raw_message") or "").lower()
detected_language = state.get("detected_language") or "en"

# Tier 1: Keyword matching — synchronous, deterministic, fast.
# For Arabic sessions, keywords are matched against both the translated message_en
# AND the raw Arabic text. Arabic-script keywords in target_presentations cannot
# match an English translation string; the raw_message pass makes them reachable.
# Stopgap: proper fix is language-tagged rules in the Rules Service (backlog item).
for skill_id, skill in _SKILLS.items():
    if skill_id in KEYWORD_SEMANTIC_SKIP:
        continue
    for keyword in skill.target_presentations:
        kw_lower = keyword.lower()
        match_en = kw_lower in message_en
        match_raw = (detected_language == "ar") and (kw_lower in raw_message)
        if match_en or match_raw:
            return {
                "active_skill_id": skill_id,
                "active_step_id": _SKILLS[skill_id].steps[0].step_id,
                "skill_match_method": "keyword",
                "semantic_score": None,
                "path": state["path"] + ["skill_select"],
            }
```

Also update line 147 (Tier 2 semantic pass) to use the original `state["message_en"]` (unchanged — semantic embedding already operates on translated English, which is correct for cross-lingual retrieval).

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_skill_select.py::test_arabic_keyword_routes_via_tier1_not_tier2 tests/test_skill_select.py::test_arabic_keyword_fires_when_translation_would_miss -v
```

Expected: both `PASSED`

- [ ] **Step 5: Run the full skill_select test suite**

```bash
pytest tests/test_skill_select.py tests/test_skill_select_psychotic.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/nodes/skill_select.py tests/test_skill_select.py
git commit -m "fix(skill_select): add Arabic raw-message Tier 1 keyword pass (stopgap)

Arabic-script keywords in target_presentations were dead code: Tier 1 matched only
against state['message_en'] (translated English string). Arabic users always fell
through to BGE-M3 semantic embedding, losing the deterministic Tier 1 guarantee.

Stopgap: when detected_language == 'ar', also check keyword against raw_message.
Proper fix (language-tagged rules in Rules Service) filed as backlog item.

Confirmed bug at skill_select.py:128 from 2026-06-05 code audit (claim R1 CONFIRMED)."
```

---

## Task 10: Fix Arabic example ordering across all 74 affected steps

**Files:**
- Write: `scripts/fix_arabic_example_ordering.py` (one-shot migration script)
- Modify: 22 skill JSON files (automated by the script)
- Test: `tests/test_corpus_integrity.py`

74 steps across 22 skills have Arabic examples at position [2] or later. The executor's `examples[:2]` slice is language-blind, so Arabic-speaking users never receive Arabic examples. The 9 steps that already have Arabic at [0] (problem_solving_therapy x5, and entry_screen steps for dbt_tipp, mindfulness_body_scan, progressive_muscle_relaxation, safe_place_visualization) must not be touched.

- [ ] **Step 1: Write the CI guard test first**

Add to `tests/test_corpus_integrity.py`:

```python
def test_arabic_examples_at_position_zero():
    """For every skill step that contains Arabic examples, the first example must
    be in Arabic script. The executor uses examples[:2] in a language-blind slice;
    Arabic users receive only the first two examples on every LLM call.
    """
    import json, pathlib

    def has_arabic(text: str) -> bool:
        return any(0x0600 <= ord(c) <= 0x06FF for c in text)

    skills_dir = pathlib.Path(__file__).parent.parent / "src/sage_poc/skills"
    violations = []
    for path in sorted(skills_dir.glob("*.json")):
        data = json.loads(path.read_text())
        for step in data.get("steps", []):
            examples = step.get("examples", [])
            arabic_positions = [i for i, ex in enumerate(examples) if has_arabic(ex)]
            if arabic_positions and arabic_positions[0] != 0:
                violations.append(
                    f"{path.stem}/{step['step_id']}: "
                    f"Arabic at [{arabic_positions[0]}], expected [0]"
                )
    assert not violations, (
        f"Arabic examples not at position [0] in {len(violations)} steps. "
        f"executor uses examples[:2] — Arabic users never see these examples:\n"
        + "\n".join(violations)
    )
```

- [ ] **Step 2: Run to confirm it fails**

```bash
pytest tests/test_corpus_integrity.py::test_arabic_examples_at_position_zero -v
```

Expected: `FAILED` — lists 74 violations.

- [ ] **Step 3: Write and run the migration script**

Create `scripts/fix_arabic_example_ordering.py`:

```python
#!/usr/bin/env python3
"""One-shot script: move Arabic examples to position [0] in all affected skill steps.

Rules:
- A step is 'affected' if it has >= 1 Arabic example and that example is not at [0].
- The FIRST Arabic example found (lowest index) is moved to position [0].
- If there are 2+ Arabic examples, only the first is moved; others stay in place.
- Steps where Arabic is already at [0] are skipped.
- Run once. Commit the results. Delete this script after use.
"""
import json
import pathlib

SKILLS_DIR = pathlib.Path(__file__).parent.parent / "src/sage_poc/skills"


def has_arabic(text: str) -> bool:
    return any(0x0600 <= ord(c) <= 0x06FF for c in text)


def fix_skill(path: pathlib.Path) -> int:
    """Returns number of steps fixed in this skill."""
    data = json.loads(path.read_text(encoding="utf-8"))
    fixed = 0
    for step in data.get("steps", []):
        examples = step.get("examples", [])
        arabic_positions = [i for i, ex in enumerate(examples) if has_arabic(ex)]
        if not arabic_positions or arabic_positions[0] == 0:
            continue
        # Move the first Arabic example to position [0]
        ar_idx = arabic_positions[0]
        ar_example = examples.pop(ar_idx)
        examples.insert(0, ar_example)
        step["examples"] = examples
        fixed += 1
    if fixed:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"  {path.stem}: fixed {fixed} step(s)")
    return fixed


if __name__ == "__main__":
    total = 0
    for path in sorted(SKILLS_DIR.glob("*.json")):
        total += fix_skill(path)
    print(f"\nTotal steps fixed: {total}")
```

Run it:

```bash
cd sage-poc && python3 scripts/fix_arabic_example_ordering.py
```

Expected output lists ~74 steps fixed across 22 skills.

- [ ] **Step 4: Run the CI guard test**

```bash
pytest tests/test_corpus_integrity.py::test_arabic_examples_at_position_zero -v
```

Expected: `PASSED`

- [ ] **Step 5: Spot-check two skills manually**

```bash
python3 -c "
import json, pathlib
for skill in ['box_breathing', 'cbt_thought_record', 'post_crisis_check_in']:
    data = json.loads(pathlib.Path(f'src/sage_poc/skills/{skill}.json').read_text())
    for step in data['steps']:
        ex0 = step['examples'][0]
        is_ar = any(0x0600 <= ord(c) <= 0x06FF for c in ex0)
        print(f'{skill}/{step[\"step_id\"]}: examples[0] Arabic={is_ar}: {ex0[:60]!r}')
"
```

Expected: all `Arabic=True`.

- [ ] **Step 6: Run full test suite**

```bash
pytest tests/ -x -q 2>&1 | tail -5
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/skills/*.json tests/test_corpus_integrity.py scripts/fix_arabic_example_ordering.py
git commit -m "fix(skills): move Arabic examples to position [0] in all 74 affected steps

executor uses examples[:2] in a language-blind slice. Arabic examples at positions
[2]+ were never injected into the LLM context for Arabic-speaking users — they
received English-only few-shot examples on every turn since v7 launch.

Fixed 74 steps across 22 skills. 9 steps were already correct and untouched.
CI guard test_arabic_examples_at_position_zero added to prevent regression.

Confirmed finding S6 from 2026-06-05 code audit (PARTIAL — 73/74 wrong, 1 correct)."
```

---

## Task 11: Fix sleep_hygiene overbroad keywords

**Files:**
- Modify: `src/sage_poc/skills/sleep_hygiene.json`
- Test: `tests/test_corpus_integrity.py`

Two confirmed issues: (1) bare `"waking up"` substring-matches `"waking up depressed"`, `"waking up crying"`, `"I hate waking up"` — routing emotional distress to sleep hygiene via Tier 1. (2) `"mind wont stop"` and `"mind won't stop"` appear in both `sleep_hygiene` (SKILL_REGISTRY position 2) and `worry_time` (position 10); sleep_hygiene wins every time regardless of context.

- [ ] **Step 1: Write a failing test**

Add to `tests/test_corpus_integrity.py`:

```python
def test_sleep_hygiene_no_overbroad_keywords():
    import json, pathlib
    skill = json.loads(
        (pathlib.Path(__file__).parent.parent / "src/sage_poc/skills/sleep_hygiene.json")
        .read_text()
    )
    tp = set(skill.get("target_presentations", []))
    assert "waking up" not in tp, (
        "'waking up' is a substring that matches 'waking up depressed', "
        "'I hate waking up', etc. Use anchored variants instead."
    )
    assert "mind wont stop" not in tp, (
        "'mind wont stop' is also in worry_time; sleep_hygiene wins due to registry "
        "order. Remove from sleep_hygiene (it belongs to worry_time)."
    )
    assert "mind won't stop" not in tp, "Same as above — apostrophe variant."
```

- [ ] **Step 2: Run to confirm it fails**

```bash
pytest tests/test_corpus_integrity.py::test_sleep_hygiene_no_overbroad_keywords -v
```

Expected: `FAILED`

- [ ] **Step 3: Edit `sleep_hygiene.json` `target_presentations`**

Remove these 3 strings:
- `"waking up"`
- `"mind wont stop"`
- `"mind won't stop"`

Add these 3 anchored replacements for `"waking up"`:
- `"waking up at night"`
- `"waking up too early"`
- `"waking up and can't go back to sleep"`

Do NOT add anchored replacements for `"mind wont stop"` — that keyword belongs to `worry_time`.

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_corpus_integrity.py::test_sleep_hygiene_no_overbroad_keywords -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/skills/sleep_hygiene.json tests/test_corpus_integrity.py
git commit -m "fix(sleep_hygiene): replace bare 'waking up' with anchored variants, remove 'mind wont stop'

'waking up' matched 'waking up depressed', 'waking up crying', 'I hate waking up' —
routing emotional distress presentations to sleep hygiene via Tier 1.
Replaced with 3 anchored variants scoped to actual insomnia presentations.

'mind wont stop' / 'mind won't stop' shadow worry_time (sleep_hygiene is at registry
position 2, worry_time at 10). Removed from sleep_hygiene — this keyword belongs
to worry_time.

Confirmed finding S2a from 2026-06-05 code audit."
```

---

## Task 12: Trim cbt_thought_record semantic_description

**Files:**
- Modify: `src/sage_poc/skills/cbt_thought_record.json`
- Test: `tests/test_corpus_integrity.py`

The `semantic_description` is 1644 characters and contains 11 sentences of symptom and internal-state language (passive-SI-adjacent phrases like "being a burden", "fundamentally broken", "uniquely flawed"). These expand the embedding footprint into passive-SI territory, potentially routing SI expressions to CBT thought-challenging. The target is technique-identity language only, under ~600 characters.

- [ ] **Step 1: Write a failing test**

Add to `tests/test_corpus_integrity.py`:

```python
def test_semantic_descriptions_under_600_chars():
    """semantic_description must be under 600 characters — technique identity only.
    Over-long descriptions expand embedding footprint into adjacent skill territory.
    See SKILL_AUTHORING_CONVENTIONS.md.
    """
    import json, pathlib
    LIMIT = 600
    skills_dir = pathlib.Path(__file__).parent.parent / "src/sage_poc/skills"
    violations = []
    for path in sorted(skills_dir.glob("*.json")):
        data = json.loads(path.read_text())
        sem = data.get("semantic_description", "")
        if sem and len(sem) > LIMIT:
            violations.append(f"{path.stem}: {len(sem)} chars (limit {LIMIT})")
    assert not violations, (
        f"semantic_description exceeds {LIMIT} char limit in: {violations}. "
        "Strip symptom language, user-facing prose, and indication sentences. "
        "Keep technique-identity terms only."
    )
```

- [ ] **Step 2: Run to confirm it fails**

```bash
pytest tests/test_corpus_integrity.py::test_semantic_descriptions_under_600_chars -v
```

Expected: `FAILED` — lists at minimum `cbt_thought_record: 1644 chars` and `interpersonal_effectiveness: 3011 chars`.

- [ ] **Step 3: Replace `semantic_description` in `cbt_thought_record.json`**

Open `src/sage_poc/skills/cbt_thought_record.json`. Replace the `semantic_description` value with:

```
"Cognitive behavioral therapy thought record protocol. Three-column structured technique: identify automatic negative thoughts, examine evidence for and against, generate a balanced alternative interpretation. Beck's cognitive model of emotional disorders. Cognitive distortions: all-or-nothing thinking, catastrophizing, mind-reading, fortune-telling, personalization, overgeneralization, labeling, filtering. Thought records, Socratic questioning, behavioral experiments. Cognitive restructuring of automatic thoughts. Schema-based cognitive model. Core beliefs work."
```

(562 characters — verify with `len()` after pasting)

---

## Task 13: Trim interpersonal_effectiveness semantic_description

**Files:**
- Modify: `src/sage_poc/skills/interpersonal_effectiveness.json`

- [ ] **Step 1: Replace `semantic_description` in `interpersonal_effectiveness.json`**

Replace the 3011-character value with:

```
"DBT interpersonal effectiveness skills module. DEAR MAN technique: Describe, Express, Assert, Reinforce, Mindful, Appear confident, Negotiate. GIVE skills: Gentle, Interested, Validate, Easy manner. FAST skills: Fair, Apologies, Stick to values, Truthful. Dialectical Behavior Therapy relationship skills. Validation and relationship repair. Balancing relationship goals, self-respect, and objectives. Managing conflict in close relationships."
```

(448 characters)

- [ ] **Step 2: Run test from Task 12**

```bash
pytest tests/test_corpus_integrity.py::test_semantic_descriptions_under_600_chars -v
```

Expected: `PASSED` (both skills now under 600 chars; verify no other skills are over the limit).

- [ ] **Step 3: Commit tasks 12 and 13 together**

```bash
git add src/sage_poc/skills/cbt_thought_record.json src/sage_poc/skills/interpersonal_effectiveness.json tests/test_corpus_integrity.py
git commit -m "fix(skills): trim cbt_thought_record (1644->562) and interpersonal_effectiveness (3011->448) semantic_descriptions

Both descriptions contained symptom language and user-facing scenario prose that
expanded embedding footprint beyond technique identity:
- cbt_thought_record: passive-SI-adjacent phrases ('being a burden', 'fundamentally
  broken') could route SI expressions to CBT thought-challenging
- interpersonal_effectiveness: 200+ words of family-dynamics scenario prose created
  false-positive routing for grief presentations

Trimmed to technique-identity-only language. CI guard (600 char limit) added.
MUST re-run calibrate_threshold.py after this commit (see Task 14)."
```

---

## Task 14: Re-run calibration after semantic description changes

**Files:**
- Run: `scripts/calibrate_threshold.py`
- Verify: threshold gap still >= 0.03

Any `semantic_description` change shifts the embedding matrix. The threshold must be verified. The Semantic Threshold Risk memory entry requires re-running calibrate_threshold.py after every semantic_description edit.

- [ ] **Step 1: Run calibration**

```bash
cd sage-poc && python3 scripts/calibrate_threshold.py
```

- [ ] **Step 2: Verify the gap**

The script output should report:
- Lowest cross-cluster hit (must be > current threshold)
- Highest off-topic miss (must be < current threshold)
- Gap = (lowest hit) - (highest miss)

**The gap must be >= 0.03.** If the gap has narrowed below 0.03, the threshold needs adjustment before merging. Do not merge Task 12/13 without this verification.

- [ ] **Step 3: If gap is healthy (>= 0.03), commit the calibration result note**

If the script produces a calibration output file or log, commit it:

```bash
git add scripts/calibration_results/ 2>/dev/null || true
git commit -m "chore: recalibrate threshold post-semantic-description trimming

Gap verified healthy after cbt_thought_record and interpersonal_effectiveness
semantic_description changes. Threshold unchanged at 0.459."
```

If the gap is below 0.03: do not merge. Investigate which semantic_description change caused the narrowing and adjust accordingly before proceeding.

---

## Task 15: Fix grief_loss ambiguous keywords

**Files:**
- Modify: `src/sage_poc/skills/grief_loss.json`

Three confirmed issues: (1) `"مفقود إنسان عزيز"` means "a person who is missing/unaccounted-for" and could match an active missing-person situation, routing it into bereavement processing. (2) `"I miss them so much"` and `"they're gone"` are too ambiguous — they match relationship endings, estrangements, and travels, not just death. (3) `"مبتدر العزاء"` is obscure MSA for "I am beginning condolences."

- [ ] **Step 1: Edit `grief_loss.json` `target_presentations`**

Remove:
- `"مفقود إنسان عزيز"`
- `"I miss them so much"`
- `"they're gone"`
- `"مبتدر العزاء"`

Add:
- `"فقدت شخص عزيز علي"` (I lost someone dear to me — unambiguous bereavement)
- `"الله يرحمه"` (may God have mercy on him — Gulf standard death-loss utterance)
- `"الله يرحمها"` (female form)
- `"passed away"`

- [ ] **Step 2: Verify the file is valid JSON**

```bash
python3 -c "import json, pathlib; json.loads(pathlib.Path('src/sage_poc/skills/grief_loss.json').read_text()); print('valid')"
```

Expected: `valid`

- [ ] **Step 3: Commit**

```bash
git add src/sage_poc/skills/grief_loss.json
git commit -m "fix(grief_loss): remove ambiguous keywords that could misroute non-bereavement presentations

Removed:
- 'مفقود إنسان عزيز' (means missing/unaccounted-for, not deceased — could route
  active missing-person situations into grief processing)
- 'I miss them so much' / 'they're gone' (match estrangement, travel, breakups)
- 'مبتدر العزاء' (obscure MSA, no Khaleeji user would produce this)

Added standard Gulf Arabic bereavement expressions (الله يرحمه/ها) and 'passed away'.

Confirmed finding S9a from 2026-06-05 code audit."
```

---

## Architecture Backlog Items (post-Gitex, not implemented here)

The following items are confirmed architectural gaps from the audit. They require planning and clinical/engineering coordination beyond the pre-Gitex window. File these as tracked issues before closing this plan.

### Backlog Item 1 (S15): Rules Service priority field for Tier 1 disambiguation

**Current state:** `skill_select.py` Tier 1 iterates `SKILL_REGISTRY` in list order and returns on the first keyword match. This means disambiguation priority is determined by `skill_ids.py` list position — a code constant, not a clinician-editable rule. This violates v7 Cardinal Rule 2 ("skills are policies, not code").

**Proper fix:** Add a `tier1_priority: int` field (or `specificity: int`) to each skill's matching rules in the Rules Service. `skill_select` should sort keyword matches by specificity before returning. Ties default to current registry order.

**Pre-Gitex stopgap already applied:** removed `"mind wont stop"` from `sleep_hygiene` (Task 11).

**File as:** `chore(backlog): S15 — Rules Service priority field for Tier 1 keyword disambiguation`

### Backlog Item 2 (R1): Language-tagged matching rules in Rules Service

**Current state:** Task 9 added a raw-message Arabic Tier 1 pass hardcoded in `skill_select.py`. This is a stopgap — it adds language-branching logic to the node itself, which will need updating if a third language is added.

**Proper fix:** Tag each keyword in the Rules Service with a `language` field (`"en"`, `"ar"`, `"*"`). `skill_select` evaluates each keyword against the appropriate message field per its language tag, removing the hardcoded `detected_language == "ar"` branch.

**File as:** `chore(backlog): R1 — language-tagged matching rules in Rules Service`

### Backlog Item 3: mood_score signal extraction

**Current state:** Task 5 replaced the dead `mood_score` signal with an `emotional_intensity <= 3` proxy. This is imprecise — a flat-affect user saying "my mood is 2/10" may not produce a low `emotional_intensity` score.

**Proper fix:** Add `mood_score` to `evaluate_step_policy`'s signals dict by extracting the integer from the user's message when the active step is `score_mood` (regex: `\b([1-9]|10)\b` in a mood-check context). Wire `"mood_score"` into `_KNOWN_STEP_POLICY_SIGNALS`.

**File as:** `chore(backlog): mood_score signal extraction for mood_check_in clinical hold`

---

## Pre-Gitex Completion Checklist

Before any user exposure:

- [ ] Task 1 complete: post_crisis_check_in L1 includes crisis line + door-open
- [ ] Task 2 complete: stop_technique authoring meta-note removed
- [ ] Task 3 complete: box_breathing dead signals and 4-7-8 removed
- [ ] Task 4 complete: financial_anxiety dead signal deleted, crisis phrases added
- [ ] Task 5 complete: mood_check_in dead signal replaced, overbroad keywords removed
- [ ] Task 6 complete: worry_time dead OCD signal removed, contraindication added
- [ ] Task 7 complete: all 17 remaining dead signals removed (count = 0)
- [ ] Task 8 complete: signals gate flipped to RuntimeError, test_no_dead_step_policy_signals passes
- [ ] Task 9 complete: Arabic Tier 1 raw-message pass in skill_select
- [ ] Task 10 complete: Arabic examples at [0] in all 74 steps, CI guard passes
- [ ] Task 11 complete: sleep_hygiene overbroad keywords fixed
- [ ] Task 12 + 13 complete: cbt_thought_record and interpersonal_effectiveness trimmed
- [ ] Task 14 complete: calibrate_threshold.py re-run, gap >= 0.03 verified
- [ ] Task 15 complete: grief_loss ambiguous keywords replaced
- [ ] All backlog items filed as tracked issues
