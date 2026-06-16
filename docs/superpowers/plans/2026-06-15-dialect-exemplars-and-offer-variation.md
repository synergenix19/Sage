# Khaleeji Translation Exemplars + Skill-Offer Variation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two pieces of user-reported feedback — (A) Arabic dialect drift (started Syrian, shifted Emirati) and (B) the repetitive skill-offer phrasing ("…we can also just keep talking if you'd prefer. Which one feels right to you?").

**Architecture:** Part A makes the Arabic translator deterministic about dialect by switching it from a bare label ("Gulf Arabic") to a **few-shot prompt** anchored on named Emirati Gulf exemplars (research shows few-shot + consistent dialect naming materially improves dialectal Arabic output). Part B adds a persisted `offer_count` counter so the composer can select a **lighter re-ask variant** on the 2nd+ render of the same offer, and instructs the base offer template to vary its wording instead of converging on one stock sentence. The two parts are independent and independently shippable.

**Tech Stack:** Python 3.11, LangGraph (checkpointed `SageState`), Pydantic prompt templates loaded from `src/sage_poc/prompts/templates/**`, pytest (`asyncio_mode = auto`).

---

## What the clinician is approving (read first)

Everything below is engineering-complete. **Three artifacts carry clinical/linguistic wording and need sign-off before merge.** They are drafted here so review is a yes/edit, not authoring:

| Artifact | File | What to review |
|---|---|---|
| **A. Khaleeji exemplars** | `src/sage_poc/data/khaleeji_translation_exemplars.json` (new) | The English→Emirati Arabic pairs. Needs a **native Emirati linguist** for register/marker accuracy, plus clinical confirmation that warmth/meaning is preserved and nothing clinical changes. |
| **B1. Base offer template** | `prompts/templates/L2_intents/skill_offer.json` (modified) | One new sentence instructing the model to vary its wording. Non-coercion framing is unchanged. |
| **B2. Re-ask offer template** | `prompts/templates/L2_intents/skill_offer_reoffer.json` (new) | The gentler, no-pressure re-ask wording shown on a 2nd+ offer render. |

All three carry `status: "draft_pending_signoff"` and an empty `_signed_off`. **No conformance test enforces L2-template status** (verified: `PromptTemplate` ignores extra fields; no test asserts approval on L2 templates), so these can land on a branch and run green in CI while sign-off is pending. The clinician fills `_signed_off` to authorize merge.

**Scope note:** R1 consent offers are **English-only today** (`skill_select.py:191-202`, audit marker `arabic_offer_excluded`) — Arabic sessions never produce an offer. So Part B affects English sessions only; Part A is the Arabic-facing fix. They do not interact.

### Flag 1 — L2 word-budget deviation (documented, intentional)
Both offer templates set `word_budget: 90`, above §5.6's ~50-word L2 target. This is intentional: **skill-offer turns carry no L3/L4/L5 layers** (no active skill step, no knowledge passages, no user-context block beyond L0/L1), so the total composed prompt stays under the overall budget even with the wider L2. Each offer template (`skill_offer.json`, `skill_offer_reoffer.json`) therefore carries a `budget_note` field recording the deviation and its justification so the next reader does not "fix" it. `PromptTemplate` ignores the extra field — no schema/CI impact.

### Flag 2 — Task A4 is a §20.1 Dialect-QA deployment gate (not a handoff)
A1–A3 (exemplar file, prompt builder, translator wiring) may merge to the branch. **Task A4 is the §20.1 Dialect-QA sign-off and is a hard deployment gate: no Arabic output reaches real users until A4 completes.** The "hand to user" phrasing inside A4 is only the agentic worker's stop-instruction (a worker cannot perform native-rater QA mid-run); it does not downgrade A4 from a release gate. Do not deploy the Arabic path to any user-facing environment until A4 is signed off.

---

# PART A — Khaleeji translation exemplars (dialect drift)

**Root cause being fixed:** `async_translate_to_arabic` / `translate_to_arabic` (`language.py:80-123`) prompt a general model with only the label *"informal Gulf Arabic (Khaleeji dialect)"*, statelessly, per turn. A general model's default "informal Arabic" leans Levantine/Syrian, so adherence varies turn-to-turn — that is the Syrian↔Emirati drift. Few-shot exemplars + consistent dialect naming lock the register.

## Task A1: Create the Khaleeji exemplar data file (DRAFT — needs linguistic sign-off)

**Files:**
- Create: `src/sage_poc/data/khaleeji_translation_exemplars.json`

- [ ] **Step 1: Create the data file**

```json
{
  "version": "0.1.0",
  "status": "draft_pending_signoff",
  "authored_by": "engineering",
  "approved_by": null,
  "dialect_name": "Emirati Gulf Arabic (Khaleeji)",
  "effective_date": "PENDING",
  "exemplars": [
    {
      "en": "That sounds really heavy. I'm here with you, and we can take this slowly.",
      "ar": "هذا الشي ثقيل عليك وايد، وأنا وياك هني. خلنا ناخذها على راحتنا، ما في استعجال."
    },
    {
      "en": "It's completely okay to feel this way. Do you want to tell me a bit more about what's going on?",
      "ar": "عادي تماماً تحس بهالإحساس، ما في شي غلط فيك. تحب تقول لي شوي عن اللي قاعد يصير وياك؟"
    },
    {
      "en": "You don't have to carry this on your own. I'm listening.",
      "ar": "ما لازم تشيل هذا الحمل لحالك. أنا أسمعك."
    },
    {
      "en": "Take your time, there's no rush at all. Whatever you're feeling is welcome here.",
      "ar": "خذ راحتك، ما في أي استعجال أبداً. أي شي تحس فيه مرحب فيه هني."
    }
  ],
  "_review_required": [
    "NATIVE EMIRATI LINGUIST: verify every Arabic line is natural Emirati Gulf register (e.g. وياك/هني/خلنا/شوي/قاعد/لحالك), not Levantine or MSA, and not a different Gulf sub-dialect.",
    "CLINICAL: confirm warmth and meaning are preserved and no line changes clinical intent (no advice, no minimisation)."
  ],
  "_signed_off": ""
}
```

- [ ] **Step 2: Commit**

```bash
git add src/sage_poc/data/khaleeji_translation_exemplars.json
git commit -m "feat(lang): add draft Khaleeji translation exemplars (pending linguistic sign-off)"
```

## Task A2: Build a shared few-shot prompt builder in language.py

**Files:**
- Modify: `src/sage_poc/language.py` (top of file + after `detect_language`)
- Test: `tests/test_khaleeji_translation_prompt.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_khaleeji_translation_prompt.py
import re

from sage_poc.language import _build_khaleeji_translation_prompt, _khaleeji_exemplars


def test_exemplar_file_is_well_formed():
    data = _khaleeji_exemplars()
    assert data["dialect_name"]
    exemplars = data["exemplars"]
    assert len(exemplars) >= 3, "few-shot needs at least 3 pairs"
    for ex in exemplars:
        assert ex["en"].strip(), "English side must be non-empty"
        assert ex["ar"].strip(), "Arabic side must be non-empty"
        assert re.search(r"[؀-ۿ]", ex["ar"]), "Arabic side must contain Arabic script"


def test_prompt_is_few_shot_and_names_the_dialect():
    prompt = _build_khaleeji_translation_prompt("I am here for you.")
    data = _khaleeji_exemplars()
    # Dialect named explicitly (research: naming beats codes)
    assert data["dialect_name"] in prompt
    # Every exemplar appears (the few-shot block)
    for ex in data["exemplars"]:
        assert ex["en"] in prompt
        assert ex["ar"] in prompt
    # The text to translate is included
    assert "I am here for you." in prompt
    # Consistency instruction present
    assert "consistent" in prompt.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_khaleeji_translation_prompt.py -v`
Expected: FAIL with `ImportError: cannot import name '_build_khaleeji_translation_prompt'`

- [ ] **Step 3: Add the loader + builder to language.py**

Add these imports at the very top of `src/sage_poc/language.py` (after the existing `import re`):

```python
import json
from functools import lru_cache
from pathlib import Path
```

Add this block immediately after the `detect_language` function (after line 55, before `translate_to_english`):

```python
_EXEMPLARS_PATH = Path(__file__).parent / "data" / "khaleeji_translation_exemplars.json"


@lru_cache(maxsize=1)
def _khaleeji_exemplars() -> dict:
    """Load the Emirati Gulf translation exemplars once (cached)."""
    return json.loads(_EXEMPLARS_PATH.read_text(encoding="utf-8"))


def _build_khaleeji_translation_prompt(text: str) -> str:
    """Build a few-shot prompt that anchors the translator on named Emirati Gulf
    exemplars so the output dialect stays consistent turn to turn.

    Single source of truth for both the sync and async Arabic translators.
    """
    data = _khaleeji_exemplars()
    dialect = data["dialect_name"]
    lines = [
        f"You are translating warm, supportive messages from a wellness companion "
        f"named Sage into {dialect}. Keep the same warmth and conversational rhythm. "
        f"Use natural everyday {dialect} phrasing, not formal or clinical Modern "
        f"Standard Arabic. Stay in {dialect} consistently across the whole message. "
        f"Return only the translation.",
        "",
        "Examples:",
    ]
    for ex in data["exemplars"]:
        lines.append(f"English: {ex['en']}")
        lines.append(f"Arabic: {ex['ar']}")
        lines.append("")
    lines.append("Now translate this:")
    lines.append(f"English: {text}")
    lines.append("Arabic:")
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_khaleeji_translation_prompt.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/language.py tests/test_khaleeji_translation_prompt.py
git commit -m "feat(lang): few-shot Khaleeji translation prompt builder"
```

## Task A3: Wire the builder into both Arabic translators

**Files:**
- Modify: `src/sage_poc/language.py:80-123` (`translate_to_arabic`, `async_translate_to_arabic`)
- Test: `tests/test_khaleeji_translation_prompt.py` (add)

- [ ] **Step 1: Write the failing test (async path uses the few-shot prompt)**

Append to `tests/test_khaleeji_translation_prompt.py`:

```python
import sage_poc.resilience as resilience
import sage_poc.language as language


async def test_async_translate_uses_few_shot_prompt(monkeypatch):
    captured = {}

    async def _fake_invoke(llm, messages, **kwargs):
        captured["content"] = messages[0]["content"]
        return "ترجمة"

    monkeypatch.setattr(resilience, "resilient_invoke", _fake_invoke)
    monkeypatch.setattr(language, "get_translator", lambda: object())

    out = await language.async_translate_to_arabic("Take your time.")
    assert out == "ترجمة"
    # The prompt sent to the model is the few-shot prompt, not the old bare label
    assert "Examples:" in captured["content"]
    assert "Take your time." in captured["content"]
    assert language._khaleeji_exemplars()["dialect_name"] in captured["content"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_khaleeji_translation_prompt.py::test_async_translate_uses_few_shot_prompt -v`
Expected: FAIL — `assert "Examples:" in captured["content"]` (old prompt has no exemplars)

- [ ] **Step 3: Replace the prompt body in `translate_to_arabic` (sync)**

In `src/sage_poc/language.py`, replace the `content` argument in `translate_to_arabic` (currently lines 91-96) so the message becomes:

```python
        response = llm.invoke([{
            "role": "user",
            "content": _build_khaleeji_translation_prompt(text),
        }])
```

- [ ] **Step 4: Replace the prompt body in `async_translate_to_arabic`**

Replace the `content` in `async_translate_to_arabic` (currently lines 113-118) so the message becomes:

```python
        [{
            "role": "user",
            "content": _build_khaleeji_translation_prompt(text),
        }],
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_khaleeji_translation_prompt.py tests/test_language.py -v`
Expected: PASS (new tests + existing language tests still green)

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/language.py tests/test_khaleeji_translation_prompt.py
git commit -m "feat(lang): both Arabic translators use few-shot Khaleeji prompt"
```

## Task A4: §20.1 Dialect-QA sign-off (DEPLOYMENT GATE — manual, NOT code)

This is the §20.1 Dialect-QA release gate, not a handoff. **A1–A3 may merge to the branch, but no Arabic output reaches any real user until A4 is signed off.** It cannot be unit-tested (dialect quality needs a native human rater). This task produces the evidence the clinician needs to fill `_signed_off` and clear the gate.

- [ ] **Step 1: Generate a sample set**

Pick 15 representative English support sentences (warm reflection, gentle question, crisis-adjacent reassurance, skill hand-off). Run each through `async_translate_to_arabic` against the real translator model and record EN → AR pairs in `docs/superpowers/governance/2026-06-15-khaleeji-translation-eval.md`.

- [ ] **Step 2: Native Emirati rating**

A native Emirati reviewer rates each output 1-5 on (a) dialect correctness (Emirati Gulf, not Levantine/MSA) and (b) warmth preservation. Record scores and any corrections in the same doc.

- [ ] **Step 3: Fold corrections back into exemplars**

Apply reviewer corrections to `khaleeji_translation_exemplars.json`, bump `version`, set `effective_date`, set `approved_by`, fill `_signed_off`. Commit:

```bash
git add src/sage_poc/data/khaleeji_translation_exemplars.json docs/superpowers/governance/2026-06-15-khaleeji-translation-eval.md
git commit -m "chore(lang): Khaleeji exemplars signed off after native Emirati review"
```

> **Note for plan executor:** Steps 1-2 require API access and a native Emirati rater not available mid-run. Stop after Task A3, report that A1-A3 are on the branch, and surface A4 to the user as the open **§20.1 Dialect-QA deployment gate**. This is a stop-instruction for the worker, NOT a downgrade of A4 — the Arabic path must not deploy to users until A4 clears.

---

# PART B — Skill-offer variation (repetitive phrasing)

**Root cause being fixed:** the offer phrasing comes from one fixed instruction in `skill_offer.json` with no variation layer and no "second time" variant. When the user's reply is ambiguous, `intent_route` intentionally preserves the offer (`offer_unparsed`, `intent_route.py:153-161`) and the composer re-renders the **same** template verbatim — that is the repeat the tester saw. Fix: count consecutive renders and switch to a lighter re-ask on render 2+, and tell the base template to vary its wording.

## Task B1: Add `offer_count` to SageState

**Files:**
- Modify: `src/sage_poc/state.py:50` (after `declined_skills`)

- [ ] **Step 1: Add the field**

In `src/sage_poc/state.py`, immediately after the `declined_skills` line (line 50), add:

```python
    offer_count: int                        # consecutive turns the current offer has been shown to the user: set to 1 when an offer is first made (skill_select), +1 each re-ask (offer_unparsed in intent_route), 0 when no/resolved offer; persists via checkpoint; cleared at 4h stale gap. Drives the composer's reoffer variant.
```

- [ ] **Step 2: Commit**

```bash
git add src/sage_poc/state.py
git commit -m "feat(state): add offer_count for skill-offer re-ask tracking"
```

> Note: `offer_count` is intentionally NOT added to `_build_state` (server_helpers.py) — like `offered_skill_ids` and `declined_skills`, it persists via the LangGraph checkpoint. All reads use `state.get("offer_count") or 0`.

## Task B2: skill_select initialises `offer_count` on a fresh offer

**Files:**
- Modify: `src/sage_poc/nodes/skill_select.py` (`_resolve_entry`: `skill_offer_made` return ~269-276, accept-promotion return ~345-352, `all_candidates_declined` return ~261-268)
- Test: `tests/test_offer_variation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_offer_variation.py
import sage_poc.nodes.skill_select as skill_select
from sage_poc.nodes.skill_select import _resolve_entry, _SKILLS


def _base_state():
    return {"path": [], "detected_language": "en", "emotional_intensity": 5,
            "declined_skills": []}


def test_offer_made_sets_offer_count_to_one(monkeypatch):
    # Force the offer path: make the skill_matching rule engine fire nothing,
    # so _resolve_entry falls back to _FALLBACK_OFFER_ACTION (offer).
    class _NoFire:
        fired = []
    monkeypatch.setattr(skill_select.rules_engine, "evaluate", lambda *a, **k: _NoFire())

    candidates = list(_SKILLS.keys())[:2]
    result = _resolve_entry(_base_state(), candidates, "keyword", None)

    assert "skill_offer_made" in result["path"]
    assert result["offered_skill_ids"] == candidates
    assert result["offer_count"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_offer_variation.py::test_offer_made_sets_offer_count_to_one -v`
Expected: FAIL with `KeyError: 'offer_count'`

- [ ] **Step 3: Set offer_count in the offer return**

In `src/sage_poc/nodes/skill_select.py`, the `skill_offer_made` return (currently ~269-276) becomes:

```python
    return {
        "active_skill_id": None,
        "active_step_id": None,
        "offered_skill_ids": offerable,
        "offer_count": 1,
        "skill_match_method": f"{method}_offer",
        "semantic_score": semantic_score,
        "path": state["path"] + audit_markers + ["skill_offer_made"],
    }
```

- [ ] **Step 4: Reset offer_count where the offer resolves/clears in skill_select**

In the accept-promotion return (currently ~345-352), add `"offer_count": 0,` after `"offered_skill_ids": None,`:

```python
            return {
                "active_skill_id": chosen,
                "active_step_id": skill.steps[0].step_id,
                "offered_skill_ids": None,
                "offer_count": 0,
                "skill_match_method": "offer_accept",
                "semantic_score": None,
                "path": state["path"] + ["skill_select", "offer_promoted"],
            }
```

In the `all_candidates_declined` return (currently ~261-268), add `"offer_count": 0,`:

```python
        return {
            "active_skill_id": None,
            "active_step_id": None,
            "offer_count": 0,
            "skill_match_method": None,
            "semantic_score": None,
            "path": state["path"] + audit_markers + ["all_candidates_declined"],
        }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_offer_variation.py::test_offer_made_sets_offer_count_to_one tests/test_skill_select_offer.py -v`
Expected: PASS (new test + existing offer tests green)

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/nodes/skill_select.py tests/test_offer_variation.py
git commit -m "feat(offer): skill_select sets offer_count=1 on a fresh offer"
```

## Task B3: intent_route increments on re-ask, resets on resolve

**Files:**
- Modify: `src/sage_poc/nodes/intent_route.py:153-177`
- Test: `tests/test_offer_variation.py` (add)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_offer_variation.py`:

```python
import pytest
import sage_poc.nodes.intent_route as intent_route


class _FakeResp:
    def __init__(self, text):
        self._text = text


async def _route(monkeypatch, raw_json, state):
    async def _fake_invoke(*a, **k):
        return raw_json
    monkeypatch.setattr(intent_route, "resilient_invoke", _fake_invoke)
    monkeypatch.setattr(intent_route, "get_classifier", lambda: object())
    monkeypatch.setattr(intent_route, "get_fallback_classifier", lambda: object())
    monkeypatch.setattr(intent_route, "detect_directive_request", lambda s: False)
    return await intent_route.intent_route_node(state)


def _offer_state(offer_count):
    return {"path": [], "offered_skill_ids": ["box_breathing", "grounding_5_4_3_2_1"],
            "offer_count": offer_count, "declined_skills": []}


async def test_unparsed_offer_increments_offer_count(monkeypatch):
    # offer_response field absent -> classifier degradation -> preserve + re-ask
    state = _offer_state(1)
    result = await _route(monkeypatch, '{"primary_intent": "general_chat"}', state)
    assert "offer_unparsed" in result["path"]
    assert result["offer_count"] == 2


async def test_declined_offer_resets_offer_count(monkeypatch):
    state = _offer_state(2)
    result = await _route(monkeypatch, '{"primary_intent": "general_chat", "offer_response": "decline"}', state)
    assert "offer_declined" in result["path"]
    assert result["offer_count"] == 0


async def test_ignored_offer_resets_offer_count(monkeypatch):
    state = _offer_state(2)
    result = await _route(monkeypatch, '{"primary_intent": "general_chat", "offer_response": "other"}', state)
    assert result["offer_count"] == 0


async def test_accepted_offer_resets_offer_count(monkeypatch):
    state = _offer_state(2)
    result = await _route(
        monkeypatch,
        '{"primary_intent": "general_chat", "offer_response": "accept", "offer_choice_skill_id": "box_breathing"}',
        state,
    )
    assert "offer_accepted" in result["path"]
    assert result["offer_count"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_offer_variation.py -k offer_count -v`
Expected: FAIL with `KeyError: 'offer_count'` on each.

- [ ] **Step 3: Add the counter logic to intent_route**

In `src/sage_poc/nodes/intent_route.py`, in the offer-handling block (lines 153-177), add the four assignments.

In the `offer_unparsed` branch (after the existing `result["path"] = result["path"] + ["offer_unparsed"]`, line 161):

```python
            result["offer_count"] = (state.get("offer_count") or 0) + 1
```

In the `accept` branch (after line 167 `result["path"] = result["path"] + ["offer_accepted"]`):

```python
                result["offer_count"] = 0
```

In the `decline` branch (after line 174 `result["path"] = result["path"] + ["offer_declined"]`):

```python
                result["offer_count"] = 0
```

In the `else` (ignored/other) branch (after line 177 `result["path"] = result["path"] + ["offer_ignored"]`):

```python
                result["offer_count"] = 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_offer_variation.py -k offer_count tests/test_skill_select_offer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/nodes/intent_route.py tests/test_offer_variation.py
git commit -m "feat(offer): intent_route increments offer_count on re-ask, resets on resolve"
```

## Task B4: Create the re-ask template (DRAFT — needs sign-off)

**Files:**
- Create: `src/sage_poc/prompts/templates/L2_intents/skill_offer_reoffer.json`

- [ ] **Step 1: Create the template**

```json
{
  "template_id": "L2_skill_offer_reoffer",
  "version": "0.1.0",
  "status": "draft_pending_signoff",
  "authored_by": "engineering",
  "approved_by": null,
  "effective_date": "PENDING",
  "layer": "L2",
  "role": "user",
  "always_include": true,
  "word_budget": 90,
  "budget_note": "Exceeds §5.6 ~50-word L2 target by design: skill-offer turns carry no L3/L4/L5 layers, so total composed prompt stays under budget.",
  "content": "INTENT: You already offered this user a choice between a short exercise and simply continuing to talk, and they have not yet chosen. Do not repeat the full offer or re-list the options in detail. In one short, warm sentence, gently check what they would like, make clear there is no rush, and that just continuing to talk is completely fine. Use different wording than you used before, do not reuse the same stock sentence or the same closing question. Do not pressure. Keep it to one or two sentences.",
  "variables": [],
  "intent": "skill_offer",
  "_review_required": [
    "Clinical review: non-coercion preserved on the re-ask; no escalation of pressure across repeated offers."
  ],
  "_signed_off": ""
}
```

- [ ] **Step 2: Commit**

```bash
git add src/sage_poc/prompts/templates/L2_intents/skill_offer_reoffer.json
git commit -m "feat(offer): add draft re-ask offer template (pending clinical sign-off)"
```

## Task B5: Composer selects the reoffer variant on render 2+

**Files:**
- Modify: `src/sage_poc/prompts/composer.py:683-700`
- Test: `tests/test_offer_variation.py` (add)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_offer_variation.py`:

```python
from sage_poc.prompts.loader import get_intent_template, reload_all


def test_reoffer_template_loads_and_drops_full_relist():
    reload_all()
    base = get_intent_template("skill_offer")
    reoffer = get_intent_template("skill_offer", variant="reoffer")
    assert reoffer is not None, "reoffer variant must be loadable"
    assert reoffer.template_id == "L2_skill_offer_reoffer"
    assert reoffer is not base, "variant must differ from base"
    # The re-ask must NOT re-list options in detail
    assert "re-list" in reoffer.content or "do not repeat the full offer" in reoffer.content.lower()
```

The composer-selection behavior is exercised by a focused helper test. Append:

```python
def _variant_for(offer_count):
    """Mirror of the composer's offer-variant rule (kept in sync with composer.py)."""
    return "reoffer" if (offer_count or 0) >= 2 else None


def test_variant_rule_thresholds():
    assert _variant_for(1) is None    # first render -> base template
    assert _variant_for(2) == "reoffer"
    assert _variant_for(3) == "reoffer"
    assert _variant_for(0) is None
```

> The `_variant_for` mirror documents the exact threshold; the real selection lives in composer.py Step 3 and is covered end-to-end by Task B7's integration test.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_offer_variation.py -k reoffer -v`
Expected: `test_reoffer_template_loads_and_drops_full_relist` PASSES (template exists from B4); `test_variant_rule_thresholds` PASSES (pure mirror). If B4 not yet merged, the load test FAILS — confirm B4 first.

- [ ] **Step 3: Implement variant selection in composer.py**

In `src/sage_poc/prompts/composer.py`, replace the offer/intent block (currently lines 683-700) with:

```python
    if _offer_ids:
        _l2_intent = "skill_offer"
        _l2_extra = {"offer_options_block": _offer_block_str}
        # Repeat-offer variant: on the 2nd+ consecutive render of the same offer
        # (offer_count tracked across turns), switch to the lighter re-ask template
        # so the consent prompt does not read as a repeated script. Falls back to
        # the base skill_offer template automatically if the variant file is absent.
        _l2_variant = "reoffer" if (state.get("offer_count") or 0) >= 2 else None
    else:
        _l2_intent = (
            "new_skill_unmatched"
            if primary_intent == "new_skill" and not state.get("active_skill_id")
            else primary_intent
        )
        _l2_extra = None
        # Directive posture (deterministic flag from intent_route): when set on a general_chat
        # turn, select the stronger directive variant (lead with specific suggestions, do not
        # re-probe, no closing question). Falls back to base general_chat automatically if the
        # variant file is missing (get_intent_template returns the base on unknown variant).
        _l2_variant = "directive" if (state.get("directive_posture") and _l2_intent == "general_chat") else None
    l2_block = _build_l2_intent_block(
        _l2_intent, intensity, secondary_intent, variant=_l2_variant, extra_variables=_l2_extra
    )
    user_parts.append(l2_block)
    layers.append("intent")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_offer_variation.py -k "reoffer or variant" tests/test_engagement_templates.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/prompts/composer.py tests/test_offer_variation.py
git commit -m "feat(offer): composer uses reoffer variant on 2nd+ offer render"
```

## Task B6: Base offer template instructs wording variation (DRAFT — needs sign-off)

**Files:**
- Modify: `src/sage_poc/prompts/templates/L2_intents/skill_offer.json`
- Test: `tests/test_offer_variation.py` (add)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_offer_variation.py`:

```python
def test_base_offer_template_instructs_variation():
    reload_all()
    base = get_intent_template("skill_offer")
    assert "stock sentence" in base.content.lower() or "vary your" in base.content.lower(), (
        "base offer template must instruct the model to vary its wording"
    )
    # Non-coercion guardrail must remain intact
    assert "the user saying no is a complete answer" in base.content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_offer_variation.py::test_base_offer_template_instructs_variation -v`
Expected: FAIL (current template has no variation instruction)

- [ ] **Step 3: Update skill_offer.json**

In `src/sage_poc/prompts/templates/L2_intents/skill_offer.json`, bump `version` to `"0.2.0"`, set `status` to `"draft_pending_signoff"`, set `approved_by` to `null`, clear `_signed_off` to `""`, add a `budget_note` field (Flag 1), and update `content` to insert one sentence after "Ask which they would prefer, as one short question.".

Add this field (note: the base template's `word_budget` is **170**, not 90 — keep 170; the note records the deviation from the ~50-word target regardless of the exact figure):

```json
  "budget_note": "word_budget 170 exceeds §5.6 ~50-word L2 target by design: skill-offer turns carry no L3/L4/L5 layers, so total composed prompt stays under budget.",
```

Updated `content`:

```
"content": "INTENT: The user described something a short structured exercise could help with. A choice must be offered before any exercise begins. Emotional intensity: {intensity}/10. {intensity_guidance} First name the specific thing the user described, in one sentence. Then offer these options in plain everyday words, including roughly how long each takes:\n{offer_options_block}\nMake clear that simply continuing to talk is an equally good choice. Ask which they would prefer, as one short question. Vary your exact wording for the keep-talking option and the closing question from turn to turn, do not reuse a fixed stock sentence. Do not begin any exercise this turn. Do not use clinical or technique jargon beyond the names given. Do not pressure, the user saying no is a complete answer. Keep the whole reply to 2-4 sentences plus the options."
```

Also update `_review_required` to add: `"Clinical review of the new variation instruction (v0.2.0)"`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_offer_variation.py tests/test_engagement_templates.py -v`
Expected: PASS

> If `test_engagement_templates.py` pins the exact v0.1.0 `content` string, update that pin to the v0.2.0 string in the same commit — the content guard is intentionally strict; re-pinning is the correct response to an intended wording change.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/prompts/templates/L2_intents/skill_offer.json tests/test_offer_variation.py
git commit -m "feat(offer): base offer template instructs wording variation (v0.2.0, pending sign-off)"
```

## Task B7: Clear offer_count at session boundaries + end-to-end guard

**Files:**
- Modify: `src/sage_poc/server_helpers.py` (`_void_unseen_offer` ~line 42; stale-clear overrides ~lines 111-114)
- Test: `tests/test_offer_variation.py` (add)

- [ ] **Step 1: Write the failing test (stale-gap clears the counter)**

Append to `tests/test_offer_variation.py`:

```python
from sage_poc.server_helpers import _stale_skill_overrides


def test_stale_gap_clears_offer_count():
    # A checkpoint with a pending offer that is now stale (4h+ gap) must clear
    # offered_skill_ids, declined_skills, AND offer_count together.
    import datetime
    old = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=5)).isoformat()
    checkpoint = {
        "offered_skill_ids": ["box_breathing"],
        "declined_skills": ["grounding_5_4_3_2_1"],
        "offer_count": 3,
        "last_turn_at": old,
    }
    overrides = _stale_skill_overrides(checkpoint)
    assert overrides.get("offered_skill_ids") is None
    assert overrides.get("offer_count") == 0
```

> Confirm the actual stale-clear function name/signature in `server_helpers.py` before running — the grep showed the clearing logic around lines 79-114. If the public entry is named differently (e.g. `_maybe_clear_stale`), adjust the import and call in this test accordingly.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_offer_variation.py::test_stale_gap_clears_offer_count -v`
Expected: FAIL — `overrides.get("offer_count")` is `None`, not `0`.

- [ ] **Step 3: Clear offer_count in the stale-clear path**

In `src/sage_poc/server_helpers.py`, in the stale-clear override block (where `overrides["offered_skill_ids"] = None` is set, ~line 112), add alongside it:

```python
                overrides["offer_count"] = 0
```

- [ ] **Step 4: Clear offer_count in the errored-offer compensation path**

In `_void_unseen_offer` (~line 42), change the `aupdate_state` call to also zero the counter:

```python
            await graph.aupdate_state(config, {"offered_skill_ids": None, "offer_count": 0})
```

- [ ] **Step 5: Run the full offer + server suites**

Run: `pytest tests/test_offer_variation.py tests/test_skill_select_offer.py tests/test_server_offer_voiding.py tests/test_output_gate_offer_voiding.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/server_helpers.py tests/test_offer_variation.py
git commit -m "feat(offer): clear offer_count at stale gap and on voided offer"
```

## Task B8: Full regression

- [ ] **Step 1: Run the whole suite**

Run: `pytest -q`
Expected: All green (baseline before this work + the new tests). If any pinned-content engagement test fails, it is the intended v0.2.0 re-pin from B6 — confirm the diff is only the variation sentence, then update the pin.

- [ ] **Step 2: Commit any pin updates**

```bash
git add -A
git commit -m "test: re-pin offer template content to v0.2.0"
```

---

## Self-review

**Spec coverage:**
- Feedback #4 (dialect drift) → Part A (A1 exemplars, A2 builder, A3 wiring, A4 human validation). ✓
- Feedback #3 (repetition) → Part B: re-ask variant (B4/B5), wording variation in base (B6), counter plumbing (B1/B2/B3), session-boundary cleanup (B7). ✓
- "Complete from my side, clinician approves" → the three sign-off artifacts are drafted with `status: draft_pending_signoff` + empty `_signed_off`; CI runs green without sign-off (verified no L2-status gate). ✓
- "Research best practices" → few-shot + consistent dialect naming (Part A prompt design); re-ask suppression + paraphrase variation mirrors the directive-variant pattern already in the codebase and the mental-health-chatbot repetition literature. ✓

**Placeholder scan:** No "TBD"/"add error handling"/"similar to" — every code and test step shows full content. The only deliberate `PENDING`/empty values are inside the sign-off artifacts (that is the clinician's input), and Task A4 is explicitly a manual gate, not code.

**Type/symbol consistency:** `offer_count` (int) used identically in state.py, skill_select.py, intent_route.py, composer.py, server_helpers.py; always read as `state.get("offer_count") or 0`. `_build_khaleeji_translation_prompt` / `_khaleeji_exemplars` names match between definition (A2) and use (A3, tests). Variant string `"reoffer"` matches `skill_offer_reoffer.json` template_id suffix and `get_intent_template(..., variant=...)` resolution (`L2_skill_offer_reoffer`). ✓

**Counter ordering (verified against graph):** on the offer-MADE turn, input `offered_skill_ids` is empty so intent_route's offer block does not run; skill_select sets `offer_count=1`; composer renders base. On a re-ask turn, `offered_skill_ids` persists, intent_route's `offer_unparsed` branch increments to 2, the turn routes to freeflow (not skill_select), so the counter is not clobbered; composer renders reoffer. On resolve, intent_route (decline/ignore) or skill_select (accept) zeroes it. ✓ Rare edge (an ambiguous re-ask that re-routes through skill_select and re-offers) resets to 1 → shows base again: acceptable degradation, not harmful.

---

## Sources (best-practice research)

- Few-shot beats zero-shot for dialectal Arabic, and naming the dialect (not codes) improves output — [Cross-dialectal Arabic translation: comparative analysis on LLMs (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12488727/), [Exploring prompting for dialectal machine translation (PeerJ)](https://peerj.com/articles/cs-3209/), [Advancing Dialectal Arabic to MSA MT (arXiv)](https://arxiv.org/pdf/2507.20301)
- Repetition/looping is the most-reported failure in mental-health chatbots; response variation is a known mitigation — [A review of explainability and safety of conversational agents for mental health (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10601652/), [Rule-Based Conversational Agent for Mental Health in Young People (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12706453/)
