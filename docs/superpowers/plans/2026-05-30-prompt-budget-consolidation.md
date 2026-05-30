# Tier 3 Prompt Budget Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Count skill cultural_overrides words against the L1 history budget so the LLM's conversation history is proactively sized rather than reactively shrunk by the overflow guard.

**Architecture:** `_compute_l1_budget` currently ignores how much system prompt has been assembled — it returns 450 or 600 regardless of cultural_overrides size. The fix adds an `override_words` parameter to that function (defaulting to 0, backward-compatible) and captures the actual injected word count in `compose_prompt` to pass through. A `_L1_MINIMUM_BUDGET = 150` floor prevents the budget from dropping to near-zero on verbose override turns (e.g. `assertive_communication` at 445 words). The overflow-shrink path at the end of `compose_prompt` becomes a true safety net rather than the primary mechanism.

**Tech Stack:** Python 3.14, pytest. No new dependencies.

---

## Context for the implementer

The composer builds prompts in two roles. System role: L0 (persona) + global cultural rules + skill cultural_overrides + clinical adaptations. User role: L1 (conversation history) + L2 (intent framing) + L5 (user context) + L3/L4 (skill/knowledge) + current user message.

All combined must fit `_TOTAL_WORD_BUDGET = 1100` words. The overflow guard at the bottom of `compose_prompt` detects violations and shrinks L1 history to a half-window with 300 words. The problem: `_compute_l1_budget` (which sets how many words L1 can use _before_ it is built) ignores the cultural_overrides word count, so on a verbose override turn (e.g. 445 words for `assertive_communication`), L1 is allocated 450 words, the total exceeds 1100, and the guard silently cuts history to 1–2 turns.

The fix is two lines of implementation code and a constant. Everything else is tests and the minimum floor logic.

---

## File Structure

**Modify only:**
- `src/sage_poc/prompts/composer.py:92-93` — add `_L1_MINIMUM_BUDGET = 150` constant
- `src/sage_poc/prompts/composer.py:104-121` — `_compute_l1_budget` signature + return
- `src/sage_poc/prompts/composer.py:347-367` — cultural_overrides block: capture `_override_words`
- `src/sage_poc/prompts/composer.py:398` — pass `override_words=_override_words` to `_compute_l1_budget`
- `tests/test_prompts_composer.py` — new tests appended (no existing tests modified)

---

## Task 1: Extend `_compute_l1_budget` to accept and apply override_words

**Files:**
- Modify: `src/sage_poc/prompts/composer.py:92-121`
- Test: `tests/test_prompts_composer.py`

- [ ] **Step 1: Write the four failing unit tests**

Append to `tests/test_prompts_composer.py`:

```python
# ---- _compute_l1_budget override_words tests ----

from sage_poc.prompts.composer import _compute_l1_budget


def _skill_state(**overrides):
    """State with a skill step active (base L1 = 450)."""
    return _make_composer_state(
        step_instruction="Check how the user is feeling",
        active_skill_id="post_crisis_check_in",
        **overrides,
    )


def _freeflow_state(**overrides):
    """State with no skill or knowledge (base L1 = 600)."""
    return _make_composer_state(
        step_instruction=None,
        active_skill_id=None,
        primary_intent="general_chat",
        **overrides,
    )


def test_compute_l1_budget_unaffected_without_overrides():
    """With no override words, budget is the normal base (450 for skill turn)."""
    assert _compute_l1_budget(_skill_state(), override_words=0) == 450


def test_compute_l1_budget_subtracts_override_words():
    """200-word override on a skill turn: 450 - 200 = 250."""
    assert _compute_l1_budget(_skill_state(), override_words=200) == 250


def test_compute_l1_budget_floors_at_minimum():
    """445-word override on a 450-base skill turn: max(150, 450-445) = 150."""
    assert _compute_l1_budget(_skill_state(), override_words=445) == 150


def test_compute_l1_budget_freeflow_base_also_reduced():
    """Freeflow base is 600. 200-word override: 600 - 200 = 400."""
    assert _compute_l1_budget(_freeflow_state(), override_words=200) == 400
```

- [ ] **Step 2: Run to confirm all four fail**

```bash
pytest tests/test_prompts_composer.py -k "compute_l1_budget" -v
```

Expected: 4 failures — `TypeError: _compute_l1_budget() got an unexpected keyword argument 'override_words'`

- [ ] **Step 3: Add `_L1_MINIMUM_BUDGET` constant and update `_compute_l1_budget`**

In `src/sage_poc/prompts/composer.py`, add the constant immediately after `_L1_FLEX_BUDGET = 600` (line 93):

```python
_L1_BASE_BUDGET = 450
_L1_FLEX_BUDGET = 600
_L1_MINIMUM_BUDGET = 150  # floor when cultural overrides consume most of the headroom
```

Replace the body of `_compute_l1_budget` (currently lines 104–121):

```python
def _compute_l1_budget(state: SageState, override_words: int = 0) -> int:
    """Return the L1 word budget for this turn.

    On freeflow turns (no skill step, no knowledge lookup), L3 and L4 layers
    are absent. Their unused budget headroom is loaned to L1 so that rich
    multi-turn disclosures don't get truncated.

    override_words: actual word count of the skill cultural_overrides block
        injected into the system prompt this turn. Subtracted from base so L1
        is proactively sized rather than shrunk reactively by the overflow guard.

    POC note: `primary_intent == "info_request"` is a conservative proxy for
    "knowledge will be retrieved." In production, this should check whether
    skill_select routed to knowledge_retrieve rather than relying on intent
    classification alone. The proxy is safe (it keeps L1 at 450 when knowledge
    might be present), but may under-flex on edge cases where info_request
    intent is classified but no snippet is found.
    """
    has_skill = bool(state.get("step_instruction"))
    has_knowledge = state.get("primary_intent") == "info_request" or \
                    state.get("secondary_intent") == "info_request"
    base = _L1_BASE_BUDGET if (has_skill or has_knowledge) else _L1_FLEX_BUDGET
    return max(_L1_MINIMUM_BUDGET, base - override_words)
```

- [ ] **Step 4: Run tests — all four must pass**

```bash
pytest tests/test_prompts_composer.py -k "compute_l1_budget" -v
```

Expected: 4 passed.

- [ ] **Step 5: Run full composer suite — no regressions**

```bash
pytest tests/test_prompts_composer.py -v
```

Expected: all previously passing tests still pass (the new `override_words=0` default means existing callers are unaffected).

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/prompts/composer.py tests/test_prompts_composer.py
git commit -m "feat(composer): add override_words to _compute_l1_budget; floor at 150"
```

---

## Task 2: Wire override_words from compose_prompt into _compute_l1_budget

**Files:**
- Modify: `src/sage_poc/prompts/composer.py:347-367` (cultural_overrides block), `composer.py:398` (l1_budget call)
- Test: `tests/test_prompts_composer.py`

- [ ] **Step 1: Write the two failing integration tests**

Append to `tests/test_prompts_composer.py`:

```python
# ---- override_words wired into _compute_l1_budget ----

from unittest.mock import patch, MagicMock, call as mock_call
from sage_poc.prompts import composer as _composer_module


def _skill_with_200w_overrides() -> Skill:
    text = "Follow Gulf cultural norms carefully in all responses. " * 4  # ~40w per entry
    return _make_skill_with_overrides(overrides={
        "entry_a": text,
        "entry_b": text,
        "entry_c": text,
    })


def test_compose_prompt_passes_override_words_to_l1_budget():
    """compose_prompt must pass the actual injected override word count to _compute_l1_budget."""
    skill = _skill_with_200w_overrides()
    state = _make_composer_state(
        active_skill_id="post_crisis_check_in",
        step_instruction="Check in with user",
    )

    with (
        patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules_mock()),
        patch("sage_poc.prompts.composer.load_skill", return_value=skill),
        patch(
            "sage_poc.prompts.composer._compute_l1_budget",
            wraps=_composer_module._compute_l1_budget,
        ) as mock_budget,
    ):
        compose_prompt(state)

    mock_budget.assert_called_once()
    _, kwargs = mock_budget.call_args
    assert kwargs.get("override_words", 0) > 0, (
        "_compute_l1_budget must receive override_words > 0 when overrides are injected; "
        f"got: {kwargs}"
    )


def test_compose_prompt_passes_zero_override_words_when_no_active_skill():
    """When no skill is active, override_words must be 0 (budget not reduced)."""
    state = _make_composer_state(active_skill_id=None)

    with (
        patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules_mock()),
        patch(
            "sage_poc.prompts.composer._compute_l1_budget",
            wraps=_composer_module._compute_l1_budget,
        ) as mock_budget,
    ):
        compose_prompt(state)

    _, kwargs = mock_budget.call_args
    assert kwargs.get("override_words", 0) == 0, (
        "_compute_l1_budget must receive override_words=0 when no skill is active; "
        f"got: {kwargs}"
    )
```

- [ ] **Step 2: Run to confirm both fail**

```bash
pytest tests/test_prompts_composer.py -k "passes_override_words" -v
```

Expected: 2 failures — `AssertionError: _compute_l1_budget must receive override_words > 0` (because the current call uses no kwargs).

- [ ] **Step 3: Capture `_override_words` in the cultural_overrides block**

In `src/sage_poc/prompts/composer.py`, replace the cultural_overrides block (currently lines 347–367):

```python
    # Skill-specific cultural overrides — more specific than global rules; injected after them.
    # _override_words is captured here so _compute_l1_budget can proactively reduce L1 budget.
    _override_words = 0
    _active_for_overrides = state.get("active_skill_id")
    if _active_for_overrides:
        try:
            _override_skill = load_skill(_active_for_overrides)
            if _override_skill.cultural_overrides:
                _override_lines = "\n".join(
                    f"- {v}" for v in _override_skill.cultural_overrides.values()
                )
                _override_block = f"SKILL-SPECIFIC CULTURAL CONTEXT:\n{_override_lines}"
                if count_words(_override_block) <= _CULTURAL_OVERRIDE_BUDGET_WORDS:
                    _override_words = count_words(_override_block)
                    system_parts.append(_override_block)
                    layers.append("cultural_skill_overrides")  # only when actually injected
                else:
                    _log.warning(
                        "cultural_overrides exceeds budget for %s", _active_for_overrides
                    )
                    # Block not injected; no layer tag — audit trail must reflect reality
        except Exception as exc:
            _log.warning("cultural_overrides load failed for %s: %s", _active_for_overrides, exc)
```

- [ ] **Step 4: Pass `override_words` to `_compute_l1_budget`**

In `src/sage_poc/prompts/composer.py`, find the line (currently ~398):

```python
    l1_budget = _compute_l1_budget(state)
```

Replace with:

```python
    l1_budget = _compute_l1_budget(state, override_words=_override_words)
```

- [ ] **Step 5: Run the two integration tests — both must pass**

```bash
pytest tests/test_prompts_composer.py -k "passes_override_words" -v
```

Expected: 2 passed.

- [ ] **Step 6: Run full composer suite and cross-concern suite**

```bash
pytest tests/test_prompts_composer.py tests/test_cultural_overrides_cross_concern.py -v
```

Expected: all pass. In particular, the existing `test_cultural_overrides_budget_exceeded_does_not_append_layer_tag` still passes (overflow path unchanged), and the cross-concern tests still pass (no regression in stale-skill or crisis-monitoring paths).

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/prompts/composer.py tests/test_prompts_composer.py
git commit -m "fix(composer): wire cultural_overrides words into L1 budget; eliminates reactive overflow shrink"
```

---

## Task 3: Update conformance.py note and verify conformance tests

**Files:**
- Modify: `src/sage_poc/skills/conformance.py:54-57` — update `skill.cultural_overrides` note
- Test: `tests/test_schema_conformance.py`

The conformance registry documents how each field is used at runtime. The `skill.cultural_overrides` note should reflect that the budget is now wired into the L1 budget calculation.

- [ ] **Step 1: Update the conformance note**

In `src/sage_poc/skills/conformance.py`, replace the `skill.cultural_overrides` note:

```python
    "skill.cultural_overrides": {
        "status": "USED",
        "injected_by": "compose_prompt (system role, SKILL-SPECIFIC CULTURAL CONTEXT block)",
        "note": (
            "All key-value pairs injected into the system prompt after global cultural rules, "
            "within a 500-word budget. Active on every turn where active_skill_id is set. "
            "The injected word count is passed to _compute_l1_budget so L1 history is "
            "proactively sized — not reactively shrunk — when overrides are verbose."
        ),
    },
```

- [ ] **Step 2: Run conformance tests**

```bash
pytest tests/test_schema_conformance.py -k "not endpoint" -v
```

Expected: 10 passed. The note change does not affect any assertion (tests check status and injected_by, not the note text).

- [ ] **Step 3: Commit**

```bash
git add src/sage_poc/skills/conformance.py
git commit -m "docs(conformance): note that cultural_overrides word count feeds L1 budget"
```

---

## Self-Review

**1. Spec coverage:**
- `_compute_l1_budget` updated: ✓ Task 1
- `compose_prompt` wires `_override_words`: ✓ Task 2
- Minimum floor (150w) prevents near-zero L1: ✓ Task 1 Step 3
- Conformance note updated: ✓ Task 3
- All existing tests still pass: ✓ Tasks 1 and 2 Step 5/6
- Overflow-shrink path unchanged (still fires as safety net): ✓ not removed, just fires less

**2. Placeholder scan:** None found. All code blocks are complete and exact.

**3. Type consistency:**
- `_compute_l1_budget(state: SageState, override_words: int = 0) -> int` — consistent across Task 1 definition and Task 2 call site.
- `_override_words` is `int` throughout (initialized to `0`, assigned `count_words(...)` which returns `int`).
- `_L1_MINIMUM_BUDGET` introduced in Task 1 Step 3 and used in same step — no forward reference.
