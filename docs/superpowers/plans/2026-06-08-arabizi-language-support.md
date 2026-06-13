# Arabizi (Latin-script Arabic) Language Support

**Date:** 2026-06-08 (revised 2026-06-09)
**Branch:** `feat/arabizi-language-support`
**Effort:** ~2 hours
**Dependencies:** None (zero new external packages)
**Clinical sign-off required:** No (routing/detection plumbing only; no clinical rule changes)

---

## Context

Arabizi is Gulf Arabic written in Latin script with numeric phoneme substitutions (3=ع, 7=ح, etc.) — common among the Dubai/Khaleeji target population. Current state:

- `detect_language()` returns `"en"` for pure Arabizi (no Arabic Unicode chars) → invisible to all Arabic-aware branches
- SK-AZ-001 and SK-AZ-002 already provide crisis safety via `text_raw` routing — **must not regress**
- Skill routing, cultural register, and translation all miss Arabizi → English freeflow, no skill activation

Confirmed via live functional test 2026-06-08: Arabizi → English response, no skill. Khaleeji Arabic → skill activated, full Arabic response.

---

## Architecture Decision: Detection Strategy

The original plan used a deterministic heuristic as the *primary* detector. This fails partially open: short Arabizi without marker words or numeric substitutions (e.g. "abi amoot") is missed.

**Revised approach: 3-tier classification**

```
Tier 0: has Arabic Unicode → definite "ar" → translate (unchanged)
Tier 1: _detect_arabizi() heuristic → high-confidence "az" → translate (fast, free)
Tier 2: _is_clearly_english() → high-confidence "en" → skip LLM (fast, free)
Tier 3: classify_and_translate() → GPT-4o decides "en"|"az" in one call (catches everything)
```

GPT-4o handles the ambiguous middle including heuristic misses. For messages where the first two tiers fire, no extra LLM call is made. For the rest, one GPT-4o call both classifies and translates — no double-call.

**Response language for "az":** English only. Output gate translates only for `lang == "ar"`. Arabizi users are Latin-script comfortable; no transliteration layer exists.

---

## Architecture Decision: `classify_and_translate` Output

Follows the same JSON-parse pattern as `intent_route.py:66-70` — prompt for JSON, parse with `re.search(r'\{.*\}', raw, re.DOTALL)` + `json.loads()`. No new infrastructure needed. Falls back to `{"language": "en", "message_en": raw}` on parse failure.

---

## Dependency Order

```
Task 1: language.py (heuristics + classify_and_translate)
  └─► Task 2: safety_check.py (3-tier detection block)
        ├─► Task 3: skill_select.py (az in raw_message branch)
        └─► Task 4: composer.py (ARABIZI SESSION block)
Task 5: docs/SageAI_architecture_current.md §522 — last
Integration gate: tests/test_arabizi_integration.py — after Tasks 1–4
```

---

## Task 1 — `language.py`: Heuristics + `classify_and_translate`

**File:** `src/sage_poc/language.py`
**Effort:** 35 min

### 1a — Extract `has_arabic_unicode()` helper

Currently `detect_language()` has the Arabic Unicode check inline at line 46. Extract it so `safety_check.py` can call it directly without duplicating the regex.

Add at module level (after `_DIRECTIONAL_MARKS`):

```python
_ARABIC_UNICODE_RE = re.compile(r'[؀-ۿ]')

def has_arabic_unicode(text: str) -> bool:
    return bool(_ARABIC_UNICODE_RE.search(text))
```

Update `detect_language()` line 46 to use `has_arabic_unicode(text)`. The existing `re.search(r'[؀-ۿ]', text)` check becomes `if has_arabic_unicode(text): return "ar"`.

### 1b — Add `_detect_arabizi()` fast pre-filter

This is now Tier 1 of the 3-tier system, not the primary detector. Same code, different role.

Add module-level constants and function:

```python
_ARABIZI_NUMERAL_RE = re.compile(
    r'(?<=[a-zA-Z])[376](?=[a-zA-Z])'   # mid-word: ta3ban, 7abibi
    r'|(?<=[a-zA-Z])[376]\b'            # trailing: ta3
    r'|\b[376](?=[a-zA-Z])',            # leading: 3alay, 7ata
    re.IGNORECASE,
)

_ARABIZI_MARKERS = frozenset({
    "wallah", "walla", "wayed", "wayid", "khalas", "inshallah",
    "habibi", "shloun", "shlon", "yalla", "3alay", "7ata",
    "bidi", "mafi", "akeed", "enshallah", "mashallah",
})

def _detect_arabizi(text: str) -> bool:
    """True when text is high-confidence Arabizi via heuristic markers or numeral substitution."""
    lower = text.lower()
    words = set(re.findall(r"[a-z]+", lower))
    return bool(words & _ARABIZI_MARKERS) or bool(_ARABIZI_NUMERAL_RE.search(text))
```

### 1c — Add `_is_clearly_english()` Tier 2 fast path

Called only when `_detect_arabizi()` returns False and there is no Arabic Unicode. Skips GPT-4o for unambiguous English.

```python
def _is_clearly_english(text: str) -> bool:
    """True if text is high-confidence English (no LLM classification needed).

    Short messages are always forwarded to classify_and_translate: 'abi amoot'
    is 9 chars, ASCII-only, and passes langdetect as English, but is Arabizi.
    Length threshold guards this class of miss.
    """
    if not text or not text.isascii():
        return False
    if len(text.strip()) < 20:
        return False
    try:
        langs = detect_langs(text)
        top = langs[0]
        return top.lang in _LATIN_SCRIPT_LANGS and top.prob > 0.92
    except LangDetectException:
        return False
```

### 1d — Add `classify_and_translate()` Tier 3 LLM path

Add `import json` to the imports. Add the function after `async_translate_to_english`:

```python
async def classify_and_translate(text: str) -> dict[str, str]:
    """Single GPT-4o call: classify language and translate if Arabizi.

    Returns {"language": "en"|"az", "message_en": str}.
    Falls back to {"language": "en", "message_en": text} on LLM or parse failure.
    Follows the same JSON-parse pattern as intent_route.py.
    """
    from sage_poc.resilience import resilient_invoke
    _SYSTEM = (
        "You are a language classifier for a Gulf Arabic mental health app.\n"
        "Examine the message and return a JSON object with exactly two fields:\n"
        "  language: 'az' if this is Gulf Arabic in Latin script (Arabizi), 'en' if English\n"
        "  message_en: the English translation if Arabizi, or the original text if English\n\n"
        "Arabizi examples: 'abi amoot', 'ana ta3ban', 'wallah mafi zain', "
        "'abi asawi breathing', 'hayati ma3andha ma3na'\n"
        "English examples: 'I feel really sad', 'can we try breathing', 'I want to die'\n\n"
        "Return ONLY valid JSON. No explanation or preamble."
    )
    raw = await resilient_invoke(
        get_translator(),
        [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": text},
        ],
        node="classify_and_translate",
        language="en",
    )
    match = re.search(r'\{.*\}', raw or "", re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            lang = data.get("language", "en")
            if lang in ("en", "az"):
                _log.debug(
                    "[classify_and_translate] text=%r lang=%s",
                    text[:60], lang,
                )
                return {"language": lang, "message_en": data.get("message_en", text)}
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    _log.warning(
        "[classify_and_translate] parse failure for text=%r — defaulting to en",
        text[:60],
    )
    return {"language": "en", "message_en": text}
```

Note: add `import logging` and `_log = logging.getLogger(__name__)` to `language.py` if not already present.

**Exports to add to `language.py`** (safety_check will import these):
`has_arabic_unicode`, `_detect_arabizi`, `_is_clearly_english`, `classify_and_translate`

### Tests (`tests/test_language.py`)

```python
# --- has_arabic_unicode ---
def test_has_arabic_unicode_arabic_text():
    assert has_arabic_unicode("والله أشعر بالحزن") is True

def test_has_arabic_unicode_pure_latin():
    assert has_arabic_unicode("I feel sad") is False

def test_has_arabic_unicode_arabizi():
    assert has_arabic_unicode("ana ta3ban") is False

# --- _detect_arabizi (Tier 1) ---
def test_detect_arabizi_numeric_substitution():
    assert _detect_arabizi("ana ta3ban") is True

def test_detect_arabizi_marker_word_wallah():
    assert _detect_arabizi("wallah i feel awful") is True

def test_detect_arabizi_yalla_khalas():
    assert _detect_arabizi("yalla khalas") is True

def test_detect_arabizi_habibi_numeric():
    assert _detect_arabizi("7abibi i miss you") is True

def test_detect_arabizi_does_not_fire_for_english():
    assert _detect_arabizi("I feel really sad today") is False

def test_detect_arabizi_does_not_fire_for_standalone_number():
    # "7" standalone must not match — no adjacent letters
    assert _detect_arabizi("I slept 7 hours") is False

def test_detect_arabizi_does_not_fire_for_arabic_script():
    # Arabic Unicode is handled upstream by has_arabic_unicode
    assert _detect_arabizi("والله أشعر") is False

# --- _is_clearly_english (Tier 2) ---
def test_is_clearly_english_long_english():
    assert _is_clearly_english("I feel really anxious and cannot sleep at night") is True

def test_is_clearly_english_short_rejects():
    # Short messages go to GPT-4o regardless
    assert _is_clearly_english("abi amoot") is False
    assert _is_clearly_english("ok thanks") is False

def test_is_clearly_english_non_ascii_rejects():
    assert _is_clearly_english("café") is False

# --- classify_and_translate (Tier 3 — mocked) ---
@pytest.mark.asyncio
async def test_classify_and_translate_arabizi_no_markers():
    """'abi amoot' has no heuristic markers but GPT-4o classifies it as az."""
    with patch("sage_poc.language.resilient_invoke",
               new_callable=AsyncMock,
               return_value='{"language": "az", "message_en": "I want to die"}'):
        result = await classify_and_translate("abi amoot")
    assert result["language"] == "az"
    assert result["message_en"] == "I want to die"

@pytest.mark.asyncio
async def test_classify_and_translate_english():
    with patch("sage_poc.language.resilient_invoke",
               new_callable=AsyncMock,
               return_value='{"language": "en", "message_en": "I feel very tired"}'):
        result = await classify_and_translate("I feel very tired")
    assert result["language"] == "en"
    assert result["message_en"] == "I feel very tired"

@pytest.mark.asyncio
async def test_classify_and_translate_parse_failure_defaults_en():
    """Unparseable LLM output falls back to en + raw text."""
    with patch("sage_poc.language.resilient_invoke",
               new_callable=AsyncMock, return_value="sorry, I cannot help"):
        result = await classify_and_translate("abi asawi breathing")
    assert result["language"] == "en"
    assert result["message_en"] == "abi asawi breathing"
```

**Commit:** `feat(language): Arabizi heuristics, has_arabic_unicode, _is_clearly_english, classify_and_translate`

---

## Task 2 — `safety_check.py`: Replace translation block with 3-tier logic

**File:** `src/sage_poc/nodes/safety_check.py`
**Effort:** 25 min

### Import change

Replace the existing import line:
```python
from sage_poc.language import detect_language, async_translate_to_english
```
with:
```python
from sage_poc.language import (
    has_arabic_unicode,
    async_translate_to_english,
    _detect_arabizi,
    _is_clearly_english,
    classify_and_translate,
)
```

`detect_language` is no longer called in this node — the 3-tier logic replaces it.

### Block replacement (lines 86–93)

```python
# before
lang = detect_language(raw)
if lang == "ar":
    message_en = await async_translate_to_english(raw)
    text_ar = raw
else:
    message_en = raw
    text_ar = None

# after
if has_arabic_unicode(raw):
    lang = "ar"
    message_en = await async_translate_to_english(raw)
    text_ar = raw
else:
    text_ar = None
    if _detect_arabizi(raw):
        lang = "az"
        message_en = await async_translate_to_english(raw)
    elif _is_clearly_english(raw):
        lang = "en"
        message_en = raw
    else:
        result = await classify_and_translate(raw)
        lang = result["language"]
        message_en = result["message_en"]
```

`text_raw = raw` (line 99) is **unchanged** — SK-AZ-001/002 still fire on the original Arabizi text regardless of `lang`.

### Tests (`tests/test_safety_node_integration.py`)

```python
@pytest.mark.asyncio
async def test_arabizi_with_markers_hits_heuristic_tier():
    """Tier 1: 'wallah ta3ban' → _detect_arabizi → translate, no classify_and_translate call."""
    state = make_state(raw_message="wallah ta3ban")
    with patch("sage_poc.nodes.safety_check.classify_and_translate") as mock_llm, \
         patch("sage_poc.nodes.safety_check.async_translate_to_english",
               new_callable=AsyncMock, return_value="I am very tired"):
        result = await safety_check_node(state)
    mock_llm.assert_not_called()   # Tier 3 not reached
    assert result["detected_language"] == "az"
    assert result["message_en"] == "I am very tired"

@pytest.mark.asyncio
async def test_arabizi_without_markers_hits_llm_tier():
    """Tier 3: 'abi amoot' → heuristic miss → classify_and_translate → az.

    Double-coverage verification: SK-AZ-001 fires on text_raw='abi amoot' (S1 rules
    engine, text_raw path) AND S3 fires on message_en='I want to die' via
    check_s3_bilingual(text_en, None) → check_s3(text_en).
    Assert crisis_flags to confirm both nets are working, not just is_safe==False.
    """
    state = make_state(raw_message="abi amoot")
    with patch("sage_poc.nodes.safety_check.classify_and_translate",
               new_callable=AsyncMock,
               return_value={"language": "az", "message_en": "I want to die"}):
        result = await safety_check_node(state)
    assert result["detected_language"] == "az"
    assert result["message_en"] == "I want to die"
    assert result["is_safe"] is False
    # S1 net: SK-AZ-001 fires on text_raw="abi amoot" → si_explicit
    assert "si_explicit" in result["crisis_flags"], (
        "SK-AZ-001 must fire on text_raw='abi amoot' via S1 keyword path"
    )
    # S3 net: check_s3_bilingual("I want to die", None) → check_s3("I want to die")
    # BGE-M3 on explicit English SI phrase should clear SEMANTIC_THRESHOLD=0.4593
    assert "s3_semantic" in result["crisis_flags"], (
        "S3 must fire on message_en='I want to die' (English translation, not raw Arabizi)"
    )

@pytest.mark.asyncio
async def test_arabizi_without_markers_skill_phrase_hits_llm_tier():
    """Tier 3: 'abi asawi breathing' → no heuristic markers → GPT-4o classifies az."""
    state = make_state(raw_message="abi asawi breathing")
    with patch("sage_poc.nodes.safety_check.classify_and_translate",
               new_callable=AsyncMock,
               return_value={"language": "az", "message_en": "I want to do breathing"}):
        result = await safety_check_node(state)
    assert result["detected_language"] == "az"
    assert result["message_en"] == "I want to do breathing"
    assert result["is_safe"] is True

@pytest.mark.asyncio
async def test_long_english_message_skips_llm():
    """Tier 2: Long clear English → _is_clearly_english → no LLM call."""
    state = make_state(raw_message="I feel really anxious and cannot sleep at night")
    with patch("sage_poc.nodes.safety_check.classify_and_translate") as mock_llm:
        result = await safety_check_node(state)
    mock_llm.assert_not_called()
    assert result["detected_language"] == "en"

@pytest.mark.asyncio
async def test_arabic_path_unaffected():
    """Tier 0: Arabic Unicode → translate, text_ar=raw (regression guard)."""
    state = make_state(raw_message="أشعر بالحزن")
    with patch("sage_poc.nodes.safety_check.async_translate_to_english",
               new_callable=AsyncMock, return_value="I feel sad") as mock_t, \
         patch("sage_poc.nodes.safety_check.classify_and_translate") as mock_llm:
        result = await safety_check_node(state)
    mock_t.assert_called_once()
    mock_llm.assert_not_called()
    assert result["detected_language"] == "ar"
    assert result["text_ar"] == "أشعر بالحزن"

@pytest.mark.asyncio
async def test_crisis_still_fires_on_arabizi_without_markers():
    """SK-AZ-001 fires on text_raw regardless of detect tier.
    Flag-level assertion: si_explicit must appear, confirming S1 net is active.
    """
    state = make_state(raw_message="abi amoot")
    with patch("sage_poc.nodes.safety_check.classify_and_translate",
               new_callable=AsyncMock,
               return_value={"language": "az", "message_en": "I want to die"}):
        result = await safety_check_node(state)
    assert result["is_safe"] is False
    assert "si_explicit" in result["crisis_flags"]
```

### Notes on `safety_check.py:130–134` comment

The existing comment reads:
> "Arabizi phrases (SK-AZ-001/002) score 0.39–0.81; only one phrase clears (+0.002). S1 keyword coverage is therefore LOAD-BEARING for Arabic and Arabizi."

This was written when Arabizi `message_en` was raw Arabizi text. After Task 2, it is only accurate for the GPT-4o parse-failure fallback path (where `message_en` falls back to raw Arabizi). For normal Tier 1–3 operation, `message_en` is an English translation and S3 operates on English — scoring correctly. Update the comment when implementing:

```python
# S1 keyword coverage is LOAD-BEARING for Arabic (text_ar path) and for any Arabizi
# that falls through the classify_and_translate failure fallback (message_en = raw).
# For normal Arabizi Tier 1-3 operation, message_en is English → S3 scores reliably.
# DO NOT prune Arabic/Arabizi keywords on the assumption that S3 covers normal paths:
# the failure fallback still needs S1 as its only backstop.
```

**Commit:** `feat(safety_check): replace translation block with 3-tier Arabizi detection`

---

## Task 3 — `skill_select.py`: Include "az" in raw_message branch

**File:** `src/sage_poc/nodes/skill_select.py`
**Effort:** 15 min

### Change (line ~146)

```python
# before
if kw_lower in message_en or (detected_language == "ar" and kw_lower in raw_message):

# after
if kw_lower in message_en or (detected_language in ("ar", "az") and kw_lower in raw_message):
```

With Task 2 done, `message_en` is an English translation for all Arabizi inputs — Tier 1 English keyword matching already works. The `raw_message` branch is belt-and-suspenders for future Arabizi-specific `target_presentations` keywords.

Tier 2 BGE-M3 semantic matching uses `state["message_en"]` (now English) — no change needed.

### Tests (`tests/test_skill_select.py`)

```python
@pytest.mark.asyncio
async def test_arabizi_keyword_match_via_translated_message_en():
    """Task 2 delivers English message_en; Tier 1 keyword matching fires correctly."""
    state = _ss_state(
        raw_message="abi asawi breathing",
        message_en="I want to do box breathing",
        detected_language="az",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "box_breathing"
    assert result["skill_match_method"] == "keyword"

@pytest.mark.asyncio
async def test_arabic_keyword_raw_message_branch_unaffected():
    state = _ss_state(
        raw_message="أشعر بالضيق",
        message_en="I feel distressed",
        detected_language="ar",
    )
    result = await skill_select_node(state)
    assert "active_skill_id" in result
```

**Commit:** `feat(skill_select): include az in Tier 1 raw_message keyword branch`

---

## Task 4 — `composer.py`: ARABIZI SESSION block

**File:** `src/sage_poc/prompts/composer.py`
**Effort:** 20 min

### Change

Add `elif language == "az":` branch immediately after the existing `if language == "ar":` block and before the indented close of the L0 extension section:

```python
elif language == "az":
    system_parts.append(
        "ARABIZI SESSION: This user writes Gulf Arabic using Latin script (Arabizi). "
        "Respond in clear, warm English. Do not use Arabic script in your response. "
        "You may naturally acknowledge Arabizi expressions the user has used."
    )
    layers.append("arabizi_register")
```

**Why English response:** Output gate at `output_gate.py` translates only for `lang == "ar"`. For `"az"`, `final_response = response_en` directly. This is by design — do not add translation for "az".

**Cultural rules:** `CulturalRule` schema defines `language: Literal["en", "ar", "any"]`. "az" is not a valid value; no cultural rules fire. Safe as-is.

**Few-shot examples:** `language == "az"` doesn't match the `"ar"` branch → falls through to first-two English examples. Correct.

### Tests (`tests/test_prompts_composer.py`)

```python
def test_compose_prompt_arabizi_session_block_injected():
    with patch("sage_poc.prompts.composer.rules_engine.evaluate",
               return_value=_no_rules_mock()):
        state = _make_composer_state(detected_language="az", message_en="ana ta3ban")
        system_str, _, layers = compose_prompt(state)
    assert "ARABIZI SESSION" in system_str
    assert "arabizi_register" in layers
    assert "Arabic script" in system_str

def test_compose_prompt_arabizi_no_arabic_session_block():
    with patch("sage_poc.prompts.composer.rules_engine.evaluate",
               return_value=_no_rules_mock()):
        state = _make_composer_state(detected_language="az", message_en="abi asawi breathing")
        system_str, _, layers = compose_prompt(state)
    assert "ARABIC SESSION" not in system_str
    assert "arabic_register" not in layers

def test_compose_prompt_arabic_session_unaffected():
    with patch("sage_poc.prompts.composer.rules_engine.evaluate",
               return_value=_no_rules_mock()):
        state = _make_composer_state(detected_language="ar", message_en="I feel sad")
        system_str, _, layers = compose_prompt(state)
    assert "ARABIC SESSION" in system_str
    assert "arabic_register" in layers

def test_compose_prompt_en_no_register_block():
    with patch("sage_poc.prompts.composer.rules_engine.evaluate",
               return_value=_no_rules_mock()):
        state = _make_composer_state(detected_language="en")
        system_str, _, layers = compose_prompt(state)
    assert "ARABIC SESSION" not in system_str
    assert "ARABIZI SESSION" not in system_str
```

**Commit:** `feat(composer): add ARABIZI SESSION register block for language==az`

---

## Task 5 — `docs/SageAI_architecture_current.md`: Update §522

**File:** `docs/SageAI_architecture_current.md`
**Effort:** 10 min

Replace the current §522 Named Decision (Arabizi Out of Scope) with:

```
#### Named Decision: Arabizi (Latin-script Arabic) — Partial Implementation, Retrieval Out of Scope

*Decision date: 2026-06-01 (original). Updated: 2026-06-09. Status: Partially in scope.*

**Detection strategy (3-tier, implemented 2026-06-09):**
- Tier 0: Arabic Unicode presence → classify as "ar" (unchanged)
- Tier 1: `_detect_arabizi()` heuristic (numeric substitution + marker words) → classify as "az" (fast, free)
- Tier 2: `_is_clearly_english()` (length + langdetect confidence) → classify as "en", skip LLM (fast, free)
- Tier 3: `classify_and_translate()` → single GPT-4o call classifies AND translates (catches all heuristic misses)

**In scope (implemented 2026-06-09):**
- Detection: all three fast tiers + GPT-4o fallback; no false negatives
- Translation: `safety_check_node` delivers English `message_en` for all Arabizi inputs
- Skill routing: Tier 1 keyword matching and Tier 2 BGE-M3 semantic matching function correctly
- Register instruction: `compose_prompt()` injects ARABIZI SESSION system block
- Response language: English by design (Arabizi users are Latin-script comfortable)
- Crisis safety (double coverage on Tier 1–3): SK-AZ-001/SK-AZ-002 fire on `text_raw`
  unconditionally (S1 keyword path, unchanged). Additionally, `check_s3_bilingual(text_en, None)`
  delegates to `check_s3(text_en)` for Arabizi — BGE-M3 runs on the English translation,
  giving full semantic crisis coverage. Both nets operate simultaneously on Tier 1–3 messages.
  Exception: GPT-4o parse-failure fallback sets `message_en = raw` (Arabizi text); in that
  case S3 scores degrade to Arabizi levels and S1 keyword coverage remains load-bearing.

**Still out of scope (deferred post-POC):**
- Knowledge retrieval: Arabizi queries route to the English corpus unchanged.
  Proper Arabizi-on-retrieval requires a transliteration layer (CAMeL Tools or equivalent).
```

**Commit:** `docs(architecture): update §522 to reflect 3-tier Arabizi detection strategy`

---

## Integration Gate

**New file:** `tests/test_arabizi_integration.py`
**Effort:** 20 min

```python
"""End-to-end smoke tests for the Arabizi detection + routing path.
All three detection tiers are exercised. SK-AZ-001/002 regression is verified.
"""
import pytest
from unittest.mock import patch, AsyncMock
from tests.helpers import make_state
from sage_poc.nodes.safety_check import safety_check_node


@pytest.mark.asyncio
async def test_tier1_arabizi_with_markers():
    """Tier 1 (heuristic): 'wallah ta3ban' → az without GPT-4o classify call."""
    state = make_state(raw_message="wallah ta3ban")
    with patch("sage_poc.nodes.safety_check.classify_and_translate") as mock_llm, \
         patch("sage_poc.nodes.safety_check.async_translate_to_english",
               new_callable=AsyncMock, return_value="I am very tired"):
        result = await safety_check_node(state)
    mock_llm.assert_not_called()
    assert result["detected_language"] == "az"
    assert result["message_en"] == "I am very tired"
    assert result["is_safe"] is True


@pytest.mark.asyncio
async def test_tier3_arabizi_without_markers():
    """Tier 3 (GPT-4o): 'abi amoot' — no heuristic markers or numerals, misses Tier 1.

    Double-coverage: SK-AZ-001 fires on text_raw='abi amoot' (S1, text_raw path).
    S3 fires on message_en='I want to die' via check_s3_bilingual(text_en, None).
    Both crisis_flags entries must be present — confirms both nets are working.
    """
    state = make_state(raw_message="abi amoot")
    with patch("sage_poc.nodes.safety_check.classify_and_translate",
               new_callable=AsyncMock,
               return_value={"language": "az", "message_en": "I want to die"}):
        result = await safety_check_node(state)
    assert result["detected_language"] == "az"
    assert result["is_safe"] is False
    assert "si_explicit" in result["crisis_flags"], "S1 net (SK-AZ-001 on text_raw) must fire"
    assert "s3_semantic" in result["crisis_flags"], "S3 net (BGE-M3 on translated message_en) must fire"


@pytest.mark.asyncio
async def test_tier3_arabizi_skill_phrase_no_markers():
    """Tier 3: 'abi asawi breathing' — Arabizi skill request without markers."""
    state = make_state(raw_message="abi asawi breathing")
    with patch("sage_poc.nodes.safety_check.classify_and_translate",
               new_callable=AsyncMock,
               return_value={"language": "az", "message_en": "I want to do breathing"}):
        result = await safety_check_node(state)
    assert result["detected_language"] == "az"
    assert result["message_en"] == "I want to do breathing"
    assert result["is_safe"] is True


@pytest.mark.asyncio
async def test_crisis_fires_regardless_of_tier():
    """SK-AZ-002 must fire on text_raw even when heuristic misses."""
    state = make_state(raw_message="hayati ma3andha ma3na")   # no standard markers
    with patch("sage_poc.nodes.safety_check.classify_and_translate",
               new_callable=AsyncMock,
               return_value={"language": "az", "message_en": "my life has no meaning"}):
        result = await safety_check_node(state)
    assert result["is_safe"] is False
    assert "si_passive" in result["crisis_flags"], "SK-AZ-002 must fire on text_raw"


@pytest.mark.asyncio
async def test_s7_monitoring_arabizi_second_turn():
    """S7 regression: Arabizi user enters crisis on turn 1, sends Arabizi on turn 2.

    evaluate_s7 is called at safety_check.py:194 with message_en (the English
    translation). Verify it classifies correctly on translated English, not raw Arabizi.
    The path: crisis_state='monitoring' → evaluate_s7(message_en='I still feel terrible')
    S7 keyword tier runs on message_en.lower(); LLM tier passes message_en to GPT-4o.
    Both work on English translations — this test confirms no regression.
    """
    state = make_state(
        raw_message="lissa ta3ban",   # Tier 1 heuristic match (numeric sub)
        crisis_state="monitoring",
    )
    with patch("sage_poc.nodes.safety_check.async_translate_to_english",
               new_callable=AsyncMock, return_value="I still feel terrible"), \
         patch("sage_poc.nodes.post_crisis_classifier.resilient_invoke",
               new_callable=AsyncMock, return_value="STILL_DISTRESSED") as mock_s7:
        result = await safety_check_node(state)
    # S7 must have been called with the English translation, not raw Arabizi
    mock_s7.assert_called_once()
    call_messages = mock_s7.call_args[0][1]   # messages list
    user_message = next(m for m in call_messages if m["role"] == "user")
    assert user_message["content"] == "I still feel terrible", (
        "evaluate_s7 must receive English translation, not raw Arabizi 'lissa ta3ban'"
    )
    assert result["s7_result"] == "STILL_DISTRESSED"


@pytest.mark.asyncio
async def test_arabic_khaleeji_path_unaffected():
    """Tier 0: Arabic Unicode → 'ar', text_ar = raw (regression guard)."""
    state = make_state(raw_message="أشعر بالحزن الشديد اليوم")
    with patch("sage_poc.nodes.safety_check.async_translate_to_english",
               new_callable=AsyncMock, return_value="I feel very sad today"),\
         patch("sage_poc.nodes.safety_check.classify_and_translate") as mock_llm:
        result = await safety_check_node(state)
    mock_llm.assert_not_called()
    assert result["detected_language"] == "ar"
    assert result["text_ar"] == "أشعر بالحزن الشديد اليوم"
```

Run with: `uv run pytest tests/test_arabizi_integration.py -v`

---

## Summary

| Task | File | Effort | Change |
|---|---|---|---|
| 1 | `src/sage_poc/language.py` | 35 min | `has_arabic_unicode`, `_detect_arabizi`, `_is_clearly_english`, `classify_and_translate` |
| 2 | `src/sage_poc/nodes/safety_check.py` | 25 min | Replace 6-line translation block with 3-tier logic |
| 3 | `src/sage_poc/nodes/skill_select.py` | 15 min | `detected_language == "ar"` → `in ("ar", "az")` |
| 4 | `src/sage_poc/prompts/composer.py` | 20 min | Add `elif language == "az":` ARABIZI SESSION block |
| 5 | `docs/SageAI_architecture_current.md` | 10 min | Update §522 Named Decision |
| Integration gate | `tests/test_arabizi_integration.py` | 20 min | 5 tests covering all 3 tiers + regression guards |
| **Total** | | **~2 hours** | |

---

## Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| GPT-4o misclassifies English with Arabic loanwords ("I went to the souk") as "az" | Low | `message_en` for English is returned unchanged; downstream effect is nil. Log all `classify_and_translate` calls for monitoring |
| `_is_clearly_english` length threshold (20 chars) too aggressive — long Arabizi sentences sent to English fast path | Very low | `_detect_arabizi` runs first; heuristic catches all long Arabizi with markers. Only marker-free AND numeral-free AND long Arabizi (rare) would reach `_is_clearly_english`, and those are ambiguous enough that langdetect + prob > 0.92 is a reasonable gate |
| `classify_and_translate` latency for short ambiguous messages | Manageable | Tier 1 + Tier 2 eliminate LLM call for the majority of messages. Short ambiguous messages are a small fraction |
| SK-AZ-001/002 crisis regression | Eliminated | `text_raw = raw` is set unconditionally before the 3-tier block and is not touched by any tier |
| `classify_and_translate` parse failure | Handled | Falls back to `{"language": "en", "message_en": raw}` — worst case is English response for misclassified Arabizi, not a crisis miss |
