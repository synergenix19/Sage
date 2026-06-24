# L0 History-Handling Regression Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Execute only the "Executable plan" section. The "RETIRED" section lists tasks the diagnostic killed — do not run them.**

**Goal:** Fix two confirmed, independent regressions in how Sage handles a user's *own* conversation history on recall turns: (1) the L0 v2.3.0 MEMORY clause makes the model falsely deny disclosures that are visible in the prompt; (2) L0 budget overflow evicts the disclosure-bearing history turn before the model sees it. **Neither involves knowledge injection** — that framing was ruled out by the diagnostic below.

**Architecture:** Two independent fixes with two independent reviews.
1. **MEMORY-clause precision (prompt, clinical):** rewrite the L0 clause to be **unconditional and A4-preserving** — answer from conversation/earlier-session context when it is present, admit-and-invite only when it is genuinely absent. No detector, no runtime gate; it must be correct on *every* turn.
2. **Eviction-exemption (engineering):** a minimal deterministic `self_reference` detector marks recall turns so the composer overflow logic never evicts the clinical-flag-bearing disclosure the user is asking about.

The broader structural L0 bloat (which degrades *all* loaded sessions, not just recall) is **flagged as a separate finding, not fixed here**.

**Tech Stack:** Python 3.11, LangGraph, pytest, L0 JSON template (+ clinical sign-off), composer budget logic in `src/sage_poc/prompts/composer.py`.

## Global Constraints

- **Two fixes, two reviews.** The MEMORY-clause rewrite is clinically-signed content → **clinical re-sign-off required**. The eviction-exemption is engineering.
- **A4 preservation is a HARD constraint.** The MEMORY clause exists to stop confabulation (claiming memory you do not have — finding A4). The fix must kill false-denial **without** regressing A4: *present → answer; absent → still admit*. PR#51 collapsed these two cases into one unconditional denial and reintroduced A4's failure in the opposite direction. Every MEMORY-clause change ships with a **bidirectional** test (both sides) or it does not ship.
- **Unconditional clause, not detector-gated.** A prompt that never denies *present* history is correct for every turn; scoping it to detected self-reference would leave the bug live for recall phrasings the regex misses. The detector does **not** gate the clause.
- **Scope discipline.** Fix "never evict the turn being recalled." Do **not** expand into a full L0/six-layer budget re-architecture mid-ticket — surface the broader bloat as its own finding (below). This is the unilateral-rebuild move avoided at every prior gate.
- **Arabic parity:** test EN + Khaleeji/MSA. Detector reads `raw_message` (ar) / `message_en` (en).
- **No em dashes in any prompt content string** (use commas).
- **One commit per task** (commit-granularity convention).
- **Memory-coordinator rule:** work-session artifact; do not write the memory dir; surface findings to the command session.

---

## Diagnostic record (the "why" — keep; do not execute)

### ⛔ TASK 0 (intent probe) — STOP. Recall does not reach knowledge_retrieve.
Local classifier probe, 5 realistic recall-on-disclosure cases (gpt-4o-mini): **0/5 classified `info_request`** — labels were `general_chat` (4) / `new_skill` (1). The `info_request → knowledge_retrieve` (Node 6) chain the original plan targeted **does not fire** for sensitive recall when realistic prior disclosure is in history. The reviewer's realistic-history probe fix was load-bearing: a bracketed placeholder could have produced a false `info_request` and sent us building the wrong path.

### ⛔⛔ FREEFLOW TRACE — NO INJECTION.
All 5 cases through `freeflow_respond_node`, gates OFF, `user_id=None`, cross-checked against a deterministic `compose_prompt` presence pass:

| Case | Disclosure in prompt | knowledge_lookup fired | Verdict |
|---|---|---|---|
| substance EN / AR | Yes | No | ✓ correct recall |
| trauma EN | Yes (present) | No | false denial |
| domestic EN / AR | No (evicted) | No | eviction |

`knowledge_lookup` fired **0/5**; L4-in-state is never populated on the `general_chat` path. **There is no injection on this path — nothing to suppress.** The injection/abstain framing (original Tasks 3/4/7, decisions #2/#3) does not apply.

### ROOT CAUSE — confirmed by counterfactual (pre-#51 L0 swap). TWO INDEPENDENT bugs.
Short-context matching-recall battery (3 runs/case), current L0 vs pre-#51 L0 (v2.2.0 @68976f3, no MEMORY clause), gates OFF, `user_id=None`:

| case | present? v2.3.0 / v2.2.0 | current L0 (v2.3.0) | pre-#51 L0 (v2.2.0) |
|---|---|---|---|
| substance | True / True | RECALL×3 | RECALL×3 |
| domestic | **False** / **True** | MIXED×3 (evicted) | RECALL×3 |
| trauma | True / True | DENY,MIXED,RECALL | **RECALL×3** |

- **Vector 2 (false denial) = CONFIRMED PR#51 (`L0_persona.json:16` MEMORY clause).** Trauma is the clean isolator: disclosure present in BOTH versions, denies under v2.3.0, recalls cleanly under v2.2.0 — absent without the clause, present with it. The clause's *"say you do not have access"* over-fires on visible within-session history. (n modest; signal clean + mechanistically explained by the literal text.)
- **Vector 1 (eviction) = PRE-EXISTING structural L0 bloat; PR#51 aggravates at the margin.** Pre-#51 L0 was already **593 words (~4× the ~150-word budget)** — older than PR#51. PR#51's +40 words tipped the borderline domestic case present→evicted. Origin is the bloat flagged at `L0_persona.json:9`; PR#51 is an aggravator.
- **No third fault.** With neither eviction nor the clause (pre-#51, present cases), all recalled 3/3 — no separate "model ignores present history" problem.
- **Caveats:** n=3 runs, `user_id=None`. Authenticated prod appends a prior-context block (`freeflow_respond.py:112-114`) — *more* competition for the same budget, so eviction is likely **worse** in prod, not better.

---

## RETIRED — superseded by the diagnostic. DO NOT EXECUTE.

These targeted a knowledge-injection vector the trace ruled out. Listed explicitly so no worker resurrects them from an earlier draft: **reroute off the `info_request → knowledge_retrieve` edge** (that edge is not taken); **L4 knowledge suppression** (no L4 on this path); **D6 abstain-threshold calibration** (no knowledge retrieved); the **`SAGE_SELF_REFERENCE_GATE` / `SAGE_SELF_REFERENCE_SUPPRESS_L4`** gates; decisions **#2 (recall-as-citation boundary)** and **#3 (abstain floor)**; the shadow-detector-plus-audit apparatus and two-gate activation. The `self_reference` detector survives only in the reduced form of Task 2 below.

---

## IMPLEMENTATION STATUS (2026-06-24)

Built + verified this session; all four review items baked into the code (not prose):
- **Task 2 (detector):** DONE. `self_reference_detect.py` + `state.py` field + `server_helpers` default (issue 3 restored) + intent_route wiring. `test_self_reference_detect.py` 9/9.
- **Task 3 (eviction-exemption):** DONE. `pin_turn` added to `_build_l1_history_block` (default None preserves all non-recall callers byte-for-byte); Arabic-aware anchor via `_recall_text`/`_anchor_turn` (issue 2, Arabic test passes); over-budget surfaced as `status:`-prefixed sentinel, not a content layer (issue 4); pin applied at BOTH the initial build and the overflow branch (TDD caught that the initial build dropped the disclosure before overflow ran). `test_composer_eviction_exemption.py` 4/4 incl. non-recall-unchanged + Arabic + over-budget.
- **Task 1 (clause):** **CLINICALLY SIGNED OFF 2026-06-24** (wording approved as-is); gate cleared; **NOT yet deployed**. L0 v2.4.0, `status: approved`, `effective_date 2026-06-24`, word_budget 640→675. Deploy is the next step and is human-authorized: staging → QA(EN+AR) → prod, as its own deploy (not bundled with the eviction fix or anything else). Bidirectional **majority-vote** live gate (issue 1, N=5 require ≥4) `test_l0_memory_clause.py`. **Full-N seed counts (the evidence that backs "preserves A4"): present→answer 5/5, cross-session-absent→admit 5/5, lacks-detail→admit 5/5** — stably at ceiling, not a single clean run. Structural `test_l0_memory_honesty.py` updated to v2.4.0; `live_llm` marker registered so the gate can't be silently skipped. Internal ordering honored: gate is green at full N, so re-sign-off may now be requested.
- **Regression:** 2104 passed in the fast suite; the only 3 failures are confirmed PRE-EXISTING (fail on clean tree): `test_compose_prompt_no_overflow_with_large_cultural_override`, `test_output_gate_offer_voiding::...voids_offer_created_this_turn`, `test_skill_routing_ba_pd::test_no_new_substring_keyword_shadowing`. Two live-graph integration tests in `test_graph.py` also pre-existing.
- **Still open (execution, not investigation):** clinical sign-off RECEIVED 2026-06-24 (gate cleared). Remaining: **deploy L0 v2.4.0 via staging → QA(EN+AR) → prod as its own deploy** (human-authorized; not done); file the broader-bloat ticket and the process-gap ticket. (Heads-up / re-sign-off messages drafted in governance; sign-off already obtained.)

### BILINGUAL STAGING QA (2026-06-24, local against v2.4.0, per-fix/per-language)

| case | isolates | result |
|---|---|---|
| EN / AR within-budget present | clause | answer 4/4 / 4/4 ✓ |
| EN / AR pressure present | eviction-exemption (+clause); disclosure pinned `in_prompt=True` | answer 4/4 / 4/4 ✓ |
| AR absent → admit | A4 transfer | **admit 0/4 ⚠️** |

- **Both fixes transfer to Arabic:** present-side clause and eviction-exemption hold 4/4 in EN and AR, disclosure survives under pressure (pinned). The regression fix is confirmed bilingual.
- **FINDING (for the clinician, do NOT push through):** the *absent* side does not cleanly transfer to Arabic — the model deflects generically instead of admit-and-invite (0/4). It does **not confabulate** (core A4 no-confabulation holds), but the specified admit+invite behavior is absent in AR (EN gate was 5/5). New-vs-pre-existing NOT established (needs v2.3.0/v2.2.0 Arabic-absent counterfactual). Goes back to the clinician.
- **Deploy blockers CLEARED 2026-06-24:** (1) sign-off attributed — `approved_by = Rohan Sarda (clinical lead)`, who reviewed the v2.4.0 wording + the 5/5 gate evidence; recorded by the engineering lead. (2) The lead judged the AR absent-side finding **NOT a deploy blocker** — it is a soft, non-confabulating gap (core A4 holds), separate from the present-side regression this deploy fixes (which transfers bilingually 4/4). **Decision is documented-and-tracked, not pushed-through-silently:** raised as its own item and still routed to Rohan as an FYI (Arabic clause behavior is a clinical surface), with the new-vs-pre-existing characterization (v2.3.0/v2.2.0 AR-absent counterfactual) as that item's first step.

**RELAY — three findings to protect through compression (the command session must not flatten these):**
1. **No injection — the original framing is dead.** Don't let anyone rebuild suppress-the-injection / calibrate-the-abstain-floor.
2. **Severity = confirmed mechanism + clinical invalidation weight, NOT frequency.** The ≈0 prevalence is because explicit recall is rare (3/1388), not because eviction doesn't happen.
3. **The L0 change is PROPOSED-AND-GATED, not shipped.** "Implementation complete" ≠ "deployed": L0 v2.4.0 is `pending_clinical_signoff`, the deploy gate blocks, and the clause wording is still the clinician's to revise. No one should read this trail as "the fix is live."

## Executable plan

### Task 1: MEMORY-clause precision rewrite (A4-preserving, unconditional) — CLINICAL SIGN-OFF

**Files:**
- Modify: `src/sage_poc/prompts/templates/L0_persona.json` (MEMORY clause text; bump `version` 2.3.0 → 2.4.0; reset sign-off status to pending)
- Test: `tests/test_l0_memory_clause.py` (new)

**Interfaces:**
- Produces: an L0 v2.4.0 whose MEMORY clause answers from present history and admits only on genuine absence.

**A4 scope (verified, blocking — review 2026-06-24).** A4 in this repo's RCA (`Sage_Feedback_RCA_and_Fix_Plan` lines 34, 60) = *"memory fabricates instead of admitting no data; empty retrieval → block silently omitted."* Its trigger is the **cross-session memory / prior-context path** (`freeflow_respond.py:108-114`: `prior_context = _get_prior_context(state)`, injected only `if prior_context:` — when empty, nothing is injected and there is no sentinel). So **a within-session-empty case (`user_id=None`) does NOT exercise A4** — prior-context retrieval never runs. The A4-preservation gate MUST include a **cross-session-absent** case (retrieval ran, returned nothing) and a **cross-session-lacks-detail** case (block present, does not contain the queried thing). Do not let "preserves A4" be asserted by a test that never touches A4's condition.

- [ ] **Step 1: Write the BIDIRECTIONAL failing test** (the firing test PR#51 lacked) — present side kills vector 2; absent side covers A4 at its real (cross-session) trigger. LLM-behavioral → `live_llm`, N=5 seeds/case, assert majority.

```python
# tests/test_l0_memory_clause.py
import pytest
import sage_poc.nodes.freeflow_respond as ff
from sage_poc.nodes.freeflow_respond import freeflow_respond_node

def _state(recall, prior, lang="en", user_id=None):
    hist = ([{"role": "user", "content": prior},
             {"role": "assistant", "content": "thank you for telling me that."}] if prior else [])
    return {"message_en": recall, "raw_message": recall, "detected_language": lang,
            "conversation_history": hist, "conversation_summary": None, "active_skill_id": None,
            "primary_intent": "general_chat", "emotional_intensity": 5, "engagement": 5,
            "clinical_flags": [], "crisis_state": "none", "user_id": user_id, "session_id": None,
            "knowledge_passages": [], "knowledge_abstain": False, "path": [], "directive_posture": False,
            "stall_detected": False, "declined_skills": []}

DENY = ["don't have access", "do not have access", "can't see", "cannot see", "no access",
        "previous conversation", "past conversation", "haven't shared", "didn't share",
        "don't recall", "cannot recall", "not sure what you"]

@pytest.mark.live_llm
@pytest.mark.asyncio
async def test_present_history_is_answered_not_denied():
    # PRESENT (within-session): disclosure is in the prompt -> recall, do NOT deny (kills vector 2)
    out = await freeflow_respond_node(_state("what did I just tell you about my drinking?",
                                             "i drink most nights to switch off"))
    r = out["response_en"].lower()
    assert any(c in r for c in ["drink", "cope", "switch off"]) and not any(d in r for d in DENY)

@pytest.mark.live_llm
@pytest.mark.asyncio
async def test_cross_session_absent_admits_not_confabulates(monkeypatch):
    # A4 at its real trigger: prior-context retrieval RAN and returned nothing -> admit, do NOT invent.
    async def _empty(_state): return ""
    monkeypatch.setattr(ff, "_get_prior_context", _empty)
    out = await freeflow_respond_node(_state("what did I tell you last week about my job?", prior="",
                                             user_id="u-1"))
    r = out["response_en"].lower()
    assert any(d in r for d in DENY + ["share", "tell me"]) and "you told me you" not in r  # no fabricated detail

@pytest.mark.live_llm
@pytest.mark.asyncio
async def test_cross_session_lacks_detail_admits(monkeypatch):
    # prior-context present but about a DIFFERENT topic; asked-for detail absent -> admit, not confabulate.
    async def _other(_state):
        return "In an earlier conversation, you mentioned feeling stressed about work deadlines."
    monkeypatch.setattr(ff, "_get_prior_context", _other)
    out = await freeflow_respond_node(_state("what did I tell you about my brother?", prior="", user_id="u-1"))
    r = out["response_en"].lower()
    assert "brother" not in r or any(d in r for d in DENY + ["share", "tell me"])  # must not invent a brother detail
```

- [ ] **Step 2: Run, verify present side FAILS and all absent sides PASS today**

Run: `pytest tests/test_l0_memory_clause.py -v -m live_llm`
Expected: `test_present_history_...` FAILS (denies, vector 2); both A4 cross-session cases PASS (A4 already holds at its real trigger). This proves the test captures vector 2 **and** guards A4's actual condition, not a proxy.

- [ ] **Step 3: Rewrite the MEMORY clause** in `L0_persona.json` (clinical `# REVIEW` — wording is a sign-off input). Replace:

> `MEMORY: You can see only this conversation, unless earlier-session context appears below. If asked to recall something not shown to you, say you do not have access and invite them to share it again, never claim it was never provided.`

with a clause that splits present from absent:

> `MEMORY: You can see this conversation, and any earlier-session context shown below. If the person refers to something they told you and it is here, answer from it directly and naturally. Only when it is genuinely not present, say you cannot see it and invite them to share it again. Never deny or contradict something that is visible to you, and never claim they did not say something they did.`

Bump `version` to `2.4.0`; set status to pending sign-off.

- [ ] **Step 4: Run the bidirectional test, verify all three cases pass**

Run: `pytest tests/test_l0_memory_clause.py -v -m live_llm`
Expected: all PASS (present → recalled; cross-session-absent → admitted; cross-session-lacks-detail → admitted, not confabulated).

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/prompts/templates/L0_persona.json tests/test_l0_memory_clause.py
git commit -m "fix(L0): MEMORY clause answers present history, admits only on genuine absence (v2.4.0; fixes PR#51 false-denial, preserves A4)"
```

- [ ] **Gate + INTERNAL ORDERING (must hold the heads-up promise):** the order inside Task 1 is **build clause + bidirectional test → confirm test GREEN → THEN request clinical re-sign-off → ship.** Do NOT request re-sign-off before the test is green — the heads-up to the lead promised *"I'll confirm green before asking for re-sign-off."* Reading "build Tasks 1–3, gated on re-sign-off" as "build all three, then ask" would break that promise. Ships via L0 version + sign-off (same path PR#51 used); the bidirectional test is the machine gate. No runtime flag.

### Task 2: Minimal `self_reference` detector — single job: eviction-exemption targeting

**Files:**
- Create: `src/sage_poc/nodes/self_reference_detect.py`
- Modify: `src/sage_poc/state.py` (`self_reference: bool` near `directive_posture`), `intent_route.py` (import + return)
- Test: `tests/test_self_reference_detect.py`

**Interfaces:**
- Produces: `detect_self_reference(state) -> bool`; state field `self_reference`. **Sole consumer is Task 3.** No gate, no shadow mode, no audit apparatus (those were for the retired suppression plan).

- [ ] **Step 1: Failing test**

```python
# tests/test_self_reference_detect.py
import pytest
from sage_poc.nodes.self_reference_detect import detect_self_reference

@pytest.mark.parametrize("msg,raw,lang,expected", [
    ("what did I just tell you about my husband?", "", "en", True),
    ("didn't I say I drink to cope?", "", "en", True),
    ("you said breathing would help", "", "en", True),
    ("ماذا قلت لك عن زوجي؟", "ماذا قلت لك عن زوجي؟", "ar", True),
    ("what is generalized anxiety disorder?", "", "en", False),
])
def test_detect_self_reference(msg, raw, lang, expected):
    assert detect_self_reference({"message_en": msg, "raw_message": raw or msg,
                                  "detected_language": lang}) is expected
```

- [ ] **Step 2: Run, verify fail** — `pytest tests/test_self_reference_detect.py -v` → `ModuleNotFoundError`.

- [ ] **Step 3: Implement** (fail toward firing; Arabic markers first)

```python
# src/sage_poc/nodes/self_reference_detect.py
"""Deterministic: is the user asking to recall something THEY told Sage earlier?
Sole consumer: composer eviction-exemption (never drop the disclosure being recalled).
Fails toward firing — a false positive only protects history from eviction (safe)."""
from __future__ import annotations
import re
from sage_poc.state import SageState

_EN = (r"\bwhat did i (just )?(tell|say to|mention to) you\b", r"\bdidn'?t i (say|tell|mention)\b",
       r"\b(do|don'?t) you remember (what|when|that) i\b", r"\byou said\b", r"\bi (told|said to) you\b")
_AR = (r"ماذا قلت لك", r"ألم (أقل|أخبرك|أذكر)", r"هل تتذكر (ما|أن|عندما)", r"قلت لك", r"كما (قلت|ذكرت|أخبرتك)")

def detect_self_reference(state: SageState) -> bool:
    lang = state.get("detected_language", "en")
    text = state.get("raw_message", "") if lang == "ar" else state.get("message_en", "")
    if not text:
        return False
    low = text.lower()
    return any(re.search(m, low) for m in (_AR if lang == "ar" else _EN))
```

Add `self_reference: bool` to `state.py`; in `intent_route_node` return dict add `"self_reference": detect_self_reference(state)`.

- [ ] **Step 4: Run, verify pass** — `pytest tests/test_self_reference_detect.py tests/test_intent_route_node.py -v`.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/nodes/self_reference_detect.py src/sage_poc/state.py src/sage_poc/nodes/intent_route.py tests/test_self_reference_detect.py
git commit -m "feat(routing): minimal self_reference detector (sole consumer: eviction-exemption)"
```

### Task 3: Eviction-exemption — never evict the disclosure on a recall turn

**Files:**
- Modify: `src/sage_poc/prompts/composer.py:899-926` (L1 overflow shrink)
- Test: `tests/test_composer_eviction_exemption.py`

**Pin target — corrected (review 2026-06-24).** `clinical_flags` is a **session-level accumulator** (`state.py:17`); `conversation_history` turns carry only `role`/`content` (`graph.py:123-124`) — there is **no per-turn flag** to map a session flag back to a history turn. So "pin the flag-bearing turn" is not expressible. Pin target is therefore **keyword-anchor**: the most-recent history turn sharing a salient content token with the recall message; fall back to the most-recent user turn when the recall has no content anchor (e.g. "what did I just tell you?"). Well-defined against the real state, no per-turn flags needed.

**Interfaces:**
- Consumes: `state["self_reference"]` (Task 2), `conversation_history`, `message_en`.
- Produces: on a `self_reference` turn, the overflow shrink retains the keyword-anchored disclosure turn; never silently ships over budget.

- [ ] **Step 1: Failing test** — recall whose content keyword ("husband") anchors a history turn; force overflow; assert that turn survives.

```python
# tests/test_composer_eviction_exemption.py
from sage_poc.prompts.composer import compose_prompt

def _state(**kw):
    base = {"raw_message": "...", "detected_language": "en", "self_reference": True,
            "conversation_summary": None, "active_skill_id": None, "primary_intent": "general_chat",
            "emotional_intensity": 5, "engagement": 5, "clinical_flags": [], "crisis_state": "none",
            "path": [], "directive_posture": False, "stall_detected": False, "declined_skills": []}
    base.update(kw); return base

def test_recall_turn_keeps_keyword_anchored_disclosure_under_overflow():
    disclosure = "things at home with my husband have gotten scary"
    padding = [{"role": "user", "content": "x " * 400}, {"role": "assistant", "content": "y " * 400}]
    state = _state(message_en="what did I just say about my husband?",
                   conversation_history=[{"role": "user", "content": disclosure},
                                         {"role": "assistant", "content": "thank you."}] + padding)
    _, user, _ = compose_prompt(state)
    assert disclosure in user   # anchored disclosure survives overflow

def test_over_budget_recall_flags_not_silently_ships(caplog):
    # Even the pinned disclosure + 4x-bloated L0 can exceed total budget. Must NOT ship silently:
    # keep the disclosure, emit a loud signal, defer structural resolution to the broader-bloat ticket.
    disclosure = "my husband has been violent " * 60   # large, forces over-budget even when pinned
    state = _state(message_en="what did I just say about my husband?",
                   conversation_history=[{"role": "user", "content": disclosure},
                                         {"role": "assistant", "content": "ok."}])
    _, user, layers = compose_prompt(state)
    assert disclosure[:40] in user                      # disclosure never dropped on a recall turn
    assert "prompt_over_budget" in layers               # observable, not silent
```

- [ ] **Step 2: Run, verify fail** (today overflow shrinks L1 to 0, drops the disclosure, and ships over-budget silently).

- [ ] **Step 3: Implement** in the overflow block (`composer.py:899-926`). When `state.get("self_reference")`:
  1. Compute the keyword anchor: salient content tokens of `message_en` (drop stopwords); the anchored turn = most-recent history turn containing one; fallback = most-recent user turn.
  2. Pin the anchored turn verbatim; shrink the **other** raw history turns first (preserve `conversation_summary` as today, per §5.6.3 order).
  3. **Sacrifice order when still over budget** (real code today reduces history only — there is no example-reduction lever in this cascade; `_select_few_shot_examples` is static `[:2]`): after non-anchored history is shrunk to zero, if `[static L0 + anchored disclosure + summary]` still exceeds `_TOTAL_WORD_BUDGET`, **keep the anchored disclosure** (the recall requires it), append a `"prompt_over_budget"` layer marker, and `_log.warning` once. **Never drop the recalled disclosure and never ship over budget silently.** Structural resolution (trim L0) is the separate broader-bloat ticket, not this one.
  4. Comment: `# Deviation from v7 §5.6.3 documented shrink order (pinning against the history shrink) — flagged in sign-off per ABSOLUTE RULE 1.`

- [ ] **Step 4: Run, verify both tests pass.** Then full suite: `pytest -q`.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/prompts/composer.py tests/test_composer_eviction_exemption.py
git commit -m "fix(composer): pin flagged disclosure against L1 eviction on a recall turn (#vector1 mitigation)"
```

### Task 4: Prod-log sizing — AFTER Tasks 1–3 freeze the mechanism descriptions

Sizing is designed against the now-frozen mechanisms (not before — the query counts what the rewrite names). Read-only; minimize fields + access-log sensitive flags (POC, but still sensitive).

- [ ] Count, **separately**, against the two confirmed mechanisms:
  - **False-denial:** sessions where a recall-phrased turn (regex of the Task 2 markers, applied in SQL over `messages`) followed a turn that set a sensitive `clinical_flag`. Direct proxy.
  - **Eviction:** sessions with a sensitive `clinical_flag` and high context pressure. Prod `session_audit` has **no eviction flag**, so approximate via prompt-size / turn-count proxies and **state the limit explicitly** — do not present the proxy as exact.
- [ ] Feed both counts into the sign-off package as separate sizes (they fix differently).

### TASK 4 RESULT (2026-06-24, prod read-only, access-logged, no bodies returned)

Schema/timestamp check folded in: query collapsed to `messages`-only (it carries `turn_number, role, content, clinical_flags, crisis_flags`); `messages.turn_number` exists (no `created_at` fallback); `detected_language` absent (Arabic proxy dropped); `model_version` NULL (boundary from deploy log: `:pr51_ts ≈ 2026-06-24 13:58:56 +04`, **approximate-to-deploy**, uncertain to ~09:54 +04 if the clause shipped pending earlier).

- **Query A (false-denial frequency) — NOT RUN, by design.** Post-PR#51 window is ~4h of prod data (deploy ~09:58 UTC; last turn 14:06 UTC), denominator ~single digits. A raw "k of 3" carries no sizing content and risks being quoted as a rate downstream; and A is the query that most wants message bodies, so not running it closes the minimization door rather than guarding it. **Vector 2's reality rests on the counterfactual (confirmed), not on prevalence.**
- **Query B (eviction-of-recalled-disclosure, all history) — RAN. Result: 0, validated.** Not a query bug: the flag filter matches 100 turns and the `?|`/jsonb path is correct; the constraint is recall phrasing — only **3 of 1388** user turns match explicit recall (lower bound; narrow regex), and **0** overlap a flagged disclosure. So the recall-of-disclosure eviction symptom is **rare-to-absent at current usage**, because users almost never phrase explicit recall — disclosures are common (~7% flagged), explicit recall of them is not.
- **Broader structural eviction is NOT sized by B and is not retroactively sizable** (no eviction marker; recall lens misses non-recall eviction). Stays open in the broader-bloat finding; needs forward prompt-size logging.
- **Net:** prevalence is not establishable from current prod for any of the three vectors. Severity rests on **confirmed mechanism + clinical invalidation weight, not frequency** — say exactly that in the package.

---

## Documented property (not a bug — a known seam)

The detector-gated Task 3 plus the unconditional Task 1 create a deliberate seam: **a recall the Task-2 regex misses gets the corrected clause (Task 1) but no eviction protection (Task 3).** Under token pressure its disclosure can still evict, and the clause then degrades to an honest *"I cannot see that, can you share it again"* — the **safe** failure (admit, never confabulate), not a false denial. This is an accepted property, recorded so it is not a surprise; widening detector recall and the broader-bloat fix both shrink the seam.

## Separate finding (FLAG — do NOT fix here): L0 bloat degrades ALL loaded sessions

The diagnostic surfaced that L0 has been ~4× budget since **≤ v2.2.0**, and the overflow logic "drops any history under load," not only on recall turns. The `user_id=None` caveat means **authenticated prod is likely worse** (the prior-context block adds more competition for the same budget). This is a **structural L0 / six-layer-budget defect whose blast radius is every long or authenticated session**.

- **Do not fix it in this ticket.** Task 3 is a targeted mitigation for the recall symptom only.
- **Severity-sharpening check — DONE (2026-06-24), result: does NOT escalate.** Question was whether overflow evicts state the executor needs mid-skill (→ orchestration state-loss, higher tier) or only response context (→ memory degradation). Verified by input-set inspection (stronger than a single trace): `skill_executor_node` **never reads `conversation_history`** (grep: 0 occurrences); its inputs are graph-state/current-turn only (`active_step_id`, `criteria_hold_count`, `prev_step_id`, `message_en`, …); `evaluate_completion_criteria` reads only `message_en` (`criteria_eval.py:35-36`); `evaluate_step_policy` reads graph-state signals. **Step progression is invariant to prompt eviction by construction — the executor cannot misstep on evicted history because it cannot see that window.** The L3 step instruction survives eviction (not L1), so the protocol still delivers. **Conclusion: this stays a memory / response-continuity degradation, NOT skill-execution state-loss. Severity does not escalate; owner unchanged.** (A confirmatory mid-skill trace would only re-demonstrate the structural invariant.)
- **Raise it as its own ticket** with its own sizing and its own clinical visibility. Folding it into the recall handoff would hide its blast radius.
- **Not retroactively sizable (confirmed 2026-06-24):** prod has no eviction marker, and Task 4's recall-scoped Query B returned 0 only because explicit recall is rare (3/1388) — it does **not** measure non-recall eviction. Accurate sizing requires **forward per-turn prompt-size logging**; `messages.token_usage`/`prompt_layers` already exist as the hook. This ticket owns adding the eviction signal, then counting.

---

## Process gap (FLAG for the command session — needs an owner, not solved here)

**PR#51 shipped a clinically-signed L0 change that regressed the exact finding (A4) it was meant to fix, and it shipped without a present-and-absent firing test that would have caught it.** The recall fix is downstream; the upstream question is process: how did a signed prompt change reach prod without a bidirectional firing test? Task 1's bidirectional test is the *local* fix. Whether a present-and-absent firing test becomes a **standing gate on all L0 / signed-prompt sign-offs** is the command session's call and needs an owner — the next signed prompt change can fail the same way. Not in scope for this ticket; recorded here so it lands somewhere rather than nowhere.

---

## Sign-off / handoff package (repointed)

- **Item A — MEMORY-clause v2.4.0 re-sign-off** (signed content). Frame with the **invalidation dimension explicitly**: denying a DV or trauma survivor's *own* disclosure back to them ("no, you didn't tell me about your husband") is actively invalidating and carries clinical weight beyond degraded rapport — that is what the lead weighs for how fast re-sign-off must move. **Severity: High, not emergency** (Node 1 crisis preemption verified intact: `graph.set_entry_point("safety_check")`, `_route_after_safety` → crisis on `not is_safe`, before `intent_route`).
  - **The clause WORDING is the clinician's to revise, not just approve.** This is a memory-honesty clause governing how the system handles trauma/DV disclosures; the proposed v2.4.0 text is a `# REVIEW` clinical *input*, not a fait accompli. Frame the request as "review and revise this wording," not "approve this wording" — the clinician owns the language (clinician-autonomy line).
  - **Separate message from the heads-up; do not merge.** The heads-up ("PR#51 regressed, fix in progress, preservation pending-green") goes today regardless. The re-sign-off request ("v2.4.0, A4 gate green at full N — counts attached — please review and revise") goes ONLY after the full-N gate run (now done: 5/5, 5/5, 5/5). Collapsing them asks for sign-off in the same breath as announcing the regression, ahead of the green-confirmation the heads-up promised.
- **Item B — broader L0-bloat eviction** as its **own** item, sized separately (see finding above). Do not merge into Item A.
- **Deviation flag (ABSOLUTE RULE 1):** Task 3 pins a history turn against v7 §5.6.3's documented overflow order ("history window shrinks first, then examples reduce"). Minor and defensible (it protects the disclosure the user is asking about), but it is a documented deviation and must be named in the sign-off, not slipped in. Also disclose the over-budget failure mode: on a recall of a long disclosure under the 4×-bloated L0, the prompt keeps the disclosure and is marked `prompt_over_budget` rather than dropping it or silently exceeding budget — the structural resolution is Item B.
- **TODAY heads-up (do not wait for prod counts):** tell the clinical lead who signed PR#51 *today* that it regressed recall — **confirmed** (reverting the clause restores recall in the counterfactual), fix in progress. Counts size it; they do not change the attribution. The message lands as a finding, not an accusation, precisely because the counterfactual is done.
- **Prevalence statement (final) — keep these sentences ADJACENT; the number quoted without the guard inverts its meaning:** Recall-of-disclosure eviction is **≈ 0 at current scale because explicit recall is rare (3/1388), NOT because eviction doesn't happen.** Therefore **severity rests on confirmed mechanism + clinical invalidation weight, explicitly NOT on frequency** — a "0" or single-digit must not be read as "rarely happens / low priority." (False-denial frequency also not sized: post-deploy window ~4h. Broader eviction not retroactively sizable.)
- **Governance record (for any future re-run of A):** the denial-window edge `:pr51_ts` is `2026-06-24 13:58:56 +04` **approximate-to-deploy**; the clause may have served pending from an earlier 06-24 deploy (as early as ~09:54 +04). `model_version` is NULL in prod so the boundary cannot be pinned from data. Written down now so a future longer-window A re-run knows the edge is soft and why.

---

## Out of scope (tracked separately)

- **#56 region config drift** (prod pinned to deprecated Railway `sfo` key). Parked behind the clinical work; do not mutate `multiRegionConfig` until the "why sfo / sanctioned region-change path" + Health-Data-Law residency questions are answered.
- **Broader L0 / six-layer budget re-architecture** — the flagged finding above; its own ticket.

---

## Self-review

**Coverage of the confirmed diagnosis:** vector 2 (false denial) → Task 1 (unconditional, A4-preserving, bidirectional test); vector 1 (eviction) → Task 2 (detector) + Task 3 (exemption); the broader structural bloat → flagged finding, not folded in; sizing → Task 4, after the rewrite freezes mechanisms; the regression-test gap PR#51 lacked → Task 1's bidirectional test.

**Dead work retired from the executable body:** reroute, L4 suppression, D6 calibration, both gates, decisions #2/#3, shadow/audit apparatus — all in the RETIRED section, none in Tasks 1–4. An agentic worker running the Executable plan cannot build them.

**Detector justification (not inertia):** the detector survives for exactly one job — telling Task 3 which turn is a recall so it can protect the disclosure. It does **not** gate the MEMORY clause (Task 1 is unconditional, correct for every turn). If Task 3 were dropped, the detector would be dropped too.

**A4 non-regression:** Task 1 ships only if **both** sides of the bidirectional test pass — present→answer and absent→admit — so the fix cannot reintroduce confabulation the way PR#51 reintroduced false-denial.

**Type/name consistency:** `detect_self_reference(state) -> bool`, state field `self_reference`, used identically in Tasks 2–3. The live-LLM tests are nondeterministic — run N seeds, assert majority; reconcile `freeflow_respond_node` fixture shape with the suite's actual helpers at execution time.
