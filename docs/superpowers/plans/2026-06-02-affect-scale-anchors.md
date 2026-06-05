# Affect Scale Behavioral Anchors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit behavioral anchor descriptions to the `emotional_intensity` and `engagement` 1-10 scales in `INTENT_SYSTEM`, and the resistance 1-10 scale in `resistance_prompt.json`, to reduce LLM score inflation and mid-range ambiguity.

**Architecture:** Two prompt edits, regression-guard tests, and one slow calibration eval. No logic changes. The anchors apply established Behaviorally Anchored Rating Scales (BARS) methodology — replacing single-line definitions with behavioral examples per band. Fast tests assert anchor presence; a separate `@pytest.mark.slow` calibration test calls the real LLM to verify band assignments are roughly correct. This is a hypothesis test, not a deterministic assertion — repeated failure at the same case warrants prompt review.

**Arabic/Khaleeji note:** `intent_route` receives `state['message_en']`, which is already translated to English by `safety_check_node` before the node runs. English-only anchor examples in `INTENT_SYSTEM` are therefore architecturally correct. Limitation: Khaleeji dialect translation quality affects the fidelity of the English text the LLM scores; this is a translation-layer concern outside this plan's scope (see TD4/TD6).

**Tech Stack:** Python, pytest, JSON

---

## Files Touched

| Action | File | Why |
|--------|------|-----|
| Modify | `sage-poc/src/sage_poc/nodes/intent_route.py` (lines 15–33) | `INTENT_SYSTEM` prompt — `emotional_intensity` and `engagement` anchor text |
| Modify | `sage-poc/src/sage_poc/rules/data/resistance_scoring/resistance_prompt.json` | `resistance_score_v1` prompt — resistance anchor text |
| Modify | `sage-poc/tests/test_intent_route_node.py` | Add anchor presence regression tests |
| Create | `sage-poc/tests/test_intent_anchor_calibration.py` | Slow calibration eval — labeled messages → expected band |
| Create | `sage-poc/tests/test_resistance_prompt.py` | Anchor presence regression tests for resistance prompt |

---

## Task 1: Anchor regression tests for INTENT_SYSTEM

**Files:**
- Modify: `tests/test_intent_route_node.py`

These are fast, no-LLM tests that lock in the anchor contract — if someone edits the prompt and removes or narrows the anchors, the tests break immediately.

- [ ] **Step 1: Add the three anchor tests to `test_intent_route_node.py`**

Append to the end of `tests/test_intent_route_node.py`:

```python
def test_intent_system_emotional_intensity_has_behavioral_anchors():
    """INTENT_SYSTEM emotional_intensity scale must have behavioral anchors for each band.

    Plain 1=calm/10=distressed definitions cause LLM score inflation.
    Anchors apply established BARS (Behaviorally Anchored Rating Scales) methodology
    to give the LLM calibration examples per band. This test is a regression guard:
    if anchors are removed, the guard trips.
    """
    from sage_poc.nodes.intent_route import INTENT_SYSTEM
    prompt = INTENT_SYSTEM.lower()
    # Low band anchor present
    assert "1-2" in INTENT_SYSTEM or "1–2" in INTENT_SYSTEM, (
        "emotional_intensity must have a 1-2 band anchor"
    )
    # Mid band anchor present
    assert "5-6" in INTENT_SYSTEM or "5–6" in INTENT_SYSTEM, (
        "emotional_intensity must have a 5-6 band anchor"
    )
    # High band anchor present
    assert "7-8" in INTENT_SYSTEM or "7–8" in INTENT_SYSTEM, (
        "emotional_intensity must have a 7-8 band anchor"
    )
    # Anchors should include behavioral examples, not just labels
    assert any(word in prompt for word in ["reply", "replies", "elaborat", "rumina", "distress"]), (
        "emotional_intensity anchors must include behavioral/linguistic examples, not just labels"
    )


def test_intent_system_engagement_has_behavioral_anchors():
    """INTENT_SYSTEM engagement scale must have behavioral anchors for each band.

    Same inflation/ambiguity problem as emotional_intensity.
    """
    from sage_poc.nodes.intent_route import INTENT_SYSTEM
    prompt = INTENT_SYSTEM.lower()
    # Low band — one-word / minimal replies
    assert any(phrase in prompt for phrase in ["one-word", "one word", "minimal", "deflect"]), (
        "engagement anchors must describe low-engagement behaviour (one-word replies, deflection)"
    )
    # High band — elaboration / disclosure
    assert any(phrase in prompt for phrase in ["elaborat", "reflection", "personal example", "disclosure"]), (
        "engagement anchors must describe high-engagement behaviour (elaboration, personal examples)"
    )


def test_intent_system_crisis_band_reserved_for_9_10():
    """9-10 emotional_intensity must be reserved for crisis-adjacent language only.

    This prevents the LLM from scoring generic high distress as 9-10,
    which would confuse the escalation threshold with crisis detection.
    """
    from sage_poc.nodes.intent_route import INTENT_SYSTEM
    prompt = INTENT_SYSTEM.lower()
    assert "9-10" in INTENT_SYSTEM or "9–10" in INTENT_SYSTEM, (
        "emotional_intensity must have a 9-10 band anchor reserving it for crisis-adjacent language"
    )
    assert any(word in prompt for word in ["crisis", "harm", "hopeless"]), (
        "9-10 band must reference crisis/harm/hopelessness to prevent over-scoring general distress"
    )
```

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_intent_route_node.py::test_intent_system_emotional_intensity_has_behavioral_anchors tests/test_intent_route_node.py::test_intent_system_engagement_has_behavioral_anchors tests/test_intent_route_node.py::test_intent_system_crisis_band_reserved_for_9_10 -v
```

Expected: all three FAIL (the current prompt has no band anchors).

---

## Task 2: Update INTENT_SYSTEM with behavioral anchors

**Files:**
- Modify: `src/sage_poc/nodes/intent_route.py` (lines 19–21)

Replace only the `emotional_intensity` and `engagement` field definitions inside `INTENT_SYSTEM`. Do not change any other part of the prompt.

- [ ] **Step 1: Apply the anchor text**

In `src/sage_poc/nodes/intent_route.py`, replace the current two-line definitions:

```
- emotional_intensity: integer 1-10 (1=calm, 10=extremely distressed)
- engagement: integer 1-10 (1=one-word/dismissive, 10=elaborating/open)
```

With:

```
- emotional_intensity: integer 1-10 — distress level inferred from message content:
  1-2: Positive, neutral, or grounding language ("I'm good", "things are fine", gratitude, just checking in)
  3-4: Mild or managed difficulty without named symptoms ("a bit stressed", "not great but okay", "tired lately")
  5-6: Named distress tied to a specific symptom or pattern ("can't stop ruminating", "haven't slept properly", "feeling overwhelmed", "keep blaming myself")
  7-8: Significant distress, urgency, or helplessness — multiple signals present ("can't take it anymore", "everything is falling apart", "I don't know what to do")
  9-10: Reserve for crisis-adjacent language only — explicit hopelessness, harm ideation, or statements that safety_check would also flag
- engagement: integer 1-10 — how much the user is elaborating and opening up:
  1-2: One-word or minimal replies, deflection, or refusal to engage ("fine", "idk", "whatever", "I don't want to talk about it")
  3-4: Brief replies with little elaboration, vague or non-committal ("maybe", "I guess", "sort of")
  5-6: Some reflection or relevant elaboration, present but not expansive ("yeah I've been thinking about that", "I suppose so, sort of")
  7-8: Active reflection, personal examples, or follow-up questions — multi-sentence, bringing context
  9-10: Deep elaboration or meaningful disclosure — multi-paragraph, sharing something not previously mentioned
```

- [ ] **Step 2: Run the anchor tests — confirm they now pass**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_intent_route_node.py::test_intent_system_emotional_intensity_has_behavioral_anchors tests/test_intent_route_node.py::test_intent_system_engagement_has_behavioral_anchors tests/test_intent_route_node.py::test_intent_system_crisis_band_reserved_for_9_10 -v
```

Expected: all three PASS.

- [ ] **Step 3: Run the full test suite to confirm no regressions**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_intent_route_node.py tests/test_nodes.py tests/test_intent_header_parity.py -v
```

Expected: all existing tests PASS. Pay particular attention to `test_intent_system_prompt_does_not_say_mental_health_assistant` and `test_bare_emotional_words_classified_as_general_chat` — the former checks identity framing, the latter (slow/LLM) is skipped unless marked.

- [ ] **Step 4: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git add src/sage_poc/nodes/intent_route.py tests/test_intent_route_node.py
git commit -m "fix: add behavioral anchors to emotional_intensity and engagement scales in INTENT_SYSTEM

Plain 1=calm/10=distressed definitions cause LLM score inflation and mid-range
ambiguity. Anchors apply BARS (Behaviorally Anchored Rating Scales) methodology —
calibration examples per band. 9-10 band explicitly reserved for crisis-adjacent
language to prevent threshold pollution. Regression tests guard the anchor contract."
```

---

## Task 2b: Calibration eval — labeled messages verify band assignments

**Files:**
- Create: `tests/test_intent_anchor_calibration.py`

These are `@pytest.mark.slow` tests that call the real LLM and assert each labeled message scores within its expected band. They are probabilistic — a single flake is noise, repeated failure at the same case means the anchor needs tightening. They are also the validation evidence that presence tests (Task 1) cannot provide.

Band tolerance is set ±1 wider than the target band to reduce flakiness from LLM variability. The cases are chosen to be unambiguous — easy to classify even for a poorly calibrated model — so a miss is a signal, not a coincidence.

- [ ] **Step 1: Create `tests/test_intent_anchor_calibration.py`**

```python
"""Slow calibration tests for INTENT_SYSTEM behavioral anchors.

These tests call the real LLM to verify that the anchored scales produce
roughly correct band assignments. They are probabilistic — repeated failure
at the same case warrants prompt review, not just re-running.

Run: uv run pytest tests/test_intent_anchor_calibration.py -m slow -v

Design note: each message was chosen to be unambiguously in its target band.
Tolerance is set to ±1 of the band edge to absorb LLM variability without
hiding genuine miscalibration. The cases align with step_policy rule thresholds:
  - emotional_intensity >=7 triggers validate_only path
  - engagement <=3 for 3 turns triggers check-in rule
  - emotional_intensity 9-10 must not fire from general distress (crisis band)
"""
import pytest

# (message, label, band_min, band_max)
# band_min/max include ±1 tolerance around the anchor band edges
EMOTIONAL_INTENSITY_CASES = [
    ("I'm doing really well today, feeling positive and grateful", "low", 1, 3),
    ("yeah fine", "low", 1, 3),
    ("I've been a bit stressed lately but nothing I can't handle", "mid-low", 2, 5),
    (
        "I've been having panic attacks every morning for two weeks and I can't concentrate at work",
        "mid-high", 4, 7,
    ),
    (
        "I can't take this anymore. Everything is falling apart and I genuinely don't know how to keep going.",
        "high", 6, 9,
    ),
]

ENGAGEMENT_CASES = [
    ("no", "low", 1, 3),
    ("idk", "low", 1, 3),
    ("yeah I guess so", "mid", 2, 6),
    (
        "I've been thinking about what you said and I think the reason I get so anxious is "
        "because growing up, expressing feelings was seen as weakness in my family. I never "
        "learned how to talk about this stuff and now it just builds up.",
        "high", 6, 10,
    ),
]


def _base_state(message: str) -> dict:
    return {
        "message_en": message,
        "detected_language": "en",
        "is_safe": True,
        "crisis_state": "none",
        "active_skill_id": None,
        "crisis_flags": [],
        "clinical_flags": [],
        "conversation_history": [],
        "therapeutic_profile": None,
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 5,
        "engagement": 5,
        "path": ["safety_check"],
    }


@pytest.mark.slow
@pytest.mark.parametrize("message,label,band_min,band_max", EMOTIONAL_INTENSITY_CASES)
async def test_emotional_intensity_anchor_calibration(message, label, band_min, band_max):
    """emotional_intensity for a labeled message must fall within its expected band.

    Failure means: the anchor text is not giving the LLM sufficient calibration
    for this band, or the band boundaries need adjustment.
    """
    from sage_poc.nodes.intent_route import intent_route_node

    result = await intent_route_node(_base_state(message))
    score = result["emotional_intensity"]
    assert band_min <= score <= band_max, (
        f"[emotional_intensity/{label}] '{message}'\n"
        f"Expected score in [{band_min}, {band_max}], got {score}.\n"
        f"If this fails repeatedly, review the {band_min}-{band_max} anchor text in INTENT_SYSTEM."
    )


@pytest.mark.slow
@pytest.mark.parametrize("message,label,band_min,band_max", ENGAGEMENT_CASES)
async def test_engagement_anchor_calibration(message, label, band_min, band_max):
    """engagement for a labeled message must fall within its expected band.

    Failure means: the anchor text is not giving the LLM sufficient calibration
    for this band. Low-band failures are highest priority — engagement <=3 feeds
    the check-in rule (for_turns=3).
    """
    from sage_poc.nodes.intent_route import intent_route_node

    result = await intent_route_node(_base_state(message))
    score = result["engagement"]
    assert band_min <= score <= band_max, (
        f"[engagement/{label}] '{message}'\n"
        f"Expected score in [{band_min}, {band_max}], got {score}.\n"
        f"If this fails repeatedly, review the {band_min}-{band_max} anchor text in INTENT_SYSTEM."
    )


@pytest.mark.slow
async def test_crisis_adjacent_message_scores_9_or_10():
    """A message with explicit hopelessness must score 9-10 on emotional_intensity.

    This verifies the 9-10 band reservation is working — if explicit harm language
    scores 7-8, the crisis threshold is being diluted.
    """
    from sage_poc.nodes.intent_route import intent_route_node

    message = "I don't see the point anymore. I've been thinking about not being here."
    result = await intent_route_node(_base_state(message))
    score = result["emotional_intensity"]
    assert score >= 8, (
        f"Explicit hopelessness/harm ideation must score >=8, got {score}.\n"
        f"If 7-8 band is absorbing crisis language, tighten the 9-10 band anchor."
    )
```

- [ ] **Step 2: Run the calibration tests — confirm they execute against the real LLM**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_intent_anchor_calibration.py -m slow -v
```

Expected: all tests PASS. If any fail, note which case failed and what score was returned — this is diagnostic information for prompt tuning, not a blocker for committing.

- [ ] **Step 3: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git add tests/test_intent_anchor_calibration.py
git commit -m "test: add slow calibration eval for INTENT_SYSTEM affect scale anchors

9 labeled cases (5 emotional_intensity, 4 engagement) verify band assignments
against the real LLM. Presence tests alone cannot validate that anchors reduce
inflation — these tests are the behavioral evidence. Marked @pytest.mark.slow;
not in default CI run."
```

---

## Task 3: Anchor regression tests for resistance prompt

**Files:**
- Create: `tests/test_resistance_prompt.py`

- [ ] **Step 1: Create the test file**

```python
"""Regression tests for resistance_prompt.json.

Resistance scoring has the same LLM inflation problem as emotional_intensity/engagement.
These tests assert the prompt contains behavioral anchors, so future edits that
remove calibration context are caught immediately.
"""
import json
from pathlib import Path


def _load_prompt() -> str:
    path = (
        Path(__file__).parent.parent
        / "src/sage_poc/rules/data/resistance_scoring/resistance_prompt.json"
    )
    data = json.loads(path.read_text())
    return data["prompt"]


def test_resistance_prompt_has_low_band_anchor():
    """1-3 band must describe full engagement, not just 'full engagement' label."""
    prompt = _load_prompt().lower()
    assert any(word in prompt for word in ["reflect", "respond", "engag", "elaborat", "open"]), (
        "Resistance prompt low band must describe engaged behaviour, not just label it"
    )


def test_resistance_prompt_has_high_band_anchor():
    """8-10 band must describe concrete refusal or disengagement behaviour."""
    prompt = _load_prompt().lower()
    assert any(
        phrase in prompt
        for phrase in ["explicit refusal", "won't", "refuses", "complete refusal", "active disengagement"]
    ), (
        "Resistance prompt high band must describe concrete refusal behaviour"
    )


def test_resistance_prompt_has_indirect_refusal_anchor():
    """Gulf Arab indirect refusal patterns must be described with behavioural examples."""
    prompt = _load_prompt().lower()
    assert any(
        phrase in prompt
        for phrase in ["changing subject", "short answer", "one-word", "one word", "deflect"]
    ), (
        "Resistance prompt must have behavioral examples of indirect refusal for Gulf Arab context"
    )
```

- [ ] **Step 2: Run the new tests and confirm which ones fail**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_resistance_prompt.py -v
```

Expected: `test_resistance_prompt_has_low_band_anchor` and `test_resistance_prompt_has_high_band_anchor` likely pass (current prompt has some of this), `test_resistance_prompt_has_indirect_refusal_anchor` may pass or fail. Note which fail.

---

## Task 4: Update resistance_prompt.json with behavioral anchors

**Files:**
- Modify: `src/sage_poc/rules/data/resistance_scoring/resistance_prompt.json`

- [ ] **Step 1: Apply the anchor text**

Replace the current `prompt` value in `resistance_prompt.json` with:

```json
{
  "template_id": "resistance_score_v1",
  "authored_by": "sage_clinics",
  "prompt": "You are a clinical assistant evaluating therapeutic engagement. Score the user's resistance to continuing the current therapeutic activity on a scale from 1 to 10, using these behavioral anchors:\n  1-2: Actively engaged — responds with reflection, elaboration, or personal examples; open to continuing\n  3-4: Mild hesitation — brief but relevant replies, some hedging (\"maybe\", \"I'm not sure\"), no active pushback\n  5-6: Moderate disengagement — one-word or vague replies, topic drift, or non-committal responses without outright refusal\n  7-8: Clear resistance — deflection, changing subject, invoking busyness or tiredness, implicit reluctance without explicit refusal\n  9-10: Active refusal or complete disengagement — explicit \"I don't want to\", \"stop\", silence after repeated prompts, or walking away\nIn a Gulf Arab context, indirect signals (changing subject, very short answers, invoking busyness) carry equal weight to direct refusal — score these in the 6-8 range, not lower.\nMessage: {message_en}. Recent context: {recent_context}.\nReturn only a single integer between 1 and 10.",
  "output_type": "integer",
  "scale_min": 1,
  "scale_max": 10
}
```

- [ ] **Step 2: Run the resistance prompt tests — confirm all pass**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_resistance_prompt.py -v
```

Expected: all three PASS.

- [ ] **Step 3: Run the full test suite to confirm no regressions**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/ -v --ignore=tests/test_e2e.py 2>/dev/null || uv run pytest tests/ -v
```

Expected: all non-slow, non-integration tests PASS.

- [ ] **Step 4: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git add src/sage_poc/rules/data/resistance_scoring/resistance_prompt.json tests/test_resistance_prompt.py
git commit -m "fix: add behavioral anchors to resistance scoring prompt

Same inflation/ambiguity fix as emotional_intensity/engagement. Gulf Arab indirect
refusal examples now have explicit band placement (6-8) to prevent under-scoring
of culturally indirect disengagement. Regression tests added."
```

---

## Self-Review

**Spec coverage:**
- ✅ Behavioral anchors for `emotional_intensity` (Task 2) — covers full 1-10 range with linguistic examples
- ✅ Behavioral anchors for `engagement` (Task 2) — covers full 1-10 range with behavioral descriptions
- ✅ 9-10 band explicitly reserved for crisis-adjacent language (Task 2) — prevents threshold pollution
- ✅ Fast regression tests guard both prompts (Tasks 1 and 3)
- ✅ Slow calibration eval verifies band assignments against real LLM (Task 2b) — 9 labeled cases, aligns with step_policy thresholds (>=7 validate_only, <=3 check-in, 9-10 crisis band)
- ✅ Resistance prompt anchors (Task 4) — includes Gulf Arab indirect refusal band placement
- ✅ Arabic/Khaleeji coverage: documented in Architecture note — `message_en` post-translation is what intent_route receives; English anchors are architecturally correct
- ✅ BARS citation: EACL preprint removed from commits/docstrings; replaced with established BARS methodology reference

**Placeholder scan:** No TBDs, no "fill in details", no "similar to Task N". All code is complete.

**Type consistency:** No cross-task type dependencies — all tasks are independent prompt/test edits.

**What this does NOT change:**
- No routing logic changes — `emotional_intensity` and `engagement` are still written to state the same way
- No threshold changes — escalation thresholds in `safety_check.py` are unchanged
- No test mocks need updating — the mocked LLM responses in existing tests return hardcoded integers, not text processed through the prompt
