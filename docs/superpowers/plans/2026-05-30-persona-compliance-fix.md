# Persona Compliance Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix GPT-4o persona violations (banned openers "It sounds like", "That sounds") at emotional_intensity ≥ 7. Fix 1 treats the root cause at L2. Fix 2 adds a deterministic banned opener gate at Node 8 using a graph-level retry loop — generation stays in Node 7, gating stays in Node 8, routing stays in the graph.

**Architecture:** Five files, no schema-breaking changes, no new nodes.
- **Fix 1** (`composer.py`): Replace vague "Prioritise validation" in `_INTENSITY_GUIDANCE["high"]` with behaviorally specific instruction that aligns with L0 and names banned openers at the generation point.
- **Fix 2** (`state.py`, `output_gate.py`, `graph.py`, `composer.py`, `freeflow_respond.py`): Deterministic detection in output_gate → early return with correction flag → graph routes back to freeflow_respond → freeflow_respond re-runs with correction appended → output_gate runs again. Max 1 retry enforced by `banned_opener_retry_count` in state.

**Root cause reference:** RCA 2026-05-30. RC-A: L2 "Prioritise validation" is an active directive 9 words from the user message that overrides L0's stylistic ban 600+ words earlier. RC-C: near-match evasion.

**Tech Stack:** Python 3.11+, pytest, pytest-asyncio, unittest.mock, uv

---

## Why graph-level retry, not inline retry in output_gate

The original plan had output_gate importing `compose_prompt`, `get_responder`, and `resilient_invoke` to retry inline. This violates v7 cardinal rule: Node 8 is a gate, not a generator. Generation belongs in Node 7. The graph-level approach:

- output_gate adds zero new imports (only `re`, already imported)
- No node reaches into another node's responsibilities
- The retry appears in the audit path as `output_gate_banned_opener_retry` — fully visible to the LangGraph checkpointer
- Loop termination is `banned_opener_retry_count` in state, capped at 1 by output_gate

---

## File Map

| Action | Path | What changes |
|---|---|---|
| Modify | `src/sage_poc/state.py` | +2 fields: `banned_opener_retry_count`, `banned_opener_correction` |
| Modify | `src/sage_poc/prompts/composer.py` | Line 89: Fix 1 string + 4-line correction consumption block |
| Modify | `src/sage_poc/nodes/output_gate.py` | 3 module-level constants + ~25-line gate block + 2 fields in return dict |
| Modify | `src/sage_poc/nodes/freeflow_respond.py` | +1 field in return dict: `banned_opener_correction: None` |
| Modify | `src/sage_poc/graph.py` | `_route_after_output_gate` function + change line 189 to conditional edge |
| Create | `tests/test_composer_intensity.py` | 5 tests for Fix 1 |
| Create | `tests/test_output_gate_banned_opener.py` | 6 tests for Fix 2 (state-based assertions) |

---

## Task 1 — Write Failing Tests for Fix 1 (L2 Intensity Guidance)

**Files:**
- Create: `sage-poc/tests/test_composer_intensity.py`

- [ ] **Step 1: Create the test file**

```python
"""Tests for L2 intensity guidance — persona compliance fix.

Root cause (RCA 2026-05-30): 'Prioritise validation' at intensity >= 7 triggers
GPT-4o's RLHF-encoded reflective paraphrase behavior, overriding L0's ban on
'It sounds like' / 'That sounds' 600+ words earlier.
"""
import pytest


def test_high_intensity_guidance_no_prioritise_validation():
    """'Prioritise validation' must not appear in the high-intensity guidance string."""
    from sage_poc.prompts.composer import _INTENSITY_GUIDANCE
    assert "Prioritise validation" not in _INTENSITY_GUIDANCE["high"], (
        f"RC-A fix not applied. Current: {_INTENSITY_GUIDANCE['high']!r}"
    )


def test_high_intensity_guidance_names_specific_action():
    """The replacement must name the specific action, not an abstract directive."""
    from sage_poc.prompts.composer import _INTENSITY_GUIDANCE
    guidance = _INTENSITY_GUIDANCE["high"]
    assert "Name the specific" in guidance, (
        f"High-intensity guidance must tell GPT-4o to name the specific thing said. Got: {guidance!r}"
    )


def test_high_intensity_guidance_carries_banned_opener_constraint():
    """The banned opener constraint must appear in L2 (generation point) not just L0."""
    from sage_poc.prompts.composer import _INTENSITY_GUIDANCE
    guidance = _INTENSITY_GUIDANCE["high"]
    assert "It sounds like" in guidance or "reflective opener" in guidance, (
        f"Banned opener constraint missing from high-intensity guidance. Got: {guidance!r}"
    )


def test_high_intensity_guidance_defers_guidance():
    """'Do NOT offer guidance yet' must be preserved."""
    from sage_poc.prompts.composer import _INTENSITY_GUIDANCE
    assert "guidance" in _INTENSITY_GUIDANCE["high"].lower()


def test_compose_prompt_intensity_8_no_prioritise_validation():
    """compose_prompt at intensity=8 must not emit 'Prioritise validation' in user prompt."""
    from sage_poc.prompts.composer import compose_prompt
    state = {
        "raw_message": "I am exhausted by everything",
        "message_en": "I am exhausted by everything",
        "detected_language": "en",
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "emotional_intensity": 8,
        "engagement": 4,
        "active_skill_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "rule_fired": None,
        "escalation_triggered": None,
        "clinical_flags": [],
        "crisis_state": "none",
        "third_party_crisis": False,
        "code_switching": False,
        "s7_result": None,
        "conversation_history": [],
        "conversation_summary": None,
        "therapeutic_profile": None,
        "knowledge_passages": [],
        "knowledge_abstain": False,
        "stale_skill_id": None,
        "banned_opener_correction": None,
    }
    _, user_str, _ = compose_prompt(state)
    assert "Prioritise validation" not in user_str, (
        f"Composed user prompt must not contain 'Prioritise validation'. Excerpt: {user_str[:200]!r}"
    )
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd sage-poc && uv run pytest tests/test_composer_intensity.py -v
```

Expected: `test_high_intensity_guidance_no_prioritise_validation`, `test_high_intensity_guidance_names_specific_action`, `test_high_intensity_guidance_carries_banned_opener_constraint`, and `test_compose_prompt_intensity_8_no_prioritise_validation` FAIL. `test_high_intensity_guidance_defers_guidance` may already PASS (current string contains "guidance") — that is acceptable.

---

## Task 2 — Write Failing Tests for Fix 2 (Output Gate + Graph Routing)

**Files:**
- Create: `sage-poc/tests/test_output_gate_banned_opener.py`

- [ ] **Step 1: Create the test file**

```python
"""Tests for output_gate banned opener detection and graph-level retry.

The gate detects banned openers in response_en, returns early with
banned_opener_correction set in state, and the graph routes back to
freeflow_respond for regeneration. Generation stays in Node 7.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _base_state(**overrides) -> dict:
    base = {
        "raw_message": "I am exhausted by everything",
        "message_en": "I am exhausted by everything",
        "detected_language": "en",
        "response_en": "It sounds like you're really overwhelmed. What's been hardest?",
        "gate_path": None,
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "emotional_intensity": 8,
        "engagement": 4,
        "active_skill_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "rule_fired": None,
        "escalation_triggered": None,
        "clinical_flags": [],
        "crisis_state": "none",
        "third_party_crisis": False,
        "code_switching": False,
        "s7_result": None,
        "conversation_history": [],
        "conversation_summary": None,
        "therapeutic_profile": None,
        "knowledge_passages": [],
        "knowledge_abstain": False,
        "stale_skill_id": None,
        "cultural_output_violations": [],
        "path": ["safety_check", "intent_route", "freeflow_respond"],
        "turn_count": 1,
        "turn_number": 1,
        "session_id": None,
        "user_id": None,
        "knowledge_source": "",
        "identity_substitution_rule_id": None,
        "original_response_hash": None,
        "original_response_text": None,
        "prompt_layers": ["persona", "intent"],
        "token_usage": {},
        "resistance_score": None,
        "resistance_history": [],
        "semantic_score": None,
        "skill_match_method": None,
        "new_clinical_flags_turn": [],
        "active_step_id": None,
        "prev_step_id": None,
        "re_escalation_within_monitoring": None,
        "engagement_trajectory": [],
        "distress_trajectory": [],
        "last_turn_at": None,
        "banned_opener_retry_count": 0,
        "banned_opener_correction": None,
    }
    return {**base, **overrides}


# ---- Pattern constant tests -------------------------------------------------

def test_banned_opener_patterns_constant_exists():
    """_BANNED_OPENER_PATTERNS must be a list of regex strings in output_gate."""
    from sage_poc.nodes.output_gate import _BANNED_OPENER_PATTERNS
    assert isinstance(_BANNED_OPENER_PATTERNS, list)
    assert len(_BANNED_OPENER_PATTERNS) >= 3


@pytest.mark.parametrize("banned", [
    "It sounds like you're really overwhelmed right now.",
    "That sounds really tough. I'm here for you.",
    "it seems like things have been hard lately.",
    "That sounds really difficult.",
    "it sounds like this has been a lot.",
])
def test_banned_opener_re_catches_violations(banned):
    from sage_poc.nodes.output_gate import _BANNED_OPENER_RE
    assert _BANNED_OPENER_RE.match(banned.lstrip()), f"Pattern missed: {banned!r}"


@pytest.mark.parametrize("clean", [
    "The exhaustion you're describing is real. What's been hardest?",
    "Three years of that — what shifted recently?",
    "Carrying all of that and still showing up. What do you need most right now?",
])
def test_banned_opener_re_passes_clean_responses(clean):
    from sage_poc.nodes.output_gate import _BANNED_OPENER_RE
    assert not _BANNED_OPENER_RE.match(clean.lstrip()), f"Pattern incorrectly flagged: {clean!r}"


# ---- output_gate_node early-return tests -----------------------------------

@pytest.mark.asyncio
async def test_output_gate_returns_correction_flag_on_first_violation():
    """On first banned opener (retry_count=0), output_gate must return early with
    banned_opener_correction set and retry_count incremented to 1.
    Generation must NOT happen inside output_gate.
    """
    from sage_poc.nodes.output_gate import output_gate_node

    state = _base_state(
        response_en="It sounds like you're really overwhelmed right now.",
        banned_opener_retry_count=0,
    )

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])):
        result = await output_gate_node(state)

    assert result.get("banned_opener_correction") is not None, (
        "output_gate must set banned_opener_correction on first violation"
    )
    assert result.get("banned_opener_retry_count") == 1, (
        f"retry_count must be incremented to 1. Got: {result.get('banned_opener_retry_count')}"
    )
    assert "output_gate_banned_opener_retry" in result.get("path", []), (
        "Path must include retry marker"
    )
    # The final response must NOT be set on the early return — output_gate exits before translation
    assert "response" not in result or result.get("response") is None, (
        "response must not be finalized on early return"
    )


@pytest.mark.asyncio
async def test_output_gate_proceeds_and_flags_audit_on_second_violation():
    """On second violation (retry_count=1), output_gate must proceed (not return early)
    and set banned_opener_violation in the audit trail.
    """
    from sage_poc.nodes.output_gate import output_gate_node

    state = _base_state(
        response_en="That sounds really tough. I'm here for you.",
        banned_opener_retry_count=1,
    )

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])):
        with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", AsyncMock(return_value="...")):
            with patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()):
                result = await output_gate_node(state)

    # Normal completion — response is set
    assert result.get("response") is not None, "response must be set on second violation (proceed)"
    # retry_count reset for next turn
    assert result.get("banned_opener_retry_count") == 0, (
        "retry_count must be reset to 0 after proceeding"
    )
    assert result.get("banned_opener_correction") is None


@pytest.mark.asyncio
async def test_output_gate_resets_retry_count_on_clean_response():
    """On a clean response, output_gate must reset banned_opener_retry_count to 0."""
    from sage_poc.nodes.output_gate import output_gate_node

    clean = "The exhaustion you're describing is real. What's been hardest this week?"
    state = _base_state(response_en=clean, banned_opener_retry_count=0)

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])):
        with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", AsyncMock(return_value="...")):
            with patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()):
                result = await output_gate_node(state)

    assert result.get("banned_opener_retry_count") == 0
    assert result.get("banned_opener_correction") is None
    assert result.get("response") is not None


@pytest.mark.asyncio
async def test_output_gate_no_banned_check_for_scope_refusal():
    """Hardcoded scope_refusal response is exempt from the banned opener check."""
    from sage_poc.nodes.output_gate import output_gate_node

    state = _base_state(gate_path="scope_refusal", response_en="")

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])):
        with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", AsyncMock(return_value="...")):
            with patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()):
                result = await output_gate_node(state)

    # No early return — scope_refusal proceeds to normal completion
    assert result.get("response") is not None
    assert result.get("banned_opener_correction") is None


# ---- Graph routing tests ---------------------------------------------------

def test_route_after_output_gate_returns_freeflow_when_correction_set():
    """_route_after_output_gate must return 'freeflow_respond' when correction is set."""
    from sage_poc.graph import _route_after_output_gate
    state = {
        "banned_opener_correction": "Your previous response began with a banned opener...",
        "banned_opener_retry_count": 1,
    }
    assert _route_after_output_gate(state) == "freeflow_respond"


def test_route_after_output_gate_returns_end_when_no_correction():
    """_route_after_output_gate must return END when no correction is pending."""
    from sage_poc.graph import _route_after_output_gate
    from langgraph.graph import END
    state = {
        "banned_opener_correction": None,
        "banned_opener_retry_count": 0,
    }
    assert _route_after_output_gate(state) == END


def test_route_after_output_gate_returns_end_after_max_retries():
    """_route_after_output_gate must return END when retry_count > 1 even if correction set."""
    from sage_poc.graph import _route_after_output_gate
    from langgraph.graph import END
    state = {
        "banned_opener_correction": "some correction",
        "banned_opener_retry_count": 2,
    }
    assert _route_after_output_gate(state) == END
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd sage-poc && uv run pytest tests/test_output_gate_banned_opener.py -v
```

Expected: All fail — `_BANNED_OPENER_PATTERNS`, `_BANNED_OPENER_RE`, `_route_after_output_gate` do not yet exist.

---

## Task 3 — Fix 1: Revise L2 Intensity Guidance in `composer.py`

**Files:**
- Modify: `sage-poc/src/sage_poc/prompts/composer.py`

Two changes in this file: the `_INTENSITY_GUIDANCE["high"]` string (Fix 1) and the correction consumption block (needed for Fix 2 but logically grouped here as a composer change).

- [ ] **Step 1: Replace `_INTENSITY_GUIDANCE["high"]` (line 89)**

**Before:**
```python
    "high": "The user is significantly distressed. Prioritise validation. Hold space before offering any guidance.",
```

**After:**
```python
    "high": "The user is significantly distressed. Name the specific thing they said, directly. Ask one focused question about it. Do NOT paraphrase or reflect back what they said. Do NOT begin with 'It sounds like', 'That sounds', or any reflective opener. Do NOT offer guidance yet.",
```

- [ ] **Step 2: Add correction consumption in `compose_prompt`**

In `compose_prompt`, after the existing `user_parts.append(f"USER: {message_en}")` line (currently the last line before the token budget check), add:

```python
    # Banned opener correction — injected when output_gate detected a violation on the
    # previous generation attempt and routed back here for retry. Cleared by freeflow_respond
    # after consuming. Placed last in user role for maximum recency weight.
    correction = state.get("banned_opener_correction")
    if correction:
        user_parts.append(f"[CORRECTION]: {correction}")
        layers.append("banned_opener_correction")
```

This block goes between `user_parts.append(f"USER: {message_en}")` and the token budget enforcement block. The correction lands after the user message — maximum recency, directly before generation.

- [ ] **Step 3: Run Fix 1 tests**

```bash
cd sage-poc && uv run pytest tests/test_composer_intensity.py -v
```

Expected: All 5 PASS.

---

## Task 4 — Fix 2 Part A: Add State Fields to `state.py`

**Files:**
- Modify: `sage-poc/src/sage_poc/state.py`

- [ ] **Step 1: Add two fields to SageState**

In `SageState`, add after the existing `stale_skill_id` field:

```python
    banned_opener_retry_count: int          # 0 = first attempt; 1 = already retried; reset to 0 by output_gate on clean pass
    banned_opener_correction: Optional[str] # corrective instruction for Node 7 on retry; None when not retrying
```

- [ ] **Step 2: Add to `_build_state` in `server_helpers.py`**

In `_build_state`, add these two fields to the returned dict:

```python
        "banned_opener_retry_count": 0,
        "banned_opener_correction": None,
```

- [ ] **Step 3: Verify no import errors**

```bash
cd sage-poc && uv run python -c "from sage_poc.state import SageState; print('OK')"
```

Expected: `OK`

---

## Task 5 — Fix 2 Part B: Add Detection Logic to `output_gate.py`

**Files:**
- Modify: `sage-poc/src/sage_poc/nodes/output_gate.py`

Three sub-changes: module-level constants, gate block inside `output_gate_node`, two fields in the normal return dict.

- [ ] **Step 1: Add module-level constants after `_FORMAT_VIOLATIONS`**

After the existing `_FORMAT_VIOLATIONS = re.compile(...)` block (around line 29–37), add:

```python
# Banned opener patterns for deterministic gate check on response_en (before translation).
# Module-level list makes the pattern set configurable in Full Build without code changes.
_BANNED_OPENER_PATTERNS: list[str] = [
    r"it sounds like\b",
    r"that sounds\b",
    r"it seems like\b",
    r"i can hear (that|how|the)\b",
    r"i can see (that|how)\b",
    r"it looks like\b",
]
_BANNED_OPENER_RE = re.compile(
    r"(?i)^(" + "|".join(_BANNED_OPENER_PATTERNS) + r")"
)
_BANNED_OPENER_CORRECTION = (
    "Your previous response began with a banned opener. "
    "Respond again without beginning with 'It sounds like', 'That sounds', or any "
    "reflective paraphrase. Name the specific thing the user said and ask one direct question."
)
```

`re` is already imported. No new imports needed.

- [ ] **Step 2: Add gate block inside `output_gate_node`**

Locate the `violations = _FORMAT_VIOLATIONS.findall(response_en)` section (currently around lines 195–202). Insert the gate block **before** the format violations check and **after** the cultural rules block (lines ~166–210).

**Gate ordering (verified by post-implementation audit 2026-05-30):** The banned opener gate runs after cultural rules (identity substitution, CUO-ID-001), not before them. If a response both starts with a banned opener AND contains an identity claim, cultural rules substitute the entire response first. The substituted canned response ("I'm Sage, a wellness companion...") does not start with a banned opener, so the gate passes it cleanly. Identity-first ordering is the safer choice: the identity violation is corrected on the first pass rather than deferred to a retry. Both orderings converge to the correct outcome, but cultural-first eliminates the identity claim unconditionally.

```python
    # Banned opener gate — runs on response_en (English, before translation) for standard path only.
    # On first violation: returns early with correction flag; graph routes back to freeflow_respond.
    # On second violation (retry already happened): proceeds with response and flags audit trail.
    # No LLM calls here — generation stays in Node 7 (freeflow_respond).
    banned_opener_violation = False
    if gate_path not in ("scope_refusal", "jailbreak") and response_en:
        banned_match = _BANNED_OPENER_RE.match(response_en.lstrip())
        if banned_match:
            retry_count = state.get("banned_opener_retry_count", 0)
            if retry_count < 1:
                _log.warning(
                    "[output_gate] banned opener detected (%r) — routing back to freeflow_respond for retry",
                    banned_match.group(0),
                )
                return {
                    "banned_opener_retry_count": retry_count + 1,
                    "banned_opener_correction": _BANNED_OPENER_CORRECTION,
                    "path": path + ["output_gate_banned_opener_retry"],
                }
            else:
                banned_opener_violation = True
                _log.warning(
                    "[output_gate] banned opener persists after retry — proceeding with original, flagging audit"
                )

    violations = _FORMAT_VIOLATIONS.findall(response_en)
    if violations:
        _log.warning("[output_gate] format violations: %s", violations)
```

- [ ] **Step 3: Add `banned_opener_retry_count`, `banned_opener_correction`, and `banned_opener_violation` to the normal return dict**

In the existing return dict (currently lines 289–301), add three fields:

```python
    return {
        "response": final_response,
        "gate_path": gate_path or "standard",
        "path": path,
        "turn_count": next_turn,
        "conversation_history": new_history,
        "conversation_summary": new_summary,
        "cultural_output_violations": cultural_output_violations,
        "identity_substitution_rule_id": _identity_sub_rule_id,
        "original_response_hash": _original_response_hash,
        "original_response_text": _original_response_text,
        "last_turn_at": datetime.now(timezone.utc).isoformat(),
        "banned_opener_retry_count": 0,       # reset for next turn
        "banned_opener_correction": None,      # reset for next turn
        "banned_opener_violation": banned_opener_violation,  # audit trail
    }
```

Also add `"banned_opener_violation": banned_opener_violation` to the JSON audit dict in the `if AUDIT_LOG_ENABLED:` block.

---

## Task 6 — Fix 2 Part C: Graph Routing in `graph.py`

**Files:**
- Modify: `sage-poc/src/sage_poc/graph.py`

- [ ] **Step 1: Add `_route_after_output_gate` function**

Add the following function after the existing `_route_after_skill_executor` function (around line 140):

```python
def _route_after_output_gate(state: SageState) -> str:
    """Route back to freeflow_respond for one retry when output_gate detected a banned opener.

    Loop termination: retry_count > 1 always routes to END, even if correction is set.
    In practice, output_gate never sets banned_opener_correction when retry_count >= 1,
    so the > 1 guard is defensive.
    """
    if state.get("banned_opener_correction") and state.get("banned_opener_retry_count", 0) <= 1:
        return "freeflow_respond"
    return END
```

- [ ] **Step 2: Replace `add_edge("output_gate", END)` with a conditional edge**

In the `build_graph` function, replace line 189:

**Before:**
```python
    graph.add_edge("output_gate", END)
```

**After:**
```python
    graph.add_conditional_edges(
        "output_gate",
        _route_after_output_gate,
        {"freeflow_respond": "freeflow_respond", END: END},
    )
```

---

## Task 7 — Fix 2 Part D: Clear Correction in `freeflow_respond.py`

**Files:**
- Modify: `sage-poc/src/sage_poc/nodes/freeflow_respond.py`

- [ ] **Step 1: Add `banned_opener_correction: None` to the return dict**

In `freeflow_respond_node`, locate the return dict (currently returning `response_en`, `prompt_layers`, `token_usage`, `path`, `stale_skill_id`, and optionally `knowledge_source`). Add one field:

```python
    return {
        "response_en":             response,
        "prompt_layers":           prompt_layers,
        "token_usage":             {},
        "path":                    (state.get("path") or []) + ["freeflow_respond"],
        "stale_skill_id":          None,
        "banned_opener_correction": None,   # consumed — clear so it does not re-fire next turn
        **knowledge_source_update,
    }
```

The `banned_opener_retry_count` is NOT cleared here — output_gate resets it on clean pass. Clearing it in freeflow_respond would prevent the loop termination check in output_gate from working correctly.

---

## Task 8 — Verify All Tests Pass and Commit

- [ ] **Step 1: Run all new tests**

```bash
cd sage-poc && uv run pytest tests/test_composer_intensity.py tests/test_output_gate_banned_opener.py -v
```

Expected: All tests PASS.

- [ ] **Step 2: Run output_gate regression suite**

```bash
cd sage-poc && uv run pytest tests/test_output_gate_response_paths.py tests/test_output_gate_clinical_review.py tests/test_output_gate_session_summary.py tests/test_identity_gate.py tests/test_cultural_output.py -v 2>&1 | tail -5
```

Expected: All 98 PASS. Any failure here means the gate block or return dict change broke an existing path — investigate before committing.

- [ ] **Step 3: Run routing tests**

```bash
cd sage-poc && uv run pytest tests/test_routing.py tests/test_graph.py -v 2>&1 | tail -5
```

Expected: All PASS. The conditional edge replaces the direct edge — existing routing logic is unaffected.

- [ ] **Step 4: Run full non-slow suite**

```bash
cd sage-poc && uv run pytest --tb=short -m "not slow" -q 2>&1 | tail -5
```

Expected: Count ≥ 1383 passing. Pre-existing DB integration failure is acceptable and unrelated.

- [ ] **Step 5: Commit**

```bash
cd sage-poc && git add \
  src/sage_poc/state.py \
  src/sage_poc/prompts/composer.py \
  src/sage_poc/nodes/output_gate.py \
  src/sage_poc/nodes/freeflow_respond.py \
  src/sage_poc/graph.py \
  tests/test_composer_intensity.py \
  tests/test_output_gate_banned_opener.py

git commit -m "$(cat <<'EOF'
fix(persona): remove 'Prioritise validation' + graph-level banned opener retry

RC-A root cause (RCA 2026-05-30): L2 'Prioritise validation' at intensity >= 7
triggered GPT-4o's RLHF-encoded reflective paraphrase behavior, overriding L0's
'It sounds like' / 'That sounds' ban 600+ words earlier.

Fix 1 (composer.py): Replace vague directive with behaviorally specific instruction.
Banned opener constraint now appears in L2 (user role, 9 words from message) for
maximum recency weight, reinforcing L0's distant ban.

Fix 2 (output_gate, graph, freeflow_respond, state): Deterministic banned opener
gate at Node 8. On first violation: early return with correction flag in state;
graph routes back to Node 7 (freeflow_respond) for retry with corrective instruction
appended by composer. On second violation: proceeds with audit flag. Max 1 retry
enforced by banned_opener_retry_count in state. No LLM calls in output_gate.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

**Spec coverage:**
- ✅ Fix 1: `_INTENSITY_GUIDANCE["high"]` string — Task 3 Step 1
- ✅ Fix 1 user refinement: "Do NOT begin with 'It sounds like'" in L2 — Task 3 Step 1
- ✅ Fix 2: correction consumption in `compose_prompt` — Task 3 Step 2
- ✅ State fields: `banned_opener_retry_count`, `banned_opener_correction` — Task 4
- ✅ Fix 2: `_BANNED_OPENER_PATTERNS` configurable constant — Task 5 Step 1
- ✅ Fix 2: gate runs on `response_en` before translation — Task 5 Step 2
- ✅ Fix 2: early return (no LLM in output_gate) — Task 5 Step 2
- ✅ Fix 2: retry with corrective message at generation point — Tasks 3+5
- ✅ Fix 2: audit flag `banned_opener_violation` on second failure — Task 5 Step 3
- ✅ Fix 2: scope_refusal/jailbreak exempt — Task 5 Step 2
- ✅ Fix 2: `banned_opener_retry_count` reset to 0 on normal output_gate return — Task 5 Step 3
- ✅ Fix 2: `banned_opener_correction` cleared by `freeflow_respond` — Task 7
- ✅ Graph: `_route_after_output_gate` conditional edge — Task 6
- ✅ Graph: loop termination at `retry_count > 1` — Task 6 Step 1
- ✅ Regression tests: output_gate existing suite — Task 8 Step 2
- ✅ Regression tests: routing — Task 8 Step 3
- ✅ Finding B (language conflict): document only — Experiment 4.1 test plan
- ✅ Finding D (wallah false positive): deferred to pre-Experiment 4.1
- ✅ Finding E (CU-CS-001 anchor): deferred to pre-production

**No new imports in output_gate.py.** Only `re` (already imported) is used for the gate logic.

**Placeholder scan:** None found.

**Type consistency:** `banned_opener_retry_count: int`, `banned_opener_correction: Optional[str]`, `banned_opener_violation: bool`, `_BANNED_OPENER_PATTERNS: list[str]`, `_BANNED_OPENER_RE: re.Pattern` — used consistently across all files.
