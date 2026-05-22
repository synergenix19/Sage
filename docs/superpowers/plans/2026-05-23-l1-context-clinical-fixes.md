# L1 Context Management & Clinical Signal Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate in-session context amnesia and close clinical signal gaps identified in the 2026-05-23 multi-turn conversation RCA (6 root causes → 6 targeted fixes).

**Architecture:** Three independent layers of change. Composer layer (Tasks 1–2): reverse L1 history iteration priority and increase the word budget with per-turn flex. Rules/Persona layer (Tasks 3–4): expand PI-EI-001 keyword set and add jargon guardrails to L0. Safety layer (Task 5): add missing test coverage for the existing `escalating_distress` mechanism and supplement it with engagement-decline tracking. Conversation summary layer (Task 6): implement the spec'd-but-unbuilt `summary_trigger`, adding a `summariser` module and state field, triggered from `output_gate` at turn 10.

**Tech Stack:** Python 3.11, pytest, LangGraph, OpenRouter via existing `get_classifier()` / `get_responder()`, JSON rule files

---

## Files Modified and Created

**Modified:**
- `src/sage_poc/prompts/composer.py` — Tasks 1, 2, 6d: L1 iteration, budget flex, summary integration
- `src/sage_poc/prompts/templates/L1_history.json` — Task 2: `word_budget` 300 → 450
- `src/sage_poc/prompts/templates/L0_persona.json` — Task 4: jargon anti-phrase constraint
- `src/sage_poc/rules/data/prompt_injection/expat_isolation.json` — Task 3: paraphrase keywords
- `src/sage_poc/state.py` — Task 6a: add `conversation_summary: Optional[str]` and `engagement_trajectory: list[int]`
- `src/sage_poc/nodes/safety_check.py` — Task 5b: engagement-decline supplement to escalating_distress
- `src/sage_poc/nodes/output_gate.py` — Task 6e: call summariser at turn 10
- `tests/test_prompts_composer.py` — Tasks 1, 2, 6
- `tests/test_nodes.py` — Task 5a

**Created:**
- `src/sage_poc/prompts/summarizer.py` — Task 6b

---

## Task 1 (P0): Reverse L1 History Iteration

**Root cause addressed:** RC-1 — `_build_l1_history_block` iterates oldest-to-newest within the 8-turn window and stops at the 300-word budget. Recent turns — exactly the context that just became relevant — are the first to be dropped.

**Fix:** Iterate newest-to-oldest; collect until budget is hit; reverse back to chronological order for the prompt. The oldest turn in the window is now the one that gets dropped under pressure, not the newest.

**Files:**
- Modify: `src/sage_poc/prompts/composer.py:192–211` (`_build_l1_history_block`)
- Modify: `tests/test_prompts_composer.py` (add new test; rename one existing test)

- [ ] **Step 1.1: Write the failing test**

Add at the bottom of the `_build_l1_history_block` test block in `tests/test_prompts_composer.py`:

```python
def test_l1_history_newest_turn_appears_when_budget_tight():
    """After Fix 1: the most recent message in the window survives truncation."""
    # 8 messages × ~57 words each ≈ 456 words > 300-word budget
    # Old iteration: markers 0–4 kept; marker7 (newest) dropped.
    # New iteration: markers 7–3 kept; marker0 (oldest) may be dropped.
    history = []
    for i in range(8):
        filler = " ".join(["filler"] * 54)
        history.append({
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"marker{i} {filler}",
        })
    block = _build_l1_history_block(history)
    assert block is not None
    assert "marker7" in block   # newest must always be present
```

- [ ] **Step 1.2: Run the failing test**

```
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_prompts_composer.py::test_l1_history_newest_turn_appears_when_budget_tight -v
```

Expected: **FAIL** — `marker7` is absent with the old iteration.

- [ ] **Step 1.3: Rename the now-misleading existing test**

In `tests/test_prompts_composer.py`, rename:

```python
# OLD:
def test_l1_history_always_includes_first_line_even_if_over_budget():

# NEW:
def test_l1_history_always_includes_newest_turn_even_if_over_budget():
```

- [ ] **Step 1.4: Implement the fix in composer.py**

In `src/sage_poc/prompts/composer.py`, replace the body of `_build_l1_history_block` starting at the window loop:

```python
def _build_l1_history_block(
    conversation_history: list[dict],
    variant: str | None = None,
) -> str | None:
    if not conversation_history:
        return None
    tmpl = get_template("L1_history", variant=variant)
    window_size = tmpl.window_size or 8
    word_budget = tmpl.word_budget or 300
    window = conversation_history[-window_size:]
    lines: list[str] = []
    word_total = 0
    for m in reversed(window):            # newest → oldest
        content = (
            _sanitize_assistant_turn(m["content"])
            if m["role"] == "assistant"
            else m["content"]
        )
        line = f"{m['role'].upper()}: {content}"
        words = count_words(line)
        if lines and word_total + words > word_budget:
            _log.debug("L1 history truncated at word budget %d", word_budget)
            break
        lines.append(line)
        word_total += words
    if not lines:
        return None
    lines.reverse()                       # restore chronological order for prompt
    history_text = _esc("\n".join(lines))
    content = tmpl.content.format(history_lines=history_text)
    _log.debug("L1_history@%s loaded", tmpl.version)
    return content
```

- [ ] **Step 1.5: Run the full L1 test block**

```
uv run pytest tests/test_prompts_composer.py -v -k "l1"
```

Expected: all L1 tests pass, including the new `test_l1_history_newest_turn_appears_when_budget_tight`.

- [ ] **Step 1.6: Run the full suite to check for regressions**

```
uv run pytest --tb=short -q
```

Expected: all tests pass.

- [ ] **Step 1.7: Commit**

```bash
git add src/sage_poc/prompts/composer.py tests/test_prompts_composer.py
git commit -m "fix(composer): reverse L1 history iteration to prioritise recency

Oldest turns now dropped first when budget is exceeded, not newest.
Fixes the primary cause of the repetitive-question failure (RCA RC-1)."
```

---

## Task 2 (P1): Word Budget Increase + Per-Turn Flex

**Root cause addressed:** RC-2 — the 300-word L1 budget is too small for Sage's persona, which invites rich multi-turn disclosure. Two normal turns saturate it, compounding Task 1's fix.

**Fix:** Raise the base budget from 300 to 450 words in `L1_history.json`. Add `_compute_l1_budget()` in `composer.py` that allows up to 600 words on freeflow turns (where L3 skill context and L4 knowledge are both absent) by borrowing from those layers' reserved budget headroom.

**Files:**
- Modify: `src/sage_poc/prompts/templates/L1_history.json`
- Modify: `src/sage_poc/prompts/composer.py` (new helper + updated call sites)
- Modify: `tests/test_prompts_composer.py` (update one existing test; add two new tests)

- [ ] **Step 2.1: Update the existing budget test to survive the budget increase**

The test `test_l1_history_respects_word_budget_for_subsequent_lines` uses 60-word messages × 6 entries ≈ 372 words — which fits in the new 450-word budget. Update it so truncation still occurs:

```python
def test_l1_history_respects_word_budget_for_subsequent_lines():
    long_content = " ".join(["word"] * 90)  # ~90 words × 6 entries = ~540 words > 450 budget
    history = [{"role": "user", "content": long_content} for _ in range(6)]
    block = _build_l1_history_block(history)
    assert block is not None
    line_count = block.count("USER:")
    assert line_count < 6   # truncation must still occur at base 450-word budget
```

- [ ] **Step 2.2: Write two new failing tests**

Add to `tests/test_prompts_composer.py`:

```python
def test_l1_history_base_budget_is_450():
    """Verify the template's base word_budget is 450 after the increase."""
    from sage_poc.prompts.loader import get_template
    tmpl = get_template("L1_history")
    assert tmpl.word_budget == 450


def test_compose_prompt_l1_budget_flexes_to_600_on_freeflow_turns():
    """L1 gets 600-word flex budget when no skill and no info_request intent."""
    from sage_poc.prompts.composer import _compute_l1_budget
    freeflow_state = _make_state(
        primary_intent="general_chat",
        secondary_intent=None,
        step_instruction=None,
    )
    assert _compute_l1_budget(freeflow_state) == 600


def test_compose_prompt_l1_budget_stays_at_450_when_skill_active():
    """L1 budget does not flex when a skill step is in progress."""
    from sage_poc.prompts.composer import _compute_l1_budget
    skill_state = _make_state(
        primary_intent="skill_continuation",
        secondary_intent=None,
        step_instruction="Invite the user to identify their thought.",
    )
    assert _compute_l1_budget(skill_state) == 450
```

- [ ] **Step 2.3: Run the three tests to confirm they fail**

```
uv run pytest tests/test_prompts_composer.py -v -k "budget"
```

Expected: all three new/updated budget tests fail (word_budget still 300; `_compute_l1_budget` doesn't exist yet).

- [ ] **Step 2.4: Raise the base budget in L1_history.json**

In `src/sage_poc/prompts/templates/L1_history.json`, change:

```json
"word_budget": 450,
```

- [ ] **Step 2.5: Add _compute_l1_budget and update _build_l1_history_block signature**

In `src/sage_poc/prompts/composer.py`, add after the `_INTENSITY_GUIDANCE` block:

```python
_L1_BASE_BUDGET = 450
_L1_FLEX_BUDGET = 600


def _compute_l1_budget(state: SageState) -> int:
    """Return the L1 word budget for this turn.

    On freeflow turns (no skill step, no knowledge lookup), L3 and L4 layers
    are absent. Their unused budget headroom is loaned to L1 so that rich
    multi-turn disclosures don't get truncated.

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
    return _L1_BASE_BUDGET if (has_skill or has_knowledge) else _L1_FLEX_BUDGET
```

Update `_build_l1_history_block` signature to accept an optional `word_budget` override:

```python
def _build_l1_history_block(
    conversation_history: list[dict],
    variant: str | None = None,
    word_budget: int | None = None,
) -> str | None:
    if not conversation_history:
        return None
    tmpl = get_template("L1_history", variant=variant)
    window_size = tmpl.window_size or 8
    effective_budget = word_budget if word_budget is not None else (tmpl.word_budget or _L1_BASE_BUDGET)
    window = conversation_history[-window_size:]
    lines: list[str] = []
    word_total = 0
    for m in reversed(window):
        content = (
            _sanitize_assistant_turn(m["content"])
            if m["role"] == "assistant"
            else m["content"]
        )
        line = f"{m['role'].upper()}: {content}"
        words = count_words(line)
        if lines and word_total + words > effective_budget:
            _log.debug("L1 history truncated at word budget %d", effective_budget)
            break
        lines.append(line)
        word_total += words
    if not lines:
        return None
    lines.reverse()
    history_text = _esc("\n".join(lines))
    content = tmpl.content.format(history_lines=history_text)
    _log.debug("L1_history@%s loaded", tmpl.version)
    return content
```

- [ ] **Step 2.6: Wire _compute_l1_budget into compose_prompt**

In `compose_prompt()`, update the L1 call:

```python
    # L1: Conversation history
    l1_budget = _compute_l1_budget(state)
    l1_block = _build_l1_history_block(
        state.get("conversation_history", []),
        word_budget=l1_budget,
    )
    if l1_block:
        user_parts.append(l1_block)
        layers.append("history")
```

Also update the overflow shrink call at the bottom of `compose_prompt` to pass an explicit conservative budget:

```python
    if total_words > _TOTAL_WORD_BUDGET and "history" in layers:
        history = state.get("conversation_history", [])
        l1_tmpl = get_template("L1_history")
        half_window = max(1, (l1_tmpl.window_size or 8) // 2)
        shrunk = _build_l1_history_block(
            history[-half_window:],
            word_budget=300,    # conservative for overflow case
        ) or ""
        user_parts[0] = shrunk
        _log.warning("Token budget overflow: L1 history shrunk to %d turns", half_window)
```

- [ ] **Step 2.7: Run the budget tests**

```
uv run pytest tests/test_prompts_composer.py -v -k "budget"
```

Expected: all budget tests pass.

- [ ] **Step 2.8: Run the full suite**

```
uv run pytest --tb=short -q
```

Expected: all tests pass.

- [ ] **Step 2.9: Commit**

```bash
git add src/sage_poc/prompts/composer.py \
        src/sage_poc/prompts/templates/L1_history.json \
        tests/test_prompts_composer.py
git commit -m "feat(composer): increase L1 budget to 450 words, flex to 600 on freeflow turns

Freeflow turns (no skill, no knowledge lookup) gain an extra 150 words
from the L3/L4 headroom. Overflow shrink stays conservative at 300 words.
Fixes RCA RC-2."
```

---

## Task 3 (quick): Expand PI-EI-001 Expat Isolation Keywords

**Root cause addressed:** RC-5 — PI-EI-001 relies on exact keyword matching. The user expressed expat isolation through paraphrase ("build a network all over again," "exhausted my network," "not my first choice of a country") and none hit the keyword list. No code change — Rules Service JSON update only.

**Files:**
- Modify: `src/sage_poc/rules/data/prompt_injection/expat_isolation.json`
- Modify: `tests/test_rules_integration.py` (add parametrize block)

- [ ] **Step 3.1: Write the failing tests**

Add to `tests/test_rules_integration.py`:

```python
@pytest.mark.parametrize("text", [
    "I have to build a network all over again",
    "I've been building a network from scratch",
    "I exhausted my network here",
    "I don't know anyone here",
    "I have no friends here",
    "starting over in a new country",
    "this wasn't my first choice of country",
    "Dubai is not my first choice",
    "I have no support system here",
    "moved here for my career but",
    "starting fresh somewhere new",
])
def test_pi_ei_001_fires_on_paraphrase_expat_isolation(text):
    from sage_poc.rules import engine
    result = engine.evaluate("prompt_injection", {
        "text": text,
        "text_ar": None,
        "clinical_flags": [],
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "session_flags": [],
    })
    rule_ids = [r.rule_id for r in result.fired]
    assert "PI-EI-001" in rule_ids, f"Expected PI-EI-001 for: {text!r}"
```

- [ ] **Step 3.2: Run to confirm they fail**

```
uv run pytest tests/test_rules_integration.py -v -k "pi_ei_001"
```

Expected: all 11 parametrize cases fail (keywords not in list yet).

- [ ] **Step 3.3: Add the paraphrase keywords to expat_isolation.json**

In `src/sage_poc/rules/data/prompt_injection/expat_isolation.json`, extend `trigger_keywords` with:

```json
"build a network",
"building a network",
"network from scratch",
"exhausted my network",
"don't know anyone here",
"dont know anyone here",
"no friends here",
"starting over",
"starting fresh",
"new country",
"not my first choice",
"wasn't my first choice",
"no support system here",
"no support system",
"moved here for",
"didn't choose to be here",
"didn't choose this country"
```

Append these inside the existing `trigger_keywords` array, after the existing English entries and before the Arabic entries.

- [ ] **Step 3.4: Run the parametrize tests**

```
uv run pytest tests/test_rules_integration.py -v -k "pi_ei_001"
```

Expected: all 11 pass.

- [ ] **Step 3.5: Run the full suite**

```
uv run pytest --tb=short -q
```

Expected: all tests pass.

- [ ] **Step 3.6: Commit**

```bash
git add src/sage_poc/rules/data/prompt_injection/expat_isolation.json \
        tests/test_rules_integration.py
git commit -m "feat(rules): expand PI-EI-001 with paraphrase expat isolation keywords

Adds 17 common paraphrase forms that keyword-only matching missed.
Fixes RCA RC-5 (layer 1 of 2; semantic fallback is next sprint)."
```

---

## Task 4 (quick): Constrain Therapeutic Jargon in L0 Persona

**Root cause addressed:** RC-6 — After losing context, the LLM recovered with abstract therapeutic phrases ("What's sitting heaviest for you right now?") that a non-native English speaker or distressed user may find opaque. L0 says "plain words" but doesn't specifically train the LLM away from therapist-speak.

**Files:**
- Modify: `src/sage_poc/prompts/templates/L0_persona.json`

- [ ] **Step 4.1: Add a jargon anti-phrase section to L0_persona.json**

The current content ends with `"Be present before being helpful."`. Extend it. The full content field should become (replace the entire `content` value):

```json
"content": "IMPORTANT. FORMAT: Write in plain prose. Use commas or short sentences instead of dashes. Use no emojis. Use no markdown (no **, no *, no bullets). Do not copy punctuation patterns from the skill instructions you receive. Those are guidance for you, not templates to mirror.\n\nFORMATTING EXAMPLE:\nWRONG: \"That really resonates, sometimes things pile up. What's been **weighing on you**?\"\nRIGHT: \"That makes sense. What's been on your mind lately?\"\n\nPHRASING: Use plain, conversational language a supportive friend would use, not a therapy textbook. Avoid abstract metaphors for distress.\nWRONG: \"What's sitting heaviest for you right now?\"\nRIGHT: \"What's been bothering you most?\"\nWRONG: \"What's weighing on you?\"\nRIGHT: \"What feels hardest right now?\"\nWRONG: \"What's taking up the most space for you?\"\nRIGHT: \"What's been on your mind the most?\"\n\nYou are Sage, a warm Khaleeji wellness companion. You provide emotional support grounded in evidence-based approaches (CBT, DBT, motivational interviewing). Speak the way a calm, attentive person would in a quiet one-on-one conversation. Short sentences. Plain words. No decoration. If something matters, say it clearly. Warmth comes from what you say, not how you format it.\n\nYou do NOT diagnose, prescribe, or replace professional mental health care. If someone is in crisis, your only role is to express care and provide emergency resources.\n\nKeep responses concise (2-4 sentences unless the user needs more). Match the user's energy and register. Be present before being helpful."
```

- [ ] **Step 4.2: Verify the existing L0 test still passes**

```
uv run pytest tests/test_prompts_composer.py::test_l0_system_block_starts_with_important -v
```

Expected: PASS (content still starts with `IMPORTANT`).

- [ ] **Step 4.3: Run the full suite**

```
uv run pytest --tb=short -q
```

Expected: all tests pass.

- [ ] **Step 4.4: Commit**

```bash
git add src/sage_poc/prompts/templates/L0_persona.json
git commit -m "feat(persona): add jargon anti-phrase constraint to L0

Instructs the LLM away from abstract therapist-speak using concrete
wrong/right examples. Addresses RCA RC-6."
```

---

## Task 5 (P1 sprint): Test Coverage and Engagement Supplement for escalating_distress

**Important correction:** RC-4 in the RCA stated that `escalating_distress` is never set by any node. This was incorrect. `safety_check_node` already implements `_update_distress_trajectory()` (lines 15–29) and sets `escalating_distress` in `clinical_flags` when 3 consecutive turns have `emotional_intensity >= 6`. The mechanism is sound. The actual gaps are: (a) zero test coverage for this mechanism, and (b) intensity alone misses the pattern in the sample conversation — the user's routine description (turn 6) likely scored intensity ~5–6 and the "yes" turn would score 2–3, potentially breaking the streak before PI-CD-001 could reinforce the context. This task adds tests and a complementary engagement-decline signal.

**Files:**
- Modify: `src/sage_poc/state.py` (add `engagement_trajectory`)
- Modify: `src/sage_poc/nodes/safety_check.py` (add engagement supplement)
- Modify: `tests/test_nodes.py` (add distress trajectory test block)

- [ ] **Step 5.1: Write tests for the existing distress trajectory mechanism**

Add to `tests/test_nodes.py` (at the end of the file):

```python
# ---------------------------------------------------------------------------
# Distress trajectory and escalating_distress flag
# ---------------------------------------------------------------------------

def test_distress_trajectory_accumulates_across_turns():
    """Each call appends current emotional_intensity to the trajectory."""
    state = make_state(emotional_intensity=7, distress_trajectory=[])
    result = safety_check_node(state)
    assert 7 in result["distress_trajectory"]


def test_escalating_distress_flag_set_after_three_high_intensity_turns():
    """escalating_distress appears in clinical_flags after 3 consecutive turns >= 6."""
    # Simulate 3 prior high-intensity turns already in the trajectory
    state = make_state(
        raw_message="I still feel terrible",
        emotional_intensity=7,           # this is intensity from the PREVIOUS turn
        distress_trajectory=[7, 7],      # two prior high-intensity turns already logged
    )
    result = safety_check_node(state)
    # trajectory now has [7, 7, 7] — three turns >= 6 → flag fires
    assert "escalating_distress" in result["clinical_flags"]


def test_escalating_distress_not_set_if_streak_broken():
    """Flag does not fire if the streak of high intensity is broken."""
    state = make_state(
        raw_message="I'm okay today",
        emotional_intensity=3,           # low intensity this turn
        distress_trajectory=[7, 7],      # prior streak
    )
    result = safety_check_node(state)
    # trajectory becomes [7, 7, 3] — streak broken
    assert "escalating_distress" not in result["clinical_flags"]


def test_escalating_distress_suppressed_during_active_skill_with_high_engagement():
    """Flag is suppressed when user is actively engaged in a skill."""
    state = make_state(
        raw_message="The thought I keep having is that I'm worthless",
        emotional_intensity=8,
        distress_trajectory=[8, 8],
        active_skill_id="cbt_thought_record",
        engagement=7,                   # good engagement within skill
    )
    result = safety_check_node(state)
    assert "escalating_distress" not in result["clinical_flags"]


def test_escalating_distress_not_suppressed_without_active_skill():
    """Flag fires normally when no skill is active, even with high engagement."""
    state = make_state(
        raw_message="I feel drained all the time",
        emotional_intensity=7,
        distress_trajectory=[7, 7],
        active_skill_id=None,
        engagement=8,
    )
    result = safety_check_node(state)
    assert "escalating_distress" in result["clinical_flags"]
```

- [ ] **Step 5.2: Run the new tests to confirm they pass against the existing code**

```
uv run pytest tests/test_nodes.py -v -k "escalating_distress or distress_trajectory"
```

Expected: all 5 tests pass. If any fail, there is a real bug in the existing mechanism — fix it before continuing.

- [ ] **Step 5.3: Add engagement_trajectory to SageState**

In `src/sage_poc/state.py`, add after `distress_trajectory`:

```python
    engagement_trajectory: list[int]
```

- [ ] **Step 5.4: Add engagement-decline supplement to safety_check.py**

The engagement-decline signal catches patterns the intensity threshold misses — a user whose intensity hovers around 5 but whose engagement is consistently dropping (becoming more withdrawn) also warrants the clinical flag.

In `src/sage_poc/nodes/safety_check.py`, update the constants and add the helper:

```python
_DISTRESS_WINDOW = 4
_DISTRESS_FLOOR = 6
_DISTRESS_STREAK = 3

_ENGAGEMENT_WINDOW = 4
_ENGAGEMENT_LOW = 4       # scores <= 4 are "withdrawn"
_ENGAGEMENT_STREAK = 3    # 3 consecutive withdrawn turns
```

Add a new helper function after `_update_distress_trajectory`:

```python
def _update_engagement_trajectory(state: SageState) -> tuple[list[int], bool]:
    """Track engagement across turns; return (updated_trajectory, declining).

    Engagement is also one-turn lagged (set by intent_route, which runs after
    safety_check). Declining is True if the last 3 turns are all <= _ENGAGEMENT_LOW.
    """
    trajectory = list(state.get("engagement_trajectory") or [])
    current = state.get("engagement", 5)
    trajectory.append(current)
    trajectory = trajectory[-_ENGAGEMENT_WINDOW:]
    declining = (
        len(trajectory) >= _ENGAGEMENT_STREAK
        and all(s <= _ENGAGEMENT_LOW for s in trajectory[-_ENGAGEMENT_STREAK:])
    )
    return trajectory, declining
```

Update `safety_check_node` to call the new helper and combine signals:

```python
    trajectory, escalating = _update_distress_trajectory(state)
    engagement_trajectory, engagement_declining = _update_engagement_trajectory(state)

    skill_active = bool(state.get("active_skill_id"))
    engagement_ok = state.get("engagement", 5) >= 5

    persisted = state.get("clinical_flags", [])
    distress_signal = escalating or engagement_declining
    extra = ["escalating_distress"] if distress_signal and not (skill_active and engagement_ok) else []
    all_clinical = list(set(new_clinical_flags + third_party_flags + extra + persisted))
```

And add `engagement_trajectory` to the return dict:

```python
    return {
        "detected_language": lang,
        "message_en": message_en,
        "is_safe": len(new_crisis_flags) == 0,
        "crisis_flags": new_crisis_flags,
        "clinical_flags": all_clinical,
        "distress_trajectory": trajectory,
        "engagement_trajectory": engagement_trajectory,
        "code_switching": code_switching,
        "crisis_state": crisis_state,
        "s7_result": s7_result,
        "s7_method": s7_method,
        "path": state["path"] + ["safety_check"],
    }
```

- [ ] **Step 5.5: Write the engagement-decline tests**

Add to `tests/test_nodes.py`:

```python
def test_engagement_trajectory_accumulates():
    """Engagement from the previous turn is appended to engagement_trajectory."""
    state = make_state(engagement=2, engagement_trajectory=[])
    result = safety_check_node(state)
    assert 2 in result["engagement_trajectory"]


def test_escalating_distress_fires_on_engagement_decline_alone():
    """escalating_distress fires when engagement is low for 3 turns, even without high intensity."""
    state = make_state(
        raw_message="I guess",
        emotional_intensity=4,           # not high enough to trigger intensity streak
        distress_trajectory=[4, 4],
        engagement=3,                    # low engagement this turn
        engagement_trajectory=[3, 3],    # two prior low-engagement turns
    )
    result = safety_check_node(state)
    assert "escalating_distress" in result["clinical_flags"]


def test_engagement_decline_does_not_fire_when_engagement_is_normal():
    state = make_state(
        raw_message="That makes sense",
        emotional_intensity=4,
        distress_trajectory=[4, 4],
        engagement=6,
        engagement_trajectory=[3, 3],   # two prior low, but this turn is normal
    )
    result = safety_check_node(state)
    assert "escalating_distress" not in result["clinical_flags"]
```

- [ ] **Step 5.6: Update make_state in test_nodes.py to include engagement_trajectory**

In `tests/test_nodes.py`, add to the `defaults` dict in `make_state()`:

```python
        "engagement_trajectory": [],
```

- [ ] **Step 5.7: Update test_rules_integration.py's _state factory similarly**

In `tests/test_rules_integration.py`, add to the `_state()` return dict:

```python
        "engagement_trajectory": [],
```

- [ ] **Step 5.8: Run the engagement tests**

```
uv run pytest tests/test_nodes.py -v -k "engagement"
```

Expected: all 3 engagement tests pass.

- [ ] **Step 5.9: Run the full suite**

```
uv run pytest --tb=short -q
```

Expected: all tests pass.

- [ ] **Step 5.10: Commit**

```bash
git add src/sage_poc/state.py \
        src/sage_poc/nodes/safety_check.py \
        tests/test_nodes.py \
        tests/test_rules_integration.py
git commit -m "feat(safety): add test coverage and engagement-decline supplement for escalating_distress

Adds 8 tests covering the existing intensity-based mechanism (previously
untested) and a new engagement_trajectory signal that fires when the user
withdraws across 3 turns regardless of intensity. Addresses RCA RC-4."
```

---

## Task 6 (P2 sprint): Implement summary_trigger

**Root cause addressed:** RC-3 — `L1_history.json:summary_trigger = 10` has been in the spec since the template was authored but no code reads it. This is the permanent fix: at turn 10 (and 20, 30 …), the conversation so far is compressed into a 2–3 sentence summary stored in state. Subsequent L1 blocks show `[SUMMARY] + [recent verbatim turns]`, giving the LLM full context regardless of conversation length.

**Files:**
- Create: `src/sage_poc/prompts/summarizer.py`
- Modify: `src/sage_poc/state.py` (add `conversation_summary`)
- Modify: `src/sage_poc/prompts/composer.py` (pass summary to `_build_l1_history_block`)
- Modify: `src/sage_poc/nodes/output_gate.py` (trigger summariser at turn 10)
- Modify: `tests/test_prompts_composer.py` (add summary integration tests)

### 6a — State field

- [ ] **Step 6a.1: Add conversation_summary to SageState**

In `src/sage_poc/state.py`, add after `engagement_trajectory`:

```python
    conversation_summary: Optional[str]
```

- [ ] **Step 6a.2: Verify all state factories compile (no code change needed)**

All access to `conversation_summary` in the codebase will use `.get("conversation_summary")`, so existing state dicts without the key work correctly at runtime. No factory updates required.

```
uv run pytest --tb=short -q
```

Expected: all tests pass (TypedDict addition doesn't break runtime).

### 6b — Summariser module

- [ ] **Step 6b.1: Write the failing test for the summariser**

Add to `tests/test_prompts_composer.py`:

```python
# ---------------------------------------------------------------------------
# Task 6: Conversation summariser
# ---------------------------------------------------------------------------
from unittest.mock import AsyncMock, patch as async_patch


@pytest.mark.asyncio
async def test_summarise_history_calls_llm_and_returns_string():
    from sage_poc.prompts.summarizer import summarise_history
    mock_llm = AsyncMock()
    with async_patch(
        "sage_poc.prompts.summarizer.resilient_invoke",
        new=AsyncMock(return_value="The user is an expat struggling with job search."),
    ):
        history = [
            {"role": "user", "content": "I moved to Dubai and can't find a job."},
            {"role": "assistant", "content": "That sounds exhausting."},
        ]
        result = await summarise_history(history, llm=mock_llm)
    assert isinstance(result, str)
    assert len(result) > 10


@pytest.mark.asyncio
async def test_summarise_history_passes_full_history_to_llm():
    from sage_poc.prompts.summarizer import summarise_history
    captured_messages = []

    async def capture(llm, messages, **kwargs):
        captured_messages.extend(messages)
        return "Summary text."

    mock_llm = AsyncMock()
    with async_patch("sage_poc.prompts.summarizer.resilient_invoke", new=capture):
        history = [
            {"role": "user", "content": "Turn 1 user content"},
            {"role": "assistant", "content": "Turn 1 assistant content"},
        ]
        await summarise_history(history, llm=mock_llm)

    user_message_content = captured_messages[1]["content"]
    assert "Turn 1 user content" in user_message_content
    assert "Turn 1 assistant content" in user_message_content
```

- [ ] **Step 6b.2: Run to confirm they fail**

```
uv run pytest tests/test_prompts_composer.py -v -k "summarise"
```

Expected: ImportError — `summariser` module does not exist yet.

- [ ] **Step 6b.3: Create the summariser module**

Create `src/sage_poc/prompts/summarizer.py`:

```python
import logging
from sage_poc.llm import get_classifier
from sage_poc.resilience import resilient_invoke

_log = logging.getLogger(__name__)

_SUMMARY_SYSTEM = (
    "You are summarising a mental health support conversation for context continuity. "
    "In 2-3 sentences, extract: (1) the key life situation the user described, "
    "(2) the main emotional themes, "
    "(3) anything the user has already shared about their daily life or routines, "
    "(4) any commitments or next steps the assistant offered (e.g. 'we can try that next time', "
    "'let's come back to this', 'we could try a grounding exercise'). "
    "Be factual. Do not advise or evaluate. Do not use bullet points or headers."
)


async def summarise_history(history: list[dict], llm=None) -> str:
    if llm is None:
        llm = get_classifier()
    turns = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in history
    )
    messages = [
        {"role": "system", "content": _SUMMARY_SYSTEM},
        {"role": "user", "content": f"Conversation:\n{turns}"},
    ]
    result = await resilient_invoke(
        llm, messages, node="summariser", language="en"
    )
    return result.strip()
```

- [ ] **Step 6b.4: Run the summariser tests**

```
uv run pytest tests/test_prompts_composer.py -v -k "summarise"
```

Expected: both tests pass.

### 6c — Update _build_l1_history_block to consume the summary

- [ ] **Step 6c.1: Write the failing test**

Add to `tests/test_prompts_composer.py`:

```python
def test_l1_history_prepends_summary_when_present():
    """When a conversation_summary exists, it appears before the recent turns."""
    history = [
        {"role": "user", "content": "Turn A"},
        {"role": "assistant", "content": "Turn B"},
    ]
    block = _build_l1_history_block(
        history,
        conversation_summary="The user is an expat who feels isolated.",
    )
    assert block is not None
    assert "The user is an expat who feels isolated." in block
    assert "Turn A" in block
    assert block.index("isolated") < block.index("Turn A")   # summary appears before turns


def test_l1_history_no_summary_prefix_when_summary_is_none():
    history = [{"role": "user", "content": "Hello"}]
    block = _build_l1_history_block(history, conversation_summary=None)
    assert "SUMMARY" not in block
```

- [ ] **Step 6c.2: Run to confirm they fail**

```
uv run pytest tests/test_prompts_composer.py -v -k "prepend_summary or no_summary_prefix"
```

Expected: TypeError — `_build_l1_history_block` does not accept `conversation_summary` yet.

- [ ] **Step 6c.3: Add conversation_summary parameter to _build_l1_history_block**

Update the function signature and body in `src/sage_poc/prompts/composer.py`:

```python
def _build_l1_history_block(
    conversation_history: list[dict],
    variant: str | None = None,
    word_budget: int | None = None,
    conversation_summary: str | None = None,
) -> str | None:
    if not conversation_history and not conversation_summary:
        return None
    tmpl = get_template("L1_history", variant=variant)
    window_size = tmpl.window_size or 8
    effective_budget = word_budget if word_budget is not None else (tmpl.word_budget or _L1_BASE_BUDGET)
    window = conversation_history[-window_size:]
    lines: list[str] = []
    word_total = 0
    for m in reversed(window):
        content = (
            _sanitize_assistant_turn(m["content"])
            if m["role"] == "assistant"
            else m["content"]
        )
        line = f"{m['role'].upper()}: {content}"
        words = count_words(line)
        if lines and word_total + words > effective_budget:
            _log.debug("L1 history truncated at word budget %d", effective_budget)
            break
        lines.append(line)
        word_total += words
    lines.reverse()

    if conversation_summary:
        summary_block = f"SUMMARY (earlier context):\n{_esc(conversation_summary)}"
        if lines:
            history_text = summary_block + "\n\nRECENT TURNS:\n" + _esc("\n".join(lines))
        else:
            history_text = summary_block
    else:
        if not lines:
            return None
        history_text = _esc("\n".join(lines))

    content = tmpl.content.format(history_lines=history_text)
    _log.debug("L1_history@%s loaded", tmpl.version)
    return content
```

- [ ] **Step 6c.4: Update the compose_prompt L1 call to pass conversation_summary**

In `compose_prompt()`:

```python
    l1_budget = _compute_l1_budget(state)
    l1_block = _build_l1_history_block(
        state.get("conversation_history", []),
        word_budget=l1_budget,
        conversation_summary=state.get("conversation_summary"),
    )
```

- [ ] **Step 6c.5: Run the summary tests**

```
uv run pytest tests/test_prompts_composer.py -v -k "summary"
```

Expected: all summary tests pass.

### 6d — Trigger summariser from output_gate

- [ ] **Step 6d.1: Write the failing test**

Add to `tests/test_prompts_composer.py` (uses `test_server.py`-style async test; also needs the output_gate test in `tests/test_nodes.py` — add it there instead):

Add to `tests/test_nodes.py`:

```python
import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_output_gate_triggers_summariser_at_turn_10():
    """At turn_count 9 (completing turn 10), output_gate calls summarise_history."""
    from sage_poc.nodes.output_gate import output_gate_node

    state = make_state(
        message_en="I'm feeling better today",
        response_en="Glad to hear that.",
        detected_language="en",
        turn_count=9,           # completing turn 10 (0-indexed)
        gate_path="standard",
        conversation_history=[
            {"role": "user", "content": f"turn {i}"}
            for i in range(18)   # existing history
        ],
        conversation_summary=None,
    )

    with patch(
        "sage_poc.nodes.output_gate.summarise_history",
        new=AsyncMock(return_value="The user has been discussing their wellbeing."),
    ):
        result = await output_gate_node(state)

    assert result["conversation_summary"] == "The user has been discussing their wellbeing."


@pytest.mark.asyncio
async def test_output_gate_does_not_call_summariser_at_other_turns():
    from sage_poc.nodes.output_gate import output_gate_node

    state = make_state(
        message_en="I'm okay",
        response_en="Good.",
        detected_language="en",
        turn_count=4,       # turn 5, not a summary trigger
        gate_path="standard",
        conversation_history=[],
        conversation_summary=None,
    )

    with patch(
        "sage_poc.nodes.output_gate.summarise_history",
        new=AsyncMock(return_value="Should not be called."),
    ) as mock_summarise:
        result = await output_gate_node(state)

    mock_summarise.assert_not_called()
    assert result.get("conversation_summary") is None
```

- [ ] **Step 6d.2: Verify output_gate_node is already async**

```bash
grep "async def output_gate_node" src/sage_poc/nodes/output_gate.py
```

Expected output: `async def output_gate_node(state: SageState) -> dict:` — it already calls `async_translate_to_arabic` so LangGraph is already wired for async here. If this grep returns nothing, stop and investigate before continuing.

- [ ] **Step 6d.3: Run to confirm the summariser tests fail**

```
uv run pytest tests/test_nodes.py -v -k "summariser"
```

Expected: ImportError — `output_gate` does not import `summarise_history` yet.

- [ ] **Step 6d.4: Update output_gate.py to import and call the summariser**

In `src/sage_poc/nodes/output_gate.py`, add import at the top:

```python
import logging
from sage_poc.prompts.summarizer import summarise_history

_log = logging.getLogger(__name__)
```

At the start of `output_gate_node`, build the updated history first (before the existing logic), then conditionally summarise:

```python
async def output_gate_node(state: SageState) -> dict:
    gate_path = state.get("gate_path")
    lang = state["detected_language"]
    path = state["path"] + ["output_gate"]

    # ... existing gate_path / response_en / violations logic unchanged ...

    new_history = state.get("conversation_history", []) + [
        {"role": "user", "content": state["message_en"]},
        {"role": "assistant", "content": response_en},
    ]

    # Summarise at turn 10, 20, 30 …
    next_turn = state["turn_count"] + 1
    existing_summary = state.get("conversation_summary")
    new_summary = existing_summary
    if next_turn % 10 == 0:
        try:
            new_summary = await summarise_history(new_history)
            _log.info("Conversation summary generated at turn %d", next_turn)
        except Exception:
            _log.warning("Summarisation failed at turn %d; keeping prior summary", next_turn)

    return {
        "response": final_response,
        "gate_path": gate_path or "standard",
        "path": path,
        "turn_count": state["turn_count"] + 1,
        "conversation_history": new_history,
        "conversation_summary": new_summary,
        "cultural_output_violations": cultural_output_violations,
    }
```

Note: Remove the existing `conversation_history` construction from the return dict (it's now built above and referenced as `new_history`).

- [ ] **Step 6d.5: Run the summariser output_gate tests**

```
uv run pytest tests/test_nodes.py -v -k "summariser"
```

Expected: both tests pass.

- [ ] **Step 6d.7: Run the full suite**

```
uv run pytest --tb=short -q
```

Expected: all tests pass.

- [ ] **Step 6d.8: Commit**

```bash
git add src/sage_poc/state.py \
        src/sage_poc/prompts/summarizer.py \
        src/sage_poc/prompts/composer.py \
        src/sage_poc/nodes/output_gate.py \
        tests/test_prompts_composer.py \
        tests/test_nodes.py
git commit -m "feat(summariser): implement summary_trigger — compress history at turn 10

Adds summariser.py (LLM-based 2-3 sentence summary), conversation_summary
state field, and output_gate trigger at turns 10/20/30. L1 now shows
[SUMMARY + recent verbatim turns] for long conversations.
Implements v7 §5.6.1 summary_trigger. Fixes RCA RC-3."
```

---

## Spec Coverage Check

| Fix | RC | Task | Covered |
|-----|----|------|---------|
| Reverse L1 iteration | RC-1 | Task 1 | ✅ |
| Budget increase + flex | RC-2 | Task 2 | ✅ |
| Implement summary_trigger | RC-3 | Task 6 | ✅ |
| Escalating_distress tests + engagement supplement | RC-4 | Task 5 | ✅ |
| PI-EI-001 paraphrase keywords | RC-5 (layer 1) | Task 3 | ✅ |
| PI-EI-001 semantic fallback | RC-5 (layer 2) | — | ⏭ next sprint |
| L0 jargon constraints | RC-6 | Task 4 | ✅ |

Fix 5b (semantic fallback for prompt injection rules) is explicitly deferred to next sprint per the priority table.
