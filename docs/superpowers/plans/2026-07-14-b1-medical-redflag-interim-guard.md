# B1 — Interim Medical Red-Flag Guard (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a deterministic regex harm-floor that routes verbatim BOT BEHAVIOUR §1 cardiac/stroke red-flag phrasing to a static medical-referral terminal, closing the live gap where "crushing pain… spreading to my jaw" currently routes to `box_breathing`.

**Architecture:** A self-contained regex detector runs inside `safety_check_node`, populating a new `medical_flags` state channel. `_route_after_safety` gains a `medical` branch (precedence: **crisis > medical > safe**) to a new `medical_response` terminal that mirrors `crisis_response` (static text → END, bypasses `output_gate`). Everything is behind `SAGE_MEDICAL_REDFLAG_GUARD`, off by default, flipped only once the must-NOT-fire controls are green.

**Tech Stack:** Python 3.12, LangGraph `StateGraph`, `pytest` (`uv run pytest`), the existing Rules-Service data convention for the clinician-ownable phrase list.

**Parent spec:** `docs/superpowers/specs/2026-07-14-bot-behaviour-routing-conformance-design.md` §2 (item 0) + §8A (red-test seed). **Escalation:** `ESC-2026-07-14-medical-redflag-override-absent`.

## Global Constraints

- **This is an INTERIM harm floor, not the fix.** Poor recall against paraphrase is expected and must be stated as such in code comments — never sold as coverage. It does **not** reduce, defer, or gate-relax the full E3 detector (separate plan, `≥95%` per-class recall on `medical_e3_recall.json`).
- **NOT frozen / additive.** Touches no signed clinical field, does not modify `acute_direct_entry`. Trips no `signed_clinical_fields.json` check. Live-shippable pre-Gitex.
- **Precedence is crisis > medical > safe.** A cardiac red flag that co-occurs with suicidal intent routes to **crisis**, never medical.
- **Trigger set is verbatim BOT BEHAVIOUR §1** (mirrored in `tests/fixtures/bot_behaviour/medical_e3_recall.json` positives). Clinical status: `PENDING Q1-triggers ratification` — ratification, not elicitation.
- **Assert on behaviour markers** (`medical_flags`, route string, `gate_path`), never on response prose.
- **Must-NOT-fire controls** (verbatim §1 negatives) stay on the support path: `racing heart`, `tight chest`, `shallow breath`, `my chest feels a little tight`, `my heart is racing from the panic`. A false medical route is its own harm.
- **Flag default OFF.** `SAGE_MEDICAL_REDFLAG_GUARD=false` until controls pass; flip is a separate governed step.
- Code verified against deploy SHA `113bb09` (files byte-identical at measurement baseline `43b9b62`).

---

### Task 1: Regex detector module + clinician-ownable phrase list

**Files:**
- Create: `src/sage_poc/safety/medical_redflag.py`
- Create: `src/sage_poc/rules/data/safety/medical_redflag_phrases.json`
- Test: `tests/test_medical_redflag_guard.py`

**Interfaces:**
- Produces: `detect_medical_redflag(*texts: str) -> list[str]` — returns ids of matched §1 phrases; `[]` when none. Case-insensitive, verbatim substring.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_medical_redflag_guard.py
from sage_poc.safety.medical_redflag import detect_medical_redflag

def test_cardiac_trace_fires():
    # The live failure trace from the escalation (fixture-aligned phrasing).
    assert detect_medical_redflag("crushing chest pain spreading to my jaw") != []

def test_must_not_fire_controls_stay_clear():
    for benign in ("racing heart", "tight chest", "shallow breath",
                   "my chest feels a little tight", "my heart is racing from the panic"):
        assert detect_medical_redflag(benign) == [], benign
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc-spec-wt && uv run pytest tests/test_medical_redflag_guard.py -v`
Expected: FAIL — `ModuleNotFoundError: sage_poc.safety.medical_redflag`

- [ ] **Step 3: Create the phrase data (verbatim §1)**

```json
// src/sage_poc/rules/data/safety/medical_redflag_phrases.json
{
  "_meta": {
    "source": "BOT BEHAVIOUR §1 universal red-flag override (verbatim); mirrors medical_e3_recall.json positives",
    "status": "INTERIM harm-floor list. Poor paraphrase recall BY DESIGN. Not coverage. Full E3 detector gates on medical_e3_recall.json.",
    "authored_by": "engineering",
    "clinical_signoff": "PENDING — Q1-triggers ratification"
  },
  "phrases": [
    {"id": "chest_pressure", "phrase": "pressure in my chest"},
    {"id": "chest_heavy",    "phrase": "chest feels heavy"},
    {"id": "crushing",       "phrase": "crushing chest pain"},
    {"id": "stabbing",       "phrase": "stabbing chest pain"},
    {"id": "searing",        "phrase": "searing chest pain"},
    {"id": "spread_arm",     "phrase": "spreading to my arm"},
    {"id": "spread_jaw",     "phrase": "spreading to my jaw"},
    {"id": "spread_back",    "phrase": "spreading to my back"},
    {"id": "numb_one_side",  "phrase": "numbness on one side"},
    {"id": "weak_one_side",  "phrase": "weakness on one side"}
  ]
}
```

- [ ] **Step 4: Implement the detector module**

```python
# src/sage_poc/safety/medical_redflag.py
"""Interim medical red-flag pre-screen (B1 harm floor).

STOPGAP, not the fix. Deterministic regex over the verbatim BOT BEHAVIOUR §1
phrase list. Poor recall against paraphrase BY DESIGN — closes the exact-phrase
case the fixtures were written for while the full E3 detector is built to the
>=95% per-class recall gate (medical_e3_recall.json). Do NOT present this as
coverage. It does not reduce or defer B1's real detector.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

_PHRASES_PATH = Path(__file__).resolve().parent.parent / "rules" / "data" / "safety" / "medical_redflag_phrases.json"


@lru_cache(maxsize=1)
def _patterns() -> tuple[tuple[str, "re.Pattern[str]"], ...]:
    data = json.loads(_PHRASES_PATH.read_text(encoding="utf-8"))
    return tuple((p["id"], re.compile(re.escape(p["phrase"]), re.IGNORECASE)) for p in data["phrases"])


def detect_medical_redflag(*texts: str) -> list[str]:
    """Ids of any §1 red-flag phrases present across the given texts. [] = none.
    Verbatim substring, case-insensitive. Paraphrase recall is intentionally weak."""
    hay = " \n ".join(t for t in texts if t)
    return [pid for pid, pat in _patterns() if pat.search(hay)]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_medical_redflag_guard.py -v`
Expected: PASS (both tests)

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/safety/medical_redflag.py src/sage_poc/rules/data/safety/medical_redflag_phrases.json tests/test_medical_redflag_guard.py
git commit -m "feat(safety): interim medical red-flag regex detector (B1 harm floor)"
```

---

### Task 2: Declare the `medical_flags` state channel + `medical` gate_path

**Files:**
- Modify: `src/sage_poc/state.py` (add field near `crisis_flags` L15; extend `gate_path` Literal L91)
- Test: `tests/test_medical_redflag_guard.py`

**Interfaces:**
- Produces: `SageState["medical_flags"]: list[str]`; `gate_path` Literal now includes `"medical"`.

- [ ] **Step 1: Write the failing test**

```python
def test_state_declares_medical_channel():
    from sage_poc.state import SageState
    import typing
    hints = typing.get_type_hints(SageState)
    assert "medical_flags" in hints, "medical_flags must be a declared channel (LangGraph drops undeclared keys)"

def test_gate_path_allows_medical():
    from sage_poc.state import SageState
    import typing
    hints = typing.get_type_hints(SageState)
    assert "medical" in str(hints["gate_path"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_medical_redflag_guard.py -k "state_declares or gate_path_allows" -v`
Expected: FAIL — `medical_flags` absent; `"medical"` not in `gate_path`.

- [ ] **Step 3: Add the field and extend the Literal**

In `src/sage_poc/state.py`, directly below `crisis_flags: list[str]` (L15) add:

```python
    medical_flags: list[str]    # B1/E3: verbatim §1 red-flag phrase ids fired this turn; empty until the interim guard or full detector populates it. Declared channel (LangGraph drops undeclared keys).
```

And change the `gate_path` line (L91) from:

```python
    gate_path: Optional[Literal["standard", "scope_refusal", "jailbreak", "crisis"]]
```

to:

```python
    gate_path: Optional[Literal["standard", "scope_refusal", "jailbreak", "crisis", "medical"]]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_medical_redflag_guard.py -k "state_declares or gate_path_allows" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/state.py tests/test_medical_redflag_guard.py
git commit -m "feat(state): declare medical_flags channel + medical gate_path (B1)"
```

---

### Task 3: Populate `medical_flags` in `safety_check_node`

**Files:**
- Modify: `src/sage_poc/nodes/safety_check.py` (import at top; add key to the return dict at ~L278–296)
- Test: `tests/test_medical_redflag_guard.py`

**Interfaces:**
- Consumes: `detect_medical_redflag` (Task 1), `SageState["medical_flags"]` (Task 2).
- Produces: `safety_check_node` return dict now carries `"medical_flags": list[str]`.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from sage_poc.nodes.safety_check import safety_check_node

def _state(msg: str) -> dict:
    return {"raw_message": msg, "message_en": msg, "detected_language": "en",
            "path": [], "crisis_flags": [], "clinical_flags": [], "crisis_state": "none"}

@pytest.mark.asyncio
async def test_safety_check_sets_medical_flags_on_cardiac():
    out = await safety_check_node(_state("crushing chest pain spreading to my jaw"))
    assert out["medical_flags"], "cardiac red-flag must populate medical_flags"

@pytest.mark.asyncio
async def test_safety_check_no_medical_flag_on_benign():
    out = await safety_check_node(_state("my heart is racing from the panic"))
    assert out["medical_flags"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_medical_redflag_guard.py -k "safety_check_sets or safety_check_no_medical" -v`
Expected: FAIL — `KeyError: 'medical_flags'` (node does not return it yet).

- [ ] **Step 3: Wire the detector into the node**

At the top of `src/sage_poc/nodes/safety_check.py` (with the other `from sage_poc...` imports, ~L28), add:

```python
from sage_poc.safety.medical_redflag import detect_medical_redflag
```

Immediately before the `return {` dict at the end of `safety_check_node` (~L278), add:

```python
    medical_flags = detect_medical_redflag(state.get("message_en", ""), state.get("raw_message", ""))
```

Then add this key inside the returned dict (alongside `"crisis_flags": new_crisis_flags,`):

```python
        "medical_flags": medical_flags,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_medical_redflag_guard.py -k "safety_check_sets or safety_check_no_medical" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/nodes/safety_check.py tests/test_medical_redflag_guard.py
git commit -m "feat(safety): populate medical_flags from the interim red-flag detector (B1)"
```

---

### Task 4: The `medical_response` terminal node

**Files:**
- Create: `src/sage_poc/nodes/medical_response.py`
- Modify: `src/sage_poc/config.py` (add referral text + terminal target, ~L240)
- Test: `tests/test_medical_redflag_guard.py`

**Interfaces:**
- Produces: `medical_response_node(state: SageState) -> dict` returning `response`/`response_en`, `gate_path="medical"`, appended `path`, `latency_ms` (crisis-node parity — it also bypasses `output_gate`).

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_medical_response_returns_referral_and_gate_path():
    from sage_poc.nodes.medical_response import medical_response_node
    out = await medical_response_node(_state("crushing chest pain spreading to my jaw") | {"medical_flags": ["crushing"]})
    assert out["gate_path"] == "medical"
    assert out["response"] and "medical" in out["response"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_medical_redflag_guard.py -k "medical_response_returns" -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Add config (referral text + terminal target — Q1-terminal default per doc L1477)**

In `src/sage_poc/config.py` (near the other feature flags, ~L240):

```python
# B1 interim medical red-flag guard. Default OFF; flip only when the must-NOT-fire
# controls are green (see plan Task 6). Not frozen; touches no signed field.
MEDICAL_REDFLAG_GUARD_ENABLED: bool = os.getenv("SAGE_MEDICAL_REDFLAG_GUARD", "false").lower() == "true"

# Q1-terminal default (doc L1477): lead with in-person/medical evaluation; 999/ER as escalation.
# Single blocking parameter — stubbed here pending clinician ratification.
MEDICAL_REFERRAL_TEXT: str = os.getenv(
    "SAGE_MEDICAL_REFERRAL_TEXT",
    "The symptoms you're describing can be signs of a medical emergency. "
    "Please seek in-person medical evaluation now — call your local emergency number "
    "(999 in the UAE) or go to the nearest emergency department. I'm not able to assess "
    "physical symptoms, and this needs a medical professional right away.",
)
```

- [ ] **Step 4: Implement the terminal node**

```python
# src/sage_poc/nodes/medical_response.py
"""B1 medical red-flag terminal. Mirrors crisis_response: static referral text -> END,
bypassing output_gate. Interim target per doc L1477 (Q1-terminal stub)."""
from sage_poc.state import SageState
from sage_poc import config as _cfg
from sage_poc.observability import stage_timer


async def medical_response_node(state: SageState) -> dict:
    with stage_timer() as t:
        text = _cfg.MEDICAL_REFERRAL_TEXT
    return {
        "response": text,
        "response_en": text,
        "gate_path": "medical",
        "medical_flags": state.get("medical_flags", []),
        "path": state["path"] + ["medical_response"],
        "latency_ms": t.ms,  # crisis-node parity: this path bypasses output_gate's latency stamp
    }
```

> If `stage_timer()`/`t.ms` differs from the `_crisis_response_node` idiom in `graph.py`, mirror that node's exact latency-stamp call instead — the requirement is only that `latency_ms` is stamped here (crisis turns had `latency_ms=NULL` until stamped; do not repeat that gap).

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_medical_redflag_guard.py -k "medical_response_returns" -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/nodes/medical_response.py src/sage_poc/config.py tests/test_medical_redflag_guard.py
git commit -m "feat(safety): medical_response terminal node + referral config (B1)"
```

---

### Task 5: Wire the live route — crisis > medical > safe, flag-gated

**Files:**
- Modify: `src/sage_poc/graph.py` (`_route_after_safety` L156–170; `build_graph` node + edges L297–316)
- Test: `tests/test_medical_redflag_guard.py`

**Interfaces:**
- Consumes: `SageState["medical_flags"]`, `config.MEDICAL_REDFLAG_GUARD_ENABLED`, `medical_response_node`.
- Produces: `_route_after_safety` may return `"medical"`; graph has a `medical_response` node → `END`.

- [ ] **Step 1: Write the failing tests**

```python
from sage_poc.graph import _route_after_safety
from sage_poc import config as _cfg

def _routed(**st) -> str:
    base = {"is_safe": True, "crisis_state": "none", "medical_flags": [], "crisis_tier": None}
    return _route_after_safety(base | st)

def test_cardiac_routes_medical_when_enabled(monkeypatch):
    monkeypatch.setattr(_cfg, "MEDICAL_REDFLAG_GUARD_ENABLED", True)
    assert _routed(is_safe=True, medical_flags=["crushing"]) == "medical"

def test_crisis_wins_over_medical(monkeypatch):
    monkeypatch.setattr(_cfg, "MEDICAL_REDFLAG_GUARD_ENABLED", True)
    # SI + cardiac in the same turn: crisis takes precedence, never medical.
    assert _routed(is_safe=False, medical_flags=["crushing"]) == "crisis"

def test_medical_route_off_by_default(monkeypatch):
    monkeypatch.setattr(_cfg, "MEDICAL_REDFLAG_GUARD_ENABLED", False)
    assert _routed(is_safe=True, medical_flags=["crushing"]) == "safe"

def test_benign_stays_safe(monkeypatch):
    monkeypatch.setattr(_cfg, "MEDICAL_REDFLAG_GUARD_ENABLED", True)
    assert _routed(is_safe=True, medical_flags=[]) == "safe"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_medical_redflag_guard.py -k "routes_medical or crisis_wins or route_off or benign_stays" -v`
Expected: FAIL — `_route_after_safety` never returns `"medical"`.

- [ ] **Step 3: Extend `_route_after_safety` (crisis first, then medical, then safe)**

Replace the final line of `_route_after_safety` (L170):

```python
    return "safe" if state["is_safe"] else "crisis"
```

with:

```python
    if not state["is_safe"]:
        return "crisis"
    if _cfg.MEDICAL_REDFLAG_GUARD_ENABLED and state.get("medical_flags"):
        return "medical"
    return "safe"
```

(Confirm `_cfg` is the module alias already imported in `graph.py`; the existing `_cfg.CRISIS_TIERING_ENABLED` reference at L168 shows it is.)

- [ ] **Step 4: Register the node + edges in `build_graph`**

Add the import near the other node imports at the top of `graph.py`:

```python
from sage_poc.nodes.medical_response import medical_response_node
```

In `build_graph`, beside `graph.add_node("crisis_response", _crisis_response_node)` (L308):

```python
    graph.add_node("medical_response", medical_response_node)
```

Extend the `safety_check` conditional-edges map (L312–315) to include the medical branch:

```python
    graph.add_conditional_edges("safety_check", _route_after_safety, {
        "safe": "intent_route",
        "crisis": "crisis_response",
        "medical": "medical_response",
    })
    graph.add_edge("medical_response", END)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_medical_redflag_guard.py -v`
Expected: PASS (all tests, including Tasks 1–4)

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/graph.py tests/test_medical_redflag_guard.py
git commit -m "feat(graph): wire medical red-flag route (crisis>medical>safe), flag-gated (B1)"
```

---

### Task 6: End-to-end red→green trace + flip-control gate + honesty record

**Files:**
- Test: `tests/test_medical_redflag_guard.py` (add the end-to-end drive + the flip-control assertion)
- Modify: `src/sage_poc/rules/data/safety/medical_redflag_phrases.json` (`_meta` honesty note already present — verify)

**Interfaces:**
- Consumes: the compiled graph (`build_graph`), all prior tasks.

- [ ] **Step 1: Write the end-to-end test (the escalation's record)**

```python
@pytest.mark.asyncio
async def test_end_to_end_cardiac_no_longer_reaches_a_skill(monkeypatch):
    monkeypatch.setattr(_cfg, "MEDICAL_REDFLAG_GUARD_ENABLED", True)
    from sage_poc.graph import build_graph
    app = build_graph()
    result = await app.ainvoke(
        {"raw_message": "crushing chest pain spreading to my jaw", "path": []},
        config={"configurable": {"thread_id": "b1-e2e"}},
    )
    assert result.get("gate_path") == "medical"
    assert "medical_response" in result.get("path", [])
    assert result.get("active_skill_id") is None  # never absorbed into box_breathing/grounding

@pytest.mark.asyncio
async def test_flip_control_benign_panic_stays_on_support_path(monkeypatch):
    monkeypatch.setattr(_cfg, "MEDICAL_REDFLAG_GUARD_ENABLED", True)
    from sage_poc.graph import build_graph
    app = build_graph()
    result = await app.ainvoke(
        {"raw_message": "my heart is racing from the panic", "path": []},
        config={"configurable": {"thread_id": "b1-benign"}},
    )
    assert result.get("gate_path") != "medical"
    assert "medical_response" not in result.get("path", [])
```

- [ ] **Step 2: Run — the cardiac test is the red baseline**

Run: `uv run pytest tests/test_medical_redflag_guard.py -k "end_to_end or flip_control" -v`
Expected on deploy SHA **before** Tasks 1–5: the cardiac drive routes to a skill (RED). After Tasks 1–5 with the flag on: PASS. Record the pre-fix red run in the escalation as the live-failure exhibit.

- [ ] **Step 3: Verify the honesty note is in the shipped artifact**

Confirm `medical_redflag_phrases.json._meta.status` still reads *"INTERIM harm-floor list. Poor paraphrase recall BY DESIGN. Not coverage. Full E3 detector gates on medical_e3_recall.json."* This sentence is a required deliverable — it prevents the mitigation being mistaken for the fix.

- [ ] **Step 4: Run the full file + confirm no regression in existing safety tests**

Run: `uv run pytest tests/test_medical_redflag_guard.py tests/test_routing.py tests/test_safety_precedence.py -v`
Expected: PASS (existing routing/precedence unaffected; medical is additive).

- [ ] **Step 5: Commit**

```bash
git add tests/test_medical_redflag_guard.py
git commit -m "test(safety): end-to-end cardiac red->green trace + benign flip-control (B1)"
```

---

## Flip-to-live (post-plan, governed — NOT a code step)

Once Task 6 is green and the must-NOT-fire controls hold, flipping `SAGE_MEDICAL_REDFLAG_GUARD=true` in prod is the go-live. It is not frozen and needs no clinical re-sign of `acute_direct_entry`, but the **Q1-terminal** value (`SAGE_MEDICAL_REFERRAL_TEXT`) should carry clinician ratification before flip, and the full E3 detector remains the real deliverable this interim does not replace.

---

## Self-Review

**Spec coverage (§2):** interim regex guard (Tasks 1–5) ✓; verbatim §1 triggers + must-not-fire negatives (Tasks 1, 6) ✓; live route because the precedence framework is inert (Tasks 4–5) ✓; crisis>medical precedence (Task 5) ✓; Q1-terminal stub/default (Task 4) ✓; honesty clause (Tasks 1, 6) ✓; flag-gated, not-frozen (Tasks 4–6) ✓; red test = live failure trace (Task 6) ✓. **Out of scope by design (own plans):** full E3 detector to ≥95% per-class gate; `fired_safety_routes` never-dropped audit completeness for medical (the full precedence wiring); AR phrasing.

**Placeholder scan:** none — every step carries the file, code, command, and expected output.

**Type consistency:** `detect_medical_redflag(*texts)->list[str]`, `medical_flags: list[str]`, `gate_path` Literal incl. `"medical"`, route string `"medical"`, node `medical_response_node`, flag `MEDICAL_REDFLAG_GUARD_ENABLED` — used identically across Tasks 1–6.
