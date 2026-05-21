# Doc 3a: Cultural Pre-generation Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement six missing pre-generation cultural adaptation rules (Items 8–12 from the v7 §5.5 gap analysis + Item 13 partial fix) that inject cultural framing into the LLM system prompt before generation.

**Architecture:** All six tasks write JSON rule files and/or edit existing ones using the established Rules Service pattern. Five tasks are pure JSON authoring (no code changes). One task (Task 6: code-switching) requires three targeted code changes: a backward-compatible schema extension, a 3-line engine addition, and moving code-switch detection from `compose_prompt` to `safety_check_node` (where all language signals belong). The budget cap for concurrent cultural injections is also wired in Task 6.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, existing `CulturalRule`/`PromptInjectionRule` schemas, `_eval_cultural` + `_eval_prompt_injection` engine functions, `compose_prompt` in `freeflow_respond.py`.

---

## Design Decisions (from code review feedback)

**Layer assignment:** All cultural rules inject at `"layer": "L5"` (User context, ~100 words, only when relevant). `"L2"` is reserved for intent instructions. Cultural context is a turn-specific user-context adaptation, not an intent instruction.

**Additive injection (not duplicative):** The L0 PERSONA already contains base Islamic framing (sabr, tawakkul, ibtila) and base collectivist framing as defaults. Cultural rules must inject turn-specific guidance that ADDS to the persona baseline, not re-state it. CU-IS-001 says "apply your Islamic framing to what the user said here"; it does not redefine sabr/tawakkul/ibtila. Same principle for CU-SH-001 and the collectivist baseline.

**No em dashes in rule content:** Rule content strings are injected into the LLM system prompt. Em dashes (—) in prompt content are a known source of em-dash mirroring in LLM output (eliminated in prior sprint). All rule content uses commas instead of em dashes.

**Cultural injection budget cap:** Multiple rules can fire simultaneously (e.g., Islamic + Ramadan + dialect + code-switch). Combined injection must stay under ~150 words (L5 budget with flex). Rules are sorted by a `priority` key inside their `action` dict (lower = higher priority); lower-priority rules are dropped when the budget is exceeded. Priority order: shame(1) > dialect(2) > code-switch(3) > Ramadan/Islamic(4) > collectivist/generic-religious(5-6).

**Code-switching detection in state:** Language signals are detected once at Node 1 (`safety_check_node`) and stored in state. Code-switching is a language detection signal. It must be detected at `safety_check_node`, stored as `code_switching: bool` in `SageState`, and read by `compose_prompt` — not recomputed at Node 7.

---

## Gap Analysis Reference

| # | Item | Status | Doc 3a Task |
|---|------|--------|------------|
| 11 | Substance use UAE legal context | Partial (PI-CF-001 missing legal text) | Task 1 |
| 13 | Non-Muslim expat handling | Partial (CU-IS-001 triggers on generic "god"/"prayer") | Task 2 |
| 12 | Shame (عيب) as cultural value | Partial (CU-CO-001 has keyword, no specific framing) | Task 3 |
| 10 | Ramadan/religious timing | Not implemented | Task 4 |
| 8  | Khaleeji dialect mirroring | Not implemented | Task 5 |
| 9  | Code-switching handling | Not implemented | Task 6 |

Items 3–6 (post-generation output checks) → Doc 3b.  
Items 7, 13 (full design decisions) → Doc 3c.

---

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `src/sage_poc/rules/data/prompt_injection/clinical_flag_adaptations.json` | Modify | PI-CF-001: add UAE legal context to substance_use adaptation |
| `src/sage_poc/rules/data/cultural/islamic_vocabulary.json` | Modify | CU-IS-001 v1.1.0: narrow to Islam-specific keywords; additive L5 content |
| `src/sage_poc/rules/data/cultural/generic_religious.json` | Create | CU-RG-001: generic religious/spiritual framing for non-Islamic users |
| `src/sage_poc/rules/data/cultural/shame_honour.json` | Create | CU-SH-001: shame as social bond framing (عيب/عار context), additive |
| `src/sage_poc/rules/data/cultural/ramadan_timing.json` | Create | CU-RR-001: Ramadan/fasting context, not clinical symptoms |
| `src/sage_poc/rules/data/cultural/dialect_mirroring.json` | Create | CU-DM-001: Khaleeji dialect mirroring instruction |
| `src/sage_poc/rules/data/cultural/code_switching.json` | Create | CU-CS-001: code-switching bilingual register mirroring |
| `src/sage_poc/rules/schemas.py` | Modify | CulturalRule: add `trigger_type` field; make `trigger_keywords` optional |
| `src/sage_poc/rules/engine.py` | Modify | `_eval_cultural`: handle `trigger_type == "code_switch"` |
| `src/sage_poc/state.py` | Modify | SageState: add `code_switching: bool` field |
| `src/sage_poc/nodes/safety_check.py` | Modify | Detect code_switching from raw_message; return in state dict |
| `src/sage_poc/nodes/freeflow_respond.py` | Modify | `compose_prompt`: read `code_switching` from state; add L5 budget cap |
| `tests/test_rules_integration.py` | Modify | Add tests for all six tasks |

---

## Task 1: PI-CF-001 UAE Legal Context

**Files:**
- Modify: `src/sage_poc/rules/data/prompt_injection/clinical_flag_adaptations.json`
- Test: `tests/test_rules_integration.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_rules_integration.py` after the existing substance_use test:

```python
def test_substance_use_uae_legal_context_injected():
    state = _freeflow_state(clinical_flags=["substance_use"])
    system_str, _ = compose_prompt(state)
    assert "legal" in system_str.lower() or "uae" in system_str.lower(), (
        "PI-CF-001 must include UAE legal context for substance use"
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
python -m pytest tests/test_rules_integration.py::test_substance_use_uae_legal_context_injected -v
```
Expected: FAIL — "legal" and "uae" not in current PI-CF-001 content.

- [ ] **Step 3: Edit PI-CF-001 action content**

In `src/sage_poc/rules/data/prompt_injection/clinical_flag_adaptations.json`, replace the PI-CF-001 `content` field value:

Old:
```json
"content": "CLINICAL ADAPTATION (substance use): The user has disclosed substance use. Use motivational interviewing language. Do NOT judge or suggest immediate cessation. Explore ambivalence gently."
```

New:
```json
"content": "CLINICAL ADAPTATION (substance use): The user has disclosed substance use. Use motivational interviewing language. Do NOT judge or suggest immediate cessation. Explore ambivalence gently. UAE LEGAL CONTEXT: Substance use carries serious legal risk in the UAE. Do NOT ask about quantities, suppliers, specific substances, or logistics. Do NOT suggest harm reduction strategies that assume legal access (needle exchanges, safe-use guidance). Focus on the emotional relationship with the substance, the feelings it manages, the role it plays, not the substance itself."
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_rules_integration.py -k "substance" -v
```
Expected: ALL substance-related tests pass (existing `test_clinical_adaptation_substance_injected_from_flag` + new test).

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/rules/data/prompt_injection/clinical_flag_adaptations.json tests/test_rules_integration.py
git commit -m "feat(rules): add UAE legal context to PI-CF-001 substance_use adaptation"
```

---

## Task 2: CU-IS-001 Refactor + CU-RG-001 (Non-Muslim Handling)

**Problem:** CU-IS-001 triggers on "god", "faith", "prayer", "religious", "spiritual" — universal terms that fire incorrectly for non-Muslim users. Fix: narrow CU-IS-001 to Islam-specific keywords; create CU-RG-001 for generic religious framing.

**Additive content principle:** L0 PERSONA already has base Islamic framing (sabr, tawakkul, ibtila). CU-IS-001 must NOT re-state the same definitions. It injects turn-specific instruction: "apply your Islamic framing to what the user expressed in this specific message."

**Files:**
- Modify: `src/sage_poc/rules/data/cultural/islamic_vocabulary.json`
- Create: `src/sage_poc/rules/data/cultural/generic_religious.json`
- Test: `tests/test_rules_integration.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rules_integration.py`:

```python
def test_islamic_framing_absent_for_generic_prayer():
    """'I pray to God every day' must NOT inject Islamic framing (no allah/quran etc)."""
    state = _freeflow_state(message_en="I pray to God every day")
    system_str, _ = compose_prompt(state)
    assert "sabr" not in system_str and "ibtila" not in system_str and "tawakkul" not in system_str, (
        "Generic prayer without Islamic keywords must not trigger CU-IS-001"
    )


def test_generic_religious_framing_fires_on_god_keyword():
    """Generic spiritual framing (CU-RG-001) must fire for universal religious language."""
    state = _freeflow_state(message_en="I pray to God every day")
    system_str, _ = compose_prompt(state)
    assert "spiritual" in system_str.lower() or "faith" in system_str.lower() or "religious" in system_str.lower(), (
        "CU-RG-001 must inject generic religious context for 'god'/'prayer' keywords"
    )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_rules_integration.py::test_islamic_framing_absent_for_generic_prayer tests/test_rules_integration.py::test_generic_religious_framing_fires_on_god_keyword -v
```
Expected: `test_islamic_framing_absent_for_generic_prayer` FAILS (currently "god" triggers CU-IS-001).
`test_generic_religious_framing_fires_on_god_keyword` FAILS (CU-RG-001 doesn't exist yet).

- [ ] **Step 3: Narrow CU-IS-001 and make its content additive**

Replace `src/sage_poc/rules/data/cultural/islamic_vocabulary.json` entirely:

```json
{
  "category": "cultural",
  "rules": [
    {
      "rule_id": "CU-IS-001",
      "version": "1.1.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Inject turn-specific Islamic framing guidance when user expresses Islam-specific faith context",
      "category": "cultural",
      "trigger_keywords": [
        "allah", "muslim", "islam", "islamic", "quran", "haram", "halal",
        "inshallah", "mashallah", "alhamdulillah", "subhanallah", "bismillah",
        "الله", "الإسلام", "مسلم", "صلاة", "دين", "إيمان",
        "الحمد لله", "إن شاء الله", "ما شاء الله", "سبحان الله"
      ],
      "language": "any",
      "action": {
        "type": "prompt_injection",
        "target": "system",
        "layer": "L5",
        "priority": 4,
        "content": "ISLAMIC CONTEXT (this turn): The user's message invokes their Islamic faith. Apply your Islamic framing (sabr, tawakkul, ibtila) directly to what they have expressed here. If they express spiritual guilt, feeling abandoned by God, or fear that their struggles indicate weak faith, explore this gently without reinforcing shame. Faith struggles are common and do not reflect a failure of faith."
      }
    }
  ]
}
```

- [ ] **Step 4: Create CU-RG-001 for generic religious framing**

Create `src/sage_poc/rules/data/cultural/generic_religious.json`:

```json
{
  "category": "cultural",
  "rules": [
    {
      "rule_id": "CU-RG-001",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Inject generic spiritual framing for universal religious language (non-Islam-specific)",
      "category": "cultural",
      "trigger_keywords": [
        "god", "faith", "prayer", "pray", "religious", "spiritual", "religion",
        "worship", "church", "temple", "synagogue", "divine", "blessing",
        "scripture", "bible", "torah", "hindu", "sikh", "buddhist"
      ],
      "language": "any",
      "action": {
        "type": "prompt_injection",
        "target": "system",
        "layer": "L5",
        "priority": 6,
        "content": "RELIGIOUS/SPIRITUAL CONTEXT (this turn): The user is framing their experience through faith or spirituality. Affirm their spiritual perspective without projecting a specific tradition. Do NOT impose Islamic-specific framing unless the user has specifically referenced Islam. Do NOT pathologise or minimise religious or spiritual belief or practice."
      }
    }
  ]
}
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_rules_integration.py -k "islamic or religious or faith" -v
```
Expected: ALL pass, including:
- `test_islamic_framing_injected_when_faith_keyword_present` (uses "allah" in message — still in CU-IS-001; new content references "sabr" and "ibtila" so assertion passes)
- `test_no_islamic_framing_without_faith_keyword` (plain anxious message — neither fires)
- `test_islamic_framing_absent_for_generic_prayer` (new)
- `test_generic_religious_framing_fires_on_god_keyword` (new)

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/rules/data/cultural/islamic_vocabulary.json src/sage_poc/rules/data/cultural/generic_religious.json tests/test_rules_integration.py
git commit -m "feat(rules): narrow CU-IS-001 to Islam-specific keywords; additive L5 content; add CU-RG-001"
```

---

## Task 3: CU-SH-001 (Shame as Cultural Value)

**Problem:** CU-CO-001 lists عيب as a collectivist trigger keyword but provides no specific handling for shame as a social bond mechanism. L0 PERSONA already has base collectivist framing. CU-SH-001 must be additive: it adds shame-specific guidance on top of the collectivist baseline, not re-state it.

**Files:**
- Create: `src/sage_poc/rules/data/cultural/shame_honour.json`
- Test: `tests/test_rules_integration.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_shame_framing_fires_on_arabic_ayb():
    """CU-SH-001 must inject shame-specific framing when عيب detected."""
    state = _freeflow_state(
        raw_message="عيب أن أتكلم عن مشاكلي",
        message_en="It is shameful to talk about my problems",
        detected_language="ar",
    )
    system_str, _ = compose_prompt(state)
    assert "shame" in system_str.lower() or "social" in system_str.lower() or "bond" in system_str.lower(), (
        "CU-SH-001 must fire on Arabic عيب and inject shame-specific framing"
    )


def test_shame_framing_fires_on_english_disgrace():
    """CU-SH-001 must fire on English shame/disgrace keywords."""
    state = _freeflow_state(message_en="I would bring disgrace to my family if they knew")
    system_str, _ = compose_prompt(state)
    assert "shame" in system_str.lower() or "social" in system_str.lower(), (
        "CU-SH-001 must fire on 'disgrace' keyword"
    )


def test_shame_framing_absent_for_generic_sad():
    """CU-SH-001 must NOT fire for generic sadness without shame/disgrace keywords."""
    state = _freeflow_state(message_en="I feel sad and hopeless today")
    system_str, _ = compose_prompt(state)
    assert "social bond" not in system_str.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_rules_integration.py::test_shame_framing_fires_on_arabic_ayb tests/test_rules_integration.py::test_shame_framing_fires_on_english_disgrace tests/test_rules_integration.py::test_shame_framing_absent_for_generic_sad -v
```
Expected: First two FAIL (rule doesn't exist), third PASS.

- [ ] **Step 3: Create CU-SH-001**

Create `src/sage_poc/rules/data/cultural/shame_honour.json`:

```json
{
  "category": "cultural",
  "rules": [
    {
      "rule_id": "CU-SH-001",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Inject shame-specific framing (additive to collectivist baseline) when عيب/عار or disgrace context detected",
      "category": "cultural",
      "trigger_keywords": [
        "عيب", "عار", "فضيحة", "خزي",
        "disgrace", "dishonour", "dishonor", "bring shame", "family shame",
        "community shame", "ashamed of myself", "they would be ashamed"
      ],
      "language": "any",
      "action": {
        "type": "prompt_injection",
        "target": "system",
        "layer": "L5",
        "priority": 1,
        "content": "SHAME CONTEXT (this turn): The user has expressed shame (عيب/عار) specifically. Apply your collectivist framing baseline. Add: in Gulf culture, shame functions as a social bond signal, not only personal failure. It signals awareness of collective standards and relational consequences. Do NOT push the user to simply overcome or dismiss it. Help them find a path that honours both their integrity and their relationships."
      }
    }
  ]
}
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_rules_integration.py -k "shame" -v
```
Expected: ALL three tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/rules/data/cultural/shame_honour.json tests/test_rules_integration.py
git commit -m "feat(rules): add CU-SH-001 shame-as-social-bond cultural framing (additive L5)"
```

---

## Task 4: CU-RR-001 (Ramadan / Religious Timing)

**Problem:** Fasting fatigue and sleep disruption during Ramadan are cultural norms, not clinical symptoms. No rule exists to contextualise them.

**Files:**
- Create: `src/sage_poc/rules/data/cultural/ramadan_timing.json`
- Test: `tests/test_rules_integration.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_ramadan_framing_fires_on_ramadan_keyword():
    """CU-RR-001 must inject Ramadan context when 'Ramadan' or 'fasting' detected."""
    state = _freeflow_state(message_en="I'm exhausted and irritable during Ramadan")
    system_str, _ = compose_prompt(state)
    assert "ramadan" in system_str.lower() or "fasting" in system_str.lower(), (
        "CU-RR-001 must inject Ramadan framing for 'Ramadan' keyword"
    )


def test_ramadan_framing_fires_on_arabic_ramadan():
    """CU-RR-001 must fire on Arabic رمضان keyword via text_ar path."""
    state = _freeflow_state(
        raw_message="رمضان هذه السنة متعب جداً",
        message_en="Ramadan this year is very tiring",
        detected_language="ar",
    )
    system_str, _ = compose_prompt(state)
    assert "ramadan" in system_str.lower() or "fasting" in system_str.lower()


def test_ramadan_framing_absent_without_keyword():
    """CU-RR-001 must NOT fire for generic tiredness without Ramadan/fasting keywords."""
    state = _freeflow_state(message_en="I'm exhausted and can't sleep")
    system_str, _ = compose_prompt(state)
    assert "ramadan" not in system_str.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_rules_integration.py::test_ramadan_framing_fires_on_ramadan_keyword tests/test_rules_integration.py::test_ramadan_framing_fires_on_arabic_ramadan tests/test_rules_integration.py::test_ramadan_framing_absent_without_keyword -v
```
Expected: First two FAIL, third PASS.

- [ ] **Step 3: Create CU-RR-001**

Create `src/sage_poc/rules/data/cultural/ramadan_timing.json`:

```json
{
  "category": "cultural",
  "rules": [
    {
      "rule_id": "CU-RR-001",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Inject Ramadan/religious timing context: fasting fatigue is a cultural norm, not a clinical symptom",
      "category": "cultural",
      "trigger_keywords": [
        "ramadan", "رمضان", "fasting", "صيام", "صوم",
        "iftar", "إفطار", "suhoor", "سحور",
        "eid", "عيد", "laylat al-qadr", "ليلة القدر"
      ],
      "language": "any",
      "action": {
        "type": "prompt_injection",
        "target": "system",
        "layer": "L5",
        "priority": 4,
        "content": "RAMADAN CONTEXT (this turn): The user has referenced Ramadan or religious fasting. During Ramadan, fatigue, sleep disruption, irritability, and reduced concentration are expected cultural norms from fasting and night worship, not necessarily clinical symptoms. Do NOT pathologise these as signs of depression or anxiety without additional context. Acknowledge the spiritual significance. If symptoms appear severe or distress seems beyond what the user describes as normal for them, gently explore whether further support would help."
      }
    }
  ]
}
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_rules_integration.py -k "ramadan" -v
```
Expected: ALL three tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/rules/data/cultural/ramadan_timing.json tests/test_rules_integration.py
git commit -m "feat(rules): add CU-RR-001 Ramadan and religious timing cultural context (L5)"
```

---

## Task 5: CU-DM-001 (Khaleeji Dialect Mirroring)

**Important:** This rule MUST be in the `cultural` category (not `prompt_injection`) because Khaleeji markers are Arabic script. The `_eval_cultural` function routes Arabic-script keywords through `text_ar` (the `raw_message` when `detected_language=="ar"`). The `_eval_prompt_injection` function only checks `text_lower` (English), so Arabic keywords would never fire there.

**Files:**
- Create: `src/sage_poc/rules/data/cultural/dialect_mirroring.json`
- Test: `tests/test_rules_integration.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_dialect_mirroring_fires_on_khaleeji_wayed():
    """CU-DM-001 must inject dialect instruction when Khaleeji وايد detected."""
    state = _freeflow_state(
        raw_message="أنا وايد تعبان اليوم",
        message_en="I am very tired today",
        detected_language="ar",
    )
    system_str, _ = compose_prompt(state)
    assert "DIALECT" in system_str or "khaleeji" in system_str.lower(), (
        "CU-DM-001 must inject dialect instruction for Khaleeji وايد"
    )


def test_dialect_mirroring_fires_on_shloun():
    """CU-DM-001 must fire on other Khaleeji markers like شلون."""
    state = _freeflow_state(
        raw_message="شلون أتعامل مع هذا الموضوع؟",
        message_en="How do I deal with this topic?",
        detected_language="ar",
    )
    system_str, _ = compose_prompt(state)
    assert "DIALECT" in system_str or "khaleeji" in system_str.lower()


def test_dialect_mirroring_absent_for_msa():
    """CU-DM-001 must NOT fire for formal MSA without Khaleeji markers."""
    state = _freeflow_state(
        raw_message="أشعر بالقلق الشديد هذا اليوم",
        message_en="I feel intense anxiety today",
        detected_language="ar",
    )
    system_str, _ = compose_prompt(state)
    assert "DIALECT" not in system_str
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_rules_integration.py::test_dialect_mirroring_fires_on_khaleeji_wayed tests/test_rules_integration.py::test_dialect_mirroring_fires_on_shloun tests/test_rules_integration.py::test_dialect_mirroring_absent_for_msa -v
```
Expected: First two FAIL, third PASS.

- [ ] **Step 3: Create CU-DM-001**

Create `src/sage_poc/rules/data/cultural/dialect_mirroring.json`:

```json
{
  "category": "cultural",
  "rules": [
    {
      "rule_id": "CU-DM-001",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Inject Khaleeji dialect mirroring instruction when Gulf Arabic dialect markers detected",
      "category": "cultural",
      "trigger_keywords": [
        "وايد", "زين", "شلون", "وش", "يبغى", "ابغى", "جذي", "ابي",
        "ليش", "واجد", "عاد", "مب", "ماكو", "اكو", "هاه", "ايش"
      ],
      "language": "any",
      "action": {
        "type": "prompt_injection",
        "target": "system",
        "layer": "L5",
        "priority": 2,
        "content": "DIALECT (this turn): The user is writing in Khaleeji Gulf Arabic dialect. Mirror their dialect in your Arabic responses. Do NOT respond in formal Modern Standard Arabic (MSA). Use natural Khaleeji vocabulary and register. Prefer 'وايد' over 'كثير', 'زين' over 'حسن', 'شلون' over 'كيف حالك'. Match the warmth and naturalness of the user's conversational register."
      }
    }
  ]
}
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_rules_integration.py -k "dialect" -v
```
Expected: ALL three tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/rules/data/cultural/dialect_mirroring.json tests/test_rules_integration.py
git commit -m "feat(rules): add CU-DM-001 Khaleeji dialect mirroring pre-generation injection (L5)"
```

---

## Task 6: CU-CS-001 Code-Switching (Schema + State + Engine + Compose + Budget Cap)

**This task requires four code changes plus one JSON file.** All code changes are backward-compatible.

1. `CulturalRule` schema: add `trigger_type` (default `"keyword_match"`); make `trigger_keywords` optional (default `[]`)
2. `SageState`: add `code_switching: bool` field
3. `safety_check_node`: detect `code_switching` from `raw_message` at Node 1; return it in state
4. `_eval_cultural` engine: handle `trigger_type == "code_switch"` branch before keyword loop
5. `compose_prompt`: read `code_switching` from state; add L5 budget cap (sort by priority, cap at ~150 words)

**Files:**
- Modify: `src/sage_poc/rules/schemas.py` (CulturalRule class)
- Modify: `src/sage_poc/state.py` (SageState TypedDict)
- Modify: `src/sage_poc/nodes/safety_check.py` (detect code_switching)
- Modify: `src/sage_poc/rules/engine.py` (`_eval_cultural`)
- Modify: `src/sage_poc/nodes/freeflow_respond.py` (`compose_prompt`)
- Create: `src/sage_poc/rules/data/cultural/code_switching.json`
- Test: `tests/test_rules_integration.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rules_integration.py`:

```python
def test_safety_check_node_detects_code_switching():
    """safety_check_node must set code_switching=True for mixed Arabic/English messages."""
    state = _state("أنا feeling really stressed اليوم")
    result = safety_check_node(state)
    assert result.get("code_switching") is True, (
        "safety_check_node must detect mixed Arabic+Latin script and set code_switching=True"
    )


def test_safety_check_node_code_switching_false_for_pure_arabic():
    """safety_check_node must set code_switching=False for pure Arabic."""
    state = _state("أنا وايد تعبان اليوم")
    result = safety_check_node(state)
    assert result.get("code_switching") is False


def test_safety_check_node_code_switching_false_for_pure_english():
    """safety_check_node must set code_switching=False for pure English."""
    state = _state("I feel really anxious today")
    result = safety_check_node(state)
    assert result.get("code_switching") is False


def test_code_switch_rule_fires_on_mixed_arabic_english():
    """CU-CS-001 must fire when state has code_switching=True."""
    state = _freeflow_state(
        raw_message="أنا feeling really stressed اليوم",
        message_en="I am feeling really stressed today",
        detected_language="ar",
        code_switching=True,
    )
    system_str, _ = compose_prompt(state)
    assert "CODE-SWITCHING" in system_str, (
        "CU-CS-001 must inject code-switching instruction when code_switching=True in state"
    )


def test_code_switch_rule_absent_for_pure_arabic():
    """CU-CS-001 must NOT fire when state has code_switching=False."""
    state = _freeflow_state(
        raw_message="أنا وايد تعبان اليوم",
        message_en="I am very tired today",
        detected_language="ar",
        code_switching=False,
    )
    system_str, _ = compose_prompt(state)
    assert "CODE-SWITCHING" not in system_str


def test_cultural_rule_schema_accepts_code_switch_trigger_type():
    """CulturalRule schema must accept trigger_type='code_switch' with empty trigger_keywords."""
    from sage_poc.rules.schemas import CulturalRule
    rule = CulturalRule.model_validate({
        "rule_id": "TEST-CS-001",
        "category": "cultural",
        "effective_date": "2026-05-21",
        "trigger_type": "code_switch",
        "trigger_keywords": [],
        "action": {"type": "test"},
    })
    assert rule.trigger_type == "code_switch"
    assert rule.trigger_keywords == []


def test_existing_cultural_rules_unaffected_by_schema_change():
    """Existing rules with no trigger_type field must default to keyword_match and still fire."""
    from sage_poc.rules.loader import reload_all
    reload_all()
    state = _freeflow_state(message_en="I feel my faith in allah is fading")
    system_str, _ = compose_prompt(state)
    assert "ISLAMIC" in system_str or "sabr" in system_str or "ibtila" in system_str, (
        "Existing CU-IS-001 must still fire after schema change (backward compat)"
    )
```

Note: `_freeflow_state` must be updated in the test file to include `code_switching: False` in its base state dict (to match the new SageState field). Update the helper:

```python
def _freeflow_state(**overrides):
    base = {
        ...
        "code_switching": False,  # ADD THIS LINE
        ...
    }
    base.update(overrides)
    return base
```

Also update `_state()` helper similarly:
```python
def _state(raw_message, clinical_flags=None):
    return {
        ...
        "code_switching": False,  # ADD THIS LINE
        ...
    }
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_rules_integration.py::test_safety_check_node_detects_code_switching tests/test_rules_integration.py::test_cultural_rule_schema_accepts_code_switch_trigger_type -v
```
Expected: Both FAIL — `code_switching` not in state dict and schema field doesn't exist yet.

- [ ] **Step 3: Add `code_switching` to SageState**

In `src/sage_poc/state.py`, add the field after `distress_trajectory`:

```python
    crisis_occurred_this_session: bool
    distress_trajectory: list[int]
    code_switching: bool          # True when raw_message contains both Arabic script and Latin letters
```

- [ ] **Step 4: Update safety_check_node to detect code_switching**

In `src/sage_poc/nodes/safety_check.py`, add at the top of the file (after existing imports):

```python
import re
_HAS_ARABIC_RE = re.compile(r'[؀-ۿ]')
_HAS_LATIN_RE = re.compile(r'[A-Za-z]')
```

In `safety_check_node`, add one line after `raw = state["raw_message"]`:

```python
    raw = state["raw_message"]
    code_switching = bool(_HAS_ARABIC_RE.search(raw) and _HAS_LATIN_RE.search(raw))
```

Add `"code_switching": code_switching` to the return dict:

```python
    return {
        "detected_language": lang,
        "message_en": message_en,
        "is_safe": len(new_crisis_flags) == 0,
        "crisis_flags": new_crisis_flags,
        "clinical_flags": all_clinical,
        "distress_trajectory": trajectory,
        "code_switching": code_switching,
        "path": state["path"] + ["safety_check"],
    }
```

- [ ] **Step 5: Update CulturalRule schema**

In `src/sage_poc/rules/schemas.py`, replace the `CulturalRule` class:

```python
class CulturalRule(BaseModel):
    rule_id: str
    version: str = "1.0.0"
    category: Literal["cultural"]
    authored_by: str = "sage_clinics"
    approved_by: str | None = None
    effective_date: str
    active: bool = True
    description: str = ""
    trigger_type: Literal["keyword_match", "code_switch"] = "keyword_match"
    trigger_keywords: list[str] = []
    language: Literal["en", "ar", "any"] = "any"
    action: dict
```

- [ ] **Step 6: Update `_eval_cultural` to handle code_switch trigger**

In `src/sage_poc/rules/engine.py`, replace the `_eval_cultural` function:

```python
def _eval_cultural(rules: list[CulturalRule], context: dict) -> EvalResult:
    """
    Accumulate all cultural rules whose trigger condition matches.

    context keys:
      text (str)            — user message (English)
      text_ar (str | None)  — original Arabic text (if language == "ar")
      language (str)        — "en" | "ar"
      code_switch (bool)    — True when raw_message contains both Arabic and Latin characters
    """
    text_lower = normalize_text(context.get("text", ""))
    text_ar = context.get("text_ar") or ""
    norm_ar = normalize_arabic(text_ar) if text_ar else ""
    language = context.get("language", "en")
    code_switch: bool = context.get("code_switch", False)

    result = EvalResult()
    for rule in rules:
        if rule.language not in ("any", language):
            continue

        if rule.trigger_type == "code_switch":
            if code_switch:
                result.fired.append(FiredRule(
                    rule_id=rule.rule_id,
                    version=rule.version,
                    action=rule.action,
                ))
            continue

        # trigger_type == "keyword_match" (default)
        matched = False
        for kw in rule.trigger_keywords:
            is_arabic_kw = any('؀' <= ch <= 'ۿ' for ch in kw)
            if is_arabic_kw:
                if norm_ar and normalize_arabic(kw) in norm_ar:
                    matched = True
                    break
            else:
                if kw.lower() in text_lower:
                    matched = True
                    break
        if matched:
            result.fired.append(FiredRule(
                rule_id=rule.rule_id,
                version=rule.version,
                action=rule.action,
            ))

    return result
```

- [ ] **Step 7: Update `compose_prompt` — read code_switching from state + add budget cap**

In `src/sage_poc/nodes/freeflow_respond.py`, add a module-level constant after `PERSONA`:

```python
_CULTURAL_BUDGET_WORDS = 150
```

Replace the cultural evaluation block in `compose_prompt` (currently lines 61–68):

```python
    code_switch = state.get("code_switching", False)

    cultural_result = rules_engine.evaluate("cultural", {
        "text": message_en,
        "text_ar": state.get("raw_message") if language == "ar" else None,
        "language": language,
        "code_switch": code_switch,
    })

    # L5 budget cap: sort by priority (lower = higher priority), cap at ~150 words
    cultural_actions = sorted(
        [a for a in cultural_result.actions if a.get("target") == "system"],
        key=lambda a: a.get("priority", 5),
    )
    word_count = 0
    for action in cultural_actions:
        content = action["content"]
        words = len(content.split())
        if word_count + words <= _CULTURAL_BUDGET_WORDS or word_count == 0:
            system_parts.append(content)
            word_count += words
        else:
            break
```

The `or word_count == 0` guard ensures at least one cultural rule fires even if a single rule exceeds the budget on its own.

- [ ] **Step 8: Create CU-CS-001**

Create `src/sage_poc/rules/data/cultural/code_switching.json`:

```json
{
  "category": "cultural",
  "rules": [
    {
      "rule_id": "CU-CS-001",
      "version": "1.0.0",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-21",
      "active": true,
      "description": "Inject code-switching instruction when user mixes Arabic script and Latin letters in one message",
      "category": "cultural",
      "trigger_type": "code_switch",
      "trigger_keywords": [],
      "language": "any",
      "action": {
        "type": "prompt_injection",
        "target": "system",
        "layer": "L5",
        "priority": 3,
        "content": "CODE-SWITCHING (this turn): The user is mixing Arabic and English in the same message. This is natural for UAE digital natives. Mirror their bilingual register: blend Arabic and English naturally in your response. Do NOT force a single language. Do NOT comment on or correct their language choice."
      }
    }
  ]
}
```

- [ ] **Step 9: Run the full test suite**

```bash
python -m pytest tests/test_rules_integration.py -v
```
Expected: ALL tests pass — new code-switching tests pass + all existing tests pass (backward compat verified).

- [ ] **Step 10: Commit**

```bash
git add src/sage_poc/state.py src/sage_poc/nodes/safety_check.py src/sage_poc/rules/schemas.py src/sage_poc/rules/engine.py src/sage_poc/nodes/freeflow_respond.py src/sage_poc/rules/data/cultural/code_switching.json tests/test_rules_integration.py
git commit -m "feat(rules): add CU-CS-001 code-switching; detect at safety_check; L5 budget cap in compose_prompt"
```

---

## Final Verification

- [ ] **Run full test suite**

```bash
python -m pytest tests/ -v
```
Expected: All tests pass (511 existing + new Doc 3a tests).

- [ ] **Verify all six rule IDs exist and are active**

```bash
python -c "
from sage_poc.rules.loader import reload_all, load_rules
reload_all()
for cat in ['cultural', 'prompt_injection']:
    rules = load_rules(cat)
    for r in rules:
        print(r.rule_id, r.active, getattr(r, 'trigger_type', 'n/a'))
"
```
Expected: CU-IS-001, CU-RG-001, CU-SH-001, CU-RR-001, CU-DM-001, CU-CS-001, PI-CF-001 (updated) all appear with `active=True`.

- [ ] **Verify budget cap with a multi-rule trigger**

```bash
python -c "
from sage_poc.rules import engine as rules_engine
from sage_poc.rules.loader import reload_all
reload_all()
result = rules_engine.evaluate('cultural', {
    'text': 'I feel disgrace and shame',
    'text_ar': 'عيب وايد رمضان',
    'language': 'ar',
    'code_switch': True,
})
print('Fired:', [r.rule_id for r in result.fired])
print('Priority order:', sorted(
    [r.action.get('priority', 5) for r in result.fired]
))
"
```
Expected: Multiple rules fire; priority values are present in each action dict.

---

## Self-Review Checklist

**Spec coverage:**
- Item 11 (PI-CF-001 UAE legal) → Task 1 ✅
- Item 13 partial (CU-IS-001 refactor + CU-RG-001) → Task 2 ✅
- Item 12 (CU-SH-001 shame) → Task 3 ✅
- Item 10 (CU-RR-001 Ramadan) → Task 4 ✅
- Item 8 (CU-DM-001 Khaleeji) → Task 5 ✅
- Item 9 (CU-CS-001 code-switch) → Task 6 ✅

**Design decisions implemented:**
- All cultural rules use `"layer": "L5"` ✅
- CU-IS-001 and CU-SH-001 are additive (no duplication of L0 PERSONA content) ✅
- No em dashes in any rule content string ✅
- Code-switching detected at Node 1 (safety_check), stored in SageState, read at Node 7 ✅
- Budget cap in compose_prompt (150 words, priority-ordered) ✅

**Backward compatibility:**
- `trigger_keywords: list[str] = []` — existing rules all provide explicit non-empty list, Pydantic ignores default ✅
- `trigger_type: ... = "keyword_match"` — existing rules get default, engine keyword loop unchanged ✅
- `code_switch` key defaults to `False` in engine context — no change for messages without Arabic ✅
- `code_switching: bool` in SageState — all existing `_state()` and `_freeflow_state()` helpers must add `"code_switching": False` to their base dicts ✅

**No em dashes in rule content:** Scan every content field before committing. Use commas instead: `sabr (صبر, patient perseverance)` not `sabr (صبر — patient perseverance)`. ✅
