# Skill Intelligence & Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the skill activation null-match bug (RT-4), add two new evidence-based skills (grounding 5-4-3-2-1 and sleep hygiene), and extend step_policy test coverage.

**Architecture:** RT-4 is a one-line JSON fix in `cbt_thought_record.json`. New skills are standalone JSON files registered in `skill_select.py::SKILL_REGISTRY`. The `Skill` Pydantic schema in `skills/schema.py` already validates all required fields — new skills must conform to it exactly. No graph changes.

**Tech Stack:** Python 3.12, pytest, Pydantic v2, JSON skill files.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `src/sage_poc/skills/cbt_thought_record.json` | Modify | Add "my fault", "blame myself" to target_presentations (RT-4) |
| `src/sage_poc/skills/grounding_5_4_3_2_1.json` | Create | 5-step sensory grounding skill (DBT) |
| `src/sage_poc/skills/sleep_hygiene.json` | Create | Sleep psychoeducation skill (3-step) |
| `src/sage_poc/nodes/skill_select.py` | Modify | Register new skills in SKILL_REGISTRY |
| `tests/test_nodes.py` | Modify | RT-4 test, new skill activation tests, step_policy extension tests |

---

### Task 1: RT-4 — Fix skill_select null-match for "my fault"

**Context:** `skill_select_node` does `keyword.lower() in message.lower()` substring matching against `skill.target_presentations`. The phrase "everything is my fault, always" fails to activate CBT because `"always my fault"` (the existing keyword) is not a substring of "everything is my fault" — the word order differs. Adding `"my fault"` as a separate shorter keyword fixes this. Add `"blame myself"` as a bonus catch for that phrasing pattern.

**Files:**
- Modify: `src/sage_poc/skills/cbt_thought_record.json:7`
- Test: `tests/test_nodes.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_nodes.py` after `test_no_skill_for_general_chat`:

```python
def test_selects_cbt_for_my_fault_phrasing():
    """RT-4: 'everything is my fault' must activate CBT — 'my fault' substring fix."""
    state = make_state(
        message_en="I keep thinking everything is my fault, always",
        primary_intent="new_skill",
    )
    result = skill_select_node(state)
    assert result["active_skill_id"] == "cbt_thought_record", \
        "RT-4: 'my fault' phrasing must activate cbt_thought_record"
    assert result["active_step_id"] == "identify_thought"


def test_selects_cbt_for_blame_myself():
    """'I always blame myself for everything' must activate CBT via 'blame myself' keyword."""
    state = make_state(
        message_en="I always blame myself for everything that goes wrong",
        primary_intent="new_skill",
    )
    result = skill_select_node(state)
    assert result["active_skill_id"] == "cbt_thought_record", \
        "'blame myself' must activate cbt_thought_record"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_nodes.py::test_selects_cbt_for_my_fault_phrasing tests/test_nodes.py::test_selects_cbt_for_blame_myself -v
```

Expected: FAIL — `AssertionError: RT-4: 'my fault' phrasing must activate cbt_thought_record`

- [ ] **Step 3: Add keywords to cbt_thought_record.json**

In `src/sage_poc/skills/cbt_thought_record.json`, find `"target_presentations"` and add `"my fault"` and `"blame myself"`:

```json
"target_presentations": [
  "negative thoughts", "self-blame", "cognitive distortions",
  "catastrophizing", "failure", "worthless", "always my fault",
  "my fault", "blame myself"
],
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_nodes.py::test_selects_cbt_for_my_fault_phrasing tests/test_nodes.py::test_selects_cbt_for_blame_myself tests/test_nodes.py::test_selects_cbt_for_negative_thought -v
```

Expected: PASS ×3 (including the existing test that must not regress).

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/skills/cbt_thought_record.json tests/test_nodes.py
git commit -m "fix(skill-select): add 'my fault' and 'blame myself' to CBT target_presentations (RT-4)"
```

---

### Task 2: S-1a — Create grounding 5-4-3-2-1 skill

**Context:** The `Skill` Pydantic schema requires: `skill_id`, `skill_name`, `skill_type`, `evidence_base`, `target_presentations` (list of strings), `steps` (list of SkillStep), `step_policy` (list of StepPolicyRule), `escalation_matrix` (dict). Each `SkillStep` needs: `step_id`, `goal`, `technique`, `tone`, `examples` (list of strings, min 2). Each `StepPolicyRule` needs: `condition` (with `signal`, `operator`, `value`, `step`), `action`, `instruction`, `next_step_id`.

The 5-4-3-2-1 grounding technique is a DBT sensory grounding exercise: 5 things you see → 4 you can touch → 3 you hear → 2 you smell → 1 you taste. Used for anxiety, panic, dissociation.

**Files:**
- Create: `src/sage_poc/skills/grounding_5_4_3_2_1.json`
- Modify: `src/sage_poc/nodes/skill_select.py` (SKILL_REGISTRY)
- Test: `tests/test_nodes.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_nodes.py`:

```python
def test_grounding_skill_schema_is_valid():
    """grounding_5_4_3_2_1 JSON must load and validate against Skill schema."""
    from sage_poc.skills.schema import load_skill
    skill = load_skill("grounding_5_4_3_2_1")
    assert skill.skill_id == "grounding_5_4_3_2_1"
    assert len(skill.steps) == 5  # 5-4-3-2-1 has 5 sense steps
    assert len(skill.target_presentations) >= 3
    # Confirm schema integrity
    assert all(len(s.examples) >= 2 for s in skill.steps)


def test_selects_grounding_for_panic_phrasing():
    """'I'm having a panic attack' must activate grounding skill."""
    state = make_state(
        message_en="I'm having a panic attack right now, I can't breathe",
        primary_intent="new_skill",
    )
    result = skill_select_node(state)
    assert result["active_skill_id"] == "grounding_5_4_3_2_1", \
        "Panic attack phrasing must activate grounding skill"
    assert result["active_step_id"] == "see_5"


def test_selects_grounding_for_overwhelmed_phrasing():
    """'I feel completely overwhelmed' must activate grounding skill."""
    state = make_state(
        message_en="I feel completely overwhelmed, my head is spinning",
        primary_intent="new_skill",
    )
    result = skill_select_node(state)
    assert result["active_skill_id"] == "grounding_5_4_3_2_1"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_nodes.py::test_grounding_skill_schema_is_valid tests/test_nodes.py::test_selects_grounding_for_panic_phrasing -v
```

Expected: FAIL — `FileNotFoundError` (JSON not yet created).

- [ ] **Step 3: Create the skill JSON**

Create `src/sage_poc/skills/grounding_5_4_3_2_1.json`:

```json
{
  "skill_id": "grounding_5_4_3_2_1",
  "skill_name": "5-4-3-2-1 Grounding",
  "skill_type": "structured",
  "evidence_base": "Linehan (1993); DBT Skills Training Manual",
  "target_presentations": [
    "panic attack", "panic", "overwhelmed", "dissociated", "dissociation",
    "can't breathe", "heart racing", "spinning", "grounding", "anxious right now",
    "anxiety attack", "feel disconnected", "not real", "losing control"
  ],
  "steps": [
    {
      "step_id": "see_5",
      "goal": "Anchor the user in their environment by naming 5 things they can see",
      "technique": "Sensory grounding — sight",
      "tone": "calm, slow, gently directive",
      "examples": [
        "Let's slow things down together. Can you look around and tell me five things you can see right now — anything at all?",
        "I'm right here with you. Start simple — what are five things your eyes can land on in this moment?"
      ]
    },
    {
      "step_id": "touch_4",
      "goal": "Deepen physical grounding by naming 4 things the user can physically feel",
      "technique": "Sensory grounding — touch",
      "tone": "calm, reassuring, present",
      "examples": [
        "Good. Now — four things you can physically feel or touch. Maybe the surface under you, your clothes, the temperature of the air.",
        "You're doing really well. Now notice four things you can feel with your hands or body right now."
      ]
    },
    {
      "step_id": "hear_3",
      "goal": "Shift attention to sound to further interrupt the panic cycle",
      "technique": "Sensory grounding — hearing",
      "tone": "calm, steady, unhurried",
      "examples": [
        "Three things you can hear. It might be something in the room, outside, even your own breathing.",
        "Listen carefully — what are three sounds you can make out right now, however faint?"
      ]
    },
    {
      "step_id": "smell_2",
      "goal": "Engage the olfactory sense to complete the sensory circuit",
      "technique": "Sensory grounding — smell",
      "tone": "gentle, exploratory",
      "examples": [
        "Two things you can smell. If nothing comes to mind, you can get up and smell something nearby — coffee, a book, your clothes.",
        "Can you notice two smells? Even very subtle ones count."
      ]
    },
    {
      "step_id": "taste_1",
      "goal": "Complete the 5-4-3-2-1 sequence and check in on the user's state",
      "technique": "Sensory grounding — taste / integration",
      "tone": "warm, encouraging, checking in",
      "examples": [
        "Last one — one thing you can taste. Even if it's just the inside of your mouth. Then take a slow breath and tell me how you're feeling now.",
        "One taste — and then let's pause and take a breath together. How are you feeling compared to when we started?"
      ]
    }
  ],
  "step_policy": [
    {
      "condition": {
        "signal": "emotional_intensity",
        "operator": ">",
        "value": 8,
        "step": "ANY"
      },
      "action": "validate_only",
      "instruction": "The user is in acute distress. Do NOT advance the exercise. Slow down, validate, and stay present. Repeat the current step's prompt in simpler language next turn.",
      "next_step_id": "current"
    },
    {
      "condition": {
        "signal": "engagement",
        "operator": "<",
        "value": 3,
        "step": "ANY"
      },
      "action": "check_in",
      "instruction": "The user seems disengaged or unable to focus. Gently check in — is this exercise helping? Would they prefer to just breathe together or talk?",
      "next_step_id": "current"
    }
  ],
  "escalation_matrix": {
    "L1": "Exit skill gracefully if user requests to stop — grounding is voluntary",
    "L2": "Add clinician_review flag if trauma or substance mention detected during exercise",
    "L3": "Exit immediately to crisis protocol if any crisis signal",
    "L4": "Trigger human handoff if 3+ crises detected in last 30 days"
  }
}
```

- [ ] **Step 4: Register the skill in skill_select.py**

In `src/sage_poc/nodes/skill_select.py`, update `SKILL_REGISTRY`:

```python
SKILL_REGISTRY = ["cbt_thought_record", "grounding_5_4_3_2_1"]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_nodes.py::test_grounding_skill_schema_is_valid tests/test_nodes.py::test_selects_grounding_for_panic_phrasing tests/test_nodes.py::test_selects_grounding_for_overwhelmed_phrasing -v
```

Expected: PASS ×3.

- [ ] **Step 6: Run full fast test suite (regression check)**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_nodes.py -v -m "not slow"
```

Expected: all pass. Watch for `test_no_skill_for_general_chat` — "weather" must still return None.

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/skills/grounding_5_4_3_2_1.json src/sage_poc/nodes/skill_select.py tests/test_nodes.py
git commit -m "feat(skills): add 5-4-3-2-1 grounding skill and register in SKILL_REGISTRY (S-1a)"
```

---

### Task 3: S-1b — Create sleep hygiene skill

**Context:** Sleep psychoeducation is a standalone 3-step skill: assess sleep pattern → provide evidence-based sleep hygiene guidance → reflect on barriers and next steps. Target presentations: sleep complaints, insomnia, can't sleep. Uses motivational interviewing tone (not prescriptive).

**Files:**
- Create: `src/sage_poc/skills/sleep_hygiene.json`
- Modify: `src/sage_poc/nodes/skill_select.py` (SKILL_REGISTRY)
- Test: `tests/test_nodes.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_nodes.py`:

```python
def test_sleep_hygiene_skill_schema_is_valid():
    """sleep_hygiene JSON must load and validate against Skill schema."""
    from sage_poc.skills.schema import load_skill
    skill = load_skill("sleep_hygiene")
    assert skill.skill_id == "sleep_hygiene"
    assert len(skill.steps) == 3
    assert len(skill.target_presentations) >= 3
    assert all(len(s.examples) >= 2 for s in skill.steps)


def test_selects_sleep_hygiene_for_insomnia_phrasing():
    """'I can't sleep at night' must activate sleep_hygiene skill."""
    state = make_state(
        message_en="I can't sleep at night, I lie awake for hours",
        primary_intent="new_skill",
    )
    result = skill_select_node(state)
    assert result["active_skill_id"] == "sleep_hygiene", \
        "'can't sleep' phrasing must activate sleep_hygiene skill"
    assert result["active_step_id"] == "assess_sleep"


def test_selects_sleep_hygiene_for_insomnia_keyword():
    """'I have insomnia' must activate sleep_hygiene skill."""
    state = make_state(
        message_en="I've been struggling with insomnia for months",
        primary_intent="new_skill",
    )
    result = skill_select_node(state)
    assert result["active_skill_id"] == "sleep_hygiene"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_nodes.py::test_sleep_hygiene_skill_schema_is_valid tests/test_nodes.py::test_selects_sleep_hygiene_for_insomnia_phrasing -v
```

Expected: FAIL — `FileNotFoundError`.

- [ ] **Step 3: Create the skill JSON**

Create `src/sage_poc/skills/sleep_hygiene.json`:

```json
{
  "skill_id": "sleep_hygiene",
  "skill_name": "Sleep Hygiene",
  "skill_type": "psychoeducation",
  "evidence_base": "Walker (2017); NHS Sleep Hygiene Guidelines; CBT-I principles",
  "target_presentations": [
    "can't sleep", "insomnia", "sleep problems", "sleeping badly",
    "lie awake", "lying awake", "sleep issues", "trouble sleeping",
    "not sleeping", "poor sleep", "sleep deprived", "no sleep",
    "waking up", "can't fall asleep"
  ],
  "steps": [
    {
      "step_id": "assess_sleep",
      "goal": "Understand the user's specific sleep pattern and what's most disruptive",
      "technique": "Collaborative assessment — open questions",
      "tone": "curious, warm, non-judgmental",
      "examples": [
        "Tell me more about your sleep — is it hard to fall asleep, or do you wake up and can't get back to sleep, or both?",
        "How long has this been going on? And what does a typical night look like for you — walk me through it."
      ]
    },
    {
      "step_id": "share_guidance",
      "goal": "Share 2-3 evidence-based sleep hygiene principles most relevant to what the user described",
      "technique": "Psychoeducation with motivational framing",
      "tone": "informative but conversational — not prescriptive or preachy",
      "examples": [
        "One thing that really helps a lot of people is keeping the same wake-up time every day — even weekends. It anchors your body clock. Does that feel possible for you?",
        "Screens before bed are sneaky — the blue light delays melatonin. Even dimming your phone or switching to a reading app can make a difference. Is that something you'd try?"
      ]
    },
    {
      "step_id": "barriers_and_next_step",
      "goal": "Identify one realistic change the user is willing to try this week, and acknowledge barriers",
      "technique": "Motivational interviewing — change talk",
      "tone": "collaborative, realistic, encouraging",
      "examples": [
        "Out of everything we talked about — what's one small thing that feels doable this week? Even if it's tiny.",
        "What's the biggest thing getting in the way of better sleep for you? Sometimes knowing the barrier is more useful than any tip."
      ]
    }
  ],
  "step_policy": [
    {
      "condition": {
        "signal": "emotional_intensity",
        "operator": ">",
        "value": 7,
        "step": "ANY"
      },
      "action": "validate_only",
      "instruction": "The user is highly distressed. Do not proceed with sleep information. Validate the exhaustion and emotional weight first. Return to assessment next turn.",
      "next_step_id": "current"
    },
    {
      "condition": {
        "signal": "engagement",
        "operator": "<",
        "value": 3,
        "step": "ANY"
      },
      "action": "check_in",
      "instruction": "User seems disengaged. Check in — is talking about sleep helpful right now, or would they prefer emotional support instead?",
      "next_step_id": "current"
    }
  ],
  "escalation_matrix": {
    "L1": "Exit skill gracefully if user requests to stop",
    "L2": "Add clinician_review flag if medication mention detected (e.g. sleeping pills dosage)",
    "L3": "Exit immediately to crisis protocol if any crisis signal",
    "L4": "Trigger human handoff if 3+ crises detected in last 30 days"
  }
}
```

- [ ] **Step 4: Register the skill in skill_select.py**

In `src/sage_poc/nodes/skill_select.py`, update `SKILL_REGISTRY`:

```python
SKILL_REGISTRY = ["cbt_thought_record", "grounding_5_4_3_2_1", "sleep_hygiene"]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_nodes.py::test_sleep_hygiene_skill_schema_is_valid tests/test_nodes.py::test_selects_sleep_hygiene_for_insomnia_phrasing tests/test_nodes.py::test_selects_sleep_hygiene_for_insomnia_keyword -v
```

Expected: PASS ×3.

- [ ] **Step 6: Run full fast test suite**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_nodes.py -v -m "not slow"
```

Watch especially: `test_no_skill_for_general_chat` ("weather" must still return None), `test_selects_cbt_for_negative_thought` (CBT must still activate on "failure, always my fault").

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/skills/sleep_hygiene.json src/sage_poc/nodes/skill_select.py tests/test_nodes.py
git commit -m "feat(skills): add sleep hygiene skill and register in SKILL_REGISTRY (S-1b)"
```

---

### Task 4: S-2 — Extend step_policy tests

**Context:** The existing step_policy tests cover high-intensity (validate_only), low-engagement (check_in), advancement, and completion. What's missing: tests for the grounding and sleep_hygiene skills' step_policy rules (they use the same signals but different threshold values — intensity >8 for grounding vs >7 for sleep). Also missing: a test confirming the grounding skill's 5-step sequence advances correctly through all 5 steps.

**Files:**
- Test: `tests/test_nodes.py`

- [ ] **Step 1: Write the failing tests**

Add after the existing step_policy tests:

```python
# S-2: Extended step_policy tests for new skills

def test_grounding_high_intensity_triggers_validate_only():
    """Grounding skill: intensity > 8 triggers validate_only (threshold is 8, not 7)."""
    from sage_poc.skills.schema import load_skill
    skill = load_skill("grounding_5_4_3_2_1")
    result = evaluate_step_policy(
        skill=skill,
        current_step_id="see_5",
        emotional_intensity=9,
        engagement=6,
    )
    assert result["action"] == "validate_only"
    assert result["next_step_id"] == "see_5"  # held in place


def test_grounding_intensity_8_does_not_trigger_validate_only():
    """Grounding skill: intensity == 8 does NOT trigger validate_only (operator is >, not >=)."""
    from sage_poc.skills.schema import load_skill
    skill = load_skill("grounding_5_4_3_2_1")
    result = evaluate_step_policy(
        skill=skill,
        current_step_id="see_5",
        emotional_intensity=8,
        engagement=7,
        message_en="I can see my desk, my lamp, my hands, the window, and the door.",
    )
    # Should advance (intensity == 8 does not satisfy > 8)
    assert result["action"] == "advance"
    assert result["next_step_id"] == "touch_4"


def test_grounding_skill_advances_through_all_5_steps():
    """Grounding skill: 5 sequential advances from see_5 → touch_4 → hear_3 → smell_2 → taste_1 → complete."""
    from sage_poc.skills.schema import load_skill
    skill = load_skill("grounding_5_4_3_2_1")
    step_sequence = ["see_5", "touch_4", "hear_3", "smell_2", "taste_1"]
    expected_next = ["touch_4", "hear_3", "smell_2", "taste_1", None]
    long_response = "I can describe many things I notice in my environment right now in detail."

    for step_id, expected_next_id in zip(step_sequence, expected_next):
        result = evaluate_step_policy(
            skill=skill,
            current_step_id=step_id,
            emotional_intensity=4,
            engagement=7,
            message_en=long_response,
        )
        if expected_next_id is None:
            assert result["action"] == "complete", \
                f"taste_1 must complete the skill; got action={result['action']!r}"
            assert result["skill_complete"] is True
        else:
            assert result["action"] == "advance", \
                f"Step {step_id} must advance; got action={result['action']!r}"
            assert result["next_step_id"] == expected_next_id, \
                f"After {step_id} expected {expected_next_id}, got {result['next_step_id']!r}"


def test_sleep_hygiene_advances_through_3_steps():
    """Sleep hygiene skill: 3 sequential advances from assess_sleep → share_guidance → barriers_and_next_step → complete."""
    from sage_poc.skills.schema import load_skill
    skill = load_skill("sleep_hygiene")
    step_sequence = ["assess_sleep", "share_guidance", "barriers_and_next_step"]
    expected_next = ["share_guidance", "barriers_and_next_step", None]
    long_response = "I have been struggling with sleep for a while and I notice many things about my routine that could improve."

    for step_id, expected_next_id in zip(step_sequence, expected_next):
        result = evaluate_step_policy(
            skill=skill,
            current_step_id=step_id,
            emotional_intensity=4,
            engagement=7,
            message_en=long_response,
        )
        if expected_next_id is None:
            assert result["action"] == "complete"
            assert result["skill_complete"] is True
        else:
            assert result["action"] == "advance"
            assert result["next_step_id"] == expected_next_id
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_nodes.py::test_grounding_high_intensity_triggers_validate_only tests/test_nodes.py::test_grounding_skill_advances_through_all_5_steps tests/test_nodes.py::test_sleep_hygiene_advances_through_3_steps -v
```

Expected: FAIL (grounding_5_4_3_2_1.json or sleep_hygiene.json not yet created — or, if Task 2/3 was completed first, these should fail due to missing test functions only).

- [ ] **Step 3: Run tests again after Tasks 2 and 3 complete**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_nodes.py::test_grounding_high_intensity_triggers_validate_only tests/test_nodes.py::test_grounding_intensity_8_does_not_trigger_validate_only tests/test_nodes.py::test_grounding_skill_advances_through_all_5_steps tests/test_nodes.py::test_sleep_hygiene_advances_through_3_steps -v
```

Expected: PASS ×4.

- [ ] **Step 4: Run full fast suite**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_nodes.py -v -m "not slow"
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_nodes.py
git commit -m "test(skills): add step_policy and sequence tests for grounding and sleep skills (S-2)"
```

---

## Self-Review Checklist

**Spec coverage:**
- RT-4 (skill_select null-match): Task 1 ✅
- S-1 (two new skills): Tasks 2 (grounding) and 3 (sleep hygiene) ✅
- S-2 (step_policy extension): Task 4 ✅

**What is NOT in scope:**
- Skill CMS / dynamic loading: SKILL_REGISTRY stays static
- Arabic translations of skill prompts: not in Tier 1 spec

**Placeholder scan:** None — all JSON has real content; all tests have real assertions.

**Type consistency:** `evaluate_step_policy` signature is `(skill, current_step_id, emotional_intensity, engagement, message_en="")` — all new tests use this signature correctly.

**Skill ordering concern:** `skill_select_node` returns the first matching skill. If a user says "I can't sleep and I feel overwhelmed", `grounding_5_4_3_2_1` may activate before `sleep_hygiene` because it appears first in SKILL_REGISTRY. This is acceptable for now — intent_route and clinical context provide the real selection signal in production.
