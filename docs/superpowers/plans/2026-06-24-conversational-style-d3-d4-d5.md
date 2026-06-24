# Conversational Style (D4 / D3 / D5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Sage answer-first when the user wants info/a decision (D4), drop the scripted-menu feel (D3), and validate feelings without co-signing distorted beliefs (D5) — reliably, via deterministic gates, reconciled to the production architecture.

**Architecture:** Spec: `docs/superpowers/specs/2026-06-24-conversational-style-d3-d4-d5-design.md` (FINAL, source-verified). Gate *mechanics* stay Python node logic (decided carve-out, ticket #22 LOCK-QDISC-22); new clinical *values* go to data (`skill_matching` JSON, config). All gates run on the English `response_en`/`message_en` before translation (covers EN + translate-out AR; R1 makes them language-aware for Arabic `؟` and closes the already-Arabic gap).

**Tech Stack:** Python 3, pytest (`asyncio_mode = "auto"`), LangGraph. Run tests: `./.venv/bin/python -m pytest`.

## Global Constraints
- **Branch:** `feat/2026-06-24-conversational-style` off `master` (the spec already lives here). `sage-poc` pushes as-is.
- **Verified base:** production `origin/master` 266183a.
- **No em dashes** in any user-facing string or rule content (commas). Crisis number from `config.CRISIS_LINE_UAE`.
- **Mechanic-vs-value rule (§17/§18):** counting/trimming/regex stays Python; tunable clinical values (offer-cooldown N, `ACUITY_FLOOR`) go to data (`skill_matching` rule / config). Do not add new clinical values as Python literals.
- **Governance preconditions for the D4 Python-gate extension (Task 3) to MERGE (not to write):** product-owner Rule-1 signature on the (extended) question-discipline-in-code deviation; #22 LOCK-QDISC-22 owner assigned; clinician owns + signs the banned-opener pattern set. (Task 0.)
- **D5 high-intensity edit (Task 5) is gated behind a STANDALONE clinical sign-off** — build behind a flag/default-off; do not flip live until signed. `ACUITY_FLOOR` default `emotional_intensity > 7` (executor `validate_only` floor, v7 §9.2 rule 1) unless clinical sets otherwise.
- **Commit trailer:** every commit ends with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **One commit per task.** Run the touched test files before each commit; full suite has a known `test_server` flake (ignore that one).

## File Structure
| File | Responsibility | Task |
|---|---|---|
| `src/sage_poc/nodes/output_gate.py` | R1 language-aware `؟` in question-discipline; Bug A vetted fallback; G1 directive⊥offer guard | 1,2,3 |
| `src/sage_poc/nodes/directive_detect.py` | D4 trigger extension (+ `primary_intent` param) | 3 |
| `src/sage_poc/nodes/intent_route.py` | pass freshly-parsed `primary_intent` into `detect_directive_request` | 3 |
| `src/sage_poc/state.py` | `last_offer_turn` field (D3 cooldown) | 4 |
| `src/sage_poc/nodes/skill_select.py` | offer-cooldown mechanic (suppress fresh offer within N turns) | 4 |
| `src/sage_poc/rules/data/skill_matching/skill_matching_rules.json` | cooldown N value (data) | 4 |
| `src/sage_poc/prompts/templates/L2_intents/skill_offer.json` | drop "which would you prefer" close | 4 |
| `src/sage_poc/prompts/composer.py` | D5 deterministic acuity gate in `_INTENSITY_GUIDANCE["high"]` (flagged) | 5 |
| `src/sage_poc/config.py` | `SKILL_OFFER_COOLDOWN_TURNS` fallback, `D5_ACUITY_FLOOR`, `D5_ACUITY_GATE_ENABLED` | 4,5 |

---

### Task 0: Governance preconditions (no code — gate)
**Deliverable:** a filled governance record, not code. This task does not merge code; it unblocks Task 3's merge.

- [ ] **Step 1:** Obtain the **product-owner Rule-1 signature** on the question-discipline / directive-detect / banned-opener "clinical-policy-in-engineer-code" deviation, now *extended* by D4. Record in `docs/superpowers/governance/2026-06-14-engagement-advice-posture.md` (the blank Rule-1 lines) or a new dated governance note referencing this plan.
- [ ] **Step 2:** Assign the **#22 LOCK-QDISC-22 owner** (the blank "Named owner:" at `docs/superpowers/plans/2026-06-14-engagement-advice-posture.md:128`).
- [ ] **Step 3:** Have a **clinician review + sign the banned-opener pattern set** (`output_gate.py` `_BANNED_OPENER_PATTERNS`) as therapeutic content, even though it stays in code under #22.
- [ ] **Step 4:** File the three §17 divergences as tickets (diverging doc trees; arch doc stale on L0 version/budget; owed v8 §17 entry).

> Tasks 1, 2, 4 have **no** governance precondition and can proceed immediately. Task 3 (the Python-gate *extension*) merges only after Steps 1–3.

---

### Task 1: R1 — language-aware question discipline (Arabic `؟`)
Closes the verified latent gap: `_limit_to_one_question`/`_strip_trailing_question` count only ASCII `?`, so they no-op on already-Arabic `response_en` and will break under native-Arabic generation.

**Files:**
- Modify: `src/sage_poc/nodes/output_gate.py` (`_SENT_SPLIT_RE` ~:91, `_TRAILING_QUESTION_RE` ~:92, `_limit_to_one_question` :99, `_strip_trailing_question` :115)
- Test: `tests/test_output_gate_question_discipline_arabic.py` (new)

**Interfaces:**
- Produces: `_limit_to_one_question`/`_strip_trailing_question` treat `؟` (U+061F) as a question terminator, in addition to `?`.

- [ ] **Step 1: Write the failing test**
```python
import pytest
from sage_poc.nodes.output_gate import _limit_to_one_question, _strip_trailing_question

def test_arabic_question_mark_collapsed():
    # two Arabic questions -> keep only the first
    t = "كيف تشعر اليوم؟ هل نمت جيدا؟"
    out = _limit_to_one_question(t)
    assert out.count("؟") == 1
    assert "كيف تشعر اليوم؟" in out

def test_strip_trailing_arabic_question():
    t = "خذ نفسا عميقا الان. هل تريد المتابعة؟"
    out = _strip_trailing_question(t)
    assert "؟" not in out
    assert "خذ نفسا عميقا الان." in out
```
- [ ] **Step 2: Run — expect FAIL** (ASCII-only counting leaves both `؟`).
Run: `./.venv/bin/python -m pytest tests/test_output_gate_question_discipline_arabic.py -v`
- [ ] **Step 3: Implement** in `output_gate.py`:
  - `_SENT_SPLIT_RE = re.compile(r"(?<=[.!?؟])\s+")`
  - `_TRAILING_QUESTION_RE = re.compile(r"(?:\s*[^.!?؟]*[?؟])+\s*$")`
  - In `_limit_to_one_question`: change `if not text or text.count("?") <= 1:` to `if not text or (text.count("?") + text.count("؟")) <= 1:` and the sentence test `if sent.rstrip().endswith("?"):` to `if sent.rstrip().endswith(("?", "؟")):`
  - In `_strip_trailing_question`: change `if not text or "?" not in text:` to `if not text or ("?" not in text and "؟" not in text):`
- [ ] **Step 4: Run — expect PASS**, then run `tests/test_output_gate_response_paths.py` to confirm no EN regression.
- [ ] **Step 5: Commit**
```bash
git add src/sage_poc/nodes/output_gate.py tests/test_output_gate_question_discipline_arabic.py
git commit -m "fix(output_gate): language-aware question discipline (Arabic ؟) [R1]"
```

---

### Task 2: Bug A — vetted fallback must not be gutted under directive_posture
**Files:** Modify `src/sage_poc/nodes/output_gate.py:176`; Test: `tests/test_output_gate_empty_failsafe.py` (extend).

**Interfaces:** Produces: `_VETTED_FALLBACK_RESPONSE` is a non-question statement, so `_strip_trailing_question` cannot reduce it to a fragment.

- [ ] **Step 1: Failing test** (add to existing file):
```python
@pytest.mark.asyncio
async def test_vetted_fallback_survives_directive_posture():
    from sage_poc.nodes.output_gate import _VETTED_FALLBACK_RESPONSE, _strip_trailing_question
    # the fallback must not collapse to a fragment when trailing-question stripping runs
    assert _strip_trailing_question(_VETTED_FALLBACK_RESPONSE) == _VETTED_FALLBACK_RESPONSE
    assert len(_VETTED_FALLBACK_RESPONSE.split()) >= 6
```
- [ ] **Step 2: Run — expect FAIL** (current fallback ends in a question → stripped).
- [ ] **Step 3: Implement** — replace `output_gate.py:176`:
```python
_VETTED_FALLBACK_RESPONSE = "I'm here with you, and what you've shared matters. Take a moment, I'm listening whenever you're ready."
```
(non-question, warm, no em dash, not a banned opener). NOTE: this string is pending its own fallback-review checklist; keep it a statement.
- [ ] **Step 4: Run — expect PASS**; run `tests/test_output_gate_empty_failsafe.py tests/test_output_gate_banned_opener.py`.
- [ ] **Step 5: Commit**
```bash
git add src/sage_poc/nodes/output_gate.py tests/test_output_gate_empty_failsafe.py
git commit -m "fix(output_gate): make vetted fallback a statement so directive-posture stripping can't gut it [Bug A]"
```

---

### Task 3: D4 — reflect-vs-answer mode switch (extend directive_detect) + G1 guard
**Governance:** merges only after Task 0 Steps 1–3.

**Files:**
- Modify: `src/sage_poc/nodes/directive_detect.py` (`detect_directive_request` signature + triggers)
- Modify: `src/sage_poc/nodes/intent_route.py:148` (pass freshly-parsed intent)
- Modify: `src/sage_poc/nodes/output_gate.py` (G1: add `not _offer_ids`-equivalent to `_strip_trailing_question` condition)
- Test: `tests/test_directive_detect.py` (extend or new)

**Interfaces:**
- Produces: `detect_directive_request(state: dict, primary_intent: str | None = None) -> bool` — returns True on existing triggers OR `primary_intent == "info_request"` OR the user message is itself a question. Default param keeps existing callers working.

- [ ] **Step 1: Failing tests**
```python
from sage_poc.nodes.directive_detect import detect_directive_request

def test_info_request_intent_triggers_directive():
    st = {"message_en": "what time is it", "conversation_history": []}
    assert detect_directive_request(st, primary_intent="info_request") is True

def test_user_question_triggers_directive():
    st = {"message_en": "can you give me a list of sleep tips?", "conversation_history": []}
    assert detect_directive_request(st) is True

def test_plain_emotional_disclosure_does_not_trigger():
    st = {"message_en": "i feel so overwhelmed and exhausted lately", "conversation_history": []}
    assert detect_directive_request(st, primary_intent="new_skill") is False
```
- [ ] **Step 2: Run — expect FAIL** (no `primary_intent` param; question not detected).
- [ ] **Step 3: Implement**
  - In `directive_detect.py`, change the signature to `def detect_directive_request(state, primary_intent=None):` and near the top of the body, after computing `text = (state.get("message_en") or "").lower()`, add:
    ```python
    if primary_intent == "info_request":
        return True
    # message is itself a direct question (info/decision signal), not an emotional disclosure
    if text.rstrip().endswith(("?", "؟")):
        return True
    ```
  - Keep the existing `_DIRECTIVE_PHRASES` / `_REPAIR_PUSHBACK` logic below.
  - In `intent_route.py:148`, change `"directive_posture": detect_directive_request(state),` to pass the just-parsed intent, e.g. `"directive_posture": detect_directive_request(state, primary_intent=data.get("primary_intent")),` (use the freshly-parsed classifier result `data`, NOT `state["primary_intent"]` which is the prior turn).
- [ ] **Step 4: G1 guard** — in `output_gate.py` question-discipline block (`:461`), make directive stripping moot when an offer is live. Change:
  ```python
  if state.get("directive_posture"):
      _disciplined = _strip_trailing_question(_disciplined)
  ```
  to:
  ```python
  if state.get("directive_posture") and not (state.get("offered_skill_ids")):
      _disciplined = _strip_trailing_question(_disciplined)
  ```
  Add a test in `tests/test_output_gate_response_paths.py`: directive_posture + offered_skill_ids set → the offer's closing question is preserved.
- [ ] **Step 5: Run — expect PASS**; run `tests/test_directive_detect.py tests/test_output_gate_response_paths.py tests/test_freeflow_respond.py -q`.
- [ ] **Step 6: Commit**
```bash
git add src/sage_poc/nodes/directive_detect.py src/sage_poc/nodes/intent_route.py src/sage_poc/nodes/output_gate.py tests/test_directive_detect.py
git commit -m "feat(routing): extend directive-posture to info_request + question + curt-reply; G1 directive-offer guard [D4]"
```

---

### Task 4: D3 — offer cooldown (value in data) + drop the menu close
**Files:**
- Modify: `src/sage_poc/config.py` (`SKILL_OFFER_COOLDOWN_TURNS = int(os.getenv("SAGE_SKILL_OFFER_COOLDOWN_TURNS", "2"))` as the fallback when the rule omits it)
- Modify: `src/sage_poc/rules/data/skill_matching/skill_matching_rules.json` (`default_offer` action gains `"cooldown_turns": 2`)
- Modify: `src/sage_poc/state.py` (add `last_offer_turn: int | None`)
- Modify: `src/sage_poc/nodes/skill_select.py` (set `last_offer_turn` when an offer is made; suppress a fresh offer when `turn_count - last_offer_turn < cooldown_turns`)
- Modify: `src/sage_poc/prompts/templates/L2_intents/skill_offer.json` (remove the "Ask which they would prefer" closing sentence)
- Test: `tests/test_skill_select_offer_cooldown.py` (new)

**Interfaces:**
- Consumes: `state["turn_count"]`, `state["last_offer_turn"]`.
- Produces: a fresh offer is suppressed (routes to freeflow, marker `offer_cooldown_suppressed`) within `cooldown_turns` of the last offer.

- [ ] **Step 1: Failing test**
```python
import pytest
from unittest.mock import patch
from sage_poc.nodes import skill_select as ss

@pytest.mark.asyncio
async def test_offer_suppressed_within_cooldown():
    state = {"primary_intent":"new_skill","crisis_state":"none","clinical_flags":[],
             "offered_skill_ids":None,"message_en":"i keep overthinking","raw_message":"i keep overthinking",
             "detected_language":"en","path":["safety_check","intent_route"],"declined_skills":[],
             "therapeutic_profile":{}, "emotional_intensity":5,
             "turn_count":6, "last_offer_turn":5}  # 1 turn since last offer, cooldown=2
    with patch.object(ss,"_semantic_match_with_runner_up",return_value=("worry_time",0.62,None)):
        result = await ss.skill_select_node(state)
    assert result["active_skill_id"] is None
    assert not result.get("offered_skill_ids")
    assert "offer_cooldown_suppressed" in result["path"]
```
- [ ] **Step 2: Run — expect FAIL** (no cooldown logic).
- [ ] **Step 3: Implement** — in `skill_select_node`, before building any offer (after intent/auto-select guards, before the semantic offer path), add:
  ```python
  _cooldown = _offer_cooldown_turns()  # reads skill_matching rule, falls back to config
  _last = state.get("last_offer_turn")
  if _last is not None and (state.get("turn_count", 0) - _last) < _cooldown:
      return {**stale_offer_clear, "active_skill_id": None, "active_step_id": None,
              "skill_match_method": None, "semantic_score": None,
              "path": state["path"] + ["skill_select", "offer_cooldown_suppressed"]}
  ```
  Add `_offer_cooldown_turns()` reading the `default_offer` rule's `cooldown_turns` (fallback `config.SKILL_OFFER_COOLDOWN_TURNS`). When an offer is made (the `skill_offer_made` return), add `"last_offer_turn": state.get("turn_count", 0)` to the returned dict. Add `last_offer_turn` to `state.py` SageState.
- [ ] **Step 4: skill_offer.json** — remove the trailing "Ask which they would prefer, as one short question." sentence from the template content (keep the offer presentation; this is clinical copy → bump template version + leave `approved_by` as-is pending sign-off, consistent with its `draft-pending-review` status).
- [ ] **Step 5: Run — expect PASS**; run `tests/test_skill_select.py tests/test_skill_select_offer_cooldown.py -q`.
- [ ] **Step 6: Commit**
```bash
git add src/sage_poc/config.py src/sage_poc/rules/data/skill_matching/skill_matching_rules.json src/sage_poc/state.py src/sage_poc/nodes/skill_select.py src/sage_poc/prompts/templates/L2_intents/skill_offer.json tests/test_skill_select_offer_cooldown.py
git commit -m "feat(routing): offer cooldown (N in skill_matching rule) + drop menu close [D3]"
```

---

### Task 5: D5 — deterministic acuity gate (GATED on standalone clinical sign-off)
**Build behind a default-off flag; DO NOT flip live until the standalone clinical sign-off + EN/AR high-intensity regression pass.**

**Files:**
- Modify: `src/sage_poc/config.py` (`D5_ACUITY_FLOOR = int(os.getenv("SAGE_D5_ACUITY_FLOOR", "8"))` — i.e. `emotional_intensity > 7`; `D5_ACUITY_GATE_ENABLED = os.getenv("SAGE_D5_ACUITY_GATE", "false").lower() == "true"`)
- Modify: `src/sage_poc/prompts/composer.py` (`_INTENSITY_GUIDANCE["high"]` / `_intensity_guidance`)
- Test: `tests/test_d5_acuity_gate.py` (new) + the EN/AR high-intensity regression

**Interfaces:**
- Produces: when `D5_ACUITY_GATE_ENABLED` and `emotional_intensity >= D5_ACUITY_FLOOR`, the high-intensity guidance instructs: validate via specific naming, **do not challenge a distorted belief, stay purely supportive** — replacing the bare "do not paraphrase or reflect back."

- [ ] **Step 1: Failing test**
```python
from sage_poc.prompts.composer import _intensity_guidance
from sage_poc import config

def test_d5_acuity_gate_text_when_enabled(monkeypatch):
    monkeypatch.setattr(config, "D5_ACUITY_GATE_ENABLED", True)
    monkeypatch.setattr(config, "D5_ACUITY_FLOOR", 8)
    g = _intensity_guidance(9)
    assert "do not challenge" in g.lower()
    assert "stay purely supportive" in g.lower()
    assert "validate" in g.lower()  # validate via specific naming, not cold

def test_d5_gate_off_by_default(monkeypatch):
    monkeypatch.setattr(config, "D5_ACUITY_GATE_ENABLED", False)
    g = _intensity_guidance(9)
    assert "do not challenge" not in g.lower()  # current behaviour unchanged when gate off
```
- [ ] **Step 2: Run — expect FAIL**.
- [ ] **Step 3: Implement** — in `composer.py`, in `_intensity_guidance(intensity)`, when `config.D5_ACUITY_GATE_ENABLED and intensity >= config.D5_ACUITY_FLOOR`, return a high-intensity string that (a) keeps "name the specific thing, no generic reflective opener, do not offer guidance yet" AND (b) adds "validate the feeling by naming it specifically; do not challenge or question a distorted belief here; stay purely supportive" (commas, no em dash, no L0 growth — this lives in the L2 intensity-guidance injection, not L0).
- [ ] **Step 4: High-intensity regression (EN + AR)** — `tests/test_d5_acuity_gate.py`: assert that with the gate ON, a high-intensity turn carrying a planted distortion does not co-sign it and is not cold (specific naming present). Provide both an EN and an AR (`؟`/Arabic) planted-distortion case. (Behavioural assertion via the composed prompt + a mocked responder; per spec §9 bind to eval R-2/R-7/P-2 in the live harness.)
- [ ] **Step 5: Run — expect PASS** (gate-off path leaves current behaviour identical).
- [ ] **Step 6: Commit (does NOT flip the flag)**
```bash
git add src/sage_poc/config.py src/sage_poc/prompts/composer.py tests/test_d5_acuity_gate.py
git commit -m "feat(D5): deterministic acuity gate behind flag (default off, pending clinical sign-off)"
```
- [ ] **Step 7 (separate, gated):** after standalone clinical sign-off + EN/AR regression review, flip `SAGE_D5_ACUITY_GATE=true` and pin `SAGE_D5_ACUITY_FLOOR` per clinical. Log the value into the decision record. **Not part of the code merge.**

---

## Self-Review
- **Spec coverage:** D4 mode-switch (Task 3) ✓; D3 de-script/cooldown (Task 4) ✓; D5 deterministic acuity gate (Task 5, gated) ✓; R1 language-aware gates (Task 1) ✓; Bug A (Task 2) ✓; G1 guard (Task 3) ✓; governance preconditions + #22 + L0-budget escalation + divergence tickets (Task 0 / Global Constraints) ✓. D5 belief-detection stays prompt-led (no task — by design). G2 (offer-suppression × banned-opener retry) — covered by Task 4 using `last_offer_turn` (state, not clearing `offered_skill_ids` mid-retry), avoiding the desync; note for the implementer.
- **Placeholder scan:** none — every code step shows the change.
- **Type consistency:** `detect_directive_request(state, primary_intent=None)`, `last_offer_turn`, `_offer_cooldown_turns()`, `D5_ACUITY_GATE_ENABLED`/`D5_ACUITY_FLOOR`, `offer_cooldown_suppressed` used consistently across tasks.
- **Sequencing:** Tasks 1, 2, 4 free now; Task 3 merge-gated on Task 0; Task 5 build-now/flip-gated on clinical sign-off. L0 budget review and native-Arabic port (R2) are out-of-tranche items.
