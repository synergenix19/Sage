# Feedback Quick-Wins Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship seven low-effort, high-leverage fixes from the 2026-06-24 user-feedback RCA: stop user-facing errors and blank replies (incl. mid-crisis), stop memory confabulation, repair Arabic English-bleed, and raise routing/knowledge/load robustness.

**Architecture:** All changes are in the `sage-poc` backend LangGraph. Six are pure code/config; one (#3) edits a versioned prompt template. Each is independently testable and shippable. No new dependencies.

> **Spec-vs-code deltas (carry into PR, not blockers for these fixes):**
> 1. The deployed graph registers **9 nodes** in `graph.py` (`add_node` x9: safety_check, intent_route, low_confidence_respond, skill_select, knowledge_retrieve, skill_executor, freeflow_respond, output_gate, crisis_response). The v7 spec ratifies **8 flat nodes**, and `low_confidence_respond` is one of them (node 3, added in v5 — confirmed in the arch-doc node table). The **only** deployed node not enumerated in the canonical 8 is **`crisis_response`**: the `crisis_protocol` branch target promoted to a discrete node. Accurate reconciliation for the architecture-doc owner: deployed graph = the 8 ratified nodes + `crisis_response`. Out of scope here (no task modifies the graph); flagged for the doc owner, not assumed resolved.
> 2. `crisis_state="monitoring"` (used by Task 2) is a **defined, live POC state** — set by `crisis_response` (`graph.py:68,138`), consumed at `graph.py:150,172` and `skill_select.py:298` (post-crisis auto-select / `post_crisis_check_in`), with re-escalation at `graph.py:43`. It is the POC's realization of the v7 post-crisis/`crisis_protocol` handling; verified in prod audit rows.

**Tech Stack:** Python 3, pytest (`asyncio_mode = "auto"`), LangGraph/LangChain, httpx, asyncpg. Run tests with `./.venv/bin/python -m pytest`.

## Global Constraints

- **Branch:** create `fix/2026-06-24-feedback-quick-wins` off `master` (these are pure-V1 fixes to the live backend, independent of the in-flight `fix/latency-ms-instrumentation` branch AND of the local-only `feat/phase0-harness` worktree, which carries the unmerged V2 retrieval-core behind the `SKILL_ROUTING_V2` flag). `sage-poc` pushes as-is (no `cdai/` prefix). **Task 6 touches `skill_select.py`, which `feat/phase0-harness` also evolves** — coordinate at that branch's eventual merge (no conflict today; master is pure-V1).
- **L0 budget drift (flag, do not silently extend):** L0 `content` is already ~593 words against a v7 spec budget of ~150 (a pre-existing ~4x drift). Task 4 raises `word_budget` to the **minimum needed (640)** to fit the justified memory clause, and flags the cumulative six-layer budget for prompt-architecture/clinical review. Do not widen beyond what the clause requires.
- **Commit granularity:** one commit per task (per the project's "one commit per finding" rule for clinical-system changes).
- **No em dashes in any user-facing string** (em dashes mirror into model output); use commas. Applies to every new copy string below.
- **Crisis number is canonical:** always source the UAE line from `sage_poc.config.CRISIS_LINE_UAE` (`"800 46342"`), never hard-code it.
- **A blank reply to a user is a clinical incident** — no code path may return an empty user-facing string.
- **Template edits (Task 4) require a version bump + clinical sign-off before *deploy*** (the code may merge to the branch; deploy is gated). Tasks 1,2,3,5,6,7 need no clinical sign-off.
- **Do not** run the existing latency/streaming work or touch `server.py`'s response/streaming path (out of scope here).
- Verify nothing regressed: after each task run the task's tests; before opening the PR run `./.venv/bin/python -m pytest -q`.

## File Structure

| Fix | Files modified | Test file |
|-----|----------------|-----------|
| #1 freeflow wrap | `src/sage_poc/nodes/freeflow_respond.py` | `tests/test_freeflow_respond.py` |
| #2 empty-reply fail-safe | `src/sage_poc/nodes/output_gate.py` | `tests/test_output_gate_empty_failsafe.py` (new) |
| #3 Arabic token guard | `src/sage_poc/language.py`, `src/sage_poc/nodes/output_gate.py` | `tests/test_language.py`, `tests/test_output_gate_arabic_token_guard.py` (new) |
| #4 memory-honesty L0 | `src/sage_poc/prompts/templates/L0_persona.json` | `tests/test_l0_memory_honesty.py` (new) |
| #5 knowledge abstain | `src/sage_poc/config.py`, `src/sage_poc/knowledge/postgres_repository.py` | `tests/test_knowledge_abstain_threshold.py` (new) |
| #6 runner-up bar + offer-floor | `src/sage_poc/config.py`, `src/sage_poc/nodes/skill_select.py` | `tests/test_skill_select_runner_up.py` (new) |
| #9 pool ceilings | `src/sage_poc/config.py`, `src/sage_poc/llm.py`, `src/sage_poc/server.py` | `tests/test_pool_config.py` (new) |

---

### Task 1: Guard the freeflow tool-loop LLM call (#1)

**Files:**
- Modify: `src/sage_poc/nodes/freeflow_respond.py` (the `for _ in range(MAX_ITERATIONS):` loop in `_invoke_with_tool_loop`, around the `ai_message = await llm_with_tools.ainvoke(messages)` line)
- Test: `tests/test_freeflow_respond.py`

**Interfaces:**
- Consumes: existing `resilient_invoke` fallback already present at the end of `freeflow_respond_node` (the `if not response:` block). `resilient_invoke` NEVER raises — it returns a warm fallback string on any failure.
- Produces: no signature change. `_invoke_with_tool_loop` returns `""` on a tool-call model exception (instead of propagating), which the caller converts to a warm fallback.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_freeflow_respond.py`:

```python
@pytest.mark.asyncio
async def test_tool_loop_model_exception_falls_back_not_raises():
    """A provider error on the bound-tools ainvoke must NOT surface as an exception;
    the user must still receive a non-empty fallback reply (RC-6 / B1)."""
    mock_llm = MagicMock()
    bound = MagicMock()
    bound.ainvoke = AsyncMock(side_effect=RuntimeError("provider 500"))
    mock_llm.bind_tools = MagicMock(return_value=bound)
    # base (non-tools) ainvoke is what resilient_invoke uses for the fallback
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="I'm here with you. What feels most present right now?"))
    mock_llm.model_name = "test-model"
    mock_llm.openai_api_base = ""

    with patch("sage_poc.nodes.freeflow_respond.get_fallback_responder", return_value=mock_llm), \
         patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules()):
        result = await freeflow_respond_node(_BASE_STATE, llm=mock_llm)

    assert result["response_en"], "user must receive a non-empty reply when the tool loop errors"
    assert "here with you" in result["response_en"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_freeflow_respond.py::test_tool_loop_model_exception_falls_back_not_raises -v`
Expected: FAIL with `RuntimeError: provider 500` propagating out of the node.

- [ ] **Step 3: Write minimal implementation**

In `src/sage_poc/nodes/freeflow_respond.py`, inside `_invoke_with_tool_loop`, replace:

```python
    for _ in range(MAX_ITERATIONS):
        ai_message = await llm_with_tools.ainvoke(messages)
```

with:

```python
    for _ in range(MAX_ITERATIONS):
        try:
            ai_message = await llm_with_tools.ainvoke(messages)
        except Exception as exc:
            import logging  # noqa: PLC0415
            logging.getLogger(__name__).warning(
                "[freeflow] tool-loop ainvoke failed (%s); returning empty to trigger fallback", exc
            )
            return ""  # caller substitutes a warm reply via resilient_invoke; never blank to user
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest tests/test_freeflow_respond.py::test_tool_loop_model_exception_falls_back_not_raises -v`
Expected: PASS

- [ ] **Step 5: Run the freeflow suite to confirm no regression**

Run: `./.venv/bin/python -m pytest tests/test_freeflow_respond.py -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/nodes/freeflow_respond.py tests/test_freeflow_respond.py
git commit -m "fix(freeflow): guard tool-loop ainvoke so provider errors fall back instead of crashing"
```

---

### Task 2: Empty-reply fail-safe in the output gate, with crisis re-surface (#2)

**Files:**
- Modify: `src/sage_poc/nodes/output_gate.py` (add a constant near `_VETTED_FALLBACK_RESPONSE`; add a guard immediately after `response_en` is resolved in `output_gate_node`; extend the import from `sage_poc.config`)
- Test: `tests/test_output_gate_empty_failsafe.py` (new)

**Interfaces:**
- Consumes: `sage_poc.config.CRISIS_LINE_UAE`, existing `_VETTED_FALLBACK_RESPONSE`, `state["crisis_state"]`.
- Produces: guarantees `output_gate_node` never emits an empty `response`/`response_en`; on a monitoring turn an empty reply is replaced with a resource re-surface line.

- [ ] **Step 1: Add the monitoring fallback constant**

In `src/sage_poc/nodes/output_gate.py`, change the config import line:

```python
from sage_poc.config import AUDIT_LOG_ENABLED
```
to:
```python
from sage_poc.config import AUDIT_LOG_ENABLED, CRISIS_LINE_UAE
```

Then, immediately after the `_VETTED_FALLBACK_RESPONSE = ...` line, add:

```python
# Re-surface resources if a MONITORING (post-crisis) turn would otherwise return blank.
# A silent turn during crisis monitoring is the worst failure mode; commas only (no em dash).
_EMPTY_MONITORING_FALLBACK = (
    "I'm still here with you. If things get harder, please reach out right now, "
    f"the UAE MoHAP support line on {CRISIS_LINE_UAE}, or 999 for an emergency."
)
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_output_gate_empty_failsafe.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from sage_poc.nodes.output_gate import output_gate_node


def make_state(**kw):
    base = {
        "gate_path": None, "path": [], "detected_language": "en",
        "message_en": "Same", "response_en": "", "is_safe": True,
        "crisis_state": "none", "crisis_flags": [], "clinical_flags": [],
        "conversation_history": [], "turn_count": 0, "conversation_summary": None,
        "session_id": "s1", "user_id": "u1", "active_skill_id": None,
        "active_step_id": None, "emotional_intensity": 5, "engagement": 5,
        "banned_opener_retry_count": 0,
    }
    return {**base, **kw}


@pytest.mark.asyncio
async def test_empty_response_substituted_on_normal_turn():
    with patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(make_state(response_en=""))
    assert result["response"].strip(), "blank reply must never reach the user"
    assert "output_gate_empty_fallback" in result["path"]


@pytest.mark.asyncio
async def test_empty_response_on_monitoring_turn_resurfaces_resources():
    state = make_state(response_en="", crisis_state="monitoring")
    with patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(state)
    assert "800 46342" in result["response"], "monitoring blank must re-surface the crisis line"
    assert "999" in result["response"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `./.venv/bin/python -m pytest tests/test_output_gate_empty_failsafe.py -v`
Expected: FAIL — `result["response"]` is empty / does not contain the number.

- [ ] **Step 4: Write minimal implementation**

In `output_gate_node`, the response is resolved by the `if gate_path == "scope_refusal": ... else: response_en = state["response_en"] or ""` block. Immediately AFTER that block (before the `_arabic_chars = ...` line), insert:

```python
    # Empty-reply fail-safe (RC-6 / feedback #2). Fires on the FIRST attempt too (the existing
    # retry-only substitution below only covers banned_opener_retry_count >= 1). A monitoring
    # turn re-surfaces resources rather than a generic line; never return silence.
    if not response_en and gate_path not in ("scope_refusal", "jailbreak"):
        if state.get("crisis_state") == "monitoring":
            response_en = _EMPTY_MONITORING_FALLBACK
        else:
            response_en = _VETTED_FALLBACK_RESPONSE
        path = path + ["output_gate_empty_fallback"]
        _log.warning(
            "[output_gate] empty response substituted (crisis_state=%s, session=%s)",
            state.get("crisis_state"), session_id,
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `./.venv/bin/python -m pytest tests/test_output_gate_empty_failsafe.py -v`
Expected: PASS

- [ ] **Step 6: Run the output_gate suite**

Run: `./.venv/bin/python -m pytest tests/test_output_gate_response_paths.py tests/test_output_gate_banned_opener.py -q`
Expected: all pass (the existing retry-only substitution still works; ours fires earlier only when response is already empty).

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/nodes/output_gate.py tests/test_output_gate_empty_failsafe.py
git commit -m "fix(output_gate): never emit a blank reply; re-surface crisis resources on empty monitoring turns"
```

---

### Task 3: Arabic English-token output guard (#4)

**Files:**
- Modify: `src/sage_poc/language.py` (add a `strict` mode to `async_translate_to_arabic`)
- Modify: `src/sage_poc/nodes/output_gate.py` (after the Arabic translation, detect leftover Latin words and re-translate once)
- Test: `tests/test_language.py`, `tests/test_output_gate_arabic_token_guard.py` (new)

**Interfaces:**
- Produces: `async_translate_to_arabic(text: str, *, strict: bool = False) -> str` — when `strict=True`, the prompt forbids leaving any English word untranslated. Default `strict=False` preserves all existing callers.
- Consumes: module-level Latin-word regex + small acronym allowlist in `output_gate.py`.

- [ ] **Step 1: Write the failing test for strict translation prompt**

Add to `tests/test_language.py`:

```python
def test_strict_arabic_prompt_forbids_english_words():
    from sage_poc.language import _build_khaleeji_translation_prompt
    strict = _build_khaleeji_translation_prompt("how is your sleep lately", strict=True)
    assert "Arabic script" in strict or "no English" in strict.lower()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_language.py::test_strict_arabic_prompt_forbids_english_words -v`
Expected: FAIL — `_build_khaleeji_translation_prompt()` takes no `strict` argument.

- [ ] **Step 3: Add `strict` to the translation prompt and async helper**

In `src/sage_poc/language.py`, change `_build_khaleeji_translation_prompt`:

```python
def _build_khaleeji_translation_prompt(text: str, *, strict: bool = False) -> str:
```
and, inside it, append a strict clause to the first instruction line. Replace the `f"Return only the translation."` segment of the first list element so the element ends with:

```python
        f"Return only the translation."
        + (
            " The output must be entirely in Arabic script with no English words; "
            "translate or transliterate any names or terms." if strict else ""
        ),
```

Then update the async helper to accept and forward `strict`:

```python
async def async_translate_to_arabic(text: str, *, strict: bool = False) -> str:
    """Translate text to Khaleeji Gulf Arabic using resilient_invoke. Returns original on failure."""
    from sage_poc.resilience import resilient_invoke
    result = await resilient_invoke(
        get_translator(),
        [{
            "role": "user",
            "content": _build_khaleeji_translation_prompt(text, strict=strict),
        }],
        node="translate_to_arabic",
        language="ar",
    )
    return result or text
```

- [ ] **Step 4: Run the language test**

Run: `./.venv/bin/python -m pytest tests/test_language.py::test_strict_arabic_prompt_forbids_english_words -v`
Expected: PASS

- [ ] **Step 5: Write the failing output-gate guard test**

Create `tests/test_output_gate_arabic_token_guard.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from sage_poc.nodes.output_gate import output_gate_node


def make_state(**kw):
    base = {
        "gate_path": None, "path": [], "detected_language": "ar",
        "message_en": "I can't sleep", "response_en": "Tell me about your sleep.",
        "is_safe": True, "crisis_state": "none", "crisis_flags": [], "clinical_flags": [],
        "conversation_history": [], "turn_count": 0, "conversation_summary": None,
        "session_id": "s1", "user_id": "u1", "active_skill_id": None, "active_step_id": None,
        "emotional_intensity": 5, "engagement": 5, "banned_opener_retry_count": 0,
    }
    return {**base, **kw}


@pytest.mark.asyncio
async def test_latin_word_in_arabic_output_triggers_strict_retranslate():
    """First translation leaks an English word; the guard re-translates strict and the
    leaked word is gone (RC-5 / feedback #4: 'نومك lately')."""
    calls = {"n": 0}

    async def fake_translate(text, *, strict=False):
        calls["n"] += 1
        # First (non-strict) call leaks English; strict retry is clean.
        return "كيف نومك lately؟" if not strict else "كيف نومك مؤخرا؟"

    with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", side_effect=fake_translate), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(make_state())

    assert calls["n"] == 2, "guard must re-translate once when Latin words remain"
    assert "lately" not in result["response"]
    assert "arabic_token_guard_retranslate" in result["path"]


@pytest.mark.asyncio
async def test_clean_arabic_output_not_retranslated():
    async def fake_translate(text, *, strict=False):
        return "كيف نومك مؤخرا؟"
    seen = {"n": 0}
    async def counting(text, *, strict=False):
        seen["n"] += 1
        return await fake_translate(text, strict=strict)
    with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", side_effect=counting), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        await output_gate_node(make_state())
    assert seen["n"] == 1, "clean Arabic must not trigger a second translation"
```

- [ ] **Step 6: Run to verify failure**

Run: `./.venv/bin/python -m pytest tests/test_output_gate_arabic_token_guard.py -v`
Expected: FAIL — only one translate call; `"lately"` still present; marker absent.

- [ ] **Step 7: Implement the guard in output_gate**

In `src/sage_poc/nodes/output_gate.py`, add a module-level regex + allowlist near the other regexes (after `_HAS_ARABIC_RE`):

```python
# Arabic-output English-bleed guard (feedback #4). Latin alphabetic runs of length >= 3 that
# are not known acronyms/brands indicate an untranslated English word in an Arabic reply.
_LATIN_WORD_RE = re.compile(r"[A-Za-z]{3,}")
_LATIN_ALLOWLIST = {"cbt", "act", "dbt", "tipp", "sage", "youtube"}


def _has_english_bleed(text: str) -> bool:
    return any(w.lower() not in _LATIN_ALLOWLIST for w in _LATIN_WORD_RE.findall(text))
```

Then replace the translation block:

```python
    if lang == "ar" and not _response_en_is_arabic:
        final_response = await async_translate_to_arabic(response_en)
    else:
        final_response = response_en
    final_response = _strip_output_format(final_response)
```

with:

```python
    if lang == "ar" and not _response_en_is_arabic:
        final_response = await async_translate_to_arabic(response_en)
        if _has_english_bleed(final_response):
            _log.warning("[output_gate] English bleed in Arabic output; re-translating strict")
            final_response = await async_translate_to_arabic(response_en, strict=True)
            path = path + ["arabic_token_guard_retranslate"]
            if _has_english_bleed(final_response):
                _log.warning("[output_gate] English bleed persists after strict re-translate (telemetry only)")
    else:
        final_response = response_en
    final_response = _strip_output_format(final_response)
```

- [ ] **Step 8: Run the guard tests + language suite**

Run: `./.venv/bin/python -m pytest tests/test_output_gate_arabic_token_guard.py tests/test_language.py -q`
Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add src/sage_poc/language.py src/sage_poc/nodes/output_gate.py tests/test_language.py tests/test_output_gate_arabic_token_guard.py
git commit -m "fix(arabic): guard Arabic output against untranslated English words via strict re-translate"
```

---

### Task 4: Memory-honesty instruction in L0 persona (#3)

**Files:**
- Modify: `src/sage_poc/prompts/templates/L0_persona.json` (add a MEMORY clause to `content`; bump `version` to `2.3.0`; bump `word_budget`; add a pending-sign-off note)
- Test: `tests/test_l0_memory_honesty.py` (new)

**Deploy gate:** This edits a clinically-approved template. The change may merge to the branch, but **must not deploy** until clinical lead signs off the new clause (light review). Mark accordingly in the JSON.

**Interfaces:**
- Produces: every assembled system prompt now contains an explicit "you cannot see other chats; if asked to recall and nothing is provided, say so; never claim a detail was never provided" instruction (fixes A4 confabulation).

- [ ] **Step 1: Write the failing test**

Create `tests/test_l0_memory_honesty.py`:

```python
import json, pathlib

_L0 = pathlib.Path("src/sage_poc/prompts/templates/L0_persona.json")


def test_l0_has_memory_honesty_clause_and_version_bump():
    data = json.loads(_L0.read_text(encoding="utf-8"))
    assert data["version"] == "2.3.0", "version must be bumped for the memory-honesty clause"
    content = data["content"].lower()
    assert "memory" in content
    # must instruct honest 'I don't have access' and forbid false denial
    assert "do not have access" in content or "don't have access" in content
    assert "never claim" in content
    # word budget must still accommodate the content
    assert len(data["content"].split()) <= data["word_budget"]
```

- [ ] **Step 2: Run to verify failure**

Run: `./.venv/bin/python -m pytest tests/test_l0_memory_honesty.py -v`
Expected: FAIL — version is `2.2.0`, no memory clause.

- [ ] **Step 3: Edit the L0 template**

In `src/sage_poc/prompts/templates/L0_persona.json`:
1. Change `"version": "2.2.0"` to `"version": "2.3.0"`.
2. Change `"word_budget": 600` to `"word_budget": 640` (minimum needed to fit the clause; current content is 593 words + the ~40-word clause = 633). Do not widen further; see the L0-budget-drift constraint.
3. Add a new key after `"_signed_off_v2_2_0"` (note: commas, no em dash, per the global constraint):
   `"_pending_signoff_v2_3_0": "PENDING clinical sign-off, adds MEMORY honesty clause (fixes confabulation finding A4, 2026-06-24); do not deploy until signed off. NOTE: L0 content (now ~633 words) is ~4x the v7 ~150-word budget, cumulative six-layer budget needs prompt-architecture review.",`
4. In `"content"`, immediately before the `CONVERSATION DISCIPLINE:` sentence, insert this clause (note the `\n\n` separators, commas not dashes):

```
MEMORY: You can see only this conversation, unless earlier-session context appears below. If asked to recall something not shown to you, say you do not have access and invite them to share it again, never claim it was never provided.\n\n
```

- [ ] **Step 4: Run the test**

Run: `./.venv/bin/python -m pytest tests/test_l0_memory_honesty.py -v`
Expected: PASS

- [ ] **Step 5: Run any template-validation + composer tests**

Run: `./.venv/bin/python -m pytest tests/test_freeflow_respond.py -q -k "compose or persona or layer"`
Expected: pass (L0 still loads and assembles).

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/prompts/templates/L0_persona.json tests/test_l0_memory_honesty.py
git commit -m "feat(L0): add memory-honesty clause (v2.3.0, pending clinical sign-off) to stop cross-chat confabulation"
```

---

### Task 5: Knowledge abstain threshold off the 0.0 POC default (#5)

**Files:**
- Modify: `src/sage_poc/config.py` (new env-configurable constant)
- Modify: `src/sage_poc/knowledge/postgres_repository.py` (source threshold from config; extract a testable filter helper)
- Test: `tests/test_knowledge_abstain_threshold.py` (new)

**Interfaces:**
- Produces: `KNOWLEDGE_ABSTAIN_THRESHOLD` now reads `SAGE_KNOWLEDGE_ABSTAIN_THRESHOLD` (default `0.015`, a conservative interim above pure RRF noise); a pure helper `_passes_abstain(rrf_score: float) -> bool`.

- [ ] **Step 1: Add the config constant**

In `src/sage_poc/config.py`, after the `CRISIS_LINE_UAE` block, add:

```python
# Knowledge retrieval abstain floor. POC shipped 0.0 (never abstain), which surfaced weak
# RRF passages as authoritative (feedback #5 "Google is better"). Interim conservative default
# 0.015 (just above single-list rank-2+ RRF noise with k=60); finalize via
# scripts/calibrate_retrieval_threshold.py once a labeled query set exists.
KNOWLEDGE_ABSTAIN_THRESHOLD = float(os.getenv("SAGE_KNOWLEDGE_ABSTAIN_THRESHOLD", "0.015"))
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_knowledge_abstain_threshold.py`:

```python
def test_threshold_is_nonzero_and_filters_weak_passages():
    from sage_poc.knowledge import postgres_repository as pr
    assert pr.KNOWLEDGE_ABSTAIN_THRESHOLD > 0.0, "POC 0.0 default must be raised"
    # a weak single-list rank-20 RRF score (1/80 = 0.0125) must NOT pass
    assert pr._passes_abstain(0.0125) is False
    # a dual-list rank-1 RRF score (1/61 + 1/61 = 0.0328) must pass
    assert pr._passes_abstain(0.0328) is True
```

- [ ] **Step 3: Run to verify failure**

Run: `./.venv/bin/python -m pytest tests/test_knowledge_abstain_threshold.py -v`
Expected: FAIL — `KNOWLEDGE_ABSTAIN_THRESHOLD` is `0.0`; `_passes_abstain` does not exist.

- [ ] **Step 4: Wire config + helper into the repository**

In `src/sage_poc/knowledge/postgres_repository.py`:
1. Replace the constant definition:
```python
KNOWLEDGE_ABSTAIN_THRESHOLD: float = 0.0
```
with:
```python
from sage_poc.config import KNOWLEDGE_ABSTAIN_THRESHOLD  # env-configurable; see config.py


def _passes_abstain(rrf_score: float) -> bool:
    """A passage clears the abstain floor when its RRF score exceeds the threshold."""
    return rrf_score > KNOWLEDGE_ABSTAIN_THRESHOLD
```
2. In `retrieve()`, replace the filter line:
```python
            if row["rrf_score"] <= KNOWLEDGE_ABSTAIN_THRESHOLD:
                continue
```
with:
```python
            if not _passes_abstain(row["rrf_score"]):
                continue
```

- [ ] **Step 5: Run the test + knowledge suite**

Run: `./.venv/bin/python -m pytest tests/test_knowledge_abstain_threshold.py tests/test_knowledge_repository.py -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/config.py src/sage_poc/knowledge/postgres_repository.py tests/test_knowledge_abstain_threshold.py
git commit -m "fix(knowledge): raise abstain floor off 0.0 POC default (env-configurable, conservative interim)"
```

- [ ] **Step 7 (follow-up, non-code, note in PR):** Run `./.venv/bin/python scripts/calibrate_retrieval_threshold.py` against the prod corpus with a small labeled in-scope/out-of-domain query set to replace `0.015` with the empirically separating value; record the value and set `SAGE_KNOWLEDGE_ABSTAIN_THRESHOLD` in the deploy env. (Tracked, not blocking this commit.)

---

### Task 6: Runner-up bar + offer-floor in skill routing (#6)

**Files:**
- Modify: `src/sage_poc/config.py` (two tunables)
- Modify: `src/sage_poc/nodes/skill_select.py` (extract a testable `_select_runner_up`; apply an offer-confidence floor in the node)
- Test: `tests/test_skill_select_runner_up.py` (new)

**Sign-off:** Step 3 (runner-up tightening) is behavior-safe — it only drops a weak *second* offer, never changes the primary. Step 5 (offer-floor) changes whether a skill is offered at all and needs a **light clinical confirm** of the floor value before deploy; ship it config-gated with a conservative default.

**Interfaces:**
- Produces: `_select_runner_up(ranked: list[tuple[str, float]], best_sid: str, best_score: float) -> tuple[str, float] | None`; config `SKILL_RUNNER_UP_MIN` (default `0.50`), `SKILL_RUNNER_UP_MARGIN` (default `0.05`), `SKILL_OFFER_CONFIDENCE_FLOOR` (default `0.50`).

- [ ] **Step 1: Add config tunables**

In `src/sage_poc/config.py`, append:

```python
# Skill-routing precision (feedback #6). A runner-up (second offer) must be strong AND close
# to the primary, else only the primary is offered. The offer floor suppresses noise-band
# single matches (0.46-0.49) into freeflow exploration. Defaults conservative; confirm with clinical.
SKILL_RUNNER_UP_MIN = float(os.getenv("SAGE_SKILL_RUNNER_UP_MIN", "0.50"))
SKILL_RUNNER_UP_MARGIN = float(os.getenv("SAGE_SKILL_RUNNER_UP_MARGIN", "0.05"))
SKILL_OFFER_CONFIDENCE_FLOOR = float(os.getenv("SAGE_SKILL_OFFER_CONFIDENCE_FLOOR", "0.50"))
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_skill_select_runner_up.py`:

```python
import pytest
from unittest.mock import patch
from sage_poc.nodes import skill_select as ss


def test_runner_up_dropped_when_below_min():
    ranked = [("worry_time", 0.62), ("financial_anxiety", 0.47)]
    assert ss._select_runner_up(ranked, "worry_time", 0.62) is None  # 0.47 < MIN 0.50


def test_runner_up_dropped_when_outside_margin():
    ranked = [("worry_time", 0.70), ("grief_loss", 0.51)]
    # 0.51 >= MIN but 0.70-0.51=0.19 > MARGIN 0.05
    assert ss._select_runner_up(ranked, "worry_time", 0.70) is None


def test_runner_up_kept_when_strong_and_close():
    ranked = [("worry_time", 0.62), ("psychoed_stress", 0.59)]
    assert ss._select_runner_up(ranked, "worry_time", 0.62) == ("psychoed_stress", 0.59)


@pytest.mark.asyncio
async def test_noise_band_primary_routes_to_freeflow():
    """A semantic match in the noise band (below the offer floor) must not be offered."""
    state = {
        "primary_intent": "new_skill", "crisis_state": "none", "clinical_flags": [],
        "offered_skill_ids": None, "message_en": "i feel a bit off today",
        "raw_message": "i feel a bit off today", "detected_language": "en",
        "path": ["safety_check", "intent_route"], "declined_skills": [],
        "therapeutic_profile": {}, "emotional_intensity": 4,
    }
    with patch.object(ss, "_semantic_match_with_runner_up", return_value=("worry_time", 0.47, None)):
        result = await ss.skill_select_node(state)
    assert result["active_skill_id"] is None
    assert not result.get("offered_skill_ids")
    assert "offer_floor_freeflow" in result["path"]
```

- [ ] **Step 3: Run to verify failure**

Run: `./.venv/bin/python -m pytest tests/test_skill_select_runner_up.py -v`
Expected: FAIL — `_select_runner_up` missing; noise-band match still offered.

- [ ] **Step 4: Extract and tighten the runner-up selector**

In `src/sage_poc/nodes/skill_select.py`:
1. Add the import + module constants near the other thresholds (after `_RERANK_TOP_K`):
```python
from sage_poc.config import (
    SKILL_RUNNER_UP_MIN, SKILL_RUNNER_UP_MARGIN, SKILL_OFFER_CONFIDENCE_FLOOR,
)


def _select_runner_up(
    ranked: list[tuple[str, float]], best_sid: str, best_score: float
) -> tuple[str, float] | None:
    """Second offer candidate: the highest OTHER skill that is both strong
    (>= SKILL_RUNNER_UP_MIN) and close to the primary (within SKILL_RUNNER_UP_MARGIN).
    Returns None otherwise, so a weak/distant second skill is never offered (feedback #6)."""
    for sid, sc in ranked:
        if sid == best_sid:
            continue
        if sc >= SKILL_RUNNER_UP_MIN and (best_score - sc) <= SKILL_RUNNER_UP_MARGIN:
            return (sid, sc)
        # ranked is descending; once a candidate fails the min, none after it can pass
        return None
    return None
```
2. Inside `_semantic_match_with_runner_up`, replace the nested `_runner_up` closure with calls to the new helper. Change the closure definition:
```python
    def _runner_up(best: str | None) -> tuple[str, float] | None:
        if best is None:
            return None
        for sid, sc in ranked:
            if sid != best and sc >= SEMANTIC_THRESHOLD:
                return (sid, sc)
        return None
```
to:
```python
    def _runner_up(best: str | None) -> tuple[str, float] | None:
        if best is None:
            return None
        return _select_runner_up(ranked, best, best_score)
```
(The three `return ..., _runner_up(...)` call sites remain unchanged. Note `best_score` is the top score bound at `best_sid, best_score = ranked[0]`; for the rerank branch the helper still compares against the original top, which is the correct closeness anchor.)

- [ ] **Step 5: Apply the offer-confidence floor in the node**

In `skill_select_node`, the Tier-2 success branch reads:
```python
    if semantic_skill is not None:
        candidates = [semantic_skill]
        if runner_up is not None and runner_up[0] != semantic_skill:
            candidates.append(runner_up[0])
```
Insert a floor check at the very top of that `if` block:
```python
    if semantic_skill is not None:
        if score < SKILL_OFFER_CONFIDENCE_FLOOR:
            # Noise-band match (>= routing threshold but below offer confidence): explore in
            # freeflow instead of offering an off-target skill (feedback #6, A5).
            return {
                **stale_offer_clear,
                "active_skill_id": None,
                "active_step_id": None,
                "skill_match_method": None,
                "semantic_score": round(score, 4),
                "path": state["path"] + ["skill_select", "offer_floor_freeflow"],
            }
        candidates = [semantic_skill]
        if runner_up is not None and runner_up[0] != semantic_skill:
            candidates.append(runner_up[0])
```

- [ ] **Step 6: Run the new tests + skill_select suite**

Run: `./.venv/bin/python -m pytest tests/test_skill_select_runner_up.py tests/test_skill_select.py -q`
Expected: all pass. If a pre-existing skill_select test asserts an offer at a sub-0.50 semantic score, that is the intended behavior change — update that test to expect freeflow and note it in the PR (flag for the clinical confirm).

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/config.py src/sage_poc/nodes/skill_select.py tests/test_skill_select_runner_up.py
git commit -m "fix(routing): tighten runner-up bar and add offer-confidence floor to stop off-target skill offers"
```

---

### Task 7: Raise DB and LLM pool ceilings (#9)

**Files:**
- Modify: `src/sage_poc/config.py` (pool tunables)
- Modify: `src/sage_poc/llm.py` (httpx limits from config, via a testable factory)
- Modify: `src/sage_poc/server.py` (asyncpg `max_size` from config)
- Test: `tests/test_pool_config.py` (new)

**Interfaces:**
- Produces: config `DB_POOL_MAX_SIZE` (default `20`), `HTTP_MAX_CONNECTIONS` (default `100`), `HTTP_MAX_KEEPALIVE` (default `20`); `llm._http_limits() -> httpx.Limits`.

- [ ] **Step 1: Add config tunables**

In `src/sage_poc/config.py`, append:

```python
# Connection-pool ceilings (feedback #9). POC ran asyncpg max_size=5 and httpx keepalive=5,
# which throttled under the 58-user load behind the p95 latency. Raise + make env-configurable.
DB_POOL_MAX_SIZE = int(os.getenv("SAGE_DB_POOL_MAX_SIZE", "20"))
HTTP_MAX_CONNECTIONS = int(os.getenv("SAGE_HTTP_MAX_CONNECTIONS", "100"))
HTTP_MAX_KEEPALIVE = int(os.getenv("SAGE_HTTP_MAX_KEEPALIVE", "20"))
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_pool_config.py`:

```python
def test_pool_defaults_raised():
    from sage_poc import config
    assert config.DB_POOL_MAX_SIZE >= 20
    assert config.HTTP_MAX_KEEPALIVE >= 20
    assert config.HTTP_MAX_CONNECTIONS >= 100


def test_llm_http_limits_use_config():
    from sage_poc import llm, config
    limits = llm._http_limits()
    assert limits.max_keepalive_connections == config.HTTP_MAX_KEEPALIVE
    assert limits.max_connections == config.HTTP_MAX_CONNECTIONS
```

- [ ] **Step 3: Run to verify failure**

Run: `./.venv/bin/python -m pytest tests/test_pool_config.py -v`
Expected: FAIL — config names missing; `llm._http_limits` missing.

- [ ] **Step 4: Wire config into llm.py**

In `src/sage_poc/llm.py`:
1. Extend the config import to include the new names:
```python
from sage_poc.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    CLASSIFIER_MODEL,
    RESPONDER_MODEL,
    TRANSLATOR_MODEL,
    FALLBACK_RESPONDER_MODEL,
    FALLBACK_CLASSIFIER_MODEL,
    RESISTANCE_MODEL,
    HTTP_MAX_CONNECTIONS,
    HTTP_MAX_KEEPALIVE,
)
```
2. Add a factory and use it for the client:
```python
def _http_limits() -> httpx.Limits:
    return httpx.Limits(
        max_connections=HTTP_MAX_CONNECTIONS,
        max_keepalive_connections=HTTP_MAX_KEEPALIVE,
        keepalive_expiry=300,
    )


_ASYNC_HTTP_CLIENT = httpx.AsyncClient(limits=_http_limits())
```
(Replace the existing `_ASYNC_HTTP_CLIENT = httpx.AsyncClient(limits=httpx.Limits(...))` block.)

- [ ] **Step 5: Wire config into server.py**

In `src/sage_poc/server.py`, where `asyncpg.create_pool(...)` is called, change `max_size=5` to `max_size=DB_POOL_MAX_SIZE` and add the import at the top of the file (with the other `sage_poc.config` imports, or a new import line):
```python
from sage_poc.config import DB_POOL_MAX_SIZE
```
Resulting call:
```python
            asyncpg_pool = await asyncpg.create_pool(
                db_url,
                min_size=1,
                max_size=DB_POOL_MAX_SIZE,
                max_inactive_connection_lifetime=300,
            )
```

- [ ] **Step 6: Run the test**

Run: `./.venv/bin/python -m pytest tests/test_pool_config.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/config.py src/sage_poc/llm.py src/sage_poc/server.py tests/test_pool_config.py
git commit -m "perf(pools): raise DB max_size and httpx keepalive/connection ceilings (env-configurable)"
```

---

## Final verification (before PR)

- [ ] Run the full suite: `./.venv/bin/python -m pytest -q`. Expected: green (note any pre-existing failures unrelated to these tasks in the PR).
- [ ] Confirm no em dashes were introduced: `git diff master --unified=0 | grep -n "—"` returns nothing.
- [ ] Open PR `fix/2026-06-24-feedback-quick-wins` → `master`. In the body:
  - List the seven commits.
  - Flag **Task 4 (L0 v2.3.0) and Task 6 step 5 (offer floor) as deploy-gated on clinical sign-off**; note the Task 5 calibration follow-up.
  - Flag the **spec-vs-code deltas** (9 vs 8 nodes; L0 ~4x word-budget drift) for the architecture-doc owner.
  - Flag the **Task 3 Latin allowlist** (`cbt, act, dbt, tipp, sage, youtube`) for confirmation — it is a reasonable default clinical-acronym/brand set, easily extended; confirm it matches the terms Sage legitimately emits in Arabic replies so the guard does not needlessly re-translate them.
  - Note **Task 6 / `skill_select.py`** overlaps `feat/phase0-harness`; coordinate at that branch's merge.

## Self-Review

- **Spec coverage:** all seven requested fixes (#1, #2, #3, #4, #5, #6, #9) have a task. ✓
- **Sign-off boundaries:** the only sign-off-gated changes (L0 clause #3→Task 4; offer floor #6→Task 6 step 5) are flagged and shipped behind a version bump / config default so they can land code-complete and flip on approval. ✓
- **Type/name consistency:** `_select_runner_up`, `_passes_abstain`, `_http_limits`, `_has_english_bleed`, `async_translate_to_arabic(..., strict=)`, `_EMPTY_MONITORING_FALLBACK` are each defined in the task that introduces them and referenced consistently. ✓
- **No placeholders:** every code and test step contains the actual code, command, and expected result. ✓
- **Risk note:** Tasks 1, 2, 5, 7 are behavior-safe hardening; Task 3 changes Arabic output only when English bleed is detected; Task 4 and Task 6-step-5 are the only behavior changes needing human sign-off and are gated.
