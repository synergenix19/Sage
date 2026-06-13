# Cultural Localization Fix Plan
**Branch:** `fix/cu-dm-001-arch-alignment`
**Date:** 2026-06-07
**Status:** Approved — ready to execute

---

## Design History

CU-DM-001 was authored on **2026-05-22** when the cultural rules engine was first built. At that point the Phase 1 Khaleeji Translation plan (`2026-05-28`) had not run — `language.py` used a bare MSA translation prompt. CU-DM-001's "MUST respond in Arabic" was the **primary delivery mechanism** for Arabic responses before EN-first/AR-delivery was operational.

The Phase 1 plan then correctly fixed the translation prompt in `language.py` to use Khaleeji register — but CU-DM-001 was never updated to reflect that the translation layer now owns delivery. It became a fossil from the pre-translation era, directly contradicting §3.1. The arch doc §17.1 noted "these are LLM instructions, not lexical enforcement" — accurate for self-hosted Falcon but false for GPT-4o on Railway/Vercel, which follows the literal instruction and generates Arabic into `response_en`, breaking the entire output_gate validation chain downstream.

---

## Already Implemented — Do Not Redo

The following are live in the current codebase. The plan makes no changes to any of these.

| What | Where | Commit / Date |
|---|---|---|
| Khaleeji translation prompt (`translate_to_arabic`, `async_translate_to_arabic`) | `language.py:80–123` | Phase 1, 2026-05-28 |
| Arabizi crisis detection: SK-AZ-001 (explicit SI), SK-AZ-002 (passive SI) via `text_raw` | `rules/data/safety/crisis_keywords.json`, `passive_si_patterns.json` | 18a7a17 + 0776268 |
| `lang="az"` routing to `text_raw` in rules engine | `rules/engine.py:94–100` | 0776268 |
| Two-path S3: `check_s3_bilingual(message_en, text_ar)` | `safety_check.py:139` | 0776268 |
| Code-switching cultural rule CU-CS-001 (fires when Arabic Unicode + Latin in same message) | `rules/data/cultural/code_switching.json` | 2026-05-21 |
| Arabic Tier 1 keyword pass — `skill_select.py` also checks `raw_message` for `detected_language="ar"` | `nodes/skill_select.py:134–146` | ac0fd72, 2026-06-05 |
| All 27 skills have Arabic examples at position [0] | `skills/*.json` | Various |
| All 27 skills have `cultural_overrides` within 200w budget | `skills/*.json` | Various |
| 20 Arabic knowledge corpus articles | `data/knowledge_corpus/ar/` | Various |

---

## Arabizi Coverage — Accurate Scope Statement

**Crisis detection: COVERED.** SK-AZ-001 and SK-AZ-002 evaluate against `text_raw` via `lang="az"` routing. Arabizi crisis phrases reach the safety gate regardless of `detect_language()` output. This is load-bearing.

**Mixed Unicode/Latin messages (code-switching): COVERED.** When a message contains both Arabic Unicode characters and Latin letters, `code_switching=True` fires in `safety_check.py`, and CU-CS-001 injects "Mirror their bilingual register" into the prompt. `detected_language="ar"` (Arabic Unicode override), so CU-DM-001 also fires. Both rules apply.

**Pure Arabizi (Latin-script Arabic, no Arabic Unicode): Cultural register NOT triggered.** Pure Arabizi (`"ta3abt wallah"`) classifies as `detected_language="en"`. CU-DM-001 and CU-CS-001 both require Arabic Unicode to fire. The user receives an English response with no Khaleeji register calibration. Crisis detection still works via SK-AZ-001/002.

**Pure Arabizi cultural register: Named deferred scope decision.** Arch doc §522 (2026-06-01) names this explicitly as out of POC scope. Transliteration requires CAMeL Tools or equivalent. There is no Task 1B.ii in this plan. This is not a gap to patch before Gitex — it is an architectural boundary with a named date and rationale.

---

## Task 1A — Rewrite `dialect_mirroring.json`

**File:** `sage-poc/src/sage_poc/rules/data/cultural/dialect_mirroring.json`

**Responsibility boundary:** CU-DM-001 owns register calibration only. The English-generation directive moves to the L0 extension (Task 1B). No duplication between layers per §5.6 progressive disclosure.

**Full replacement:**

```json
{
  "category": "cultural",
  "rules": [
    {
      "rule_id": "CU-DM-001",
      "version": "1.2.0",
      "last_updated": "2026-06-07",
      "authored_by": "sage_clinics",
      "effective_date": "2026-05-22",
      "active": true,
      "description": "Khaleeji register calibration for Arabic sessions — fires after L0 establishes generation contract. Trimmed from v1.1: English-generation directive moved to L0 extension (composer.py) to avoid contradicting EN-first architecture.",
      "category": "cultural",
      "trigger_keywords": [],
      "language": "ar",
      "action": {
        "type": "prompt_injection",
        "target": "system",
        "layer": "L5",
        "priority": 2,
        "content": "KHALEEJI REGISTER: The user is writing in Gulf Arabic. Calibrate emotional warmth, phrasing rhythm, and vocabulary for natural Khaleeji translation. If the user uses markers (وايد، زين، شلونك), match their warmth level. Avoid clinical or formal MSA phrasing."
      }
    }
  ]
}
```

**Tests to add** (`tests/test_rules_engine.py` or `tests/test_cultural_rules.py`):

```python
def test_cu_dm_001_fires_arabic_turn():
    result = rules_engine.evaluate("cultural", {
        "text": "hello", "text_ar": "مرحبا",
        "language": "ar", "code_switch": False,
    })
    fired_contents = [a["content"] for a in result.actions if a.get("target") == "system"]
    dm = next((c for c in fired_contents if "KHALEEJI" in c or "وايد" in c), None)
    assert dm is not None, "CU-DM-001 did not fire for Arabic turn"

def test_cu_dm_001_no_generation_language_instruction():
    result = rules_engine.evaluate("cultural", {
        "text": "hello", "text_ar": "مرحبا",
        "language": "ar", "code_switch": False,
    })
    fired_contents = [a["content"] for a in result.actions if a.get("target") == "system"]
    dm = next((c for c in fired_contents if "KHALEEJI" in c or "وايد" in c), "")
    assert "MUST respond in Arabic" not in dm
    assert "generate your response in English" not in dm.lower()
    assert "translation layer handles delivery" not in dm

def test_cu_dm_001_does_not_fire_english_turn():
    result = rules_engine.evaluate("cultural", {
        "text": "hello", "text_ar": None,
        "language": "en", "code_switch": False,
    })
    fired_contents = [a["content"] for a in result.actions if a.get("target") == "system"]
    assert not any("KHALEEJI" in c for c in fired_contents)
```

**Commit:** `fix(cultural-rules): CU-DM-001 v1.2 — trim to register calibration, remove generation-language instruction`

---

## Task 1B — L0 Arabic Register Block in `composer.py`

**File:** `sage-poc/src/sage_poc/prompts/composer.py`

The L0 extension is the **sole authoritative location** for the English-generation contract. It fires before the cultural rules block, ensuring the LLM knows the translation architecture regardless of which cultural rules fire on a given turn.

Note on layering: CU-CS-001 already handles mixed Arabic+Latin messages by injecting "Mirror their bilingual register" at L5. This is correct and untouched. Task 1B.i adds the EN-generation directive at L0 specifically for pure Arabic sessions (`detected_language="ar"`), which is the scenario where CU-DM-001's "MUST respond in Arabic" has been firing.

**Change:** In `compose_prompt()`, after lines 348–349:

```python
    # L0: Base persona (always included)
    system_parts = [_build_l0_system_block()]
    layers.append("persona")

    # L0 extension: Arabic session generation contract.
    # Sole authoritative location for the EN-first directive — CU-DM-001 must not
    # restate this after v1.2 trim. Fires before cultural rules so the LLM sees
    # the translation architecture before register calibration instructions arrive.
    if language == "ar":
        system_parts.append(
            "ARABIC SESSION: This user writes in Arabic. Your response will be "
            "translated to Khaleeji Arabic by the delivery layer. Generate in English "
            "with warmth and conversational rhythm that translates naturally to Gulf "
            "Arabic, not clinical or formal phrasing. Do not write in Arabic."
        )
        layers.append("arabic_register")
```

**Tests to add** (`tests/test_composer.py`):

```python
def test_compose_prompt_arabic_session_register_cue():
    state = _make_minimal_state(detected_language="ar", message_en="I am feeling low")
    system_str, _, layers = compose_prompt(state)
    assert "arabic_register" in layers
    assert "Do not write in Arabic" in system_str
    # L0 extension must precede CU-DM-001 (KHALEEJI REGISTER block)
    if "KHALEEJI REGISTER" in system_str:
        assert system_str.index("ARABIC SESSION") < system_str.index("KHALEEJI REGISTER")

def test_compose_prompt_english_no_register_cue():
    state = _make_minimal_state(detected_language="en", message_en="I feel anxious")
    system_str, _, layers = compose_prompt(state)
    assert "arabic_register" not in layers
    assert "ARABIC SESSION" not in system_str

def test_compose_prompt_arabic_no_duplicate_generation_directive():
    """CU-DM-001 v1.2 must not restate the EN-generation directive."""
    state = _make_minimal_state(detected_language="ar", message_en="hello")
    system_str, _, _ = compose_prompt(state)
    # "Do not write in Arabic" appears exactly once — from L0 extension only
    assert system_str.count("Do not write in Arabic") == 1
```

**Commit:** `fix(composer): add L0 Arabic register extension — authoritative EN-generation directive`

---

## Task 1C — `response_en` Arabic Guard in `output_gate.py`

**File:** `sage-poc/src/sage_poc/nodes/output_gate.py`

### Step 1 — Add Arabic character regex (after line 49, near `_BANNED_OPENER_RE`)

```python
_HAS_ARABIC_RE = re.compile(r"[؀-ۿ]")
```

### Step 2 — Add ratio-based guard after `response_en` is resolved (after line 180)

Ratio check rather than any-presence: preserves legitimate code-switching in `response_en` (e.g., `"I understand you're feeling ضغط at work"` is ~5% Arabic chars, well below threshold) while catching full Arabic generation (typically >80% Arabic chars):

```python
    # Guard: detect whether response_en is predominantly Arabic.
    # Ratio check (>40%) preserves legitimate code-switched responses while
    # catching the CU-DM-001 regression case where LLM generated fully Arabic.
    # English validators and translation are both skipped on trigger:
    #   - _BANNED_OPENER_RE and cultural output rules use English-only patterns
    #   - Translating already-Arabic text produces garbled output
    # WARNING log treats guard firing as a regression signal, not a silent fallback.
    _arabic_chars = len(_HAS_ARABIC_RE.findall(response_en))
    _total_chars = len(response_en.strip())
    _response_en_is_arabic = (
        lang == "ar"
        and gate_path not in ("scope_refusal", "jailbreak")
        and _total_chars > 0
        and (_arabic_chars / _total_chars) > 0.4
    )
    if _response_en_is_arabic:
        _log.warning(
            "[output_gate] response_en is predominantly Arabic "
            "(ratio=%.2f, session=%s, gate=%s) — "
            "skipping EN validators and translation; audit for CU-DM-001 regression",
            _arabic_chars / _total_chars, session_id, gate_path,
        )
```

### Step 3 — Patch cultural output check (line 182)

**Before:** `if gate_path not in ("scope_refusal", "jailbreak"):`
**After:** `if gate_path not in ("scope_refusal", "jailbreak") and not _response_en_is_arabic:`

### Step 4 — Patch banned opener check (line 251)

**Before:** `if gate_path not in ("scope_refusal", "jailbreak") and response_en:`
**After:** `if gate_path not in ("scope_refusal", "jailbreak") and response_en and not _response_en_is_arabic:`

### Step 5 — Patch translation (line 306)

**Before:**
```python
    if lang == "ar":
        final_response = await async_translate_to_arabic(response_en)
    else:
        final_response = response_en
```
**After:**
```python
    if lang == "ar" and not _response_en_is_arabic:
        final_response = await async_translate_to_arabic(response_en)
    else:
        final_response = response_en
```

**Tests to add** (`tests/test_output_gate.py`):

```python
@pytest.mark.asyncio
async def test_output_gate_arabic_response_en_skips_translation():
    """Predominantly Arabic response_en must skip async_translate_to_arabic."""
    arabic_text = "أنا هنا معك. شو اللي يساعدك؟"  # >40% Arabic chars
    state = _make_output_gate_state(detected_language="ar", response_en=arabic_text)
    with patch("sage_poc.nodes.output_gate.async_translate_to_arabic") as mock_translate:
        result = await output_gate_node(state)
    mock_translate.assert_not_called()
    assert result["response"] == arabic_text

@pytest.mark.asyncio
async def test_output_gate_arabic_response_en_skips_banned_opener_check():
    """Arabic response_en must not trigger English banned-opener retry."""
    arabic_text = "أنا هنا معك."
    state = _make_output_gate_state(
        detected_language="ar", response_en=arabic_text, banned_opener_retry_count=0,
    )
    result = await output_gate_node(state)
    assert result.get("banned_opener_retry_count", 0) == 0

@pytest.mark.asyncio
async def test_output_gate_code_switched_response_en_does_not_skip_translation():
    """response_en with minority Arabic content (<40%) must still go through translation."""
    mixed_text = "I understand you're feeling ضغط at work. Let's slow down."
    state = _make_output_gate_state(detected_language="ar", response_en=mixed_text)
    with patch("sage_poc.nodes.output_gate.async_translate_to_arabic",
               new_callable=AsyncMock, return_value="ترجمة") as mock_translate:
        await output_gate_node(state)
    mock_translate.assert_called_once_with(mixed_text)
```

**Commit:** `fix(output-gate): ratio-based Arabic guard — skip EN validators and translation on full Arabic response_en`

---

## Priority 2A — Therapeutic Profile Language Preference (scoped)

**File:** `sage-poc/src/sage_poc/memory/profile_extractor.py`

Add `preferred_language` to `_EXTRACTION_SYSTEM` (line 20):

```python
"  cultural_preferences: object with keys religious_framing (bool), "
"family_context (bool), gender_address (string or null), "
"preferred_language (string: 'ar' or 'en' — infer from whether "
"the conversation reads as translated from Arabic)\n"
```

**Scope gate — verify before committing as complete:**

This change has runtime effect only if the session-start loader reads `cultural_preferences` from the persisted Supabase profile and injects it into `SageState.therapeutic_profile`. Confirm:

1. Does session initialization fetch `therapeutic_profile` from Supabase and pass it into the initial `SageState`?
2. Is `therapeutic_profile["cultural_preferences"]["preferred_language"]` read anywhere in the composition pipeline?

If (1) is No: the schema change is correct but has no runtime effect — **do not mark complete.** Track as a pre-pilot blocker. The test must assert cross-session persistence round-trip:

```python
@pytest.mark.asyncio
async def test_profile_extractor_preferred_language_present():
    history = [
        {"role": "user", "content": "I feel tired and heavy"},
        {"role": "assistant", "content": "That sounds exhausting..."},
    ]
    profile = await extract_session_profile(history)
    assert "preferred_language" in (profile or {}).get("cultural_preferences", {})
```

**Commit:** `feat(profile-extractor): add preferred_language to cultural_preferences schema` *(conditional on scope gate verification)*

---

## Priority 2B — Arabic Knowledge Corpus: 6 Ungated Articles

**Location:** `sage-poc/data/knowledge_corpus/ar/`

Current state: 20 Arabic articles on master. Missing articles that exist in English but not Arabic (all ungated — no clinical sign-off required):

| Article | Rationale |
|---|---|
| `cbt-001`, `cbt-002` | CBT is active skill family — highest retrieval value |
| `trauma-001` | Batch 2 trauma contraindications are active |
| `breathing-001` | `box_breathing` skill active |
| `grounding-001` | `stop_technique` references grounding |
| `therapy-001` | Lower priority |

`crisis-001` through `crisis-004` remain **clinically gated** (dual-clinician sign-off required, arch doc §20.1 `AR-KB-CRISIS`). Do not author for Gitex.

Verify retrieval after ingestion:
```bash
cd sage-poc && uv run python -c "
import asyncio
from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository
async def main():
    repo = PostgresKnowledgeRepository()
    results = await repo.retrieve('أفكار سلبية', language='ar', top_k=5)
    print([r['source_id'] for r in results])
asyncio.run(main())
"
```

Expected: `cbt-001` and `cbt-002` in top results.

**Commits:** `feat(knowledge-corpus): add Arabic cbt-001, cbt-002` then `feat(knowledge-corpus): add Arabic trauma-001, breathing-001, grounding-001, therapy-001`

---

## Priority 3 — Architecture Doc Update

**File:** `sage-poc/docs/SageAI_architecture_current.md`

Three changes:

1. **Replace stale `CUO-missing` entry in §20.4** with:
   > `CUO-missing: RESOLVED 2026-06-07. All 27 skills have cultural_overrides within the 200w clinician-signed cap. Verified by word-count script. Original finding was accurate at 2026-05-31; overrides were authored after that date.`

2. **Update §17.1** to document CU-DM-001 v1.1→v1.2: the architectural separation of concerns (L0 owns generation contract, CU-DM-001 owns register calibration), and the root cause (GPT-4o literal instruction compliance, pre-translation-layer fossil from 2026-05-22).

3. **Add Arabizi cultural register** to documented known gaps section — distinct from §522 retrieval gap which is already documented:
   > `Arabizi cultural register (2026-06-07): Pure Arabizi (Latin-script Arabic, no Arabic Unicode) classifies as detected_language="en". Crisis detection is covered via SK-AZ-001/SK-AZ-002 (text_raw evaluation). Cultural register calibration and Khaleeji delivery are not triggered for pure Arabizi. Fix requires detect_language() to emit a new signal or upstream Arabizi keyword heuristic. Deferred post-Gitex; scope decision consistent with §522 retrieval deferral.`

**Commit:** `docs(architecture): CUO-missing resolved, CU-DM-001 v1.2 rationale, Arabizi cultural register gap documented`

---

## Commit Sequence

All P1 commits land on `fix/cu-dm-001-arch-alignment`.

| # | Commit | Task | When |
|---|---|---|---|
| 1 | `fix(cultural-rules): CU-DM-001 v1.2 — trim to register calibration` | 1A | Immediate |
| 2 | `fix(composer): add L0 Arabic register extension` | 1B | Immediate |
| 3 | `fix(output-gate): ratio-based Arabic guard` | 1C | Immediate |
| 4 | `docs(architecture): CUO-missing resolved, CU-DM-001 v1.2 rationale, Arabizi gap` | P3 | After commits 1–3 land |
| 5 | `feat(profile-extractor): add preferred_language` | 2A | After scope gate verification |
| 6 | `feat(knowledge-corpus): add Arabic cbt-001, cbt-002` | 2B | Independent branch |
| 7 | `feat(knowledge-corpus): add Arabic trauma-001, breathing-001, grounding-001, therapy-001` | 2B | Independent branch |

---

## Integration Gate (after commits 1–3)

Run full non-slow suite:
```bash
cd sage-poc && uv run pytest --tb=short -m "not slow" -q 2>&1 | tail -15
```
Count must be ≥ baseline (1651) + new tests added. Zero new failures.

**Manual smoke checklist** (Arabic turn through full graph):

- [ ] `layers` contains both `"cultural"` and `"arabic_register"`
- [ ] `"ARABIC SESSION"` appears **before** `"KHALEEJI REGISTER"` in assembled system prompt — layering separation only works if L0 extension precedes CU-DM-001 injection
- [ ] `response_en` contains English text (not Arabic)
- [ ] `response` contains Khaleeji Arabic (translated from `response_en`)
- [ ] No `[output_gate] response_en is predominantly Arabic` WARNING in logs (guard firing = regression signal, not expected success path)
- [ ] `arabic_register` precedes `cultural` in `prompt_layers` list
