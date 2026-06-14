# Engagement: Advice Posture, Question Discipline & Anti-Generic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the advice-conversation failure mode (endless questions, then generic advice, ending on another question) by rebalancing the *default* conversational posture, enforcing question discipline deterministically, and detecting explicit delegation without loading the LLM classifier — addressing the three failures the People/Pain/LLMs research brief (June 2026) weights hardest.

**Architecture:** Four independent levers, sequenced posture-first:
1. **Posture (L0 + L2 `general_chat`)** — clinician-authored prompt change: validate → give *specific* suggestions once there's enough to act on → ask at most **one open question, never stacked** → **resist over-affirmation** (gentle challenge when warranted). Helps every conversation; no classifier dependency.
2. **Deterministic delegation backstop** — a keyword + frustration-repair detector sets a `directive_posture` state flag (NOT an intent, NOT the LLM classifier). The composer then selects a stronger `general_chat_directive` L2 variant.
3. **Question-discipline gate (Node 8 output_gate)** — deterministic: collapse stacked questions to one; strip the trailing question on directive turns. (NOT a rules-engine rule — the schema can't count/trim; see Task 8 note.)
4. **Anti-generic eval coverage** — register ≥4.0 + a specificity/tailoring dimension in the quality-log rubric, plus directive scenarios. Prompt/few-shot lever only; this one **cannot** be a deterministic gate (you can't regex "specific to what the user said").

**Tech Stack:** Python 3.11, LangGraph, pydantic prompt templates (JSON), the rules engine (`sage_poc.rules`), pytest (asyncio_mode=auto; `-m slow` = live-LLM tests), the `tests/experiment_4_4` clinician quality-log harness.

**Why (evidence):** Production replay 2026-06-14 (chat.biosight.ai) reproduced the loop through turn 4. The brief flags the exact failures: "Generic, superficial responses" is the #1 cited frustration (JMIR 2025: "so generic I just existed in this space"); "over-affirmation without challenge" is a distinct top frustration (~60 Reddit comments); MIND-SAFE mandates "ask one question at a time, never stack." See [[advice-request-option-b]] and the superseded plan `2026-06-14-advice-request-intent-option-b.md` for why the discrete-intent approach was rejected.

---

## Decision Points (resolve BEFORE Task 1)

- **D1 — Question-discipline scope (clinical awareness).** `_limit_to_one_question` runs on **freeflow turns only** — it is SKIPPED when `state.get("step_instruction")` is set (skill-execution turns), so it never overrides a clinician-authored skill step that legitimately phrases its own question. **Default: freeflow-only** (changed from global on review — respects clinician autonomy over L3 step content and shrinks the Flag-1 surface). Override → global (drop the `step_instruction` guard) if clinicians want stacking collapsed inside skills too.
- **D2 — Delegation detector precision (clinical).** The phrase list (Task 2) is deliberately high-precision (explicit delegation + frustration-repair), NOT genuine first questions. **Default: as listed.** Clinician may add/remove phrases.
- **D3 — Over-affirmation challenge strength (clinical).** The posture rewrite adds "resist over-affirmation / gentle challenge." Gentle-challenge is dependency-sensitive; per [[engagement-layer-proposal]] it must stay gated (warmth-first, never on a crisis/acute turn). **Default: gentle, non-acute only.**
- **Rule 1 scope.** No *control-layer* change (no new intent, no routing change), so no Rule-1 review on routing. L0/L2 changes are prompt-layer → clinical sign-off, like the L0 v2.0.0 rewrite. **BUT question-discipline IS a Rule-1 deviation (see Task 0):** it is a clinical policy — a clinical threshold ("one question") plus a clinical carve-out (crisis/monitoring) — being hardcoded into engineer-owned `output_gate.py` instead of the CMS-authored Rules Service, only because the `cultural_output` schema cannot count/trim. That needs explicit Rule-1 approval + clinical awareness on the threshold + a post-POC schema-extension follow-up. NOT filed as "no sign-off."

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `src/sage_poc/state.py` | `SageState` TypedDict | Add `directive_posture: bool` |
| `src/sage_poc/server_helpers.py` | `_build_state` per-turn reset | Init `directive_posture: False` |
| `src/sage_poc/nodes/directive_detect.py` | Deterministic delegation/frustration detector | **New** |
| `src/sage_poc/nodes/intent_route.py` | Node 2 | Call detector, set flag (no classifier change) |
| `src/sage_poc/prompts/composer.py` | L2 selection | Pass `variant="directive"` when flag set + general_chat |
| `src/sage_poc/prompts/templates/L2_intents/general_chat_directive.json` | Directive posture variant | **New** (repurpose advice draft) |
| `src/sage_poc/prompts/templates/L2_intents/general_chat.json` | Base posture | Rewrite: validate→specific→floor-return→companion-scope (≤1Q + resist-over-affirmation live in L0, NOT here) |
| `src/sage_poc/prompts/templates/L2_intents/advice_request.json` | Old draft | **Delete** (content moves to the variant) |
| `src/sage_poc/prompts/templates/L0_persona.json` | Persona | v2.1.0 additive: one-question rule + resist over-affirmation |
| `src/sage_poc/nodes/output_gate.py` | Node 8 | `_limit_to_one_question` + `_strip_trailing_question` |
| `tests/experiment_4_4/generate_quality_log.py` | Quality rubric | Add `register_score` + `specificity_tailoring` |
| `tests/test_directive_detect.py` | Detector unit tests | **New** |
| `tests/test_routing.py`, `tests/test_intent_route_node.py`, `tests/test_prompts_loader.py`, `tests/test_nodes.py`, `tests/test_output_gate_response_paths.py` | Coverage | Extend |
| `docs/superpowers/governance/2026-06-14-engagement-advice-posture.md` | Sign-off record | **New** |

---

## Task 0: Governance record (clinical sign-off; no Rule 1)

**Files:** Create `docs/superpowers/governance/2026-06-14-engagement-advice-posture.md`

- [ ] **Step 1: Write the record**

```markdown
# Governance: Engagement Advice Posture, Question Discipline & Anti-Generic

**Date:** 2026-06-14
**Supersedes posture stopgap:** Option A (general_chat exception clause — absorbed into base posture, Task 6)
**Control-layer change?** NO. No new intent, no routing change → no Rule 1.
**Evidence:** Production replay 2026-06-14 (chat.biosight.ai); People/Pain/LLMs brief (MIND-SAFE,
JMIR 2025 genericness #1 frustration, Reddit over-affirmation ~60 comments).

## Sign-offs
- [ ] Clinical: L2 general_chat base posture rewrite (Task 6) — approver: ____  date: ____
- [ ] Clinical: L0 persona v2.1.0 additive (Task 7) — approver: ____  date: ____
- [ ] Clinical: general_chat_directive variant content (Task 5) — approver: ____  date: ____
- [ ] Clinical: delegation phrase list precision (Task 2, D2) — approver: ____  date: ____

## Decisions (see plan §Decision Points)
- D1 question-discipline scope: GLOBAL. Approved? ____
- D3 over-affirmation challenge: gentle, non-acute only. Approved? ____

## Absolute Rule 1 — L0/L2 word-budget deviation (APPROVED 2026-06-14, option: compress + document)
The v7 prompt-architecture budgets L2 at ~50w with a ~1,100w total ceiling when all layers fire.
This feature deviates; recorded here per Absolute Rule 1 (flag + approve, do not silently bump).
- **L2 general_chat (always_include:true): 50 → 100** (actual content ~95w). Reason: validate→specific→
  floor-return→companion-scope cannot compress to 50w. The two truly-global rules (one-question,
  resist-over-affirmation) are placed in L0 ONLY (not duplicated per-L2) to minimise this.
- **L2 general_chat_directive variant: budget 100 (~95w).** NOT always-on — it REPLACES the base
  general_chat block on directive turns, so it is mutually exclusive with the base, not additive.
- **L0 persona: 550 → 590** (v2.1.0, actual ~585w). L0 was already a documented deviation (542w vs
  spec 150w, set in v2.0.0); v2.1.0 adds the one-question + resist-over-affirmation global rules.
- **Total-ceiling check (verified against composer.py):** L3 (skill, needs step_instruction, :780) and
  L4 (knowledge, needs info_request, :254) do NOT fire on general_chat freeflow turns (:216). So the
  170→1,220 worst-case does not occur. Realistic general_chat turn = L0(~585) + L1(flex cap 600, a
  history-TRUNCATION cap not a fixed cost — early turns carry little) + L2(~95) + L5(~100) + optional
  cultural/clinical blocks. The driver is the pre-existing L0+L1 base, not this change; net NEW
  always-on cost from this plan ≈ +50w (L2) + ~40w (L0). Accepted for POC.
- **Approved by (product owner, Rule 1):** ____________  date: 2026-06-14

## Deploy gate (issue #3 — clinician autonomy)
Task 10 (deploy) and the draft→approved status flips in Tasks 5/6/7 MUST NOT proceed until the four
clinical sign-off boxes above are checked (name + date). Engineering-only tasks (1-4, 8, 9) may land
first. If the boxes are unchecked at Task 10, STOP and surface to the user — do not deploy
clinician-authored posture on POC-provisional drafts unless the user explicitly accepts that risk
in writing here: ____________

## Governance burn-down lane (KNOWN_LIVE_TEMPLATES) — lifecycle
Clinician-authored templates that are wired into routing but not yet signed off must use the canonical
`status: "draft-pending-review"` (exempts them from `test_no_live_template_without_approved_by`) AND be
listed in `tests/test_clinical_governance.py::test_draft_templates_are_actually_inert`'s
`KNOWN_LIVE_TEMPLATES` set — a forcing function that keeps the governance lane RED (the lane is excluded
from the unit-gate) until sign-off. This matches the `new_skill_unmatched` precedent.
- `L2_general_chat_directive` — ADDED to KNOWN_LIVE_TEMPLATES 2026-06-14 (done, commit on branch).
- `L2_general_chat` (Task 6) and `L0_persona` (Task 7) — these are currently APPROVED+live; when Task 6/7
  set them to `draft-pending-review` during the change window, ADD both to KNOWN_LIVE_TEMPLATES too (they
  are always wired), else `test_no_live_template_without_approved_by` will flag them as live-unsigned.
- **Task 10 Step 3b activation** must, after flipping each template `status->approved` + `approved_by`,
  REMOVE it from KNOWN_LIVE_TEMPLATES (the forcing function is discharged) — exactly as L2_skill_offer /
  L2_general_chat were removed on 2026-06-13 sign-off.

## Absolute Rule 1 — question-discipline as clinical policy in engineer code (DEVIATION)
Question-discipline (Task 8) is a MIND-SAFE clinical policy: a clinical THRESHOLD ("ask one question
at a time") plus a clinical CARVE-OUT (skip on crisis/monitoring, and on skill-execution turns). In
the v7 model, deterministic post-generation transformations belong at Node 8 in the **Rules Service**
as CMS-authored JSON (`cultural_output`), clinician-tunable. We are hardcoding it in engineer-owned
`output_gate.py` instead — ONLY because the `cultural_output` schema is blocklist/allowlist
substring→substitute and cannot count question sentences or trim. That is a defensible POC choice but
a real deviation (a clinical policy moves where clinicians cannot tune the threshold via CMS), so per
Rule 1 it is flagged + approved here, NOT filed as "no sign-off."
- **Clinical awareness on the threshold itself** (one-question rule + crisis/monitoring + skill-step
  carve-out, not just D1 scope) — approver: ____________  date: ____
- **Product-owner Rule-1 approval** (hardcode-for-POC) — approver: ____________  date: 2026-06-14
- **Follow-up (post-POC, HARD CONDITION of this approval — not optional):** **`LOCK-QDISC-22`** —
  extend the Rules Service schema with a `structural_output` rule type (count/trim/limit ops) so
  question-discipline migrates back to CMS-authored, clinician-tunable JSON. Tracked ticket created
  2026-06-14 (session task #22). Until it lands the policy lives in code. Named owner: ____________
  (assign before closing the engagement-advice-posture work — "post-POC required" without a name
  becomes "never").

## Deterministic (no sign-off, recorded for awareness)
- directive_posture detector (Task 2/3): keyword + repair signal, not the classifier.
- Crisis safety: question-discipline is gated on crisis_state in (None,"none") so monitoring/crisis/
  resolved turns are never question-stripped; crisis_response bypasses output_gate entirely
  (graph.py:272). Skill-execution turns (step_instruction set) are also skipped (D1 freeflow-only).

## Anti-generic = eval, NOT a gate (Task 9)
Cannot regex "tailored to what the user said." Coverage = register>=4.0 + specificity_tailoring
rubric dimension + directive scenarios, clinician-scored. Judge-LLM, if used, must be calibrated
against human raters before gating (see [[test-content-guardrails]]).
```

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/governance/2026-06-14-engagement-advice-posture.md
git commit -m "docs: governance record for engagement advice posture + question discipline"
```

---

## Task 1: Add `directive_posture` state field + per-turn reset

**Files:**
- Modify: `src/sage_poc/state.py` (SageState TypedDict, near `code_switching`)
- Modify: `src/sage_poc/server_helpers.py:_build_state` (after `"code_switching": False,`)
- Test: `tests/test_routing.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_routing.py`:

```python
def test_build_state_resets_directive_posture_false():
    """directive_posture is a per-turn deterministic flag — it must reset to False each
    turn so a prior directive turn cannot leak into the next."""
    from sage_poc.server_helpers import _build_state

    class _Req:
        messages = [type("M", (), {"role": "user", "content": "hello"})()]
        session_id = "s1"
        user_id = None
    state = _build_state(_Req())
    assert state["directive_posture"] is False
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_routing.py::test_build_state_resets_directive_posture_false -v`
Expected: FAIL — `KeyError: 'directive_posture'`.

- [ ] **Step 3: Add the field to SageState**

In `src/sage_poc/state.py`, in the `SageState` TypedDict, immediately after the `code_switching: bool` line, add:

```python
    directive_posture: bool   # deterministic flag: user explicitly delegated / is frustrated by questions and wants direct guidance (set in intent_route, NOT the LLM classifier)
```

- [ ] **Step 4: Reset it in `_build_state`**

In `src/sage_poc/server_helpers.py`, in the dict returned by `_build_state`, immediately after the `"code_switching":     False,` line, add:

```python
        "directive_posture":  False,
```

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/test_routing.py::test_build_state_resets_directive_posture_false -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/state.py src/sage_poc/server_helpers.py tests/test_routing.py
git commit -m "feat: add per-turn directive_posture state flag"
```

---

## Task 2: Deterministic delegation + frustration-repair detector

**Files:**
- Create: `src/sage_poc/nodes/directive_detect.py`
- Test: `tests/test_directive_detect.py`

- [ ] **Step 0: Verify the two upstream assumptions (both confirmed 2026-06-14; re-confirm before coding)**

  1. **History element shape = dict.** `output_gate.py:387-389` appends `{"role": ..., "content": ...}` dicts, and `intent_route.build_intent_prompt` already subscripts `m['role']`/`m['content']` — so `.get("role")`/`.get("content")` in the detector is correct. Confirm with: `grep -n 'conversation_history' src/sage_poc/nodes/output_gate.py` (expect dict append at ~:387).
  2. **`message_en` populated before Node 2.** `safety_check_node` (Node 1) runs `message_en = await async_translate_to_english(raw)` and returns it (`safety_check.py:89,207`); Node 1 precedes Node 2 (intent_route). So the detector sees translated English. Confirm with: `grep -n 'message_en' src/sage_poc/nodes/safety_check.py`. NOTE: the phrase list is English; Arabic delegation rides on translation fidelity. Native-Arabic delegation phrases are a deliberate future add (out of scope here) — record in the governance doc, not a blocker.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_directive_detect.py`:

```python
from sage_poc.nodes.directive_detect import detect_directive_request


def _state(message_en, history=None):
    return {"message_en": message_en, "conversation_history": history or []}


def test_explicit_delegation_phrases_detected():
    for phrase in [
        "just tell me what to do",
        "you tell me",
        "you decide",
        "you pick",
        "I want answers, not questions",
        "stop asking me questions",
        "you need to guide me, not ask me",
        "you're the one with the answers",
        "I don't need more questions",
    ]:
        assert detect_directive_request(_state(phrase)) is True, f"missed: {phrase!r}"


def test_frustration_repair_signal_after_a_question():
    """Repair signal: the prior assistant turn asked a question AND the user pushes back
    on being questioned — even with phrasing not in the literal list."""
    history = [
        {"role": "user", "content": "my dad reacted badly"},
        {"role": "assistant", "content": "How does that usually affect you?"},
    ]
    assert detect_directive_request(_state("why do you keep questioning me", history)) is True


def test_repair_signal_requires_prior_question():
    """No prior question → a bare 'why' is not a directive signal."""
    history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "I'm here with you."},
    ]
    assert detect_directive_request(_state("why", history)) is False


def test_genuine_first_question_is_not_directive():
    for phrase in [
        "How do I deal with my father's response like this?",
        "what should I think about here",
        "I feel anxious",
        "can you help me understand why I feel this way",
    ]:
        assert detect_directive_request(_state(phrase)) is False, f"false positive: {phrase!r}"
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_directive_detect.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement the detector**

Create `src/sage_poc/nodes/directive_detect.py`:

```python
"""Deterministic detection of explicit advice-delegation and question-fatigue.

This is intentionally NOT part of the LLM intent classifier (intent_route's
INTENT_SYSTEM), which carries a documented single-point-of-failure warning. The
signal here is keyword-detectable and a conversation-state repair pattern, so it is
computed deterministically and sets the `directive_posture` flag. The composer then
selects a stronger directive L2 variant; output_gate strips any trailing question.

House style mirrors skill_executor.L1_EXIT_PHRASES: module-level phrase list +
substring match on lowercased text.
"""
from sage_poc.state import SageState

# High-precision: explicit handing-over of the decision, OR explicit objection to
# being questioned. Deliberately excludes genuine first questions ("how do I...",
# "what should I think about") which warrant one round of exploration.
_DIRECTIVE_PHRASES = [
    "just tell me what to do",
    "just tell me",
    "you tell me",
    "you decide",
    "you pick",
    "you choose",
    "tell me what to do",
    "give me answers",
    "i want answers",
    "i need answers",
    "answers not questions",
    "answers, not questions",
    "stop asking me questions",
    "stop asking questions",
    "stop asking me",
    "quit asking",
    "no more questions",
    "enough questions",
    "i don't need more questions",
    "i dont need more questions",
    "you need to guide me",
    "guide me, not ask me",
    "guide me not ask me",
    "you're the one with the answers",
    "youre the one with the answers",
    "you are the one with the answers",
    "i thought you were the one with the answers",
]

# Repair-signal pushback markers: short objections to being questioned that only count
# when the PRIOR assistant turn actually asked a question.
_REPAIR_PUSHBACK = [
    "why do you keep asking",
    "what do you keep asking",
    "why do you keep questioning",
    "you keep asking",
    "you keep questioning",
    "more questions",
    "again with the questions",
    "another question",
]


def _last_assistant_asked_question(history: list[dict]) -> bool:
    for msg in reversed(history or []):
        if msg.get("role") == "assistant":
            return msg.get("content", "").rstrip().endswith("?")
    return False


def detect_directive_request(state: SageState) -> bool:
    """True when the user has explicitly delegated the decision to Sage, or is
    objecting to being questioned after Sage asked a question. Deterministic, no LLM."""
    text = (state.get("message_en") or "").lower()
    if not text:
        return False
    if any(phrase in text for phrase in _DIRECTIVE_PHRASES):
        return True
    if _last_assistant_asked_question(state.get("conversation_history") or []):
        if any(marker in text for marker in _REPAIR_PUSHBACK):
            return True
    return False
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_directive_detect.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/nodes/directive_detect.py tests/test_directive_detect.py
git commit -m "feat: deterministic delegation + question-fatigue detector"
```

---

## Task 3: Set `directive_posture` in `intent_route_node` (Node 2)

**Files:**
- Modify: `src/sage_poc/nodes/intent_route.py` (import + set in `result`)
- Test: `tests/test_intent_route_node.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_intent_route_node.py`:

```python
@pytest.mark.asyncio
async def test_intent_route_sets_directive_posture_deterministically():
    """directive_posture is set by the deterministic detector regardless of what the LLM
    classifier returns — it does not depend on primary_intent."""
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.4, "emotional_intensity": 5, "engagement": 4}'
    )
    state = _base_state(message_en="just tell me what to do")

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["directive_posture"] is True


@pytest.mark.asyncio
async def test_intent_route_directive_posture_false_for_normal_message():
    from sage_poc.nodes.intent_route import intent_route_node
    mock_response = (
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.9, "emotional_intensity": 3, "engagement": 8}'
    )
    state = _base_state(message_en="how do I deal with my father's response like this?")
    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)
    assert result["directive_posture"] is False
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_intent_route_node.py -k directive_posture -v`
Expected: FAIL — `KeyError: 'directive_posture'`.

- [ ] **Step 3: Wire the detector in**

In `src/sage_poc/nodes/intent_route.py`, add the import after line 5 (`from sage_poc.resilience import resilient_invoke`):

```python
from sage_poc.nodes.directive_detect import detect_directive_request
```

Then in `intent_route_node`, in the `result` dict (lines 135-142), add the `directive_posture` key after `"path": ...`:

```python
    result = {
        "primary_intent": primary_intent,
        "secondary_intent": data.get("secondary_intent"),
        "intent_confidence": float(data.get("intent_confidence", 0.5)),
        "emotional_intensity": _safe_int(data.get("emotional_intensity"), 5),
        "engagement": _safe_int(data.get("engagement"), 5),
        "path": state["path"] + ["intent_route"],
        "directive_posture": detect_directive_request(state),
    }
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_intent_route_node.py -k directive_posture -v`
Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/nodes/intent_route.py tests/test_intent_route_node.py
git commit -m "feat: set directive_posture in intent_route (deterministic, classifier-independent)"
```

---

## Task 4: Composer selects the `directive` variant when the flag is set

**Files:**
- Modify: `src/sage_poc/prompts/composer.py:683-693`
- Test: `tests/test_prompts_loader.py` (composer-level)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_prompts_loader.py` (this test will fail at the assertion until both this task AND Task 5's template exist; that ordering is fine — implement Task 4 then Task 5, re-run after Task 5):

```python
def test_compose_prompt_uses_directive_variant_when_flag_set(monkeypatch):
    """When directive_posture is True on a general_chat turn, compose_prompt must select
    the L2_general_chat_directive variant."""
    from sage_poc.prompts import composer
    captured = {}
    real = composer._build_l2_intent_block

    def _spy(primary_intent, intensity, secondary_intent=None, variant=None, extra_variables=None):
        captured["variant"] = variant
        return real(primary_intent, intensity, secondary_intent, variant, extra_variables)

    monkeypatch.setattr(composer, "_build_l2_intent_block", _spy)
    state = _make_min_compose_state(primary_intent="general_chat", directive_posture=True)
    composer.compose_prompt(state)
    assert captured["variant"] == "directive"
```

> **Implementer note:** `tests/test_prompts_loader.py` / `test_nodes.py` already build minimal compose states. Reuse the existing factory (search the test files for an existing `compose_prompt(` call and copy its state dict), naming it `_make_min_compose_state` or inlining. Ensure it sets `directive_posture` and `primary_intent`. Do not invent new fixtures.

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_prompts_loader.py -k directive_variant -v`
Expected: FAIL — variant is `None` (composer never passes it).

- [ ] **Step 3: Pass the variant in `compose_prompt`**

In `src/sage_poc/prompts/composer.py`, replace the `else` branch and the `_build_l2_intent_block` call (lines 686-693) with:

```python
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
```

- [ ] **Step 4: Defer running** until Task 5 creates the variant template, then run Step 2's command — Expected: PASS.

- [ ] **Step 5: Commit** (after Task 5 green)

```bash
git add src/sage_poc/prompts/composer.py tests/test_prompts_loader.py
git commit -m "feat: composer selects general_chat directive variant on directive_posture"
```

---

## Task 5: Create the `general_chat_directive` variant; delete the advice draft

**Files:**
- Create: `src/sage_poc/prompts/templates/L2_intents/general_chat_directive.json`
- Delete: `src/sage_poc/prompts/templates/L2_intents/advice_request.json`
- Test: `tests/test_prompts_loader.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_prompts_loader.py`:

```python
def test_general_chat_directive_variant_loads():
    from sage_poc.prompts.loader import get_intent_template
    tmpl = get_intent_template("general_chat", variant="directive")
    assert tmpl is not None, "general_chat_directive variant missing"
    assert tmpl.template_id == "L2_general_chat_directive"
    lowered = tmpl.content.lower()
    assert "specific" in lowered or "concrete" in lowered
    assert "do not end" in lowered and "question" in lowered  # no closing question


def test_advice_request_draft_removed():
    """The discrete advice_request intent approach was superseded; its draft template
    must be gone so it can never be selected by primary_intent."""
    from sage_poc.prompts.loader import get_intent_template
    assert get_intent_template("advice_request") is None
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_prompts_loader.py -k "directive_variant_loads or advice_request_draft_removed" -v`
Expected: both FAIL (variant absent; advice_request still present).

- [ ] **Step 3: Create the variant template**

Create `src/sage_poc/prompts/templates/L2_intents/general_chat_directive.json`:

```json
{
  "template_id": "L2_general_chat_directive",
  "version": "1.0.0",
  "status": "draft-pending-review",
  "authored_by": "sage_clinics",
  "approved_by": null,
  "effective_date": "pending",
  "layer": "L2",
  "role": "user",
  "always_include": true,
  "word_budget": 100,
  "content": "INTENT: The user has handed the decision to you or is frustrated at being asked questions. Emotional intensity: {intensity}/10. {intensity_guidance} Lead now. Give two or three concrete, specific suggestions tied to exactly what this user described, not generic advice that would fit anyone. Do not ask another exploratory question and do not end your reply with a question. If the user is frustrated that you keep asking, acknowledge that in one short clause, then give the suggestions, do not defend the questions. Stay warm and brief.",
  "variables": ["intensity", "intensity_guidance"],
  "intent": "general_chat"
}
```

- [ ] **Step 4: Delete the superseded advice draft**

```bash
git rm src/sage_poc/prompts/templates/L2_intents/advice_request.json
```

- [ ] **Step 5: Run to verify the tests pass**

Run: `uv run pytest tests/test_prompts_loader.py -k "directive_variant_loads or advice_request_draft_removed or directive_variant" -v`
Expected: PASS (including Task 4's `test_compose_prompt_uses_directive_variant_when_flag_set`).

- [ ] **Step 6: Em-dash + content hygiene check** (per [[em-dash-in-rule-content]])

Run: `uv run python -c "import json; c=json.load(open('src/sage_poc/prompts/templates/L2_intents/general_chat_directive.json'))['content']; assert '—' not in c; print('clean')"`
Expected: prints `clean`.

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/prompts/templates/L2_intents/general_chat_directive.json tests/test_prompts_loader.py
git commit -m "feat: add general_chat directive variant; remove superseded advice_request draft"
```

---

## Task 6: Rewrite the L2 `general_chat` base posture (clinical)

This is the highest-leverage lever: it changes the **default** so the loop is fixed even when the directive flag never fires. It absorbs the live Option A exception clause and adds specificity + one-question + resist-over-affirmation.

**Files:**
- Modify: `src/sage_poc/prompts/templates/L2_intents/general_chat.json`
- Test: `tests/test_intent_route_node.py` (the existing Option-A guard at lines 331-364), `tests/test_prompts_loader.py`

> **Budget (per Task 0 Rule-1 deviation, approved):** L2 general_chat `word_budget` becomes **100** (~95w content). The two GLOBAL rules (≤1 question / never stack, resist over-affirmation) live in **L0 only** (Task 7), NOT here — that is what keeps this block at ~95w instead of 170w. This base block carries only the freeflow-specific posture: validate → specific suggestions → floor-return → companion-scope.

- [ ] **Step 1: Write the content guard test (L2-scoped only)**

In `tests/test_prompts_loader.py`, add:

```python
def test_general_chat_base_posture_directives_present():
    from sage_poc.prompts.composer import _build_l2_intent_block
    block = _build_l2_intent_block("general_chat", intensity=5, secondary_intent=None).lower()
    assert "validate before you inform" in block      # validate-first
    assert "specific" in block                         # specific-not-generic
    assert "do not know" in block or "suggest" in block  # floor-return (absorbs Option A)
    assert "wellness companion" in block               # companion-scope
    # NOTE: one-question + resist-over-affirmation are asserted in L0 (test_nodes / loader L0 tests),
    # NOT here — they are global persona rules, deliberately not duplicated per-L2.
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_prompts_loader.py -k general_chat_base_posture -v`
Expected: FAIL (current v1.3.0 content lacks "validate before you inform" / "specific").

- [ ] **Step 3: Rewrite the content (compressed, ~95w)**

In `src/sage_poc/prompts/templates/L2_intents/general_chat.json`, bump `version` to `"1.4.0"`, set `status` to `"draft-pending-review"` and `approved_by` to `null`, set `word_budget` to `100`, and replace `content` with:

```
INTENT: The user is in open conversation. Emotional intensity: {intensity}/10. {intensity_guidance} Be present and warm, and reflect the feeling back before anything else. Validate before you inform. Once the user has given you enough to act on, or if they ask you to suggest something or say they do not know, give two or three specific suggestions tied to what they actually said, not generic advice that would fit anyone, rather than rephrasing the same question. You are a wellness companion. If the user raises a topic that is not about their own wellbeing, engage with it briefly and substantively, then connect it back to them, and after two turns on a side topic bring the focus gently back to the user.
```

- [ ] **Step 3b: Re-point the absorbed Option-A guard test(s)**

Option A (the literal `Exception:` clause) is absorbed into this base posture, so the guard that asserted the literal words `"Exception"` and `"concrete"` no longer matches and must be re-pointed to the new wording (the floor-return *behaviour* is preserved). In `tests/test_intent_route_node.py`, in `test_general_chat_template_contains_exception_clause_for_floor_return` (lines ~331-364), replace the assertions:

```python
    block = _build_l2_intent_block("general_chat", intensity=5, secondary_intent=None)
    # Option A absorbed into the v1.4.0 base posture (2026-06-14): floor-return is now
    # expressed as "say they do not know -> give specific suggestions", not a literal
    # "Exception:" clause. Behaviour preserved; wording changed.
    assert "do not know" in block.lower(), "floor-return trigger missing from base posture"
    assert "specific" in block.lower(), "floor-return must yield specific suggestions, not a re-ask"
    assert "rephrasing the same question" in block.lower(), "must forbid re-asking on floor-return"
```

Also search for a sibling guard `test_exception_clause_present_in_user_prompt_for_floor_return` (per [[advice-request-option-b]]); if present, re-point it the same way (assert the behaviour, not the literal "Exception"/"concrete" tokens). Run `grep -rn "Exception\|concrete" tests/test_intent_route_node.py` first to find every assertion that pins the old wording.

- [ ] **Step 4: Run the content + Option-A guard tests**

Run: `uv run pytest tests/test_prompts_loader.py -k "general_chat_base_posture or all_intents_have_l2" tests/test_intent_route_node.py -k "floor_return" -v`
Expected: PASS.

- [ ] **Step 5: Em-dash hygiene**

Run: `uv run python -c "import json; c=json.load(open('src/sage_poc/prompts/templates/L2_intents/general_chat.json'))['content']; assert '—' not in c; print('clean')"`
Expected: `clean`.

- [ ] **Step 6: Commit** (status stays draft until Task 0 clinical sign-off recorded)

```bash
git add src/sage_poc/prompts/templates/L2_intents/general_chat.json tests/test_prompts_loader.py
git commit -m "feat: rewrite general_chat posture (validate->specific, one question, resist over-affirmation)"
```

---

## Task 7: L0 persona v2.1.0 — one-question rule + resist over-affirmation

Minimal additive edit to the v2.0.0 persona (do NOT rewrite the whole block — it was just clinically signed off). Adds two cross-cutting guarantees so they hold on skill and freeflow turns alike.

**Files:**
- Modify: `src/sage_poc/prompts/templates/L0_persona.json`
- Test: `tests/test_prompts_loader.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_prompts_loader.py`:

```python
def test_l0_persona_has_one_question_and_anti_over_affirmation():
    tmpl = get_template("L0_persona")
    lowered = tmpl.content.lower()
    assert "one question" in lowered and ("never stack" in lowered or "not stack" in lowered)
    assert "over-affirm" in lowered or "uncritical" in lowered
    assert tmpl.version == "2.1.0"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_prompts_loader.py::test_l0_persona_has_one_question_and_anti_over_affirmation -v`
Expected: FAIL.

- [ ] **Step 3: Edit the persona**

In `src/sage_poc/prompts/templates/L0_persona.json`: bump `version` to `"2.1.0"`, set `status` to `"draft-pending-review"` and `approved_by` to `null`, raise `word_budget` `550 → 590` (per Task 0 Rule-1 deviation, approved — L0 is the SOLE home for the two global rules below), and append to the existing `content` (inside the relational/format guidance, NOT the safety block) these two sentences:

```
 Ask at most one question per turn and never stack multiple questions in one reply. Warmth is not constant agreement: when a thought pattern may not be serving the person, reflect it back gently rather than affirming it uncritically, but never do this on a turn where the person is in acute distress.
```

(The acute-distress carve-out implements D3 / the [[engagement-layer-proposal]] gating.)

- [ ] **Step 4: Run the persona tests (full, no regression)**

Run: `uv run pytest tests/test_prompts_loader.py -k "l0_persona" -v`
Expected: the new test PASSES; update `test_load_l0_persona` if it pins `version == "2.0.0"` (change to `"2.1.0"`) and re-run. The em-dash test (`test_l0_persona_has_no_em_dashes`) must stay green — verify no `—` was introduced.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/prompts/templates/L0_persona.json tests/test_prompts_loader.py
git commit -m "feat: L0 persona v2.1.0 — one-question rule + resist over-affirmation (acute-gated)"
```

---

## Task 8: Question-discipline gate in `output_gate` (deterministic)

**Why here and not the rules engine:** the `cultural_output` rule schema (`rules/schemas.py:70-85`) supports only `blocklist`/`allowlist_required` substring matching → substitute. It cannot count question sentences or trim a trailing one. Question-discipline is structural, so it lives as deterministic logic in the Node 8 function, alongside the existing banned-opener handling.

**Files:**
- Modify: `src/sage_poc/nodes/output_gate.py` (helpers + a hook after the banned-opener block, ~line 316, before `violations = _FORMAT_VIOLATIONS.findall(...)` at line 337)
- Test: `tests/test_output_gate_response_paths.py`

- [ ] **Step 0: Verify the carve-out can't silently invert (Flag 2)**

The carve-out runs discipline only when `crisis_state in (None,"none")` and `not step_instruction`. Confirm the NORMAL-turn values so the feature isn't dead in prod while tests stay green:
- `crisis_state`: confirmed `"none"` on every normal turn — `safety_check_node` reads `state.get("crisis_state", "none")` and writes it through (`safety_check.py:189,217`); fresh sessions default to `"none"` (`server_helpers.py:89`). So `"none"` ∈ the run-set. Re-confirm: `grep -n 'crisis_state' src/sage_poc/nodes/safety_check.py`.
- `step_instruction`: absent/None on freeflow turns (set only by skill_executor). Re-confirm it's not initialized truthy in `_build_state`: `grep -n 'step_instruction' src/sage_poc/server_helpers.py` (expect `"step_instruction": None`).

The node-integration test `test_output_gate_collapses_stacked_questions_on_default_freeflow_turn` (Step 5) is the permanent guard: it builds a state with NO crisis/step kwargs and asserts collapse happens — so if a future change makes the normal-turn `crisis_state` something outside `(None,"none")`, this test goes red instead of the feature going silently inert.

- [ ] **Step 1: Write the failing helper tests**

Add to `tests/test_output_gate_response_paths.py`:

```python
def test_limit_to_one_question_collapses_stacked_questions():
    from sage_poc.nodes.output_gate import _limit_to_one_question
    text = ("Where would you place yourself from one to ten? And what could help boost "
            "your confidence a bit more?")
    out = _limit_to_one_question(text)
    assert out.count("?") == 1
    assert "Where would you place yourself" in out


def test_limit_to_one_question_keeps_statements_and_first_question():
    from sage_poc.nodes.output_gate import _limit_to_one_question
    text = "That sounds heavy. What's weighing on you most? Do you feel anxious?"
    out = _limit_to_one_question(text)
    assert out == "That sounds heavy. What's weighing on you most?"


def test_limit_to_one_question_noop_for_single_question():
    from sage_poc.nodes.output_gate import _limit_to_one_question
    text = "That sounds hard. What's been hardest?"
    assert _limit_to_one_question(text) == text


def test_strip_trailing_question_removes_dangling_question():
    from sage_poc.nodes.output_gate import _strip_trailing_question
    text = ("Prepare a few calm, assertive phrases beforehand. You can set a boundary by "
            "naming when you need a break. How does this sit with you?")
    assert _strip_trailing_question(text).endswith("need a break.")


def test_strip_trailing_question_keeps_question_only_response():
    from sage_poc.nodes.output_gate import _strip_trailing_question
    text = "What feels hardest right now?"
    assert _strip_trailing_question(text) == text
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_output_gate_response_paths.py -k "limit_to_one_question or strip_trailing_question" -v`
Expected: FAIL — helpers undefined.

- [ ] **Step 3: Implement the helpers**

In `src/sage_poc/nodes/output_gate.py`, add at module level (near the other regex constants; `re` is already imported at the top of this module — reuse it):

```python
# Question-discipline (Node 8, deterministic). MIND-SAFE: one question at a time, never
# stack. Cannot be a cultural_output rule (that schema is blocklist/allowlist substitute
# only — see rules/schemas.py), so it lives here as structural logic.
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_TRAILING_QUESTION_RE = re.compile(r"(?:\s*[^.!?]*\?)+\s*$")


def _limit_to_one_question(text: str) -> str:
    """Keep at most one question sentence (the first); drop later question sentences.
    Statements are preserved in order. No-op when 0 or 1 question. Never returns empty."""
    if not text or text.count("?") <= 1:
        return text
    out, seen_q = [], False
    for sent in _SENT_SPLIT_RE.split(text.strip()):
        if sent.rstrip().endswith("?"):
            if seen_q:
                continue
            seen_q = True
        out.append(sent)
    result = " ".join(out).strip()
    return result if result else text


def _strip_trailing_question(text: str) -> str:
    """Drop trailing question sentence(s) so an advice turn ends on substance. Returns the
    original unchanged if stripping would empty the turn (whole turn was a question)."""
    if not text or "?" not in text:
        return text
    stripped = _TRAILING_QUESTION_RE.sub("", text).rstrip()
    return stripped if stripped else text
```

- [ ] **Step 4: Run helper tests to verify they pass**

Run: `uv run pytest tests/test_output_gate_response_paths.py -k "limit_to_one_question or strip_trailing_question" -v`
Expected: all PASS.

- [ ] **Step 5: Write the node-integration tests**

Add to `tests/test_output_gate_response_paths.py` (reuse this file's existing gate-state construction — set `session_id=None`/`user_id=None` to skip DB writes, exactly as the file's passing tests do):

```python
import pytest


@pytest.mark.asyncio
async def test_output_gate_collapses_stacked_questions_on_default_freeflow_turn():
    """Flag-2 permanent guard: a DEFAULT freeflow turn (no crisis_state / step_instruction
    kwargs) MUST collapse stacked questions. If the normal-turn carve-out values ever drift
    so discipline goes inert, this test goes red instead of the feature dying silently."""
    from sage_poc.nodes import output_gate as og
    state = _make_gate_state(
        primary_intent="general_chat",
        directive_posture=False,
        response_en="That's a lot. What's heaviest? And what would help right now?",
    )
    result = await og.output_gate_node(state)
    assert result["response_en"].count("?") == 1


@pytest.mark.asyncio
async def test_question_discipline_skips_skill_execution_turn():
    """D1 freeflow-only: a skill-execution turn (step_instruction set) must NOT be
    disciplined — a clinician-authored L3 step may legitimately phrase its own question."""
    from sage_poc.nodes import output_gate as og
    state = _make_gate_state(
        primary_intent="skill_continuation",
        directive_posture=False,
        step_instruction="Ask the user to recall the situation. What happened? How did you feel?",
        response_en="Let's look at that. What happened? How did you feel?",
    )
    result = await og.output_gate_node(state)
    assert result["response_en"].count("?") == 2, (
        "discipline ran on a skill-execution turn — step_instruction guard missing"
    )


@pytest.mark.asyncio
async def test_output_gate_strips_trailing_question_on_directive_turn():
    from sage_poc.nodes import output_gate as og
    state = _make_gate_state(
        primary_intent="general_chat",
        directive_posture=True,
        response_en="Prepare a few calm, assertive phrases beforehand. How does this sit with you?",
    )
    result = await og.output_gate_node(state)
    assert "?" not in result["response_en"]
    assert "Prepare a few calm, assertive phrases beforehand." in result["response_en"]


@pytest.mark.asyncio
async def test_question_discipline_skips_monitoring_turn_preserving_safety_question():
    """SAFETY (issue #2): on a post-crisis monitoring turn, stacked questions must NOT be
    collapsed — a safety question appearing as the 2nd question must survive."""
    from sage_poc.nodes import output_gate as og
    state = _make_gate_state(
        primary_intent="general_chat",
        directive_posture=False,
        crisis_state="monitoring",
        response_en="I hear how much pain you're in. Are you safe right now?",
    )
    # craft a stacked-question monitoring response so the carve-out is actually exercised
    state["response_en"] = "I hear how much pain you're in. What's happening? Are you safe right now?"
    result = await og.output_gate_node(state)
    assert "Are you safe right now?" in result["response_en"], (
        "safety question was stripped on a monitoring turn — crisis_state carve-out missing"
    )


def test_crisis_response_bypasses_output_gate_edge():
    """SAFETY (issue #2): crisis_response routes straight to END, never through output_gate,
    so question-discipline can never touch a crisis response. Pin the graph edge."""
    import sage_poc.graph as g
    import inspect
    src = inspect.getsource(g.build_graph)
    assert 'add_edge("crisis_response", END)' in src, (
        "crisis_response must edge directly to END (bypassing output_gate)"
    )
```

- [ ] **Step 6: Run to verify they fail**

Run: `uv run pytest tests/test_output_gate_response_paths.py -k "collapses_stacked or strips_trailing_question_on_directive or skips_monitoring or skips_skill_execution" -v`
Expected: `collapses_stacked...` and `strips_trailing_question_on_directive` FAIL (gate doesn't call helpers yet); `skips_monitoring` FAILS too (without the crisis_state guard, the monitoring turn would be stripped). `skips_skill_execution` PASSES already (no discipline runs yet, so the 2 questions survive — it will still pass after the guard, for the right reason). `test_crisis_response_bypasses_output_gate_edge` already PASSES (graph unchanged).

- [ ] **Step 7: Wire the helpers into the node**

In `src/sage_poc/nodes/output_gate.py`, immediately after the banned-opener enforcement block (after line 316, before the offer-voiding block at line 318), insert:

```python
    # Question discipline (deterministic). Global: collapse stacked questions to one
    # (MIND-SAFE: one question at a time). Directive turns additionally end on substance,
    # not a question. Runs on English text before translation (line ~341) so the Arabic
    # render inherits the cleaned text.
    # SAFETY CARVE-OUT (issue #2): NEVER run on a crisis/monitoring turn. crisis_response
    # bypasses output_gate entirely (graph.py:272), but post-crisis MONITORING turns DO
    # transit here and can legitimately carry a safety question ("Are you safe right now?")
    # as the 2nd question — _limit_to_one_question would strip it. Safety questions must be
    # deterministic, so gate on crisis_state. Also skip boundary-violation gate paths.
    # D1 (freeflow-only): skip skill-execution turns (step_instruction set) so a clinician-
    # authored L3 step's own question is never overridden — clinician autonomy over L3 content.
    if (
        gate_path not in ("scope_refusal", "jailbreak")
        and state.get("crisis_state") in (None, "none")
        and not state.get("step_instruction")
        and response_en
    ):
        _disciplined = _limit_to_one_question(response_en)
        if state.get("directive_posture"):
            _disciplined = _strip_trailing_question(_disciplined)
        if _disciplined != response_en:
            response_en = _disciplined
            path = path + ["question_discipline_applied"]
```

> **D1 override (global scope):** remove the `and not state.get("step_instruction")` line to collapse stacking inside skills too (needs clinician approval — it would override L3 step wording).

- [ ] **Step 8: Run node tests to verify they pass**

Run: `uv run pytest tests/test_output_gate_response_paths.py -k "collapses_stacked or strips_trailing_question_on_directive or skips_monitoring or skips_skill_execution or bypasses_output_gate" -v`
Expected: all PASS — including the default-freeflow collapse guard, the monitoring + skill-step carve-outs, and the crisis-bypass edge pin.

- [ ] **Step 9: Full output_gate regression**

Run: `uv run pytest tests/test_output_gate_response_paths.py tests/test_output_gate_banned_opener.py tests/test_output_gate_loop_mechanics.py tests/test_output_gate_offer_voiding.py -v`
Expected: all PASS.

- [ ] **Step 10: Commit**

```bash
git add src/sage_poc/nodes/output_gate.py tests/test_output_gate_response_paths.py
git commit -m "feat: question-discipline gate (collapse stacked Qs; strip trailing Q on directive)"
```

---

## Task 9: Anti-generic eval coverage (NOT a gate)

Per the caveat: specificity cannot be regex-enforced. Coverage = two new clinician-scored rubric dimensions + directive scenarios + a register ≥4.0 KPI line.

**Files:**
- Modify: `tests/experiment_4_4/generate_quality_log.py` (`_blank_rubric` lines 64-73; `kpi_targets` lines 239-244)
- Modify: `tests/experiment_4_4/scenarios.py` (add directive scenarios)

- [ ] **Step 1: Add rubric dimensions**

In `tests/experiment_4_4/generate_quality_log.py`, replace `_blank_rubric` (lines 64-73) with:

```python
def _blank_rubric() -> dict:
    """Clinician scoring rubric — all fields null until manually filled."""
    return {
        "tone_appropriate":       None,   # 1-5: emotionally attuned tone
        "matches_instruction":    None,   # 1-5: response follows step_instruction
        "validation_genuine":     None,   # 1-5: validation feels authentic, not scripted
        "socratic_quality":       None,   # 1-5: open questions invite reflection
        "register_score":         None,   # 1-5: warmth/register; gate target >= 4.0
        "specificity_tailoring":  None,   # 1-5: advice is specific to THIS user, not generic
        "overall":                None,   # 1-5: holistic quality rating
        "reviewer_notes":         None,
    }
```

- [ ] **Step 2: Add the KPI line**

In the same file, update `kpi_targets` (lines 239-244) to add:

```python
    "kpi_targets": {
        "completion_rate": "≥80% (≥6/7 happy-path scenarios)",
        "quality_score":   "≥4.0/5.0 clinician-scored",
        "register_score":  "≥4.0/5.0 clinician-scored (anti-generic / warmth)",
        "specificity":     "≥4.0/5.0 clinician-scored (advice tailored, not boilerplate)",
        "rule_accuracy":   "binary per rule (see test_rule_accuracy.py)",
        "turn_latency":    "<3s p95 (see test_latency.py)",
    },
```

- [ ] **Step 3: Add directive scenarios**

In `tests/experiment_4_4/scenarios.py`, add two scenarios to the scenario list (match the existing dict shape — `id`, `description`, and the multi-turn override keys the harness uses; copy the nearest existing freeflow scenario and adapt the messages):

```python
    {
        "id": "directive_father_conflict",
        "description": "User asks how to handle a parent's reaction, then explicitly "
                       "delegates and pushes back on being questioned (advice-loop regression).",
        "skill_id": None,
        "initial_step": None,
        "_turns": [
            "How do I deal with my father's response like this?",
            "It makes me feel powerless. You need to guide me, not ask me.",
            "What do you keep asking me? I thought you were the one with the answers.",
            "I want answers, not questions.",
        ],
    },
    {
        "id": "directive_decision_help",
        "description": "User asks for a concrete decision recommendation (delegation).",
        "skill_id": None,
        "initial_step": None,
        "_turns": [
            "I can't decide whether to take the new job. Just tell me what to do.",
        ],
    },
```

> **Implementer note:** if `scenarios.py` uses a different multi-turn key than `_turns` (e.g. `_turn_overrides`/`_recurring_message` referenced in `generate_quality_log.py`), match that file's actual convention — read it first and mirror the closest existing freeflow scenario exactly.

- [ ] **Step 4: Generate the quality log (smoke run)**

Run: `uv run python tests/experiment_4_4/generate_quality_log.py` (or the documented invocation in that file's header)
Expected: produces the log with the new rubric fields present (null) and the directive scenarios included. This is the artifact clinicians score — there is no automated pass/fail here by design.

- [ ] **Step 5: Commit**

```bash
git add tests/experiment_4_4/generate_quality_log.py tests/experiment_4_4/scenarios.py
git commit -m "test: add register + specificity rubric dims and directive scenarios (anti-generic eval)"
```

---

## Task 10: Full regression, production harness, deploy

**Files:**
- Modify: `scripts/functional_multiturn_prod.py`

- [ ] **Step 1: Unit gate (fast suite)**

Run: `uv run pytest -m "not slow" -q`
Expected: all PASS. Record the count vs the pre-change baseline so none were dropped.

- [ ] **Step 2: Slow guard tests (no classification regression)**

Run: `uv run pytest tests/test_nodes.py -k "bare_emotional_words" -m slow -v`
Expected: PASS. (We did NOT touch INTENT_SYSTEM, so this should be unaffected — confirm.)

- [ ] **Step 3: Add the advice-loop scenario to the prod harness**

In `scripts/functional_multiturn_prod.py`, add to `SCENARIOS`:

```python
    {
        "name": "D. Advice-loop + question discipline (posture regression)",
        "turns": [
            "How do I deal with my father's response like this?",
            "It makes me feel powerless. You need to guide me, not ask me.",
            "What do you keep asking me? I thought you were the one with the answers.",
            "I want answers, not questions.",
        ],
    },
```

- [ ] **Step 3b: SIGN-OFF GATE + activation (issue #3 — do NOT skip)**

Before any deploy, confirm ALL FOUR clinical sign-off boxes in `docs/superpowers/governance/2026-06-14-engagement-advice-posture.md` are checked with name + date. If any is unchecked, STOP — either obtain the sign-off, or get the user's explicit written POC-provisional acceptance recorded in the governance doc's deploy-gate line. Do not flip status or deploy on unchecked boxes.

Once confirmed, activate the three clinician-authored templates (flip draft → approved):
- `general_chat.json` (v1.4.0), `general_chat_directive.json` (v1.0.0), `L0_persona.json` (v2.1.0): set `"status": "approved"`, `"approved_by": "clinical_lead"`, `"effective_date": "2026-06-14"`.

Verify nothing ships as draft:

```bash
uv run python -c "import json,glob,sys; bad=[f for f in ['src/sage_poc/prompts/templates/L2_intents/general_chat.json','src/sage_poc/prompts/templates/L2_intents/general_chat_directive.json','src/sage_poc/prompts/templates/L0_persona.json'] if json.load(open(f)).get('status')!='approved']; print('UNAPPROVED:',bad) or sys.exit(1 if bad else 0)"
```
Expected: exits 0 (no unapproved templates). Then commit the activation:

```bash
git add src/sage_poc/prompts/templates/L2_intents/general_chat.json src/sage_poc/prompts/templates/L2_intents/general_chat_directive.json src/sage_poc/prompts/templates/L0_persona.json docs/superpowers/governance/2026-06-14-engagement-advice-posture.md
git commit -m "feat: activate engagement posture templates after clinical sign-off"
```

- [ ] **Step 4: Deploy (manual Railway — prompts/code are baked into the image)**

ONLY after Step 3b's gate passes. Per [[engagement-layer-proposal]] deploy notes:

```bash
railway up --service sage-api
```

Verify: `curl -s -o /dev/null -w "%{http_code}" https://sage-api-production-3328.up.railway.app/health/schema-conformance` → `200`.

- [ ] **Step 5: Run the harness against production**

Run: `python scripts/functional_multiturn_prod.py`
Expected (post-deploy): by turn 2 the reply gives specific suggestions and does NOT end on a question; no turn stacks two questions; the turn-3 complaint is not met with another question. Capture the transcript for the governance record. This is the direct before/after for the reported failure.

- [ ] **Step 6: Commit**

```bash
git add scripts/functional_multiturn_prod.py
git commit -m "test: add advice-loop scenario to prod functional harness"
```

---

## Self-Review

**1. Spec coverage (against the brief + the three transcript failures).**
- Question loop (advance to advice) → Task 6 base posture + Task 5/4/3/2 directive backstop. ✓
- Stacked questions (MIND-SAFE) → Task 8 `_limit_to_one_question` (freeflow-only, D1) + Task 7 (L0 one-question rule). ✓
- Generic advice (#1 frustration) → Task 6/5 "specific to what they said" + Task 9 eval (register + specificity). ✓ (not gateable — Task 9 is eval, per caveat.)
- Over-affirmation (distinct top frustration, Refinement 1) → Task 7 (L0 "resist over-affirmation / gentle challenge," acute-gated). NOTE: the global rules live in L0 ONLY; Task 6 (L2 general_chat) carries validate→specific→floor-return→companion-scope, not these. ✓
- Reactive→default: highest-leverage change is the base posture (Task 6), not a flag. ✓
- Backstop deterministic, not classifier (Refinement 2) → Task 2/3 flag, zero INTENT_SYSTEM change. ✓
- Trailing question on advice turn → Task 8 `_strip_trailing_question` (directive). ✓
- No Rule 1 (no control-layer change); clinical sign-off for L0/L2 → Task 0. ✓

**2. Placeholder scan.** Every code step shows the code; every test step shows assertions and the exact command + expected result. The two "implementer note" reuse-existing-fixture pointers (Task 4 Step 1, Task 8 Step 5, Task 9 Step 3) are explicit instructions to mirror existing patterns, not placeholders. ✓

**3. Type consistency.** `directive_posture` (bool) defined Task 1, set Task 3, read Task 4 + Task 8 — same name throughout. `detect_directive_request(state)->bool` defined Task 2, imported/called Task 3 with matching signature. `_limit_to_one_question`/`_strip_trailing_question` defined Task 8 Step 3, used Steps 1/5/7. `variant="directive"` string matches the `general_chat_directive.json` → `L2_general_chat_directive` id (loader builds `L2_{intent}_{variant}`). ✓

**Honest limitations surfaced (not gaps):**
- Anti-generic (Task 9) is clinician-scored, not automatically enforced — by design (you can't regex tailoring). If a Judge-LLM is later used to automate it, it must be calibrated vs human raters before gating ([[test-content-guardrails]]).
- `_limit_to_one_question` is a deterministic mutation; by D1 (default freeflow-only) it skips skill-execution turns so clinician-authored L3 step questions are untouched. D1 override switches it to global.
- `_strip_trailing_question` only removes *trailing* questions, so a non-trailing question mid-reply can survive on a directive turn. Acceptable: the prompt (directive variant: "do not ask another exploratory question") is the primary lever; the gate is the trailing-question backstop, not a full question remover.
- Question-discipline is conservatively OFF for crisis/monitoring/active/**resolved** sessions (crisis_state not in (None,"none")) — a post-crisis-resolved session won't get stacked-question collapsing for the rest of that session. Harmless (no safety impact), accepted for POC; matches the graph.py:246 non-crisis convention.
- Question-discipline is a clinical policy in engineer code (Rule-1 deviation, Task 0): clinicians cannot tune the "one question" threshold via CMS until the `structural_output` schema-extension follow-up lands post-POC.
- The directive detector is high-precision by choice; some genuine delegations phrased unusually will fall through to the base posture (Task 6) — which already validates-then-advises, so the failure mode degrades gracefully, not back into the loop.
- The detector reads translated English `message_en`; native-Arabic/Arabizi delegation phrases are not in the list yet (recorded in the governance doc as a future add). Arabic delegation rides on translation fidelity until then.
