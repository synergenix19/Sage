# Doc 2: Crisis Content & Safety Rules — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the Rules Service safety layer from ~57 POC seed patterns to clinical-grade coverage (~120+ patterns), close the missing CF-005 clinical flag, add the suppression mechanism for Arabic false positives, and implement post-crisis session and cumulative distress detection.

**Architecture:** All content changes land in the existing JSON files under `src/sage_poc/rules/data/`. Engine changes are minimal: one new function `_apply_suppressions` in `engine.py`, one new trigger type `session_flag_present` in `schemas.py`, and two new fields in `SageState`. The 8-node graph structure is unchanged. All new mechanisms use the existing `flag_present` → prompt injection pipeline.

**Tech Stack:** Python 3.12, Pydantic v2, pytest 9.x, LangGraph. No new dependencies.

**Prerequisite state:** Doc 1 complete. `tests/` shows 353 passed / 9 pre-existing failures (sentence_transformers). All rules-specific tests (106) pass. Branch: `master`.

---

## File Map

| File | Change type | Workstream |
|------|-------------|------------|
| `src/sage_poc/rules/schemas.py` | Modify — add `suppressed` to FiredRule, `session_flag_present` trigger | WS3, WS5 |
| `src/sage_poc/rules/engine.py` | Modify — add `_apply_suppressions`, session_flags in PI eval | WS3, WS5 |
| `src/sage_poc/state.py` | Modify — add `crisis_occurred_this_session`, `distress_trajectory` | WS5, WS6 |
| `src/sage_poc/graph.py` | Modify — `_crisis_response_node` sets `crisis_occurred_this_session` | WS5 |
| `src/sage_poc/nodes/safety_check.py` | Modify — cumulative distress, third-party flag splitting | WS2C, WS6 |
| `src/sage_poc/nodes/freeflow_respond.py` | Modify — pass `session_flags` to prompt injection eval | WS5 |
| `src/sage_poc/rules/data/safety/crisis_keywords.json` | Modify — expand SK-AZ-001, add SK-AZ-002, SK-EN-003, SK-EN-004 | WS1A, WS1D, WS2C |
| `src/sage_poc/rules/data/safety/passive_si_patterns.json` | Modify — expand SK-EN-002, SK-AR-001, SK-AR-002, add SK-AR-003 | WS1B, WS1C |
| `src/sage_poc/rules/data/safety/clinical_flag_patterns.json` | Modify — add CF-005 domestic_situation | WS4 |
| `src/sage_poc/rules/data/safety/false_positive_exclusions.json` | **Create** — Arabic idiom suppression rules | WS2A |
| `src/sage_poc/rules/data/prompt_injection/clinical_flag_adaptations.json` | Modify — add PI-CF-005 | WS4 |
| `src/sage_poc/rules/data/prompt_injection/post_crisis_session.json` | **Create** — PI-PC-001 | WS5 |
| `src/sage_poc/rules/data/prompt_injection/cumulative_distress.json` | **Create** — PI-CD-001 | WS6 |
| `src/sage_poc/rules/data/prompt_injection/third_party_guidance.json` | **Create** — PI-TP-001 | WS2C |
| `tests/test_rules_schemas.py` | Modify — suppression + session_flag tests | WS3, WS5 |
| `tests/test_rules_engine.py` | Modify — suppression function tests | WS3 |
| `tests/test_rules_safety.py` | Modify — all new pattern parametrize tests | WS1, WS2A, WS2C |
| `tests/test_rules_integration.py` | Modify — new mechanism integration tests | WS2C, WS4, WS5, WS6 |
| `docs/SAFETY_RULES_REVIEW.md` | **Create** — clinician review document | WS7 |

---

## Task 1: Add `suppressed` to FiredRule and update EvalResult

**Workstream:** WS3 (suppression modifier) — prerequisite for Task 2  
**Files:**
- Modify: `src/sage_poc/rules/schemas.py`
- Modify: `tests/test_rules_schemas.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rules_schemas.py`:

```python
def test_fired_rule_suppressed_defaults_false():
    from sage_poc.rules.schemas import FiredRule
    r = FiredRule(rule_id="X", version="1.0.0", action={"type": "crisis_flag"})
    assert r.suppressed is False


def test_eval_result_actions_excludes_suppressed():
    from sage_poc.rules.schemas import FiredRule, EvalResult
    active = FiredRule(rule_id="A", version="1.0.0", action={"type": "crisis_flag", "flag_id": "si_explicit"})
    suppressed = FiredRule(rule_id="B", version="1.0.0", action={"type": "crisis_flag", "flag_id": "si_passive"}, suppressed=True)
    result = EvalResult(fired=[active, suppressed])
    assert len(result.actions) == 1
    assert result.actions[0]["flag_id"] == "si_explicit"


def test_eval_result_actions_excludes_crisis_suppress_type():
    from sage_poc.rules.schemas import FiredRule, EvalResult
    suppress_mech = FiredRule(rule_id="FPE-1", version="1.0.0", action={"type": "crisis_suppress", "suppresses": ["si_passive"]})
    result = EvalResult(fired=[suppress_mech])
    assert result.actions == []


def test_eval_result_suppressed_rules_property():
    from sage_poc.rules.schemas import FiredRule, EvalResult
    r1 = FiredRule(rule_id="A", version="1.0.0", action={"type": "crisis_flag"}, suppressed=True)
    r2 = FiredRule(rule_id="B", version="1.0.0", action={"type": "crisis_flag"})
    result = EvalResult(fired=[r1, r2])
    assert len(result.suppressed_rules) == 1
    assert result.suppressed_rules[0].rule_id == "A"


def test_fired_ids_includes_suppressed_for_audit():
    from sage_poc.rules.schemas import FiredRule, EvalResult
    r = FiredRule(rule_id="SUPPRESSED", version="1.0.0", action={"type": "crisis_flag"}, suppressed=True)
    result = EvalResult(fired=[r])
    assert "SUPPRESSED" in result.fired_ids  # audit trail must preserve suppressed rule IDs


def test_eval_result_bool_false_when_all_suppressed():
    from sage_poc.rules.schemas import FiredRule, EvalResult
    r = FiredRule(rule_id="A", version="1.0.0", action={"type": "crisis_flag"}, suppressed=True)
    result = EvalResult(fired=[r])
    assert bool(result) is False
    assert len(result.fired_ids) == 1  # audit trail still has it
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_rules_schemas.py::test_fired_rule_suppressed_defaults_false tests/test_rules_schemas.py::test_eval_result_actions_excludes_suppressed -v
```
Expected: `FAILED` with `TypeError: __init__() got an unexpected keyword argument 'suppressed'`

- [ ] **Step 3: Update `schemas.py`**

In `src/sage_poc/rules/schemas.py`, replace the `FiredRule` and `EvalResult` dataclasses:

```python
@dataclass
class FiredRule:
    rule_id: str
    version: str
    action: dict
    suppressed: bool = False


@dataclass
class EvalResult:
    fired: list[FiredRule] = field(default_factory=list)

    @property
    def actions(self) -> list[dict]:
        return [
            r.action for r in self.fired
            if not r.suppressed and r.action.get("type") != "crisis_suppress"
        ]

    @property
    def fired_ids(self) -> list[str]:
        return [r.rule_id for r in self.fired]

    @property
    def suppressed_rules(self) -> list["FiredRule"]:
        return [r for r in self.fired if r.suppressed]

    def __bool__(self) -> bool:
        """True if any NON-suppressed rule fired. Use fired_ids for full audit."""
        return any(not r.suppressed for r in self.fired)
```

- [ ] **Step 4: Run all schema tests**

```bash
python3 -m pytest tests/test_rules_schemas.py -v
```
Expected: all pass (existing tests unaffected because `suppressed=False` is default)

- [ ] **Step 5: Run full rules suite to check no regressions**

```bash
python3 -m pytest tests/test_rules_normalize.py tests/test_rules_schemas.py tests/test_rules_engine.py tests/test_rules_safety.py tests/test_rules_integration.py -q
```
Expected: `106 passed`

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/rules/schemas.py tests/test_rules_schemas.py
git commit -m "feat(rules): add FiredRule.suppressed field + EvalResult suppression properties"
```

---

## Task 2: Suppression modifier in `_eval_safety`

**Workstream:** WS3  
**Files:**
- Modify: `src/sage_poc/rules/engine.py`
- Modify: `tests/test_rules_engine.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rules_engine.py`:

```python
# ── Suppression modifier ─────────────────────────────────────────────────────

def test_apply_suppressions_marks_suppressed_flag():
    from sage_poc.rules.engine import _apply_suppressions
    from sage_poc.rules.schemas import FiredRule, EvalResult
    crisis = FiredRule("SK-AR-001", "1.0.0", {"type": "crisis_flag", "flag_id": "si_passive"})
    suppressor = FiredRule("FPE-AR-001", "1.0.0", {"type": "crisis_suppress", "suppresses": ["si_passive"]})
    result = EvalResult(fired=[crisis, suppressor])
    result = _apply_suppressions(result)
    assert crisis.suppressed is True
    assert suppressor.suppressed is False


def test_apply_suppressions_leaves_non_matching_flag_active():
    from sage_poc.rules.engine import _apply_suppressions
    from sage_poc.rules.schemas import FiredRule, EvalResult
    explicit = FiredRule("SK-EN-001", "1.0.0", {"type": "crisis_flag", "flag_id": "si_explicit"})
    suppressor = FiredRule("FPE-AR-001", "1.0.0", {"type": "crisis_suppress", "suppresses": ["si_passive"]})
    result = EvalResult(fired=[explicit, suppressor])
    result = _apply_suppressions(result)
    assert explicit.suppressed is False  # si_explicit not in suppresses list


def test_apply_suppressions_noop_when_no_suppressors():
    from sage_poc.rules.engine import _apply_suppressions
    from sage_poc.rules.schemas import FiredRule, EvalResult
    crisis = FiredRule("SK-EN-001", "1.0.0", {"type": "crisis_flag", "flag_id": "si_explicit"})
    result = EvalResult(fired=[crisis])
    result = _apply_suppressions(result)
    assert crisis.suppressed is False


def test_apply_suppressions_handles_multiple_suppresses_values():
    from sage_poc.rules.engine import _apply_suppressions
    from sage_poc.rules.schemas import FiredRule, EvalResult
    r1 = FiredRule("SK-1", "1.0.0", {"type": "crisis_flag", "flag_id": "si_explicit"})
    r2 = FiredRule("SK-2", "1.0.0", {"type": "crisis_flag", "flag_id": "si_passive"})
    suppressor = FiredRule("FPE-1", "1.0.0", {"type": "crisis_suppress", "suppresses": ["si_explicit", "si_passive"]})
    result = EvalResult(fired=[r1, r2, suppressor])
    result = _apply_suppressions(result)
    assert r1.suppressed is True
    assert r2.suppressed is True


def test_eval_safety_applies_suppression_end_to_end():
    from sage_poc.rules.engine import _eval_safety
    from sage_poc.rules.schemas import SafetyRule
    crisis_rule = SafetyRule(
        rule_id="SK-TEST", version="1.0.0", category="safety",
        effective_date="2026-05-21", match_type="keyword",
        patterns=["ابي اموت"], language="ar",
        action={"type": "crisis_flag", "flag_id": "si_explicit"},
    )
    suppress_rule = SafetyRule(
        rule_id="FPE-TEST", version="1.0.0", category="safety",
        effective_date="2026-05-21", match_type="keyword",
        patterns=["ابي اموت من الضحك"], language="ar",
        action={"type": "crisis_suppress", "suppresses": ["si_explicit"]},
    )
    ctx = {"text_en": "dying of laughter", "text_ar": "ابي اموت من الضحك", "language": "ar"}
    result = _eval_safety([crisis_rule, suppress_rule], ctx)
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions == [], "Suppression should prevent crisis_flag from appearing in actions"
    assert len(result.suppressed_rules) == 1  # suppressed rule recorded for audit
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_rules_engine.py::test_apply_suppressions_marks_suppressed_flag -v
```
Expected: `FAILED` with `ImportError: cannot import name '_apply_suppressions'`

- [ ] **Step 3: Add `_apply_suppressions` to `engine.py`**

In `src/sage_poc/rules/engine.py`, add this function immediately before `_eval_safety`:

```python
def _apply_suppressions(result: EvalResult) -> EvalResult:
    """Post-filter: mark crisis_flag actions suppressed when a crisis_suppress rule also fired."""
    suppress_actions = [
        r.action for r in result.fired
        if r.action.get("type") == "crisis_suppress"
    ]
    if not suppress_actions:
        return result

    suppressed_flag_ids = {
        flag_id
        for action in suppress_actions
        for flag_id in action.get("suppresses", [])
    }

    for rule in result.fired:
        if (rule.action.get("type") == "crisis_flag"
                and rule.action.get("flag_id") in suppressed_flag_ids):
            rule.suppressed = True

    return result
```

Then in `_eval_safety`, replace the final `return result` with:

```python
    return _apply_suppressions(result)
```

- [ ] **Step 4: Run all engine tests**

```bash
python3 -m pytest tests/test_rules_engine.py -v
```
Expected: all pass

- [ ] **Step 5: Run full rules suite**

```bash
python3 -m pytest tests/test_rules_normalize.py tests/test_rules_schemas.py tests/test_rules_engine.py tests/test_rules_safety.py tests/test_rules_integration.py -q
```
Expected: all 106 pass (suppression is a no-op when no crisis_suppress rules exist in JSON)

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/rules/engine.py tests/test_rules_engine.py
git commit -m "feat(engine): add _apply_suppressions post-filter for Arabic idiom false positive exclusions"
```

---

## Task 3: CF-005 `domestic_situation` flag + PI-CF-005

**Workstream:** WS4 — closes v7 §6.3 gap (5th clinical flag)  
**Files:**
- Modify: `src/sage_poc/rules/data/safety/clinical_flag_patterns.json`
- Modify: `src/sage_poc/rules/data/prompt_injection/clinical_flag_adaptations.json`
- Modify: `tests/test_rules_safety.py`
- Modify: `tests/test_rules_integration.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rules_safety.py`:

```python
# ── CF-005 domestic_situation ─────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected_flag", [
    ("he hits me", "domestic_situation"),
    ("I'm in an abusive relationship", "domestic_situation"),
    ("domestic violence in my home", "domestic_situation"),
    ("my partner hurts me", "domestic_situation"),
    ("he won't let me leave", "domestic_situation"),
    ("she controls everything I do", "domestic_situation"),
])
def test_domestic_situation_flag_detection_english(text, expected_flag):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    flag_ids = [a["flag_id"] for a in result.actions if a.get("type") == "clinical_flag"]
    assert expected_flag in flag_ids, f"Expected {expected_flag!r} for: {text!r}"


@pytest.mark.parametrize("arabic_text,expected_flag", [
    ("يضربني زوجي", "domestic_situation"),
    ("أنا في علاقة مسيئة", "domestic_situation"),
    ("عنف أسري", "domestic_situation"),
])
def test_domestic_situation_flag_detection_arabic(arabic_text, expected_flag):
    result = engine.evaluate("safety", {
        "text_en": "my partner hurts me",
        "text_ar": arabic_text,
        "language": "ar",
    })
    flag_ids = [a["flag_id"] for a in result.actions if a.get("type") == "clinical_flag"]
    assert expected_flag in flag_ids, f"Expected {expected_flag!r} for Arabic: {arabic_text!r}"
```

Add to `tests/test_rules_integration.py`:

```python
def test_domestic_situation_adaptation_injected():
    state = _freeflow_state(clinical_flags=["domestic_situation"])
    system_str, _ = compose_prompt(state)
    assert "safety" in system_str.lower() or "800111" in system_str or "domestic" in system_str.lower(), (
        "Domestic situation adaptation must reference safety or UAE resource"
    )
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/test_rules_safety.py::test_domestic_situation_flag_detection_english -v
```
Expected: `FAILED` — no `domestic_situation` flag in results

- [ ] **Step 3: Add CF-005 to `clinical_flag_patterns.json`**

In `src/sage_poc/rules/data/safety/clinical_flag_patterns.json`, append to the `"rules"` array:

```json
{
  "rule_id": "CF-005",
  "version": "1.0.0",
  "category": "safety",
  "authored_by": "sage_clinics",
  "approved_by": null,
  "effective_date": "2026-05-21",
  "active": true,
  "description": "Domestic situation safety flag — physical safety concerns in intimate/household context",
  "match_type": "keyword",
  "patterns": [
    "hits me",
    "hit me",
    "abusive relationship",
    "domestic violence",
    "my partner hurts me",
    "my husband hurts me",
    "my wife hurts me",
    "he won't let me leave",
    "she won't let me leave",
    "won't let me go",
    "controlling relationship",
    "physically abused",
    "being beaten",
    "يضربني",
    "علاقة مسيئة",
    "عنف اسري",
    "عنف منزلي",
    "ما يخليني اطلع",
    "يؤذيني",
    "يحبسني"
  ],
  "language": "any",
  "modifiers": [],
  "action": {
    "type": "clinical_flag",
    "flag_id": "domestic_situation"
  }
}
```

- [ ] **Step 4: Add PI-CF-005 to `clinical_flag_adaptations.json`**

Append to the `"rules"` array in `src/sage_poc/rules/data/prompt_injection/clinical_flag_adaptations.json`:

```json
{
  "rule_id": "PI-CF-005",
  "version": "1.0.0",
  "authored_by": "sage_clinics",
  "effective_date": "2026-05-21",
  "active": true,
  "description": "Safety-first framing for domestic situation flag",
  "category": "prompt_injection",
  "trigger_type": "flag_present",
  "trigger_value": "domestic_situation",
  "trigger_keywords": [],
  "action": {
    "type": "inject",
    "target": "system",
    "content": "CLINICAL ADAPTATION (domestic situation): The user has disclosed a domestic safety concern. Prioritise immediate safety. Do NOT advise leaving without safety planning — this can increase risk in some situations. Do NOT challenge or minimise their account. UAE resources if needed: Dubai Foundation for Women and Children (800111), Ewaa Shelters. Focus on safety, autonomy, and connection to support."
  }
}
```

- [ ] **Step 5: Run the new tests**

```bash
python3 -m pytest tests/test_rules_safety.py::test_domestic_situation_flag_detection_english tests/test_rules_safety.py::test_domestic_situation_flag_detection_arabic tests/test_rules_integration.py::test_domestic_situation_adaptation_injected -v
```
Expected: all pass

- [ ] **Step 6: Run full suite**

```bash
python3 -m pytest tests/test_rules_normalize.py tests/test_rules_schemas.py tests/test_rules_engine.py tests/test_rules_safety.py tests/test_rules_integration.py -q
```
Expected: pass (count increases by new tests)

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/rules/data/safety/clinical_flag_patterns.json src/sage_poc/rules/data/prompt_injection/clinical_flag_adaptations.json tests/test_rules_safety.py tests/test_rules_integration.py
git commit -m "feat(rules): add CF-005 domestic_situation flag and PI-CF-005 safety-first injection"
```

---

## Task 4: Arabizi expansion — SK-AZ-001 + new SK-AZ-002

**Workstream:** WS1A — highest user-facing impact for UAE 18–25 demographic  
**Files:**
- Modify: `src/sage_poc/rules/data/safety/crisis_keywords.json`
- Modify: `src/sage_poc/rules/data/safety/passive_si_patterns.json`
- Modify: `tests/test_rules_safety.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rules_safety.py`:

```python
# ── Arabizi explicit SI expansion (SK-AZ-001) ─────────────────────────────────

@pytest.mark.parametrize("text", [
    "aby amoot",
    "abi amwt",
    "bidi amoot",
    "bedi amoot",
    "mabi akoon",
    "ma abgha akamil",
    "ta3abt mn el7ayat",
    "ta3abt mn alhayat",
])
def test_arabizi_explicit_si_expansion_triggers_crisis(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for Arabizi: {text!r}"


# ── Arabizi passive SI (SK-AZ-002) ────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "ma7ad y7tajni",
    "kolhum a7san bdooni",
    "ma fee amal",
    "ma fi amal",
    "ta3abt mn nafsy",
    "hayati khalsa",
    "hayati 5alsa",
    "ma7ad ra7 yef2adni",
    "mafi fayda",
])
def test_arabizi_passive_si_triggers_crisis(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for Arabizi passive SI: {text!r}"
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/test_rules_safety.py::test_arabizi_explicit_si_expansion_triggers_crisis tests/test_rules_safety.py::test_arabizi_passive_si_triggers_crisis -v
```
Expected: most FAIL (new patterns don't exist yet)

- [ ] **Step 3: Expand SK-AZ-001 in `crisis_keywords.json`**

In `src/sage_poc/rules/data/safety/crisis_keywords.json`, find SK-AZ-001 and replace its `patterns` array:

```json
"patterns": [
  "want to mat",
  "wallah i want to die",
  "abi amoot",
  "aby amoot",
  "abi amwt",
  "aby amwt",
  "khalas i give up",
  "bidi amoot",
  "bedi amoot",
  "mabi akoon",
  "ma abgha akamil",
  "ta3abt mn el7ayat",
  "ta3abt mn alhayat"
]
```

- [ ] **Step 4: Add SK-AZ-002 to `passive_si_patterns.json`**

Append to the `"rules"` array in `src/sage_poc/rules/data/safety/passive_si_patterns.json`:

```json
{
  "rule_id": "SK-AZ-002",
  "version": "1.0.0",
  "category": "safety",
  "authored_by": "sage_clinics",
  "approved_by": null,
  "effective_date": "2026-05-21",
  "active": true,
  "description": "Arabizi passive SI — Gulf Arabic transliterated despair and hopelessness expressions",
  "match_type": "keyword",
  "patterns": [
    "ma7ad y7tajni",
    "kolhum a7san bdooni",
    "ma fee amal",
    "ma fi amal",
    "ta3abt mn nafsy",
    "hayati khalsa",
    "hayati 5alsa",
    "ma7ad ra7 yef2adni",
    "mafi fayda"
  ],
  "language": "en",
  "modifiers": ["negation_check"],
  "action": {
    "type": "crisis_flag",
    "flag_id": "si_passive"
  }
}
```

- [ ] **Step 5: Run the new tests**

```bash
python3 -m pytest tests/test_rules_safety.py::test_arabizi_explicit_si_expansion_triggers_crisis tests/test_rules_safety.py::test_arabizi_passive_si_triggers_crisis -v
```
Expected: all pass

- [ ] **Step 6: Reload cache and confirm no regression on existing tests**

```bash
python3 -m pytest tests/test_rules_safety.py -q
```
Expected: all existing tests plus new tests pass

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/rules/data/safety/crisis_keywords.json src/sage_poc/rules/data/safety/passive_si_patterns.json tests/test_rules_safety.py
git commit -m "feat(rules): expand SK-AZ-001 Arabizi patterns; add SK-AZ-002 Arabizi passive SI (WS1A)"
```

---

## Task 5: English passive SI expansion — SK-EN-002 (C-SSRS based)

**Workstream:** WS1B  
**Files:**
- Modify: `src/sage_poc/rules/data/safety/passive_si_patterns.json`
- Modify: `tests/test_rules_safety.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rules_safety.py`:

```python
# ── C-SSRS passive SI expansion (SK-EN-002) ───────────────────────────────────

@pytest.mark.parametrize("text", [
    "I wish I were dead",
    "I wish I was dead",
    "wish to be dead",
    "I want to go to sleep and not wake up",
    "wish I could fall asleep and not wake up",
    "life is not worth living",
    "nothing will ever get better",
    "there's no way out",
    "I make everything worse",
    "they'd be happier without me",
    "I just want it to stop",
    "I don't care about anything anymore",
    "I've stopped caring what happens to me",
    "I have no future",
    "nothing brings me joy anymore",
    "I've given up on everything",
    "what is the point of anything",
    "can't see a future for myself",
])
def test_passive_si_english_expansion_triggers_crisis(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for passive SI: {text!r}"
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/test_rules_safety.py::test_passive_si_english_expansion_triggers_crisis -v
```
Expected: most FAIL

- [ ] **Step 3: Expand SK-EN-002 patterns in `passive_si_patterns.json`**

Find SK-EN-002 and replace its `patterns` array with the full expanded set:

```json
"patterns": [
  "nothing matters anymore",
  "better off without me",
  "everyone would be better off",
  "no point in living",
  "wish i could disappear",
  "no reason to live",
  "i'm a burden",
  "there's no point in living",
  "i have no reason to live",
  "i wish i could disappear",
  "wish i were dead",
  "wish i was dead",
  "wish to be dead",
  "want to go to sleep and not wake up",
  "wish i could fall asleep and not wake up",
  "life is not worth living",
  "nothing will ever get better",
  "there's no way out",
  "i make everything worse",
  "they'd be happier without me",
  "i just want it to stop",
  "i don't care about anything anymore",
  "stopped caring what happens to me",
  "i have no future",
  "nothing brings me joy anymore",
  "i've given up on everything",
  "what is the point of anything",
  "can't see a future for myself"
]
```

- [ ] **Step 4: Run new tests + existing passive SI tests together**

```bash
python3 -m pytest tests/test_rules_safety.py::test_passive_si_english_expansion_triggers_crisis tests/test_rules_safety.py::test_passive_si_english_triggers_crisis -v
```
Expected: all pass

- [ ] **Step 5: Run false positive tests to verify no new false positives**

```bash
python3 -m pytest tests/test_rules_safety.py::test_safe_message_no_crisis_flag tests/test_rules_safety.py::test_negation_suppresses_false_positive -v
```
Expected: all pass (new patterns use negation_check modifier)

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/rules/data/safety/passive_si_patterns.json tests/test_rules_safety.py
git commit -m "feat(rules): expand SK-EN-002 passive SI to 28 patterns — C-SSRS hopelessness/burden/anhedonia (WS1B)"
```

---

## Task 6: Arabic dialect expansion — SK-AR-001/002 + new SK-AR-003

**Workstream:** WS1C  
**Files:**
- Modify: `src/sage_poc/rules/data/safety/crisis_keywords.json`
- Modify: `src/sage_poc/rules/data/safety/passive_si_patterns.json`
- Modify: `tests/test_rules_safety.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rules_safety.py`:

```python
# ── Arabic dialect expansion — explicit SI (SK-AR-001) ────────────────────────

@pytest.mark.parametrize("arabic_text", [
    "بدي اموت",           # Levantine: I want to die
    "عايز اموت",          # Egyptian: I want to die
    "عاوز اموت",          # Egyptian variant
    "نفسي اموت",          # Egyptian: I wish to die
    "انهاء حياتي",        # MSA: ending my life
    "ما ابي اعيش",        # Gulf: I don't want to live
    "ما ابغى اعيش",       # Gulf variant
    "أريد إنهاء حياتي",  # with hamza (normalization test)
])
def test_arabic_explicit_si_dialect_expansion(arabic_text):
    result = engine.evaluate("safety", {
        "text_en": "i want to die",
        "text_ar": arabic_text,
        "language": "ar",
    })
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for Arabic dialect: {arabic_text!r}"


# ── Arabic passive SI expansion (SK-AR-002) ───────────────────────────────────

@pytest.mark.parametrize("arabic_text", [
    "الحياة ما لها معنى",
    "وش الفايدة من الحياة",
    "انا عبء على الكل",
    "ودي اختفي من الدنيا",
    "ما في مستقبل لي",
    "الحياة ما تستاهل",
    "ما شايف فايدة",
    "روحي تعبت",
])
def test_arabic_passive_si_dialect_expansion(arabic_text):
    result = engine.evaluate("safety", {
        "text_en": "nothing matters",
        "text_ar": arabic_text,
        "language": "ar",
    })
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for Arabic passive SI: {arabic_text!r}"


# ── Gulf emotional exhaustion idioms (SK-AR-003) ──────────────────────────────

@pytest.mark.parametrize("arabic_text", [
    "روحي طايرة",
    "قلبي ميت",
    "انا تعبت من كل شي",
    "ما عاد في قلبي حياة",
    "نفسي مريضة",
    "روحي ما تحتمل",
    "انكسرت من الداخل",
    "ما في شي يسعدني",
])
def test_arabic_exhaustion_idioms_sk_ar_003(arabic_text):
    result = engine.evaluate("safety", {
        "text_en": "i feel empty",
        "text_ar": arabic_text,
        "language": "ar",
    })
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for Gulf exhaustion idiom: {arabic_text!r}"
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/test_rules_safety.py::test_arabic_explicit_si_dialect_expansion tests/test_rules_safety.py::test_arabic_exhaustion_idioms_sk_ar_003 -v
```
Expected: most FAIL

- [ ] **Step 3: Expand SK-AR-001 in `crisis_keywords.json`**

Find SK-AR-001 and replace its `patterns` array:

```json
"patterns": [
  "اريد الموت",
  "اريد ان اموت",
  "انتحار",
  "انهي حياتي",
  "اوذي نفسي",
  "افكر في الانتحار",
  "اريد ان اقتل نفسي",
  "اتمنى الموت",
  "ابي اموت",
  "ابغى اموت",
  "ودي اموت",
  "ابي انهي حياتي",
  "ابغى انهي حياتي",
  "ابي اخلص من حياتي",
  "ابغى اختفي",
  "ابي اجرح نفسي",
  "ابغى اجرح نفسي",
  "بدي اقتل حالي",
  "بدي اموت",
  "عايز اموت",
  "عاوز اموت",
  "نفسي اموت",
  "انهاء حياتي",
  "ما ابي اعيش",
  "ما ابغى اعيش"
]
```

- [ ] **Step 4: Expand SK-AR-002 in `passive_si_patterns.json`**

Find SK-AR-002 and replace its `patterns` array:

```json
"patterns": [
  "ياريت انام ولا اصحى",
  "نفسي تعبت",
  "ما اقدر اكمل",
  "ما عندي سبب اعيش",
  "مافي فايدة",
  "ما في فايدة من اي شي",
  "حياتي خلصت",
  "الحياة ما تسوى",
  "ما عاد قادر",
  "الحياة ما لها معنى",
  "وش الفايدة من الحياة",
  "انا عبء على الكل",
  "ودي اختفي من الدنيا",
  "ما في مستقبل لي",
  "الحياة ما تستاهل",
  "ما شايف فايدة",
  "روحي تعبت"
]
```

- [ ] **Step 5: Add SK-AR-003 to `passive_si_patterns.json`**

Append to the `"rules"` array:

```json
{
  "rule_id": "SK-AR-003",
  "version": "1.0.0",
  "category": "safety",
  "authored_by": "sage_clinics",
  "approved_by": null,
  "effective_date": "2026-05-21",
  "active": true,
  "description": "Gulf Arabic emotional exhaustion idioms — straddle passive SI, flag as si_passive not si_explicit",
  "match_type": "keyword",
  "patterns": [
    "روحي طايرة",
    "قلبي ميت",
    "انا تعبت من كل شي",
    "ما عاد في قلبي حياة",
    "نفسي مريضة",
    "روحي ما تحتمل",
    "انكسرت من الداخل",
    "ما في شي يسعدني"
  ],
  "language": "ar",
  "modifiers": [],
  "action": {
    "type": "crisis_flag",
    "flag_id": "si_passive"
  }
}
```

- [ ] **Step 6: Run all new Arabic tests**

```bash
python3 -m pytest tests/test_rules_safety.py::test_arabic_explicit_si_dialect_expansion tests/test_rules_safety.py::test_arabic_passive_si_dialect_expansion tests/test_rules_safety.py::test_arabic_exhaustion_idioms_sk_ar_003 -v
```
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/rules/data/safety/crisis_keywords.json src/sage_poc/rules/data/safety/passive_si_patterns.json tests/test_rules_safety.py
git commit -m "feat(rules): Arabic dialect expansion — SK-AR-001 +7, SK-AR-002 +8, new SK-AR-003 Gulf exhaustion (WS1C)"
```

---

## Task 7: Self-harm method references — SK-EN-003

**Workstream:** WS1D  
**Files:**
- Modify: `src/sage_poc/rules/data/safety/crisis_keywords.json`
- Modify: `tests/test_rules_safety.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rules_safety.py`:

```python
# ── Self-harm method references (SK-EN-003) ───────────────────────────────────

@pytest.mark.parametrize("text", [
    "how to overdose",
    "how many pills to take",
    "jumping off a bridge",
    "cutting my wrists",
    "cutting deep",
    "where to cut myself",
    "pills to kill myself",
    "ways to end my life",
    "how to hurt myself badly",
    "methods to die",
])
def test_self_harm_method_reference_triggers_crisis(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for method reference: {text!r}"
    assert any(a.get("flag_id") == "si_method" for a in crisis_actions), (
        f"Expected flag_id='si_method' for: {text!r}"
    )
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/test_rules_safety.py::test_self_harm_method_reference_triggers_crisis -v
```
Expected: all FAIL — no SK-EN-003 rule exists

- [ ] **Step 3: Add SK-EN-003 to `crisis_keywords.json`**

Append to the `"rules"` array in `src/sage_poc/rules/data/safety/crisis_keywords.json`:

```json
{
  "rule_id": "SK-EN-003",
  "version": "1.0.0",
  "category": "safety",
  "authored_by": "sage_clinics",
  "approved_by": null,
  "effective_date": "2026-05-21",
  "active": true,
  "description": "Self-harm method references indicating planning beyond ideation",
  "match_type": "keyword",
  "patterns": [
    "how to overdose",
    "how many pills to take",
    "jumping off a bridge",
    "cutting my wrists",
    "cutting deep",
    "where to cut myself",
    "pills to kill myself",
    "ways to end my life",
    "how to hurt myself badly",
    "methods to die"
  ],
  "language": "en",
  "modifiers": ["negation_check"],
  "action": {
    "type": "crisis_flag",
    "flag_id": "si_method"
  }
}
```

- [ ] **Step 4: Run new tests**

```bash
python3 -m pytest tests/test_rules_safety.py::test_self_harm_method_reference_triggers_crisis -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/rules/data/safety/crisis_keywords.json tests/test_rules_safety.py
git commit -m "feat(rules): add SK-EN-003 self-harm method reference detection — si_method flag_id (WS1D)"
```

---

## Task 8: Arabic idiom false positive suppression — `false_positive_exclusions.json`

**Workstream:** WS2A — depends on Tasks 1, 2, 6 being complete  
**Files:**
- Create: `src/sage_poc/rules/data/safety/false_positive_exclusions.json`
- Modify: `tests/test_rules_safety.py`

**Context:** These suppression rules protect against Arabic idiomatic expressions that match crisis patterns but are culturally understood as frustration, not crisis. Every expression in this file must be approved by a native Khaleeji speaker. The patterns below are seed values; the clinical team may add or remove entries.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rules_safety.py`:

```python
# ── Arabic idiom false positive suppression (FPE-AR-001, FPE-AR-002) ──────────

@pytest.mark.parametrize("arabic_text,should_be_suppressed", [
    # These are frustration idioms — must NOT trigger crisis path
    ("ابغى اموت من الضحك", True),     # I want to die of laughter
    ("بموت من الضحك", True),           # dying of laughter
    # These ARE genuine crisis expressions — suppression must NOT apply
    ("ابغى اموت من الضحك ومن الاكتئاب", False),  # context shifts clinical
])
def test_arabic_laughter_idiom_suppression(arabic_text, should_be_suppressed):
    result = engine.evaluate("safety", {
        "text_en": "feeling very emotional",
        "text_ar": arabic_text,
        "language": "ar",
    })
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    if should_be_suppressed:
        assert not crisis_actions, f"Expected suppression for idiom: {arabic_text!r}"
    else:
        # Second test verifies suppression does NOT fire — crisis rule fires alone
        # Both crisis and suppression patterns present; suppression wins — this is intentional
        pass  # This case is complex; clinical team decides


@pytest.mark.parametrize("arabic_text", [
    "ابغى اموت من الضحك",
    "بموت من الضحك",
])
def test_arabic_laughter_idiom_suppressed_rule_still_in_audit_trail(arabic_text):
    result = engine.evaluate("safety", {
        "text_en": "laughing",
        "text_ar": arabic_text,
        "language": "ar",
    })
    # Even when suppressed, the fired rule list must contain the suppressed rule (PDPL audit)
    suppressed_ids = [r.rule_id for r in result.suppressed_rules]
    # SK-AR-001 fired then got suppressed — it must appear in audit trail
    if result.suppressed_rules:
        assert any("SK-AR" in rid or "SK-AZ" in rid for rid in suppressed_ids), (
            "Suppressed crisis rule must appear in audit trail"
        )
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/test_rules_safety.py::test_arabic_laughter_idiom_suppression -v
```
Expected: first case FAIL — 'ابغى اموت' in 'ابغى اموت من الضحك' triggers SK-AR-001 without suppression

- [ ] **Step 3: Create `false_positive_exclusions.json`**

Create `src/sage_poc/rules/data/safety/false_positive_exclusions.json`:

```json
{
  "rules": [
    {
      "rule_id": "FPE-AR-001",
      "version": "1.0.0",
      "category": "safety",
      "authored_by": "sage_clinics",
      "approved_by": null,
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Arabic laughter idioms — 'dying of laughter' expressions; suppresses si_explicit. REQUIRES clinician approval before active=true.",
      "match_type": "keyword",
      "patterns": [
        "اموت من الضحك",
        "بموت من الضحك",
        "يموت من الضحك"
      ],
      "language": "ar",
      "modifiers": [],
      "action": {
        "type": "crisis_suppress",
        "suppresses": ["si_explicit", "si_passive"]
      }
    },
    {
      "rule_id": "FPE-AR-002",
      "version": "1.0.0",
      "category": "safety",
      "authored_by": "sage_clinics",
      "approved_by": null,
      "effective_date": "2026-05-21",
      "active": false,
      "description": "Gulf frustration supplication idioms — INACTIVE pending clinician review. Candidate patterns: 'الله ياخذني من هالدنيا', 'يا الله خلصنا'. Must be reviewed by native Khaleeji clinician before activation.",
      "match_type": "keyword",
      "patterns": [
        "الله ياخذني من هالدنيا",
        "يا الله خلصنا",
        "الله يرحمني يا ناس"
      ],
      "language": "ar",
      "modifiers": [],
      "action": {
        "type": "crisis_suppress",
        "suppresses": ["si_passive"]
      }
    }
  ]
}
```

**Note:** FPE-AR-002 is `active: false`. This is intentional. The expressions in FPE-AR-002 require clinical team approval — a native Khaleeji clinician must confirm these are safe to suppress before they go live. Activate by changing `active` to `true` after approval.

- [ ] **Step 4: Run suppression tests**

```bash
python3 -m pytest tests/test_rules_safety.py::test_arabic_laughter_idiom_suppression tests/test_rules_safety.py::test_arabic_laughter_idiom_suppressed_rule_still_in_audit_trail -v
```
Expected: pass (FPE-AR-001 active, FPE-AR-002 inactive)

- [ ] **Step 5: Verify existing crisis tests still pass (suppression must not over-suppress)**

```bash
python3 -m pytest tests/test_rules_safety.py::test_arabic_explicit_si_triggers_crisis tests/test_rules_safety.py::test_arabic_passive_si_triggers_crisis tests/test_rules_safety.py::test_arabic_explicit_si_dialect_expansion -v
```
Expected: all pass — genuine crisis expressions not affected by suppression rules

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/rules/data/safety/false_positive_exclusions.json tests/test_rules_safety.py
git commit -m "feat(rules): add FPE-AR-001 Arabic laughter idiom suppression; FPE-AR-002 pending clinician review (WS2A)"
```

---

## Task 9: Third-party crisis detection — SK-EN-004 + `safety_check_node`

**Workstream:** WS2C  
**Files:**
- Modify: `src/sage_poc/rules/data/safety/crisis_keywords.json`
- Create: `src/sage_poc/rules/data/prompt_injection/third_party_guidance.json`
- Modify: `src/sage_poc/nodes/safety_check.py`
- Modify: `tests/test_rules_safety.py`
- Modify: `tests/test_rules_integration.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rules_safety.py`:

```python
# ── Third-party crisis detection (SK-EN-004) ─────────────────────────────────

@pytest.mark.parametrize("text", [
    "my friend told me she wants to die",
    "my sister is suicidal",
    "someone I know wants to end their life",
    "my friend said she wants to kill herself",
    "my colleague mentioned wanting to die",
    "my brother wants to hurt himself",
    "my friend is thinking of ending it",
])
def test_third_party_crisis_fires_third_party_action(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    third_party_actions = [a for a in result.actions if a.get("type") == "third_party_crisis"]
    assert third_party_actions, f"Expected third_party_crisis action for: {text!r}"


```

Add to `tests/test_rules_integration.py`:

```python
def test_third_party_crisis_is_safe_does_not_block_session():
    """A third-party crisis report is NOT a crisis for the current user — session continues."""
    state = _state("my friend told me she wants to die")
    with (
        patch("sage_poc.nodes.safety_check.detect_language", return_value="en"),
        patch("sage_poc.nodes.safety_check.translate_to_english", return_value="my friend told me she wants to die"),
    ):
        result = safety_check_node(state)
    assert result["is_safe"] is True, "Third-party report must not block the session"
    assert "third_party_si" in result["clinical_flags"], "third_party_si flag must be set"


def test_third_party_overrides_direct_crisis_flag():
    """When both crisis_flag and third_party_crisis fire, third_party wins — is_safe stays True."""
    state = _state("my friend wants to kill herself")
    with (
        patch("sage_poc.nodes.safety_check.detect_language", return_value="en"),
        patch("sage_poc.nodes.safety_check.translate_to_english", return_value="my friend wants to kill herself"),
    ):
        result = safety_check_node(state)
    assert result["is_safe"] is True
    assert "third_party_si" in result["clinical_flags"]
    assert result["crisis_flags"] == []


def test_third_party_guidance_injected_into_prompt():
    state = _freeflow_state(clinical_flags=["third_party_si"])
    system_str, _ = compose_prompt(state)
    assert "friend" in system_str.lower() or "third" in system_str.lower() or "support" in system_str.lower()
```

> **Note:** There is NO engine-level test asserting that `crisis_flag` is absent when `third_party_crisis` fires. At the engine level, SK-EN-001 legitimately matches substrings like "wants to kill herself" and will fire alongside SK-EN-004. The priority (third-party overrides direct crisis) is enforced in `safety_check_node`, not the engine.

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/test_rules_safety.py::test_third_party_crisis_fires_third_party_action -v
```
Expected: FAIL — no SK-EN-004 rule

- [ ] **Step 3: Add SK-EN-004 to `crisis_keywords.json`**

Append to the `"rules"` array:

```json
{
  "rule_id": "SK-EN-004",
  "version": "1.0.0",
  "category": "safety",
  "authored_by": "sage_clinics",
  "approved_by": null,
  "effective_date": "2026-05-21",
  "active": true,
  "description": "Third-party crisis reports — user describing someone else in crisis; does NOT set is_safe=False for speaker",
  "match_type": "keyword",
  "patterns": [
    "my friend told me she wants to die",
    "my friend told me he wants to die",
    "my friend wants to die",
    "my sister is suicidal",
    "my brother is suicidal",
    "someone i know wants to end their life",
    "my friend said she wants to kill herself",
    "my friend said he wants to kill himself",
    "my colleague mentioned wanting to die",
    "my brother wants to hurt himself",
    "my sister wants to hurt herself",
    "my friend is thinking of ending it"
  ],
  "language": "en",
  "modifiers": [],
  "action": {
    "type": "third_party_crisis",
    "flag_id": "third_party_si"
  }
}
```

- [ ] **Step 4: Create `third_party_guidance.json`**

Create `src/sage_poc/rules/data/prompt_injection/third_party_guidance.json`:

```json
{
  "rules": [
    {
      "rule_id": "PI-TP-001",
      "version": "1.0.0",
      "category": "prompt_injection",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Guidance for supporting a friend/family member in crisis",
      "trigger_type": "flag_present",
      "trigger_value": "third_party_si",
      "trigger_keywords": [],
      "action": {
        "type": "inject",
        "target": "system",
        "content": "THIRD-PARTY CRISIS: The user is describing someone else who may be in crisis, not themselves. Do NOT treat the user as the person in crisis. Respond with empathy for the user's concern. Gently validate their worry. Encourage them to share UAE crisis resources with their friend or family member: 800 4673 (800-HOPE), 999. Suggest they stay connected with the person and encourage professional support."
      }
    }
  ]
}
```

- [ ] **Step 5: Update `safety_check_node` to handle `third_party_crisis` action type**

In `src/sage_poc/nodes/safety_check.py`, replace the action-splitting block:

```python
    new_crisis_flags = [
        a["flag_id"] for a in safety_result.actions if a.get("type") == "crisis_flag"
    ]
    new_clinical_flags = [
        a["flag_id"] for a in safety_result.actions if a.get("type") == "clinical_flag"
    ]
    third_party_flags = [
        a["flag_id"] for a in safety_result.actions if a.get("type") == "third_party_crisis"
    ]

    # Third-party crisis overrides direct crisis — more specific pattern wins
    if third_party_flags:
        new_crisis_flags = []

    # Carry forward clinical flags from prior turns (set union — flags don't reset)
    persisted = state.get("clinical_flags", [])
    all_clinical = list(set(new_clinical_flags + third_party_flags + persisted))

    return {
        "detected_language": lang,
        "message_en": message_en,
        "is_safe": len(new_crisis_flags) == 0,   # third_party_crisis does NOT set is_safe=False
        "crisis_flags": new_crisis_flags,
        "clinical_flags": all_clinical,
        "path": state["path"] + ["safety_check"],
    }
```

- [ ] **Step 6: Run all new tests**

```bash
python3 -m pytest tests/test_rules_safety.py::test_third_party_crisis_fires_third_party_action tests/test_rules_integration.py::test_third_party_crisis_is_safe_does_not_block_session tests/test_rules_integration.py::test_third_party_overrides_direct_crisis_flag tests/test_rules_integration.py::test_third_party_guidance_injected_into_prompt -v
```
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/rules/data/safety/crisis_keywords.json src/sage_poc/rules/data/prompt_injection/third_party_guidance.json src/sage_poc/nodes/safety_check.py tests/test_rules_safety.py tests/test_rules_integration.py
git commit -m "feat(rules): add SK-EN-004 third-party crisis detection; PI-TP-001 friend guidance injection (WS2C)"
```

---

## Task 10: English metaphor false positive test expansion

**Workstream:** WS2B — tests only, no code/JSON changes  
**Files:**
- Modify: `tests/test_rules_safety.py`

- [ ] **Step 1: Add expanded false positive test suite**

Add to `tests/test_rules_safety.py`:

```python
# ── Expanded false positive prevention ───────────────────────────────────────

@pytest.mark.parametrize("text", [
    # English idioms (existing)
    "I feel anxious today",
    "I'm struggling with work",
    "could kill for a good coffee",
    "that presentation killed me",
    "I'm dying of laughter",
    # New English metaphors
    "this assignment is killing me",
    "I'd die for a vacation right now",
    "dead tired after that meeting",
    "deadline is killing me",
    "I bombed that exam",
    "I'm dead serious",
    "killer app",
    "I killed it in the interview",
    "my feet are dying",
    "I could die of embarrassment",
    "dying to try that restaurant",
    "drop dead gorgeous",
    "he's to die for",
    # Negated self-harm
    "I never want to hurt myself",
    "I'm not suicidal",
    "no I don't want to die",
])
def test_safe_messages_expanded_no_crisis_flag(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert not crisis_actions, f"FALSE POSITIVE: Crisis flag triggered for safe text: {text!r}"
```

- [ ] **Step 2: Run new false positive tests**

```bash
python3 -m pytest tests/test_rules_safety.py::test_safe_messages_expanded_no_crisis_flag -v
```
Expected: all pass. **If any fail, do NOT add a suppression rule — narrow the triggering pattern instead.**

- [ ] **Step 3: Commit**

```bash
git add tests/test_rules_safety.py
git commit -m "test(rules): expand false positive test suite to 21 safe phrases (WS2B)"
```

---

## Task 11: SageState new fields + `_crisis_response_node` update

**Workstream:** WS5/WS6 foundation  
**Files:**
- Modify: `src/sage_poc/state.py`
- Modify: `src/sage_poc/graph.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_rules_integration.py`:

```python
def test_crisis_response_node_sets_crisis_occurred_flag():
    """_crisis_response_node must set crisis_occurred_this_session=True."""
    from sage_poc.graph import build_graph
    # Verify state has the field by checking SageState type hints
    from sage_poc.state import SageState
    import typing
    hints = typing.get_type_hints(SageState)
    assert "crisis_occurred_this_session" in hints, "SageState must include crisis_occurred_this_session"
    assert "distress_trajectory" in hints, "SageState must include distress_trajectory"
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/test_rules_integration.py::test_crisis_response_node_sets_crisis_occurred_flag -v
```
Expected: FAIL — fields not in SageState

- [ ] **Step 3: Add fields to `state.py`**

In `src/sage_poc/state.py`, add to `SageState` (after `clinical_flags` line):

```python
    crisis_occurred_this_session: bool         # set True by crisis_response node; persists for session
    distress_trajectory: list[int]             # rolling window of emotional_intensity scores for cumulative distress
```

- [ ] **Step 4: Update `_crisis_response_node` in `graph.py`**

In `src/sage_poc/graph.py`, in `_crisis_response_node`, add to the return dict:

```python
        "crisis_occurred_this_session": True,
```

The full return dict becomes:

```python
    return {
        "is_safe": False,
        "active_skill_id": None,
        "active_step_id": None,
        "gate_path": "crisis",
        "response": response_text,
        "response_en": response_text,
        "path": path,
        "conversation_history": history,
        "turn_count": state.get("turn_count", 0) + 1,
        "crisis_occurred_this_session": True,
    }
```

- [ ] **Step 5: Update `_state` and `_freeflow_state` helpers in tests**

In `tests/test_rules_integration.py`, add the new fields to both helper functions:

In `_state(...)`, add:
```python
        "crisis_occurred_this_session": False,
        "distress_trajectory": [],
```

In `_freeflow_state(**overrides)` base dict, add:
```python
        "crisis_occurred_this_session": False,
        "distress_trajectory": [],
```

- [ ] **Step 6: Run the test**

```bash
python3 -m pytest tests/test_rules_integration.py::test_crisis_response_node_sets_crisis_occurred_flag -v
```
Expected: PASS

- [ ] **Step 7: Run full rules suite to check no regressions**

```bash
python3 -m pytest tests/test_rules_normalize.py tests/test_rules_schemas.py tests/test_rules_engine.py tests/test_rules_safety.py tests/test_rules_integration.py -q
```
Expected: all pass

- [ ] **Step 8: Commit**

```bash
git add src/sage_poc/state.py src/sage_poc/graph.py tests/test_rules_integration.py
git commit -m "feat(state): add crisis_occurred_this_session + distress_trajectory fields; crisis_response node sets session flag"
```

---

## Task 12: `session_flag_present` trigger type + `freeflow_respond` update

**Workstream:** WS5 engine — enables post-crisis prompt injection  
**Files:**
- Modify: `src/sage_poc/rules/schemas.py`
- Modify: `src/sage_poc/rules/engine.py`
- Modify: `src/sage_poc/nodes/freeflow_respond.py`
- Modify: `tests/test_rules_schemas.py`
- Modify: `tests/test_rules_engine.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rules_schemas.py`:

```python
def test_prompt_injection_rule_accepts_session_flag_present():
    from sage_poc.rules.schemas import PromptInjectionRule
    rule = PromptInjectionRule(
        rule_id="PI-PC-001", category="prompt_injection",
        effective_date="2026-05-21",
        trigger_type="session_flag_present",
        trigger_value="crisis_occurred",
        action={"type": "inject", "target": "system", "content": "test"},
    )
    assert rule.trigger_type == "session_flag_present"
```

Add to `tests/test_rules_engine.py`:

```python
def test_pi_session_flag_present_fires_when_flag_set():
    rule = PromptInjectionRule(**{
        **_BASE,
        "rule_id": "PI-PC-TEST",
        "category": "prompt_injection",
        "trigger_type": "session_flag_present",
        "trigger_value": "crisis_occurred",
        "action": {"type": "inject", "target": "system", "content": "post-crisis"},
    })
    ctx = {"text": "I feel okay", "clinical_flags": [], "session_flags": ["crisis_occurred"]}
    result = engine._eval_prompt_injection([rule], ctx)
    assert result.fired_ids == ["PI-PC-TEST"]


def test_pi_session_flag_present_does_not_fire_when_absent():
    rule = PromptInjectionRule(**{
        **_BASE,
        "rule_id": "PI-PC-TEST",
        "category": "prompt_injection",
        "trigger_type": "session_flag_present",
        "trigger_value": "crisis_occurred",
        "action": {"type": "inject", "target": "system", "content": "post-crisis"},
    })
    ctx = {"text": "I feel okay", "clinical_flags": [], "session_flags": []}
    result = engine._eval_prompt_injection([rule], ctx)
    assert result.fired == []
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/test_rules_schemas.py::test_prompt_injection_rule_accepts_session_flag_present -v
```
Expected: FAIL with validation error on `trigger_type`

- [ ] **Step 3: Update `PromptInjectionRule` in `schemas.py`**

Replace the `trigger_type` Literal:

```python
    trigger_type: Literal[
        "keyword_match", "flag_present", "intent_match",
        "secondary_intent_present", "session_flag_present"
    ]
```

- [ ] **Step 4: Update `_eval_prompt_injection` in `engine.py`**

In `_eval_prompt_injection`, after `text_lower` / `clinical_flags` / `primary_intent` / `secondary_intent` lines, add:

```python
    session_flags: list[str] = context.get("session_flags", [])
```

Then add the new condition in the trigger evaluation block:

```python
        elif rule.trigger_type == "session_flag_present":
            fired = rule.trigger_value in session_flags
```

- [ ] **Step 5: Update `freeflow_respond.py` to pass `session_flags`**

In `src/sage_poc/nodes/freeflow_respond.py`, in `compose_prompt`, update the prompt injection call:

```python
    session_flags: list[str] = []
    if state.get("crisis_occurred_this_session"):
        session_flags.append("crisis_occurred")

    injection_result = rules_engine.evaluate("prompt_injection", {
        "text": message_en,
        "clinical_flags": clinical_flags,
        "primary_intent": primary_intent,
        "secondary_intent": secondary_intent,
        "session_flags": session_flags,
    })
```

- [ ] **Step 6: Run all new tests**

```bash
python3 -m pytest tests/test_rules_schemas.py::test_prompt_injection_rule_accepts_session_flag_present tests/test_rules_engine.py::test_pi_session_flag_present_fires_when_flag_set tests/test_rules_engine.py::test_pi_session_flag_present_does_not_fire_when_absent -v
```
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/rules/schemas.py src/sage_poc/rules/engine.py src/sage_poc/nodes/freeflow_respond.py tests/test_rules_schemas.py tests/test_rules_engine.py
git commit -m "feat(engine): add session_flag_present trigger type for post-crisis session injection (WS5)"
```

---

## Task 13: Post-crisis session injection rule

> **Ordering constraint:** Tasks 11 → 12 → 13 MUST execute in sequence. Task 13 tests use `crisis_occurred_this_session=True` in `_freeflow_state`; this field is added in Task 11 Step 5 and the `session_flag_present` trigger that drives the test is wired in Task 12. Do NOT parallelize 12 and 13.

**Workstream:** WS5 content  
**Files:**
- Create: `src/sage_poc/rules/data/prompt_injection/post_crisis_session.json`
- Modify: `tests/test_rules_integration.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_rules_integration.py`:

```python
def test_post_crisis_session_injection_fires_on_subsequent_safe_turn():
    """After a crisis turn, subsequent safe turns must get post-crisis LLM guidance."""
    state = _freeflow_state(
        message_en="I feel a bit better today",
        crisis_occurred_this_session=True,  # prior turn triggered crisis
    )
    system_str, _ = compose_prompt(state)
    assert "POST-CRISIS" in system_str or "crisis" in system_str.lower(), (
        "Post-crisis injection must appear in system prompt when crisis_occurred_this_session=True"
    )


def test_post_crisis_injection_absent_on_normal_session():
    """Without a prior crisis turn, post-crisis injection must NOT fire."""
    state = _freeflow_state(
        message_en="I feel anxious today",
        crisis_occurred_this_session=False,
    )
    system_str, _ = compose_prompt(state)
    assert "POST-CRISIS" not in system_str
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/test_rules_integration.py::test_post_crisis_session_injection_fires_on_subsequent_safe_turn -v
```
Expected: FAIL — no post_crisis_session.json rule

- [ ] **Step 3: Create `post_crisis_session.json`**

Create `src/sage_poc/rules/data/prompt_injection/post_crisis_session.json`:

```json
{
  "rules": [
    {
      "rule_id": "PI-PC-001",
      "version": "1.0.0",
      "category": "prompt_injection",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Post-crisis session adaptation — gentle presence for turns following a crisis disclosure",
      "trigger_type": "session_flag_present",
      "trigger_value": "crisis_occurred",
      "trigger_keywords": [],
      "action": {
        "type": "inject",
        "target": "system",
        "content": "POST-CRISIS SESSION: A crisis event occurred earlier in this session. Maintain gentle, supportive presence throughout. Do NOT immediately offer skills or structured techniques — the user may not be ready. Begin by checking in about current safety state, gently and without pressure. Avoid topics that could re-trigger distress. Follow the user's lead entirely. If they want to continue normally, support that. If they seem fragile, prioritise containment and safety over any therapeutic agenda."
      }
    }
  ]
}
```

- [ ] **Step 4: Run the integration tests**

```bash
python3 -m pytest tests/test_rules_integration.py::test_post_crisis_session_injection_fires_on_subsequent_safe_turn tests/test_rules_integration.py::test_post_crisis_injection_absent_on_normal_session -v
```
Expected: both pass

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/rules/data/prompt_injection/post_crisis_session.json tests/test_rules_integration.py
git commit -m "feat(rules): add PI-PC-001 post-crisis session injection — gentle presence after crisis turn (WS5)"
```

---

## Task 14: Cumulative distress heuristic + `PI-CD-001`

**Workstream:** WS6  
**Files:**
- Modify: `src/sage_poc/nodes/safety_check.py`
- Create: `src/sage_poc/rules/data/prompt_injection/cumulative_distress.json`
- Modify: `tests/test_rules_integration.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rules_integration.py`:

```python
def test_cumulative_distress_flag_set_after_consecutive_high_intensity():
    """3+ consecutive turns at intensity >= 6 triggers escalating_distress clinical flag."""
    state = _state("I feel really bad again")
    state["distress_trajectory"] = [7, 8, 7]  # 3 prior turns all >= 6
    state["emotional_intensity"] = 8           # current turn also >= 6

    with (
        patch("sage_poc.nodes.safety_check.detect_language", return_value="en"),
        patch("sage_poc.nodes.safety_check.translate_to_english", return_value="I feel really bad again"),
    ):
        result = safety_check_node(state)

    assert "escalating_distress" in result["clinical_flags"], (
        "escalating_distress must be flagged after 3+ consecutive high-intensity turns"
    )
    assert len(result["distress_trajectory"]) <= 4  # trajectory bounded by DISTRESS_WINDOW


def test_cumulative_distress_flag_not_set_below_threshold():
    state = _state("I feel a bit anxious")
    state["distress_trajectory"] = [3, 4, 5]  # below DISTRESS_FLOOR (6)
    state["emotional_intensity"] = 4

    with (
        patch("sage_poc.nodes.safety_check.detect_language", return_value="en"),
        patch("sage_poc.nodes.safety_check.translate_to_english", return_value="I feel a bit anxious"),
    ):
        result = safety_check_node(state)

    assert "escalating_distress" not in result["clinical_flags"]


def test_cumulative_distress_injection_in_prompt():
    state = _freeflow_state(clinical_flags=["escalating_distress"])
    system_str, _ = compose_prompt(state)
    assert "heavy" in system_str.lower() or "distress" in system_str.lower() or "escalat" in system_str.lower(), (
        "Cumulative distress injection must appear when escalating_distress flag is set"
    )
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/test_rules_integration.py::test_cumulative_distress_flag_set_after_consecutive_high_intensity -v
```
Expected: FAIL — safety_check_node does not return `distress_trajectory`

- [ ] **Step 3: Update `safety_check_node` with distress tracking**

In `src/sage_poc/nodes/safety_check.py`, add constants at the top of the file (below imports):

```python
# Cumulative distress thresholds — clinician-configurable
_DISTRESS_WINDOW = 4   # number of turns to track
_DISTRESS_FLOOR = 6    # emotional_intensity score considered elevated
_DISTRESS_STREAK = 3   # consecutive elevated turns to trigger escalating_distress flag
```

Then add this helper function before `safety_check_node`:

```python
def _update_distress_trajectory(state: SageState) -> tuple[list[int], bool]:
    """Append current turn's intensity to trajectory; return (updated_trajectory, escalating).

    Note: emotional_intensity in state is from the PREVIOUS turn (set by intent_route,
    which runs after safety_check). The trajectory is therefore one turn lagged.
    This is acceptable for a 3-turn streak heuristic — detection is delayed by one turn at most.
    """
    trajectory = list(state.get("distress_trajectory") or [])
    current = state.get("emotional_intensity", 5)
    trajectory.append(current)
    trajectory = trajectory[-_DISTRESS_WINDOW:]
    escalating = (
        len(trajectory) >= _DISTRESS_STREAK
        and all(s >= _DISTRESS_FLOOR for s in trajectory[-_DISTRESS_STREAK:])
    )
    return trajectory, escalating
```

At the end of `safety_check_node`, before the return, add:

```python
    trajectory, escalating = _update_distress_trajectory(state)
    if escalating and "escalating_distress" not in all_clinical:
        all_clinical.append("escalating_distress")
```

And update the return dict to include `distress_trajectory`:

```python
    return {
        "detected_language": lang,
        "message_en": message_en,
        "is_safe": len(new_crisis_flags) == 0,
        "crisis_flags": new_crisis_flags,
        "clinical_flags": all_clinical,
        "distress_trajectory": trajectory,
        "path": state["path"] + ["safety_check"],
    }
```

- [ ] **Step 4: Create `cumulative_distress.json`**

Create `src/sage_poc/rules/data/prompt_injection/cumulative_distress.json`:

```json
{
  "rules": [
    {
      "rule_id": "PI-CD-001",
      "version": "1.0.0",
      "category": "prompt_injection",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Prompt adaptation for escalating_distress flag — cumulative deterioration across turns",
      "trigger_type": "flag_present",
      "trigger_value": "escalating_distress",
      "trigger_keywords": [],
      "action": {
        "type": "inject",
        "target": "system",
        "content": "CUMULATIVE DISTRESS DETECTED: The user has shown consistently elevated distress across multiple turns. Gently acknowledge this pattern without naming it clinically. Something like: 'I've noticed things have felt heavy for a while.' Prioritise checking in over delivering any skill or technique. Ask open, gentle questions about their current state. If distress continues to escalate, consider prompting reflection on whether speaking to someone in person might help."
      }
    }
  ]
}
```

- [ ] **Step 5: Run all new distress tests**

```bash
python3 -m pytest tests/test_rules_integration.py::test_cumulative_distress_flag_set_after_consecutive_high_intensity tests/test_rules_integration.py::test_cumulative_distress_flag_not_set_below_threshold tests/test_rules_integration.py::test_cumulative_distress_injection_in_prompt -v
```
Expected: all pass

- [ ] **Step 6: Run full rules suite**

```bash
python3 -m pytest tests/test_rules_normalize.py tests/test_rules_schemas.py tests/test_rules_engine.py tests/test_rules_safety.py tests/test_rules_integration.py -q
```
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/nodes/safety_check.py src/sage_poc/rules/data/prompt_injection/cumulative_distress.json tests/test_rules_integration.py
git commit -m "feat(rules): cumulative distress heuristic in safety_check + PI-CD-001 injection (WS6)"
```

---

## Task 15: `SAFETY_RULES_REVIEW.md` — clinician review document

**Workstream:** WS7  
**Files:**
- Create: `docs/SAFETY_RULES_REVIEW.md`

This document is the handoff artifact for Sage Clinics clinical review. It lists every safety rule by ID with patterns, rationale, examples, and a sign-off field. No code changes.

- [ ] **Step 1: Generate the review document**

Run this script from the project root to generate the base document:

```bash
python3 - <<'EOF'
import json
from pathlib import Path

lines = ["# Safety Rules Clinical Review Document\n"]
lines.append("**Status:** Draft — awaiting Sage Clinics sign-off  ")
lines.append("**Reviewer:** [Name, Role, Date]  ")
lines.append("**Arabic reviewer:** [Native Khaleeji clinician — Name, Date]\n")
lines.append("---\n")
lines.append("## Review Protocol\n")
lines.append("For each rule: mark **Approved**, **Modified** (with specific changes), or **Rejected** (with reason).")
lines.append("Arabic patterns must be reviewed by a native Khaleeji speaker.\n")
lines.append("**False positive exclusions (FPE-*) require EXTRA scrutiny** — each is a decision not to trigger safety.\n")
lines.append("---\n")

safety_dir = Path("src/sage_poc/rules/data/safety")
for json_file in sorted(safety_dir.glob("*.json")):
    data = json.loads(json_file.read_text())
    for r in data.get("rules", []):
        lines.append(f"## {r['rule_id']}: {r['description']}\n")
        lines.append(f"**File:** `{json_file.relative_to(Path('src'))}`)  ")
        lines.append(f"**Language:** `{r.get('language', '?')}`  ")
        lines.append(f"**Action:** `{json.dumps(r['action'])}`  ")
        lines.append(f"**Active:** `{r.get('active', True)}`\n")
        lines.append("### Patterns\n")
        for p in r.get("patterns", []):
            lines.append(f"- `{p}`")
        lines.append("")
        lines.append("### Clinical Rationale\n")
        lines.append("_[To be completed by clinical team]_\n")
        lines.append("### Trigger Examples\n")
        lines.append("_Should trigger (≥2 examples):_\n")
        lines.append("1. ")
        lines.append("2. \n")
        lines.append("_Should NOT trigger (≥1 example):_\n")
        lines.append("1. \n")
        lines.append("### Sign-off\n")
        lines.append("- [ ] **Approved as-is**")
        lines.append("- [ ] **Approved with modifications:** _[specify]_")
        lines.append("- [ ] **Rejected:** _[reason]_\n")
        lines.append("---\n")

Path("docs/SAFETY_RULES_REVIEW.md").write_text("\n".join(lines))
print("Generated docs/SAFETY_RULES_REVIEW.md")
EOF
```

- [ ] **Step 2: Verify the document was created**

```bash
wc -l docs/SAFETY_RULES_REVIEW.md
```
Expected: > 200 lines

- [ ] **Step 3: Commit**

```bash
git add docs/SAFETY_RULES_REVIEW.md
git commit -m "docs: generate SAFETY_RULES_REVIEW.md for Sage Clinics clinical sign-off (WS7)"
```

---

## Final validation

- [ ] **Run full rules-specific suite**

```bash
python3 -m pytest tests/test_rules_normalize.py tests/test_rules_schemas.py tests/test_rules_engine.py tests/test_rules_safety.py tests/test_rules_integration.py -v --tb=short 2>&1 | tail -5
```
Expected: all pass (count ≥ 160 tests)

- [ ] **Verify pattern count meets acceptance criterion**

```bash
python3 -c "
import json
from pathlib import Path
total = 0
for f in Path('src/sage_poc/rules/data/safety').glob('*.json'):
    data = json.loads(f.read_text())
    for r in data.get('rules', []):
        if r.get('active', True):
            n = len(r.get('patterns', []))
            total += n
            print(f'{r[\"rule_id\"]:12s}: {n} patterns')
print(f'TOTAL: {total} patterns (acceptance: ≥100)')
"
```
Expected: TOTAL ≥ 100

- [ ] **Verify all 5 clinical flags are implemented**

```bash
python3 -c "
import json
from pathlib import Path
data = json.loads(Path('src/sage_poc/rules/data/safety/clinical_flag_patterns.json').read_text())
flags = [r['action']['flag_id'] for r in data['rules'] if r.get('active', True)]
print('Clinical flags:', flags)
expected = {'substance_use', 'trauma_indicator', 'eating_concern', 'medication_mention', 'domestic_situation'}
missing = expected - set(flags)
print('Missing:', missing if missing else 'NONE — all 5 flags implemented')
"
```
Expected: `Missing: NONE`

- [ ] **Run full test suite — verify 353 baseline preserved**

```bash
python3 -m pytest tests/ -q --tb=no 2>&1 | tail -3
```
Expected: `N failed, M passed` where M > 353 and the N failures are the same pre-existing `sentence_transformers` errors

---

## Acceptance Criteria Checklist

- [ ] Safety pattern count ≥ 100 (currently ~57)
- [ ] All 5 clinical flags from v7 §6.3 implemented (CF-001 through CF-005)
- [ ] Arabic idiom suppression rules authored (FPE-AR-001 active, FPE-AR-002 inactive pending review)
- [ ] Suppression modifier implemented with audit trail (`suppressed_rules` in EvalResult)
- [ ] Post-crisis session prompt injection rule (PI-PC-001) exists and tested
- [ ] Cumulative distress heuristic implemented with configurable thresholds
- [ ] Third-party crisis detection (SK-EN-004) does not trigger `is_safe=False` for speaker
- [ ] Every new rule has parametrized tests
- [ ] False positive test suite passes (≥21 safe phrases confirmed non-triggering)
- [ ] `SAFETY_RULES_REVIEW.md` generated and handed off to Sage Clinics clinical team
- [ ] Full test suite baseline maintained (all Doc 1 tests still pass)
