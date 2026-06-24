# Conversational Style (D4 / D3 / D5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Sage answer-first when the user wants info/a decision (D4), drop the scripted-menu feel (D3), and validate feelings without co-signing distorted beliefs (D5) — reliably, via deterministic gates, reconciled to the production architecture.

**Architecture:** Spec: `docs/superpowers/specs/2026-06-24-conversational-style-d3-d4-d5-design.md` (FINAL, source-verified). Gate *mechanics* stay Python node logic (decided carve-out, ticket #22 LOCK-QDISC-22); new clinical *values* go to data (`skill_matching` JSON, config). All gates run on the English `response_en`/`message_en` before translation (covers EN + translate-out AR). **R1 scope (corrected):** Task 1 makes only the *question-discipline* gate language-aware for Arabic `؟` and closes ITS already-Arabic gap; the *banned-opener* gate's already-Arabic bypass (`_response_en_is_arabic` at `output_gate.py:408`) is **out of scope here** — scoped to the native-Arabic track (R2) under the documented "English-source-only while translate-out is in force" guarantee (§16). Do not claim R1 closes the whole already-Arabic gap.

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
    # it is emitted on a fallback path; it must not itself be a banned opener (second-order strip)
    from sage_poc.nodes.output_gate import _BANNED_OPENER_RE
    assert _BANNED_OPENER_RE.match(_VETTED_FALLBACK_RESPONSE.lstrip()) is None
```
NOTE: the new fallback copy is strictly better than the live gutting bug, so merge now; route the final wording to **clinical confirmation post-merge** (it is user-facing copy on a measurable path).
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
- Produces: `detect_directive_request(state: dict, primary_intent: str | None = None) -> bool` — returns True on existing triggers OR `primary_intent == "info_request"`. Default param keeps existing callers working. NOTE (must-fix, see Step 3): there is deliberately NO bare question-mark trigger; a `?` does not disambiguate an info request from an emotional disclosure ("am I broken?").

- [ ] **Step 1: Failing tests**
```python
from sage_poc.nodes.directive_detect import detect_directive_request

def test_info_request_intent_triggers_directive():
    # a genuine factual/list request classifies as info_request -> answer-first
    st = {"message_en": "can you give me a list of sleep tips?", "conversation_history": []}
    assert detect_directive_request(st, primary_intent="info_request") is True

# MUST-FIX (clinical over-fire guard): a question mark does NOT trigger answer-first.
# Emotional disclosure phrased as a question stays in Reflect mode so the earned open
# question is not stripped (the §5 carve-out). These classify as disclosure intents, not info_request.
def test_emotional_disclosure_question_does_not_trigger():
    for q in ["am I broken?", "why do I always feel like this?", "what's wrong with me?", "is it my fault?"]:
        st = {"message_en": q, "conversation_history": []}
        assert detect_directive_request(st, primary_intent="new_skill") is False, q

def test_plain_emotional_disclosure_does_not_trigger():
    st = {"message_en": "i feel so overwhelmed and exhausted lately", "conversation_history": []}
    assert detect_directive_request(st, primary_intent="new_skill") is False
```
- [ ] **Step 2: Run — expect FAIL** (no `primary_intent` param yet).
- [ ] **Step 3: Implement (intent-gated only — NO punctuation trigger)**
  - In `directive_detect.py`, change the signature to `def detect_directive_request(state, primary_intent=None):` and near the top of the body, after `text = (state.get("message_en") or "").lower()`, add ONLY the intent-based trigger:
    ```python
    if primary_intent == "info_request":
        return True
    ```
    **Do NOT add a bare `text.endswith("?"/"؟")` trigger.** A question mark does not disambiguate an info request from an emotional disclosure ("am I broken?"); firing `directive_posture` there would let `_strip_trailing_question` remove the earned open question from a Reflect-mode reply (the exact §5 harm). Genuine factual/list questions already classify as `info_request`, so the intent trigger covers them without the false positive. Keep the existing `_DIRECTIVE_PHRASES` / `_REPAIR_PUSHBACK` (curt-reply-after-question) logic below unchanged.
  - In `intent_route.py:148`, change `"directive_posture": detect_directive_request(state),` to `"directive_posture": detect_directive_request(state, primary_intent=data.get("primary_intent")),` (use the freshly-parsed classifier result `data`, NOT `state["primary_intent"]` which holds the prior turn).
- [ ] **Step 3b: Audit marker (F3) for directive-set.** In `intent_route_node`, when the computed `directive_posture` is True, append `"directive_posture_set"` to the turn's `path` (the same `node_path` that `session_audit` records), so §9 replay can attribute firings to the new logic. Add a test asserting the marker appears on an info_request turn and is absent otherwise.
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
git commit -m "feat(routing): extend directive-posture to info_request (intent-gated, no bare-? trigger) + curt-reply; G1 directive-offer guard [D4]"
```

---

### Task 4a: D3 — offer cooldown (mechanic + value in data) — UNGATED (merges with batch)
> **Split (condition 2, verified):** `skill_offer.json` is `status:"approved"`, `approved_by:clinical_lead`, v0.2.0, and **live-serving** (loader serves regardless of status). So the "drop the which-would-you-prefer close" copy edit is a change to **live clinician-approved therapeutic copy** → it is **Task 4b (gated)**: a separate draft→review→canary change (sign-off C1), NOT shipped on this merge. Task 4a below is the cooldown mechanic/state/config only and merges freely.
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
- [ ] **Step 3: Implement** — PLACEMENT MATTERS (SF2/G2). Add the cooldown check in `skill_select_node` **immediately after the offer-accept promotion block** (after `skill_select.py:380`, where `stale_offer_clear` is defined and any accepted/pending offer has already returned) and **before** keyword/semantic matching:
  ```python
  _cooldown = _offer_cooldown_turns()  # reads skill_matching rule, falls back to config
  _last = state.get("last_offer_turn")
  if _last is not None and (state.get("turn_count", 0) - _last) < _cooldown:
      return {**stale_offer_clear, "active_skill_id": None, "active_step_id": None,
              "skill_match_method": None, "semantic_score": None,
              "path": state["path"] + ["skill_select", "offer_cooldown_suppressed"]}
  ```
  - **G2 (verified safe):** at this placement `stale_offer_clear` is `{}` in the normal case (it is only `{"offered_skill_ids": None}` on a *stale-rename* accept, where clearing is correct), and the cooldown itself never touches `offered_skill_ids` — so it cannot void a pending offer the user already saw. A pending offer being *accepted* already returned at `:366-371` above this check.
  - **SF3 (verified):** `turn_count` exists (`state.py:74`) and is incremented every turn in `output_gate` (`:557`, returned `:606`), so the cross-turn arithmetic is sound — no new counter needed.
  - Add `_offer_cooldown_turns()` reading the `default_offer` rule's `cooldown_turns` (fallback `config.SKILL_OFFER_COOLDOWN_TURNS`). When an offer is made (the `skill_offer_made` return ~`:290`), add `"last_offer_turn": state.get("turn_count", 0)` to that returned dict. Add `last_offer_turn: int | None` to `state.py` SageState.
- [ ] **Step 4: (moved to Task 4b — gated)** Do NOT edit `skill_offer.json` in Task 4a. The copy edit (remove "Ask which they would prefer, as one short question.") is **Task 4b**: it touches a live approved template, so it goes on a **separate branch/PR held for clinical sign-off C1 + canary (v7 §9.5)** and is excluded from the ungated merge batch. Task 4a ships the cooldown only; the repeat-menu feel is reduced by suppression (4a) now, and the single-woven-offer copy lands with 4b after C1.
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

def test_d5_floor_boundary(monkeypatch):
    monkeypatch.setattr(config, "D5_ACUITY_GATE_ENABLED", True)
    monkeypatch.setattr(config, "D5_ACUITY_FLOOR", 8)
    assert "do not challenge" not in _intensity_guidance(7).lower()  # high band, below floor -> no D5
    assert "do not challenge" in _intensity_guidance(8).lower()      # at floor -> D5 active
```
- [ ] **Step 2: Run — expect FAIL**.
- [ ] **Step 3: Implement (SF4 — function + band confirmed).** `_intensity_guidance(intensity)` exists at `composer.py:211` and is the real path; its **`high` band starts at intensity ≥ 7** (`<=3` low, `<=6` mid, else high). The D5 augmentation keys on its **own** `config.D5_ACUITY_FLOOR` (default 8 = `emotional_intensity > 7`, the executor `validate_only` floor), so: when `config.D5_ACUITY_GATE_ENABLED and intensity >= config.D5_ACUITY_FLOOR`, return a string that (a) keeps "name the specific thing, no generic reflective opener, do not offer guidance yet" AND (b) adds "validate the feeling by naming it specifically; do not challenge or question a distorted belief here; stay purely supportive" (commas, no em dash; lives in the L2 intensity-guidance injection, **not** L0 → zero L0 growth).
  - **Floor/band gap (clinical decision, document it):** with floor=8, **intensity == 7 is in the `high` band but below the acuity floor** → it gets the standard high guidance, NOT the D5 challenge-suppress. This matches the `validate_only` floor (>7). If clinical prefers the D5 gate to cover all of `high`, set `D5_ACUITY_FLOOR=7`. Pin the value at the standalone sign-off (Step 7); default 8 until then.
- [ ] **Step 4: High-intensity regression (EN + AR)** — `tests/test_d5_acuity_gate.py`: assert that with the gate ON, a high-intensity turn carrying a planted distortion does not co-sign it and is not cold (specific naming present). Provide both an EN and an AR (`؟`/Arabic) planted-distortion case. (Behavioural assertion via the composed prompt + a mocked responder; per spec §9 bind to eval R-2/R-7/P-2 in the live harness.)
- [ ] **Step 5: Run — expect PASS** (gate-off path leaves current behaviour identical).
- [ ] **Step 6: Commit (does NOT flip the flag)**
```bash
git add src/sage_poc/config.py src/sage_poc/prompts/composer.py tests/test_d5_acuity_gate.py
git commit -m "feat(D5): deterministic acuity gate behind flag (default off, pending clinical sign-off)"
```
- [ ] **Step 7 (separate, gated):** after standalone clinical sign-off + EN/AR regression review, flip `SAGE_D5_ACUITY_GATE=true` and pin `SAGE_D5_ACUITY_FLOOR` per clinical. Log the value into the decision record. **Not part of the code merge.**

---

### Task 6: Behavioral acceptance — §9 replay + Abby-parity (final gate before "done")
Unit tests miss exactly the failure class the reviewer flagged (D4 over-fire on disclosure-questions). Add a behavioral gate, run on **staging** after Tasks 1–4 merge, before declaring the tranche done.

**Files:** Test/harness: `tests/routing_eval/` or a staging replay script (reuse the feedback-replay harness pattern from `scratchpad/feedbacktest.py`). Bind assertions to the live eval instruments **R-2** (question count/type), **R-7** (response-shape), **P-2** (warmth register) — confirm exact IDs against the current test harness, not the 2026-05-20 v1.0 doc.

- [ ] **Step 1:** Replay the feedback scenarios against staging: **D4** — ID24/46/57/58 (over-questioning) now answer-first on info; **and the over-fire guard** — a disclosure-question ("am I broken?", "why do I feel this way?") still gets a Reflect-mode reply that **keeps its one earned open question** (directive_posture False; question NOT stripped). **D3** — ID41/36/37/56 now one woven offer, no repeated menu within N turns.
- [ ] **Step 2:** Abby-parity probes (the §3 four): emotional disclosure → validate + one open question; explicit "just give me a list" → answer-first; "that's a lot, one thing?" → one concrete step + one optional offer.
- [ ] **Step 3:** Confirm `directive_posture_set` + `offer_cooldown_suppressed` markers appear in `session_audit.node_path` for the relevant turns (F3 traceability).
- [ ] **Step 4:** Record results; only then mark the tranche done. (D5 high-intensity behavioral check is part of its separate sign-off regression, Task 5 Step 4, EN+AR.)

---

## Self-Review
- **Spec coverage:** D4 mode-switch (Task 3, intent-gated — no punctuation over-fire) ✓; D3 de-script/cooldown (Task 4) ✓; D5 deterministic acuity gate (Task 5, gated, floor/band reconciled) ✓; **R1 = question-discipline half only (Task 1)** — banned-opener-on-already-Arabic is **out of tranche → R2/native-Arabic track** under the English-source-only guarantee (do NOT mark R1 fully closed); Bug A (Task 2) ✓; G1 guard (Task 3) ✓; F3 audit markers — `directive_posture_set` (Task 3b) + `offer_cooldown_suppressed` (Task 4) ✓; behavioral acceptance (Task 6) ✓. Governance preconditions + #22 owner (Task 0) ✓; **L0-budget drift = filed/ticketed (Task 0 Step 4), NOT resolved** — the 4×-drift prompt-architecture review is out-of-tranche. D5 belief-detection stays prompt-led (by design). G2 (offer-suppression × banned-opener retry) — covered by Task 4 using `last_offer_turn` (never clears `offered_skill_ids`), placement verified after the accept block.
- **Placeholder scan:** none — every code step shows the change.
- **Type consistency:** `detect_directive_request(state, primary_intent=None)`, `last_offer_turn`, `_offer_cooldown_turns()`, `D5_ACUITY_GATE_ENABLED`/`D5_ACUITY_FLOOR`, `offer_cooldown_suppressed` used consistently across tasks.
- **Sequencing:** Tasks 1, 2, 4 free now; Task 3 merge-gated on Task 0; Task 5 build-now/flip-gated on clinical sign-off. L0 budget review and native-Arabic port (R2) are out-of-tranche items.
