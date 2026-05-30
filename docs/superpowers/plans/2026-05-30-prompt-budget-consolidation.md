# Tier 3 Prompt Budget Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the L1 history squeeze caused by verbose skill cultural_overrides — by lowering the override cap to the clinically signed-off bound, then wiring the actual override word count into the L1 budget calculation so history is proactively sized.

**Architecture:** Two-phase approach. Task 0 (prerequisite): lower `_CULTURAL_OVERRIDE_BUDGET_WORDS` from 500 to 200 (pending clinical sign-off) and add the CI gate test. The seven over-budget skill JSON files are remediated in a parallel CMS clinical review track — they are not touched by the engineer. Once the clinical track delivers, the worst-case L1 subtraction becomes 200w, giving L1 a floor of 250w on every current skill turn — the budget-wiring in Tasks 1–2 then becomes defensive depth rather than load-bearing. Task 1 adds the `override_words` parameter to `_compute_l1_budget`. Task 2 wires the actual injected word count through and adds an end-to-end behavioral test that discriminates between fixed and unfixed code. The overflow guard at the bottom of `compose_prompt` remains unchanged as a §5.6.3 safety net.

**Tech Stack:** Python 3.14, pytest. No new dependencies.

---

## Architecture background for the implementer

### Why turn-relevance filtering is NOT in this plan

The feedback thread resolved this explicitly. Global cultural rules (Rules Service JSON) are safe to relevance-filter in the prompt because `output_gate` (§5.5, §6.5.7) re-evaluates the full set on generated text — the gate is the deterministic backstop. Skill `cultural_overrides` have no equivalent backstop: per the conformance registry their only runtime use is `injected_by: compose_prompt (system role)`. Filtering overrides by input keywords would selectively remove a guardrail on turns where the cultural risk lives in the output, not the input — a user who never says "family" can still receive a response that frames assertiveness as "stand up to your parents." That violates Absolute Rules on cultural enforcement, determinism, and safety over capability.

**Filtering is architecturally correct long-term, but only after skill overrides gain a deterministic gate backstop.** See Architectural Review Item B at the bottom of this document. Do not add input-keyword filtering in this plan.

### Why the cap reduction is safe without filtering

Lowering the cap forces clinicians to author concise, complete overrides that apply on every turn the skill is active. It never selectively removes a guardrail. All 13 skills currently within 189w show that effective overrides can be written in that range. Re-authoring the seven over-budget skills to ≤200w is clinical editing work, not architectural change.

### Spec divergence to know about

`_L1_BASE_BUDGET = 450` and `_L1_FLEX_BUDGET = 600` are pre-existing divergences from v7 §5.6.1 (~300w). This plan does not introduce or worsen them. See Architectural Review Item A. A spec-divergence comment is added in Task 1.

The `primary_intent == "info_request"` proxy in `_compute_l1_budget` misses tool-invoked knowledge (§6.5.2 knowledge_lookup can add ~300w of evidence on a turn classified as emotional support). This is pre-existing and not worsened here. A one-line POC note citing §6.5.2 is added in Task 1.

### Stale active_skill_id — confirmed closed

`active_skill_id` is cleared at: `skill_executor.py:338` (L1 escalation exit), `skill_executor.py:430` (skill_complete), `skill_select.py:81` (info_request), `skill_select.py:133` and `:152` (no-match/freeflow). LangGraph propagates the returned dict to subsequent nodes in the same turn, so `compose_prompt` (called inside the responder node, which runs after skill_executor) sees the cleared value on the completion turn. The stale-session path (`_stale_skill_overrides`) sets `active_skill_id=None` and is covered by cross-concern test C-1. This concern is closed.

---

## File Structure

**Modify (engineering track — this plan):**
- `src/sage_poc/prompts/composer.py:92-121` — constant + `_compute_l1_budget`
- `src/sage_poc/prompts/composer.py:296` — lower cap constant
- `src/sage_poc/prompts/composer.py:347-367` — capture `_override_words`
- `src/sage_poc/prompts/composer.py:398` — pass `override_words=_override_words`
- `src/sage_poc/skills/conformance.py:54-57` — update note
- `tests/test_prompts_composer.py` — new tests appended

---

## Task 0: Lower the cap and add the CI gate test (PREREQUISITE — engineering track)

**This task must be complete before Tasks 1–2.** Without it, the 150w floor in Task 1 is clinically unsanctioned (150w = 1–2 turns, risky on structured skill turns). With it, the worst-case L1 budget is max(150, 450-200) = 250w — never near the floor — and the floor becomes unreachable defensive code.

**Clinical sign-off required on the cap value before this task begins.** The suggested value of 200w aligns with the highest compliant skill (stop_technique at 182w) plus a small authoring buffer. All 13 currently compliant skills are 63–182w; their authors demonstrated effective overrides in that range. If the clinical team chooses a different value, replace 200 throughout this task.

**Clinical governance boundary.** This task has two halves with different owners:

- **Engineering (this task):** Lower `_CULTURAL_OVERRIDE_BUDGET_WORDS` from 500 to 200 and write the CI gate test. This can merge immediately. After the constant is lowered, the 7 over-budget skills will silently drop their overrides at runtime (same behaviour as before the Phase F 500w fix), and the CI test will be RED. The CI RED state is the clinical governance gate — it tracks outstanding work, not a broken build.
- **Clinical (separate CMS workflow):** The 7 over-budget skill JSON files must be re-authored by clinicians through the CMS draft→peer-review→approval workflow per §9.4–9.5. An engineer may draft condensed proposals as CMS drafts, but the CMS approval (Emirati-speaker review + both clinicians) is the merge gate. Once CMS delivers, the CI test goes GREEN. The 7 files are **not** in the commit below and **must not** be committed by an engineer.

Parallel execution: Tasks 1 and 2 (code-side changes) can proceed concurrently with the clinical CMS workflow. All merge together when both tracks are complete.

**Files:**
- Modify: `src/sage_poc/prompts/composer.py:296`
- Test: `tests/test_prompts_composer.py`

- [ ] **Step 1: Write the verification test first**

Append to `tests/test_prompts_composer.py`:

```python
# ---- Task 0: cap reduction verification ----

import json
import os

_SKILLS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "src", "sage_poc", "skills"
)
_CAP_WORDS = 200  # must match _CULTURAL_OVERRIDE_BUDGET_WORDS after Task 0


def _block_words(overrides: dict) -> int:
    from sage_poc.tokens import count_words
    lines = "\n".join(f"- {v}" for v in overrides.values())
    block = f"SKILL-SPECIFIC CULTURAL CONTEXT:\n{lines}"
    return count_words(block)


def test_all_skills_cultural_overrides_within_cap():
    """Every skill's cultural_overrides must fit within _CULTURAL_OVERRIDE_BUDGET_WORDS.
    Fails with the exact word count and file name for each violation — fix the JSON,
    not the test.
    """
    over_budget = []
    for fname in sorted(os.listdir(_SKILLS_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(_SKILLS_DIR, fname)) as f:
            data = json.load(f)
        overrides = data.get("cultural_overrides") or {}
        if overrides:
            wc = _block_words(overrides)
            if wc > _CAP_WORDS:
                over_budget.append((data["skill_id"], wc))
    assert not over_budget, (
        f"Skills exceed {_CAP_WORDS}-word override cap "
        f"(fix the JSON files, not the constant):\n"
        + "\n".join(f"  {sid}: {wc}w" for sid, wc in over_budget)
    )
```

- [ ] **Step 2: Run the test — confirm it catches all seven violations**

```bash
pytest tests/test_prompts_composer.py::test_all_skills_cultural_overrides_within_cap -v
```

Expected: FAIL listing all seven over-budget skills with their word counts.

- [ ] **Step 3: Lower the constant**

In `src/sage_poc/prompts/composer.py` line 296, change:

```python
_CULTURAL_OVERRIDE_BUDGET_WORDS = 500  # per-skill cultural override budget; covers all 20 v7 skills
```

to:

```python
_CULTURAL_OVERRIDE_BUDGET_WORDS = 200  # clinician-signed cap; forces concise complete overrides
```

- [ ] **Step 4: Confirm the test shows the 7 violations after the constant change**

```bash
pytest tests/test_prompts_composer.py::test_all_skills_cultural_overrides_within_cap -v
```

Expected: FAIL, listing all seven over-budget skills. This is the correct state — the CI failure is the tracking gate for the parallel CMS remediation workflow. It confirms:
1. The test still catches the same 7 skills. (Note: `_CAP_WORDS = 200` is hardcoded in the test, independent of the production constant — the test was already failing at Step 2 for this reason. Confirm the violation list is identical.)
2. The constant change had no unintended side effects on other tests.

Do not attempt to make this test pass by editing the JSON files. That is clinical work for the CMS track.

- [ ] **Step 5: Commit engineering-only changes**

```bash
git add src/sage_poc/prompts/composer.py tests/test_prompts_composer.py
git commit -m "fix(composer): lower cultural_overrides cap to 200w; add CI gate test for override budget"
```

The 7 over-budget skill JSON files are excluded. CI will be RED on `test_all_skills_cultural_overrides_within_cap` until the CMS track delivers. Tasks 1 and 2 proceed from here.

---

## Task 1: Extend `_compute_l1_budget` to accept and apply override_words

With Task 0 complete, the worst-case input to this function is 200w. The resulting L1 budget is max(150, 450-200) = 250w — the 150w floor is unreachable on every current skill. It remains as defensive code for future over-budget edge cases and signals clearly to the next reader that 150w is the clinical minimum.

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
    """Hypothetical 445-word override: max(150, 450-445) = 150. Defensive only — unreachable
    on current skills after Task 0 lowers cap to 200w."""
    assert _compute_l1_budget(_skill_state(), override_words=445) == 150


def test_compute_l1_budget_freeflow_base_also_reduced():
    """Freeflow base is 600. 200-word override: 600 - 200 = 400.
    Note: freeflow turns have no active_skill_id so override_words will be 0 in practice.
    This tests the arithmetic in isolation."""
    assert _compute_l1_budget(_freeflow_state(), override_words=200) == 400
```

- [ ] **Step 2: Run — confirm all four fail**

```bash
pytest tests/test_prompts_composer.py -k "compute_l1_budget" -v
```

Expected: 4 failures — `TypeError: _compute_l1_budget() got an unexpected keyword argument 'override_words'`

- [ ] **Step 3: Add `_L1_MINIMUM_BUDGET` and update `_compute_l1_budget`**

In `src/sage_poc/prompts/composer.py`, add the constant immediately after `_L1_FLEX_BUDGET = 600` (line 93):

```python
_L1_BASE_BUDGET = 450
_L1_FLEX_BUDGET = 600
_L1_MINIMUM_BUDGET = 150  # defensive floor — clinical minimum; unreachable after Task 0 cap reduction
```

Replace the body of `_compute_l1_budget` (lines 104–121):

```python
def _compute_l1_budget(state: SageState, override_words: int = 0) -> int:
    """Return the L1 word budget for this turn.

    On freeflow turns (no skill step, no knowledge lookup), L3 and L4 layers
    are absent. Their unused budget headroom is loaned to L1 so that rich
    multi-turn disclosures don't get truncated.

    override_words: actual word count of the skill cultural_overrides block
        injected into the system prompt this turn. Subtracted from base so L1
        is proactively sized rather than shrunk reactively by the overflow guard.
        After Task 0 (cap=200w), max subtraction is 200, giving L1 ≥ 250w on
        skill turns — _L1_MINIMUM_BUDGET (150) is unreachable in practice.

    SPEC DIVERGENCE (§5.6.1): v7 §5.6.1 specifies ~300w for L1. The 450/600
    values are a pre-existing architectural deviation pending review. Do not
    adjust these constants here — raise via the §5.6.1 architectural review.

    POC NOTE (§6.5.2): The info_request proxy misses tool-invoked knowledge.
    knowledge_lookup (§6.5.2) can add ~300w of evidence on a turn classified
    as emotional support — that turn is treated as freeflow (L1=600) with no
    knowledge-budget deduction. This is a pre-existing gap; fixing it requires
    routing information not yet available at budget calculation time.
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

Expected: all previously passing tests still pass (the `override_words=0` default means existing callers are unaffected).

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/prompts/composer.py tests/test_prompts_composer.py
git commit -m "feat(composer): add override_words to _compute_l1_budget; floor at 150w"
```

---

## Task 2: Wire override_words and add end-to-end behavioral test

**Files:**
- Modify: `src/sage_poc/prompts/composer.py:347-367` (cultural_overrides block), `composer.py:398` (l1_budget call)
- Modify: `src/sage_poc/skills/conformance.py:54-57` — update note
- Test: `tests/test_prompts_composer.py`

- [ ] **Step 1: Write the three failing tests**

Before writing: confirm `compose_prompt`'s return signature is `tuple[str, str, list[str]]` (line 300 and 532 of `composer.py`) — the `system_str, user_str, layers = compose_prompt(state)` unpacking is correct. Confirm `_make_composer_state` accepts `conversation_history` (line 128 of test file, it's in the base dict). `_make_skill_with_overrides` is defined at line 136.

Append to `tests/test_prompts_composer.py`:

```python
# ---- override_words wired into _compute_l1_budget ----

from sage_poc.prompts import composer as _composer_module
from sage_poc.tokens import count_words


def _skill_with_180w_overrides() -> Skill:
    """Overrides totalling ~180w — within 200w cap, used in wiring tests 1 and 2."""
    entry = (
        "Follow Gulf cultural norms carefully in all responses for this skill. "
        "Maintain face-saving framing and indirect expression patterns throughout."
    )  # ~30w per entry
    return _make_skill_with_overrides(overrides={
        "entry_a": entry,
        "entry_b": entry,
        "entry_c": entry,
        "entry_d": entry,
        "entry_e": entry,
    })


def _skill_with_large_overrides() -> Skill:
    """Returns a skill with a cultural_overrides block of ~445w.

    Deliberately exceeds the Task 0 cap of 200w. Used only in the behavioral
    regression test (test 3), which patches _CULTURAL_OVERRIDE_BUDGET_WORDS to
    allow the block through. Using a large block is the only way to make the
    test discriminate between fixed and unfixed code:

      ~180w override + unfixed L1 (450): total ≈ 302 + 180 + 450 = 932w ≤ 1100
        — overflow never fires regardless of the fix (vacuous pass)
      ~445w override + unfixed L1 (450): total ≈ 302 + 445 + 450 = 1197w > 1100
        — overflow fires → test FAILS on unfixed code (correct discrimination)
      ~445w override + fixed L1 (max(150,450-445)=150): total ≈ 302 + 445 + 150 = 897w
        — no overflow → test PASSES on fixed code

    The 302w for system-sans-overrides is approximate; exact value depends on
    templates and state. Verify the test actually discriminates by temporarily
    removing the override_words kwarg from the _compute_l1_budget call and
    confirming the test fails before restoring it.

    Run this to verify block word count before committing the test:
        python3 -c "
        import re
        entry = '<paste entry_a here>'
        lines = chr(10).join('- ' + entry for _ in range(4))
        block = 'SKILL-SPECIFIC CULTURAL CONTEXT:' + chr(10) + lines
        print(len(re.split(r'\\\\s+', block.strip())), 'words')
        "
    Adjust entry length until block totals 430-460w.
    """
    # 4 identical entries; goal is word count, not semantic variety.
    # Each entry ~108w; 4 entries + header + bullet hyphens ≈ 445w total block.
    entry_a = (
        "Gulf Arab culture places collective wellbeing, family honour (ird), and communal "
        "harmony far above individual preferences or personal rights. When guiding users "
        "through this skill, consistently frame every suggestion in terms of how it "
        "strengthens relationships, maintains dignity, and fulfils social obligations rather "
        "than advancing personal comfort alone. Avoid any framing that implies individual "
        "autonomy supersedes family decisions, community expectations, or religious duty. "
        "Calibrate directness carefully to the user's context: women in Gulf settings may "
        "face different social costs and safety risks than men — acknowledge structural "
        "constraints before offering any technique. Islamic values such as sabr and tawakkul "
        "are therapeutic resources; reference them when relevant and never position them as "
        "in conflict with psychological wellbeing or effective coping."
    )
    return _make_skill_with_overrides(overrides={
        "collective_harmony_a": entry_a,
        "collective_harmony_b": entry_a,
        "collective_harmony_c": entry_a,
        "collective_harmony_d": entry_a,
    })


def test_compose_prompt_passes_override_words_to_l1_budget():
    """compose_prompt must pass the actual injected override word count to _compute_l1_budget."""
    skill = _skill_with_180w_overrides()
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
        f"got kwargs: {kwargs}"
    )


def test_compose_prompt_passes_zero_override_words_when_no_active_skill():
    """When no skill is active, override_words must be 0 (L1 budget not reduced)."""
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
        f"got kwargs: {kwargs}"
    )


def test_compose_prompt_no_overflow_with_large_cultural_override():
    """Behavioral regression guard: proactive L1 budget reduction must prevent the
    overflow-shrink guard from firing when a large cultural override block is injected.

    Patches _CULTURAL_OVERRIDE_BUDGET_WORDS to 500 so the ~445w block passes the cap
    check — this is intentional: mocks bypass the Task 0 clinical cap to test the
    defensive wiring under worst-case load. The confirmed overflow warning string
    (composer.py:529) is "Token budget overflow: L1 history shrunk to %d turns";
    substring "Token budget overflow" is used below.

    Discrimination: fails on unfixed code (total ≈1197w → overflow fires);
    passes on fixed code (total ≈897w → no overflow).
    """
    skill = _skill_with_large_overrides()

    # 12 turns at ~50w each = ~600w total; fills whatever L1 budget is given.
    long_history = [
        {
            "role": "user" if i % 2 == 0 else "assistant",
            "content": (
                "I have been thinking carefully about this situation and I am not sure "
                "what the right approach is given everything that has happened recently. "
                "There are many factors to consider and I want to make the best decision "
                "for myself and for the people around me in my life."
            ),
        }
        for i in range(12)
    ]

    state = _make_composer_state(
        active_skill_id="post_crisis_check_in",
        step_instruction="Guide the user through the next step.",
        conversation_history=long_history,
    )

    warning_calls: list[str] = []

    def _spy(msg, *args, **kwargs):
        warning_calls.append(msg % args if args else msg)

    with (
        patch("sage_poc.prompts.composer._CULTURAL_OVERRIDE_BUDGET_WORDS", 500),
        patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules_mock()),
        patch("sage_poc.prompts.composer.load_skill", return_value=skill),
        patch("sage_poc.prompts.composer._log") as mock_log,
    ):
        mock_log.warning.side_effect = _spy
        system_str, user_str, layers = compose_prompt(state)

    # Overrides must have been injected (cap patch allows the large block through).
    assert "cultural_skill_overrides" in layers, (
        "Override block was not injected; _CULTURAL_OVERRIDE_BUDGET_WORDS patch may not be working."
    )

    # Overflow guard must not fire.
    overflow_fired = any("Token budget overflow" in w for w in warning_calls)
    assert not overflow_fired, (
        "Overflow-shrink guard fired despite proactive budget accounting. "
        f"Warning calls: {warning_calls}"
    )

    # Total must be within budget.
    total = count_words(system_str) + count_words(user_str)
    assert total <= 1100, (
        f"Total prompt {total}w exceeds 1100w budget even with proactive L1 reduction."
    )
```

- [ ] **Step 2: Run — confirm all three fail**

```bash
pytest tests/test_prompts_composer.py -k "passes_override_words or no_overflow_with_large" -v
```

Expected: 3 failures — first two fail because `override_words` isn't passed yet; third fails because the overflow guard fires with the current code. If test 3 does NOT fail (overflow guard does not fire), the `_skill_with_large_overrides` block is too small — increase the entry length and re-verify the block word count.

- [ ] **Step 3: Capture `_override_words` in the cultural_overrides block**

In `src/sage_poc/prompts/composer.py`, replace the cultural_overrides block (lines 347–367):

```python
    # Skill-specific cultural overrides — more specific than global rules; injected after them.
    # _override_words is captured here so _compute_l1_budget can proactively reduce L1 budget,
    # eliminating the need for reactive overflow shrinking on normal skill turns.
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

In `src/sage_poc/prompts/composer.py`, replace (current line ~398):

```python
    l1_budget = _compute_l1_budget(state)
```

with:

```python
    l1_budget = _compute_l1_budget(state, override_words=_override_words)
```

- [ ] **Step 5: Update the conformance note**

In `src/sage_poc/skills/conformance.py`, replace the `skill.cultural_overrides` entry:

```python
    "skill.cultural_overrides": {
        "status": "USED",
        "injected_by": "compose_prompt (system role, SKILL-SPECIFIC CULTURAL CONTEXT block)",
        "note": (
            "All key-value pairs injected into the system prompt after global cultural rules, "
            "within a 200-word budget (clinician-signed). Active on every turn where "
            "active_skill_id is set. The injected word count is passed to _compute_l1_budget "
            "so L1 history is proactively sized — not reactively shrunk — when overrides are used."
        ),
    },
```

- [ ] **Step 6: Run all three new tests — must pass**

```bash
pytest tests/test_prompts_composer.py -k "passes_override_words or no_overflow_with_large" -v
```

Expected: 3 passed.

- [ ] **Step 7: Run full suite for affected areas**

```bash
pytest tests/test_prompts_composer.py tests/test_schema_conformance.py tests/test_cultural_overrides_cross_concern.py -k "not endpoint" -v
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/sage_poc/prompts/composer.py src/sage_poc/skills/conformance.py tests/test_prompts_composer.py
git commit -m "fix(composer): wire cultural_overrides words into L1 budget; reduces reliance on reactive overflow shrink"
```

---

## Architectural Review Items (do not implement in this plan)

### A — L1 budget divergence from §5.6.1 and skill-context stacking

**What:** `_L1_BASE_BUDGET = 450` and `_L1_FLEX_BUDGET = 600` diverge from v7 §5.6.1 (~300w). The "flex loaning" of unused L3/L4 headroom to L1 on freeflow turns is defensible against the 1,100-word total budget but is not in the ratified spec.

Additionally: the 200w cultural override cap sits in the system role alongside L3's ~200w skill-context budget (step instruction, technique, examples). On an active skill turn the combined skill-specific footprint is therefore ~400w — roughly double the §5.6.1 envelope for skill context. 200w is a large improvement over 500w and represents the cap value all 13 compliant skills already operate under, but the stacking relationship with L3 requires architectural sign-off before the cap value is treated as final.

**Action needed:** Confirm whether 450/600 was approved or is an unreviewed implementation choice; and confirm the 200w override cap alongside L3's ~200w is architecturally acceptable or whether the cap needs further reduction (which would require re-authoring some of the currently compliant skills). If unapproved, schedule architectural review before the next capability increment that relies on L1 turn depth. The spec-divergence comment added in Task 1 marks this for the next reader.

### B — Migrate skill cultural_overrides into the Rules Service (prerequisite for turn-relevance filtering)

**What:** The architecturally aligned endpoint is for skill `cultural_overrides` to migrate from JSON schema fields into the Rules Service as clinician-authored, versioned, skill-tagged JSON — same draft→review→publish workflow as global cultural rules. Once in the Rules Service, `output_gate` (§5.5, §6.5.7) can enforce the full set on generated text (the deterministic completeness guarantee), and relevance selection for prompt injection becomes safe because the gate acts as backstop.

**Why not now:** Turn-relevance filtering without a gate backstop is unsafe. A user who never says "family" can still receive a response that needs family-context guidance. With the gate re-evaluating all skill overrides on the output (as it does for global rules), input-keyword filtering in the prompt becomes safe and the L1 budget problem disappears rather than being managed.

**Action needed:** Raise as a Full Build backlog item. Pair with the §6.5.2 knowledge_lookup tool path review.

---

## Self-Review

**1. Spec coverage:**
- Cap lowered to 200w: ✓ Task 0
- Seven over-budget skills re-authored: clinical CMS track (not in this plan)
- Test catches future violations: ✓ Task 0 Step 1
- `_compute_l1_budget` updated: ✓ Task 1
- `_L1_MINIMUM_BUDGET = 150` floor: ✓ Task 1
- Spec-divergence §5.6.1 comment: ✓ Task 1 Step 3
- §6.5.2 POC note: ✓ Task 1 Step 3
- `compose_prompt` wires `_override_words`: ✓ Task 2
- End-to-end behavioral test (total ≤1100, no overflow warning, ~445w override via cap patch): ✓ Task 2 Step 1
- Conformance note updated: ✓ Task 2 Step 5
- Commit message reads "reduces reliance on": ✓ Task 2 Step 8
- Turn-relevance filtering: correctly absent (deferred to Review Item B)
- Stale active_skill_id: confirmed closed, documented in background section
- Architectural review items documented: ✓ both A and B

**2. Placeholder scan:** None found.

**3. Type consistency:**
- `_compute_l1_budget(state: SageState, override_words: int = 0) -> int` — consistent across Task 1 definition and Task 2 call site.
- `_override_words` is `int` throughout — initialized to `0`, assigned `count_words(...)` which returns `int`.
- `_CAP_WORDS = 200` in Task 0 test matches `_CULTURAL_OVERRIDE_BUDGET_WORDS = 200` in production.
- `_skill_with_180w_overrides()` helper is defined once in Task 2 tests and used only there.
