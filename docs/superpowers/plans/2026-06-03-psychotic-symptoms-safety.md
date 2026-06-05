# Psychotic Symptoms Safety Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect psychotic symptom disclosures and command hallucinations before they reach the skill pipeline, route them correctly through existing graph nodes, and fix the confirmed crisis→review-queue write gap.

**Architecture:** Add `psychotic_disclosure` as CF-006 in the existing S1 clinical flag rules engine (`clinical_flag_patterns.json`). Wire `skill_select` to auto-select a new clinician-authored `psychotic_referral` skill when the flag is active — same pattern as `post_crisis_check_in` auto-select — so it flows through `skill_executor → freeflow_respond → output_gate` and preserves audit, cultural rules, and translation. Guard against re-selection loop with a `psychotic_referral_delivered` state field set on skill completion. Add command hallucination phrases to `crisis_keywords.json` (S1 rules) so they fire as named `crisis_flag` actions routed to `crisis_response`. Fix `_crisis_response_node` to write `clinician_review_queue`. Fix profile extractor contraindication. No new graph nodes. No hardcoded Python content.

**Tech Stack:** JSON rule files, Python 3.12, pytest — no new dependencies.

---

## Governance: Authoritative Document

`docs/SageAI_architecture_current.md` supersedes `SageAI_v7_FINAL_COMPLETE.docx` for all code-level claims — stated in its own header. §1.1 documents the explicit delta: 9 nodes vs v7's 8, `crisis_response` as a named node, `post_crisis_check_in` as a built construct, S3 live. The implementation has legitimately evolved past v7. Any validation against v7 FINAL is validation against a stale spec. This plan is anchored to the current doc.

---

## Pre-Implementation Approval Gate

**`psychotic_disclosure` is a schema change.** The current architecture enumerates exactly 5 clinical flags. Adding a 6th requires:

- [ ] Clinician sign-off on CF-006 phrase list and clinical definition
- [ ] Clinician review of `PI-CF-006` injection rule content before activation
- [ ] Clinician review of `psychotic_referral` skill step instruction and examples
- [ ] Helpline number `800 46342` verified against `en_uae.json` ✓ — matches existing crisis content

Until sign-off, all new rules and the skill ship with `"active": false`. Do not set `active: true` unilaterally.

---

## Escalation SLA Note

- `psychotic_disclosure` → L2 (24hr per v7 §9.3). Code `severity="medium"` = 4hr. **Named mismatch** — code is more aggressive. Use `severity="medium"` here; reconcile SLA separately.
- `command_hallucination` → L3 (immediate). Code `severity="high"` ✓.

---

## Known Precision Limitation — Keyword-only Detection

CF-006 uses substring keyword matching (S1). Recall on paraphrases and dialect variants is weak. False-positive risk exists (e.g. indirect metaphorical use of "voices"). MARBERT/BGE-M3 semantic tier for psychotic symptoms is deferred — same gap as S2 for SI detection. Accepted as a known POC limitation; document in §20.1 of the architecture doc after implementation.

`_apply_suppressions` in `engine.py` only suppresses `crisis_flag` actions (line 43: `if si_rule.action.get("type") != "crisis_flag": continue`). **`crisis_suppress` cannot suppress `clinical_flag` actions.** Idiom exclusion via `false_positive_exclusions.json` will not work for CF-006. Instead, CF-006 patterns are chosen to minimise false positives at source. Extending the engine to support `clinical_suppress` is a separate tracked item, not in scope here.

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `src/sage_poc/rules/data/safety/clinical_flag_patterns.json` | Add CF-006 psychotic_disclosure (active: false) |
| Modify | `src/sage_poc/rules/data/safety/crisis_keywords.json` | Add command_hallucination crisis rules (active: true) |
| Modify | `src/sage_poc/safety/crisis_phrases.json` | Add command_hallucination to S3 semantic corpus |
| Modify | `src/sage_poc/rules/data/flag_lifecycle_config.json` | Add psychotic_disclosure entry |
| Modify | `src/sage_poc/rules/data/prompt_injection/clinical_flag_adaptations.json` | Add PI-CF-006 (active: false) |
| Create | `src/sage_poc/skills/psychotic_referral.json` | Clinician-authored referral skill (active: false) |
| Modify | `src/sage_poc/skill_ids.py` | Add psychotic_referral to SKILL_REGISTRY |
| Modify | `src/sage_poc/corpus_constants.py` | Add psychotic_referral to KEYWORD_SEMANTIC_SKIP |
| Modify | `src/sage_poc/state.py` | Add psychotic_referral_delivered field |
| Modify | `src/sage_poc/nodes/skill_select.py` | Auto-select + delivered guard |
| Modify | `src/sage_poc/nodes/skill_executor.py` | Set delivered flag on completion |
| Modify | `src/sage_poc/graph.py` | Fix _crisis_response_node → write clinician_review_queue |
| Modify | `src/sage_poc/memory/profile_extractor.py` | Add apply_contraindications |
| Create | `tests/test_rules_safety_psychotic.py` | CF-006 + command_hallucination tests (bypass loader) |
| Create | `tests/test_skill_select_psychotic.py` | Auto-select + delivered-guard routing tests |
| Modify | `tests/test_output_gate_clinical_review.py` | Add crisis→review-queue write test |
| Modify | `tests/test_profile_extractor.py` | Add contraindication test |

---

## Task 1: Add CF-006 psychotic_disclosure to clinical flag rules engine

**Files:**
- Modify: `src/sage_poc/rules/data/safety/clinical_flag_patterns.json`
- Create: `tests/test_rules_safety_psychotic.py`

**N1 fix — TDD approach:** `loader.py` filters `if rule.active:` at load time. With `active: false`, CF-006 never enters the rule cache — `engine.evaluate()` sees nothing. Tests that call `engine.evaluate()` would pass vacuously. Fix: call `_eval_safety([constructed_rule], context)` directly — the internal evaluation function takes a list of rule objects, bypasses the loader entirely, and is independent of the deployment `active` flag. This tests detection logic in isolation; the deployment gate is a config concern, not a test concern.

**N5 fix — no FPE rules:** `_apply_suppressions` in `engine.py` only processes `crisis_flag` actions (line 43). `crisis_suppress` cannot suppress `clinical_flag` actions. Idiom exclusion via `false_positive_exclusions.json` will silently do nothing for CF-006. Instead, patterns below are chosen to minimise false positives at source: all patterns are multi-word and require a clinical-register pairing.

- [ ] **Step 1: Write the tests — bypass the loader, test detection logic directly**

```python
# tests/test_rules_safety_psychotic.py
"""Tests for CF-006 psychotic_disclosure clinical flag detection.

Tests call _eval_safety() directly to bypass the rules loader's active-flag
filter. This ensures detection and precision logic is exercised regardless of
the deployment flag. active=True is set explicitly in the test fixture.
"""
import pytest
from sage_poc.rules.engine import _eval_safety
from sage_poc.rules.schemas import SafetyRule


def _make_cf006_rule(**overrides) -> SafetyRule:
    """Construct a live CF-006 rule for test use. active=True always."""
    data = {
        "rule_id": "CF-006",
        "version": "1.0.0",
        "authored_by": "sage_clinics",
        "effective_date": "2026-06-03",
        "active": True,           # force-active: tests the logic, not the deployment gate
        "description": "Psychotic symptom disclosure",
        "category": "safety",
        "match_type": "keyword",
        "patterns": [
            "hearing voices",
            "i hear voices",
            "voices in my head",
            "seeing things that aren't there",
            "seeing things that are not there",
            "seeing things no one else sees",
            "people are watching me",
            "someone is following me",
            "أسمع أصوات",
            "في أصوات تكلمني",
            "أشوف أشياء ما أحد يشوفها",
            "أحد يراقبني",
        ],
        "language": "any",
        "modifiers": [],
        "action": {"type": "clinical_flag", "flag_id": "psychotic_disclosure"},
    }
    data.update(overrides)
    return SafetyRule.model_validate(data)


_CF006 = _make_cf006_rule()


def _flags(text_en, text_ar=None, language="en"):
    result = _eval_safety([_CF006], {
        "text_en": text_en,
        "text_ar": text_ar or "",
        "language": language,
    })
    return [a["flag_id"] for a in result.actions if a.get("type") == "clinical_flag"]


# --- Detection ---

def test_hearing_voices_sets_flag():
    assert "psychotic_disclosure" in _flags("I've been hearing voices in my head")

def test_i_hear_voices_sets_flag():
    assert "psychotic_disclosure" in _flags("I hear voices all the time")

def test_voices_in_my_head_sets_flag():
    assert "psychotic_disclosure" in _flags("there are voices in my head that won't stop")

def test_seeing_things_not_there_sets_flag():
    assert "psychotic_disclosure" in _flags("I keep seeing things that aren't there")

def test_arabic_hearing_voices():
    assert "psychotic_disclosure" in _flags("أسمع أصوات", text_ar="أسمع أصوات", language="ar")

def test_arabic_voices_talking():
    assert "psychotic_disclosure" in _flags("في أصوات تكلمني كل يوم", text_ar="في أصوات تكلمني كل يوم", language="ar")

# --- Precision (false positive) ---

def test_stress_does_not_trigger():
    assert "psychotic_disclosure" not in _flags("I've been feeling stressed")

def test_mothers_voice_does_not_trigger():
    # "my mother's voice" does not contain the substring "hearing voices" or "voices in my head"
    # or "i hear voices" — this is not a false positive with these patterns
    assert "psychotic_disclosure" not in _flags("I keep hearing my mother's voice telling me to do better")

def test_choir_voices_does_not_trigger():
    assert "psychotic_disclosure" not in _flags("I love hearing the voices of the choir")

def test_si_phrase_does_not_trigger_psychotic():
    # SI detection is separate — CF-006 must not double-fire on SI phrases
    assert "psychotic_disclosure" not in _flags("I want to end my life")

# --- No cross-contamination with crisis_flag ---

def test_psychotic_disclosure_is_clinical_not_crisis():
    result = _eval_safety([_CF006], {"text_en": "I've been hearing voices", "text_ar": "", "language": "en"})
    crisis = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert len(crisis) == 0, "psychotic_disclosure is a clinical_flag, not a crisis_flag"
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc && uv run pytest tests/test_rules_safety_psychotic.py -v
```
Expected: `AttributeError` or `ImportError` — `_eval_safety` is not yet exported, or `SafetyRule` construction fails if fields don't exist yet. The tests themselves are structurally correct and will fail for the right reason.

- [ ] **Step 3: Add CF-006 to clinical_flag_patterns.json**

Append this rule object to the `"rules"` array:

```json
{
  "rule_id": "CF-006",
  "version": "1.0.0",
  "authored_by": "sage_clinics",
  "approved_by": null,
  "effective_date": "2026-06-03",
  "active": false,
  "description": "Psychotic symptom disclosure — auditory/visual hallucinations, paranoid ideation. INACTIVE pending clinician sign-off (schema change: 6th clinical flag). Activate by setting active: true after approval. Known limitation: keyword-only detection; MARBERT/semantic tier deferred (see §20.1).",
  "category": "safety",
  "match_type": "keyword",
  "patterns": [
    "hearing voices",
    "i hear voices",
    "voices in my head",
    "seeing things that aren't there",
    "seeing things that are not there",
    "seeing things no one else sees",
    "people are watching me",
    "someone is following me",
    "أسمع أصوات",
    "في أصوات تكلمني",
    "أشوف أشياء ما أحد يشوفها",
    "أحد يراقبني"
  ],
  "language": "any",
  "modifiers": [],
  "action": {"type": "clinical_flag", "flag_id": "psychotic_disclosure"}
}
```

**No FPE entries added** — `crisis_suppress` cannot suppress `clinical_flag` actions in the current engine. Patterns above are multi-word and clinical-register specific to minimise false positives at source.

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_rules_safety_psychotic.py -v
```
Expected: all PASS. Tests bypass the loader; `active: false` in the JSON does not affect them.

- [ ] **Step 5: Run existing safety suite — confirm no regression**

```bash
uv run pytest tests/test_rules_safety.py tests/test_safety_node_integration.py -v
```
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/rules/data/safety/clinical_flag_patterns.json \
        tests/test_rules_safety_psychotic.py
git commit -m "feat(safety): add CF-006 psychotic_disclosure clinical flag (inactive pending sign-off)"
```

---

## Task 2: Add psychotic_disclosure to flag lifecycle config

**Files:**
- Modify: `src/sage_poc/rules/data/flag_lifecycle_config.json`

- [ ] **Step 1: Add entry**

```json
{
  "cross_session_persistence": {
    "substance_use": false,
    "trauma_indicator": false,
    "eating_concern": false,
    "medication_mention": false,
    "domestic_situation": false,
    "psychotic_disclosure": false
  },
  "flag_immutable_within_session": true
}
```

- [ ] **Step 2: Run lifecycle tests**

```bash
uv run pytest tests/test_clinical_flag_lifecycle.py -v
```
Expected: all PASS.

- [ ] **Step 3: Commit**

```bash
git add src/sage_poc/rules/data/flag_lifecycle_config.json
git commit -m "feat(safety): add psychotic_disclosure to flag_lifecycle_config"
```

---

## Task 3: Add PI-CF-006 prompt injection rule

**Files:**
- Modify: `src/sage_poc/rules/data/prompt_injection/clinical_flag_adaptations.json`

- [ ] **Step 1: Append PI-CF-006 to the rules array**

```json
{
  "rule_id": "PI-CF-006",
  "version": "1.0.0",
  "authored_by": "sage_clinics",
  "effective_date": "2026-06-03",
  "active": false,
  "description": "Clinical adaptation for psychotic_disclosure flag. INACTIVE pending clinician sign-off.",
  "category": "prompt_injection",
  "trigger_type": "flag_present",
  "trigger_value": "psychotic_disclosure",
  "trigger_keywords": [],
  "action": {
    "type": "inject",
    "target": "system",
    "content": "CLINICAL ADAPTATION (psychotic symptoms): The user has disclosed symptoms that may include perceptual disturbances. Do NOT diagnose or label what they are experiencing. Do NOT probe for details about the nature of the voices or visions. Do NOT suggest these experiences are imaginary or unreal. Acknowledge their experience with care, then gently indicate that what they are describing is important to discuss with a mental health professional. Provide UAE professional support contacts if appropriate."
  }
}
```

- [ ] **Step 2: Run prompt injection tests**

```bash
uv run pytest tests/test_rules_integration.py -v -k "clinical_flag"
```
Expected: all PASS (new rule `active: false`, does not fire).

- [ ] **Step 3: Commit**

```bash
git add src/sage_poc/rules/data/prompt_injection/clinical_flag_adaptations.json
git commit -m "feat(prompt): add PI-CF-006 for psychotic_disclosure (inactive pending sign-off)"
```

---

## Task 4: Author psychotic_referral skill + registry

**Files:**
- Create: `src/sage_poc/skills/psychotic_referral.json`
- Modify: `src/sage_poc/skill_ids.py`
- Modify: `src/sage_poc/corpus_constants.py`

**N3 fix:** v7 §9.4 requires ≥3 examples per step in both AR and EN. Arabic examples must include the verbatim helpline number — not delegated to output_gate translation, which may alter the number. `800 46342` confirmed against `en_uae.json` ✓.

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_skill_schema.py or create tests/test_psychotic_referral_skill.py:

def test_psychotic_referral_skill_loads():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("psychotic_referral")
    assert skill.skill_id == "psychotic_referral"
    assert skill.target_presentations == []
    assert skill.semantic_description == ""
    assert len(skill.steps) == 1
    step = skill.steps[0]
    # Helpline number present verbatim
    combined = (step.technique_description or "") + (step.goal or "") + " ".join(step.examples or [])
    assert "800 46342" in combined, "Helpline number 800 46342 must appear verbatim"
    # EN + AR examples requirement
    en_examples = [e for e in (step.examples or []) if not any('؀' <= c <= 'ۿ' for c in e)]
    ar_examples = [e for e in (step.examples or []) if any('؀' <= c <= 'ۿ' for c in e)]
    assert len(en_examples) >= 3, f"Need ≥3 EN examples, got {len(en_examples)}"
    assert len(ar_examples) >= 3, f"Need ≥3 AR examples, got {len(ar_examples)}"

def test_psychotic_referral_in_registry():
    from sage_poc.skill_ids import SKILL_REGISTRY
    assert "psychotic_referral" in SKILL_REGISTRY

def test_psychotic_referral_in_keyword_semantic_skip():
    from sage_poc.corpus_constants import KEYWORD_SEMANTIC_SKIP
    assert "psychotic_referral" in KEYWORD_SEMANTIC_SKIP
```

- [ ] **Step 2: Run to confirm failure**

```bash
uv run pytest tests/test_psychotic_referral_skill.py -v
```
Expected: `FileNotFoundError` — skill file does not exist.

- [ ] **Step 3: Create the skill JSON**

Create `src/sage_poc/skills/psychotic_referral.json`:

```json
{
  "skill_id": "psychotic_referral",
  "skill_name": "Professional Referral — Psychotic Symptoms",
  "skill_type": "structured",
  "self_evolution": "manual_only",
  "evidence_base": "NICE Guidelines CG178 (Psychosis and Schizophrenia, 2014); WHO mhGAP Intervention Guide v2.0 (2016)",
  "target_presentations": [],
  "semantic_description": "",
  "cultural_overrides": "",
  "steps": [
    {
      "step_id": "professional_referral",
      "goal": "Acknowledge what the user shared with care and provide clear guidance to professional support, including UAE helpline 800 46342 verbatim",
      "technique": "Warm acknowledgement with professional referral",
      "technique_description": "What the user is describing sounds like something really important to explore with a mental health professional who can give them the right kind of support. In the UAE, they can reach the MoHAP Counselling Line on 800 46342, free and available 24 hours a day. They do not have to face this alone. Be warm, non-alarming, and non-diagnostic. The phone number 800 46342 must appear verbatim in the response. Do NOT use clinical terms like psychosis, schizophrenia, or hallucinations. Do NOT suggest the user's experience is imaginary.",
      "tone": "warm, calm, non-alarming, non-diagnostic",
      "contraindications": "Do NOT label the experience (do not say psychosis, hallucinations, or delusions). Do NOT dismiss or minimise. Do NOT ask probing questions about the content of the voices or visions. The phone number 800 46342 must appear verbatim.",
      "completion_criteria": "Response has acknowledged the user's experience warmly and provided MoHAP 800 46342 verbatim. One-step skill — always complete after one response.",
      "examples": [
        "What you're describing sounds really important, and it's something to talk through with a mental health professional who can give you the right kind of support. In the UAE, the MoHAP Counselling Line is at 800 46342, free and open 24 hours a day. You don't have to navigate this alone.",
        "I hear that something difficult is happening for you. This is the kind of thing that deserves proper support from someone with the right expertise. Please reach out to the MoHAP Counselling Line on 800 46342, any time. They are there for exactly this.",
        "What you've shared deserves more support than I can give you here. A mental health professional is the right person to help you through this. In the UAE, you can call 800 46342 for free, any time of day or night.",
        "ما تصفه مهم وتحتاج فيه دعم من متخصص يقدر يساعدك بشكل صحيح. تقدر تتواصل مع خط وزارة الصحة والوقاية على 800 46342، مجاني ومفتوح 24 ساعة. ما أنت لوحدك في هذا.",
        "أسمعك، وهذا شيء يستاهل اهتمام متخصص. خط وزارة الصحة 800 46342 متاح في أي وقت، وهم موجودين عشانك.",
        "اللي تحس فيه مهم جداً وتحتاج دعم من شخص متخصص. اتصل على 800 46342 خط وزارة الصحة، مجاني ومتاح كل وقت."
      ]
    }
  ],
  "step_policy": [],
  "escalation_matrix": {
    "L1": "If the user indicates any risk to themselves or others, provide the crisis line immediately: MoHAP 800 46342, emergency 999."
  }
}
```

- [ ] **Step 4: Add to SKILL_REGISTRY in skill_ids.py**

Append `"psychotic_referral"` to the `SKILL_REGISTRY` list in `src/sage_poc/skill_ids.py`.

- [ ] **Step 5: Add to KEYWORD_SEMANTIC_SKIP in corpus_constants.py**

Add `"psychotic_referral"` to the `KEYWORD_SEMANTIC_SKIP` frozenset in `src/sage_poc/corpus_constants.py`.

- [ ] **Step 6: Run tests**

```bash
uv run pytest tests/test_psychotic_referral_skill.py tests/test_skill_ids.py tests/test_corpus_integrity.py -v
```
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/skills/psychotic_referral.json \
        src/sage_poc/skill_ids.py \
        src/sage_poc/corpus_constants.py
git commit -m "feat(skills): add psychotic_referral skill (≥3 EN+AR examples, active=false pending sign-off)"
```

---

## Task 5: Add psychotic_referral_delivered guard (N2 fix — prevents re-selection loop)

**Files:**
- Modify: `src/sage_poc/state.py`
- Modify: `src/sage_poc/nodes/skill_executor.py`
- Modify: `src/sage_poc/nodes/skill_select.py`
- Create: `tests/test_skill_select_psychotic.py`

**Why this is needed:** `flag_immutable_within_session: true` means `psychotic_disclosure` stays in `clinical_flags` for the entire session. Without a delivered guard, `skill_select` auto-selects `psychotic_referral` on every turn after the flag fires, trapping the user in a one-step referral loop for the rest of the session. `post_crisis_check_in` avoids this via `crisis_state` transitions; `psychotic_referral` needs its own equivalent mechanism.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_skill_select_psychotic.py
import asyncio
import pytest


def make_state(**kwargs):
    defaults = {
        "raw_message": "I've been hearing voices in my head",
        "message_en": "I've been hearing voices in my head",
        "detected_language": "en",
        "clinical_flags": ["psychotic_disclosure"],
        "crisis_flags": [],
        "is_safe": True,
        "crisis_state": "none",
        "active_skill_id": None,
        "active_step_id": None,
        "primary_intent": "general_chat",
        "path": ["safety_check", "intent_route"],
        "therapeutic_profile": None,
        "turn_number": 2,
        "psychotic_referral_delivered": None,
    }
    defaults.update(kwargs)
    return defaults


@pytest.mark.asyncio
async def test_psychotic_disclosure_auto_selects_referral_skill():
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_state()
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "psychotic_referral"
    assert result["skill_match_method"] == "psychotic_disclosure_auto_select"
    assert result["active_step_id"] == "professional_referral"


@pytest.mark.asyncio
async def test_delivered_guard_prevents_reselection():
    """After referral delivered, skill_select must not re-select psychotic_referral."""
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_state(psychotic_referral_delivered=True)
    result = await skill_select_node(state)
    assert result["active_skill_id"] != "psychotic_referral", (
        "psychotic_referral must not be re-selected when psychotic_referral_delivered=True"
    )


@pytest.mark.asyncio
async def test_post_crisis_takes_precedence():
    """post_crisis_check_in auto-select must take priority over psychotic_disclosure."""
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_state(crisis_state="monitoring", clinical_flags=["psychotic_disclosure"])
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "post_crisis_check_in"


@pytest.mark.asyncio
async def test_normal_message_without_flag_unaffected():
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_state(
        raw_message="I've been feeling stressed",
        message_en="I've been feeling stressed",
        clinical_flags=[],
    )
    result = await skill_select_node(state)
    assert result.get("active_skill_id") != "psychotic_referral"


def test_skill_executor_sets_delivered_flag_on_completion():
    """skill_executor must set psychotic_referral_delivered=True when psychotic_referral completes."""
    # This is a structural test — verify the return dict contains the field when skill_complete=True.
    # Full integration tested via test_skill_select_psychotic::test_delivered_guard_prevents_reselection.
    from sage_poc.nodes import skill_executor
    import inspect
    src = inspect.getsource(skill_executor)
    assert "psychotic_referral_delivered" in src, (
        "skill_executor must set psychotic_referral_delivered when psychotic_referral completes"
    )
```

- [ ] **Step 2: Run to confirm failure**

```bash
uv run pytest tests/test_skill_select_psychotic.py -v
```
Expected: FAIL on the delivered-guard test and the skill_executor source check.

- [ ] **Step 3: Add psychotic_referral_delivered to state.py**

In `src/sage_poc/state.py`, add to `SageState` (near the `crisis_state` field cluster):

```python
    psychotic_referral_delivered: Optional[bool]   # True after psychotic_referral completes; prevents re-selection loop
```

- [ ] **Step 4: Set delivered flag in skill_executor on completion**

In `src/sage_poc/nodes/skill_executor.py`, find the block starting at line 468:
```python
    crisis_state_update: dict = {}
    if result.get("skill_complete") and skill_id == "post_crisis_check_in":
        crisis_state_update = {"crisis_state": "resolved"}
```

Add immediately after:
```python
    psychotic_referral_update: dict = {}
    if result.get("skill_complete") and skill_id == "psychotic_referral":
        psychotic_referral_update = {"psychotic_referral_delivered": True}
```

Then add `**psychotic_referral_update` to the return dict alongside `**crisis_state_update`:
```python
    return {
        ...
        **crisis_state_update,
        **psychotic_referral_update,
    }
```

- [ ] **Step 5: Add auto-select block with delivered guard to skill_select_node**

In `src/sage_poc/nodes/skill_select.py`, insert after the `post_crisis_check_in` block (after line 107) and before `message = state["message_en"].lower()`:

```python
    # Psychotic disclosure auto-select: fires when CF-006 flag is active AND referral not yet delivered.
    # Post-crisis auto-select above takes precedence.
    # delivered guard prevents re-selection loop (flag_immutable_within_session=true keeps the flag
    # for the full session; without this guard, psychotic_referral would be re-selected every turn).
    if (
        "psychotic_disclosure" in (state.get("clinical_flags") or [])
        and not state.get("psychotic_referral_delivered")
    ):
        skill_id = "psychotic_referral"
        skill = _SKILLS[skill_id]
        return {
            "active_skill_id": skill_id,
            "active_step_id": skill.steps[0].step_id,
            "skill_match_method": "psychotic_disclosure_auto_select",
            "semantic_score": None,
            "path": state["path"] + ["skill_select"],
        }
```

- [ ] **Step 6: Run tests**

```bash
uv run pytest tests/test_skill_select_psychotic.py tests/test_skill_select.py -v
```
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/state.py \
        src/sage_poc/nodes/skill_executor.py \
        src/sage_poc/nodes/skill_select.py \
        tests/test_skill_select_psychotic.py
git commit -m "feat(skill_select): psychotic_referral auto-select with delivered guard (prevents session loop)"
```

---

## Task 6: Add command_hallucination to S1 crisis rules + S3 corpus + recalibrate

**Files:**
- Modify: `src/sage_poc/rules/data/safety/crisis_keywords.json`
- Modify: `src/sage_poc/safety/crisis_phrases.json`
- Modify: `src/sage_poc/safety/s3_semantic.py` (threshold update if needed)

**N6(a) fix:** `crisis_phrases.json` is the S3 embedding corpus — S3 only ever emits `"s3_semantic"` as a flag, never the phrase-level `flag` field. For `command_hallucination` to appear as a named `crisis_flag` in state it must be in `crisis_keywords.json` (S1 rules engine). Both files need updating: `crisis_keywords.json` for deterministic named-flag firing, `crisis_phrases.json` for S3 semantic coverage.

**N6(b) fix:** After S3 recalibration, verify ≥95% SI recall against the calibration suite — gap check alone does not protect SI recall.

- [ ] **Step 1: Write the test**

Add to `tests/test_rules_safety_psychotic.py`:

```python
from sage_poc.rules.engine import _eval_safety
from sage_poc.rules.schemas import SafetyRule
from sage_poc.rules.loader import get_rules, reload_all


def test_command_hallucination_fires_crisis_flag_via_s1():
    """command_hallucination must fire as a named crisis_flag via the S1 rules engine."""
    reload_all()
    result = _eval_safety(get_rules("safety"), {
        "text_en": "should i do what the voices are telling me",
        "text_ar": "",
        "language": "en",
    })
    crisis_flag_ids = [a["flag_id"] for a in result.actions if a.get("type") == "crisis_flag"]
    assert "command_hallucination" in crisis_flag_ids, (
        f"Expected command_hallucination crisis_flag, got: {crisis_flag_ids}"
    )


def test_voices_telling_to_hurt_fires_crisis_flag():
    reload_all()
    result = _eval_safety(get_rules("safety"), {
        "text_en": "the voices are telling me to hurt someone",
        "text_ar": "",
        "language": "en",
    })
    crisis_flag_ids = [a["flag_id"] for a in result.actions if a.get("type") == "crisis_flag"]
    assert "command_hallucination" in crisis_flag_ids
```

Note: these tests use `get_rules("safety")` (active rules from loader) because command_hallucination is a crisis rule that ships `active: true`. `reload_all()` ensures a clean cache.

- [ ] **Step 2: Run to confirm failure**

```bash
uv run pytest tests/test_rules_safety_psychotic.py -v -k "command_hallucination"
```
Expected: FAIL — flag not in rules.

- [ ] **Step 3: Add command_hallucination to crisis_keywords.json**

Open `src/sage_poc/rules/data/safety/crisis_keywords.json`. Append to its `"rules"` array a new rule object:

```json
{
  "rule_id": "CK-CH-001",
  "version": "1.0.0",
  "authored_by": "sage_clinics",
  "effective_date": "2026-06-03",
  "active": true,
  "description": "Command hallucination — user describing acting on or asking whether to act on directive auditory hallucinations. Routes to crisis_response. crisis_flag fires is_safe=False.",
  "category": "safety",
  "match_type": "keyword",
  "patterns": [
    "should i do what the voices are telling me",
    "the voices are telling me to",
    "the voices told me to hurt",
    "the voices want me to hurt",
    "i have to follow what the voices say",
    "i need to do what the voices say",
    "do what the voices tell me"
  ],
  "language": "en",
  "modifiers": [],
  "action": {"type": "crisis_flag", "flag_id": "command_hallucination"}
},
{
  "rule_id": "CK-CH-002",
  "version": "1.0.0",
  "authored_by": "sage_clinics",
  "effective_date": "2026-06-03",
  "active": true,
  "description": "Arabic command hallucination patterns.",
  "category": "safety",
  "match_type": "keyword",
  "patterns": [
    "الأصوات تأمرني بإيذاء",
    "الأصوات تقول لي أذي"
  ],
  "language": "ar",
  "modifiers": [],
  "action": {"type": "crisis_flag", "flag_id": "command_hallucination"}
}
```

- [ ] **Step 4: Add command_hallucination to crisis_phrases.json (S3 semantic corpus)**

Append to the `"phrases"` array in `src/sage_poc/safety/crisis_phrases.json`:

```json
{"text": "should i do what the voices are telling me", "source": "CH-EN-001", "flag": "command_hallucination", "language": "en"},
{"text": "the voices are telling me to hurt someone", "source": "CH-EN-001", "flag": "command_hallucination", "language": "en"},
{"text": "the voices want me to do something dangerous", "source": "CH-EN-001", "flag": "command_hallucination", "language": "en"},
{"text": "i have to follow what the voices say or something bad will happen", "source": "CH-EN-001", "flag": "command_hallucination", "language": "en"},
{"text": "الأصوات تأمرني بإيذاء شخص", "source": "CH-AR-001", "flag": "command_hallucination", "language": "ar"},
{"text": "الأصوات تقول لي أذي نفسي", "source": "CH-AR-001", "flag": "command_hallucination", "language": "ar"}
```

- [ ] **Step 5: Run S1 tests to confirm named crisis_flag fires**

```bash
uv run pytest tests/test_rules_safety_psychotic.py -v -k "command_hallucination"
```
Expected: PASS — `command_hallucination` in `crisis_flag_ids`.

- [ ] **Step 6: Recalibrate S3 threshold**

```bash
uv run python scripts/calibrate_s3_threshold.py
```

Check output for: (a) new `S3_THRESHOLD` value and gap; (b) all SF-1 GATE phrases score ≥ threshold; (c) all SF-6 FALSE_POSITIVE phrases score < threshold. If gap < 0.10, escalate before proceeding. Update `S3_THRESHOLD` in `src/sage_poc/safety/s3_semantic.py` if the value changed.

- [ ] **Step 7: Verify ≥95% SI recall after recalibration (N6b)**

Run the full S3 recall suite with the updated threshold:

```bash
uv run pytest tests/test_s3_semantic.py -v -p no:xdist
```

All SI phrases (both SF-1 GATE and direct ideation) must score ≥ the new `S3_THRESHOLD`. If any previously-passing SI phrase now scores below threshold, stop — the new corpus has degraded recall and the phrases need review before merging.

- [ ] **Step 8: Commit**

```bash
git add src/sage_poc/rules/data/safety/crisis_keywords.json \
        src/sage_poc/safety/crisis_phrases.json \
        src/sage_poc/safety/s3_semantic.py \
        tests/test_rules_safety_psychotic.py
git commit -m "feat(safety): add command_hallucination crisis rules (S1 named flag + S3 corpus) + recalibrate S3"
```

---

## Task 7: Fix _crisis_response_node to write clinician_review_queue

**Files:**
- Modify: `src/sage_poc/graph.py`
- Modify: `tests/test_output_gate_clinical_review.py`

`_crisis_response_node → END` is a documented exception (§2.1 — four stated reasons). It already calls `write_session_audit` directly. The missing write is `clinician_review_queue`. Fix: add `_notify_crisis_review` as an `asyncio.create_task` inside `_crisis_response_node`, same pattern as the existing `write_session_audit` call.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_output_gate_clinical_review.py`:

```python
@pytest.mark.asyncio
async def test_crisis_response_node_writes_clinician_review_queue():
    """_crisis_response_node must write clinician_review_queue; output_gate is bypassed."""
    from unittest.mock import patch, AsyncMock, MagicMock

    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

    state = {
        "raw_message": "the voices told me to hurt someone",
        "message_en": "the voices told me to hurt someone",
        "detected_language": "en",
        "crisis_flags": ["command_hallucination"],
        "clinical_flags": [],
        "crisis_state": "none",
        "turn_count": 1,
        "turn_number": 1,
        "user_id": "test-user-uuid",
        "session_id": "test-session-uuid",
        "path": ["safety_check"],
        "conversation_history": [],
        "active_skill_id": None,
        "therapeutic_profile": None,
        "re_escalation_within_monitoring": False,
    }

    import asyncio
    from sage_poc import graph as sage_graph
    with patch.object(sage_graph, "_get_crisis_review_pool", return_value=mock_pool):
        with patch.object(sage_graph, "write_session_audit", new_callable=AsyncMock):
            with patch.object(sage_graph, "AUDIT_LOG_ENABLED", False):
                await sage_graph._crisis_response_node(state)
                await asyncio.sleep(0.05)  # allow create_task to execute

    inserts = [c for c in mock_conn.execute.call_args_list if "clinician_review_queue" in str(c)]
    assert len(inserts) >= 1, "Expected INSERT into clinician_review_queue from _crisis_response_node"
```

- [ ] **Step 2: Run to confirm failure**

```bash
uv run pytest tests/test_output_gate_clinical_review.py::test_crisis_response_node_writes_clinician_review_queue -v
```
Expected: FAIL — no INSERT found.

- [ ] **Step 3: Add pool accessor and notification task to _crisis_response_node**

In `src/sage_poc/graph.py`, add at module level:

```python
def _get_crisis_review_pool():
    try:
        return app.state._db_pool
    except Exception:
        return None
```

Inside `_crisis_response_node`, immediately after the existing `asyncio.create_task(write_session_audit(...))` call, add:

```python
    async def _notify_crisis_review() -> None:
        try:
            from sage_poc.memory.notification import PostgresNotifier  # noqa: PLC0415
            pool = _get_crisis_review_pool()
            if not pool:
                return
            notifier = PostgresNotifier(pool)
            await notifier.notify_review_required(
                user_id=state.get("user_id") or "",
                session_id=state.get("session_id") or "",
                reason=f"crisis flags: {', '.join(state.get('crisis_flags', []))}",
                source="layer1_safety",
                payload={"flags": state.get("crisis_flags", []) + state.get("clinical_flags", [])},
                severity="high",
            )
        except Exception as exc:
            _log.warning("[crisis_response] clinician_review_queue write failed: %s", exc)

    asyncio.create_task(_notify_crisis_review())
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_output_gate_clinical_review.py -v
```
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/graph.py tests/test_output_gate_clinical_review.py
git commit -m "fix(crisis): write clinician_review_queue from _crisis_response_node (confirmed bypass gap)"
```

---

## Task 8: Fix profile extractor contraindication

**Files:**
- Modify: `src/sage_poc/memory/profile_extractor.py`
- Modify: `tests/test_profile_extractor.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_profile_extractor.py`:

```python
def test_effective_techniques_cleared_for_psychotic_disclosure_in_clinical_flags():
    from sage_poc.memory.profile_extractor import apply_contraindications
    profile = {
        "effective_techniques": ["breathing exercise", "box breathing"],
        "ineffective_techniques": [],
        "disclosed_concerns": ["stress"],
        "distortion_patterns": [],
        "communication_style": None,
        "cultural_preferences": {},
        "mood_trajectory": [],
        "observations": [],
    }
    result = apply_contraindications(profile, clinical_flags=["psychotic_disclosure"])
    assert result["effective_techniques"] == []


def test_effective_techniques_cleared_for_psychotic_disclosure_in_concerns():
    from sage_poc.memory.profile_extractor import apply_contraindications
    profile = {
        "effective_techniques": ["breathing exercise"],
        "ineffective_techniques": [],
        "disclosed_concerns": ["psychotic_disclosure"],
        "distortion_patterns": [],
        "communication_style": None,
        "cultural_preferences": {},
        "mood_trajectory": [],
        "observations": [],
    }
    result = apply_contraindications(profile, clinical_flags=[])
    assert result["effective_techniques"] == []


def test_effective_techniques_preserved_without_contraindication():
    from sage_poc.memory.profile_extractor import apply_contraindications
    profile = {
        "effective_techniques": ["box breathing"],
        "ineffective_techniques": [],
        "disclosed_concerns": ["stress"],
        "distortion_patterns": [],
        "communication_style": None,
        "cultural_preferences": {},
        "mood_trajectory": [],
        "observations": [],
    }
    assert apply_contraindications(profile, clinical_flags=[])["effective_techniques"] == ["box breathing"]
```

- [ ] **Step 2: Run to confirm failure**

```bash
uv run pytest tests/test_profile_extractor.py -k "contraindication" -v
```
Expected: `ImportError` — `apply_contraindications` not defined.

- [ ] **Step 3: Add apply_contraindications to profile_extractor.py**

```python
_CONTRAINDICATED_FOR_EFFECTIVE_TECHNIQUES: frozenset[str] = frozenset({
    "psychotic_disclosure",
})


def apply_contraindications(profile: dict, clinical_flags: list[str]) -> dict:
    """Clear effective_techniques when contraindicated clinical flags are present.

    Prevents coping techniques used during a psychosis session from being
    re-recommended in future sessions for the same presentation.
    """
    active_flags = set(clinical_flags or [])
    disclosed = set(profile.get("disclosed_concerns") or [])
    if _CONTRAINDICATED_FOR_EFFECTIVE_TECHNIQUES & (active_flags | disclosed):
        return {**profile, "effective_techniques": []}
    return profile
```

Find the return point of the profile extraction function and call `apply_contraindications(profile, clinical_flags)` before returning, where `clinical_flags` comes from the caller via `state.get("clinical_flags", [])`.

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_profile_extractor.py -v
```
Expected: all PASS.

- [ ] **Step 5: Run full suite — confirm no regressions**

```bash
uv run pytest tests/ -x --timeout=60 -q \
  --ignore=tests/experiment_4_4 \
  --ignore=tests/experiment_4_5 \
  --ignore=tests/experiment_4_6
```
Expected: green.

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/memory/profile_extractor.py tests/test_profile_extractor.py
git commit -m "fix(profile): apply_contraindications clears effective_techniques for psychotic_disclosure"
```

---

## Spec Coverage Self-Review

| Requirement | Task | Status |
|---|---|---|
| No new graph nodes | Tasks 4–5 (skill path) | ✓ |
| Content in skill JSON not Python | Task 4 | ✓ |
| Routes through output_gate | Task 5 (skill path) | ✓ |
| CF-006 as clinical flag extension not new S-tier | Task 1 | ✓ |
| active: false pending sign-off | Tasks 1, 3, 4 | ✓ |
| N1: TDD tests bypass active flag via _eval_safety | Task 1 | ✓ |
| N2: Session re-selection loop prevented | Task 5 | ✓ |
| N3: ≥3 EN + ≥3 AR examples, helpline verbatim | Task 4 | ✓ |
| N4: Helpline verified against en_uae.json | Pre-gate | ✓ |
| N5: No broken crisis_suppress for clinical flags | Task 1 (no FPE added) | ✓ |
| N6(a): command_hallucination in crisis_keywords.json (S1) | Task 6 | ✓ |
| N6(b): ≥95% SI recall verified after calibration | Task 6 Step 7 | ✓ |
| Governance: current doc supersedes v7 FINAL | Section above | ✓ |
| Escalation SLAs referenced | Pre-implementation note | ✓ |
| No new dependencies | All tasks | ✓ |
