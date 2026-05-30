# Persona Compliance Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix GPT-4o persona violations (banned openers "It sounds like", "That sounds") caused by L2's "Prioritise validation" directive competing with L0's stylistic ban at emotional_intensity ≥ 7.

**Architecture:** Three changes across two files. Fix 1 treats the root cause (L2 competing with L0) by replacing the vague "Prioritise validation" directive with behaviorally specific instruction that aligns with L0. Fix 2 adds a deterministic banned opener gate in output_gate.py (Node 8) that detects, retries with a corrective message, and flags unresolved violations in the audit trail. Fix 3 adds regression tests that make both fixes permanent. No schema changes, no new nodes, no architecture changes.

**Root cause reference:** RCA 2026-05-30. RC-A (primary): L2 "Prioritise validation" at intensity ≥ 7 is an active directive 9 words from the user message; it overrides L0's stylistic ban 600+ words earlier via recency and relevance bias. RC-C (secondary): near-match evasion — GPT-4o generates variations not exactly matching banned examples.

**Tech Stack:** Python 3.11+, pytest, pytest-asyncio, unittest.mock, uv

---

## Background

**Root cause:** `_INTENSITY_GUIDANCE["high"]` in `composer.py` (line 89) currently reads:
```
"The user is significantly distressed. Prioritise validation. Hold space before offering any guidance."
```
"Prioritise validation" triggers GPT-4o's RLHF-encoded validation behavior (reflective paraphrase openers) at the point of generation, overriding L0's constraint 600+ words earlier.

**Secondary safety net:** output_gate.py currently has no check for banned openers in `response_en`. Without a deterministic gate, any L2 fix that partially fails under edge cases (new distress phrasings, future models) will go uncaught.

---

## File Map

| Action | Path | What changes |
|---|---|---|
| Modify | `sage-poc/src/sage_poc/prompts/composer.py` | Line 89: replace `_INTENSITY_GUIDANCE["high"]` string |
| Modify | `sage-poc/src/sage_poc/nodes/output_gate.py` | Add 3 imports + `_BANNED_OPENER_PATTERNS` constant + ~30 lines of gate logic in `output_gate_node` |
| Modify | `sage-poc/tests/test_composer_intensity.py` (create) | New test file for Fix 1 |
| Modify | `sage-poc/tests/test_output_gate_banned_opener.py` (create) | New test file for Fix 2 |

---

## Task 1 — Write Failing Tests for Fix 1 (L2 Intensity Guidance)

**Files:**
- Create: `sage-poc/tests/test_composer_intensity.py`

- [ ] **Step 1: Create the test file**

Create `sage-poc/tests/test_composer_intensity.py`:

```python
"""Tests for L2 intensity guidance — persona compliance fix.

Verifies that the high-intensity directive no longer contains "Prioritise validation"
(the root cause of the "It sounds like" banned opener violations per RCA 2026-05-30)
and that the replacement string contains the required behavioral specificity.
"""
import pytest


def test_high_intensity_guidance_no_prioritise_validation():
    """'Prioritise validation' must not appear in the high-intensity guidance string.

    RC-A root cause: 'Prioritise validation' is an active directive that triggers
    GPT-4o's RLHF-encoded reflective paraphrase behavior at the generation point,
    overriding L0's stylistic ban on 'It sounds like' / 'That sounds'.
    """
    from sage_poc.prompts.composer import _INTENSITY_GUIDANCE
    assert "Prioritise validation" not in _INTENSITY_GUIDANCE["high"], (
        "RC-A fix not applied: 'Prioritise validation' still in high-intensity guidance. "
        "This triggers banned opener behavior at intensity >= 7."
    )


def test_high_intensity_guidance_contains_specific_behavioral_instruction():
    """The high-intensity guidance must name the specific behavior, not abstract directives."""
    from sage_poc.prompts.composer import _INTENSITY_GUIDANCE
    guidance = _INTENSITY_GUIDANCE["high"]
    assert "Name the specific" in guidance, (
        "High-intensity guidance must tell GPT-4o to name the specific thing said. "
        f"Current guidance: {guidance!r}"
    )


def test_high_intensity_guidance_contains_banned_opener_constraint():
    """The high-intensity guidance must carry the banned opener constraint at generation point.

    RC-C fix: placing the negative constraint in L2 (user role, 9 words from message)
    gives it maximum recency weight vs L0 (system role, 600+ words away).
    """
    from sage_poc.prompts.composer import _INTENSITY_GUIDANCE
    guidance = _INTENSITY_GUIDANCE["high"]
    # The constraint must name specific banned patterns
    assert "It sounds like" in guidance or "reflective opener" in guidance, (
        "High-intensity guidance must explicitly name banned openers at generation point. "
        f"Current guidance: {guidance!r}"
    )


def test_high_intensity_guidance_contains_no_guidance_instruction():
    """The 'do not offer guidance yet' constraint must be preserved."""
    from sage_poc.prompts.composer import _INTENSITY_GUIDANCE
    guidance = _INTENSITY_GUIDANCE["high"]
    assert "guidance" in guidance.lower(), (
        f"High-intensity guidance must still defer guidance. Current: {guidance!r}"
    )


def test_compose_prompt_high_intensity_does_not_emit_validation_word():
    """compose_prompt at intensity=8 must not include 'Prioritise validation' in user prompt."""
    from sage_poc.prompts.composer import compose_prompt
    state = {
        "raw_message": "I am really struggling right now",
        "message_en": "I am really struggling right now",
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
    }
    _, user_str, _ = compose_prompt(state)
    assert "Prioritise validation" not in user_str, (
        "Composed prompt at intensity=8 must not contain 'Prioritise validation'. "
        f"User prompt excerpt: {user_str[:200]!r}"
    )
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd sage-poc && uv run pytest tests/test_composer_intensity.py -v
```

Expected: `test_high_intensity_guidance_no_prioritise_validation` and `test_high_intensity_guidance_contains_specific_behavioral_instruction` and `test_high_intensity_guidance_contains_banned_opener_constraint` FAIL. `test_high_intensity_guidance_contains_no_guidance_instruction` may PASS (current string has "guidance"). `test_compose_prompt_high_intensity_does_not_emit_validation_word` FAILS.

If all pass before the code change: the test assertions are wrong — check the import path resolves to `composer.py` in the project, not a cached version.

---

## Task 2 — Write Failing Tests for Fix 2 (Output Gate Banned Opener Check)

**Files:**
- Create: `sage-poc/tests/test_output_gate_banned_opener.py`

- [ ] **Step 1: Create the test file**

Create `sage-poc/tests/test_output_gate_banned_opener.py`:

```python
"""Tests for output_gate banned opener detection and retry (Fix 2).

The gate runs on response_en (English, before translation) and retries once
with a corrective message appended. On second failure, it proceeds with the
original response but flags the violation in the audit trail.
"""
import re
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _base_state(**overrides) -> dict:
    base = {
        "raw_message": "I am exhausted by everything",
        "message_en": "I am exhausted by everything",
        "detected_language": "en",
        "response_en": "It sounds like you're really overwhelmed right now. What's been hardest?",
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
        "knowledge_abstain": False,
        "stale_skill_id": None,
    }
    return {**base, **overrides}


# ---- Pattern list unit tests -----------------------------------------------

def test_banned_opener_patterns_constant_exists():
    """_BANNED_OPENER_PATTERNS must be a list of regex strings in output_gate."""
    from sage_poc.nodes.output_gate import _BANNED_OPENER_PATTERNS
    assert isinstance(_BANNED_OPENER_PATTERNS, list)
    assert len(_BANNED_OPENER_PATTERNS) >= 3, "Must cover at least: it sounds like, that sounds, it seems like"


@pytest.mark.parametrize("banned_opener", [
    "It sounds like you're really overwhelmed right now.",
    "That sounds really tough. I'm here for you.",
    "it seems like things have been hard lately.",
    "It sounds like this has been a difficult week.",
    "That sounds really difficult.",
])
def test_banned_opener_regex_catches_known_violations(banned_opener):
    """The compiled pattern must match all known banned openers from the RCA."""
    from sage_poc.nodes.output_gate import _BANNED_OPENER_RE
    assert _BANNED_OPENER_RE.match(banned_opener.lstrip()), (
        f"Pattern did not catch known banned opener: {banned_opener!r}"
    )


@pytest.mark.parametrize("clean_opener", [
    "The exhaustion you're describing is real. What's been hardest?",
    "Three years is a long time to carry that. What shifted recently?",
    "Carrying that weight through everything — what's been the breaking point?",
    "Wallah, that kind of tiredness goes deep. What do you need most right now?",
])
def test_banned_opener_regex_does_not_catch_clean_responses(clean_opener):
    """The pattern must NOT match Sage's correct response style."""
    from sage_poc.nodes.output_gate import _BANNED_OPENER_RE
    assert not _BANNED_OPENER_RE.match(clean_opener.lstrip()), (
        f"Pattern incorrectly flagged a clean response: {clean_opener!r}"
    )


# ---- output_gate_node integration tests ------------------------------------

@pytest.mark.asyncio
async def test_output_gate_retries_on_banned_opener_and_uses_clean_retry():
    """When response_en starts with a banned opener, output_gate must retry once.

    Retry receives a corrective message. If the retry is clean, the clean
    response must be used as the final response_en (before translation).
    """
    from sage_poc.nodes.output_gate import output_gate_node
    from sage_poc.rules.engine import EvaluationResult

    banned_response = "It sounds like you're really overwhelmed right now. What's been hardest?"
    clean_retry = "The exhaustion you're describing is real. What's been hardest this week?"

    # Retry returns a clean response
    mock_resilient = AsyncMock(return_value=clean_retry)
    mock_eval = MagicMock(return_value=MagicMock(fired=[]))

    state = _base_state(response_en=banned_response)

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", mock_eval):
        with patch("sage_poc.nodes.output_gate.resilient_invoke", mock_resilient):
            with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", AsyncMock(return_value="...")):
                result = await output_gate_node(state)

    assert result["response"] != banned_response or result["response"] == "...", (
        "Banned response must not reach the user when a clean retry is available."
    )
    mock_resilient.assert_called_once()

    # Verify the corrective instruction was included in the retry call
    retry_call_args = mock_resilient.call_args
    retry_messages = retry_call_args[0][1]  # positional: llm, messages, node, language
    retry_user_content = retry_messages[-1]["content"]
    assert "banned opener" in retry_user_content.lower() or "It sounds like" in retry_user_content, (
        f"Retry must include corrective instruction. Got user content: {retry_user_content[:200]!r}"
    )


@pytest.mark.asyncio
async def test_output_gate_flags_audit_when_retry_also_violates():
    """When both first and retry responses start with banned openers, output_gate
    must proceed with the original but set banned_opener_violation=True in the audit log.
    """
    from sage_poc.nodes.output_gate import output_gate_node

    banned_response = "It sounds like you're overwhelmed. What's been hardest?"
    banned_retry = "That sounds really difficult. Tell me more."

    call_count = 0
    async def mock_resilient(llm, messages, node, language):
        nonlocal call_count
        call_count += 1
        return banned_retry

    state = _base_state(response_en=banned_response)

    captured_audit = {}
    original_log_info = __import__("logging").getLogger("sage_poc.nodes.output_gate").info

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])):
        with patch("sage_poc.nodes.output_gate.resilient_invoke", mock_resilient):
            with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", AsyncMock(return_value="...")):
                with patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()) as mock_audit:
                    result = await output_gate_node(state)

    assert call_count == 1, "Must retry exactly once on first violation"


@pytest.mark.asyncio
async def test_output_gate_no_retry_for_clean_response():
    """When response_en has no banned opener, output_gate must NOT call the LLM."""
    from sage_poc.nodes.output_gate import output_gate_node

    clean_response = "The exhaustion you're carrying is real. What's been the hardest part this week?"
    mock_resilient = AsyncMock()

    state = _base_state(response_en=clean_response)

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])):
        with patch("sage_poc.nodes.output_gate.resilient_invoke", mock_resilient):
            with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", AsyncMock(return_value="...")):
                await output_gate_node(state)

    mock_resilient.assert_not_called()


@pytest.mark.asyncio
async def test_output_gate_no_banned_check_for_scope_refusal():
    """scope_refusal path uses a hardcoded response — banned opener check must not run."""
    from sage_poc.nodes.output_gate import output_gate_node

    mock_resilient = AsyncMock()
    state = _base_state(gate_path="scope_refusal", response_en="")

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])):
        with patch("sage_poc.nodes.output_gate.resilient_invoke", mock_resilient):
            with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", AsyncMock(return_value="...")):
                await output_gate_node(state)

    mock_resilient.assert_not_called()
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd sage-poc && uv run pytest tests/test_output_gate_banned_opener.py -v
```

Expected failures:
- `test_banned_opener_patterns_constant_exists` → ImportError: `_BANNED_OPENER_PATTERNS` not in output_gate
- `test_banned_opener_regex_catches_known_violations` → ImportError: `_BANNED_OPENER_RE` not in output_gate
- All integration tests → no retry logic exists yet

If any pass: check that you're not importing a cached `.pyc` version. Run `find . -name "*.pyc" -delete` to clear caches.

---

## Task 3 — Fix 1: Revise L2 Intensity Guidance in `composer.py`

**Files:**
- Modify: `sage-poc/src/sage_poc/prompts/composer.py`, line 89

- [ ] **Step 1: Replace the `_INTENSITY_GUIDANCE["high"]` string**

In `sage-poc/src/sage_poc/prompts/composer.py`, replace the `"high"` entry only:

**Before (line 89):**
```python
    "high": "The user is significantly distressed. Prioritise validation. Hold space before offering any guidance.",
```

**After:**
```python
    "high": "The user is significantly distressed. Name the specific thing they said, directly. Ask one focused question about it. Do NOT paraphrase or reflect back what they said. Do NOT begin with 'It sounds like', 'That sounds', or any reflective opener. Do NOT offer guidance yet.",
```

No other lines change in this file.

- [ ] **Step 2: Run Fix 1 tests — all 5 must pass**

```bash
cd sage-poc && uv run pytest tests/test_composer_intensity.py -v
```

Expected: All 5 PASS.

- [ ] **Step 3: Confirm no regression in compose_prompt tests**

```bash
cd sage-poc && uv run pytest tests/test_composer.py tests/test_prompt_composer.py -v 2>&1 | tail -10
```

Expected: All PASS. (If no composer-specific test file exists, this will collect 0 items — that's acceptable.)

---

## Task 4 — Fix 2: Add Banned Opener Gate in `output_gate.py`

**Files:**
- Modify: `sage-poc/src/sage_poc/nodes/output_gate.py`

Three changes: new imports, new module-level constants, and a gate block inside `output_gate_node`.

- [ ] **Step 1: Add imports**

In `output_gate.py`, add these three imports after the existing imports:

```python
from sage_poc.prompts.composer import compose_prompt
from sage_poc.llm import get_responder
from sage_poc.resilience import resilient_invoke
```

- [ ] **Step 2: Add module-level constants after the existing `_FORMAT_VIOLATIONS` regex**

After the `_FORMAT_VIOLATIONS = re.compile(...)` block (around line 29–37), add:

```python
# Banned opener patterns — checked on response_en before translation.
# Configurable: clinicians can add patterns via CMS in Full Build.
# Patterns are anchored to start of response (after stripping leading whitespace).
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

- [ ] **Step 3: Add the gate block inside `output_gate_node`**

The gate runs on `response_en` after the cultural violations check and before the translation call. Locate this section in `output_gate_node` (currently around lines 195–202):

```python
    violations = _FORMAT_VIOLATIONS.findall(response_en)
    if violations:
        _log.warning("[output_gate] format violations: %s", violations)

    if lang == "ar":
        final_response = await async_translate_to_arabic(response_en)
    else:
        final_response = response_en
```

Replace it with:

```python
    violations = _FORMAT_VIOLATIONS.findall(response_en)
    if violations:
        _log.warning("[output_gate] format violations: %s", violations)

    # Banned opener gate — deterministic check on English response before translation.
    # Retries once with a corrective message. If retry also fails, proceeds with original
    # and flags in audit trail. Scope: standard path only (hardcoded refusals are exempt).
    banned_opener_violation = False
    if gate_path not in ("scope_refusal", "jailbreak") and response_en:
        banned_match = _BANNED_OPENER_RE.match(response_en.lstrip())
        if banned_match:
            _log.warning(
                "[output_gate] banned opener detected (matched: %r) — retrying",
                banned_match.group(0),
            )
            try:
                system_str, user_str, _ = compose_prompt(state)
                retry_messages = [
                    {"role": "system", "content": system_str},
                    {"role": "user", "content": user_str + "\n\n[CORRECTION]: " + _BANNED_OPENER_CORRECTION},
                ]
                retry_response = await resilient_invoke(
                    get_responder(),
                    retry_messages,
                    node="output_gate_retry",
                    language=lang,
                )
                if retry_response and not _BANNED_OPENER_RE.match(retry_response.lstrip()):
                    response_en = retry_response
                    _log.info("[output_gate] retry resolved banned opener violation")
                else:
                    banned_opener_violation = True
                    _log.warning(
                        "[output_gate] retry also produced banned opener — proceeding with original, flagging audit"
                    )
            except Exception as exc:
                banned_opener_violation = True
                _log.warning("[output_gate] banned opener retry failed: %s — proceeding with original", exc)

    if lang == "ar":
        final_response = await async_translate_to_arabic(response_en)
    else:
        final_response = response_en
```

- [ ] **Step 4: Add `banned_opener_violation` to the audit log**

In the `if AUDIT_LOG_ENABLED:` block, add one entry to the `audit` dict after the existing fields:

```python
            "banned_opener_violation": banned_opener_violation,
```

This makes persona violations queryable from the audit trail without schema changes.

- [ ] **Step 5: Run Fix 2 tests — all must pass**

```bash
cd sage-poc && uv run pytest tests/test_output_gate_banned_opener.py -v
```

Expected: All tests PASS.

---

## Task 5 — Verify Full Test Suite and Commit

- [ ] **Step 1: Run all new tests together**

```bash
cd sage-poc && uv run pytest tests/test_composer_intensity.py tests/test_output_gate_banned_opener.py -v
```

Expected: All pass. Zero failures.

- [ ] **Step 2: Run output_gate regression tests**

```bash
cd sage-poc && uv run pytest tests/test_output_gate_response_paths.py tests/test_output_gate_clinical_review.py tests/test_output_gate_session_summary.py tests/test_identity_gate.py tests/test_cultural_output.py -v 2>&1 | tail -8
```

Expected: All 98 pass. Any failure here means the new imports or the gate block broke an existing path — investigate before committing.

- [ ] **Step 3: Run full non-slow suite**

```bash
cd sage-poc && uv run pytest --tb=short -m "not slow" -q 2>&1 | tail -5
```

Expected: Total count ≥ 1383 passing (pre-existing DB integration failure is acceptable, unrelated to this change).

- [ ] **Step 4: Commit**

```bash
cd sage-poc && git add \
  src/sage_poc/prompts/composer.py \
  src/sage_poc/nodes/output_gate.py \
  tests/test_composer_intensity.py \
  tests/test_output_gate_banned_opener.py

git commit -m "$(cat <<'EOF'
fix(persona): remove 'Prioritise validation' from L2 high-intensity guidance

RC-A root cause (RCA 2026-05-30): L2's 'Prioritise validation' at intensity >= 7
triggered GPT-4o's RLHF-encoded reflective paraphrase behavior, overriding L0's
'It sounds like' / 'That sounds' ban 600+ words earlier.

Fix 1: Replace vague 'Prioritise validation' with behaviorally specific instruction
that names the required action and repeats the banned opener constraint at the
generation point (L2 user role, 9 words from user message).

Fix 2: Add deterministic banned opener gate in output_gate (Node 8). Retries once
with a corrective message; flags audit trail on second failure. Consistent with
v7 cardinal rule: safety guardrails are deterministic.

Fix 3: Regression tests — 5 for L2 guidance, 5 for output gate patterns and retry.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

**Spec coverage:**
- ✅ Fix 1 (RC-A): Replace `_INTENSITY_GUIDANCE["high"]` string — Task 3
- ✅ Fix 1 refinement (user): Add "Do NOT begin with 'It sounds like'" in L2 — Task 3
- ✅ Fix 2: `_BANNED_OPENER_PATTERNS` configurable constant — Task 4 Step 2
- ✅ Fix 2: Check runs on `response_en` before translation — Task 4 Step 3
- ✅ Fix 2: Retry with corrective message appended (not bare retry) — Task 4 Step 3
- ✅ Fix 2: Flag `banned_opener_violation` in audit on second failure — Task 4 Step 4
- ✅ Fix 2: Exempt scope_refusal/jailbreak paths — Task 4 Step 3
- ✅ Fix 3: Regression tests for both fixes — Tasks 1, 2
- ✅ Finding B (language conflict): Document only — goes in Experiment 4.1 test plan
- ✅ Finding D (wallah false positive): Deferred to pre-Experiment 4.1 milestone
- ✅ Finding E (CU-CS-001 anchor): Deferred to pre-production milestone

**Placeholder scan:** None found.

**Type consistency:** `_BANNED_OPENER_PATTERNS: list[str]`, `_BANNED_OPENER_RE: re.Pattern`, `banned_opener_violation: bool` — all used consistently.

**Imports added to output_gate.py:** `compose_prompt`, `get_responder`, `resilient_invoke` — all confirmed present in the codebase at their specified import paths.
