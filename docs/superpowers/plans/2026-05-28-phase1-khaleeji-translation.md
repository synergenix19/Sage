# Phase 1 — Khaleeji Translation Prompt Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the bare "Modern Standard Arabic" translation prompt in `language.py` with a Khaleeji-dialect, therapeutic-register-aware prompt, and confirm neither the English translation path nor existing tests regress.

**Architecture:** Two functions changed (`translate_to_arabic` and `async_translate_to_arabic`), zero functions added, zero schema changes. The English translation functions (`translate_to_english`, `async_translate_to_english`) are explicitly left unchanged — they serve safety classification and intent routing, which require accurate literal translation, not register-aware output. New tests verify prompt content by mocking the LLM and capturing the messages argument. Existing slow tests (real API calls) verify end-to-end Arabic output quality after the change.

**Tech Stack:** Python 3.11+, pytest, pytest-asyncio, unittest.mock, uv

---

## Background

`language.py` contains four translation functions. Two need to change; two must not:

| Function | Direction | Change? | Why |
|---|---|---|---|
| `translate_to_arabic` | EN → AR | **Yes** | User-facing output; must be Khaleeji |
| `async_translate_to_arabic` | EN → AR | **Yes** | User-facing output; must be Khaleeji |
| `translate_to_english` | AR → EN | No | Used for safety + intent classification; needs accurate literal translation |
| `async_translate_to_english` | AR → EN | No | Same reason |

**Current prompt (both Arabic functions):**
```
"Translate the following text to Modern Standard Arabic. Return ONLY the [Arabic] translation, nothing else."
```

**New prompt (both Arabic functions):**
```
"You are translating warm, supportive messages from a wellness companion named Sage. "
"Translate to informal Gulf Arabic (Khaleeji dialect). Preserve emotional warmth and "
"conversational tone. Avoid formal or clinical Arabic. Return only the translation."
```

---

## File Map

| Action | Path |
|---|---|
| Modify | `sage-poc/src/sage_poc/language.py` — update 2 prompt strings |
| Modify | `sage-poc/tests/test_language.py` — add 8 new prompt-content tests |

No other files change.

---

## Task 1 — Write Failing Tests for New Translation Prompts

**Files:**
- Modify: `sage-poc/tests/test_language.py`

The tests mock the LLM to capture what prompt is sent. They do not make real API calls and do not need `@pytest.mark.slow`. Eight tests total: four for each Arabic function (Khaleeji present, MSA absent, wellness context present, English functions unchanged).

- [ ] **Step 1: Add the 8 new tests to `tests/test_language.py`**

Append to the end of `sage-poc/tests/test_language.py`:

```python
# ---- Prompt content tests (mocked — no API calls) --------------------------------
# These tests verify the prompt strings sent to the LLM, not the translation quality.
# Quality is validated separately by a native Khaleeji speaker (see Validation Protocol).

from unittest.mock import AsyncMock, MagicMock, patch


# ---- translate_to_arabic (sync) --------------------------------------------------

def test_translate_to_arabic_prompt_specifies_khaleeji():
    """translate_to_arabic must request Khaleeji dialect, not Modern Standard Arabic."""
    captured = {}

    def mock_invoke(messages):
        captured["messages"] = messages
        resp = MagicMock()
        resp.content = "مرحبا"
        return resp

    mock_llm = MagicMock()
    mock_llm.invoke = mock_invoke

    with patch("sage_poc.llm.get_translator", return_value=mock_llm):
        from sage_poc.language import translate_to_arabic
        translate_to_arabic("Hello, how are you feeling today?")

    prompt = captured["messages"][0]["content"]
    assert "Khaleeji" in prompt, (
        f"'Khaleeji' not found in translate_to_arabic prompt.\nGot: {prompt}"
    )
    assert "Modern Standard Arabic" not in prompt, (
        f"Old MSA instruction still present in translate_to_arabic.\nGot: {prompt}"
    )


def test_translate_to_arabic_prompt_contains_wellness_context():
    """translate_to_arabic must include therapeutic register context (warmth + Sage identity)."""
    captured = {}

    def mock_invoke(messages):
        captured["messages"] = messages
        resp = MagicMock()
        resp.content = "مرحبا"
        return resp

    mock_llm = MagicMock()
    mock_llm.invoke = mock_invoke

    with patch("sage_poc.llm.get_translator", return_value=mock_llm):
        from sage_poc.language import translate_to_arabic
        translate_to_arabic("That sounds really hard. What's been most difficult for you?")

    prompt = captured["messages"][0]["content"]
    assert "Sage" in prompt, (
        f"'Sage' not found in translate_to_arabic prompt.\nGot: {prompt}"
    )
    assert "warm" in prompt.lower(), (
        f"No warmth instruction in translate_to_arabic prompt.\nGot: {prompt}"
    )


def test_translate_to_arabic_returns_original_on_failure():
    """translate_to_arabic must return the original English text when the LLM call fails.

    This verifies the existing resilience behaviour is not broken by the prompt change.
    """
    with patch("sage_poc.llm.get_translator", side_effect=RuntimeError("API down")):
        from sage_poc.language import translate_to_arabic
        result = translate_to_arabic("Fallback text that must survive")
    assert result == "Fallback text that must survive"


# ---- async_translate_to_arabic ---------------------------------------------------

@pytest.mark.asyncio
async def test_async_translate_to_arabic_prompt_specifies_khaleeji():
    """async_translate_to_arabic must request Khaleeji dialect."""
    captured = {}

    async def mock_resilient_invoke(llm, messages, node, language):
        captured["messages"] = messages
        return "مرحبا"

    mock_llm = MagicMock()

    with patch("sage_poc.resilience.resilient_invoke", mock_resilient_invoke):
        with patch("sage_poc.language.get_translator", return_value=mock_llm):
            from sage_poc.language import async_translate_to_arabic
            await async_translate_to_arabic("Hello, how are you feeling today?")

    prompt = captured["messages"][0]["content"]
    assert "Khaleeji" in prompt, (
        f"'Khaleeji' not found in async_translate_to_arabic prompt.\nGot: {prompt}"
    )
    assert "Modern Standard Arabic" not in prompt, (
        f"Old MSA instruction still present in async_translate_to_arabic.\nGot: {prompt}"
    )


@pytest.mark.asyncio
async def test_async_translate_to_arabic_prompt_contains_wellness_context():
    """async_translate_to_arabic must include Sage identity and warmth instruction."""
    captured = {}

    async def mock_resilient_invoke(llm, messages, node, language):
        captured["messages"] = messages
        return "مرحبا"

    mock_llm = MagicMock()

    with patch("sage_poc.resilience.resilient_invoke", mock_resilient_invoke):
        with patch("sage_poc.language.get_translator", return_value=mock_llm):
            from sage_poc.language import async_translate_to_arabic
            await async_translate_to_arabic("That makes complete sense.")

    prompt = captured["messages"][0]["content"]
    assert "Sage" in prompt, (
        f"'Sage' not found in async_translate_to_arabic prompt.\nGot: {prompt}"
    )
    assert "warm" in prompt.lower(), (
        f"No warmth instruction in async_translate_to_arabic prompt.\nGot: {prompt}"
    )


@pytest.mark.asyncio
async def test_async_translate_to_arabic_returns_original_on_empty_result():
    """async_translate_to_arabic must return the original text when resilient_invoke returns empty.

    resilient_invoke returns '' on full fallback exhaustion. The `result or text` guard
    in the function must catch this and return the English original.
    """
    async def mock_resilient_invoke(llm, messages, node, language):
        return ""

    mock_llm = MagicMock()

    with patch("sage_poc.resilience.resilient_invoke", mock_resilient_invoke):
        with patch("sage_poc.language.get_translator", return_value=mock_llm):
            from sage_poc.language import async_translate_to_arabic
            result = await async_translate_to_arabic("English fallback text")

    assert result == "English fallback text"


# ---- English translation functions — must NOT be affected -------------------------

def test_translate_to_english_prompt_unchanged():
    """translate_to_english must NOT include Khaleeji or therapeutic context.

    This function feeds safety classification (S1/S3) and intent routing.
    Therapeutic framing would bias those classifiers away from literal meaning.
    """
    captured = {}

    def mock_invoke(messages):
        captured["messages"] = messages
        resp = MagicMock()
        resp.content = "I am scared"
        return resp

    mock_llm = MagicMock()
    mock_llm.invoke = mock_invoke

    with patch("sage_poc.llm.get_translator", return_value=mock_llm):
        from sage_poc.language import translate_to_english
        translate_to_english("أنا خائف")

    prompt = captured["messages"][0]["content"]
    assert "Khaleeji" not in prompt, (
        f"Khaleeji instruction leaked into translate_to_english prompt.\nGot: {prompt}"
    )
    assert "English" in prompt, (
        f"'English' target language missing from translate_to_english prompt.\nGot: {prompt}"
    )


@pytest.mark.asyncio
async def test_async_translate_to_english_prompt_unchanged():
    """async_translate_to_english must NOT include Khaleeji or therapeutic context."""
    captured = {}

    async def mock_resilient_invoke(llm, messages, node, language):
        captured["messages"] = messages
        return "I am scared"

    mock_llm = MagicMock()

    with patch("sage_poc.resilience.resilient_invoke", mock_resilient_invoke):
        with patch("sage_poc.language.get_translator", return_value=mock_llm):
            from sage_poc.language import async_translate_to_english
            await async_translate_to_english("أنا خائف")

    prompt = captured["messages"][0]["content"]
    assert "Khaleeji" not in prompt, (
        f"Khaleeji instruction leaked into async_translate_to_english.\nGot: {prompt}"
    )
    assert "English" in prompt
```

- [ ] **Step 2: Run the new tests — all 8 must fail**

```bash
cd sage-poc && uv run pytest tests/test_language.py -v -k "khaleeji or wellness or unchanged or fallback" -m "not slow"
```

Expected: **8 FAIL**. The failures confirm the tests are checking the right thing before the code changes. Specifically:
- `test_translate_to_arabic_prompt_specifies_khaleeji` → FAIL: `'Khaleeji' not found`
- `test_translate_to_arabic_prompt_contains_wellness_context` → FAIL: `'Sage' not found`
- `test_async_translate_to_arabic_prompt_specifies_khaleeji` → FAIL: `'Khaleeji' not found`
- `test_async_translate_to_arabic_prompt_contains_wellness_context` → FAIL: `'Sage' not found`
- The 4 resilience/unchanged tests may already pass — that is acceptable.

If ALL 8 pass before any code change: the test mocking is wrong. Check that patch targets resolve correctly.

- [ ] **Step 3: Confirm the 3 existing language tests still pass**

```bash
cd sage-poc && uv run pytest tests/test_language.py -v -m "not slow"
```

Expected: The 3 existing `detect_*` tests pass, the 8 new tests fail as described above.

---

## Task 2 — Implement the Prompt Changes in `language.py`

**Files:**
- Modify: `sage-poc/src/sage_poc/language.py`

Two prompt strings change. Nothing else in the file changes.

- [ ] **Step 1: Update `translate_to_arabic` (sync, lines 80–99)**

In `sage-poc/src/sage_poc/language.py`, replace the `translate_to_arabic` function body. The only change is the prompt string in the `"content"` field:

**Before (lines 86–93):**
```python
        response = llm.invoke([{
            "role": "user",
            "content": (
                "Translate the following text to Modern Standard Arabic. "
                "Return ONLY the translation, nothing else:\n\n"
                f"{text}"
            ),
        }])
```

**After:**
```python
        response = llm.invoke([{
            "role": "user",
            "content": (
                "You are translating warm, supportive messages from a wellness companion named Sage. "
                "Translate to informal Gulf Arabic (Khaleeji dialect). Preserve emotional warmth and "
                "conversational tone. Avoid formal or clinical Arabic. Return only the translation.\n\n"
                f"{text}"
            ),
        }])
```

Everything else in `translate_to_arabic` (the try/except, the `return text` fallback, the docstring) stays unchanged.

- [ ] **Step 2: Update `async_translate_to_arabic` (async, lines 105–121)**

In the same file, replace the prompt string in `async_translate_to_arabic`:

**Before (lines 108–115):**
```python
    result = await resilient_invoke(
        get_translator(),
        [{
            "role": "user",
            "content": (
                "Translate the following text to Modern Standard Arabic. "
                "Return ONLY the Arabic translation, nothing else:\n\n"
                f"{text}"
            ),
        }],
```

**After:**
```python
    result = await resilient_invoke(
        get_translator(),
        [{
            "role": "user",
            "content": (
                "You are translating warm, supportive messages from a wellness companion named Sage. "
                "Translate to informal Gulf Arabic (Khaleeji dialect). Preserve emotional warmth and "
                "conversational tone. Avoid formal or clinical Arabic. Return only the translation.\n\n"
                f"{text}"
            ),
        }],
```

Everything else in `async_translate_to_arabic` stays unchanged.

- [ ] **Step 3: Confirm `translate_to_english` and `async_translate_to_english` are untouched**

Read lines 58–77 and 124–140 of `language.py` and verify they still say `"Translate the following text to English."` — nothing else changed.

---

## Task 3 — Verify Tests Pass + Run Regression Suite

- [ ] **Step 1: Run the new prompt-content tests — all 8 must pass**

```bash
cd sage-poc && uv run pytest tests/test_language.py -v -m "not slow"
```

Expected: All **11 tests PASS** (3 existing detect tests + 8 new prompt-content tests).

If any of the 4 Khaleeji/wellness tests still fail: the prompt string change is incorrect. Re-read Task 2 and confirm both functions were updated.

If any of the 4 unchanged/fallback tests fail: a resilience behaviour was accidentally broken. Check that `return result or text` is still present in `async_translate_to_arabic` and `return text` is still in the except block of `translate_to_arabic`.

- [ ] **Step 2: Run the output_gate test suite — no regressions**

The output_gate tests mock `async_translate_to_arabic` so they don't call the real function. They should be unaffected. Run them to confirm.

```bash
cd sage-poc && uv run pytest tests/test_output_gate.py -v 2>&1 | tail -10
```

Expected: All pass. Any failure here means a mock path changed — investigate before continuing.

- [ ] **Step 3: Run the full non-slow test suite**

```bash
cd sage-poc && uv run pytest --tb=short -m "not slow" -q 2>&1 | tail -10
```

Expected: All tests pass. Total count must be equal to or greater than the pre-change baseline. No new failures.

- [ ] **Step 4: Commit**

```bash
cd sage-poc && git add src/sage_poc/language.py tests/test_language.py
git commit -m "feat(language): translate to Khaleeji dialect with therapeutic register context

Replace bare MSA translation prompt with register-aware Khaleeji prompt.
English translation functions unchanged (used for safety classification).
Validated by 8 new prompt-content unit tests."
```

---

## Task 4 — Structured Native Speaker Validation Protocol

This task is a **process step**, not a code step. It generates the 10 Arabic outputs and scores them before any Arabic-facing demo.

No approval needed to run this — it's an evaluation, not a change.

### How to generate outputs

Run the following Python script (from `sage-poc/`), which calls `async_translate_to_arabic` directly with the 10 test strings. This isolates the translation function from GPT-4o's response generation so the evaluation tests the translation only.

```bash
cd sage-poc && uv run python -c "
import asyncio
from sage_poc.language import async_translate_to_arabic

INPUTS = [
    # C-1, C-2: High-emotion (warmth survival)
    'I hear you. Carrying that kind of heaviness every single day is exhausting. What has been the hardest part for you this week?',
    'That makes complete sense. When you give so much to everyone else and still feel invisible, it wears you down in a way that is hard to explain to people.',
    # C-3, C-4: Clinical content (no formal medical Arabic)
    'Anxiety sometimes shows up in the body as tension or tightness. We could try something simple together that might help things settle a little. Would that be okay?',
    'What you are describing, the low energy, the loss of interest in things you used to enjoy, makes sense as your mind protecting itself when things get too heavy.',
    # C-5, C-6: Conversational register (Khaleeji rhythm)
    'That kind of tiredness, when you are exhausted in your soul and not just your body, is real. What do you need most right now?',
    'Sometimes the weight of feeling like you have to hold everything together, especially when no one asks how you are, really gets to you. That is not weakness.',
    # C-7, C-8: Gender-neutral (document default gender agreement used)
    'You have been carrying this with so much patience. Asking for support when things are this heavy takes real courage.',
    'That is a real insight about yourself. Recognising your own strength even in difficult moments is something worth holding onto.',
    # C-9, C-10: Cultural/Islamic framing
    'There is something meaningful in the fact that you are here today. Finding support when you are struggling is a kind of strength too.',
    'You have been patient with yourself through a lot. Whatever today brings, you do not have to carry it alone.',
]

async def main():
    for i, text in enumerate(INPUTS, 1):
        result = await async_translate_to_arabic(text)
        print(f'--- Output {i} ---')
        print(f'EN: {text}')
        print(f'AR: {result}')
        print()

asyncio.run(main())
" 2>&1 | tee /tmp/khaleeji_validation.txt
```

Expected: 10 Arabic translations printed to `/tmp/khaleeji_validation.txt`. If any output is the original English text, `resilient_invoke` failed — check API key and connectivity.

### Scoring rubric (give to native speaker)

The reviewer is a native Khaleeji Arabic speaker. They read each English input and its Arabic translation and score on four dimensions (1–5):

| Dimension | 5 | 1 |
|---|---|---|
| **Dialect** | Clearly Khaleeji Gulf Arabic | Formal MSA or other Arabic variety |
| **Warmth** | Matches or exceeds source warmth | Flat, cold, or clinical tone |
| **Naturalness** | Sounds like a real person speaking | Sounds machine-translated |
| **Appropriateness** | No clinical jargon, culturally sensitive | Formal medical terminology |

**Pass threshold:** Average ≥ 3.5 across all 4 dimensions for every output. No single dimension < 3.0 for any output.

### Known limitation to document (not a blocker)

Outputs 7 and 8 use gender-neutral English. Arabic requires gendered verb and adjective agreement. The translation will default to one grammatical gender. Record which the reviewer observes and note it as a documented gap: the translation function does not receive user profile data, so gender-appropriate forms require a future extension (injecting user gender from the therapeutic profile into the translation prompt). This is deferred to Full Build.

### If validation fails

If 3 or more outputs score below threshold on **Dialect** or **Warmth**: the `gpt-4o-mini` translator is not respecting the Khaleeji register instruction even with the enriched prompt. Escalate to Experiment 4.1 — this indicates the translation step may need a more capable model or a different architecture (e.g., pass the L0 persona excerpt to the translator as a system prompt).

If only 1–2 outputs fail on **Naturalness**: acceptable for POC. Document as a known gap.

---

## Self-Review

**Spec coverage:**
- ✅ Khaleeji dialect instruction: Task 2 Step 1+2
- ✅ Therapeutic register context: Task 2 Step 1+2 (Sage identity, warmth, no clinical)
- ✅ English translation functions unchanged: Task 2 Step 3, tests in Task 1
- ✅ Resilience behaviours preserved: fallback tests in Task 1
- ✅ Regression: Task 3 Step 2+3
- ✅ Validation protocol: Task 4
- ✅ Gender limitation documented: Task 4 known limitation section

**Placeholder scan:** None found.

**Type consistency:** No new types introduced. All patches target confirmed module paths (`sage_poc.llm.get_translator`, `sage_poc.language.get_translator`, `sage_poc.resilience.resilient_invoke`).
