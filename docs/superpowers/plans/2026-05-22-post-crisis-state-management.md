# Post-Crisis State Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dead `crisis_occurred_this_session: bool` flag with a `CrisisState` state machine (`none → monitoring → resolved`) that drives a dedicated S7 post-crisis classifier and auto-selects a `post_crisis_check_in` skill on subsequent turns, then transitions to `resolved` so normal conversation flow resumes.

**Architecture:** `safety_check_node` gains an S7 sub-classifier that fires only when `crisis_state == "monitoring"`, evaluating the current message in isolation (no history) using deterministic keywords first and LLM fallback. S7's `STILL_DISTRESSED` keyword list contains only non-crisis distress signals — phrases that overlap with S1–S6 crisis detection are intentionally excluded because those are caught by the existing pipeline before S7 runs. `_route_after_safety` routes to crisis only when S1–S6 fire directly or S7 returns `NEW_CRISIS`; all other monitoring-state results route safe. `skill_select_node` auto-selects `post_crisis_check_in` when `crisis_state == "monitoring"` and falls through to normal matching when `"resolved"`. `skill_executor_node` writes `crisis_state: "resolved"` when `post_crisis_check_in` completes both steps, so S7 and the auto-select guard never fire again that session, while the L5 heightened-sensitivity prompt layer remains active.

**Tech Stack:** Python 3.11, LangGraph 0.x, LangChain ChatOpenAI (OpenRouter), Pydantic v2, pytest

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `src/sage_poc/state.py` | Modify | Replace `crisis_occurred_this_session: bool` with `crisis_state: str`, add `s7_result`, `s7_method` |
| `src/sage_poc/nodes/post_crisis_classifier.py` | **Create** | Deterministic keyword tier + LLM fallback S7 classifier |
| `src/sage_poc/nodes/safety_check.py` | Modify | Call S7 when `crisis_state == "monitoring"`, return s7 fields |
| `src/sage_poc/graph.py` | Modify | `_crisis_response_node` → set `crisis_state: "monitoring"`; `_route_after_safety` → monitoring-aware routing |
| `src/sage_poc/skills/post_crisis_check_in.json` | **Create** | Structured 2-step skill: acknowledge_and_check → bridge_or_close |
| `src/sage_poc/nodes/skill_select.py` | Modify | Auto-select `post_crisis_check_in` when `crisis_state == "monitoring"`; fall through when `"resolved"` |
| `src/sage_poc/nodes/skill_executor.py` | Modify | Write `crisis_state: "resolved"` when `post_crisis_check_in` skill completes |
| `src/sage_poc/nodes/freeflow_respond.py` | Modify | Replace `crisis_occurred_this_session` session flag (include "resolved"); inject s7 context for monitoring only |
| `src/sage_poc/nodes/output_gate.py` | Modify | Add `crisis_state`, `s7_result`, `s7_method` to audit log |
| `tests/test_post_crisis_classifier.py` | **Create** | Unit tests for evaluate_s7: keyword tier, LLM fallback, invalid label fallback |
| `tests/test_state.py` | Modify | Update TypedDict literal to include new fields |
| `tests/test_nodes.py` | Modify | Add `crisis_state: "none"` to make_state helper |
| `tests/test_routing.py` | Modify | Update make_full_state helper; add monitoring routing tests |
| `tests/test_rules_integration.py` | Modify | Replace all `crisis_occurred_this_session` references; update schema assertion test |
| `tests/test_graph.py` | Modify | Add `crisis_state` to make_e2e_state + _CARRY_FIELDS; add 3 e2e monitoring tests |

---

## Task 1: SageState field replacement

**Files:**
- Modify: `src/sage_poc/state.py`
- Modify: `tests/test_state.py`
- Modify: `tests/test_nodes.py:5-32` (make_state helper)
- Modify: `tests/test_routing.py:11-24` (make_full_state helper)
- Modify: `tests/test_rules_integration.py` (two helpers + two tests)
- Modify: `tests/test_graph.py:6-49` (make_e2e_state, _CARRY_FIELDS)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_state.py  — replace file contents
from sage_poc.state import SageState
import typing

def test_state_has_required_fields():
    state: SageState = {
        "raw_message": "hello",
        "detected_language": "en",
        "message_en": "hello",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
        "skill_match_method": None,
        "semantic_score": None,
    }
    assert state["raw_message"] == "hello"
    assert state["crisis_state"] == "none"
    assert state["s7_result"] is None

def test_state_has_crisis_state_not_legacy_bool():
    hints = typing.get_type_hints(SageState)
    assert "crisis_state" in hints, "SageState must declare crisis_state"
    assert "s7_result" in hints, "SageState must declare s7_result"
    assert "s7_method" in hints, "SageState must declare s7_method"
    assert "crisis_occurred_this_session" not in hints, "legacy field must be removed"

def test_state_path_is_list():
    state: SageState = {
        "raw_message": "test",
        "detected_language": "en",
        "message_en": "test",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": ["substance_use"],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "intent_confidence": 0.9,
        "emotional_intensity": 3,
        "engagement": 7,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": "identify_thought",
        "step_instruction": None,
        "escalation_triggered": {"level": "L2", "reason": "substance detected"},
        "response_en": "I'm here for you.",
        "response": "I'm here for you.",
        "path": ["safety_check", "intent_route", "freeflow_respond", "output_gate"],
        "turn_count": 1,
        "conversation_history": [{"role": "user", "content": "test"}],
        "skill_match_method": None,
        "semantic_score": None,
    }
    assert len(state["path"]) == 4
    assert state["crisis_state"] == "none"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && python -m pytest tests/test_state.py -v`
Expected: FAIL — `crisis_state` not in SageState hints; `crisis_occurred_this_session` still present

- [ ] **Step 3: Update state.py**

In `src/sage_poc/state.py`, replace line 18:
```python
    crisis_occurred_this_session: bool         # set True by crisis_response node; persists for session
```
with:
```python
    crisis_state: str              # "none" | "active" | "monitoring" | "resolved"
    s7_result: Optional[str]       # "RECOVERING" | "STILL_DISTRESSED" | "UNCLEAR" | "NEW_CRISIS"
    s7_method: Optional[str]       # "keyword" | "llm"
```

The full block around lines 14–20 should now read:
```python
    is_safe: bool
    crisis_flags: list[str]
    clinical_flags: list[str]   # substance_use, trauma_indicator, eating_concern, medication_mention

    crisis_state: str              # "none" | "active" | "monitoring" | "resolved"
    s7_result: Optional[str]       # "RECOVERING" | "STILL_DISTRESSED" | "UNCLEAR" | "NEW_CRISIS"
    s7_method: Optional[str]       # "keyword" | "llm"
    distress_trajectory: list[int]
    code_switching: bool
```

- [ ] **Step 4: Update make_state helper in test_nodes.py**

In `tests/test_nodes.py`, add to the `defaults` dict inside `make_state`:
```python
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
```
(Add these after the `"clinical_flags": [],` line. Also add `"distress_trajectory": [],` and `"code_switching": False,` if not already present.)

- [ ] **Step 5: Update make_full_state helper in test_routing.py**

In `tests/test_routing.py`, add to the `defaults` dict inside `make_full_state`:
```python
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "distress_trajectory": [],
        "code_switching": False,
```

- [ ] **Step 6: Update test_rules_integration.py — helpers and tests**

In `tests/test_rules_integration.py`:

**(a)** In the `_state()` helper, replace `"crisis_occurred_this_session": False,` with:
```python
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
```

**(b)** In the `_freeflow_state()` helper, replace `"crisis_occurred_this_session": False,` with:
```python
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
```

**(c)** Replace `test_state_schema_includes_crisis_fields` (lines 274–280):
```python
def test_state_schema_includes_crisis_fields():
    """SageState TypedDict must declare crisis_state, s7_result, and distress_trajectory."""
    from sage_poc.state import SageState
    import typing
    hints = typing.get_type_hints(SageState)
    assert "crisis_state" in hints, "SageState must include crisis_state"
    assert "s7_result" in hints, "SageState must include s7_result"
    assert "distress_trajectory" in hints, "SageState must include distress_trajectory"
    assert "crisis_occurred_this_session" not in hints, "legacy field must be removed"
```

**(d)** Replace `test_post_crisis_session_injection_fires_on_subsequent_safe_turn` (lines 283–292):
```python
def test_post_crisis_session_injection_fires_on_subsequent_safe_turn():
    """After a crisis turn (crisis_state='monitoring'), subsequent safe turns get post-crisis guidance."""
    state = _freeflow_state(
        message_en="I feel a bit better today",
        crisis_state="monitoring",
    )
    system_str, _ = compose_prompt(state)
    assert "POST-CRISIS" in system_str or "crisis" in system_str.lower(), (
        "Post-crisis injection must appear in system prompt when crisis_state='monitoring'"
    )
```

**(e)** Replace `test_post_crisis_injection_absent_on_normal_session` (lines 295–302):
```python
def test_post_crisis_injection_absent_on_normal_session():
    """With crisis_state='none', post-crisis injection must NOT fire."""
    state = _freeflow_state(
        message_en="I feel anxious today",
        crisis_state="none",
    )
    system_str, _ = compose_prompt(state)
    assert "POST-CRISIS" not in system_str
```

- [ ] **Step 7: Update make_e2e_state and _CARRY_FIELDS in test_graph.py**

In `tests/test_graph.py`:

Replace `_CARRY_FIELDS` tuple:
```python
_CARRY_FIELDS = (
    "turn_count", "clinical_flags", "conversation_history",
    "active_skill_id", "active_step_id", "emotional_intensity", "engagement",
    "crisis_state",
)
```

In `make_e2e_state`, add to the `base` dict:
```python
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "distress_trajectory": [],
        "code_switching": False,
```
(Remove `"crisis_occurred_this_session"` if present in base dict — it was never there per current code.)

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && python -m pytest tests/test_state.py tests/test_nodes.py tests/test_routing.py -v`

Expected: All tests pass. (test_rules_integration.py will fail at this point because freeflow_respond still reads `crisis_occurred_this_session` — that is fixed in Task 6.)

- [ ] **Step 9: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git add src/sage_poc/state.py tests/test_state.py tests/test_nodes.py tests/test_routing.py tests/test_graph.py tests/test_rules_integration.py
git commit -m "feat(state): replace crisis_occurred_this_session with crisis_state + s7 fields"
```

---

## Task 2: S7 post-crisis classifier module

**Files:**
- Create: `src/sage_poc/nodes/post_crisis_classifier.py`
- Create: `tests/test_post_crisis_classifier.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_post_crisis_classifier.py
import pytest
from unittest.mock import MagicMock
from sage_poc.nodes.post_crisis_classifier import evaluate_s7, _VALID_LABELS


def test_recovery_keyword_returns_recovering():
    label, method = evaluate_s7("thank you, I'm feeling better now")
    assert label == "RECOVERING"
    assert method == "keyword"


def test_still_distressed_keyword_returns_still_distressed():
    # S7's STILL_DISTRESSED tier covers the gap between "I'm fine" and explicit harm language.
    # Explicit crisis phrases ("want to die", etc.) are excluded — S1–S6 catch those before S7 runs.
    label, method = evaluate_s7("I'm still feeling down, nothing has changed")
    assert label == "STILL_DISTRESSED"
    assert method == "keyword"


def test_no_keyword_falls_back_to_llm():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="UNCLEAR")
    label, method = evaluate_s7("I don't know", llm=mock_llm)
    assert label == "UNCLEAR"
    assert method == "llm"
    # LLM was called with only the current message — no conversation history
    call_args = mock_llm.invoke.call_args[0][0]
    assert len(call_args) == 2  # system + user only
    assert call_args[1]["role"] == "user"
    assert call_args[1]["content"] == "I don't know"


def test_llm_invalid_label_falls_back_to_unclear():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="CONFUSED_RESPONSE")
    label, method = evaluate_s7("something unknown", llm=mock_llm)
    assert label == "UNCLEAR"
    assert method == "llm"


def test_all_valid_labels_defined():
    assert _VALID_LABELS == {"RECOVERING", "STILL_DISTRESSED", "UNCLEAR", "NEW_CRISIS"}


def test_still_distressed_keyword_checked_before_recovery():
    """A message containing both a non-crisis distress signal and a recovery phrase: STILL_DISTRESSED wins."""
    label, method = evaluate_s7("nothing has changed but thank you for asking")
    assert label == "STILL_DISTRESSED"
    assert method == "keyword"


def test_crisis_phrase_not_in_still_distressed_keywords():
    """Explicit crisis phrases must NOT be in _STILL_DISTRESSED_KEYWORDS — S1–S6 catch those first."""
    from sage_poc.nodes.post_crisis_classifier import _STILL_DISTRESSED_KEYWORDS
    assert "want to die" not in _STILL_DISTRESSED_KEYWORDS
    assert "going to end it" not in _STILL_DISTRESSED_KEYWORDS
    assert "want to hurt myself" not in _STILL_DISTRESSED_KEYWORDS
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && python -m pytest tests/test_post_crisis_classifier.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sage_poc.nodes.post_crisis_classifier'`

- [ ] **Step 3: Create post_crisis_classifier.py**

```python
# src/sage_poc/nodes/post_crisis_classifier.py
from __future__ import annotations

_RECOVERY_KEYWORDS = frozenset([
    "feeling better", "feel better", "better now", "much better", "a lot better",
    "calmer", "calm now", "calmed down",
    "okay now", "i'm okay", "im okay", "i am okay",
    "thank you", "thanks for", "that helped", "that was helpful",
    "relieved", "feel relieved", "feeling relieved",
    "safer", "feel safe", "feeling safe",
    "not thinking about", "stopped thinking about",
    "going to call", "called the", "reached out", "got support", "got help",
])

_STILL_DISTRESSED_KEYWORDS = frozenset([
    # Non-crisis distress signals only — phrases that overlap with S1–S6 crisis lexicon are
    # intentionally excluded. If a message contains "want to die" or "going to end it",
    # S1–S6 set is_safe=False and _route_after_safety routes to crisis before S7 is relevant.
    "still not okay", "still not well", "still not good",
    "still feel down", "still feeling down", "still feel low", "still feeling low",
    "still struggling", "still the same", "still upset",
    "nothing has changed", "nothing changed", "nothing is different",
    "doesn't help", "does not help", "doesn't work", "does not work",
    "nothing helps", "nothing works",
    "same as before", "same as always",
    "can't stop thinking", "cannot stop thinking",
    "still can't", "haven't been able to",
])

S7_SYSTEM = (
    "You are a clinical triage classifier. A user was recently in acute crisis. "
    "Classify their CURRENT message ONLY (ignore any prior context) using one of four labels:\n\n"
    "RECOVERING       — user shows relief, improved mood, gratitude, or reduced distress\n"
    "STILL_DISTRESSED — user remains in active distress but without new explicit harm intent\n"
    "UNCLEAR          — insufficient information to classify\n"
    "NEW_CRISIS       — user shows new or escalating explicit harm intent\n\n"
    "Respond with exactly one word: RECOVERING, STILL_DISTRESSED, UNCLEAR, or NEW_CRISIS."
)

_VALID_LABELS = frozenset({"RECOVERING", "STILL_DISTRESSED", "UNCLEAR", "NEW_CRISIS"})


def evaluate_s7(message_en: str, llm=None) -> tuple[str, str]:
    """Return (label, method) where method is 'keyword' or 'llm'.

    Deterministic keyword tier runs first; STILL_DISTRESSED checked before RECOVERING.
    LLM is called only when keywords produce no match.
    Evaluates the current message in isolation — no conversation history passed to LLM.
    """
    text = message_en.lower()

    for kw in _STILL_DISTRESSED_KEYWORDS:
        if kw in text:
            return "STILL_DISTRESSED", "keyword"

    for kw in _RECOVERY_KEYWORDS:
        if kw in text:
            return "RECOVERING", "keyword"

    if llm is None:
        from sage_poc.llm import get_classifier
        llm = get_classifier()

    messages = [
        {"role": "system", "content": S7_SYSTEM},
        {"role": "user", "content": message_en},
    ]
    response = llm.invoke(messages)
    label = response.content.strip().upper()
    if label not in _VALID_LABELS:
        return "UNCLEAR", "llm"
    return label, "llm"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && python -m pytest tests/test_post_crisis_classifier.py -v`
Expected: 6/6 PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git add src/sage_poc/nodes/post_crisis_classifier.py tests/test_post_crisis_classifier.py
git commit -m "feat(nodes): add S7 post-crisis classifier with keyword tier and LLM fallback"
```

---

## Task 3: safety_check_node — S7 integration

**Files:**
- Modify: `src/sage_poc/nodes/safety_check.py`
- Modify: `tests/test_nodes.py` (add S7 integration tests)

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_nodes.py`:

```python
def test_s7_not_called_when_crisis_state_is_none():
    """S7 classifier must be skipped when crisis_state is 'none'."""
    state = make_state(raw_message="I feel okay", crisis_state="none")
    result = safety_check_node(state)
    assert result["s7_result"] is None
    assert result["s7_method"] is None


def test_s7_called_when_crisis_state_is_monitoring():
    """S7 classifier must fire when crisis_state is 'monitoring'."""
    state = make_state(
        raw_message="thank you, feeling much better",
        crisis_state="monitoring",
    )
    result = safety_check_node(state)
    assert result["s7_result"] == "RECOVERING"
    assert result["s7_method"] == "keyword"


def test_s7_monitoring_still_distressed_keyword():
    state = make_state(
        raw_message="nothing has changed, I still feel the same",
        crisis_state="monitoring",
    )
    result = safety_check_node(state)
    assert result["s7_result"] == "STILL_DISTRESSED"
    assert result["s7_method"] == "keyword"


def test_safety_check_returns_crisis_state_unchanged():
    """safety_check_node passes crisis_state through unchanged."""
    state = make_state(raw_message="I feel okay", crisis_state="monitoring")
    result = safety_check_node(state)
    assert result["crisis_state"] == "monitoring"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && python -m pytest tests/test_nodes.py::test_s7_not_called_when_crisis_state_is_none -v`
Expected: FAIL — `s7_result` not in result dict (safety_check_node doesn't return it yet)

- [ ] **Step 3: Update safety_check_node**

In `src/sage_poc/nodes/safety_check.py`, modify the `safety_check_node` function. Replace the `return` statement at the end (lines 71–80) with:

```python
    crisis_state = state.get("crisis_state", "none")
    s7_result: str | None = None
    s7_method: str | None = None

    if crisis_state == "monitoring":
        from sage_poc.nodes.post_crisis_classifier import evaluate_s7
        s7_result, s7_method = evaluate_s7(message_en)

    return {
        "detected_language": lang,
        "message_en": message_en,
        "is_safe": len(new_crisis_flags) == 0,
        "crisis_flags": new_crisis_flags,
        "clinical_flags": all_clinical,
        "distress_trajectory": trajectory,
        "code_switching": code_switching,
        "crisis_state": crisis_state,
        "s7_result": s7_result,
        "s7_method": s7_method,
        "path": state["path"] + ["safety_check"],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && python -m pytest tests/test_nodes.py -v`
Expected: All tests pass, including the 4 new S7 tests

- [ ] **Step 5: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git add src/sage_poc/nodes/safety_check.py tests/test_nodes.py
git commit -m "feat(safety_check): integrate S7 post-crisis classifier for monitoring state"
```

---

## Task 4: graph.py — state transitions and monitoring-aware routing

**Files:**
- Modify: `src/sage_poc/graph.py`
- Modify: `tests/test_routing.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_routing.py`:

```python
# --- _route_after_safety with monitoring state ---

def test_route_safe_in_monitoring_when_s1_s6_safe_and_s7_recovering():
    """In monitoring state with S1-S6 clear and S7=RECOVERING, route to safe."""
    state = make_full_state(
        is_safe=True,
        crisis_state="monitoring",
        s7_result="RECOVERING",
    )
    assert _route_after_safety(state) == "safe"


def test_route_safe_in_monitoring_when_s7_still_distressed():
    """STILL_DISTRESSED does NOT re-route to crisis — post_crisis_check_in handles it."""
    state = make_full_state(
        is_safe=True,
        crisis_state="monitoring",
        s7_result="STILL_DISTRESSED",
    )
    assert _route_after_safety(state) == "safe"


def test_route_safe_in_monitoring_when_s7_unclear():
    state = make_full_state(
        is_safe=True,
        crisis_state="monitoring",
        s7_result="UNCLEAR",
    )
    assert _route_after_safety(state) == "safe"


def test_route_crisis_in_monitoring_when_s7_new_crisis():
    """S7=NEW_CRISIS re-routes to crisis even when S1-S6 didn't fire."""
    state = make_full_state(
        is_safe=True,
        crisis_state="monitoring",
        s7_result="NEW_CRISIS",
    )
    assert _route_after_safety(state) == "crisis"


def test_route_crisis_in_monitoring_when_s1_s6_fire():
    """Direct S1-S6 crisis flag always routes to crisis regardless of monitoring state."""
    state = make_full_state(
        is_safe=False,
        crisis_state="monitoring",
        s7_result="STILL_DISTRESSED",
    )
    assert _route_after_safety(state) == "crisis"
```

Also add `"crisis_state": "none"` and `"s7_result": None` to `make_full_state` defaults in test_routing.py if not already done in Task 1 Step 5.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && python -m pytest tests/test_routing.py -k "monitoring" -v`
Expected: FAIL — current `_route_after_safety` only checks `is_safe`

- [ ] **Step 3: Update _route_after_safety in graph.py**

Replace `_route_after_safety` (lines 70–71):
```python
def _route_after_safety(state: SageState) -> str:
    return "safe" if state["is_safe"] else "crisis"
```
with:
```python
def _route_after_safety(state: SageState) -> str:
    if state.get("crisis_state") == "monitoring":
        # In monitoring: only re-escalate if S1-S6 fired directly or S7 classified a new crisis
        if not state["is_safe"] or state.get("s7_result") == "NEW_CRISIS":
            return "crisis"
        return "safe"
    return "safe" if state["is_safe"] else "crisis"
```

- [ ] **Step 4: Update _crisis_response_node in graph.py**

In `_crisis_response_node`, replace line 66:
```python
        "crisis_occurred_this_session": True,
```
with:
```python
        "crisis_state": "monitoring",
        "s7_result": None,
        "s7_method": None,
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && python -m pytest tests/test_routing.py -v`
Expected: All routing tests pass (including the 5 new monitoring tests)

- [ ] **Step 6: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git add src/sage_poc/graph.py tests/test_routing.py
git commit -m "feat(graph): monitoring-aware routing and crisis_state transitions"
```

---

## Task 5: post_crisis_check_in skill JSON

**Files:**
- Create: `src/sage_poc/skills/post_crisis_check_in.json`
- Modify: `tests/test_skill_schema.py` (add load test for new skill)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_skill_schema.py`:
```python
def test_post_crisis_check_in_skill_loads_and_validates():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("post_crisis_check_in")
    assert skill.skill_id == "post_crisis_check_in"
    assert len(skill.steps) == 2
    assert skill.steps[0].step_id == "acknowledge_and_check"
    assert skill.steps[1].step_id == "bridge_or_close"
    assert skill.target_presentations == []
    assert skill.semantic_description == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && python -m pytest tests/test_skill_schema.py::test_post_crisis_check_in_skill_loads_and_validates -v`
Expected: FAIL with `FileNotFoundError` (JSON doesn't exist yet)

- [ ] **Step 3: Create the skill JSON**

Create `src/sage_poc/skills/post_crisis_check_in.json`:

```json
{
  "skill_id": "post_crisis_check_in",
  "skill_name": "Post-Crisis Check-In",
  "skill_type": "structured",
  "evidence_base": "ASIST (2018); SafeTALK; SAMHSA Safe Messaging Guidelines (2023)",
  "target_presentations": [],
  "semantic_description": "",
  "steps": [
    {
      "step_id": "acknowledge_and_check",
      "goal": "Acknowledge what the user has been through and gently check in on how they are right now",
      "technique": "Active listening, validation, open check-in",
      "tone": "warm, unhurried, non-intrusive",
      "examples": [
        "I am really glad you are still here. How are you feeling right now, compared to a little while ago?",
        "That was a lot. I want to make sure you are okay. How are you doing in this moment?",
        "You have been through something difficult. I am here. How does it feel right now?"
      ]
    },
    {
      "step_id": "bridge_or_close",
      "goal": "Based on how the user responds, either bridge toward continued support or gently close the check-in",
      "technique": "Safety planning bridge or warm closure",
      "tone": "warm, steady, forward-looking",
      "examples": [
        "It sounds like things are a little steadier now. Is there anything you would find helpful to talk through?",
        "I am glad you are feeling calmer. If things get harder again, I am right here, and support is also available at 800 46342.",
        "You do not have to have everything figured out right now. I am here whenever you want to talk."
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
      "instruction": "The user is still highly distressed. Stay present and validating. Do not attempt to move forward. Express that you are here and that support is also available at 800 46342.",
      "next_step_id": "current"
    }
  ],
  "escalation_matrix": {
    "L1": "Exit skill gracefully if user explicitly requests to stop",
    "L2": "Add clinician_review flag if trauma or substance mention detected",
    "L3": "Exit immediately to crisis protocol if any new crisis signal",
    "L4": "Trigger human handoff if 3 or more crises detected in last 30 days"
  }
}
```

> **IMPORTANT — HOTLINE NUMBER:** The number `800 46342` appears in bridge_or_close examples and the step_policy instruction. This must be confirmed with CDA before production deploy. The number used here matches the existing hardcoded fallback in `graph.py` and the crisis_content JSON rules, but CDA sign-off is required.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && python -m pytest tests/test_skill_schema.py -v`
Expected: All tests pass including the new one

- [ ] **Step 5: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git add src/sage_poc/skills/post_crisis_check_in.json tests/test_skill_schema.py
git commit -m "feat(skills): add post_crisis_check_in structured skill JSON"
```

---

## Task 6: skill_select auto-select + RESOLVED transition + freeflow_respond crisis context

**Files:**
- Modify: `src/sage_poc/nodes/skill_select.py`
- Modify: `src/sage_poc/nodes/skill_executor.py` (RESOLVED transition when post_crisis_check_in completes)
- Modify: `src/sage_poc/nodes/freeflow_respond.py`
- Modify: `tests/test_rules_integration.py` (the two `compose_prompt` tests now depend on freeflow changes)

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_nodes.py` or create `tests/test_skill_select.py`:

```python
# tests/test_skill_select.py
from sage_poc.nodes.skill_select import skill_select_node


def _ss_state(**overrides):
    base = {
        "raw_message": "",
        "detected_language": "en",
        "message_en": "",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 1.0,
        "emotional_intensity": 5,
        "engagement": 7,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
        "skill_match_method": None,
        "semantic_score": None,
        "distress_trajectory": [],
        "code_switching": False,
    }
    base.update(overrides)
    return base


def test_monitoring_state_always_selects_post_crisis_check_in():
    """When crisis_state=='monitoring', skill_select bypasses keyword/semantic and returns post_crisis_check_in."""
    state = _ss_state(
        message_en="I feel a bit calmer now",
        crisis_state="monitoring",
    )
    result = skill_select_node(state)
    assert result["active_skill_id"] == "post_crisis_check_in"
    assert result["skill_match_method"] == "post_crisis_auto_select"
    assert result["active_step_id"] == "acknowledge_and_check"


def test_monitoring_state_continues_from_current_step_if_already_in_skill():
    """If post_crisis_check_in is already active on step 2, skill_select preserves that step."""
    state = _ss_state(
        message_en="I feel a bit calmer",
        crisis_state="monitoring",
        active_skill_id="post_crisis_check_in",
        active_step_id="bridge_or_close",
    )
    result = skill_select_node(state)
    assert result["active_skill_id"] == "post_crisis_check_in"
    assert result["active_step_id"] == "bridge_or_close"


def test_normal_state_not_affected_by_post_crisis_check_in_in_registry():
    """post_crisis_check_in's empty target_presentations must not match via keyword or semantic."""
    state = _ss_state(
        message_en="I keep thinking everything is my fault",
        crisis_state="none",
    )
    result = skill_select_node(state)
    assert result["active_skill_id"] != "post_crisis_check_in"


def test_resolved_state_falls_through_to_normal_skill_matching():
    """In resolved state, skill_select must use normal keyword/semantic matching, not auto-select."""
    state = _ss_state(
        message_en="I keep thinking everything is my fault",
        crisis_state="resolved",
    )
    result = skill_select_node(state)
    assert result["active_skill_id"] == "cbt_thought_record"
    assert result["skill_match_method"] == "keyword"
```

Add to `tests/test_skill_select.py` for the RESOLVED transition:
```python
def test_skill_executor_sets_resolved_when_post_crisis_skill_completes():
    """skill_executor_node must write crisis_state='resolved' when post_crisis_check_in finishes."""
    from sage_poc.nodes.skill_executor import skill_executor_node
    # Build a state where bridge_or_close is the active step and message is long enough to advance
    state = _ss_state(
        message_en="I feel much steadier now and I think I am okay to continue with my day",
        crisis_state="monitoring",
        active_skill_id="post_crisis_check_in",
        active_step_id="bridge_or_close",
        emotional_intensity=3,
        engagement=8,
    )
    result = skill_executor_node(state)
    # Skill completes: active_skill_id becomes None
    assert result["active_skill_id"] is None, "Skill must be cleared when bridge_or_close completes"
    assert result["crisis_state"] == "resolved", (
        "crisis_state must transition to 'resolved' when post_crisis_check_in finishes"
    )
```

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && python -m pytest tests/test_skill_select.py -v`
Expected: FAIL — `post_crisis_check_in` not in SKILL_REGISTRY, auto-select guard not present, resolved transition not in skill_executor

- [ ] **Step 2: Update skill_select.py**

In `src/sage_poc/nodes/skill_select.py`:

**(a)** Add `"post_crisis_check_in"` to `SKILL_REGISTRY`:
```python
SKILL_REGISTRY = ["cbt_thought_record", "grounding_5_4_3_2_1", "sleep_hygiene", "post_crisis_check_in"]
```

**(b)** Add the auto-select guard at the top of `skill_select_node`, before the keyword loop:
```python
def skill_select_node(state: SageState) -> dict:
    # Post-crisis auto-select: bypass keyword and semantic matching entirely
    if state.get("crisis_state") == "monitoring":
        skill_id = "post_crisis_check_in"
        skill = _SKILLS[skill_id]
        current_step = (
            state.get("active_step_id")
            if state.get("active_skill_id") == skill_id
            else skill.steps[0].step_id
        )
        return {
            "active_skill_id": skill_id,
            "active_step_id": current_step,
            "skill_match_method": "post_crisis_auto_select",
            "semantic_score": None,
            "path": state["path"] + ["skill_select"],
        }

    message = state["message_en"].lower()
    # ... rest of existing function unchanged (keyword loop, then semantic fallback)
```

- [ ] **Step 3: Update skill_executor.py — RESOLVED transition**

In `src/sage_poc/nodes/skill_executor.py`, find the `return` statement at the end of `skill_executor_node` (lines 164–170):

```python
    return {
        "step_instruction": result["instruction"],
        "executed_step_id": step_id,
        "active_step_id": result["next_step_id"],
        "active_skill_id": None if result.get("skill_complete") else skill_id,
        "escalation_triggered": None,
        "path": state["path"] + ["skill_executor"],
    }
```

Replace with:

```python
    crisis_state_update: dict = {}
    if result.get("skill_complete") and skill_id == "post_crisis_check_in":
        crisis_state_update = {"crisis_state": "resolved"}

    return {
        "step_instruction": result["instruction"],
        "executed_step_id": step_id,
        "active_step_id": result["next_step_id"],
        "active_skill_id": None if result.get("skill_complete") else skill_id,
        "escalation_triggered": None,
        "path": state["path"] + ["skill_executor"],
        **crisis_state_update,
    }
```

- [ ] **Step 4: Update freeflow_respond.py**

In `src/sage_poc/nodes/freeflow_respond.py`:

**(a)** Replace lines 88–90 (session_flags block):
```python
    # Old:
    if state.get("crisis_occurred_this_session"):
        session_flags.append("crisis_occurred")
```
with:
```python
    # "resolved" is included: the L5 heightened-sensitivity prompt layer stays active
    # even after the skill completes, so the LLM remains careful for the rest of the session.
    if state.get("crisis_state") in ("active", "monitoring", "resolved"):
        session_flags.append("crisis_occurred")
```

**(b)** In the `user_parts` section, after the `intent_line` block (after line ~131), add s7 context injection for monitoring only (not resolved):
```python
    # POST-CRISIS CONTEXT block fires only in monitoring state, not resolved.
    # In resolved state the session_flag 'crisis_occurred' (above) keeps the LLM
    # sensitised without pinning every response to the crisis event.
    if state.get("crisis_state") == "monitoring":
        s7 = state.get("s7_result") or "UNCLEAR"
        user_parts.append(
            f"POST-CRISIS CONTEXT: The user was recently in crisis. "
            f"S7 recovery classifier result: {s7}. "
            f"Respond with extra warmth, patience, and safety-consciousness. "
            f"Do not probe for details of the crisis. Meet the user where they are."
        )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && python -m pytest tests/test_skill_select.py tests/test_rules_integration.py -v`
Expected: All tests pass (including the two compose_prompt post-crisis tests now fixed, and the RESOLVED transition test)

- [ ] **Step 7: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git add src/sage_poc/nodes/skill_select.py src/sage_poc/nodes/skill_executor.py src/sage_poc/nodes/freeflow_respond.py tests/test_skill_select.py
git commit -m "feat(skill_select, skill_executor, freeflow): post-crisis auto-select, resolved transition, crisis context"
```

---

## Task 7: output_gate audit extension + end-to-end tests

**Files:**
- Modify: `src/sage_poc/nodes/output_gate.py`
- Modify: `tests/test_graph.py` (3 new e2e tests)

- [ ] **Step 1: Write the failing e2e tests**

Add to `tests/test_graph.py`:

```python
@pytest.mark.slow
def test_crisis_response_sets_crisis_state_monitoring():
    """After crisis response node, crisis_state must be 'monitoring' (not legacy bool)."""
    from sage_poc.graph import build_graph
    graph = build_graph()
    result = asyncio.run(graph.ainvoke(make_e2e_state("I want to kill myself tonight")))
    assert result["crisis_state"] == "monitoring", (
        "crisis_response_node must set crisis_state='monitoring'"
    )
    assert result.get("crisis_occurred_this_session") is None, (
        "legacy field must not exist on output state"
    )


@pytest.mark.slow
def test_post_crisis_monitoring_routes_safe_and_activates_skill():
    """In monitoring state, a recovery message must route safe and activate post_crisis_check_in."""
    from sage_poc.graph import build_graph
    graph = build_graph()
    # Turn 1: trigger crisis
    t1 = asyncio.run(graph.ainvoke(make_e2e_state("I want to kill myself tonight")))
    assert t1["crisis_state"] == "monitoring"

    # Turn 2: recovery signal
    t2_input = carry_state(t1, "thank you, I'm feeling better now")
    assert t2_input["crisis_state"] == "monitoring", (
        "carry_state must copy crisis_state='monitoring' from t1 via _CARRY_FIELDS"
    )
    t2 = asyncio.run(graph.ainvoke(t2_input))
    assert t2["is_safe"] is True, "Recovery message must not re-trigger crisis"
    assert "crisis_response" not in t2["path"], "Must not route to crisis_response"
    assert t2["s7_result"] is not None, "S7 must have fired in monitoring state"
    assert t2["active_skill_id"] == "post_crisis_check_in", (
        "skill_select must auto-select post_crisis_check_in in monitoring state"
    )
    assert t2["response"] is not None


@pytest.mark.slow
def test_post_crisis_new_crisis_signal_rerouts_to_crisis():
    """In monitoring state, a message matching S1-S6 directly must re-route to crisis."""
    from sage_poc.graph import build_graph
    graph = build_graph()
    t1 = asyncio.run(graph.ainvoke(make_e2e_state("I want to kill myself tonight")))
    assert t1["crisis_state"] == "monitoring"

    t2 = asyncio.run(graph.ainvoke(
        carry_state(t1, "I still want to die, nothing has changed")
    ))
    assert "crisis_response" in t2["path"], "Direct crisis language must re-trigger crisis_response"
    assert t2["crisis_state"] == "monitoring"
```

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && python -m pytest tests/test_graph.py::test_crisis_response_sets_crisis_state_monitoring -v -m slow`
Expected: FAIL — result has `crisis_occurred_this_session` (not yet replaced), not `crisis_state`

(Tasks 3 and 4 already replaced the source code; this test validates the full graph wiring together.)

- [ ] **Step 2: Extend output_gate audit log**

In `src/sage_poc/nodes/output_gate.py`, inside the `if AUDIT_LOG_ENABLED:` block, add to the `audit` dict:
```python
            "crisis_state": state.get("crisis_state", "none"),
            "s7_result": state.get("s7_result"),
            "s7_method": state.get("s7_method"),
```

Add these lines after `"is_safe": state.get("is_safe"),` in the existing audit dict.

- [ ] **Step 3: Run all tests**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && python -m pytest tests/ -v --ignore=tests/test_graph.py && python -m pytest tests/test_graph.py -v -m slow`

Expected: All unit tests pass. The 3 new e2e tests pass (require uvicorn/graph to be available and OpenRouter API key set).

- [ ] **Step 4: Final commit**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git add src/sage_poc/nodes/output_gate.py tests/test_graph.py
git commit -m "feat(output_gate, tests): crisis_state audit fields and post-crisis e2e tests"
```

---

## Task 8: Documentation updates

**Files:**
- Create: `docs/v7.1-post-crisis-state-addendum.md`
- Modify: find Intellie Evaluation doc — `grep -rl "SF-3\|SF-4\|Intellie" docs/` — update SF-3 and SF-4 to ADDRESSED
- Modify: find Skills inventory — `grep -rl "structured.*28\|skill.*inventory\|28 structured" docs/` — update skill count from 28 to 29
- Modify: find POC Plan — `grep -rl "POC Plan\|poc.*plan\|proof.*of.*concept" docs/` — add post-audit note

- [ ] **Step 1: Create the v7.1 addendum**

Create `docs/v7.1-post-crisis-state-addendum.md`:

```markdown
# v7.1 Addendum: Post-Crisis State Management

**Status:** Implemented post-R2 audit as a safety fix.
**Date:** 2026-05-22
**References:** Implementation plan `docs/superpowers/plans/2026-05-22-post-crisis-state-management.md`

## Change Summary

This addendum extends the v7 architecture specification to document post-crisis state
management, added after the R2 audit identified that `crisis_occurred_this_session: bool`
was never read by the routing layer (dead state).

## 1. CrisisState Field Replacement

`SageState.crisis_occurred_this_session: bool` is replaced by `SageState.crisis_state: str`
with values `"none" | "active" | "monitoring" | "resolved"`.

Rationale: the bool was a dead flag — it was written by `_crisis_response_node` but never
read by `_route_after_safety`. The richer string enum enables the monitoring→resolved
state machine described below. String literals (not a Python Enum class) are used to
preserve Cosmos DB checkpointing compatibility.

## 2. S7 Post-Crisis Classifier (Sub-component of Node 1)

S7 is a sub-component of `safety_check_node` (Node 1), not a new graph node.
It fires only when `crisis_state == "monitoring"`, evaluating the current message in
isolation with no conversation history (C-SSRS "Since Last Visit" principle; also
consistent with Woebot Safety Net and SAFE-T frameworks).

| Classification | Meaning | graph routing outcome |
|---|---|---|
| `RECOVERING` | Relief, gratitude, reduced distress | safe → post_crisis_check_in |
| `STILL_DISTRESSED` | Ongoing distress, no new harm intent | safe → post_crisis_check_in |
| `UNCLEAR` | Insufficient signal | safe → post_crisis_check_in |
| `NEW_CRISIS` | New or escalating harm intent | crisis → crisis_response |

S7 uses a two-tier architecture:
- Tier 1: deterministic keyword matching (non-crisis distress signals only — phrases
  overlapping with S1–S6 crisis lexicon are excluded because S1–S6 catch those first)
- Tier 2: LLM fallback (get_classifier model, message-only prompt, no history)

## 3. Modified _route_after_safety Routing Table

| crisis_state | is_safe (S1–S6) | s7_result | Route |
|---|---|---|---|
| none | True | — | safe |
| none | False | — | crisis |
| monitoring | True | RECOVERING / STILL_DISTRESSED / UNCLEAR | safe |
| monitoring | True | NEW_CRISIS | crisis |
| monitoring | False | any | crisis |
| resolved | True | — (S7 does not fire) | safe |
| resolved | False | — | crisis |

## 4. post_crisis_check_in Skill

A new structured skill added to the Skills Library (bringing the structured skill count
to 29). It is never selected via keyword or semantic matching (empty `target_presentations`,
empty `semantic_description`). Selection is exclusively via the `post_crisis_auto_select`
rule in `skill_select_node`.

Steps: `acknowledge_and_check` → `bridge_or_close`

Evidence base: ASIST (2018); SafeTALK; SAMHSA Safe Messaging Guidelines (2023)

## 5. State Transitions

```
NONE ──[crisis_response fires]──► MONITORING
MONITORING ──[post_crisis_check_in completes]──► RESOLVED
```

In RESOLVED state:
- S7 does not fire
- `skill_select_node` auto-select guard is skipped (normal matching resumes)
- The `crisis_occurred` session flag remains active (L5 heightened-sensitivity prompt
  injection stays on for the rest of the session)
- The explicit `POST-CRISIS CONTEXT` user-part injection is cleared

## 6. Audit Trail Extension

`output_gate_node` AUDIT log now includes: `crisis_state`, `s7_result`, `s7_method`

## 7. Clinical References

- **C-SSRS "Since Last Visit"**: isolating evaluation to the current message prevents
  prior crisis content from contaminating the recovery classifier
- **Woebot Safety Net**: post-crisis re-engagement pattern
- **SAFE-T (Suicide Assessment Five-step Evaluation and Triage)**: structured step-down
  from active crisis to monitoring and closure
```

- [ ] **Step 2: Update Intellie Evaluation — mark SF-3 and SF-4 as ADDRESSED**

Find the Intellie Evaluation file:
```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
grep -rl "SF-3\|SF-4\|Intellie" docs/ | head -5
```

In the found file, locate entries for SF-3 (post-crisis session handling) and SF-4 (cumulative distress) and update their status from the current value to `ADDRESSED`. Add a reference: `Implementation: docs/superpowers/plans/2026-05-22-post-crisis-state-management.md`

- [ ] **Step 3: Update Skills & Knowledge Base inventory — skill count 28 → 29**

Find the skills inventory file:
```bash
grep -rl "28 structured\|structured.*28\|skill.*count\|skills.*library" docs/ | head -5
```

In the found file, update the structured skill count from 28 to 29 and add `post_crisis_check_in` to the skill list with: `Post-Crisis Check-In | acknowledge_and_check → bridge_or_close | ASIST (2018); SafeTALK; SAMHSA Safe Messaging (2023) | Post-audit safety addition`

- [ ] **Step 4: Add post-audit note to POC Plan**

Find the POC plan file:
```bash
grep -rl "POC Plan\|poc.*test.*suite\|proof of concept" docs/ | head -5
```

Add a note under the test suite section:
```
Post-audit addition (2026-05-22): post-crisis state management (crisis_state field,
S7 classifier, post_crisis_check_in skill) added as a safety fix after R2 audit
identified dead crisis_occurred_this_session flag. Three e2e test scenarios added
to tests/test_graph.py: crisis-then-monitoring, monitoring-then-recovery, monitoring-then-recrisis.
```

**Post-audit addition (2026-05-22):** post-crisis state management (crisis_state field,
S7 classifier, post_crisis_check_in skill) added as a safety fix after R2 audit
identified dead crisis_occurred_this_session flag. Three e2e test scenarios added
to tests/test_graph.py: crisis-then-monitoring, monitoring-then-recovery, monitoring-then-recrisis.

- [ ] **Step 5: Commit all documentation**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git add docs/v7.1-post-crisis-state-addendum.md
git add $(git diff --name-only docs/)
git commit -m "docs: v7.1 addendum, Intellie SF-3/SF-4 addressed, skill count 28->29, POC plan note"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] `CrisisState` enum (as string literals) replaces `crisis_occurred_this_session: bool` — Task 1
- [x] `_crisis_response_node` transitions to `"monitoring"` — Task 4 Step 4
- [x] S7 classifier: deterministic keywords first, LLM fallback, evaluates current message only — Task 2
- [x] S7 keyword tier excludes S1-S6 crisis phrases — Task 2 Step 3 and test `test_crisis_phrase_not_in_still_distressed_keywords`
- [x] S7 fires only when `crisis_state == "monitoring"` — Task 3 Step 3
- [x] `_route_after_safety`: monitoring state routes safe unless S1-S6 fire or S7=NEW_CRISIS — Task 4 Step 3
- [x] `post_crisis_check_in` skill: 2 steps (acknowledge_and_check, bridge_or_close) — Task 5
- [x] `post_crisis_auto_select` rule in `skill_select_node`; falls through on `"resolved"` — Task 6 Step 2
- [x] `skill_executor_node` writes `crisis_state: "resolved"` when skill completes — Task 6 Step 3
- [x] freeflow session_flags include `"resolved"` (L5 stays active); `POST-CRISIS CONTEXT` block fires on `"monitoring"` only — Task 6 Step 5
- [x] Audit trail extended with `crisis_state`, `s7_result`, `s7_method` — Task 7 Step 2
- [x] All test helpers updated (make_e2e_state, _CARRY_FIELDS, make_full_state, _state, _freeflow_state) — Task 1
- [x] carry_state preservation of `crisis_state` explicitly asserted in e2e test — Task 7 Step 1
- [x] Documentation: v7.1 addendum, Intellie Evaluation, Skills inventory, POC Plan — Task 8

**Files with `crisis_occurred_this_session` — all removed:**
- `src/sage_poc/state.py` — Task 1 Step 3
- `src/sage_poc/graph.py` — Task 4 Step 4
- `src/sage_poc/nodes/freeflow_respond.py` — Task 6 Step 5
- `tests/test_rules_integration.py` — Task 1 Step 6
- `tests/test_nodes.py` — Task 1 Step 4
- `tests/test_routing.py` — Task 1 Step 5
- `tests/test_graph.py` — Task 1 Step 7

**Deferred (out of scope for this plan):**
- `crisis_history` audit field (audit trail of multiple crisis events per session) — mentioned in spec, deferred
- `post_crisis_skill_step` in audit — `executed_step_id` in existing audit already covers this
