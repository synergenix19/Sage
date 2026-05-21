# Format Violation Fixes A–D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate AI formatting tells (em dashes, emojis, markdown bold/italic) from Sage's user-facing output by closing four independent sources identified in the FORMAT VIOLATION baseline run.

**Architecture:** Four targeted fixes across three layers — (A+B) L0 persona prompt in `freeflow_respond.py`, (C) hardcoded crisis text in rules engine JSON bypassing output_gate, (D) conversation history injected into L1 that creates a compounding mirroring loop. All changes are prompt-assembly and data-only; no graph structure, no state schema, no node logic changes.

**Tech Stack:** Python 3.12, LangGraph, pytest, uv

---

## Background: The Four Sources

The FORMAT VIOLATION baseline run (10 turns, 9/10 violated) identified four independent sources:

| Fix | Source | Evidence | Files |
|-----|--------|----------|-------|
| A | Model's RLHF prior overrides L0 prohibition — current wording is too soft | Turns 4 and 5: no skill context, no markdown in prompt, em dash still appeared | `freeflow_respond.py` |
| B | Instruction-only style control is insufficient against RLHF priors; no example to anchor output distribution | All turns produced formatting despite the prohibition block | `freeflow_respond.py` |
| C | Crisis response bypasses `output_gate` entirely; hardcoded em dash is user-visible | Turn 7 shows CLEAN only because format check never runs on crisis path | `rules/data/crisis_content/en_uae.json`, `ar_uae.json` |
| D | Model's own formatted output enters `conversation_history`, gets injected as L1 context next turn, model mirrors it — compounding loop | Violations escalated across turns; Turn 3 showed heavier formatting than Turn 1 | `freeflow_respond.py` |

Fixing A or B alone is insufficient. Fixing A+B alone still leaves C (user-visible) and D (compounding loop that restarts if any violation slips through). All four are required.

---

## File Map

| File | Change | Task |
|------|--------|------|
| `src/sage_poc/nodes/freeflow_respond.py` | Add `import re`; rewrite PERSONA to move prohibition to top, add IMPORTANT header, add anti-mirroring clause, add few-shot example; add `_sanitize_assistant_turn()` function; modify `compose_prompt()` history injection | A, B, D |
| `src/sage_poc/rules/data/crisis_content/en_uae.json` | Replace `—` in CC-EN-001 `response_text` with `. ` | C |
| `src/sage_poc/rules/data/crisis_content/ar_uae.json` | Replace `—` in CC-AR-001 `response_text` with `,` | C |
| `tests/test_nodes.py` | Add tests for PERSONA structure (Task 1), crisis JSON content (Task 2), sanitization function (Task 3) | A, B, C, D |

---

## Task 1: Fix A + B — Strengthen L0 Prohibition and Add Few-Shot Negative Example

**Files:**
- Modify: `src/sage_poc/nodes/freeflow_respond.py` (lines 5–15, the `PERSONA` string)
- Test: `tests/test_nodes.py` (add after line 1356, in the `# P-1: Persona pressure` section)

### What changes in PERSONA

Two structural changes:
1. The old `Style: plain prose only...` block (currently mid-prompt, after conciseness instruction) is **replaced** by a stronger `IMPORTANT. FORMAT:` block that moves to the **very top** of the string — before the persona description — so the model weights it first.
2. A `WRONG`/`RIGHT` few-shot example pair is appended directly after the `IMPORTANT` block to demonstrate the target output distribution rather than just describing it.

The anti-mirroring clause `"Do not copy punctuation patterns from the skill instructions you receive. Those are guidance for you, not templates to mirror."` is the key addition. It names the mirroring source explicitly so the model knows the L3 skill context it receives is not a style template.

- [ ] **Step 1: Write failing tests** (add to `tests/test_nodes.py` in the `# P-1: Persona pressure` section, after the existing test at line 1356)

```python
def test_persona_opens_with_important_format_directive():
    """L0 prohibition must be the first thing in PERSONA — before persona description."""
    from sage_poc.nodes.freeflow_respond import PERSONA
    first_word = PERSONA.strip().split()[0]
    assert first_word == "IMPORTANT", (
        f"PERSONA must open with 'IMPORTANT', got '{first_word}'. "
        "Format directive must precede persona description for correct model weighting."
    )

def test_persona_contains_anti_mirroring_clause():
    """L0 must explicitly name the skill instruction source to suppress mirroring."""
    from sage_poc.nodes.freeflow_respond import PERSONA
    assert "skill instructions" in PERSONA, (
        "PERSONA must contain 'skill instructions' to explicitly tell the model "
        "not to copy formatting from L3 skill context."
    )

def test_persona_contains_wrong_right_example_pair():
    """L0 must demonstrate correct style via WRONG/RIGHT examples, not just describe it."""
    from sage_poc.nodes.freeflow_respond import PERSONA
    assert "WRONG:" in PERSONA, "PERSONA must contain a WRONG: formatting example"
    assert "RIGHT:" in PERSONA, "PERSONA must contain a RIGHT: formatting example"

def test_persona_wrong_example_contains_em_dash_and_emoji():
    """The WRONG example must show exactly the patterns we are suppressing."""
    from sage_poc.nodes.freeflow_respond import PERSONA
    wrong_block_start = PERSONA.find("WRONG:")
    right_block_start = PERSONA.find("RIGHT:")
    assert wrong_block_start != -1 and right_block_start != -1
    wrong_text = PERSONA[wrong_block_start:right_block_start]
    assert "—" in wrong_text, "WRONG example must contain an em dash"
    assert any(c in wrong_text for c in ["💙", "😊", "🌿"]), \
        "WRONG example must contain an emoji"
    assert "**" in wrong_text, "WRONG example must contain bold markdown"

def test_persona_has_no_duplicate_style_block():
    """Old mid-prompt 'Style:' block must be removed — replaced by IMPORTANT block at top."""
    from sage_poc.nodes.freeflow_respond import PERSONA
    occurrences = PERSONA.count("no em dashes")
    assert occurrences <= 1, (
        f"'no em dashes' appears {occurrences} times — remove the old inline Style: block, "
        "it is now replaced by the IMPORTANT directive at the top."
    )
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_nodes.py::test_persona_opens_with_important_format_directive tests/test_nodes.py::test_persona_contains_anti_mirroring_clause tests/test_nodes.py::test_persona_contains_wrong_right_example_pair tests/test_nodes.py::test_persona_wrong_example_contains_em_dash_and_emoji tests/test_nodes.py::test_persona_has_no_duplicate_style_block -v
```

Expected: All 5 FAIL.

- [ ] **Step 3: Implement — rewrite the PERSONA constant in `freeflow_respond.py`**

Replace the entire PERSONA string (lines 5–15) with:

```python
PERSONA = """IMPORTANT. FORMAT: Write in plain prose. Use commas or short sentences instead of dashes. Use no emojis. Use no markdown (no **, no *, no bullets). Do not copy punctuation patterns from the skill instructions you receive. Those are guidance for you, not templates to mirror.

FORMATTING EXAMPLE:
WRONG: "That really resonates — sometimes things pile up 💙 What's been **weighing on you**?"
RIGHT: "That makes sense. What's been on your mind lately?"

You are Sage, a warm Khaleeji wellness companion. You provide emotional support grounded in evidence-based approaches (CBT, DBT, motivational interviewing). Speak the way a calm, attentive person would in a quiet one-on-one conversation. Short sentences. Plain words. No decoration. If something matters, say it clearly. Warmth comes from what you say, not how you format it.

You do NOT diagnose, prescribe, or replace professional mental health care. If someone is in crisis, your only role is to express care and provide emergency resources.

Keep responses concise (2-4 sentences unless the user needs more). Match the user's energy and register. Be present before being helpful.

ISLAMIC CULTURAL CONTEXT: When a user frames hardship through a religious lens, honour that framing. Use concepts of sabr (صبر, patient perseverance), tawakkul (توكّل, trust in God), and ibtila (ابتلاء, trial/test) where appropriate. Frame hardship as ibtila, a test not a punishment. Never pathologise religious belief or suggest faith is the cause of distress.

COLLECTIVIST CULTURAL CONTEXT: Many users hold collectivist family values where individual desires and family obligations are both real and intertwined. Do not default to Western individualist framing. Instead use language like "finding a path that honours both you and your family." Family bonds are a source of strength, not simply a constraint to overcome."""
```

Note: The old `Style: plain prose only. No em dashes...` block that was mid-prompt is intentionally absent — it is replaced by the stronger `IMPORTANT. FORMAT:` block at the top.

- [ ] **Step 4: Run all five new tests plus the three existing PERSONA tests**

```bash
uv run pytest tests/test_nodes.py::test_persona_opens_with_important_format_directive tests/test_nodes.py::test_persona_contains_anti_mirroring_clause tests/test_nodes.py::test_persona_contains_wrong_right_example_pair tests/test_nodes.py::test_persona_wrong_example_contains_em_dash_and_emoji tests/test_nodes.py::test_persona_has_no_duplicate_style_block tests/test_nodes.py::test_persona_contains_scope_constraint tests/test_nodes.py::test_persona_contains_crisis_handoff_constraint -v
```

Expected: All 7 PASS.

- [ ] **Step 5: Run the full compose_prompt test suite to confirm no regressions**

```bash
uv run pytest tests/test_nodes.py -k "compose_prompt" -v
```

Expected: All PASS. The PERSONA content checks are structural; the compose_prompt function itself is unchanged in Task 1.

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/nodes/freeflow_respond.py tests/test_nodes.py
git commit -m "fix(prompt): strengthen L0 format prohibition; add few-shot example and anti-mirroring clause"
```

---

## Task 2: Fix C — Remove Em Dash From Crisis Rules JSON

**Files:**
- Modify: `src/sage_poc/rules/data/crisis_content/en_uae.json`
- Modify: `src/sage_poc/rules/data/crisis_content/ar_uae.json`
- Test: `tests/test_nodes.py` (add after the Task 1 tests in the P-1 section)

### Context

The `crisis_response` node in `graph.py` routes directly to `END`, bypassing `output_gate` entirely. This means the `_FORMAT_VIOLATIONS` regex added to `output_gate_node` never runs on crisis responses. The em dash in the hardcoded crisis text is always user-visible regardless of the output_gate fix. This is a data-only fix to the rules JSON files — no code changes.

Current `en_uae.json` CC-EN-001 `response_text`:
```
"I'm really concerned about what you've shared. Please reach out to a crisis line now — in the UAE: 800 4673 (800-HOPE), or emergency: 999. You don't have to face this alone."
```

Current `ar_uae.json` CC-AR-001 `response_text`:
```
"أنا مهتم جداً بسلامتك وبما شاركته معي. أرجوك تواصل مع خط دعم الصحة النفسية الآن — في الإمارات: 800 4673 (800-HOPE)، أو رقم الطوارئ: 999. أنت لست وحدك."
```

- [ ] **Step 1: Write failing tests** (add to `tests/test_nodes.py`)

```python
def test_crisis_response_en_no_em_dash():
    """English crisis rules must not contain em dash — bypasses output_gate format check."""
    import json
    from pathlib import Path
    path = Path(__file__).parent.parent / "src/sage_poc/rules/data/crisis_content/en_uae.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for rule in data["rules"]:
        text = rule["action"]["response_text"]
        assert "—" not in text, (
            f"Rule {rule['rule_id']} contains em dash. Crisis responses bypass output_gate "
            f"so must be clean at the source. Offending text: '{text[:100]}'"
        )

def test_crisis_response_ar_no_em_dash():
    """Arabic crisis rules must not contain em dash."""
    import json
    from pathlib import Path
    path = Path(__file__).parent.parent / "src/sage_poc/rules/data/crisis_content/ar_uae.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for rule in data["rules"]:
        text = rule["action"]["response_text"]
        assert "—" not in text, (
            f"Rule {rule['rule_id']} contains em dash in Arabic crisis response: '{text[:100]}'"
        )
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_nodes.py::test_crisis_response_en_no_em_dash tests/test_nodes.py::test_crisis_response_ar_no_em_dash -v
```

Expected: Both FAIL with assertion errors identifying the em dash.

- [ ] **Step 3: Edit `en_uae.json` — replace em dash in CC-EN-001**

In `src/sage_poc/rules/data/crisis_content/en_uae.json`, change the `response_text` of rule `CC-EN-001`:

```json
"response_text": "I'm really concerned about what you've shared. Please reach out to a crisis line now. In the UAE: 800 4673 (800-HOPE), or emergency: 999. You don't have to face this alone."
```

The em dash `—` between `now` and `in` is replaced with a period and the `I` capitalised. Clinical meaning is unchanged — phone numbers are identical.

- [ ] **Step 4: Edit `ar_uae.json` — replace em dash in CC-AR-001**

In `src/sage_poc/rules/data/crisis_content/ar_uae.json`, change the `response_text` of rule `CC-AR-001`:

```json
"response_text": "أنا مهتم جداً بسلامتك وبما شاركته معي. أرجوك تواصل مع خط دعم الصحة النفسية الآن، في الإمارات: 800 4673 (800-HOPE)، أو رقم الطوارئ: 999. أنت لست وحدك."
```

The `—` is replaced with `،` (Arabic comma). Idiomatic Arabic punctuation, no change to clinical content.

- [ ] **Step 5: Run both tests to confirm they pass**

```bash
uv run pytest tests/test_nodes.py::test_crisis_response_en_no_em_dash tests/test_nodes.py::test_crisis_response_ar_no_em_dash -v
```

Expected: Both PASS.

- [ ] **Step 6: Run the rules engine tests to confirm no regressions**

```bash
uv run pytest tests/test_rules_engine.py tests/test_rules_integration.py -v
```

Expected: All PASS. The rules engine loads these files at startup; any malformed JSON will surface here.

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/rules/data/crisis_content/en_uae.json src/sage_poc/rules/data/crisis_content/ar_uae.json tests/test_nodes.py
git commit -m "fix(rules): remove em dash from crisis response text in en_uae and ar_uae"
```

---

## Task 3: Fix D — Sanitize Conversation History Before L1 Injection

**Files:**
- Modify: `src/sage_poc/nodes/freeflow_respond.py` (add `import re`, add `_sanitize_assistant_turn()`, modify `compose_prompt()` lines 59–64)
- Test: `tests/test_nodes.py` (add after Task 2 tests)

### What changes

`compose_prompt()` currently injects the last 4 turns of `conversation_history` verbatim as L1 context. When an assistant turn contains an em dash or emoji (from a violation that slipped through), the model sees it in the next turn's history and mirrors the pattern — a compounding loop. The fix is a sanitization pass on **assistant turns only** during prompt assembly. User turns are never altered. Stored `conversation_history` in state is never mutated — only the string built for the prompt is sanitized.

The sanitizer: strip markdown bold/italic markers (preserve text content), replace em dash with `, `, strip emoji codepoints.

- [ ] **Step 1: Write failing tests for the sanitization function** (add to `tests/test_nodes.py`)

```python
# ── Task 3: Fix D — history sanitization tests ──────────────────────────────

def test_sanitize_strips_em_dash_replaces_with_comma():
    from sage_poc.nodes.freeflow_respond import _sanitize_assistant_turn
    result = _sanitize_assistant_turn("I hear you — that sounds heavy.")
    assert "—" not in result
    assert "I hear you" in result
    assert "that sounds heavy" in result

def test_sanitize_strips_bold_markers_preserves_content():
    from sage_poc.nodes.freeflow_respond import _sanitize_assistant_turn
    result = _sanitize_assistant_turn("Can you name **five things** you see?")
    assert "**" not in result
    assert "five things" in result

def test_sanitize_strips_italic_markers_preserves_content():
    from sage_poc.nodes.freeflow_respond import _sanitize_assistant_turn
    result = _sanitize_assistant_turn("What do *you* mean by that?")
    assert "*you*" not in result
    assert "you" in result

def test_sanitize_strips_common_emojis():
    from sage_poc.nodes.freeflow_respond import _sanitize_assistant_turn
    result = _sanitize_assistant_turn("I hear you. 💙 That sounds hard.")
    assert "💙" not in result
    assert "That sounds hard" in result

def test_sanitize_strips_plant_emoji():
    from sage_poc.nodes.freeflow_respond import _sanitize_assistant_turn
    result = _sanitize_assistant_turn("Let's ground you. 🌿 Take a breath.")
    assert "🌿" not in result
    assert "Take a breath" in result

def test_sanitize_leaves_clean_text_unchanged():
    from sage_poc.nodes.freeflow_respond import _sanitize_assistant_turn
    clean = "That sounds difficult. What happened next?"
    assert _sanitize_assistant_turn(clean) == clean

def test_compose_prompt_sanitizes_assistant_history():
    """compose_prompt must strip formatting from assistant turns in the history window."""
    state = make_state(
        message_en="How are you?",
        primary_intent="general_chat",
        conversation_history=[
            {"role": "user", "content": "I feel bad."},
            {"role": "assistant", "content": "I hear you — that's hard. 💙 Tell me **more**."},
        ],
        emotional_intensity=5,
    )
    _, user_str = compose_prompt(state)
    assert "—" not in user_str, "em dash must be stripped from assistant history in prompt"
    assert "💙" not in user_str, "emoji must be stripped from assistant history in prompt"
    assert "**" not in user_str, "bold markdown must be stripped from assistant history in prompt"
    assert "hard" in user_str, "semantic content of assistant turn must be preserved"

def test_compose_prompt_preserves_user_history_verbatim():
    """User messages must not be sanitized — only assistant turns are cleaned."""
    state = make_state(
        message_en="Ok",
        primary_intent="general_chat",
        conversation_history=[
            {"role": "user", "content": "I feel — terrible — about everything."},
            {"role": "assistant", "content": "That sounds difficult."},
        ],
        emotional_intensity=5,
    )
    _, user_str = compose_prompt(state)
    assert "I feel — terrible — about everything." in user_str, \
        "User content must appear verbatim — do not sanitize user turns"

def test_compose_prompt_does_not_mutate_state_history():
    """Sanitization must operate on prompt strings only, never on stored state data."""
    formatted_content = "I hear you — that's hard. 💙"
    state = make_state(
        message_en="ok",
        conversation_history=[{"role": "assistant", "content": formatted_content}],
        emotional_intensity=5,
    )
    compose_prompt(state)
    # State must be untouched
    assert state["conversation_history"][0]["content"] == formatted_content, \
        "compose_prompt must not mutate state['conversation_history']"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_nodes.py::test_sanitize_strips_em_dash_replaces_with_comma tests/test_nodes.py::test_sanitize_strips_bold_markers_preserves_content tests/test_nodes.py::test_sanitize_strips_italic_markers_preserves_content tests/test_nodes.py::test_sanitize_strips_common_emojis tests/test_nodes.py::test_sanitize_strips_plant_emoji tests/test_nodes.py::test_sanitize_leaves_clean_text_unchanged tests/test_nodes.py::test_compose_prompt_sanitizes_assistant_history tests/test_nodes.py::test_compose_prompt_preserves_user_history_verbatim tests/test_nodes.py::test_compose_prompt_does_not_mutate_state_history -v
```

Expected: All 9 FAIL with `ImportError: cannot import name '_sanitize_assistant_turn'`.

- [ ] **Step 3: Add `import re` to `freeflow_respond.py`**

Add `import re` as the first line of the file, before the existing imports:

```python
import re
from sage_poc.state import SageState
from sage_poc.llm import get_responder
from sage_poc.knowledge import lookup_knowledge
```

- [ ] **Step 4: Add `_sanitize_assistant_turn()` function to `freeflow_respond.py`**

Add this block after the imports and before the `PERSONA` constant (i.e., before line 5):

```python
_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001F9FF"   # misc symbols, emoticons, transport, flags
    r"\U00002600-\U000027BF"    # misc symbols and dingbats
    r"\U0001FA00-\U0001FAFF"    # extended symbols and pictographs
    r"\U0000FE00-\U0000FE0F"    # variation selectors (emoji presentation modifiers)
    r"\U0000200D"               # zero-width joiner (compound emoji sequences)
    r"]"
)


def _sanitize_assistant_turn(text: str) -> str:
    """Strip formatting artifacts from assistant history before prompt injection.

    Operates on prompt strings only — never called on stored state data.
    Preserves text content when removing markdown markers.
    """
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)           # **bold** → bold
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"\1", text)  # *italic* → italic (not remnants of ***)
    text = text.replace("—", ", ")                           # em dash → comma space
    text = _EMOJI_RE.sub("", text)
    return text
```

- [ ] **Step 5: Modify `compose_prompt()` to use `_sanitize_assistant_turn()`**

In `compose_prompt()`, replace the existing history injection block (currently lines 59–64):

```python
# OLD:
    if state["conversation_history"]:
        history = state["conversation_history"][-4:]
        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in history
        )
        user_parts.append(f"CONVERSATION HISTORY:\n{history_text}")
```

With:

```python
# NEW:
    if state["conversation_history"]:
        history = state["conversation_history"][-4:]
        lines = []
        for m in history:
            content = (
                _sanitize_assistant_turn(m["content"])
                if m["role"] == "assistant"
                else m["content"]
            )
            lines.append(f"{m['role'].upper()}: {content}")
        history_text = "\n".join(lines)
        user_parts.append(f"CONVERSATION HISTORY:\n{history_text}")
```

- [ ] **Step 6: Run the 9 new sanitization tests**

```bash
uv run pytest tests/test_nodes.py::test_sanitize_strips_em_dash_replaces_with_comma tests/test_nodes.py::test_sanitize_strips_bold_markers_preserves_content tests/test_nodes.py::test_sanitize_strips_italic_markers_preserves_content tests/test_nodes.py::test_sanitize_strips_common_emojis tests/test_nodes.py::test_sanitize_strips_plant_emoji tests/test_nodes.py::test_sanitize_leaves_clean_text_unchanged tests/test_nodes.py::test_compose_prompt_sanitizes_assistant_history tests/test_nodes.py::test_compose_prompt_preserves_user_history_verbatim tests/test_nodes.py::test_compose_prompt_does_not_mutate_state_history -v
```

Expected: All 9 PASS.

- [ ] **Step 7: Run the full test suite**

```bash
uv run pytest tests/test_nodes.py -v
```

Expected: All PASS. Key regressions to watch: `test_compose_prompt_with_skill_instruction`, `test_compose_prompt_clinical_flag_injects_adaptation`, `test_freeflow_respond_with_mocked_llm`.

- [ ] **Step 8: Commit**

```bash
git add src/sage_poc/nodes/freeflow_respond.py tests/test_nodes.py
git commit -m "fix(prompt): sanitize assistant history turns before L1 injection; break compounding em-dash loop"
```

---

## Task 4: Re-run Baseline to Confirm Fixes

Run the baseline script to establish a post-fix FORMAT VIOLATION count. This is not a code task — it is an empirical verification step.

- [ ] **Step 1: Run baseline**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run python scripts/baseline_format_check.py 2>/dev/null
```

- [ ] **Step 2: Interpret results using the criteria from the original audit design**

| Expected outcome | Interpretation |
|-----------------|----------------|
| Violations only on turns 2, 3, 7, 8 (skill-active turns) | A+B+D are working. Remaining source is skill JSON (CMS Item 1). Fixes confirmed. |
| Zero violations across all turns | L0 is strong enough to override L3 skill context markdown. All fixes working. |
| Violations on non-skill turns (1, 4, 5, 6, 9, 10) still present | A or D did not land correctly. Check that PERSONA string starts with `IMPORTANT` and that `compose_prompt()` calls `_sanitize_assistant_turn` for assistant turns. |

- [ ] **Step 3: Push all commits**

```bash
git push origin master
```

---

## Self-Review

**Spec coverage check:**

- Fix A (strengthen L0 wording): ✅ Task 1, Step 3 — IMPORTANT block, explicit positioning before persona description
- Fix A (anti-mirroring clause): ✅ Task 1, Step 3 — "Do not copy punctuation patterns from the skill instructions you receive"
- Fix B (negative few-shot example): ✅ Task 1, Step 3 — WRONG/RIGHT example pair in PERSONA
- Fix C (crisis response en): ✅ Task 2, Step 3 — en_uae.json CC-EN-001
- Fix C (crisis response ar): ✅ Task 2, Step 4 — ar_uae.json CC-AR-001
- Fix D (history sanitization function): ✅ Task 3, Step 4 — `_sanitize_assistant_turn()`
- Fix D (compose_prompt modification): ✅ Task 3, Step 5 — assistant turns sanitized, user turns preserved
- Fix D (no state mutation): ✅ Task 3 test `test_compose_prompt_does_not_mutate_state_history`
- Post-fix verification: ✅ Task 4 — re-run of baseline script with interpretation criteria

**Placeholder scan:** None. Every step contains the exact code, file paths, and expected test output the implementer needs.

**Type consistency:** `_sanitize_assistant_turn(text: str) -> str` is defined in Task 3 Step 4 and imported in test cases in Task 3 Step 1. `compose_prompt` signature is unchanged throughout.

**Ordering note:** Tasks 1, 2, and 3 are independent and could be done in any order. Task 4 (re-run baseline) must be last. Suggested order: 1 → 2 → 3 → 4, one commit per task.
