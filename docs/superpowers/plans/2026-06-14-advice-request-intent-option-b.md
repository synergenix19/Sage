> **⚠️ SUPERSEDED 2026-06-14** by `2026-06-14-engagement-advice-posture.md`.
> After review against the People/Pain/LLMs research brief (June 2026), the discrete
> `advice_request` intent approach was rejected: it loads the already-single-point-of-failure
> classifier, is reactive (only fires after the user complains), and misses the two
> failures the literature weights hardest — generic advice (#1 frustration) and
> stacked questions (MIND-SAFE "one question at a time"). The replacement is posture-first
> + a deterministic (non-classifier) delegation backstop + a question-discipline gate +
> anti-generic eval coverage. Kept here for history only. DO NOT EXECUTE THIS FILE.

---

# advice_request Intent (Option B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote the floor-return / advice-seeking case to a first-class `advice_request` intent so that, when a user explicitly delegates ("just tell me what to do") or pushes back on being questioned ("you need to guide me, not ask me"), Sage gives concrete suggestions instead of asking another exploratory question.

**Architecture:** `advice_request` becomes a member of the `Intent` literal, a classification rule in `INTENT_SYSTEM`, a routing branch in `_route_after_intent` (→ `freeflow`, bypassing the confidence gate, deferring to safety/acute redirects), and the already-drafted `L2_advice_request` template selected automatically by the composer. A deterministic output-gate backstop guarantees an advice-mode turn never ends on a question. The live Option A stopgap (the `general_chat` exception clause) is **kept** as defense-in-depth for borderline turns that still classify as `general_chat`.

**Tech Stack:** Python 3.11, LangGraph state machine, pydantic prompt templates (JSON), pytest (asyncio_mode=auto; `-m slow` marks live-LLM classification tests).

**Why this change:** Live production replay on 2026-06-14 (chat.biosight.ai, "How do I deal with my father's response like this?") reproduced the frustration loop: turn 2 ("you need to guide me, not ask me") → skill offer + question; turn 3 ("what do you keep asking me?") → another question; only turn 4 ("I want answers, not questions") finally produced advice — and even then it ended with a question. Root cause: only Option A (the `general_chat` exception clause) is live; its trigger is too narrow and prompt-only. See [[advice-request-option-b]].

---

## Decision Points (resolve BEFORE Task 1 — these are clinical/control-layer calls)

These are flagged because they change therapeutic posture or the safety control layer. The defaults below are coded into the plan; if a reviewer overrides one, adjust the named task.

- **D1 — Classification trigger scope (clinical).** `advice_request` fires on: (a) explicit delegation ("just tell me what to do", "you pick", "any ideas?", "I don't know, can you suggest something?"), and (b) **frustration-with-being-questioned** ("you need to guide me, not ask me", "what do you keep asking me?", "I want answers, not questions", "stop asking me questions"). It does **NOT** fire on a first genuine help-seeking question ("how do I deal with X?") — that still gets one round of exploration. **Default: as stated.** This is the key gap the live test exposed (group (b)).
- **D2 — Rule 1 (engineering, control-layer).** Adding an intent to `INTENT_SYSTEM` + routing is a control-layer change requiring Rule 1 approval (per the draft template's `_review_required`). **Default: required before merge (Task 0).**
- **D3 — Acute-intensity precedence (clinical).** An `advice_request` at `emotional_intensity >= ACUTE_INTENSITY_FLOOR` (8) with no active skill routes to `skill_select` (offer down-regulation first), NOT to direct advice. **Default: stabilise-then-guide (coded in Task 3).** Override → route acute advice_request straight to `freeflow`.
- **D4 — Trailing-question guarantee mechanism.** Deterministic strip in `output_gate` (no extra LLM round-trip), gated on `primary_intent == "advice_request"`. **Default: strip (Task 5).** Override → mirror the banned-opener retry-then-fallback loop instead (heavier; documented in Task 5 notes).

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `src/sage_poc/state.py` | Canonical `Intent` literal | Add `"advice_request"` |
| `src/sage_poc/nodes/intent_route.py` | LLM intent classification (`INTENT_SYSTEM`) | Add `advice_request` to the type list + a classification rule |
| `src/sage_poc/graph.py` | `_route_after_intent` precedence | Add an `advice_request` branch after SF-2, before the confidence gate |
| `src/sage_poc/prompts/templates/L2_intents/advice_request.json` | L2 advice posture (already drafted v0.1.0) | Add frustration-repair posture + "no trailing question"; flip status to approved on sign-off |
| `src/sage_poc/nodes/output_gate.py` | Output enforcement | Add deterministic trailing-question strip for advice_request |
| `tests/test_routing.py` | `_route_after_intent` branch coverage | Add advice_request routing cases |
| `tests/test_intent_route_node.py` | Node parse + live classification | Add advice_request parse test + slow classification tests |
| `tests/test_nodes.py` | Guard tests | Extend the bare-emotional-words guard note (no regression) |
| `tests/test_prompts_loader.py` | L2 template existence | Add `"advice_request"` to the parametrize list |
| `tests/test_output_gate_response_paths.py` | Gate output behavior | Add trailing-question-strip tests |
| `docs/superpowers/governance/2026-06-14-advice-request-option-b.md` | Sign-off record | New governance doc |

---

## Task 0: Governance gate (Rule 1 + clinical sign-off)

No code in this task — it records the two approvals the control-layer + posture change requires. The implementer should NOT flip `advice_request.json` to `status: approved` until both are recorded (that flip is Task 6, Step 5).

**Files:**
- Create: `docs/superpowers/governance/2026-06-14-advice-request-option-b.md`

- [ ] **Step 1: Write the governance record**

Create `docs/superpowers/governance/2026-06-14-advice-request-option-b.md` with this content:

```markdown
# Governance: advice_request Intent (Option B)

**Date opened:** 2026-06-14
**Supersedes:** Option A (the general_chat exception clause, kept as defense-in-depth)
**Evidence:** Production replay 2026-06-14 (chat.biosight.ai) reproduced the
question-loop frustration through turn 4. Transcript in the engineering thread.

## What changes
- New first-class intent `advice_request` in the control layer (state.py Intent
  literal, INTENT_SYSTEM classification rule, _route_after_intent branch).
- L2_advice_request template activated (v1.0.0).
- Deterministic output-gate backstop: advice-mode turns never end on a question.

## Required sign-offs (BOTH required before merge)
- [ ] Rule 1 (engineering control-layer change) — approver: __________  date: ______
- [ ] Clinical review (direct recommendation vs guided exploration posture;
      frustration-repair wording) — approver: __________  date: ______

## Decision points (see plan §Decision Points)
- D1 trigger scope: delegation + frustration-with-questioning. APPROVED? ____
- D3 acute precedence: stabilise-then-guide. APPROVED? ____
```

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/governance/2026-06-14-advice-request-option-b.md
git commit -m "docs: open governance record for advice_request intent (Option B)"
```

---

## Task 1: Add `advice_request` to the Intent literal

**Files:**
- Modify: `src/sage_poc/state.py:3-7`
- Test: `tests/test_routing.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_routing.py` (end of the `_route_after_intent` section, after line 81):

```python
def test_advice_request_is_a_valid_intent_member():
    """advice_request must be a member of the Intent literal so state typing and
    INTENT_SYSTEM parsing accept it."""
    from typing import get_args
    from sage_poc.state import Intent
    assert "advice_request" in get_args(Intent), (
        "advice_request missing from the Intent literal in state.py"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_routing.py::test_advice_request_is_a_valid_intent_member -v`
Expected: FAIL — `"advice_request" not in (...)`.

- [ ] **Step 3: Add the member**

In `src/sage_poc/state.py`, change the `Intent` literal (lines 3-7) from:

```python
Intent = Literal[
    "skill_continuation", "new_skill", "general_chat",
    "crisis", "info_request", "exit_skill",
    "scope_refusal", "jailbreak",
]
```

to:

```python
Intent = Literal[
    "skill_continuation", "new_skill", "general_chat",
    "crisis", "info_request", "exit_skill",
    "scope_refusal", "jailbreak", "advice_request",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_routing.py::test_advice_request_is_a_valid_intent_member -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/state.py tests/test_routing.py
git commit -m "feat: add advice_request to Intent literal"
```

---

## Task 2: Route `advice_request` in `_route_after_intent`

**Files:**
- Modify: `src/sage_poc/graph.py:206-211` (insert a branch between the SF-2 block and the confidence gate)
- Test: `tests/test_routing.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_routing.py` after the test from Task 1:

```python
@pytest.mark.parametrize("confidence", [0.9, 0.3])
def test_advice_request_no_skill_routes_to_freeflow(confidence):
    """advice_request with no active skill → freeflow (where the L2 advice template
    fires). Bypasses the confidence gate: terse delegations classify low-confidence
    by nature, same precedent as offer-accept."""
    state = make_full_state(
        primary_intent="advice_request",
        intent_confidence=confidence,
        emotional_intensity=5,
        active_skill_id=None,
    )
    assert _route_after_intent(state) == "freeflow"


def test_advice_request_with_active_skill_routes_to_executor():
    """Mid-skill 'just tell me what to do' must not clear the checkpoint — the
    executor handles it (mirrors new_skill/skill_continuation guards)."""
    state = make_full_state(
        primary_intent="advice_request",
        intent_confidence=0.9,
        active_skill_id="cbt_thought_record",
    )
    assert _route_after_intent(state) == "skill_executor"


def test_advice_request_acute_defers_to_skill_select():
    """D3: an acute-intensity advice_request with no active skill defers to
    skill_select so down-regulation is offered before advice (stabilise, then guide)."""
    state = make_full_state(
        primary_intent="advice_request",
        intent_confidence=0.9,
        emotional_intensity=9,
        active_skill_id=None,
    )
    assert _route_after_intent(state) == "skill_select"


def test_crisis_still_beats_advice_request_intensity():
    """Safety precedence: crisis intent wins even if intensity is acute."""
    state = make_full_state(primary_intent="crisis", emotional_intensity=10)
    assert _route_after_intent(state) == "crisis"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_routing.py -k advice_request -v`
Expected: the three `advice_request` routing tests FAIL (current code falls through to the confidence gate / default freeflow, so `test_advice_request_no_skill_routes_to_freeflow[0.3]` fails with `low_confidence`, and the acute/active-skill cases fail). `test_crisis_still_beats_advice_request_intensity` passes already.

- [ ] **Step 3: Insert the routing branch**

In `src/sage_poc/graph.py`, find the SF-2 block ending at line 209 (`return "skill_select"`) and the confidence gate at line 210 (`if confidence < 0.6:`). Insert the following branch **between** them (after line 209, before line 210):

```python
    # advice_request (Option B, 2026-06-14): the user has explicitly delegated the
    # decision to Sage, or is frustrated by being questioned and wants direct guidance.
    # Route to freeflow, where the L2_advice_request template instructs concrete
    # suggestions instead of another exploratory question. Bypasses the confidence gate:
    # terse delegations ("just tell me", "you pick") classify low-confidence by nature
    # (same precedent as offer-accept and post-crisis monitoring above). Placed AFTER the
    # crisis/scope/jailbreak/monitoring/psychotic/offer-accept/SF-2 redirects so every
    # safety and acute-distress branch stays senior.
    #   - Mid-skill (active_skill_id set): defer to the executor so the active protocol
    #     and its checkpoint are preserved (mirrors new_skill/skill_continuation below).
    #   - Acute, no active skill (D3): defer to skill_select so down-regulation is offered
    #     before advice — stabilise, then guide.
    if intent == "advice_request":
        if state.get("active_skill_id"):
            return "skill_executor"
        if state.get("emotional_intensity", 5) >= ACUTE_INTENSITY_FLOOR:
            return "skill_select"
        return "freeflow"
```

(No change to `build_graph`'s edge map is needed — `"freeflow"`, `"skill_select"`, and `"skill_executor"` are all already declared targets at lines 274-281.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_routing.py -k advice_request -v`
Expected: all four PASS.

- [ ] **Step 5: Run the full routing suite (no regression)**

Run: `uv run pytest tests/test_routing.py -v`
Expected: all PASS (existing SF-2, psychotic, offer-accept, confidence-boundary cases unchanged).

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/graph.py tests/test_routing.py
git commit -m "feat: route advice_request to freeflow (acute defers to skill_select)"
```

---

## Task 3: Add the `advice_request` classification rule to `INTENT_SYSTEM`

**Files:**
- Modify: `src/sage_poc/nodes/intent_route.py:17` (the `primary_intent` type list) and `:31` (add the rule after `jailbreak`)
- Test: `tests/test_intent_route_node.py`

- [ ] **Step 1: Write the failing parse test (mocked LLM)**

Add to `tests/test_intent_route_node.py` (after the existing tests):

```python
@pytest.mark.asyncio
async def test_advice_request_intent_parsed_and_written():
    """When the classifier returns advice_request, the node must write it through
    to primary_intent unchanged (parse-layer guarantee)."""
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "advice_request", "secondary_intent": null, '
        '"intent_confidence": 0.66, "emotional_intensity": 5, "engagement": 6}'
    )
    state = _base_state(message_en="just tell me what to do")

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["primary_intent"] == "advice_request"
```

- [ ] **Step 2: Run test to verify it passes already (parse layer is intent-agnostic)**

Run: `uv run pytest tests/test_intent_route_node.py::test_advice_request_intent_parsed_and_written -v`
Expected: PASS (the node passes any `primary_intent` string through). This test pins the parse contract; the behavior change is in the prompt (next steps) and is covered by the slow tests below.

- [ ] **Step 3: Add the slow classification tests (live LLM)**

Add to `tests/test_nodes.py` directly after `test_bare_emotional_words_classified_as_general_chat` (after line 419). These hit the real classifier (`-m slow`), mirroring the guard test pattern:

```python
@pytest.mark.slow
async def test_advice_request_classified_for_delegation_and_frustration():
    """D1: explicit delegation AND frustration-with-being-questioned classify as
    advice_request, so the L2 advice template fires instead of another question."""
    from sage_poc.nodes.intent_route import intent_route_node
    advice_phrases = [
        "just tell me what to do",
        "I don't know, can you suggest something?",
        "you need to guide me, not ask me",
        "what do you keep asking me? I thought you were the one with the answers",
        "I want answers, not questions",
    ]
    for phrase in advice_phrases:
        state = make_state(raw_message=phrase, message_en=phrase)
        result = await intent_route_node(state)
        assert result["primary_intent"] == "advice_request", (
            f"{phrase!r} classified as {result['primary_intent']!r}, expected advice_request. "
            f"The user is delegating/frustrated and must get direct guidance, not a re-probe."
        )


@pytest.mark.slow
async def test_advice_request_does_not_capture_bare_emotional_words():
    """GUARD (no regression): bare emotional affect must STILL be general_chat, not
    advice_request. advice_request requires explicit delegation/frustration, not mere
    distress. (Even if it misfired, advice_request routes to freeflow — never
    skill_select — so the SEMANTIC_THRESHOLD skill-activation guard is unaffected.)"""
    from sage_poc.nodes.intent_route import intent_route_node
    for phrase in ("stressed", "anxious", "I feel sad", "things are hard"):
        state = make_state(raw_message=phrase, message_en=phrase)
        result = await intent_route_node(state)
        assert result["primary_intent"] == "general_chat", (
            f"GUARD FAILURE: {phrase!r} classified as {result['primary_intent']!r}; "
            f"bare affect must remain general_chat."
        )


@pytest.mark.slow
async def test_first_help_seeking_question_is_not_advice_request():
    """D1 boundary: a first genuine 'how do I deal with X' question is NOT advice_request —
    it warrants one round of exploration. advice_request is for explicit delegation or
    frustration after being questioned."""
    from sage_poc.nodes.intent_route import intent_route_node
    state = make_state(
        raw_message="How do I deal with my father's response like this?",
        message_en="How do I deal with my father's response like this?",
    )
    result = await intent_route_node(state)
    assert result["primary_intent"] != "advice_request", (
        f"A first help-seeking question classified as advice_request "
        f"({result['primary_intent']!r} expected new_skill or general_chat) — this would "
        f"skip exploration entirely."
    )
```

- [ ] **Step 4: Run the slow tests to verify they FAIL (rule not added yet)**

Run: `uv run pytest tests/test_nodes.py -k "advice_request or first_help_seeking" -m slow -v`
Expected: `test_advice_request_classified_for_delegation_and_frustration` FAILS (phrases currently classify as `general_chat`). The two guard tests likely PASS already (they assert the *absence* of advice_request); they protect against over-firing once the rule is added.

- [ ] **Step 5: Add `advice_request` to the type list**

In `src/sage_poc/nodes/intent_route.py`, line 17, change:

```python
- primary_intent: one of "skill_continuation" | "new_skill" | "general_chat" | "crisis" | "info_request" | "exit_skill" | "scope_refusal" | "jailbreak"
```

to:

```python
- primary_intent: one of "skill_continuation" | "new_skill" | "general_chat" | "crisis" | "info_request" | "exit_skill" | "scope_refusal" | "jailbreak" | "advice_request"
```

- [ ] **Step 6: Add the classification rule**

In the same file, after the `jailbreak` rule (line 31) and before the closing `Return ONLY the JSON object.` line (line 33), insert:

```python
- advice_request: the user has explicitly handed the decision to Sage, or is frustrated at being asked questions and wants direct guidance — NOT presenting a new symptom. Fires on (a) explicit delegation: "just tell me what to do", "you pick", "any ideas?", "I don't know, can you suggest something?", "you decide"; or (b) frustration with being questioned: "you need to guide me, not ask me", "what do you keep asking me?", "I want answers, not questions", "stop asking me questions" (and Arabic/Arabizi equivalents). This is NOT new_skill (no specific symptom is presented) and NOT general_chat (the user has explicitly delegated or objected to exploration). A first, genuine help-seeking question that still invites exploration ("how do I deal with this?", "what should I think about?") is NOT advice_request — classify those as new_skill or general_chat. Secondary can be emotional_support for blended turns.
```

- [ ] **Step 7: Run the slow tests to verify they pass**

Run: `uv run pytest tests/test_nodes.py -k "advice_request or first_help_seeking" -m slow -v`
Expected: all PASS.

- [ ] **Step 8: Run the bare-emotional-words guard (critical no-regression check)**

Run: `uv run pytest tests/test_nodes.py -k "bare_emotional_words" -m slow -v`
Expected: PASS. (Per the SINGLE-POINT-OF-FAILURE warning at `intent_route.py:7-14`, this guard must stay green after any `INTENT_SYSTEM` edit.)

- [ ] **Step 9: Commit**

```bash
git add src/sage_poc/nodes/intent_route.py tests/test_intent_route_node.py tests/test_nodes.py
git commit -m "feat: classify explicit delegation + question-frustration as advice_request"
```

---

## Task 4: Register the L2 template so the composer selects it

The composer (`_build_l2_intent_block`, `composer.py:263-290`) already selects the template by `primary_intent`, so once `advice_request.json` exists (it does, as a draft) and `advice_request` flows through, the template is used automatically. This task pins that with tests and adds the intent to the existence-parametrize.

**Files:**
- Modify: `tests/test_prompts_loader.py:119-127`
- Test: `tests/test_prompts_loader.py`

- [ ] **Step 1: Write the failing test**

In `tests/test_prompts_loader.py`, add `"advice_request"` to the parametrize list at lines 119-122:

```python
@_pytest.mark.parametrize("intent", [
    "general_chat", "new_skill", "skill_continuation", "info_request",
    "exit_skill", "scope_refusal", "jailbreak", "crisis", "low_confidence",
    "advice_request",
])
def test_all_intents_have_l2_template(intent):
    tmpl = get_intent_template(intent)
    assert tmpl is not None, f"No L2 template for intent: {intent}"
    assert tmpl.layer == "L2"
    assert tmpl.intent == intent
```

Also add a composer-selection test at the end of the file:

```python
def test_composer_selects_advice_request_template():
    """compose-layer guarantee: when primary_intent is advice_request, the L2 block is
    the advice template (direct suggestions), not the general_chat fallback."""
    from sage_poc.prompts.composer import _build_l2_intent_block
    block = _build_l2_intent_block("advice_request", intensity=5, secondary_intent=None)
    lowered = block.lower()
    assert "concrete" in lowered or "suggestions" in lowered, (
        "advice_request L2 block must instruct concrete suggestions"
    )
    assert "do not ask another exploratory question" in lowered, (
        "advice_request L2 block must suppress the exploratory re-ask"
    )
```

- [ ] **Step 2: Run tests to verify status**

Run: `uv run pytest tests/test_prompts_loader.py -k "advice_request or all_intents_have_l2" -v`
Expected: `test_all_intents_have_l2_template[advice_request]` PASSES (the draft file exists and has `intent: advice_request`). `test_composer_selects_advice_request_template` PASSES against the current draft content (it already contains "concrete" and "Do not ask another exploratory question"). If either fails, the draft template path/content is wrong — fix the file at `src/sage_poc/prompts/templates/L2_intents/advice_request.json` before proceeding.

- [ ] **Step 3: Commit**

```bash
git add tests/test_prompts_loader.py
git commit -m "test: pin advice_request L2 template existence and composer selection"
```

---

## Task 5: Output-gate backstop — advice-mode turns never end on a question

The draft template says "Do not ask another exploratory question," but prompt-only instructions are not guaranteed (the same lesson as banned openers — see [[em-dash-in-rule-content]] reasoning and the output_gate banned-opener enforcement). This task adds a deterministic strip (D4 default).

**Files:**
- Modify: `src/sage_poc/nodes/output_gate.py` (add a module-level helper, and call it after the banned-opener block at ~line 336, before `violations = _FORMAT_VIOLATIONS.findall(...)` at line 337)
- Test: `tests/test_output_gate_response_paths.py`

- [ ] **Step 1: Write the failing unit test for the helper**

Add to `tests/test_output_gate_response_paths.py`:

```python
def test_strip_trailing_question_removes_dangling_question():
    from sage_poc.nodes.output_gate import _strip_trailing_question
    text = ("Prepare a few calm, assertive phrases beforehand. You can also set a "
            "boundary by letting him know when you need a break. How does this sit with you?")
    out = _strip_trailing_question(text)
    assert out == ("Prepare a few calm, assertive phrases beforehand. You can also set a "
                   "boundary by letting him know when you need a break.")


def test_strip_trailing_question_removes_multiple_trailing_questions():
    from sage_poc.nodes.output_gate import _strip_trailing_question
    text = "Try writing down your worry first. Does that help? What do you think?"
    assert _strip_trailing_question(text) == "Try writing down your worry first."


def test_strip_trailing_question_keeps_question_only_response():
    """If the whole response is a single question (no substantive advice before it),
    leave it — stripping would empty the turn. Such a turn shouldn't occur in advice
    mode, but the backstop must never produce an empty response."""
    from sage_poc.nodes.output_gate import _strip_trailing_question
    text = "What feels hardest right now?"
    assert _strip_trailing_question(text) == "What feels hardest right now?"


def test_strip_trailing_question_noop_without_trailing_question():
    from sage_poc.nodes.output_gate import _strip_trailing_question
    text = "Set a boundary and take a short break when things get heated."
    assert _strip_trailing_question(text) == text
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_output_gate_response_paths.py -k strip_trailing_question -v`
Expected: FAIL — `_strip_trailing_question` not defined.

- [ ] **Step 3: Implement the helper**

In `src/sage_poc/nodes/output_gate.py`, add at module level (near the other module-level helpers/constants, e.g. after the `_BANNED_OPENER_*` definitions):

```python
import re as _re_oq  # local alias; `re` is already imported at module top — reuse it if present

# Trailing-question strip for advice mode (Option B). Removes one or more question
# sentences at the very end of a response so an advice_request turn never ends on a
# question. Safe: only strips when substantive (non-question) content remains.
_TRAILING_QUESTION_RE = re.compile(r"(?:\s*[^.!?]*\?)+\s*$")


def _strip_trailing_question(text: str) -> str:
    """Drop trailing interrogative sentence(s). If the result would be empty (the whole
    turn was a question), return the original text unchanged."""
    if not text or "?" not in text:
        return text
    stripped = _TRAILING_QUESTION_RE.sub("", text).rstrip()
    return stripped if stripped else text
```

(If `re` is already imported at the top of the file — it is in most nodes — delete the `import re as _re_oq` alias line; it is only a safety net. Use the existing module `re`.)

- [ ] **Step 4: Run the helper tests to verify they pass**

Run: `uv run pytest tests/test_output_gate_response_paths.py -k strip_trailing_question -v`
Expected: all four PASS.

- [ ] **Step 5: Write the failing node-integration test**

Add to `tests/test_output_gate_response_paths.py`. Mirror the existing node tests in this file for state shape (copy a passing test's state dict and adjust); the key assertions are intent-gated stripping:

```python
import pytest


@pytest.mark.asyncio
async def test_output_gate_strips_trailing_question_for_advice_request(monkeypatch):
    """An advice_request turn ending on a question must have the question removed."""
    from sage_poc.nodes import output_gate as og
    state = _make_gate_state(  # use this file's existing state factory/helper
        primary_intent="advice_request",
        response_en=("Prepare a few calm, assertive phrases beforehand. "
                     "How does this sit with you?"),
    )
    result = await og.output_gate_node(state)
    assert "?" not in result["response_en"]
    assert "Prepare a few calm, assertive phrases beforehand." in result["response_en"]


@pytest.mark.asyncio
async def test_output_gate_keeps_trailing_question_for_general_chat(monkeypatch):
    """The strip is advice-mode-only: general_chat may legitimately end on a question."""
    from sage_poc.nodes import output_gate as og
    state = _make_gate_state(
        primary_intent="general_chat",
        response_en="That sounds heavy. What's been weighing on you most?",
    )
    result = await og.output_gate_node(state)
    assert result["response_en"].endswith("?")
```

> **Implementer note:** `tests/test_output_gate_response_paths.py` already constructs gate state for its existing tests. Reuse that construction (a `_make_gate_state`-style helper or inline dict) so `output_gate_node` runs without a DB pool — set `session_id=None`/`user_id=None` to skip audit writes, exactly as the existing passing tests in this file do. Do not invent new fixtures.

- [ ] **Step 6: Run to verify they fail**

Run: `uv run pytest tests/test_output_gate_response_paths.py -k "trailing_question_for" -v`
Expected: FAIL — the gate does not yet strip.

- [ ] **Step 7: Wire the strip into the node**

In `src/sage_poc/nodes/output_gate.py`, immediately after the banned-opener enforcement block (after line 316, before the offer-voiding block at line 318 — or at the latest, right before `violations = _FORMAT_VIOLATIONS.findall(response_en)` at line 337), insert:

```python
    # Option B backstop: advice_request turns must never end on a question. The L2
    # template instructs this, but prompt-only guarantees leak (cf. banned openers).
    # Deterministic strip; only when substantive content remains (helper no-ops on a
    # question-only response). Gated strictly on intent so exploratory general_chat is
    # untouched. Runs on English text before translation (line 341), so the Arabic
    # render inherits the stripped text.
    if (
        state.get("primary_intent") == "advice_request"
        and response_en
        and gate_path not in ("scope_refusal", "jailbreak")
    ):
        _stripped = _strip_trailing_question(response_en)
        if _stripped != response_en:
            response_en = _stripped
            path = path + ["advice_trailing_question_stripped"]
```

- [ ] **Step 8: Run the node tests to verify they pass**

Run: `uv run pytest tests/test_output_gate_response_paths.py -k "trailing_question" -v`
Expected: all PASS.

- [ ] **Step 9: Run the full output_gate suite (no regression)**

Run: `uv run pytest tests/test_output_gate_response_paths.py tests/test_output_gate_banned_opener.py tests/test_output_gate_loop_mechanics.py -v`
Expected: all PASS.

- [ ] **Step 10: Commit**

```bash
git add src/sage_poc/nodes/output_gate.py tests/test_output_gate_response_paths.py
git commit -m "feat: strip trailing question on advice_request turns (output_gate backstop)"
```

> **D4 override (only if a reviewer rejects deterministic stripping):** instead of Steps 3/7, add an `advice_question_correction` constant and a retry branch mirroring the banned-opener loop (`output_gate.py:275-316`) plus a clause in `_route_after_output_gate` (`graph.py:244-250`) that routes back to `freeflow_respond` while `advice_question_retry_count <= 1`. This costs one extra LLM round-trip per offending turn. Not recommended (YAGNI); the strip is a hard guarantee with no latency cost.

---

## Task 6: Finalize the L2 template (clinical authoring + activation)

**Files:**
- Modify: `src/sage_poc/prompts/templates/L2_intents/advice_request.json`
- Test: `tests/test_prompts_loader.py` (reuse Task 4 tests)

- [ ] **Step 1: Add frustration-repair posture to the template content**

In `src/sage_poc/prompts/templates/L2_intents/advice_request.json`, replace the `content` value with (this extends the draft to explicitly handle the frustration case the live test exposed, and reinforces the no-trailing-question rule the gate now enforces):

```
INTENT: The user has explicitly asked Sage to lead, or is frustrated at being asked questions. They are not presenting a new symptom, they are handing over the decision to Sage. Emotional intensity: {intensity}/10. {intensity_guidance} Provide concrete, warm, practical suggestions directly, two or three specific ideas. Do not ask another exploratory question, and do not end your reply with a question. If the user is frustrated that you keep asking questions, acknowledge that briefly in one short clause, then give the suggestions, do not defend the questions. If Sage asked a question in the prior turn and the user said they do not know, answer your own question with specific ideas. Lead gently but clearly.
```

- [ ] **Step 2: Verify content tests still pass**

Run: `uv run pytest tests/test_prompts_loader.py -k advice_request -v`
Expected: PASS (content still contains "concrete" and "do not ask another exploratory question").

- [ ] **Step 3: Verify em-dash hygiene (per [[em-dash-in-rule-content]])**

Run: `uv run python -c "import json; c=json.load(open('src/sage_poc/prompts/templates/L2_intents/advice_request.json'))['content']; assert '—' not in c, 'em dash found'; print('clean')"`
Expected: prints `clean`.

- [ ] **Step 4: Activate the template — ONLY after Task 0 sign-offs are recorded**

Confirm both checkboxes in `docs/superpowers/governance/2026-06-14-advice-request-option-b.md` are filled (Rule 1 + clinical, with names and dates). If not, STOP and surface to the human — do not flip status. Once confirmed, in `advice_request.json` set:

```json
  "version": "1.0.0",
  "status": "approved",
  "authored_by": "sage_clinics",
  "approved_by": "clinical_lead",
  "effective_date": "2026-06-14",
```

and remove the draft-only bookkeeping keys (`_review_required`, `_option_b_routing_change`, `_option_b_test_coverage`, `_selector_condition`) now that the routing and tests live in code.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/prompts/templates/L2_intents/advice_request.json docs/superpowers/governance/2026-06-14-advice-request-option-b.md
git commit -m "feat: activate L2_advice_request v1.0.0 with frustration-repair posture"
```

---

## Task 7: Full regression + production verification

**Files:**
- Test: full suite
- Verify: `scripts/functional_multiturn_prod.py` (extend with the advice scenario)

- [ ] **Step 1: Run the unit gate (fast suite)**

Run: `uv run pytest -m "not slow" -q`
Expected: all PASS, no collection errors. Note the test count and compare to the pre-change baseline so none were dropped.

- [ ] **Step 2: Run the slow classification + guard tests**

Run: `uv run pytest tests/test_nodes.py -k "advice_request or first_help_seeking or bare_emotional_words" -m slow -v`
Expected: all PASS — advice_request fires on delegation/frustration; bare affect and first help-seeking questions do NOT.

- [ ] **Step 3: Add the advice scenario to the production harness**

In `scripts/functional_multiturn_prod.py`, add to the `SCENARIOS` list:

```python
    {
        "name": "D. Advice-request frustration loop (Option B regression)",
        "turns": [
            "How do I deal with my father's response like this?",
            "It makes me feel powerless. But if I knew what to do I wouldn't be asking you. You need to guide me, not ask me.",
            "What do you keep asking me? I thought you were the one with the answers.",
            "I want answers, not questions.",
        ],
    },
```

- [ ] **Step 4: After deploy, run the harness against production**

Run: `python scripts/functional_multiturn_prod.py`
Expected (post-deploy): by turn 2 ("you need to guide me, not ask me") the reply gives concrete suggestions and does NOT end on a question; `META` shows `intent=advice_request`. The turn-3 complaint is NOT answered with another question. This is the direct before/after for the live frustration the user reported.

- [ ] **Step 5: Commit the harness update**

```bash
git add scripts/functional_multiturn_prod.py
git commit -m "test: add advice-request frustration scenario to prod harness"
```

- [ ] **Step 6: Deploy (manual Railway — see [[engagement-layer-proposal]] deploy notes)**

Prompts and code are baked into the Docker image; a redeploy is required for the new intent + template to take effect:

```bash
railway up --service sage-api
```

Then verify liveness: `curl -s -o /dev/null -w "%{http_code}" https://sage-api-production-3328.up.railway.app/health/schema-conformance` → `200`, and run Step 4.

---

## Self-Review

**1. Spec coverage.**
- Promote floor-return to first-class intent → Tasks 1, 3 (enum + classification). ✓
- Route it so it gives advice not questions → Task 2 (routing to freeflow) + Task 4 (template selection). ✓
- Broaden trigger beyond "answers not questions" to "guide me, not ask me" / "what do you keep asking me" → Task 3 rule clause (b) + slow test. ✓ (this is the live-test gap.)
- Frustration/repair signal so a complaint-about-questions isn't met with a question → Task 3 (classification) + Task 6 (acknowledge-then-suggest wording). ✓
- Suppress the trailing question in advice mode → Task 5 (deterministic gate strip). ✓
- Control-layer governance (Rule 1) + clinical sign-off → Task 0 + Task 6 Step 4 gate. ✓
- No regression to the bare-emotional-words single-point-of-failure guard → Task 3 Step 8 + Task 7 Step 2. ✓

**2. Placeholder scan.** No "TBD"/"handle edge cases"/"similar to Task N". Every code step shows the code; every test step shows the assertion. The one cross-reference (Task 5 Step 5 reusing this file's state factory) is explicit about reusing the existing helper rather than inventing one, with a fallback instruction. ✓

**3. Type consistency.** `_strip_trailing_question` defined in Task 5 Step 3, used in Steps 1/5/7 with matching signature. `advice_request` string used identically across state.py, INTENT_SYSTEM, `_route_after_intent`, the template `intent` field, and all tests. `ACUTE_INTENSITY_FLOOR` is the existing graph.py constant (no new symbol). Routing targets (`freeflow`/`skill_select`/`skill_executor`) all pre-exist in the edge map. ✓

**Known limitation surfaced (not a gap):** classification quality depends on the LLM following the new `INTENT_SYSTEM` rule; the slow tests in Task 3/7 are the regression guard, and the Task 5 gate strip is a deterministic backstop for the most visible failure (trailing question) regardless of classification. The Option A `general_chat` exception clause is intentionally retained as defense-in-depth for borderline turns that still classify `general_chat`.
