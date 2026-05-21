# Rules Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Python Rules Service (`sage_poc/rules/`) that moves all hardcoded clinical logic — crisis keywords, negation patterns, cultural adaptation triggers, and prompt injection templates — out of Python source files and into versioned, clinician-editable JSON rule documents, making the first call site in every node deterministic and auditable.

**Architecture:** A stateless `engine.evaluate(category, context)` function dispatches to a category-specific evaluator, matches rules from JSON files in `rules/data/{category}/`, and returns an `EvalResult` of fired rules and their actions. Nodes call the engine before any LLM call; they read state, pass a context dict in, and write the results back to state. The JSON schemas authored now are the production content — no migration cost when the Full Build swaps the file loader for Cosmos DB.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, existing sage-poc LangGraph stack. No new dependencies.

---

## Spec Reference (Section 1 — Design Principles)

- **Rules are data, not code.** Every rule is a JSON document with a defined schema. Engineers never write therapeutic logic in Python.
- **Evaluate deterministically, then fall through.** Engine fires first; LLM is second.
- **Rules are versioned, testable, and auditable.** Every rule carries `rule_id`, `version`, `authored_by`, `effective_date`.
- **Rules compose, they don't override.** Engine collects all fired actions; calling node applies fusion logic.
- **Engine is stateless.** Receives context dict, returns `EvalResult`. Never reads or writes `SageState`.

---

## Codebase Context (read before implementing)

Key facts confirmed from source:

| File | Relevant existing code |
|---|---|
| `src/sage_poc/nodes/safety_check.py:6–81` | `CRISIS_KEYWORDS` and `CLINICAL_KEYWORD_SETS` — move to JSON rules |
| `src/sage_poc/nodes/safety_check.py:84–88` | `_contains_crisis()` — uses ZWSP strip + `.lower()` — replace with `normalize.normalize_text()` |
| `src/sage_poc/nodes/freeflow_respond.py:5–32` | `PERSONA` and `_CLINICAL_ADAPTATIONS` — PERSONA core stays; clinical adaptations move to `prompt_injection` rules; Islamic/collectivist text moves to `cultural` rules |
| `src/sage_poc/graph.py:16–45` | `CRISIS_RESPONSE`, `CRISIS_RESPONSE_AR`, `CRISIS_RESPONSE_EXTENDED` — hardcoded strings; move to `crisis_content` JSON rules |
| `src/sage_poc/graph.py:48–81` | `_crisis_response_node` already exists and sets `gate_path: "crisis"` — **no new node needed** |
| `src/sage_poc/nodes/output_gate.py:7–16` | `SCOPE_REFUSAL_RESPONSE`, `JAILBREAK_RESPONSE` — **keep as-is**, not part of Rules Service |
| `src/sage_poc/skills/schema.py:36` | `semantic_description: str = ""` already present — **no schema fix needed** |
| `src/sage_poc/state.py:32` | `gate_path: Optional[Literal["standard", "scope_refusal", "jailbreak"]]` — add `"crisis"` to the Literal (graph.py already sets it but type is wrong) |

---

## File Map

### New files

| File | Responsibility |
|---|---|
| `src/sage_poc/rules/__init__.py` | Export `evaluate`, `reload_all` |
| `src/sage_poc/rules/schemas.py` | Pydantic models for all rule types + `EvalResult` / `FiredRule` dataclasses |
| `src/sage_poc/rules/normalize.py` | Text pre-processing: ZWSP strip, lowercase, Arabic alef normalization, diacritic removal |
| `src/sage_poc/rules/loader.py` | File-based JSON loader with module-level cache + `reload_all()` |
| `src/sage_poc/rules/engine.py` | `evaluate(category, context) → EvalResult` — stateless dispatch to category evaluators |
| `src/sage_poc/rules/data/safety/crisis_keywords.json` | Explicit SI keyword rules (English + Gulf Arabic + Arabizi) |
| `src/sage_poc/rules/data/safety/passive_si_patterns.json` | Passive SI / veiled ideation patterns (English + Arabic) |
| `src/sage_poc/rules/data/safety/clinical_flag_patterns.json` | Clinical flag keyword rules (substance_use, trauma, eating, medication) |
| `src/sage_poc/rules/data/crisis_content/en_uae.json` | English acute + extended UAE crisis response templates |
| `src/sage_poc/rules/data/crisis_content/ar_uae.json` | Arabic acute UAE crisis response template |
| `src/sage_poc/rules/data/cultural/islamic_vocabulary.json` | Islamic framing injection rule |
| `src/sage_poc/rules/data/cultural/collectivist_framing.json` | Collectivist framing injection rule |
| `src/sage_poc/rules/data/prompt_injection/secondary_intent.json` | Dialectical framing injection when secondary_intent is set |
| `src/sage_poc/rules/data/prompt_injection/clinical_flag_adaptations.json` | Clinical adaptation injections for each flag type |
| `tests/test_rules_normalize.py` | Unit tests for normalize.py |
| `tests/test_rules_engine.py` | Engine unit tests with synthetic rules (no file I/O) |
| `tests/test_rules_safety.py` | Integration tests: real JSON safety rules vs. known-good inputs |
| `tests/test_rules_integration.py` | Node integration: migrated safety_check_node, freeflow compose_prompt, crisis_response_node |

### Modified files

| File | What changes |
|---|---|
| `src/sage_poc/nodes/safety_check.py` | Remove `CRISIS_KEYWORDS`, `CLINICAL_KEYWORD_SETS`, `_contains_crisis`, `_detect_clinical_flags`; replace with `engine.evaluate("safety", ...)` call; add clinical flag carry-forward |
| `src/sage_poc/nodes/freeflow_respond.py` | Remove `_CLINICAL_ADAPTATIONS` dict; strip Islamic/collectivist text from `PERSONA`; replace `compose_prompt` with engine-driven injection assembly |
| `src/sage_poc/graph.py` | Remove `CRISIS_RESPONSE`, `CRISIS_RESPONSE_AR`, `CRISIS_RESPONSE_EXTENDED` constants; `_crisis_response_node` fetches text from `engine.evaluate("crisis_content", ...)` |
| `src/sage_poc/state.py` | Add `"crisis"` to `gate_path` Literal |

---

## Task 1: Pre-processing pipeline — `normalize.py`

**Files:**
- Create: `src/sage_poc/rules/normalize.py`
- Create: `tests/test_rules_normalize.py`

- [ ] **Step 1.1: Write failing tests**

```python
# tests/test_rules_normalize.py
import pytest
from sage_poc.rules.normalize import (
    strip_invisible, strip_arabic_diacritics,
    normalize_alef, normalize_text, normalize_arabic,
)


def test_strip_invisible_removes_zwsp():
    assert strip_invisible("want​to die") == "wantto die"


def test_strip_invisible_removes_bom():
    assert strip_invisible("﻿hello") == "hello"


def test_strip_invisible_removes_zwnj():
    assert strip_invisible("don‌t") == "dont"


def test_strip_arabic_diacritics_removes_fatha():
    # fatha U+064E on alef
    assert strip_arabic_diacritics("أَ") == "أ"


def test_strip_arabic_diacritics_removes_sukun():
    assert strip_arabic_diacritics("مْ") == "م"


def test_normalize_alef_hamza_above():
    # أ (U+0623) → ا (U+0627)
    assert normalize_alef("أبي") == "ابي"


def test_normalize_alef_madda():
    # آ (U+0622) → ا
    assert normalize_alef("آخر") == "اخر"


def test_normalize_alef_hamza_below():
    # إ (U+0625) → ا
    assert normalize_alef("إبراهيم") == "ابراهيم"


def test_normalize_alef_wasla():
    # ٱ (U+0671) → ا
    assert normalize_alef("ٱلله") == "الله"


def test_normalize_text_lowercases():
    assert normalize_text("KILL MYSELF") == "kill myself"


def test_normalize_text_strips_invisible_before_lowercase():
    assert normalize_text("want​to DIE") == "wantto die"


def test_normalize_arabic_full_pipeline():
    # أبي أموت (with hamza above alef) → normalized to bare alef
    result = normalize_arabic("أبي أموت")
    assert result == "ابي اموت"


def test_normalize_arabic_strips_diacritics_and_alef():
    # أَبِي أَمُوتُ (with full harakat) → ابي اموت
    result = normalize_arabic("أَبِي أَمُوتُ")
    assert result == "ابي اموت"


def test_normalize_arabic_bare_alef_unchanged():
    assert normalize_arabic("ابي اموت") == "ابي اموت"
```

- [ ] **Step 1.2: Run tests to confirm they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_rules_normalize.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'sage_poc.rules'`

- [ ] **Step 1.3: Create the `rules` package directory**

```bash
mkdir -p src/sage_poc/rules/data/safety
mkdir -p src/sage_poc/rules/data/crisis_content
mkdir -p src/sage_poc/rules/data/cultural
mkdir -p src/sage_poc/rules/data/prompt_injection
touch src/sage_poc/rules/__init__.py
```

- [ ] **Step 1.4: Write `normalize.py`**

```python
# src/sage_poc/rules/normalize.py
import re
import unicodedata


def strip_invisible(text: str) -> str:
    """Remove ZWSP (U+200B), ZWNJ (U+200C), ZWJ (U+200D), BOM (U+FEFF)."""
    return re.sub(r'[​‌‍﻿]', '', text)


def strip_arabic_diacritics(text: str) -> str:
    """Remove Arabic harakat: fatha, damma, kasra, sukun, shadda, and other diacritics."""
    return re.sub(r'[ً-ٰٟ]', '', text)


def normalize_alef(text: str) -> str:
    """Normalise alef-hamza-above (أ U+0623), alef-madda (آ U+0622),
    alef-hamza-below (إ U+0625), and alef-wasla (ٱ U+0671) to bare alef (ا U+0627)."""
    return re.sub(r'[آأإٱ]', 'ا', text)


def normalize_text(text: str) -> str:
    """
    Universal pre-processing for all text before keyword matching.
    Pipeline: strip_invisible → lowercase.
    Use for both English and Arabic before rule evaluation.
    """
    return strip_invisible(text).lower()


def normalize_arabic(text: str) -> str:
    """
    Extended normalization for Arabic text.
    Pipeline: strip_invisible → NFKC → strip_diacritics → normalize_alef → lowercase.
    Use when matching Arabic keywords to catch orthographic variants across dialects.
    """
    text = strip_invisible(text)
    text = unicodedata.normalize('NFKC', text)
    text = strip_arabic_diacritics(text)
    text = normalize_alef(text)
    return text.lower()
```

- [ ] **Step 1.5: Run tests to confirm they pass**

```bash
uv run pytest tests/test_rules_normalize.py -v
```

Expected: `13 passed`

- [ ] **Step 1.6: Commit**

```bash
git add src/sage_poc/rules/__init__.py src/sage_poc/rules/normalize.py tests/test_rules_normalize.py
git commit -m "feat(rules): add normalize.py pre-processing pipeline with Arabic alef normalization"
```

---

## Task 2: Rule schemas and result types — `schemas.py`

**Files:**
- Create: `src/sage_poc/rules/schemas.py`
- Create: `tests/test_rules_schemas.py`

- [ ] **Step 2.1: Write failing tests**

```python
# tests/test_rules_schemas.py
import pytest
from pydantic import ValidationError
from sage_poc.rules.schemas import (
    SafetyRule, CrisisContentRule, CulturalRule, PromptInjectionRule,
    EvalResult, FiredRule,
)

_BASE = {
    "rule_id": "TEST-001",
    "version": "1.0.0",
    "authored_by": "test",
    "effective_date": "2026-05-21",
    "action": {"type": "crisis_flag", "flag_id": "si_explicit"},
}


def test_safety_rule_valid():
    rule = SafetyRule(**{
        **_BASE,
        "category": "safety",
        "match_type": "keyword",
        "patterns": ["want to die"],
        "language": "en",
        "modifiers": ["negation_check"],
    })
    assert rule.rule_id == "TEST-001"
    assert rule.active is True
    assert "negation_check" in rule.modifiers


def test_safety_rule_defaults():
    rule = SafetyRule(**{
        **_BASE,
        "category": "safety",
        "match_type": "keyword",
        "patterns": ["want to die"],
    })
    assert rule.language == "any"
    assert rule.modifiers == []


def test_safety_rule_rejects_bad_language():
    with pytest.raises(ValidationError):
        SafetyRule(**{
            **_BASE,
            "category": "safety",
            "match_type": "keyword",
            "patterns": ["test"],
            "language": "fr",  # not in allowed Literal
        })


def test_crisis_content_rule_valid():
    rule = CrisisContentRule(**{
        **_BASE,
        "category": "crisis_content",
        "locale": "en_uae",
        "crisis_level": "acute",
        "action": {
            "type": "crisis_response",
            "response_text": "Please call 999.",
            "resources": [],
        },
    })
    assert rule.locale == "en_uae"
    assert rule.crisis_level == "acute"


def test_cultural_rule_valid():
    rule = CulturalRule(**{
        **_BASE,
        "category": "cultural",
        "trigger_keywords": ["allah", "faith"],
        "action": {"type": "prompt_injection", "target": "system", "content": "..."},
    })
    assert rule.trigger_keywords == ["allah", "faith"]


def test_prompt_injection_rule_valid():
    rule = PromptInjectionRule(**{
        **_BASE,
        "category": "prompt_injection",
        "trigger_type": "flag_present",
        "trigger_value": "substance_use",
        "action": {"type": "inject", "target": "system", "content": "Use MI."},
    })
    assert rule.trigger_type == "flag_present"
    assert rule.trigger_value == "substance_use"


def test_inactive_rule_field():
    rule = SafetyRule(**{
        **_BASE,
        "category": "safety",
        "match_type": "keyword",
        "patterns": ["test"],
        "active": False,
    })
    assert rule.active is False


def test_eval_result_empty():
    result = EvalResult()
    assert result.fired == []
    assert result.actions == []
    assert result.fired_ids == []
    assert bool(result) is False


def test_eval_result_with_fired_rules():
    result = EvalResult()
    result.fired.append(FiredRule(
        rule_id="TEST-001",
        version="1.0.0",
        action={"type": "crisis_flag", "flag_id": "si_explicit"},
    ))
    assert len(result.actions) == 1
    assert result.actions[0]["flag_id"] == "si_explicit"
    assert result.fired_ids == ["TEST-001"]
    assert bool(result) is True
```

- [ ] **Step 2.2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_rules_schemas.py -v 2>&1 | head -10
```

Expected: `ImportError`

- [ ] **Step 2.3: Write `schemas.py`**

```python
# src/sage_poc/rules/schemas.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
from pydantic import BaseModel


class SafetyRule(BaseModel):
    rule_id: str
    version: str = "1.0.0"
    category: Literal["safety"]
    authored_by: str = "sage_clinics"
    approved_by: str | None = None
    effective_date: str
    active: bool = True
    description: str = ""
    match_type: Literal["keyword", "regex"]
    patterns: list[str]
    language: Literal["en", "ar", "any"] = "any"
    modifiers: list[str] = []
    action: dict


class CrisisContentRule(BaseModel):
    rule_id: str
    version: str = "1.0.0"
    category: Literal["crisis_content"]
    authored_by: str = "sage_clinics"
    approved_by: str | None = None
    effective_date: str
    active: bool = True
    description: str = ""
    locale: str
    crisis_level: Literal["acute", "extended"]
    action: dict


class CulturalRule(BaseModel):
    rule_id: str
    version: str = "1.0.0"
    category: Literal["cultural"]
    authored_by: str = "sage_clinics"
    approved_by: str | None = None
    effective_date: str
    active: bool = True
    description: str = ""
    trigger_keywords: list[str]
    language: Literal["en", "ar", "any"] = "any"
    action: dict


class PromptInjectionRule(BaseModel):
    rule_id: str
    version: str = "1.0.0"
    category: Literal["prompt_injection"]
    authored_by: str = "sage_clinics"
    approved_by: str | None = None
    effective_date: str
    active: bool = True
    description: str = ""
    trigger_type: Literal[
        "keyword_match", "flag_present", "intent_match", "secondary_intent_present"
    ]
    trigger_value: str | None = None
    trigger_keywords: list[str] = []
    action: dict


@dataclass
class FiredRule:
    rule_id: str
    version: str
    action: dict


@dataclass
class EvalResult:
    fired: list[FiredRule] = field(default_factory=list)

    @property
    def actions(self) -> list[dict]:
        return [r.action for r in self.fired]

    @property
    def fired_ids(self) -> list[str]:
        return [r.rule_id for r in self.fired]

    def __bool__(self) -> bool:
        return len(self.fired) > 0
```

- [ ] **Step 2.4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_rules_schemas.py -v
```

Expected: `10 passed`

- [ ] **Step 2.5: Commit**

```bash
git add src/sage_poc/rules/schemas.py tests/test_rules_schemas.py
git commit -m "feat(rules): add rule schemas and EvalResult types"
```

---

## Task 3: File-based loader — `loader.py`

**Files:**
- Create: `src/sage_poc/rules/loader.py`
- Test: `tests/test_rules_engine.py` (loader section added in Task 4)

- [ ] **Step 3.1: Write `loader.py`**

```python
# src/sage_poc/rules/loader.py
import json
from pathlib import Path
from sage_poc.rules.schemas import (
    SafetyRule, CrisisContentRule, CulturalRule, PromptInjectionRule,
)

_RULE_MODELS: dict[str, type] = {
    "safety": SafetyRule,
    "crisis_content": CrisisContentRule,
    "cultural": CulturalRule,
    "prompt_injection": PromptInjectionRule,
}

_DATA_DIR = Path(__file__).parent / "data"

# Module-level cache — populated on first get_rules() call per category.
# Clear with reload_all() in tests or after hot-editing JSON files.
_cache: dict[str, list] = {}


def load_rules(category: str) -> list:
    """Read all active rules for *category* from JSON files in data/{category}/.
    Files are loaded in alphabetical order. Within each file, rules are appended
    in the order they appear in the "rules" array.
    """
    category_dir = _DATA_DIR / category
    if not category_dir.exists():
        return []

    model_cls = _RULE_MODELS.get(category)
    if model_cls is None:
        raise ValueError(f"Unknown rule category: {category!r}. "
                         f"Known categories: {list(_RULE_MODELS)}")

    rules = []
    for json_file in sorted(category_dir.glob("*.json")):
        raw = json.loads(json_file.read_text(encoding="utf-8"))
        for rule_data in raw.get("rules", []):
            rule = model_cls.model_validate(rule_data)
            if rule.active:
                rules.append(rule)
    return rules


def get_rules(category: str) -> list:
    """Return cached rules for *category*, loading from disk on first access."""
    if category not in _cache:
        _cache[category] = load_rules(category)
    return _cache[category]


def reload_all() -> None:
    """Invalidate the rule cache. Use in tests after writing fixture files,
    or after hot-editing JSON rule documents in development."""
    _cache.clear()
```

- [ ] **Step 3.2: Commit**

```bash
git add src/sage_poc/rules/loader.py
git commit -m "feat(rules): add file-based JSON loader with module-level cache"
```

---

## Task 4: Evaluation engine — `engine.py`

**Files:**
- Create: `src/sage_poc/rules/engine.py`
- Create: `tests/test_rules_engine.py`
- Modify: `src/sage_poc/rules/__init__.py`

- [ ] **Step 4.1: Write failing engine tests (synthetic rules, no file I/O)**

```python
# tests/test_rules_engine.py
import pytest
from unittest.mock import patch
from sage_poc.rules.schemas import SafetyRule, CulturalRule, PromptInjectionRule, EvalResult
from sage_poc.rules import engine


_BASE = {
    "version": "1.0.0", "authored_by": "test",
    "effective_date": "2026-05-21", "active": True,
}


# ── Safety evaluator ────────────────────────────────────────────────────────

def _safety_rule(rule_id, patterns, language="en", modifiers=None):
    return SafetyRule(**{
        **_BASE,
        "rule_id": rule_id,
        "category": "safety",
        "match_type": "keyword",
        "patterns": patterns,
        "language": language,
        "modifiers": modifiers or [],
        "action": {"type": "crisis_flag", "flag_id": "si_test"},
    })


def test_safety_keyword_match_fires():
    rules = [_safety_rule("T1", ["want to die"])]
    ctx = {"text_en": "I want to die", "text_ar": None, "language": "en"}
    result = engine._eval_safety(rules, ctx)
    assert "T1" in result.fired_ids


def test_safety_keyword_no_match():
    rules = [_safety_rule("T1", ["want to die"])]
    ctx = {"text_en": "I want to live fully", "text_ar": None, "language": "en"}
    result = engine._eval_safety(rules, ctx)
    assert result.fired == []


def test_safety_negation_suppresses_match():
    rules = [_safety_rule("T1", ["want to die"], modifiers=["negation_check"])]
    ctx = {"text_en": "I don't want to die", "text_ar": None, "language": "en"}
    result = engine._eval_safety(rules, ctx)
    assert result.fired == []


def test_safety_negation_does_not_suppress_without_modifier():
    rules = [_safety_rule("T1", ["want to die"], modifiers=[])]
    ctx = {"text_en": "I don't want to die", "text_ar": None, "language": "en"}
    result = engine._eval_safety(rules, ctx)
    # No negation_check modifier → still fires (keyword substring present)
    assert "T1" in result.fired_ids


def test_safety_arabic_rule_matches_normalized_text():
    # Arabic rule with alef-hamza pattern; input has alef-hamza variant
    rules = [_safety_rule("T2", ["ابي اموت"], language="ar", modifiers=[])]
    # Input: أبي أموت (with alef-hamza-above) — normalized to ابي اموت
    ctx = {"text_en": "want to die", "text_ar": "أبي أموت", "language": "ar"}
    result = engine._eval_safety(rules, ctx)
    assert "T2" in result.fired_ids


def test_safety_arabic_rule_matches_diacritic_variant():
    # Input has full harakat; rule pattern has no harakat
    rules = [_safety_rule("T2", ["ابي اموت"], language="ar")]
    ctx = {"text_en": "i want to die", "text_ar": "أَبِي أَمُوتُ", "language": "ar"}
    result = engine._eval_safety(rules, ctx)
    assert "T2" in result.fired_ids


def test_safety_multiple_rules_all_evaluated():
    rules = [
        _safety_rule("T1", ["want to die"]),
        _safety_rule("T2", ["no reason to live"]),
    ]
    ctx = {"text_en": "I want to die, there is no reason to live", "language": "en"}
    result = engine._eval_safety(rules, ctx)
    assert "T1" in result.fired_ids
    assert "T2" in result.fired_ids


def test_safety_inactive_rule_skipped():
    rule = SafetyRule(**{
        **_BASE,
        "rule_id": "T1",
        "category": "safety",
        "match_type": "keyword",
        "patterns": ["want to die"],
        "active": False,
        "action": {"type": "crisis_flag", "flag_id": "si_test"},
    })
    # loader only returns active rules, but test engine directly with inactive rule
    rules = [rule]
    ctx = {"text_en": "I want to die", "language": "en"}
    # The engine receives rules from loader; loader filters inactive. 
    # Here we test the engine with the rule passed in — engine trusts what loader gives it.
    result = engine._eval_safety(rules, ctx)
    assert "T1" in result.fired_ids  # engine does NOT filter; loader does


# ── Cultural evaluator ───────────────────────────────────────────────────────

def _cultural_rule(rule_id, keywords, language="any"):
    return CulturalRule(**{
        **_BASE,
        "rule_id": rule_id,
        "category": "cultural",
        "trigger_keywords": keywords,
        "language": language,
        "action": {"type": "prompt_injection", "target": "system", "content": f"[{rule_id}]"},
    })


def test_cultural_rule_fires_on_keyword():
    rules = [_cultural_rule("C1", ["allah", "faith"])]
    ctx = {"text": "I feel distant from my faith", "language": "en"}
    result = engine._eval_cultural(rules, ctx)
    assert "C1" in result.fired_ids


def test_cultural_rule_no_match():
    rules = [_cultural_rule("C1", ["allah", "faith"])]
    ctx = {"text": "I feel anxious about my exam", "language": "en"}
    result = engine._eval_cultural(rules, ctx)
    assert result.fired == []


def test_cultural_rule_language_filter():
    rules = [_cultural_rule("C1", ["الله"], language="ar")]
    ctx = {"text": "الله يساعدني", "language": "ar"}
    result = engine._eval_cultural(rules, ctx)
    assert "C1" in result.fired_ids


def test_cultural_rule_language_mismatch_does_not_fire():
    rules = [_cultural_rule("C1", ["الله"], language="ar")]
    ctx = {"text": "الله يساعدني", "language": "en"}  # language="en" but rule requires "ar"
    result = engine._eval_cultural(rules, ctx)
    assert result.fired == []


def test_cultural_accumulates_multiple_matches():
    rules = [
        _cultural_rule("C1", ["allah"]),
        _cultural_rule("C2", ["family"]),
    ]
    ctx = {"text": "My family and my faith in allah help me", "language": "en"}
    result = engine._eval_cultural(rules, ctx)
    assert "C1" in result.fired_ids
    assert "C2" in result.fired_ids


# ── Prompt injection evaluator ───────────────────────────────────────────────

def _pi_rule(rule_id, trigger_type, trigger_value=None, trigger_keywords=None):
    return PromptInjectionRule(**{
        **_BASE,
        "rule_id": rule_id,
        "category": "prompt_injection",
        "trigger_type": trigger_type,
        "trigger_value": trigger_value,
        "trigger_keywords": trigger_keywords or [],
        "action": {"type": "inject", "target": "system", "content": f"[{rule_id}]"},
    })


def test_pi_flag_present_fires():
    rules = [_pi_rule("P1", "flag_present", trigger_value="substance_use")]
    ctx = {"clinical_flags": ["substance_use"], "primary_intent": None, "secondary_intent": None, "text": ""}
    result = engine._eval_prompt_injection(rules, ctx)
    assert "P1" in result.fired_ids


def test_pi_flag_present_does_not_fire_when_absent():
    rules = [_pi_rule("P1", "flag_present", trigger_value="substance_use")]
    ctx = {"clinical_flags": ["trauma_indicator"], "primary_intent": None, "secondary_intent": None, "text": ""}
    result = engine._eval_prompt_injection(rules, ctx)
    assert result.fired == []


def test_pi_secondary_intent_present_fires():
    rules = [_pi_rule("P2", "secondary_intent_present")]
    ctx = {"clinical_flags": [], "primary_intent": "new_skill", "secondary_intent": "info_request", "text": ""}
    result = engine._eval_prompt_injection(rules, ctx)
    assert "P2" in result.fired_ids


def test_pi_secondary_intent_present_does_not_fire_when_none():
    rules = [_pi_rule("P2", "secondary_intent_present")]
    ctx = {"clinical_flags": [], "primary_intent": "new_skill", "secondary_intent": None, "text": ""}
    result = engine._eval_prompt_injection(rules, ctx)
    assert result.fired == []


def test_pi_intent_match_fires_on_primary():
    rules = [_pi_rule("P3", "intent_match", trigger_value="info_request")]
    ctx = {"clinical_flags": [], "primary_intent": "info_request", "secondary_intent": None, "text": ""}
    result = engine._eval_prompt_injection(rules, ctx)
    assert "P3" in result.fired_ids


def test_pi_intent_match_fires_on_secondary():
    rules = [_pi_rule("P3", "intent_match", trigger_value="info_request")]
    ctx = {"clinical_flags": [], "primary_intent": "new_skill", "secondary_intent": "info_request", "text": ""}
    result = engine._eval_prompt_injection(rules, ctx)
    assert "P3" in result.fired_ids


# ── Top-level evaluate() dispatch ───────────────────────────────────────────

def test_evaluate_dispatches_to_safety(tmp_path, monkeypatch):
    """evaluate() with mocked loader calls _eval_safety."""
    monkeypatch.setattr("sage_poc.rules.engine.get_rules", lambda cat: [
        _safety_rule("T1", ["want to die"]) if cat == "safety" else []
    ])
    result = engine.evaluate("safety", {"text_en": "I want to die", "language": "en"})
    assert "T1" in result.fired_ids


def test_evaluate_raises_on_unknown_category():
    with pytest.raises(ValueError, match="Unknown rule category"):
        engine.evaluate("nonexistent", {})
```

- [ ] **Step 4.2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_rules_engine.py -v 2>&1 | head -20
```

Expected: `ImportError: cannot import name 'engine'`

- [ ] **Step 4.3: Write `engine.py`**

```python
# src/sage_poc/rules/engine.py
from __future__ import annotations
import re
from sage_poc.rules.schemas import (
    SafetyRule, CrisisContentRule, CulturalRule, PromptInjectionRule,
    EvalResult, FiredRule,
)
from sage_poc.rules.loader import get_rules
from sage_poc.rules.normalize import normalize_text, normalize_arabic

# Negation suppression: words within this many tokens before a keyword cancel the match.
_NEGATION_WORDS = frozenset([
    "don't", "dont", "do not", "not", "never", "no", "cannot", "can't", "cant",
    "لا", "ما", "مو", "مش", "مب", "ليس",
])
_NEGATION_WINDOW = 6  # tokens


def _has_negation(text_lower: str, match_start: int) -> bool:
    """True if any negation word appears in the _NEGATION_WINDOW tokens before match_start."""
    prefix_tokens = text_lower[:match_start].split()
    window = prefix_tokens[-_NEGATION_WINDOW:]
    return any(neg in window for neg in _NEGATION_WORDS)


def _eval_safety(rules: list[SafetyRule], context: dict) -> EvalResult:
    """
    Evaluate safety rules. All matching rules fire (OR-semantics for crisis detection,
    accumulate-semantics for clinical flags — the calling node splits by action.type).

    context keys:
      text_en (str)         — English text (raw message if English; translated if Arabic)
      text_ar (str | None)  — Original Arabic text (None if message was English)
      language (str)        — "en" | "ar"
    """
    text_en = context.get("text_en", "")
    text_ar = context.get("text_ar") or ""
    language = context.get("language", "en")

    norm_en = normalize_text(text_en)
    norm_ar = normalize_arabic(text_ar) if text_ar else ""

    result = EvalResult()

    for rule in rules:
        lang = rule.language
        if lang == "ar":
            text_to_check = norm_ar
        elif lang == "en":
            text_to_check = norm_en
        else:  # "any" — check English path (already translated)
            text_to_check = norm_en

        if not text_to_check:
            continue

        for pattern in rule.patterns:
            pattern_norm = (normalize_arabic(pattern) if lang == "ar"
                            else normalize_text(pattern))
            idx = text_to_check.find(pattern_norm)
            if idx == -1:
                continue
            if "negation_check" in rule.modifiers and _has_negation(text_to_check, idx):
                continue
            # Pattern matched and passed modifiers — fire the rule
            result.fired.append(FiredRule(
                rule_id=rule.rule_id,
                version=rule.version,
                action=rule.action,
            ))
            break  # one pattern match per rule is enough

    return result


def _eval_crisis_content(rules: list[CrisisContentRule], context: dict) -> EvalResult:
    """
    Select the crisis content rule matching locale + crisis_level.
    Returns at most one fired rule (locale-select strategy: first match wins).

    context keys:
      language (str)      — "en" | "ar"
      crisis_level (str)  — "acute" | "extended"
    """
    language = context.get("language", "en")
    crisis_level = context.get("crisis_level", "acute")
    locale = f"{language}_uae"

    result = EvalResult()
    for rule in rules:
        if rule.locale == locale and rule.crisis_level == crisis_level:
            result.fired.append(FiredRule(
                rule_id=rule.rule_id,
                version=rule.version,
                action=rule.action,
            ))
            break  # locale-select: first match wins

    return result


def _eval_cultural(rules: list[CulturalRule], context: dict) -> EvalResult:
    """
    Accumulate all cultural rules whose trigger_keywords appear in the message text.

    context keys:
      text (str)      — user message (English)
      language (str)  — "en" | "ar"
    """
    text_lower = normalize_text(context.get("text", ""))
    language = context.get("language", "en")

    result = EvalResult()
    for rule in rules:
        if rule.language not in ("any", language):
            continue
        if any(kw.lower() in text_lower for kw in rule.trigger_keywords):
            result.fired.append(FiredRule(
                rule_id=rule.rule_id,
                version=rule.version,
                action=rule.action,
            ))

    return result


def _eval_prompt_injection(rules: list[PromptInjectionRule], context: dict) -> EvalResult:
    """
    Accumulate all prompt injection rules whose trigger condition matches.

    context keys:
      text (str)                      — user message (English)
      clinical_flags (list[str])      — e.g. ["substance_use"]
      primary_intent (str | None)
      secondary_intent (str | None)
    """
    text_lower = normalize_text(context.get("text", ""))
    clinical_flags: list[str] = context.get("clinical_flags", [])
    primary_intent: str | None = context.get("primary_intent")
    secondary_intent: str | None = context.get("secondary_intent")

    result = EvalResult()
    for rule in rules:
        fired = False
        if rule.trigger_type == "keyword_match":
            fired = any(kw.lower() in text_lower for kw in rule.trigger_keywords)
        elif rule.trigger_type == "flag_present":
            fired = rule.trigger_value in clinical_flags
        elif rule.trigger_type == "intent_match":
            fired = rule.trigger_value in (primary_intent, secondary_intent)
        elif rule.trigger_type == "secondary_intent_present":
            fired = secondary_intent is not None

        if fired:
            result.fired.append(FiredRule(
                rule_id=rule.rule_id,
                version=rule.version,
                action=rule.action,
            ))

    return result


_EVAL_DISPATCH = {
    "safety": _eval_safety,
    "crisis_content": _eval_crisis_content,
    "cultural": _eval_cultural,
    "prompt_injection": _eval_prompt_injection,
}


def evaluate(category: str, context: dict) -> EvalResult:
    """
    Evaluate all active rules in *category* against *context*.
    Returns EvalResult containing every fired rule and its action dict.

    The engine is stateless — it never reads or writes SageState.
    Calling nodes are responsible for reading state before calling evaluate()
    and writing the results back to state after receiving EvalResult.
    """
    rules = get_rules(category)
    eval_fn = _EVAL_DISPATCH.get(category)
    if eval_fn is None:
        raise ValueError(
            f"Unknown rule category: {category!r}. "
            f"Known categories: {list(_EVAL_DISPATCH)}"
        )
    return eval_fn(rules, context)
```

- [ ] **Step 4.4: Update `__init__.py`**

```python
# src/sage_poc/rules/__init__.py
from sage_poc.rules.engine import evaluate
from sage_poc.rules.loader import reload_all

__all__ = ["evaluate", "reload_all"]
```

- [ ] **Step 4.5: Run engine tests**

```bash
uv run pytest tests/test_rules_engine.py -v
```

Expected: `24 passed`

- [ ] **Step 4.6: Commit**

```bash
git add src/sage_poc/rules/engine.py src/sage_poc/rules/__init__.py tests/test_rules_engine.py
git commit -m "feat(rules): add stateless evaluation engine with safety/cultural/prompt-injection/crisis-content dispatch"
```

---

## Task 5: Safety rule JSON data files

**Files:**
- Create: `src/sage_poc/rules/data/safety/crisis_keywords.json`
- Create: `src/sage_poc/rules/data/safety/passive_si_patterns.json`
- Create: `src/sage_poc/rules/data/safety/clinical_flag_patterns.json`
- Create: `tests/test_rules_safety.py`

- [ ] **Step 5.1: Write failing safety data tests**

```python
# tests/test_rules_safety.py
import pytest
from sage_poc.rules import engine, reload_all
from sage_poc.rules.loader import reload_all


@pytest.fixture(autouse=True)
def fresh_cache():
    reload_all()
    yield
    reload_all()


# ── Explicit SI (English) ────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "I want to die",
    "thinking about ending my life",
    "I've been thinking of ending it",
    "I am suicidal",
    "I want to kill myself",
    "better off dead",
    "I don't want to be alive anymore",
])
def test_explicit_si_english_triggers_crisis(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for: {text!r}"


# ── Passive SI (English) ─────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "nothing matters anymore",
    "everyone would be better off without me",
    "there's no point in living",
    "I wish I could disappear",
    "I have no reason to live",
])
def test_passive_si_english_triggers_crisis(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for passive SI: {text!r}"


# ── Negation suppression (false positive prevention) ────────────────────────

@pytest.mark.parametrize("text", [
    "I don't want to die",
    "I never want to die",
    "no I don't want to end my life",
    "I do not want to kill myself",
])
def test_negation_suppresses_false_positive(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert not crisis_actions, f"Expected NO crisis flag for negated: {text!r}"


# ── ZWSP obfuscation bypass ──────────────────────────────────────────────────

def test_zwsp_bypass_still_detected():
    text = "want​to die"  # ZWSP injected between 'want' and 'to die'
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    assert any(a.get("type") == "crisis_flag" for a in result.actions)


# ── Arabic explicit SI ───────────────────────────────────────────────────────

@pytest.mark.parametrize("arabic_text", [
    "أبي أموت",          # Gulf alef-hamza-above
    "ابي اموت",          # bare alef (same after normalization)
    "أريد الموت",        # MSA
    "أبغى أختفي",        # Gulf: want to disappear
    "ابغى اختفي",        # bare alef variant
])
def test_arabic_explicit_si_triggers_crisis(arabic_text):
    result = engine.evaluate("safety", {
        "text_en": "i want to die",
        "text_ar": arabic_text,
        "language": "ar",
    })
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for Arabic: {arabic_text!r}"


# ── Arabic passive SI ────────────────────────────────────────────────────────

@pytest.mark.parametrize("arabic_text", [
    "نفسي تعبت",           # "my soul is tired"
    "ما عاد قادر",         # "I can no longer cope"
    "مافي فايدة",          # Gulf: "no use/no point"
    "ياريت انام ولا اصحى", # "I wish I'd sleep and not wake up"
])
def test_arabic_passive_si_triggers_crisis(arabic_text):
    result = engine.evaluate("safety", {
        "text_en": "nothing matters",
        "text_ar": arabic_text,
        "language": "ar",
    })
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for Arabic passive SI: {arabic_text!r}"


# ── Clinical flags ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected_flag", [
    ("I've been drinking a lot to cope", "substance_use"),
    ("I'm on antidepressants", "medication_mention"),
    ("I was assaulted last year", "trauma_indicator"),
    ("I've been binge eating and purging", "eating_concern"),
])
def test_clinical_flag_detection(text, expected_flag):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    flag_ids = [a["flag_id"] for a in result.actions if a.get("type") == "clinical_flag"]
    assert expected_flag in flag_ids, f"Expected {expected_flag!r} for: {text!r}"


# ── No false positives on safe messages ─────────────────────────────────────

@pytest.mark.parametrize("text", [
    "I feel anxious today",
    "I'm struggling with work",
    "could kill for a good coffee",
    "that presentation killed me",
    "I'm dying of laughter",
])
def test_safe_message_no_crisis_flag(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert not crisis_actions, f"Expected NO crisis flag for: {text!r}"
```

- [ ] **Step 5.2: Run to confirm failures**

```bash
uv run pytest tests/test_rules_safety.py -v 2>&1 | head -20
```

Expected: tests fail because data directories are empty.

- [ ] **Step 5.3: Create `crisis_keywords.json`**

```json
{
  "category": "safety",
  "rules": [
    {
      "rule_id": "SK-EN-001",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Core English explicit SI keywords",
      "category": "safety",
      "match_type": "keyword",
      "patterns": [
        "kill myself", "want to die", "end my life", "suicide", "suicidal",
        "hurt myself", "self-harm", "cut myself", "overdose",
        "better off dead", "can't go on", "not worth living",
        "want to disappear", "don't want to be here", "thinking of ending it",
        "i'm a burden", "don't want to be alive", "end it all",
        "no reason to live"
      ],
      "language": "en",
      "modifiers": ["negation_check"],
      "action": {"type": "crisis_flag", "flag_id": "si_explicit"}
    },
    {
      "rule_id": "SK-AZ-001",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Arabizi / code-switching explicit SI",
      "category": "safety",
      "match_type": "keyword",
      "patterns": [
        "want to mat",
        "wallah i want to die",
        "abi amoot",
        "khalas i give up"
      ],
      "language": "en",
      "modifiers": ["negation_check"],
      "action": {"type": "crisis_flag", "flag_id": "si_explicit"}
    },
    {
      "rule_id": "SK-AR-001",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Arabic MSA and Gulf explicit SI (alef-normalized patterns)",
      "category": "safety",
      "match_type": "keyword",
      "patterns": [
        "اريد الموت", "اريد ان اموت", "انتحار", "انهي حياتي", "اوذي نفسي",
        "افكر في الانتحار", "اريد ان اقتل نفسي", "اتمنى الموت",
        "ابي اموت", "ابغى اموت", "ودي اموت",
        "ابي انهي حياتي", "ابغى انهي حياتي",
        "ابي اخلص من حياتي",
        "ابغى اختفي",
        "ابي اجرح نفسي", "ابغى اجرح نفسي",
        "بدي اقتل حالي"
      ],
      "language": "ar",
      "modifiers": [],
      "action": {"type": "crisis_flag", "flag_id": "si_explicit"}
    }
  ]
}
```

> **Note on Arabic patterns:** All patterns are written in post-normalization form (bare alef, no diacritics). The engine normalizes both the pattern and the input via `normalize_arabic()` before matching, so authoring in the normalized form eliminates ambiguity.

- [ ] **Step 5.4: Create `passive_si_patterns.json`**

```json
{
  "category": "safety",
  "rules": [
    {
      "rule_id": "SK-EN-002",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "English passive SI and veiled ideation",
      "category": "safety",
      "match_type": "keyword",
      "patterns": [
        "nothing matters anymore",
        "better off without me",
        "everyone would be better off",
        "no point in living",
        "wish i could disappear",
        "no reason to live",
        "i'm a burden"
      ],
      "language": "en",
      "modifiers": ["negation_check"],
      "action": {"type": "crisis_flag", "flag_id": "si_passive"}
    },
    {
      "rule_id": "SK-AR-002",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Arabic passive SI and escape ideation (Gulf dialect, alef-normalized)",
      "category": "safety",
      "match_type": "keyword",
      "patterns": [
        "ياريت انام ولا اصحى",
        "نفسي تعبت",
        "ما اقدر اكمل",
        "ما عندي سبب اعيش",
        "مافي فايدة",
        "ما في فايدة من اي شي",
        "حياتي خلصت",
        "الحياة ما تسوى",
        "ما عاد قادر"
      ],
      "language": "ar",
      "modifiers": [],
      "action": {"type": "crisis_flag", "flag_id": "si_passive"}
    }
  ]
}
```

- [ ] **Step 5.5: Create `clinical_flag_patterns.json`**

```json
{
  "category": "safety",
  "rules": [
    {
      "rule_id": "CF-001",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Substance use detection",
      "category": "safety",
      "match_type": "keyword",
      "patterns": [
        "drinking", "drunk", "alcohol", "alcoholism", "liquor", "beer", "wine",
        "drugs", "drug use", "cocaine", "heroin", "marijuana", "weed",
        "using pills", "numb the pain", "cope with drink",
        "كحول", "مخدرات", "حبوب مخدرة", "مدمن"
      ],
      "language": "any",
      "modifiers": [],
      "action": {"type": "clinical_flag", "flag_id": "substance_use"}
    },
    {
      "rule_id": "CF-002",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Trauma indicator detection",
      "category": "safety",
      "match_type": "keyword",
      "patterns": [
        "abuse", "abused", "assault", "assaulted", "attacked", "violence",
        "hurt me", "hit me", "rape", "molested", "trauma",
        "إساءة", "اعتداء", "عنف"
      ],
      "language": "any",
      "modifiers": [],
      "action": {"type": "clinical_flag", "flag_id": "trauma_indicator"}
    },
    {
      "rule_id": "CF-003",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Eating concern detection",
      "category": "safety",
      "match_type": "keyword",
      "patterns": [
        "purging", "binge eating", "starving myself", "not eating",
        "eating disorder", "anorexia", "bulimia",
        "لا اكل", "اتجوع"
      ],
      "language": "any",
      "modifiers": [],
      "action": {"type": "clinical_flag", "flag_id": "eating_concern"}
    },
    {
      "rule_id": "CF-004",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Medication mention detection",
      "category": "safety",
      "match_type": "keyword",
      "patterns": [
        "medication", "antidepressant", "dosage", "prescribed", "prescription",
        "دواء", "مضادات الاكتئاب", "جرعة"
      ],
      "language": "any",
      "modifiers": [],
      "action": {"type": "clinical_flag", "flag_id": "medication_mention"}
    }
  ]
}
```

- [ ] **Step 5.6: Run safety data tests**

```bash
uv run pytest tests/test_rules_safety.py -v
```

Expected: all pass. If any Arabic test fails, verify the input's alef variant is covered. Add the normalized form directly to the JSON `patterns` array.

- [ ] **Step 5.7: Commit**

```bash
git add src/sage_poc/rules/data/safety/ tests/test_rules_safety.py
git commit -m "feat(rules): add safety rule JSON data — crisis keywords, passive SI, clinical flags"
```

---

## Task 6: Migrate `safety_check_node` to Rules Service

**Files:**
- Modify: `src/sage_poc/nodes/safety_check.py`
- Test: `tests/test_rules_integration.py` (safety section)

- [ ] **Step 6.1: Write integration tests for the migrated node**

```python
# tests/test_rules_integration.py
import pytest
from unittest.mock import patch
from sage_poc.rules.loader import reload_all
from sage_poc.nodes.safety_check import safety_check_node


@pytest.fixture(autouse=True)
def fresh_rules():
    reload_all()
    yield
    reload_all()


def _state(raw_message, clinical_flags=None):
    return {
        "raw_message": raw_message,
        "detected_language": "en",
        "message_en": raw_message,
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": clinical_flags or [],
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 1.0,
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "skill_match_method": None,
        "semantic_score": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
    }


# ── Crisis detection via Rules Service ──────────────────────────────────────

def test_safety_check_node_crisis_sets_is_safe_false():
    result = safety_check_node(_state("I want to die"))
    assert result["is_safe"] is False
    assert len(result["crisis_flags"]) > 0


def test_safety_check_node_safe_message():
    result = safety_check_node(_state("I feel anxious today"))
    assert result["is_safe"] is True
    assert result["crisis_flags"] == []


def test_safety_check_node_negation_no_crisis():
    result = safety_check_node(_state("I don't want to die"))
    assert result["is_safe"] is True, "Negation should suppress crisis flag"


def test_safety_check_node_clinical_flag_substance():
    result = safety_check_node(_state("I've been drinking to cope"))
    assert "substance_use" in result["clinical_flags"]


# ── Clinical flag carry-forward ──────────────────────────────────────────────

def test_clinical_flags_carry_forward_across_turns():
    """Flags from a prior turn are merged, not erased, by the next turn."""
    # Turn 2: neutral message, but state carries substance_use from turn 1
    state = _state("I'm feeling better today", clinical_flags=["substance_use"])
    result = safety_check_node(state)
    assert "substance_use" in result["clinical_flags"], (
        "substance_use flag from prior turn must persist into turn 2"
    )


def test_new_clinical_flag_merges_with_existing():
    """New flag from current turn merges with flag persisted from prior turn."""
    state = _state("I was assaulted and I drink too much", clinical_flags=["substance_use"])
    result = safety_check_node(state)
    assert "substance_use" in result["clinical_flags"]
    assert "trauma_indicator" in result["clinical_flags"]


def test_no_duplicate_flags():
    """If the same flag fires again, it appears once, not twice."""
    state = _state("I drink a lot", clinical_flags=["substance_use"])
    result = safety_check_node(state)
    assert result["clinical_flags"].count("substance_use") == 1
```

- [ ] **Step 6.2: Run to confirm failures**

```bash
uv run pytest tests/test_rules_integration.py -v 2>&1 | head -20
```

Expected: most pass (existing node still works) except carry-forward tests which currently fail.

- [ ] **Step 6.3: Rewrite `safety_check.py`**

Replace the entire file:

```python
# src/sage_poc/nodes/safety_check.py
from sage_poc.state import SageState
from sage_poc.language import detect_language, translate_to_english
from sage_poc.rules import engine as rules_engine


def safety_check_node(state: SageState) -> dict:
    raw = state["raw_message"]
    lang = detect_language(raw)

    if lang == "ar":
        message_en = translate_to_english(raw)
        text_ar = raw
    else:
        message_en = raw
        text_ar = None

    # Evaluate safety rules (normalization happens inside the engine)
    safety_result = rules_engine.evaluate("safety", {
        "text_en": message_en,
        "text_ar": text_ar,
        "language": lang,
    })

    # Split actions by type
    new_crisis_flags = [
        a["flag_id"] for a in safety_result.actions if a.get("type") == "crisis_flag"
    ]
    new_clinical_flags = [
        a["flag_id"] for a in safety_result.actions if a.get("type") == "clinical_flag"
    ]

    # Carry forward clinical flags from prior turns (set union — flags don't reset)
    persisted = state.get("clinical_flags", [])
    all_clinical = list(set(new_clinical_flags + persisted))

    return {
        "detected_language": lang,
        "message_en": message_en,
        "is_safe": len(new_crisis_flags) == 0,
        "crisis_flags": new_crisis_flags,
        "clinical_flags": all_clinical,
        "path": state["path"] + ["safety_check"],
    }
```

- [ ] **Step 6.4: Run integration tests**

```bash
uv run pytest tests/test_rules_integration.py -v
```

Expected: all pass.

- [ ] **Step 6.5: Run the full existing test suite to confirm no regressions**

```bash
uv run pytest tests/ -v --ignore=tests/test_rules_normalize.py \
  --ignore=tests/test_rules_schemas.py \
  --ignore=tests/test_rules_engine.py \
  --ignore=tests/test_rules_safety.py \
  --ignore=tests/test_rules_integration.py
```

Expected: 211 passed (all prior tests green).

- [ ] **Step 6.6: Commit**

```bash
git add src/sage_poc/nodes/safety_check.py tests/test_rules_integration.py
git commit -m "feat(rules): migrate safety_check_node to Rules Service; add clinical flag carry-forward"
```

---

## Task 7: Crisis content JSON data files + `_crisis_response_node` migration

**Files:**
- Create: `src/sage_poc/rules/data/crisis_content/en_uae.json`
- Create: `src/sage_poc/rules/data/crisis_content/ar_uae.json`
- Modify: `src/sage_poc/graph.py`
- Modify: `src/sage_poc/state.py`

- [ ] **Step 7.1: Create `en_uae.json`**

```json
{
  "category": "crisis_content",
  "rules": [
    {
      "rule_id": "CC-EN-001",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "English acute crisis response for UAE",
      "category": "crisis_content",
      "locale": "en_uae",
      "crisis_level": "acute",
      "action": {
        "type": "crisis_response",
        "response_text": "I'm really concerned about what you've shared. Please reach out to a crisis line now — in the UAE: 800 4673 (800-HOPE), or emergency: 999. You don't have to face this alone.",
        "resources": [
          {"name": "National Lifeline (Estijaba)", "number": "800-4673", "available": "24/7"},
          {"name": "Emergency Services", "number": "999", "available": "24/7"}
        ]
      }
    },
    {
      "rule_id": "CC-EN-002",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "English extended crisis resources for proactive queries",
      "category": "crisis_content",
      "locale": "en_uae",
      "crisis_level": "extended",
      "action": {
        "type": "crisis_response",
        "response_text": "Here are crisis and mental health resources in the UAE:\n- CDA Mental Health Support: 800-4888\n- National Lifeline (Estijaba): 800-HOPE (800-4673)\n- Emergency Services: 999\n- Al Amal Psychiatric Hospital: in-person psychiatric support\n- Lighthouse Arabia, Camali Clinic, American Center for Psychiatry and Neurology: therapy in Dubai\n\nIf you're in immediate danger, please call 999 or go to your nearest emergency room.",
        "resources": [
          {"name": "CDA Mental Health Support", "number": "800-4888"},
          {"name": "National Lifeline (Estijaba)", "number": "800-HOPE (800-4673)", "available": "24/7"},
          {"name": "Emergency Services", "number": "999", "available": "24/7"},
          {"name": "Al Amal Psychiatric Hospital", "type": "in-person"},
          {"name": "Lighthouse Arabia", "type": "therapy"},
          {"name": "Camali Clinic", "type": "therapy"},
          {"name": "American Center for Psychiatry and Neurology", "type": "therapy"}
        ]
      }
    }
  ]
}
```

- [ ] **Step 7.2: Create `ar_uae.json`**

```json
{
  "category": "crisis_content",
  "rules": [
    {
      "rule_id": "CC-AR-001",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Arabic acute crisis response for UAE",
      "category": "crisis_content",
      "locale": "ar_uae",
      "crisis_level": "acute",
      "action": {
        "type": "crisis_response",
        "response_text": "أنا مهتم جداً بسلامتك وبما شاركته معي. أرجوك تواصل مع خط دعم الصحة النفسية الآن — في الإمارات: 800 4673 (800-HOPE)، أو رقم الطوارئ: 999. أنت لست وحدك.",
        "resources": [
          {"name": "الخط الوطني (استجابة)", "number": "800-4673", "available": "24/7"},
          {"name": "خدمات الطوارئ", "number": "999", "available": "24/7"}
        ]
      }
    }
  ]
}
```

- [ ] **Step 7.3: Fix `gate_path` Literal in `state.py`**

In `src/sage_poc/state.py`, line 32, change:

```python
# Before
gate_path: Optional[Literal["standard", "scope_refusal", "jailbreak"]]
```

to:

```python
# After
gate_path: Optional[Literal["standard", "scope_refusal", "jailbreak", "crisis"]]
```

- [ ] **Step 7.4: Migrate `_crisis_response_node` in `graph.py`**

Replace lines 16–81 of `graph.py` (the three hardcoded constants + `_crisis_response_node`) with the following. The audit logging and history-append logic is unchanged; only the response text source changes:

```python
# REMOVE these three module-level constants (lines 16-45):
# CRISIS_RESPONSE = "..."
# CRISIS_RESPONSE_AR = "..."
# CRISIS_RESPONSE_EXTENDED = "..."

# Replace _crisis_response_node (lines 48-81) with:
def _crisis_response_node(state: SageState) -> dict:
    from sage_poc.rules import engine as rules_engine

    lang = state.get("detected_language", "en")

    # Load crisis response content from Rules Service
    crisis_result = rules_engine.evaluate("crisis_content", {
        "language": lang,
        "crisis_level": "acute",
    })

    if crisis_result.fired:
        response_text = crisis_result.fired[0].action["response_text"]
    else:
        # Hard fallback: should never fire if JSON files are present
        response_text = (
            "Please reach out for help now. UAE: 800 4673 (800-HOPE) or 999."
            if lang != "ar"
            else "أرجوك اتصل بـ 800 4673 أو 999 الآن."
        )

    path = state["path"] + ["crisis_response"]

    if AUDIT_LOG_ENABLED:
        audit = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "CRISIS_RESPONSE",
            "turn": state.get("turn_count"),
            "detected_language": lang,
            "crisis_flags": state.get("crisis_flags", []),
            "clinical_flags": state.get("clinical_flags", []),
            "active_skill_cleared": state.get("active_skill_id"),
            "crisis_content_rule": crisis_result.fired[0].rule_id if crisis_result.fired else "fallback",
        }
        print(f"\n[AUDIT:CRISIS] {json.dumps(audit, indent=2)}")

    history = state.get("conversation_history", []) + [
        {"role": "user", "content": state.get("message_en", state.get("raw_message", ""))},
        {"role": "assistant", "content": response_text},
    ]

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
    }
```

- [ ] **Step 7.5: Add crisis content tests to `test_rules_integration.py`**

Append to `tests/test_rules_integration.py`:

```python
# ── Crisis content ───────────────────────────────────────────────────────────
from sage_poc.rules import engine as rules_engine


def test_crisis_content_en_returns_uae_number():
    result = rules_engine.evaluate("crisis_content", {"language": "en", "crisis_level": "acute"})
    assert result.fired
    text = result.fired[0].action["response_text"]
    assert "800" in text and "4673" in text


def test_crisis_content_ar_returns_arabic_text():
    result = rules_engine.evaluate("crisis_content", {"language": "ar", "crisis_level": "acute"})
    assert result.fired
    text = result.fired[0].action["response_text"]
    assert "أنا" in text or "الإمارات" in text


def test_crisis_content_extended_returns_resource_list():
    result = rules_engine.evaluate("crisis_content", {"language": "en", "crisis_level": "extended"})
    assert result.fired
    resources = result.fired[0].action.get("resources", [])
    names = [r["name"] for r in resources]
    assert any("Estijaba" in n or "HOPE" in n for n in names)
```

- [ ] **Step 7.6: Run full test suite**

```bash
uv run pytest tests/ -v
```

Expected: all prior 211 + new rules tests pass. Zero regressions.

- [ ] **Step 7.7: Commit**

```bash
git add src/sage_poc/rules/data/crisis_content/ src/sage_poc/graph.py src/sage_poc/state.py tests/test_rules_integration.py
git commit -m "feat(rules): migrate crisis response to Rules Service; fix gate_path Literal; remove hardcoded CRISIS_RESPONSE strings"
```

---

## Task 8: Cultural and prompt injection JSON data files

**Files:**
- Create: `src/sage_poc/rules/data/cultural/islamic_vocabulary.json`
- Create: `src/sage_poc/rules/data/cultural/collectivist_framing.json`
- Create: `src/sage_poc/rules/data/prompt_injection/secondary_intent.json`
- Create: `src/sage_poc/rules/data/prompt_injection/clinical_flag_adaptations.json`

- [ ] **Step 8.1: Create `islamic_vocabulary.json`**

```json
{
  "category": "cultural",
  "rules": [
    {
      "rule_id": "CU-IS-001",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Inject Islamic framing when user expresses faith context",
      "category": "cultural",
      "trigger_keywords": [
        "god", "allah", "muslim", "islam", "islamic", "faith", "prayer", "pray",
        "religious", "spiritual", "religion", "quran", "haram", "halal", "inshallah",
        "الله", "الإسلام", "مسلم", "صلاة", "دين", "إيمان", "الحمد لله", "إن شاء الله"
      ],
      "language": "any",
      "action": {
        "type": "prompt_injection",
        "target": "system",
        "layer": "L2",
        "content": "ISLAMIC CULTURAL CONTEXT: The user is framing their experience through their faith. Use concepts of sabr (صبر — patient perseverance through trials), tawakkul (توكّل — trust in God), and ibtila (ابتلاء — viewing hardship as a test, not a punishment). Affirm their faith perspective; do NOT pathologize religious belief or suggest faith is the cause of distress. If they express spiritual guilt, explore it gently without reinforcing shame."
      }
    }
  ]
}
```

- [ ] **Step 8.2: Create `collectivist_framing.json`**

```json
{
  "category": "cultural",
  "rules": [
    {
      "rule_id": "CU-CO-001",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Inject collectivist framing when family or duty context is detected",
      "category": "cultural",
      "trigger_keywords": [
        "family", "parents", "mother", "father", "brother", "sister", "husband", "wife",
        "expectation", "expectations", "duty", "obligation", "pressure", "honor", "shame",
        "عائلة", "أهل", "والدين", "أم", "أب", "أخ", "أخت", "واجب", "التزام", "شرف", "عيب"
      ],
      "language": "any",
      "action": {
        "type": "prompt_injection",
        "target": "system",
        "layer": "L2",
        "content": "COLLECTIVIST CULTURAL CONTEXT: The user is navigating family bonds and collective obligations. Do NOT apply Western individualist framing ('prioritize your own needs over family'). Hold space for BOTH the user's individual feelings AND the legitimacy of family roles. Use language like: 'It sounds like both your own sense of direction AND your family's expectations matter deeply to you — finding a path that honours both is real work.' Do NOT pathologize family bonds or treat them simply as constraints to overcome."
      }
    }
  ]
}
```

- [ ] **Step 8.3: Create `secondary_intent.json`**

```json
{
  "category": "prompt_injection",
  "rules": [
    {
      "rule_id": "PI-SI-001",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "DBT dialectical framing when any secondary intent is present",
      "category": "prompt_injection",
      "trigger_type": "secondary_intent_present",
      "trigger_value": null,
      "trigger_keywords": [],
      "action": {
        "type": "inject",
        "target": "user",
        "content": "SECONDARY INTENT PRESENT: Use DBT dialectical framing — two things can be true at once. Address BOTH the primary and secondary emotion/need explicitly in your response. Example framing: 'It makes sense that you feel [primary emotion] AND that you also [secondary need]. Both are real and valid.'"
      }
    }
  ]
}
```

- [ ] **Step 8.4: Create `clinical_flag_adaptations.json`**

```json
{
  "category": "prompt_injection",
  "rules": [
    {
      "rule_id": "PI-CF-001",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Motivational interviewing for substance_use flag",
      "category": "prompt_injection",
      "trigger_type": "flag_present",
      "trigger_value": "substance_use",
      "trigger_keywords": [],
      "action": {
        "type": "inject",
        "target": "system",
        "content": "CLINICAL ADAPTATION (substance use): The user has disclosed substance use. Use motivational interviewing language. Do NOT judge or suggest immediate cessation. Explore ambivalence gently."
      }
    },
    {
      "rule_id": "PI-CF-002",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Trauma-sensitive language for trauma_indicator flag",
      "category": "prompt_injection",
      "trigger_type": "flag_present",
      "trigger_value": "trauma_indicator",
      "trigger_keywords": [],
      "action": {
        "type": "inject",
        "target": "system",
        "content": "CLINICAL ADAPTATION (trauma): The user has disclosed trauma. Use trauma-sensitive language. Do NOT push for details. Prioritise emotional safety and containment."
      }
    },
    {
      "rule_id": "PI-CF-003",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Body-neutral language for eating_concern flag",
      "category": "prompt_injection",
      "trigger_type": "flag_present",
      "trigger_value": "eating_concern",
      "trigger_keywords": [],
      "action": {
        "type": "inject",
        "target": "system",
        "content": "CLINICAL ADAPTATION (eating concern): The user has disclosed eating concerns. Avoid all body or weight comments. Be sensitive. Gently encourage professional support if appropriate."
      }
    },
    {
      "rule_id": "PI-CF-004",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "No medication advice for medication_mention flag",
      "category": "prompt_injection",
      "trigger_type": "flag_present",
      "trigger_value": "medication_mention",
      "trigger_keywords": [],
      "action": {
        "type": "inject",
        "target": "system",
        "content": "CLINICAL ADAPTATION (medication): The user mentioned medication. Do NOT advise on dosage or medication changes. Encourage speaking with their prescriber for any medication questions."
      }
    }
  ]
}
```

- [ ] **Step 8.5: Commit**

```bash
git add src/sage_poc/rules/data/cultural/ src/sage_poc/rules/data/prompt_injection/
git commit -m "feat(rules): add cultural and prompt injection JSON rule data files"
```

---

## Task 9: Migrate `freeflow_respond.py` to Rules Service

**Files:**
- Modify: `src/sage_poc/nodes/freeflow_respond.py`
- Extend: `tests/test_rules_integration.py`

- [ ] **Step 9.1: Write integration tests for the migrated compose_prompt**

Append to `tests/test_rules_integration.py`:

```python
# ── freeflow_respond compose_prompt via Rules Service ────────────────────────
from sage_poc.nodes.freeflow_respond import compose_prompt


def _freeflow_state(**overrides):
    base = {
        "raw_message": "I feel anxious",
        "detected_language": "en",
        "message_en": "I feel anxious",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "intent_confidence": 0.9,
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "skill_match_method": None,
        "semantic_score": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
    }
    base.update(overrides)
    return base


def test_islamic_framing_injected_when_faith_keyword_present():
    state = _freeflow_state(message_en="I feel my faith in allah is fading")
    system_str, _ = compose_prompt(state)
    assert "ISLAMIC" in system_str or "sabr" in system_str or "ibtila" in system_str


def test_no_islamic_framing_without_faith_keyword():
    state = _freeflow_state(message_en="I feel really anxious today")
    system_str, _ = compose_prompt(state)
    assert "ibtila" not in system_str


def test_collectivist_framing_injected_when_family_keyword_present():
    state = _freeflow_state(message_en="My family expects me to be an engineer")
    system_str, _ = compose_prompt(state)
    assert "COLLECTIVIST" in system_str or "honour" in system_str or "family" in system_str.upper()


def test_clinical_adaptation_substance_injected_from_flag():
    state = _freeflow_state(clinical_flags=["substance_use"])
    system_str, _ = compose_prompt(state)
    assert "motivational interviewing" in system_str.lower() or "substance" in system_str.lower()


def test_secondary_intent_dialectical_framing_injected():
    state = _freeflow_state(
        primary_intent="new_skill",
        secondary_intent="info_request",
    )
    _, user_str = compose_prompt(state)
    assert "SECONDARY INTENT" in user_str or "dialectical" in user_str.lower()


def test_no_secondary_intent_framing_when_none():
    state = _freeflow_state(primary_intent="new_skill", secondary_intent=None)
    _, user_str = compose_prompt(state)
    assert "SECONDARY INTENT" not in user_str
```

- [ ] **Step 9.2: Run to confirm failures**

```bash
uv run pytest tests/test_rules_integration.py::test_islamic_framing_injected_when_faith_keyword_present -v
```

Expected: FAIL (PERSONA still has embedded cultural text, but no conditional injection).

- [ ] **Step 9.3: Rewrite `freeflow_respond.py`**

Replace the entire file:

```python
# src/sage_poc/nodes/freeflow_respond.py
from sage_poc.state import SageState
from sage_poc.llm import get_responder
from sage_poc.knowledge import lookup_knowledge
from sage_poc.rules import engine as rules_engine

# Core persona: character, scope constraints, communication style.
# Islamic and collectivist framing removed — now injected conditionally by Rules Service
# when triggered by user message content. Clinical adaptations moved to prompt_injection rules.
PERSONA = """You are Sage, a warm and empathetic wellness companion. You provide emotional support grounded in evidence-based approaches (CBT, DBT, motivational interviewing). You are conversational, never clinical or cold. You listen deeply, reflect back what you hear, and gently guide users toward insight.

You do NOT diagnose, prescribe, or replace professional mental health care. If someone is in crisis, your only role is to express care and provide emergency resources.

Keep responses concise (2–4 sentences unless the user needs more). Match the user's energy and register. Be present before being helpful."""


def compose_prompt(state: SageState) -> tuple[str, str]:
    """Return (system_str, user_str) for role-separated LLM invocation.

    system_str: persona + culturally-triggered injections + clinical adaptations.
    user_str:   history + intent + secondary-intent framing + skill instruction +
                knowledge snippet + user message.
    """
    message_en = state.get("message_en", "")
    language = state.get("detected_language", "en")
    clinical_flags = state.get("clinical_flags", [])
    primary_intent = state.get("primary_intent")
    secondary_intent = state.get("secondary_intent")

    # ── System role ────────────────────────────────────────────────────────────
    system_parts = [PERSONA]

    # Cultural injections (Islamic framing, collectivist framing)
    cultural_result = rules_engine.evaluate("cultural", {
        "text": message_en,
        "language": language,
    })
    for action in cultural_result.actions:
        if action.get("target") == "system":
            system_parts.append(action["content"])

    # Prompt injection: clinical flag adaptations + secondary intent (system-targeted)
    injection_result = rules_engine.evaluate("prompt_injection", {
        "text": message_en,
        "clinical_flags": clinical_flags,
        "primary_intent": primary_intent,
        "secondary_intent": secondary_intent,
    })
    system_injections = [
        a["content"] for a in injection_result.actions if a.get("target") == "system"
    ]
    if system_injections:
        system_parts.append(
            "\nCLINICAL ADAPTATIONS (follow these strictly):\n"
            + "\n".join(f"- {c}" for c in system_injections)
        )

    system_str = "\n\n".join(system_parts)

    # ── User role ──────────────────────────────────────────────────────────────
    user_parts = []

    if state["conversation_history"]:
        history = state["conversation_history"][-4:]
        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in history
        )
        user_parts.append(f"CONVERSATION HISTORY:\n{history_text}")

    intensity = state.get("emotional_intensity", 5)
    intent_line = f"INTENT: {primary_intent or 'general_chat'}"
    if secondary_intent:
        intent_line += f" + {secondary_intent} (blended)"
    user_parts.append(f"{intent_line} | Emotional intensity: {intensity}/10")

    # Prompt injection: user-targeted injections (dialectical framing for secondary intent)
    user_injections = [
        a["content"] for a in injection_result.actions if a.get("target") == "user"
    ]
    for content in user_injections:
        user_parts.append(content)

    if state.get("step_instruction"):
        user_parts.append(f"SKILL INSTRUCTION:\n{state['step_instruction']}")

    # Knowledge injection for info_request intent
    intent_set = {primary_intent, secondary_intent}
    if "info_request" in intent_set:
        snippet = lookup_knowledge(message_en)
        if snippet:
            user_parts.append(
                f"KNOWLEDGE (weave naturally into your response if relevant):\n{snippet}"
            )

    user_parts.append(f"USER: {message_en}")
    user_str = "\n\n".join(user_parts)

    return system_str, user_str


async def freeflow_respond_node(state: SageState, llm=None) -> dict:
    if llm is None:
        llm = get_responder()

    system_str, user_str = compose_prompt(state)
    messages = [
        {"role": "system", "content": system_str},
        {"role": "user", "content": user_str},
    ]

    chunks: list[str] = []
    async for chunk in llm.astream(messages):
        if isinstance(chunk.content, str) and chunk.content:
            chunks.append(chunk.content)
    response = "".join(chunks).strip()

    return {
        "response_en": response,
        "path": state["path"] + ["freeflow_respond"],
    }
```

- [ ] **Step 9.4: Run integration tests**

```bash
uv run pytest tests/test_rules_integration.py -v
```

Expected: all pass.

- [ ] **Step 9.5: Run full test suite**

```bash
uv run pytest tests/ -v
```

Expected: all 211 prior tests + all new rules tests pass. If any existing test asserts specific text from the old `_CLINICAL_ADAPTATIONS` dict, update the assertion to match the new injection content from JSON rules.

- [ ] **Step 9.6: Commit**

```bash
git add src/sage_poc/nodes/freeflow_respond.py tests/test_rules_integration.py
git commit -m "feat(rules): migrate freeflow_respond compose_prompt to Rules Service; Islamic and collectivist framing now engine-injected"
```

---

## Task 10: Passive SI end-to-end graph tests (P0 validation)

These tests are not part of the Rules Service itself — they validate that the P0 safety requirement (passive SI triggers crisis routing through the full LangGraph) actually passes.

**Files:**
- Extend: `tests/test_graph.py`

- [ ] **Step 10.1: Add passive SI E2E tests**

Append to `tests/test_graph.py` (locate the existing `make_e2e_state` helper and use it):

```python
# ── P0: Passive SI end-to-end validation ─────────────────────────────────────
# These tests confirm that veiled ideation routes to crisis_response through
# the full graph — not just that keywords exist in the lexicon.

import pytest
from unittest.mock import patch, AsyncMock
from sage_poc.graph import build_graph

_graph = build_graph()


def make_e2e_state(raw_message):
    return {
        "raw_message": raw_message,
        "detected_language": "en",
        "message_en": raw_message,
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 1.0,
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "skill_match_method": None,
        "semantic_score": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
    }


@pytest.mark.parametrize("message", [
    "nothing matters anymore",
    "everyone would be better off without me",
    "there's no point in living",
    "I wish I could disappear",
    "I have no reason to live",
])
def test_passive_si_english_routes_to_crisis_path(message):
    """Full graph run: passive SI → safety_check → crisis_response (not intent_route)."""
    result = _graph.invoke(make_e2e_state(message))
    assert result["is_safe"] is False, f"Expected is_safe=False for: {message!r}"
    assert "crisis_response" in result["path"], (
        f"Expected crisis_response in path for: {message!r}. Got path: {result['path']}"
    )
    assert result["gate_path"] == "crisis", (
        f"Expected gate_path='crisis' for: {message!r}"
    )
    # Verify UAE resource is in the response
    assert "800" in result["response"] or "999" in result["response"], (
        f"Expected UAE hotline in crisis response for: {message!r}"
    )


@pytest.mark.parametrize("arabic_message", [
    "نفسي تعبت",
    "ما عاد قادر",
    "مافي فايدة",
    "ياريت انام ولا اصحى",
])
def test_passive_si_arabic_routes_to_crisis_path(arabic_message):
    """Full graph run: Arabic passive SI → crisis_response."""
    state = make_e2e_state(arabic_message)
    result = _graph.invoke(state)
    assert result["is_safe"] is False, (
        f"Expected is_safe=False for Arabic passive SI: {arabic_message!r}"
    )
    assert "crisis_response" in result["path"]
    assert result["gate_path"] == "crisis"


@pytest.mark.parametrize("safe_message", [
    "I don't want to die",
    "I never want to end my life",
    "could kill for a good coffee right now",
    "that meeting killed me",
    "I'm dying of laughter",
])
def test_negated_and_metaphor_phrases_do_not_trigger_crisis(safe_message):
    """Full graph run: negated/metaphor messages must NOT route to crisis_response."""
    with patch("sage_poc.nodes.intent_route.intent_route_node") as mock_intent:
        mock_intent.return_value = {
            "primary_intent": "general_chat",
            "secondary_intent": None,
            "intent_confidence": 0.9,
            "emotional_intensity": 5,
            "engagement": 5,
            "path": ["safety_check", "intent_route"],
        }
        result = _graph.invoke(make_e2e_state(safe_message))
    assert result["is_safe"] is True, (
        f"Expected is_safe=True (no false positive) for: {safe_message!r}"
    )
    assert "crisis_response" not in result["path"], (
        f"Expected NO crisis_response for: {safe_message!r}. Got path: {result['path']}"
    )
```

- [ ] **Step 10.2: Run passive SI tests**

```bash
uv run pytest tests/test_graph.py -v -k "passive_si"
```

Expected: all 9 parametrized tests pass. If any fail, check the corresponding JSON rule patterns and add missing variants.

- [ ] **Step 10.3: Run full suite one final time**

```bash
uv run pytest tests/ -v
```

Expected: 230+ tests, 0 failures.

- [ ] **Step 10.4: Final commit**

```bash
git add tests/test_graph.py
git commit -m "test(safety): add P0 passive SI end-to-end graph tests — crisis routing validated"
```

---

## Section 2 — JSON Rule Schema Reference

Every rule file contains a `"rules"` array. Each element follows one of these schemas:

### Safety Rule
```json
{
  "rule_id": "SK-EN-001",          // unique, never reused
  "version": "1.0.0",
  "authored_by": "sage_clinics",
  "effective_date": "YYYY-MM-DD",
  "active": true,
  "description": "...",
  "category": "safety",
  "match_type": "keyword",          // "keyword" | "regex"
  "patterns": ["..."],              // exact lowercase strings; Arabic in normalized form
  "language": "en",                 // "en" | "ar" | "any"
  "modifiers": ["negation_check"],  // optional; "negation_check" suppresses false positives
  "action": {
    "type": "crisis_flag",          // or "clinical_flag"
    "flag_id": "si_explicit"        // matched against SageState.crisis_flags / clinical_flags
  }
}
```

### Crisis Content Rule
```json
{
  "rule_id": "CC-EN-001",
  "version": "1.0.0",
  "authored_by": "sage_clinics",
  "effective_date": "YYYY-MM-DD",
  "active": true,
  "category": "crisis_content",
  "locale": "en_uae",              // "{language}_uae"
  "crisis_level": "acute",         // "acute" | "extended"
  "action": {
    "type": "crisis_response",
    "response_text": "...",         // full response string; update hotline numbers here
    "resources": [{"name": "...", "number": "..."}]
  }
}
```

### Cultural Rule
```json
{
  "rule_id": "CU-IS-001",
  "version": "1.0.0",
  "authored_by": "sage_clinics",
  "effective_date": "YYYY-MM-DD",
  "active": true,
  "category": "cultural",
  "trigger_keywords": ["allah", "faith"],
  "language": "any",
  "action": {
    "type": "prompt_injection",
    "target": "system",             // "system" or "user" — which LLM role receives this
    "layer": "L2",                  // informational; which prompt layer this belongs to
    "content": "..."                // injected verbatim into the prompt
  }
}
```

### Prompt Injection Rule
```json
{
  "rule_id": "PI-CF-001",
  "version": "1.0.0",
  "authored_by": "sage_clinics",
  "effective_date": "YYYY-MM-DD",
  "active": true,
  "category": "prompt_injection",
  "trigger_type": "flag_present",                  // see trigger types below
  "trigger_value": "substance_use",                // used by flag_present + intent_match
  "trigger_keywords": [],                          // used by keyword_match
  "action": {
    "type": "inject",
    "target": "system",
    "content": "..."
  }
}
```

**Trigger types:**

| `trigger_type` | Fires when |
|---|---|
| `keyword_match` | any `trigger_keywords` entry appears in `text` |
| `flag_present` | `trigger_value` is in `clinical_flags` |
| `intent_match` | `trigger_value` matches `primary_intent` or `secondary_intent` |
| `secondary_intent_present` | `secondary_intent` is not None |

---

## Section 3 — Evaluation Engine Interface

```python
from sage_poc.rules import evaluate
from sage_poc.rules.schemas import EvalResult

result: EvalResult = evaluate(category="safety", context={...})

# result.fired         — list[FiredRule] in evaluation order
# result.actions       — list[dict] — the action dicts from all fired rules
# result.fired_ids     — list[str] — rule IDs, for audit logging
# bool(result)         — True if any rule fired
```

**Context dict per category:**

| Category | Required keys |
|---|---|
| `"safety"` | `text_en: str`, `text_ar: str \| None`, `language: str` |
| `"crisis_content"` | `language: str`, `crisis_level: str` |
| `"cultural"` | `text: str`, `language: str` |
| `"prompt_injection"` | `text: str`, `clinical_flags: list[str]`, `primary_intent: str \| None`, `secondary_intent: str \| None` |

---

## Section 4 — Node Integration Points

| Node | Category called | Context built from | Result consumed |
|---|---|---|---|
| `safety_check_node` | `"safety"` | `text_en=message_en`, `text_ar=raw` (if ar), `language=lang` | `crisis_flag` actions → `crisis_flags`; `clinical_flag` actions → `clinical_flags` (merged with prior turn) |
| `_crisis_response_node` | `"crisis_content"` | `language=lang`, `crisis_level="acute"` | `response_text` from first fired rule |
| `freeflow_respond compose_prompt` | `"cultural"` | `text=message_en`, `language=lang` | `system`-targeted injections appended to system prompt |
| `freeflow_respond compose_prompt` | `"prompt_injection"` | `text`, `clinical_flags`, `primary_intent`, `secondary_intent` | `system`-targeted → CLINICAL ADAPTATIONS block; `user`-targeted → user role additions |

---

## Section 5 — Authoring Contract

**POC workflow (clinicians + engineers):**

1. Edit a JSON file in `src/sage_poc/rules/data/{category}/`
2. Validate the schema: `uv run python -c "from sage_poc.rules.loader import load_rules; load_rules('safety')"`
3. Test the specific rule: write a pytest parametrize case for the new pattern in `test_rules_safety.py`
4. Confirm no regressions: `uv run pytest tests/test_rules_safety.py tests/test_rules_integration.py -v`
5. PR review: all rule changes reviewed by both a clinician and the lead engineer

**Full Build workflow (CMS → Cosmos DB):**
- Same JSON schema; JSON is imported directly into Cosmos DB
- `loader.py` gains a `CosmosDbLoader` that implements the same interface
- `reload_all()` becomes a cache-invalidation event subscription
- Rule authoring moves to a CMS form; JSON export remains the source of truth

**Clinician-owned fields:** `patterns`, `trigger_keywords`, `action.content`, `action.response_text`, `active`, `description`  
**Engineer-owned fields:** `rule_id`, `version`, `match_type`, `modifiers`, `trigger_type`, `effective_date`

---

## Section 6 — Pre-processing Pipeline

The `normalize.py` module runs before all rule evaluation. The engine calls it internally — node code never calls normalize directly.

**Pipeline per text type:**

| Input | Function | What it does |
|---|---|---|
| Any text before English keyword matching | `normalize_text(text)` | `strip_invisible` → `lower()` |
| Arabic text before Arabic keyword matching | `normalize_arabic(text)` | `strip_invisible` → NFKC → strip diacritics → normalize alef → `lower()` |
| Arabic patterns in JSON files | Written in post-normalization form | Authors write `"ابي اموت"` (bare alef), not `"أبي أموت"` |

**Why patterns are pre-normalized in JSON:** Eliminates ambiguity at authoring time. The engine normalizes both pattern and input before comparison, so alef variants and diacritics always match regardless of which orthographic form the user typed.

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered in |
|---|---|
| Rules are data, not code | Tasks 5, 7, 8: all clinical content in JSON |
| Deterministic first, LLM second | Task 6 (safety), Task 9 (freeflow) |
| Rules versioned + auditable | schemas.py `rule_id`, `version`, `effective_date`; engine logs `fired_ids` |
| Engine stateless | engine.py: no state reads/writes |
| Bridge strategy: JSON files ARE production content | Section 5 authoring contract |
| Negation handling (P0-3) | engine.py `_has_negation`; safety JSON `"modifiers": ["negation_check"]` |
| Arabic alef normalization (P1-3) | normalize.py; engine._eval_safety |
| Islamic framing deployed (P1-1) | Task 8: `islamic_vocabulary.json`; Task 9: compose_prompt engine call |
| Collectivist framing deployed (P1-2) | Task 8: `collectivist_framing.json` |
| Clinical flag carry-forward (P1-6) | Task 6: set union in safety_check_node |
| Secondary intent in response (P1-7) | Task 8: `secondary_intent.json`; Task 9: user-targeted injection |
| Passive SI E2E validated (P0-2) | Task 10: 9 parametrized graph tests |
| Crisis response content from JSON (P0-1) | Task 7: `_crisis_response_node` migration |
| `gate_path` Literal includes "crisis" | Task 7: state.py fix |

**Placeholder scan:** None found.

**Type consistency:** `EvalResult`, `FiredRule`, `SafetyRule`, `CrisisContentRule`, `CulturalRule`, `PromptInjectionRule` — consistent across schemas.py, engine.py, loader.py, and all test files.
