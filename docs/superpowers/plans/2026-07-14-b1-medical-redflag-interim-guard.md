# B1 — Interim Medical Red-Flag Guard (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a deterministic regex harm-floor that routes cardiac/stroke red-flag phrasing to a static medical-referral terminal, closing the live gap where the escalation trace — *"crushing pain in my chest spreading to my jaw, my left arm's gone numb"* — and its jaw-less variant currently route to `box_breathing`.

**Architecture:** A self-contained regex/literal detector runs inside `safety_check_node`, populating a new `medical_flags` state channel. `_route_after_safety` gains a `medical` branch (precedence: **crisis > medical > safe**) to a new `medical_response` terminal that goes straight to END. It bypasses `output_gate` (like `crisis_response`) **but writes its own `write_session_audit` record** — it must not inherit the crisis node's audit gap. Everything is behind `SAGE_MEDICAL_REDFLAG_GUARD`, off by default, flipped only once the must-NOT-fire controls are green.

**Tech Stack:** Python 3.12, LangGraph `StateGraph`, `pytest` (`uv run pytest`), the existing Rules-Service data convention for the clinician-ownable phrase list.

**Parent spec:** `docs/superpowers/specs/2026-07-14-bot-behaviour-routing-conformance-design.md` §2 (item 0) + §8A (red-test seed). **Escalation:** `ESC-2026-07-14-medical-redflag-override-absent`.

## Global Constraints

- **This is an INTERIM harm floor, not the fix.** Poor recall against paraphrase is expected and must be stated as such in code comments — never sold as coverage. It does **not** reduce, defer, or gate-relax the full E3 detector (separate plan, `≥95%` per-class recall on `medical_e3_recall.json`).
- **NOT frozen / additive.** Touches no signed clinical field, does not modify `acute_direct_entry`. Trips no `signed_clinical_fields.json` check. Live-shippable pre-Gitex.
- **Precedence is crisis > medical > safe.** A cardiac red flag that co-occurs with suicidal intent routes to **crisis**, never medical.
- **Q1-triggers is now two parts (governance shape changed by the Defect-1 fix):** (a) **ratify** the verbatim BOT BEHAVIOUR §1 list (mirrored in `medical_e3_recall.json` positives) — a ratification; (b) **approve or amend** the two engineering-authored variants `crushing_variant` and `one_sided_numb`, added because the verbatim §1 list does not fire on the real trace — these are engineering's clinical judgment about what a cardiac/stroke presentation looks like and must be **signed, not assumed** (an elicitation). Status: `PENDING Q1-triggers (a)+(b)`.
- **Assert on behaviour markers** (`medical_flags`, route string, `gate_path`), never on response prose.
- **Must-NOT-fire controls** stay on the support path — panic negatives AND benign-numbness negatives: `racing heart`, `tight chest`, `shallow breath`, `my chest feels a little tight`, `my heart is racing from the panic`, `my foot's gone numb from sitting`, `my hand went numb from sleeping on it`, `my leg's gone numb from sitting cross-legged`. A false medical route (a dead leg sent to the ER) is its own harm; benign limb-numbness without laterality must not fire.
- **The red test is the verbatim escalation trace, never a phrasing adjusted to fit the list.** Both the full trace and its jaw-less variant must fire; if the jaw-less variant does not, the phrase list is wrong — extend the list (word-order/proximity variants), never narrow the test. (This defect was caught in review: the first draft fitted the test to the regex.)
- **Arabic coverage is not native.** The detector is English-only. Arabic input rides the EN path **solely** via the upstream machine translation `raw → message_en` in `safety_check` (L90-93); there is no Arabic phrase list, and verbatim-English-against-machine-translation recall is **unvalidated and expected near-zero for colloquial Gulf**. This exact claim ships in `_meta`, the module docstring, and the escalation — "we don't know" is not acceptable in a safety artifact.
- **The medical terminal writes its own audit record** (`write_session_audit`): path, `medical_flags`, matched phrase ids, flag state, latency. It must not inherit the crisis node's bypass-and-under-audit gap.
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

# The VERBATIM escalation trace. Do not adjust this string to fit the phrase list.
LIVE_TRACE = "crushing pain in my chest spreading to my jaw, my left arm's gone numb"
# The same presentation with the one clause that trivially matched removed. A textbook
# cardiac presentation phrased the way people actually phrase it — MUST still fire.
JAWLESS_VARIANT = "crushing pain in my chest, my left arm's gone numb"

def test_live_trace_fires():
    assert detect_medical_redflag(LIVE_TRACE) != []

def test_jawless_variant_fires():
    # If this fails, the phrase list is wrong — extend it (word-order/proximity
    # variants), never narrow this test.
    assert detect_medical_redflag(JAWLESS_VARIANT) != []

def test_must_not_fire_controls_stay_clear():
    # Panic negatives AND benign-numbness negatives. Benign limb-numbness (no
    # laterality) must NOT route to a medical emergency — §1's criterion is one-sided.
    for benign in ("racing heart", "tight chest", "shallow breath",
                   "my chest feels a little tight", "my heart is racing from the panic",
                   "my foot's gone numb from sitting",
                   "my hand went numb from sleeping on it",
                   "my leg's gone numb from sitting cross-legged"):
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
    "source": "BOT BEHAVIOUR §1 universal red-flag override (verbatim §1 positives from medical_e3_recall.json) + word-order/proximity variants required to fire the verbatim escalation trace and its jaw-less form",
    "status": "INTERIM harm-floor list. Poor paraphrase recall BY DESIGN. Not coverage. Full E3 detector gates on medical_e3_recall.json.",
    "arabic": "ZERO native Arabic coverage. English-only. Arabic input rides the EN path solely via upstream machine translation (safety_check L90-93); AR recall is unvalidated and expected near-zero for colloquial Gulf. NOT covered.",
    "authored_by": "engineering",
    "clinical_signoff": "PENDING — Q1-triggers ratification",
    "match_field": "entries default to literal (re.escape) substring; entries with match:\"regex\" are compiled as regex."
  },
  "phrases": [
    {"id": "chest_pressure",   "phrase": "pressure in my chest"},
    {"id": "chest_heavy",      "phrase": "chest feels heavy"},
    {"id": "crushing",         "phrase": "crushing chest pain"},
    {"id": "crushing_variant", "phrase": "crushing pain in (my |the )?chest", "match": "regex"},
    {"id": "stabbing",         "phrase": "stabbing chest pain"},
    {"id": "searing",          "phrase": "searing chest pain"},
    {"id": "spread_arm",       "phrase": "spreading to my arm"},
    {"id": "spread_jaw",       "phrase": "spreading to my jaw"},
    {"id": "spread_back",      "phrase": "spreading to my back"},
    {"id": "numb_one_side",    "phrase": "numbness on one side"},
    {"id": "weak_one_side",    "phrase": "weakness on one side"},
    {"id": "one_sided_numb",   "phrase": "(left|right) (arm|hand|side|face|leg|foot)[^.,;]{0,20}(gone |went )?numb", "match": "regex"}
  ]
}
```

> **Why the two variants exist (do not delete them), and why `one_sided_numb` is laterality-bound:** the verbatim §1 list alone fails the real trace — `"crushing pain in my chest"` is not a substring of `"crushing chest pain"` (word order), and `"my left arm's gone numb"` is not `"numbness on one side"`. `crushing_variant` and `one_sided_numb` are the minimum engineering-authored additions that fire both the full trace and the jaw-less variant. **`one_sided_numb` is deliberately bound to laterality (`left|right … numb`) because §1's actual criterion is *one-sided* numbness.** An earlier draft used a bare `gone_numb` literal — it fired on `"my foot's gone numb from sitting"`, routing a dead leg to the ER (caught in review; pattern-vs-criterion drift, widening). These two variants are **engineering's clinical judgment, not §1 verbatim** — they are Q1-triggers part (b), an elicitation requiring sign-off. Verify against the benign-numbness AND panic must-NOT-fire controls after any edit.

- [ ] **Step 4: Implement the detector module**

```python
# src/sage_poc/safety/medical_redflag.py
"""Interim medical red-flag pre-screen (B1 harm floor).

STOPGAP, not the fix. Deterministic literal/regex match over the BOT BEHAVIOUR §1
phrase list. Poor recall against paraphrase BY DESIGN — closes the exact-phrase
and near-phrase case the fixtures were written for while the full E3 detector is
built to the >=95% per-class recall gate (medical_e3_recall.json). Do NOT present
this as coverage. It does not reduce or defer B1's real detector.

ARABIC: ZERO native coverage. This matcher is English-only. Arabic input reaches it
ONLY as the upstream machine translation raw->message_en produced in safety_check
(L90-93); there is no Arabic phrase list, and verbatim-English against a machine
translation of colloquial Gulf is unvalidated and expected near-zero. AR is NOT
covered by this guard.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

_PHRASES_PATH = Path(__file__).resolve().parent.parent / "rules" / "data" / "safety" / "medical_redflag_phrases.json"


@lru_cache(maxsize=1)
def _patterns() -> tuple[tuple[str, "re.Pattern[str]"], ...]:
    data = json.loads(_PHRASES_PATH.read_text(encoding="utf-8"))
    out = []
    for p in data["phrases"]:
        expr = p["phrase"] if p.get("match") == "regex" else re.escape(p["phrase"])
        out.append((p["id"], re.compile(expr, re.IGNORECASE)))
    return tuple(out)


def detect_medical_redflag(*texts: str) -> list[str]:
    """Ids of any §1 red-flag phrases present across the given texts. [] = none.
    Case-insensitive; entries are literal substrings unless flagged match:"regex".
    English-only; paraphrase and Arabic recall are intentionally weak/absent."""
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
    out = await medical_response_node(_state("x") | {"medical_flags": ["crushing"]})
    assert out["gate_path"] == "medical"
    assert out["response"] and "medical" in out["response"].lower()

@pytest.mark.asyncio
async def test_medical_response_writes_its_own_audit(monkeypatch):
    # Defect 3: this path bypasses output_gate, so it MUST write its own audit.
    import asyncio
    import sage_poc.nodes.medical_response as mr
    captured = {}
    async def _fake_audit(rec): captured.update(rec)
    monkeypatch.setattr(mr, "write_session_audit", _fake_audit)
    await mr.medical_response_node(_state("x") | {"medical_flags": ["crushing"]})
    await asyncio.sleep(0)  # let the fire-and-forget audit task run
    assert captured.get("gate_path") == "medical"
    assert captured.get("medical_flags") == ["crushing"]
    assert "latency_ms" in captured and "path" in captured
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
"""B1 medical red-flag terminal: static referral text -> END, bypassing output_gate.
UNLIKE crisis_response's historical gap, it writes its OWN session audit record — a
medical-emergency turn is the most consequential the system emits and must be fully
traceable (path, flags, matched phrase ids, latency). Interim target per doc L1477
(Q1-terminal stub)."""
import asyncio
import logging
import time
from sage_poc.state import SageState
from sage_poc import config as _cfg
from sage_poc.audit import write_session_audit

_log = logging.getLogger(__name__)


async def medical_response_node(state: SageState) -> dict:
    _t0 = time.monotonic()
    text = _cfg.MEDICAL_REFERRAL_TEXT
    latency_ms = int((time.monotonic() - _t0) * 1000)
    medical_flags = state.get("medical_flags", [])
    path = state["path"] + ["medical_response"]

    # Explicit audit: output_gate (the normal audit-write point) is bypassed on this
    # path, so without this the single most consequential turn is unrecorded. Fire-and-
    # forget, mirroring crisis_response's task pattern — but here it is NOT optional.
    _audit_task = asyncio.create_task(write_session_audit({
        "session_id": state.get("session_id"),
        "user_id": state.get("user_id"),
        "gate_path": "medical",
        "path": path,
        "medical_flags": medical_flags,
        "crisis_flags": state.get("crisis_flags", []),
        "response_text": text,
        "latency_ms": latency_ms,
    }))
    _audit_task.add_done_callback(
        lambda tk: _log.warning("[medical_response] session audit error: %s", tk.exception())
        if not tk.cancelled() and tk.exception() else None
    )

    return {
        "response": text,
        "response_en": text,
        "gate_path": "medical",
        "medical_flags": medical_flags,
        "path": path,
        "latency_ms": latency_ms,
    }
```

> Reconcile the audit dict keys with `sage_poc.audit.write_session_audit`'s actual signature (see its call in `_crisis_response_node`, `graph.py:70`). The **requirement** is that a medical turn produces a traceable record carrying `gate_path="medical"`, `medical_flags`, `path`, and `latency_ms`; match the audit schema's field names exactly so the row is not silently dropped.

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
import pytest
from sage_poc import config as _cfg

@pytest.mark.parametrize("trace,tid", [
    ("crushing pain in my chest spreading to my jaw, my left arm's gone numb", "b1-e2e-full"),
    ("crushing pain in my chest, my left arm's gone numb", "b1-e2e-jawless"),  # jaw clause removed
])
@pytest.mark.asyncio
async def test_end_to_end_cardiac_no_longer_reaches_a_skill(monkeypatch, trace, tid):
    monkeypatch.setattr(_cfg, "MEDICAL_REDFLAG_GUARD_ENABLED", True)
    from sage_poc.graph import build_graph
    app = build_graph()
    result = await app.ainvoke(
        {"raw_message": trace, "path": []},
        config={"configurable": {"thread_id": tid}},
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

- [ ] **Step 3: Verify BOTH honesty notes are in the shipped artifacts**

Confirm two claims ship verbatim (each is a required deliverable — they prevent the mitigation being mistaken for the fix):
1. `_meta.status` (and the module docstring): *"INTERIM harm-floor list. Poor paraphrase recall BY DESIGN. Not coverage. Full E3 detector gates on medical_e3_recall.json."*
2. `_meta.arabic` (and the module docstring): *"ZERO native Arabic coverage… Arabic input rides the EN path solely via upstream machine translation… unvalidated and expected near-zero… NOT covered."*

Add an assertion so this can't silently regress:

```python
def test_honesty_notes_ship_verbatim():
    import json
    from pathlib import Path
    import sage_poc.safety.medical_redflag as mr
    meta = json.loads(Path(mr._PHRASES_PATH).read_text())["_meta"]
    assert "Not coverage" in meta["status"]
    assert "ZERO native Arabic" in meta["arabic"]
    assert "Arabic" in mr.__doc__ and "ZERO native coverage" in mr.__doc__
```

The Arabic claim also goes into the escalation record (command session owns that write).

- [ ] **Step 4: Run the full file + confirm no regression in existing safety tests**

Run: `uv run pytest tests/test_medical_redflag_guard.py tests/test_routing.py tests/test_safety_precedence.py -v`
Expected: PASS (existing routing/precedence unaffected; medical is additive).

- [ ] **Step 5: Commit**

```bash
git add tests/test_medical_redflag_guard.py
git commit -m "test(safety): end-to-end cardiac red->green trace + benign flip-control (B1)"
```

---

## Accepted interim debt (record, do not fix here)

This plan wires a **parallel medical route in `graph.py`** rather than reviving the existing but inert `safety_precedence.py` framework (`SAFETY_ROUTE_ORDER`, `_medical_fired`, `SAGE_ROUTE_PRECEDENCE`). That is the correct call for an interim — the framework is dead code and reviving it is B1-full's job — but it means **two precedence mechanisms now coexist**: the live `_route_after_safety` branch here, and the inert framework. 

**Retirement condition (named so B1-full converges rather than forks):** when B1-full lands, medical routing moves onto the `safety_precedence` framework (its detector populates `medical_flags`; `SAGE_ROUTE_PRECEDENCE` consumes the winner and records `fired_safety_routes` per the §4.5 never-dropped rule), and the parallel `_route_after_safety` medical branch added in Task 5 is **removed**. Until then, the interim branch is the single source of medical routing and the framework stays inert. Do not wire both live at once.

## Flip-to-live (post-plan, governed — NOT a code step)

Once Task 6 is green and the must-NOT-fire controls hold, flipping `SAGE_MEDICAL_REDFLAG_GUARD=true` in prod is the go-live. It is not frozen and needs no clinical re-sign of `acute_direct_entry`, but the **Q1-terminal** value (`SAGE_MEDICAL_REFERRAL_TEXT`) should carry clinician ratification before flip, and the full E3 detector remains the real deliverable this interim does not replace.

---

## Self-Review

**Spec coverage (§2):** interim regex/literal guard (Tasks 1–5) ✓; verbatim §1 triggers + word-order variants + must-not-fire negatives (Tasks 1, 6) ✓; live route because the precedence framework is inert (Tasks 4–5) ✓; crisis>medical precedence (Task 5) ✓; Q1-terminal stub/default (Task 4) ✓; harm-floor + **Arabic-zero** honesty clauses shipped and test-guarded (Tasks 1, 6) ✓; explicit medical-turn audit (Task 4, Defect 3) ✓; flag-gated, not-frozen (Tasks 4–6) ✓; **red test = verbatim escalation trace + jaw-less variant** (Tasks 1, 6, Defect 1) ✓.

**Arabic (stated, not buried):** the guard is English-only; AR reaches it solely via upstream machine translation (`safety_check` L90-93), unvalidated and near-zero — shipped verbatim in `_meta.arabic`, the module docstring, and the escalation. This is a **named live gap the full E3 detector must close with a native AR path**, not an out-of-scope item.

**Out of scope by design (own plans):** full E3 detector to ≥95% per-class gate + native AR; the `safety_precedence` framework revival + `fired_safety_routes` never-dropped completeness (see Accepted interim debt).

**Placeholder scan:** none — every step carries the file, code, command, and expected output.

**Type consistency:** `detect_medical_redflag(*texts)->list[str]`, `medical_flags: list[str]`, `gate_path` Literal incl. `"medical"`, route string `"medical"`, node `medical_response_node`, flag `MEDICAL_REDFLAG_GUARD_ENABLED` — used identically across Tasks 1–6.
