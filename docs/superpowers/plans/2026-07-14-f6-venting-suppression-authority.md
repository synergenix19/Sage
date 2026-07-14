# F6 — Venting/Presence Suppression Authority (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Steps use `- [ ]` checkboxes.

**Goal:** Give the venting/"just listen" signal **authority to suppress skill imposition**, closing the one live corner where high-intensity venting-with-distress gets `dbt_tipp` imposed on a user who explicitly asked not to be fixed.

**Architecture:** `intent_route` already computes deterministic routing signals (stall, self-reference, prepass). Add a **`venting_detected`** signal (reusing the existing `PI-VI-001` / `venting_intent.json` keyword set), then guard **Routing-SF-2** in `_route_after_intent` so a venting turn routes to `freeflow` (presence) instead of `skill_select` — even at high intensity. Flag-gated (`SAGE_VENTING_SUPPRESSION`, default OFF). No node added; no graph edge added; one new deterministic signal + one routing guard.

**Tech Stack:** Python 3.12, LangGraph, `pytest` (`uv run pytest`).

**Parent spec:** `2026-07-14-bot-behaviour-routing-conformance-design.md` §3 (F6). **Escalation:** `ESC-2026-07-14-...` §6 (F6 = the only remaining verified live gap).

## Re-baseline discipline (READ FIRST — this plan does not inherit a stale tree)

Every behavioural claim below was verified against **`origin/master` `52cba81` in the FULL GRAPH** (`app.ainvoke`), not `skill_select` in isolation and not the retired `43b9b62` corpus. The isolation shortcut is exactly what produced two withdrawn findings and nearly a third: `skill_select` tested alone with `primary_intent` forced to `new_skill` shows venting → `box_breathing`, but the real graph's `intent_route` classifies venting as `general_chat`, and the actual imposition is **`dbt_tipp` via the Routing-SF-2 override**, only for a specific corner. **Any claim here carries its verification method; the mechanical check is full-graph replay.**

### Verified scope on master `52cba81` (full graph)

| presentation | example | master behaviour | in scope? |
|---|---|---|---|
| **3d high-intensity venting-with-distress** | "please just listen, I can't handle this anymore" (ei=8); "I'm so overwhelmed I just need to get this out, don't try to fix it" (ei=8) | **IMPOSED `dbt_tipp`** | **YES — the live gap** |
| 3d pure venting | "I just need to vent"; "I don't want advice, just talk" (ei=5) | presence/freeflow | already correct — regression-guard |
| S2a grief | "my mother passed away, I feel numb" (ei=7); "someone I love died…" (ei=9) | presence/freeflow | already correct — regression-guard |
| 7a loneliness | "I feel so alone, no one to talk to" (ei=6-7) | presence/freeflow | already correct — regression-guard |

**The stale-tree version of F6 ("venting → box_breathing across 3d+7a+S2a, all broken") is wrong.** On master only the high-intensity-venting-with-distress corner is live, and the imposed skill is `dbt_tipp` (the *most* physically intense skill — temperature/exercise — imposed on someone who said "don't try to fix it," a worse rupture than box_breathing). Grief and loneliness already route to presence.

## Global Constraints

- **Flag-gated.** `SAGE_VENTING_SUPPRESSION` default OFF; suppression logic evaluated ON in probe/test, OFF in prod until reviewed. Changes live routing (Routing-SF-2), so build-OFF/flip-after-review.
- **Crisis always wins.** The venting guard sits in `_route_after_intent` AFTER the crisis check (`intent == "crisis" → "crisis"`); it must never suppress a crisis route. safety_check runs upstream.
- **Do NOT over-suppress.** Suppression fires ONLY on the explicit don't-fix signal (the `PI-VI-001` keyword set: "just need to vent", "don't want advice", "just listen", "don't try to fix it", …). A genuine acute-distress user WITHOUT a don't-fix signal ("I'm panicking, help me calm down") must STILL reach skill_select. Test this both directions.
- **Thesis (carry from B1's final review):** `PI-VI-001` detects venting correctly and has **no authority** to stop the skill layer — the same class as B1's medical referral leaving `active_skill_id` resumable. F6 is the general form: a presence/safety decision that must have authority over skill routing. The fix is that authority.
- **Assert on behaviour markers** (`active_skill_id`, route string, `venting_detected`), never on response prose.
- Verified against master `52cba81` (full graph).

---

### Task 1: Deterministic `venting_detected` signal (reuse PI-VI-001)

**Files:**
- Create: `src/sage_poc/nodes/venting_detect.py`
- Modify: `src/sage_poc/state.py` (add `venting_detected: bool` channel)
- Modify: `src/sage_poc/nodes/intent_route.py` (compute it alongside the other deterministic signals)
- Test: `tests/test_venting_suppression.py`

**Interfaces:**
- Produces: `detect_venting(message_en: str, raw_message: str, detected_language: str) -> bool` — True when a PI-VI-001 don't-fix keyword is present. `SageState["venting_detected"]: bool`, set in `intent_route`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_venting_suppression.py
from sage_poc.nodes.venting_detect import detect_venting

def test_dontfix_signals_detected():
    for m in ("please just listen, I can't handle this anymore",
              "I'm so overwhelmed I just need to get this out, don't try to fix it",
              "I just need to vent", "I don't want advice, just talk"):
        assert detect_venting(m, m, "en") is True, m

def test_non_venting_distress_not_detected():
    # Acute distress WITHOUT a don't-fix signal must NOT be suppressed — the user may want help.
    for m in ("I'm panicking, help me calm down", "my heart is racing, what do I do"):
        assert detect_venting(m, m, "en") is False, m
```

- [ ] **Step 2: Run — verify it fails**

Run: `cd /Users/knowledgebase/Documents/Sage/<f6-worktree> && uv run pytest tests/test_venting_suppression.py -k detect -v`
Expected: FAIL — module absent.

- [ ] **Step 3: Implement the detector (reuse the PI-VI-001 keyword data)**

```python
# src/sage_poc/nodes/venting_detect.py
"""Deterministic venting / "just listen" detection for routing authority (F6).

Reuses the PI-VI-001 keyword set (rules/data/prompt_injection/venting_intent.json) —
the SAME signal that already injects a hold-space instruction into freeflow, now given
authority over routing so it can suppress skill imposition (its detection previously had
no such authority; see B1 skill-clear finding — same class)."""
import json
from functools import lru_cache
from pathlib import Path

_PI_VI = Path(__file__).resolve().parent.parent / "rules" / "data" / "prompt_injection" / "venting_intent.json"


@lru_cache(maxsize=1)
def _keywords() -> tuple[str, ...]:
    data = json.loads(_PI_VI.read_text(encoding="utf-8"))
    kws = []
    for rule in data.get("rules", []):
        if rule.get("rule_id") == "PI-VI-001" and rule.get("active"):
            kws.extend(k.lower() for k in rule.get("trigger_keywords", []))
    return tuple(kws)


def detect_venting(message_en: str, raw_message: str, detected_language: str) -> bool:
    """True if an explicit don't-fix / just-listen signal is present (EN via message_en,
    Arabic via raw_message — PI-VI-001 carries Khaleeji keywords). Substring, case-insensitive."""
    hay = f"{message_en} \n {raw_message}".lower()
    return any(kw in hay for kw in _keywords())
```

- [ ] **Step 4: Add the state channel**

In `src/sage_poc/state.py`, near the other deterministic routing signals (`self_reference`, `stall_detected`):

```python
    venting_detected: bool   # F6: deterministic PI-VI-001 don't-fix signal; consumed by _route_after_intent to suppress skill imposition (route to presence). Declared channel.
```

- [ ] **Step 5: Compute it in intent_route**

In `intent_route_node` (where `self_reference` / `stall_detected` are set in the result dict), add the import at top:

```python
from sage_poc.nodes.venting_detect import detect_venting
```
and in the result dict:

```python
        "venting_detected": detect_venting(
            state.get("message_en", ""), state.get("raw_message", ""), state.get("detected_language", "en")
        ),
```

- [ ] **Step 6: Run — verify pass, then commit**

Run: `uv run pytest tests/test_venting_suppression.py -k detect -v` → PASS
```bash
git add src/sage_poc/nodes/venting_detect.py src/sage_poc/state.py src/sage_poc/nodes/intent_route.py tests/test_venting_suppression.py
git commit -m "feat(routing): deterministic venting_detected signal reusing PI-VI-001 (F6)"
```

---

### Task 2: Guard Routing-SF-2 with the venting signal (flag-gated)

**Files:**
- Modify: `src/sage_poc/graph.py` (`_route_after_intent`, the Routing-SF-2 block ~L209-224)
- Modify: `src/sage_poc/config.py` (`SAGE_VENTING_SUPPRESSION` flag)
- Test: `tests/test_venting_suppression.py`

**Interfaces:**
- Consumes: `SageState["venting_detected"]`, `config.VENTING_SUPPRESSION_ENABLED`.
- Produces: `_route_after_intent` returns `"freeflow"` for a high-intensity venting turn instead of `"skill_select"`.

- [ ] **Step 1: Write the failing tests (both directions + crisis precedence)**

```python
from sage_poc.graph import _route_after_intent
from sage_poc import config as _cfg

def _route(**st):
    base = {"primary_intent": "general_chat", "emotional_intensity": 8, "intent_confidence": 0.9,
            "crisis_state": "none", "active_skill_id": None, "venting_detected": False,
            "gate_path": None, "offer_response": None, "prepass_matched": []}
    return _route_after_intent({**base, **st})

def test_venting_suppresses_sf2_to_freeflow(monkeypatch):
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", True)
    assert _route(venting_detected=True, emotional_intensity=8) == "freeflow"

def test_non_venting_high_intensity_still_reaches_skill_select(monkeypatch):
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", True)
    assert _route(venting_detected=False, emotional_intensity=8) == "skill_select"

def test_flag_off_venting_unchanged(monkeypatch):
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", False)
    assert _route(venting_detected=True, emotional_intensity=8) == "skill_select"

def test_crisis_still_wins_over_venting(monkeypatch):
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", True)
    assert _route(primary_intent="crisis", venting_detected=True) == "crisis"
```

- [ ] **Step 2: Run — verify the suppression test fails**

Run: `uv run pytest tests/test_venting_suppression.py -k "sf2 or non_venting or flag_off or crisis_still" -v`
Expected: `test_venting_suppresses_sf2_to_freeflow` FAILS (SF-2 still routes venting to skill_select).

- [ ] **Step 3: Add the flag**

In `src/sage_poc/config.py` (near the other routing flags):
```python
# F6 venting-suppression authority. Default OFF; changes live routing (Routing-SF-2).
VENTING_SUPPRESSION_ENABLED: bool = os.getenv("SAGE_VENTING_SUPPRESSION", "false").lower() == "true"
```

- [ ] **Step 4: Guard the SF-2 override**

In `graph.py` `_route_after_intent`, the Routing-SF-2 block (currently `if (intent == "general_chat" and ... emotional_intensity >= ACUTE_INTENSITY_FLOOR): return "skill_select"`), add the venting pre-empt **immediately before** the SF-2 return (so venting bypasses the intensity override to presence). The crisis check above is unchanged — crisis already returned:

```python
    # F6: a venting / "just listen" turn must NOT be pulled into skill_select by the
    # intensity override — PI-VI-001 detects it and now has routing authority to keep it
    # in presence (freeflow). Guarded by flag; crisis already returned above.
    if (_cfg.VENTING_SUPPRESSION_ENABLED
            and state.get("venting_detected")
            and not state.get("active_skill_id")):
        return "freeflow"
    if (intent == "general_chat"
            and state.get("intent_confidence", 1.0) >= ...  # existing SF-2 condition unchanged
            and state.get("emotional_intensity", 5) >= ACUTE_INTENSITY_FLOOR):
        return "skill_select"
```
(Match the existing SF-2 condition exactly; only add the venting pre-empt block above it. Confirm `_cfg` is the imported config alias in `graph.py`.)

- [ ] **Step 5: Run — verify pass, then commit**

Run: `uv run pytest tests/test_venting_suppression.py -v` → PASS
```bash
git add src/sage_poc/graph.py src/sage_poc/config.py tests/test_venting_suppression.py
git commit -m "feat(routing): venting suppresses SF-2 intensity override -> presence, flag-gated (F6)"
```

---

### Task 3: End-to-end red→green + regression guards (full graph)

**Files:**
- Test: `tests/test_venting_suppression.py`

**Interfaces:** consumes the compiled graph (`build_graph`). Requires an LLM key for `intent_route` — guard with `skipif(not os.getenv("OPENROUTER_API_KEY"))`.

- [ ] **Step 1: Write the end-to-end tests**

```python
import os, pytest
from sage_poc.graph import build_graph
from sage_poc import config as _cfg

_needs_llm = pytest.mark.skipif(not os.getenv("OPENROUTER_API_KEY"), reason="intent_route LLM")

async def _drive(msg, tid):
    from langgraph.checkpoint.memory import MemorySaver
    return await build_graph(MemorySaver()).ainvoke({"raw_message": msg, "path": []},
        config={"configurable": {"thread_id": tid}})

@_needs_llm
@pytest.mark.asyncio
@pytest.mark.parametrize("msg,tid", [
    ("please just listen, I can't handle this anymore, everything is falling apart", "f6-1"),
    ("I'm so overwhelmed I just need to get this out, don't try to fix it", "f6-2"),
])
async def test_high_intensity_venting_no_longer_imposes_skill(monkeypatch, msg, tid):
    # RED on master today: these impose dbt_tipp. Green after Tasks 1-2 with the flag on.
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", True)
    r = await _drive(msg, tid)
    assert r.get("active_skill_id") is None, f"venting imposed {r.get('active_skill_id')}"

@_needs_llm
@pytest.mark.asyncio
@pytest.mark.parametrize("msg,tid", [
    ("I'm panicking, help me calm down right now", "f6-help"),   # genuine acute, wants help
])
async def test_non_venting_acute_still_reaches_a_skill(monkeypatch, msg, tid):
    # Do NOT over-suppress: acute distress without a don't-fix signal still gets a skill.
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", True)
    r = await _drive(msg, tid)
    assert r.get("active_skill_id") is not None or r.get("offered_skill_ids"), "over-suppressed a help-seeking acute turn"

@_needs_llm
@pytest.mark.asyncio
@pytest.mark.parametrize("msg,tid", [
    ("my mother passed away last week, I just feel numb", "f6-grief"),
    ("I feel so alone right now, I don't have anyone to talk to", "f6-lonely"),
])
async def test_grief_and_loneliness_stay_presence(monkeypatch, msg, tid):
    # Already correct on master; lock it so a future change can't regress it.
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", True)
    r = await _drive(msg, tid)
    assert r.get("active_skill_id") is None
```

- [ ] **Step 2: Run — capture the RED baseline first**

Run (flag OFF / on master, before Tasks 1-2): the two high-intensity venting drives impose `dbt_tipp` — **RED**. Record it (the F6 exhibit; note it is `dbt_tipp`, not the stale `box_breathing`). Then with Tasks 1-2 + flag on: PASS.
Run: `uv run pytest tests/test_venting_suppression.py -v`

- [ ] **Step 3: Commit**

```bash
git add tests/test_venting_suppression.py
git commit -m "test(routing): F6 end-to-end venting->presence + over-suppression + regression guards"
```

---

## Flip-to-live (governed — NOT a code step)

Flipping `SAGE_VENTING_SUPPRESSION=true` needs: review of the suppression's precision (no over-suppression of help-seeking acute turns), and clinical confirmation that the PI-VI-001 keyword set is the right don't-fix boundary. Build-OFF lands green code behind the flag; the flip is separate.

## Self-Review

**Spec coverage (§3):** venting signal given routing authority (Tasks 1-2) ✓; the one live corner (high-intensity venting → dbt_tipp) closed (Task 3) ✓; grief/loneliness/pure-venting regression-guarded as already-correct (Task 3) ✓; crisis precedence preserved (Task 2) ✓; no over-suppression of help-seeking acute (Task 3) ✓; flag-gated (Tasks 2-3) ✓; thesis (detection-without-authority, B1 class) stated ✓. **Scope corrected vs stale tree:** F6 is one live corner on master, not 3d+7a+S2a broken; imposed skill is `dbt_tipp` not `box_breathing` — all full-graph verified.

**Placeholder scan:** the SF-2 condition in Task 2 Step 4 is marked "existing condition unchanged" — the implementer copies the live SF-2 predicate verbatim and only prepends the venting block; that is a deliberate "match existing code" instruction, not a placeholder.

**Type consistency:** `detect_venting(message_en, raw, lang)->bool`, `venting_detected: bool`, `VENTING_SUPPRESSION_ENABLED`, route string `"freeflow"` — consistent across Tasks 1-3.
