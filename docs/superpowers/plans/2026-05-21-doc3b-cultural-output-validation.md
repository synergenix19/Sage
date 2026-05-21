# Doc 3b: Cultural Output Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement post-generation cultural output validation (v7 §5.5 Node 8 rows) — a new `cultural_output` rule category that checks the LLM-generated response text for cultural violations after generation and logs them to the audit trail.

**Architecture:** Add a new `cultural_output` rule category following the same pattern as `safety`, `cultural`, and `prompt_injection`. This requires: (1) a new `CulturalOutputRule` Pydantic schema, (2) loader registration, (3) a new `_eval_cultural_output` eval function + dispatch entry, and (4) wiring into `output_gate_node`. Output rules are **audit-only** for the POC — they log violations but do not block or regenerate. Four rule files implement Items 3–6 from the v7 §5.5 gap analysis.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, `output_gate.py` (Node 8), existing Rules Service engine pattern.

---

## Gap Analysis Reference

| # | Item | Mechanism | Doc 3b Task |
|---|------|-----------|------------|
| 3 | Religious language mirroring check | Post-gen allowlist_required | Task 3: CUO-IS-001 |
| 4 | Family not dismissed check | Post-gen blocklist | Task 4: CUO-FA-001 |
| 5 | Substance language UAE-appropriate | Post-gen blocklist | Task 5: CUO-SU-001 |
| 6 | General cultural inappropriateness | Post-gen blocklist | Task 5: CUO-GC-001 |

Pre-generation rules (Items 8–13) → Doc 3a.  
State-dependent design decisions (Items 7, 13 full) → Doc 3c.

---

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `src/sage_poc/rules/schemas.py` | Modify | Add `CulturalOutputRule` class |
| `src/sage_poc/rules/loader.py` | Modify | Register `"cultural_output": CulturalOutputRule` in `_RULE_MODELS` |
| `src/sage_poc/rules/engine.py` | Modify | Add `_eval_cultural_output` + dispatch entry |
| `src/sage_poc/nodes/output_gate.py` | Modify | Call `rules_engine.evaluate("cultural_output", ...)` after selecting `response_en` |
| `src/sage_poc/rules/data/cultural_output/religious_mirroring.json` | Create | CUO-IS-001: Islamic vocabulary mirroring check |
| `src/sage_poc/rules/data/cultural_output/family_framing.json` | Create | CUO-FA-001: family-not-dismissed blocklist |
| `src/sage_poc/rules/data/cultural_output/substance_language.json` | Create | CUO-SU-001: UAE-appropriate substance language |
| `src/sage_poc/rules/data/cultural_output/general_cultural.json` | Create | CUO-GC-001: general cultural appropriateness |
| `tests/test_cultural_output.py` | Create | All Doc 3b tests |

---

## CulturalOutputRule Schema Design

Two check types, three condition types:

```
check_type:
  "blocklist"          — violation if ANY pattern IS found in response_text
  "allowlist_required" — violation if NO pattern is found in response_text (when condition met)

condition_type:
  "always"             — check fires unconditionally
  "keyword_in_message" — check fires only when condition_keywords appear in message_en
  "flag_present"       — check fires only when condition_value clinical flag is active
```

Engine context keys: `response_text` (generated English response), `message_en` (user message), `clinical_flags` (list).

---

## Task 1: CulturalOutputRule Schema + Loader + Engine

**Files:**
- Modify: `src/sage_poc/rules/schemas.py`
- Modify: `src/sage_poc/rules/loader.py`
- Modify: `src/sage_poc/rules/engine.py`
- Create: `tests/test_cultural_output.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cultural_output.py`:

```python
# tests/test_cultural_output.py
import pytest
from sage_poc.rules.loader import reload_all
from sage_poc.rules import engine as rules_engine
from sage_poc.rules.schemas import CulturalOutputRule


@pytest.fixture(autouse=True)
def fresh_rules():
    reload_all()
    yield
    reload_all()


def test_cultural_output_rule_schema_validates():
    """CulturalOutputRule must validate a well-formed rule dict."""
    rule = CulturalOutputRule.model_validate({
        "rule_id": "TEST-CUO-001",
        "category": "cultural_output",
        "effective_date": "2026-05-21",
        "check_type": "blocklist",
        "condition_type": "always",
        "patterns": ["bad phrase"],
        "action": {"type": "audit_warn", "severity": "medium", "message": "test"},
    })
    assert rule.rule_id == "TEST-CUO-001"
    assert rule.check_type == "blocklist"
    assert rule.condition_type == "always"


def test_cultural_output_rule_schema_allowlist_required():
    """CulturalOutputRule must accept allowlist_required check_type."""
    rule = CulturalOutputRule.model_validate({
        "rule_id": "TEST-CUO-002",
        "category": "cultural_output",
        "effective_date": "2026-05-21",
        "check_type": "allowlist_required",
        "condition_type": "keyword_in_message",
        "condition_keywords": ["allah"],
        "patterns": ["sabr", "allah"],
        "action": {"type": "audit_warn", "severity": "medium", "message": "test"},
    })
    assert rule.check_type == "allowlist_required"
    assert rule.condition_keywords == ["allah"]


def test_evaluate_cultural_output_unknown_category_raises():
    """evaluate() with unknown category must raise ValueError."""
    with pytest.raises(ValueError, match="Unknown rule category"):
        rules_engine.evaluate("nonexistent_category", {})


def test_evaluate_cultural_output_empty_rules_returns_empty_result():
    """evaluate('cultural_output', ...) with no rule files returns empty EvalResult."""
    # cultural_output dir exists but may be empty before Task 3 files are added
    # If dir doesn't exist yet, loader returns [] — result has no fired rules
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "you should prioritize yourself",
        "message_en": "I feel pressured by my family",
        "clinical_flags": [],
    })
    # Result is valid EvalResult — may have 0 or more fired rules depending on state
    assert hasattr(result, "fired")
    assert hasattr(result, "actions")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
python -m pytest tests/test_cultural_output.py -v
```
Expected: ALL fail — `CulturalOutputRule` doesn't exist yet.

- [ ] **Step 3: Add CulturalOutputRule to schemas.py**

In `src/sage_poc/rules/schemas.py`, add after the `PromptInjectionRule` class (after line 66):

```python
class CulturalOutputRule(BaseModel):
    rule_id: str
    version: str = "1.0.0"
    category: Literal["cultural_output"]
    authored_by: str = "sage_clinics"
    approved_by: str | None = None
    effective_date: str
    active: bool = True
    description: str = ""
    check_type: Literal["blocklist", "allowlist_required"]
    condition_type: Literal["always", "keyword_in_message", "flag_present"]
    condition_keywords: list[str] = []
    condition_value: str | None = None
    patterns: list[str]
    action: dict
```

- [ ] **Step 4: Register CulturalOutputRule in loader.py**

In `src/sage_poc/rules/loader.py`, update the import and `_RULE_MODELS`:

```python
from sage_poc.rules.schemas import (
    SafetyRule, CrisisContentRule, CulturalRule, PromptInjectionRule, CulturalOutputRule,
)

_RULE_MODELS: dict[str, type] = {
    "safety": SafetyRule,
    "crisis_content": CrisisContentRule,
    "cultural": CulturalRule,
    "prompt_injection": PromptInjectionRule,
    "cultural_output": CulturalOutputRule,
}
```

- [ ] **Step 5: Add _eval_cultural_output to engine.py**

In `src/sage_poc/rules/engine.py`, update the import:

```python
from sage_poc.rules.schemas import (
    SafetyRule, CrisisContentRule, CulturalRule, PromptInjectionRule, CulturalOutputRule,
    EvalResult, FiredRule,
)
```

Add the `_eval_cultural_output` function before `_EVAL_DISPATCH`:

```python
def _eval_cultural_output(rules: list[CulturalOutputRule], context: dict) -> EvalResult:
    """
    Evaluate post-generation cultural output rules.

    Fires when a rule's condition is met AND the response violates the check type:
      blocklist          — any pattern found in response → violation
      allowlist_required — no pattern found in response → violation

    context keys:
      response_text (str)          — generated English response text
      message_en (str)             — original user message in English
      clinical_flags (list[str])   — active clinical flags from state
    """
    response_text = normalize_text(context.get("response_text", ""))
    message_en = normalize_text(context.get("message_en", ""))
    clinical_flags: list[str] = context.get("clinical_flags", [])

    result = EvalResult()
    for rule in rules:
        condition_met = False
        if rule.condition_type == "always":
            condition_met = True
        elif rule.condition_type == "keyword_in_message":
            condition_met = any(kw.lower() in message_en for kw in rule.condition_keywords)
        elif rule.condition_type == "flag_present":
            condition_met = rule.condition_value in clinical_flags

        if not condition_met:
            continue

        violated = False
        if rule.check_type == "blocklist":
            violated = any(p.lower() in response_text for p in rule.patterns)
        elif rule.check_type == "allowlist_required":
            violated = not any(p.lower() in response_text for p in rule.patterns)

        if violated:
            result.fired.append(FiredRule(
                rule_id=rule.rule_id,
                version=rule.version,
                action=rule.action,
            ))

    return result
```

Update `_EVAL_DISPATCH` to include the new category:

```python
_EVAL_DISPATCH = {
    "safety": _eval_safety,
    "crisis_content": _eval_crisis_content,
    "cultural": _eval_cultural,
    "prompt_injection": _eval_prompt_injection,
    "cultural_output": _eval_cultural_output,
}
```

- [ ] **Step 6: Create the data directory**

```bash
mkdir -p src/sage_poc/rules/data/cultural_output
```

- [ ] **Step 7: Run tests**

```bash
python -m pytest tests/test_cultural_output.py -v
```
Expected: ALL four schema/loader/engine tests pass.

- [ ] **Step 8: Commit**

```bash
git add src/sage_poc/rules/schemas.py src/sage_poc/rules/loader.py src/sage_poc/rules/engine.py tests/test_cultural_output.py
git commit -m "feat(rules): add cultural_output rule category — schema, loader, engine"
```

---

## Task 2: output_gate Wiring

**Files:**
- Modify: `src/sage_poc/nodes/output_gate.py`
- Test: `tests/test_cultural_output.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cultural_output.py`:

```python
def test_output_gate_calls_cultural_output_evaluate(monkeypatch):
    """output_gate_node must call rules_engine.evaluate('cultural_output', ...) for standard path."""
    from sage_poc.nodes.output_gate import output_gate_node
    from sage_poc.rules import engine as rules_engine

    calls = []
    original_evaluate = rules_engine.evaluate

    def mock_evaluate(category, context):
        calls.append((category, context))
        return original_evaluate(category, context)

    monkeypatch.setattr(rules_engine, "evaluate", mock_evaluate)

    state = {
        "gate_path": None,
        "detected_language": "en",
        "path": [],
        "response_en": "That makes sense. How are you feeling about it?",
        "message_en": "I feel anxious",
        "clinical_flags": [],
        "turn_count": 0,
        "conversation_history": [],
    }
    output_gate_node(state)

    cultural_output_calls = [c for c in calls if c[0] == "cultural_output"]
    assert len(cultural_output_calls) == 1, "output_gate_node must call evaluate('cultural_output', ...) once"
    ctx = cultural_output_calls[0][1]
    assert ctx["response_text"] == "That makes sense. How are you feeling about it?"
    assert ctx["message_en"] == "I feel anxious"
    assert ctx["clinical_flags"] == []


def test_output_gate_skips_cultural_output_for_scope_refusal():
    """Scope refusal path must skip cultural output evaluation — fixed response, not LLM-generated."""
    from sage_poc.nodes.output_gate import output_gate_node
    from sage_poc.rules import engine as rules_engine

    calls = []
    original_evaluate = rules_engine.evaluate

    def mock_evaluate(category, context):
        calls.append(category)
        return original_evaluate(category, context)

    import sage_poc.nodes.output_gate as og_module
    og_module_engine = og_module.rules_engine
    original = og_module_engine.evaluate
    og_module_engine.evaluate = mock_evaluate

    try:
        state = {
            "gate_path": "scope_refusal",
            "detected_language": "en",
            "path": [],
            "response_en": None,
            "message_en": "diagnose me",
            "clinical_flags": [],
            "turn_count": 0,
            "conversation_history": [],
        }
        output_gate_node(state)
        assert "cultural_output" not in calls
    finally:
        og_module_engine.evaluate = original
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_cultural_output.py::test_output_gate_calls_cultural_output_evaluate tests/test_cultural_output.py::test_output_gate_skips_cultural_output_for_scope_refusal -v
```
Expected: Both FAIL — `output_gate.py` doesn't import or call `rules_engine` yet.

- [ ] **Step 3: Wire cultural_output evaluation into output_gate.py**

In `src/sage_poc/nodes/output_gate.py`, add the import at the top:

```python
from sage_poc.rules import engine as rules_engine
```

Then in `output_gate_node`, after the three-path gate selection and before the format violation check, add:

```python
    # Cultural output validation — audit-only, non-blocking
    if gate_path not in ("scope_refusal", "jailbreak"):
        cultural_violations = rules_engine.evaluate("cultural_output", {
            "response_text": response_en,
            "message_en": state.get("message_en", ""),
            "clinical_flags": state.get("clinical_flags", []),
        })
        for rule in cultural_violations.fired:
            print(
                f"\n[CULTURAL OUTPUT VIOLATION] {rule.rule_id} v{rule.version}: "
                f"{rule.action.get('message', rule.action.get('type', ''))}"
            )
```

Full updated `output_gate_node` function (showing insertion point relative to existing code):

```python
def output_gate_node(state: SageState) -> dict:
    gate_path = state.get("gate_path")
    lang = state["detected_language"]
    path = state["path"] + ["output_gate"]

    if gate_path == "scope_refusal":
        response_en = SCOPE_REFUSAL_RESPONSE
    elif gate_path == "jailbreak":
        response_en = JAILBREAK_RESPONSE
    else:
        response_en = state["response_en"] or ""

    # Cultural output validation — audit-only, non-blocking
    if gate_path not in ("scope_refusal", "jailbreak"):
        cultural_violations = rules_engine.evaluate("cultural_output", {
            "response_text": response_en,
            "message_en": state.get("message_en", ""),
            "clinical_flags": state.get("clinical_flags", []),
        })
        for rule in cultural_violations.fired:
            print(
                f"\n[CULTURAL OUTPUT VIOLATION] {rule.rule_id} v{rule.version}: "
                f"{rule.action.get('message', rule.action.get('type', ''))}"
            )

    violations = _FORMAT_VIOLATIONS.findall(response_en)
    if violations:
        print(f"\n[FORMAT VIOLATION] Disallowed formatting detected: {violations}")
    # ... rest of function unchanged
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_cultural_output.py -v
```
Expected: ALL tests pass.

- [ ] **Step 5: Run full suite to confirm no regressions**

```bash
python -m pytest tests/ -v
```
Expected: ALL tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/nodes/output_gate.py tests/test_cultural_output.py
git commit -m "feat(output_gate): wire cultural_output evaluation — audit-only post-generation checks"
```

---

## Task 3: CUO-IS-001 (Religious Language Mirroring)

**Rule:** When the user used Islamic vocabulary, the response should mirror it. If it doesn't, log an audit warning.

**Check type:** `allowlist_required` — the response must contain at least one Islamic vocabulary term when the condition is met.

**Files:**
- Create: `src/sage_poc/rules/data/cultural_output/religious_mirroring.json`
- Test: `tests/test_cultural_output.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cultural_output.py`:

```python
# ── CUO-IS-001 ───────────────────────────────────────────────────────────────

def test_cuo_is_001_fires_when_islamic_input_but_secular_response():
    """CUO-IS-001 must fire when user used 'allah' but response contains no Islamic vocabulary."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "That sounds really difficult. How are you coping with it?",
        "message_en": "I feel like allah has abandoned me",
        "clinical_flags": [],
    })
    fired_ids = result.fired_ids
    assert "CUO-IS-001" in fired_ids, (
        "CUO-IS-001 must fire when Islamic keyword in message but no Islamic vocab in response"
    )


def test_cuo_is_001_passes_when_response_mirrors_islamic_vocab():
    """CUO-IS-001 must NOT fire when response includes Islamic vocabulary."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "The concept of sabr can help — patient perseverance through difficulty is honoured.",
        "message_en": "I feel like allah has abandoned me",
        "clinical_flags": [],
    })
    fired_ids = result.fired_ids
    assert "CUO-IS-001" not in fired_ids


def test_cuo_is_001_does_not_fire_without_islamic_input():
    """CUO-IS-001 must NOT fire when the user's message has no Islamic keywords."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "That sounds really difficult. How are you coping with it?",
        "message_en": "I feel so alone and hopeless",
        "clinical_flags": [],
    })
    fired_ids = result.fired_ids
    assert "CUO-IS-001" not in fired_ids
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_cultural_output.py -k "cuo_is" -v
```
Expected: ALL FAIL — rule file doesn't exist yet.

- [ ] **Step 3: Create CUO-IS-001**

Create `src/sage_poc/rules/data/cultural_output/religious_mirroring.json`:

```json
{
  "category": "cultural_output",
  "rules": [
    {
      "rule_id": "CUO-IS-001",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Warn when user used Islamic vocabulary but response contains no Islamic vocabulary — mirroring may have failed",
      "category": "cultural_output",
      "check_type": "allowlist_required",
      "condition_type": "keyword_in_message",
      "condition_keywords": [
        "allah", "الله", "inshallah", "إن شاء الله",
        "alhamdulillah", "الحمد لله", "mashallah", "subhanallah", "bismillah"
      ],
      "condition_value": null,
      "patterns": [
        "allah", "الله", "sabr", "tawakkul", "ibtila",
        "inshallah", "إن شاء الله", "alhamdulillah", "الحمد لله",
        "mashallah", "subhanallah", "bismillah", "patience", "perseverance"
      ],
      "action": {
        "type": "audit_warn",
        "severity": "medium",
        "message": "User used Islamic vocabulary but response contains no Islamic vocabulary — cultural mirroring may have failed."
      }
    }
  ]
}
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_cultural_output.py -k "cuo_is" -v
```
Expected: ALL three tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/rules/data/cultural_output/religious_mirroring.json tests/test_cultural_output.py
git commit -m "feat(rules): add CUO-IS-001 Islamic vocabulary mirroring post-generation check"
```

---

## Task 4: CUO-FA-001 (Family Not Dismissed)

**Rule:** When the user discussed family context, the response must not contain Western individualist dismissals of family obligations.

**Check type:** `blocklist` — violation if individualist dismissal phrases appear in response when family context was present.

**Files:**
- Create: `src/sage_poc/rules/data/cultural_output/family_framing.json`
- Test: `tests/test_cultural_output.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cultural_output.py`:

```python
# ── CUO-FA-001 ───────────────────────────────────────────────────────────────

def test_cuo_fa_001_fires_when_family_context_and_individualist_response():
    """CUO-FA-001 must fire when family context + individualist dismissal phrase in response."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "It sounds hard. Remember, you need to put yourself first and set boundaries with your family.",
        "message_en": "My parents expect me to give up my career",
        "clinical_flags": [],
    })
    assert "CUO-FA-001" in result.fired_ids, (
        "CUO-FA-001 must fire on 'put yourself first' when family context present"
    )


def test_cuo_fa_001_fires_on_you_owe_them_nothing():
    """CUO-FA-001 must fire on 'you owe them nothing' dismissal."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "You owe them nothing. Your own happiness matters most.",
        "message_en": "I feel guilty about letting my family down",
        "clinical_flags": [],
    })
    assert "CUO-FA-001" in result.fired_ids


def test_cuo_fa_001_absent_without_family_context():
    """CUO-FA-001 must NOT fire when message has no family keywords."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "You need to put yourself first and prioritize your own needs.",
        "message_en": "I feel really overwhelmed by work",
        "clinical_flags": [],
    })
    assert "CUO-FA-001" not in result.fired_ids, (
        "CUO-FA-001 must not fire without family context, even if individualist phrase present"
    )


def test_cuo_fa_001_absent_when_response_is_balanced():
    """CUO-FA-001 must NOT fire when response is balanced (no individualist dismissal phrases)."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "It sounds like you're trying to hold a lot of things at once — your own needs and the expectations of people you love.",
        "message_en": "My parents expect me to give up my career",
        "clinical_flags": [],
    })
    assert "CUO-FA-001" not in result.fired_ids
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_cultural_output.py -k "cuo_fa" -v
```
Expected: ALL FAIL.

- [ ] **Step 3: Create CUO-FA-001**

Create `src/sage_poc/rules/data/cultural_output/family_framing.json`:

```json
{
  "category": "cultural_output",
  "rules": [
    {
      "rule_id": "CUO-FA-001",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Warn when response dismisses family obligations with Western individualist framing when family context was present",
      "category": "cultural_output",
      "check_type": "blocklist",
      "condition_type": "keyword_in_message",
      "condition_keywords": [
        "family", "parents", "mother", "father", "husband", "wife",
        "brother", "sister", "obligation", "duty", "expectation",
        "عائلة", "أهل", "والدين", "أم", "أب"
      ],
      "condition_value": null,
      "patterns": [
        "put yourself first",
        "prioritize yourself",
        "prioritize your own needs",
        "that's not your responsibility",
        "you owe them nothing",
        "set boundaries with your family",
        "your needs matter more",
        "you don't owe your family",
        "family is holding you back"
      ],
      "action": {
        "type": "audit_warn",
        "severity": "high",
        "message": "Response may be applying individualist framing (dismissing family obligations) when collectivist cultural context was detected."
      }
    }
  ]
}
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_cultural_output.py -k "cuo_fa" -v
```
Expected: ALL four tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/rules/data/cultural_output/family_framing.json tests/test_cultural_output.py
git commit -m "feat(rules): add CUO-FA-001 family-not-dismissed post-generation blocklist check"
```

---

## Task 5: CUO-SU-001 + CUO-GC-001 (Substance Language + General Cultural)

**CUO-SU-001:** When `substance_use` clinical flag is active, block responses that suggest harm reduction strategies inappropriate for UAE legal context.

**CUO-GC-001:** Always-active blocklist for content that is culturally inappropriate in a Khaleeji/UAE context.

**Files:**
- Create: `src/sage_poc/rules/data/cultural_output/substance_language.json`
- Create: `src/sage_poc/rules/data/cultural_output/general_cultural.json`
- Test: `tests/test_cultural_output.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cultural_output.py`:

```python
# ── CUO-SU-001 ───────────────────────────────────────────────────────────────

def test_cuo_su_001_fires_on_harm_reduction_with_substance_flag():
    """CUO-SU-001 must fire when response contains harm-reduction language + substance_use flag."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "Harm reduction strategies like using clean needles can help keep you safer.",
        "message_en": "I've been using drugs to cope",
        "clinical_flags": ["substance_use"],
    })
    assert "CUO-SU-001" in result.fired_ids, (
        "CUO-SU-001 must fire on 'harm reduction' when substance_use flag active"
    )


def test_cuo_su_001_fires_on_moderate_use_language():
    """CUO-SU-001 must fire on 'moderate use' framing."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "Some people find that moderate use of alcohol helps them relax.",
        "message_en": "I drink to deal with stress",
        "clinical_flags": ["substance_use"],
    })
    assert "CUO-SU-001" in result.fired_ids


def test_cuo_su_001_absent_without_substance_flag():
    """CUO-SU-001 must NOT fire when substance_use flag is not active."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "Harm reduction approaches can sometimes be helpful.",
        "message_en": "I'm struggling",
        "clinical_flags": [],
    })
    assert "CUO-SU-001" not in result.fired_ids


def test_cuo_su_001_absent_for_clean_substance_response():
    """CUO-SU-001 must NOT fire when substance_use flag active but response is clean."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "It sounds like the substance is helping you manage some really difficult feelings. What emotions does it help with?",
        "message_en": "I drink to deal with stress",
        "clinical_flags": ["substance_use"],
    })
    assert "CUO-SU-001" not in result.fired_ids


# ── CUO-GC-001 ───────────────────────────────────────────────────────────────

def test_cuo_gc_001_fires_on_western_dating_language():
    """CUO-GC-001 must fire when response references dating apps in an UAE cultural context."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "Maybe trying dating apps could help you feel more connected.",
        "message_en": "I feel so lonely",
        "clinical_flags": [],
    })
    assert "CUO-GC-001" in result.fired_ids


def test_cuo_gc_001_fires_on_pork_idiom():
    """CUO-GC-001 must fire on pork-related idioms inappropriate in Islamic context."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "You could say he's bringing home the bacon with that job.",
        "message_en": "My husband works very hard",
        "clinical_flags": [],
    })
    assert "CUO-GC-001" in result.fired_ids


def test_cuo_gc_001_absent_for_appropriate_response():
    """CUO-GC-001 must NOT fire for culturally appropriate responses."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "That sounds really isolating. What kinds of connection have felt meaningful to you in the past?",
        "message_en": "I feel so lonely",
        "clinical_flags": [],
    })
    assert "CUO-GC-001" not in result.fired_ids
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_cultural_output.py -k "cuo_su or cuo_gc" -v
```
Expected: ALL FAIL.

- [ ] **Step 3: Create CUO-SU-001**

Create `src/sage_poc/rules/data/cultural_output/substance_language.json`:

```json
{
  "category": "cultural_output",
  "rules": [
    {
      "rule_id": "CUO-SU-001",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Warn when response contains harm-reduction language inappropriate for UAE legal context when substance_use flag active",
      "category": "cultural_output",
      "check_type": "blocklist",
      "condition_type": "flag_present",
      "condition_keywords": [],
      "condition_value": "substance_use",
      "patterns": [
        "harm reduction",
        "needle exchange",
        "safe injection",
        "moderate use",
        "recreational use",
        "cannabis is",
        "marijuana is",
        "alcohol is legal",
        "drinking in moderation",
        "using safely"
      ],
      "action": {
        "type": "audit_warn",
        "severity": "high",
        "message": "Response may contain substance-related language inappropriate for UAE legal context — harm reduction framing detected with substance_use flag active."
      }
    }
  ]
}
```

- [ ] **Step 4: Create CUO-GC-001**

Create `src/sage_poc/rules/data/cultural_output/general_cultural.json`:

```json
{
  "category": "cultural_output",
  "rules": [
    {
      "rule_id": "CUO-GC-001",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Always-active blocklist for culturally inappropriate content in UAE/Gulf context",
      "category": "cultural_output",
      "check_type": "blocklist",
      "condition_type": "always",
      "condition_keywords": [],
      "condition_value": null,
      "patterns": [
        "dating apps",
        "hook up",
        "hookup",
        "premarital sex",
        "pork",
        "bringing home the bacon",
        "pig out",
        "happy hour"
      ],
      "action": {
        "type": "audit_warn",
        "severity": "medium",
        "message": "Response may contain culturally inappropriate content for UAE/Gulf Khaleeji context."
      }
    }
  ]
}
```

- [ ] **Step 5: Run all cultural output tests**

```bash
python -m pytest tests/test_cultural_output.py -v
```
Expected: ALL tests pass.

- [ ] **Step 6: Run full test suite**

```bash
python -m pytest tests/ -v
```
Expected: ALL tests pass — no regressions.

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/rules/data/cultural_output/substance_language.json src/sage_poc/rules/data/cultural_output/general_cultural.json tests/test_cultural_output.py
git commit -m "feat(rules): add CUO-SU-001 substance language check and CUO-GC-001 general cultural blocklist"
```

---

## Final Verification

- [ ] **Verify all CUO rule IDs are active**

```bash
python -c "
from sage_poc.rules.loader import reload_all, load_rules
reload_all()
rules = load_rules('cultural_output')
for r in rules:
    print(r.rule_id, r.check_type, r.condition_type, r.active)
"
```
Expected output:
```
CUO-IS-001 allowlist_required keyword_in_message True
CUO-FA-001 blocklist keyword_in_message True
CUO-SU-001 blocklist flag_present True
CUO-GC-001 blocklist always True
```

- [ ] **Confirm output_gate integration end-to-end**

```bash
python -c "
from sage_poc.rules import engine as rules_engine
from sage_poc.rules.loader import reload_all
reload_all()
result = rules_engine.evaluate('cultural_output', {
    'response_text': 'Maybe try dating apps to feel connected.',
    'message_en': 'I feel lonely',
    'clinical_flags': [],
})
print('Fired:', result.fired_ids)
"
```
Expected: `Fired: ['CUO-GC-001']`

---

## Self-Review Checklist

**Spec coverage:**
- Item 3 (religious mirroring check) → Task 3: CUO-IS-001 ✅
- Item 4 (family not dismissed) → Task 4: CUO-FA-001 ✅
- Item 5 (substance language UAE) → Task 5: CUO-SU-001 ✅
- Item 6 (general cultural) → Task 5: CUO-GC-001 ✅

**Architecture alignment:**
- New category follows exact same loader/engine/schema pattern as existing categories ✅
- POC scope: audit-only (print violations, no blocking/regeneration) ✅
- `output_gate` integration non-blocking — existing response flow unchanged ✅
- No state field additions required — engine gets context from existing state keys ✅

**Type consistency:**
- `CulturalOutputRule` added to both `loader._RULE_MODELS` and `engine._EVAL_DISPATCH` ✅
- Import in `engine.py` updated to include `CulturalOutputRule` ✅
- `condition_value: str | None = None` correctly handles `flag_present` and non-flag conditions ✅
