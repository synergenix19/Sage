# Group 1: Crisis & Skill State Ferry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the crisis state ferry and skill session continuity across the HTTP API boundary — fixing the broken pipeline that spans INT-C1, INT-C2, BE-C1, BE-C5, and BE-C2 as one atomic change.

**Architecture:** The HTTP path `sage-poc → route.ts → browser → route.ts → sage-poc` currently drops all session state at both proxy hops. Each fix is meaningless without the others: sage-poc must accept ferried state from the client, route.ts must pass it through in both directions, and the browser must read and re-send it. These eight tasks form a single end-to-end pipeline and must all land together.

The Next.js `route.ts` is a deliberate security boundary, not a thin pass-through. It is the only component that holds `SAGE_API_URL` (kept server-side, never exposed to the browser), performs Supabase persistence, and will carry auth checks (Group 2). All sage-poc calls originate from the Next.js server process — CORS headers on sage-poc are irrelevant to this call path.

**Distress trajectory (POC stopgap note):** `distress_trajectory` is ferried client-side in this plan because there is no server-side session store in the POC. `safety_check.py:_update_distress_trajectory()` reads and appends to this list every turn to detect escalating distress across three consecutive turns (clinical flag `escalating_distress`). Ferrying it is correct for the POC. In the v7 full build, trajectory must migrate to Cosmos DB / LangGraph checkpointing — at that point the client-ferry field becomes redundant and should be removed.

**Tech Stack:** Python 3.12 / FastAPI / Pydantic v2 (sage-poc) · Next.js 14 App Router / TypeScript / Vitest (cdai)

---

## Files Modified

| File | Change |
|------|--------|
| `sage-poc/src/sage_poc/skill_ids.py` | **Create** — lightweight SKILL_REGISTRY list, no heavy imports |
| `sage-poc/src/sage_poc/nodes/skill_select.py` | Import SKILL_REGISTRY from `skill_ids` instead of defining it inline |
| `sage-poc/src/sage_poc/state.py` | Add `cultural_output_violations: list[str]` field |
| `sage-poc/server.py` | Add `"resolved"` to `_VALID_CRISIS_STATES`; import SKILL_REGISTRY from `skill_ids`; extend `ChatRequest` with 4 new optional fields; update `_build_state` to use them; add 2 new response headers |
| `sage-poc/tests/test_skill_ids.py` | **Create** — tests for the new skill_ids module |
| `sage-poc/tests/test_state.py` | Add test for `cultural_output_violations` in TypedDict |
| `sage-poc/tests/test_graph.py` | Add `cultural_output_violations` to `make_e2e_state` |
| `sage-poc/tests/test_server.py` | Add tests for "resolved" not coerced; skill fields passed through; crisis and skill state preserved in 2-turn sequences |
| `cdai/apps/web/app/api/chat/route.ts` | Destructure 5 new fields from request; forward them to sage-poc; forward 5 response headers back to browser |
| `cdai/apps/web/app/api/chat/__tests__/route.test.ts` | Add tests for crisis state and skill state forwarding in both directions |
| `cdai/apps/web/components/chat/chat-interface.tsx` | Replace 4 ferry `useState` vars with `useRef`; read 5 response headers; include all ref values in request body; reduce `useCallback` deps to `[sessionId]` |

---

## Task 1: Add `cultural_output_violations` to `SageState` (BE-C2)

**Why first:** `output_gate_node` already writes this key. If the LangGraph schema validates the TypedDict strictly, every turn that fires a cultural rule causes a runtime crash. Fixing the schema before touching anything else prevents phantom failures from masking later test runs.

**Files:**
- Modify: `sage-poc/src/sage_poc/state.py`
- Modify: `sage-poc/tests/test_state.py`
- Modify: `sage-poc/tests/test_graph.py`

- [ ] **Step 1.1: Write the failing test — `cultural_output_violations` must be in `SageState` TypedDict hints**

```python
# In sage-poc/tests/test_state.py, add after test_state_has_crisis_state_not_legacy_bool:

def test_state_has_cultural_output_violations():
    import typing
    hints = typing.get_type_hints(SageState)
    assert "cultural_output_violations" in hints, (
        "SageState must declare cultural_output_violations — "
        "output_gate_node writes this key but it was absent from the schema"
    )
```

- [ ] **Step 1.2: Run to confirm it fails**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
source .venv/bin/activate
pytest tests/test_state.py::test_state_has_cultural_output_violations -v
```

Expected output: `FAILED tests/test_state.py::test_state_has_cultural_output_violations`

- [ ] **Step 1.3: Add field to `SageState`**

In `sage-poc/src/sage_poc/state.py`, add one line after the `escalation_triggered` field (line 38):

```python
    escalation_triggered: Optional[dict]  # {"level": "L1"|"L2", "reason": str, "action": str}

    cultural_output_violations: list[str]  # rule_ids fired in output_gate cultural check

    gate_path: Optional[Literal["standard", "scope_refusal", "jailbreak", "crisis"]]
```

- [ ] **Step 1.4: Run to confirm test passes**

```bash
pytest tests/test_state.py::test_state_has_cultural_output_violations -v
```

Expected: `PASSED`

- [ ] **Step 1.5: Update `make_e2e_state` in `test_graph.py`**

In `sage-poc/tests/test_graph.py`, add `cultural_output_violations` to the `base` dict in `make_e2e_state`. Insert after the `semantic_score` entry (line 43):

```python
        "skill_match_method": None,
        "semantic_score": None,
        "cultural_output_violations": [],
    }
```

- [ ] **Step 1.6: Update `test_state_has_required_fields` in `test_state.py`**

In the existing `test_state_has_required_fields` test, add `"cultural_output_violations": []` to the `state` dict (insert before the final `assert`):

```python
        "skill_match_method": None,
        "semantic_score": None,
        "cultural_output_violations": [],
    }
    assert state["raw_message"] == "hello"
    assert state["crisis_state"] == "none"
    assert state["cultural_output_violations"] == []
```

Also update `test_state_path_is_list` the same way — add `"cultural_output_violations": []` to that state dict.

- [ ] **Step 1.7: Run all state tests**

```bash
pytest tests/test_state.py -v
```

Expected: all PASSED, no failures

- [ ] **Step 1.8: Commit**

```bash
git add src/sage_poc/state.py tests/test_state.py tests/test_graph.py
git commit -m "fix(state): add cultural_output_violations to SageState TypedDict

output_gate_node wrote this key but it was absent from the schema,
causing either silent data loss or a LangGraph validation error on
every turn that fires a cultural output rule."
```

---

## Task 2: Allow `"resolved"` through the crisis state boundary (BE-C1)

**Why second:** Until `"resolved"` is a valid state, the monitor window disappears immediately after the post-crisis check-in completes — the turn when the user is most vulnerable. This is a one-line change with a targeted test.

**Files:**
- Modify: `sage-poc/server.py`
- Modify: `sage-poc/tests/test_server.py`

- [ ] **Step 2.1: Write the failing test**

In `sage-poc/tests/test_server.py`, add after `test_crisis_path_gate_path_and_no_skill`:

```python
def test_crisis_state_resolved_not_coerced_to_none(monkeypatch):
    """crisis_state='resolved' must survive the _build_state boundary.

    BE-C1: _VALID_CRISIS_STATES previously omitted 'resolved', so the post-
    crisis warmth window was silently dropped on the first turn after check-in.
    """
    import server as srv

    received_states = []

    async def _capture_state(state):
        received_states.append(state.get("crisis_state"))
        return {
            "path": ["safety_check", "output_gate"],
            "is_safe": True,
            "response": "I hear you.",
            "crisis_state": "resolved",
            "crisis_flags": [],
            "clinical_flags": [],
            "emotional_intensity": 5,
            "active_skill_id": None,
            "executed_step_id": None,
            "gate_path": "standard",
        }

    monkeypatch.setattr(srv, "_graph", type("G", (), {"ainvoke": staticmethod(_capture_state)})())
    client = get_client()
    client.post("/chat", json={
        "messages": [{"role": "user", "content": "I'm feeling much better now"}],
        "session_id": "test",
        "crisis_state": "resolved",
    })
    assert received_states == ["resolved"], (
        f"Expected graph to receive crisis_state='resolved' but got {received_states}. "
        "Check _VALID_CRISIS_STATES in server.py."
    )
```

- [ ] **Step 2.2: Run to confirm it fails**

```bash
pytest tests/test_server.py::test_crisis_state_resolved_not_coerced_to_none -v
```

Expected: `FAILED` — `AssertionError: Expected graph to receive crisis_state='resolved' but got ['none']`

- [ ] **Step 2.3: Add `"resolved"` to `_VALID_CRISIS_STATES`**

In `sage-poc/server.py`, line 29, replace the frozenset:

```python
# Closed set enforced at the HTTP boundary — v7 §5.5.
# crisis_state is client-ferried between turns; arbitrary strings must never enter the graph.
_VALID_CRISIS_STATES = frozenset({"none", "monitoring", "active_crisis", "resolved"})
```

- [ ] **Step 2.4: Run to confirm test passes**

```bash
pytest tests/test_server.py::test_crisis_state_resolved_not_coerced_to_none -v
```

Expected: `PASSED`

- [ ] **Step 2.5: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "fix(server): add 'resolved' to _VALID_CRISIS_STATES

Previously, crisis_state='resolved' was coerced to 'none' at the API
boundary. The post-crisis warmth window (freeflow_respond line 89) was
silently dropped on the first turn after post_crisis_check_in completed —
exactly when the user is most vulnerable.

Closes BE-C1."
```

---

## Task 3: Extract `SKILL_REGISTRY` to `skill_ids.py` (startup import hygiene)

**Why third:** `server.py` (Task 4) needs to import `SKILL_REGISTRY` to build `_VALID_SKILL_IDS` for sanitizing client-ferried `active_skill_id`. Importing it from `skill_select.py` would pull `import numpy as np` (a module-level import in `skill_select.py`) into server startup — adding ~200 ms cold-start overhead and creating an accidental coupling between the HTTP server and the ML stack. Extracting the list to a zero-dependency module breaks this chain.

**Files:**
- Create: `sage-poc/src/sage_poc/skill_ids.py`
- Modify: `sage-poc/src/sage_poc/nodes/skill_select.py`
- Create: `sage-poc/tests/test_skill_ids.py`

- [ ] **Step 3.1: Write the failing test**

```python
# sage-poc/tests/test_skill_ids.py

def test_skill_ids_importable_and_complete():
    """skill_ids.py must exist and export SKILL_REGISTRY as a plain list.

    This module is the canonical source of skill IDs. It must have no
    heavy dependencies so server.py can import it without triggering the
    numpy / sentence-transformers import chain.
    """
    from sage_poc.skill_ids import SKILL_REGISTRY

    assert isinstance(SKILL_REGISTRY, list), "SKILL_REGISTRY must be a list"
    assert len(SKILL_REGISTRY) == 12, f"Expected 12 skills, got {len(SKILL_REGISTRY)}"
    assert "cbt_thought_record" in SKILL_REGISTRY
    assert "grounding_5_4_3_2_1" in SKILL_REGISTRY
    assert "sleep_hygiene" in SKILL_REGISTRY
    assert "post_crisis_check_in" in SKILL_REGISTRY
    assert all(isinstance(sid, str) for sid in SKILL_REGISTRY), \
        "All SKILL_REGISTRY entries must be strings"
    assert len(SKILL_REGISTRY) == len(set(SKILL_REGISTRY)), \
        "SKILL_REGISTRY must not contain duplicates"


def test_skill_select_still_exports_skill_registry():
    """skill_select.py must re-export SKILL_REGISTRY for backward compatibility."""
    from sage_poc.nodes.skill_select import SKILL_REGISTRY as sr_registry
    from sage_poc.skill_ids import SKILL_REGISTRY as ids_registry
    assert sr_registry is ids_registry, (
        "skill_select.SKILL_REGISTRY must be the same object as skill_ids.SKILL_REGISTRY — "
        "skill_select should import from skill_ids, not define its own copy"
    )
```

- [ ] **Step 3.2: Run to confirm both tests fail**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
source .venv/bin/activate
pytest tests/test_skill_ids.py -v
```

Expected: `ERROR` — `ModuleNotFoundError: No module named 'sage_poc.skill_ids'`

- [ ] **Step 3.3: Create `skill_ids.py`**

Create `sage-poc/src/sage_poc/skill_ids.py` with this exact content:

```python
SKILL_REGISTRY = [
    "cbt_thought_record",
    "grounding_5_4_3_2_1",
    "sleep_hygiene",
    "post_crisis_check_in",
    "box_breathing",
    "mood_check_in",
    "behavioral_activation",
    "worry_time",
    "mi_readiness_ruler",
    "stop_technique",
    "progressive_muscle_relaxation",
    "safe_place_visualization",
]
```

No imports. No other code.

- [ ] **Step 3.4: Update `skill_select.py` to import from `skill_ids`**

In `sage-poc/src/sage_poc/nodes/skill_select.py`, find the line that defines `SKILL_REGISTRY` (the list literal at the top of the file) and replace it with:

```python
from sage_poc.skill_ids import SKILL_REGISTRY
```

Do not change any other line in `skill_select.py`.

- [ ] **Step 3.5: Run tests to confirm both pass**

```bash
pytest tests/test_skill_ids.py -v
```

Expected: both `PASSED`

- [ ] **Step 3.6: Run full sage-poc test suite to confirm no regressions**

```bash
pytest tests/ -v --tb=short
```

Expected: all tests pass. Any failure here means a test was importing `SKILL_REGISTRY` directly from `skill_select` via a path that now needs updating — fix by changing the import to `from sage_poc.skill_ids import SKILL_REGISTRY`.

- [ ] **Step 3.7: Commit**

```bash
git add src/sage_poc/skill_ids.py src/sage_poc/nodes/skill_select.py tests/test_skill_ids.py
git commit -m "refactor(skill_ids): extract SKILL_REGISTRY to zero-dependency module

skill_select.py has 'import numpy as np' at module level. Importing
SKILL_REGISTRY from skill_select into server.py would pull numpy into
every server startup — adding cold-start overhead and coupling the HTTP
server to the ML stack.

skill_ids.py is a plain list with no imports. server.py (next commit)
imports from here. skill_select.py re-exports from skill_ids so no
existing caller breaks."
```

---

## Task 4: Extend `ChatRequest` and `_build_state` to carry skill and clinical state (BE-C5)

**Why fourth:** The server must be able to receive ferried state before route.ts is wired to send it. Doing server changes first means the sage-poc test suite covers the receiving end before the proxy is touched.

**Files:**
- Modify: `sage-poc/server.py`
- Modify: `sage-poc/tests/test_server.py`

- [ ] **Step 4.1: Write the failing tests**

Add these two tests to `sage-poc/tests/test_server.py`:

```python
def test_active_skill_id_ferried_into_graph_state(monkeypatch):
    """active_skill_id from the request must reach the graph as-is.

    BE-C5: _build_state previously hardcoded active_skill_id=None, so
    multi-turn skills always restarted from scratch through the HTTP API.
    """
    import server as srv

    received = {}

    async def _capture(state):
        received["active_skill_id"] = state.get("active_skill_id")
        received["active_step_id"] = state.get("active_step_id")
        return {
            "path": ["output_gate"],
            "is_safe": True,
            "response": "ok",
            "crisis_state": "none",
            "crisis_flags": [],
            "clinical_flags": [],
            "emotional_intensity": 5,
            "active_skill_id": "cbt_thought_record",
            "executed_step_id": None,
            "gate_path": "standard",
        }

    monkeypatch.setattr(srv, "_graph", type("G", (), {"ainvoke": staticmethod(_capture)})())
    client = get_client()
    client.post("/chat", json={
        "messages": [{"role": "user", "content": "continue"}],
        "session_id": "test",
        "active_skill_id": "cbt_thought_record",
        "active_step_id": "explore_distortion",
    })
    assert received["active_skill_id"] == "cbt_thought_record", (
        f"Graph received active_skill_id={received['active_skill_id']!r}, expected 'cbt_thought_record'"
    )
    assert received["active_step_id"] == "explore_distortion"


def test_clinical_flags_ferried_into_graph_state(monkeypatch):
    """clinical_flags from prior turns must be carried into the new turn's state."""
    import server as srv

    received = {}

    async def _capture(state):
        received["clinical_flags"] = state.get("clinical_flags")
        return {
            "path": ["output_gate"],
            "is_safe": True,
            "response": "ok",
            "crisis_state": "none",
            "crisis_flags": [],
            "clinical_flags": ["trauma_indicator"],
            "emotional_intensity": 5,
            "active_skill_id": None,
            "executed_step_id": None,
            "gate_path": "standard",
        }

    monkeypatch.setattr(srv, "_graph", type("G", (), {"ainvoke": staticmethod(_capture)})())
    client = get_client()
    client.post("/chat", json={
        "messages": [{"role": "user", "content": "I feel okay"}],
        "session_id": "test",
        "clinical_flags": ["trauma_indicator"],
    })
    assert received["clinical_flags"] == ["trauma_indicator"], (
        f"Graph received clinical_flags={received['clinical_flags']!r}, expected ['trauma_indicator']"
    )
```

- [ ] **Step 4.2: Run to confirm both fail**

```bash
pytest tests/test_server.py::test_active_skill_id_ferried_into_graph_state tests/test_server.py::test_clinical_flags_ferried_into_graph_state -v
```

Expected: both `FAILED` — received values are `None` and `[]` respectively.

- [ ] **Step 4.3: Extend `ChatRequest` and `_build_state` in `server.py`**

Replace the `Message`, `ChatRequest`, and `_build_state` section (lines 32–82) with:

```python
# Import SKILL_REGISTRY from the zero-dependency module — does NOT load numpy or BGE-M3.
from sage_poc.skill_ids import SKILL_REGISTRY as _SKILL_REGISTRY
_VALID_SKILL_IDS: frozenset[str] = frozenset(_SKILL_REGISTRY)

# Known clinical flag IDs — matches safety_check.py clinical flag production values.
_VALID_CLINICAL_FLAGS: frozenset[str] = frozenset({
    "substance_use", "trauma_indicator", "eating_concern",
    "medication_mention", "third_party_si",
})


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    # session_id is received from the client but intentionally not stored in SageState —
    # the graph has no concept of sessions; persistence is the frontend's responsibility.
    session_id: str
    # --- Client-ferried state: values computed by the graph on turn N, returned as
    # response headers, stored by the browser, and sent back on turn N+1.
    # All fields are optional with safe defaults so old clients continue to work. ---
    crisis_state: str = "none"
    active_skill_id: str | None = None
    active_step_id: str | None = None
    clinical_flags: list[str] = []
    distress_trajectory: list[int] = []


def _sanitize_skill_id(value: str | None) -> str | None:
    """Reject unknown skill IDs — prevents an injected value from crashing skill_executor."""
    if not value:
        return None
    return value if value in _VALID_SKILL_IDS else None


def _sanitize_step_id(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    # Step IDs are short ASCII slugs; reject anything that looks like an injection.
    return cleaned if cleaned and len(cleaned) <= 64 and cleaned.isidentifier() else None


def _sanitize_clinical_flags(flags: list[str]) -> list[str]:
    """Keep only known clinical flag IDs; discard unrecognised strings."""
    return [f for f in flags if f in _VALID_CLINICAL_FLAGS]


def _sanitize_trajectory(values: list[int]) -> list[int]:
    """Clamp each value to [0, 10] and keep only the last 20 entries.

    POC stopgap: distress_trajectory is client-ferried because there is no
    server-side session store. In v7, migrate to Cosmos DB / LangGraph
    checkpointing and remove this field from ChatRequest.
    """
    clamped = [max(0, min(10, int(v))) for v in values if isinstance(v, (int, float))]
    return clamped[-20:]


def _build_state(req: ChatRequest) -> dict:
    previous = req.messages[:-1]
    current = req.messages[-1]
    history = [
        {"role": m.role if m.role == "user" else "assistant", "content": m.content}
        for m in previous
    ]
    turn_count = sum(1 for m in previous if m.role != "user")
    crisis_state = req.crisis_state if req.crisis_state in _VALID_CRISIS_STATES else "none"
    return {
        "raw_message": current.content,
        "detected_language": "en",      # safety_check_node overwrites
        "message_en": current.content,  # safety_check_node overwrites for Arabic
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": _sanitize_clinical_flags(req.clinical_flags),
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 5,
        "engagement": 7,
        "active_skill_id": _sanitize_skill_id(req.active_skill_id),
        "active_step_id": _sanitize_step_id(req.active_step_id),
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": turn_count,
        "crisis_state": crisis_state,
        "distress_trajectory": _sanitize_trajectory(req.distress_trajectory),
        "code_switching": False,
        "s7_result": None,
        "s7_method": None,
        "skill_match_method": None,
        "semantic_score": None,
        "prompt_layers": [],
        "token_usage": {},
        "cultural_output_violations": [],
        # Raw message pairs from the client. compose_prompt() in freeflow_respond.py
        # windows this to the last 4 turns — windowing is the graph's responsibility.
        "conversation_history": history,
    }
```

- [ ] **Step 4.4: Run to confirm new tests pass**

```bash
pytest tests/test_server.py::test_active_skill_id_ferried_into_graph_state tests/test_server.py::test_clinical_flags_ferried_into_graph_state -v
```

Expected: both `PASSED`

- [ ] **Step 4.5: Run full server test suite to confirm no regressions**

```bash
pytest tests/test_server.py -v
```

Expected: all existing tests pass, 2 new tests pass.

- [ ] **Step 4.6: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "fix(server): carry skill and clinical state across HTTP turns (BE-C5)

_build_state previously hardcoded active_skill_id=None, active_step_id=None,
and clinical_flags=[] on every request. Multi-turn guided skills were therefore
non-functional through the HTTP API — the CLI carried these fields correctly
(run.py:86-95) but the server did not.

ChatRequest now accepts active_skill_id, active_step_id, clinical_flags,
and distress_trajectory as optional fields with safe defaults. Each is
sanitized before entering the graph: skill IDs are validated against
SKILL_REGISTRY, step IDs are length+format checked, clinical flags are
filtered to the known set, and trajectory values are clamped to [0,10].

SKILL_REGISTRY is imported from sage_poc.skill_ids (zero-dependency) —
not from skill_select — so server startup does not trigger the numpy import.

Also initializes code_switching, skill_match_method, prompt_layers,
token_usage, and cultural_output_violations in _build_state so SageState
is fully populated from turn 1.

Closes BE-C5."
```

---

## Task 5: Add `X-Sage-Active-Step-Id` and `X-Sage-Distress-Trajectory` response headers

**Why:** `X-Sage-Step-Id` currently carries `executed_step_id` (the step used this turn for audit). What the ferry needs is `active_step_id` (the step the *next* turn should start from). These are different. We add a new header rather than changing the semantics of the existing one.

**Files:**
- Modify: `sage-poc/server.py`
- Modify: `sage-poc/tests/test_server.py`

- [ ] **Step 5.1: Write the failing test**

Add to `sage-poc/tests/test_server.py`:

```python
def test_skill_ferry_headers_present(monkeypatch):
    """active_step_id and distress_trajectory must be returned as headers for client ferry."""
    import server as srv
    import json as _json

    async def _mock(state):
        return {
            "path": ["safety_check", "skill_select", "skill_executor", "output_gate"],
            "is_safe": True,
            "response": "Let's try step 2.",
            "crisis_state": "none",
            "crisis_flags": [],
            "clinical_flags": [],
            "emotional_intensity": 6,
            "active_skill_id": "cbt_thought_record",
            "active_step_id": "explore_distortion",   # next turn's step
            "executed_step_id": "identify_thought",   # this turn's step (audit)
            "gate_path": "standard",
            "distress_trajectory": [7, 6, 5],
        }

    monkeypatch.setattr(srv, "_graph", type("G", (), {"ainvoke": staticmethod(_mock)})())
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "ok let's continue"}],
        "session_id": "test",
    })
    assert res.status_code == 200
    # Ferry header: active_step_id (the NEXT step), not executed_step_id (this turn's audit)
    assert res.headers.get("x-sage-active-step-id") == "explore_distortion", (
        "x-sage-active-step-id must carry active_step_id, not executed_step_id"
    )
    # Existing audit header unchanged
    assert res.headers.get("x-sage-step-id") == "identify_thought"
    trajectory = _json.loads(res.headers.get("x-sage-distress-trajectory", "[]"))
    assert trajectory == [7, 6, 5]
```

- [ ] **Step 5.2: Run to confirm it fails**

```bash
pytest tests/test_server.py::test_skill_ferry_headers_present -v
```

Expected: `FAILED` — `x-sage-active-step-id` not in headers

- [ ] **Step 5.3: Add the two new response headers to `server.py`**

In `server.py`, inside the `return StreamingResponse(...)` headers dict, add the two new lines after the `X-Sage-Emotional-Intensity` entry:

```python
        headers={
            "X-Sage-Node-Path":              json.dumps(path),
            "X-Sage-Model":                  RESPONDER_MODEL,
            "X-Sage-Skill-Id":               result.get("active_skill_id") or "",
            "X-Sage-Step-Id":                result.get("executed_step_id") or "",
            "X-Sage-Active-Step-Id":         result.get("active_step_id") or "",
            "X-Sage-Gate-Path":              result.get("gate_path") or "",
            "X-Sage-Crisis-Flags":           json.dumps(result.get("crisis_flags") or []),
            "X-Sage-Clinical-Flags":         json.dumps(result.get("clinical_flags") or []),
            "X-Sage-Emotional-Intensity":    str(result.get("emotional_intensity") or 0),
            "X-Sage-Crisis-State":           result.get("crisis_state") or "none",
            "X-Sage-Distress-Trajectory":    json.dumps(result.get("distress_trajectory") or []),
            # Trace fields: Priority 1
            "X-Sage-Intent":                 result.get("primary_intent") or "",
            "X-Sage-Semantic-Score":         str(result.get("semantic_score") or ""),
            "X-Sage-Prompt-Layers":          json.dumps(result.get("prompt_layers") or []),
            "X-Sage-Token-Usage":            json.dumps(result.get("token_usage") or {}),
            "X-Sage-Turn-Number":            str(result.get("turn_count") or 0),
        },
```

- [ ] **Step 5.4: Run to confirm test passes**

```bash
pytest tests/test_server.py::test_skill_ferry_headers_present -v
```

Expected: `PASSED`

- [ ] **Step 5.5: Run full test suite**

```bash
pytest tests/test_server.py -v
```

Expected: all tests pass.

- [ ] **Step 5.6: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat(server): add X-Sage-Active-Step-Id and X-Sage-Distress-Trajectory headers

X-Sage-Step-Id carries executed_step_id (the step used THIS turn for audit).
The ferry requires active_step_id (the step the NEXT turn starts from).
Adding X-Sage-Active-Step-Id as a separate header preserves the existing
audit semantics while enabling correct skill continuation in the proxy.

X-Sage-Distress-Trajectory is needed for the full clinical state ferry."
```

---

## Task 6: Fix `route.ts` proxy — forward state in both directions (INT-C1 + INT-C2)

**Why sixth:** The backend is now ready to receive and return all ferried state. The proxy fix makes the data flow through the Next.js layer.

`route.ts` is a deliberate security boundary. It is the only process that knows `SAGE_API_URL` (a server-side env var, never sent to the browser), performs Supabase persistence, and will carry auth checks. Do not move any of this logic to the browser. The CORS allow-list on sage-poc is irrelevant here — all sage-poc calls come from the Next.js server process, not the browser.

**Files:**
- Modify: `cdai/apps/web/app/api/chat/route.ts`
- Modify: `cdai/apps/web/app/api/chat/__tests__/route.test.ts`

- [ ] **Step 6.1: Write failing tests**

Replace the entire content of `cdai/apps/web/app/api/chat/__tests__/route.test.ts` with:

```typescript
// apps/web/app/api/chat/__tests__/route.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockInsert = vi.fn().mockResolvedValue({ error: null })
const mockSelect = vi.fn().mockReturnThis()
const mockEq = vi.fn().mockReturnThis()
const mockSingle = vi.fn().mockResolvedValue({ data: { name: null } })
const mockUpdate = vi.fn().mockReturnValue({ eq: vi.fn().mockResolvedValue({ error: null }) })

vi.mock('ai', () => ({
  generateText: vi.fn().mockResolvedValue({ text: 'emotional' }),
}))
vi.mock('@ai-sdk/openai', () => ({ createOpenAI: vi.fn(() => vi.fn()) }))
vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    from: () => ({
      insert: mockInsert,
      select: mockSelect,
      eq: mockEq,
      single: mockSingle,
      update: mockUpdate,
    }),
  }),
}))

import { POST } from '../route'

function makeSageResponse(
  bodyText = 'hello world',
  overrideHeaders: Record<string, string> = {}
) {
  const body = new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(bodyText))
      controller.close()
    },
  })
  return new Response(body, {
    status: 200,
    headers: {
      'X-Sage-Node-Path':            '["safety_check","intent_route","freeflow_respond","output_gate"]',
      'X-Sage-Model':                'anthropic/claude-haiku-4-5',
      'X-Sage-Skill-Id':             '',
      'X-Sage-Step-Id':              '',
      'X-Sage-Active-Step-Id':       '',
      'X-Sage-Gate-Path':            'standard',
      'X-Sage-Crisis-Flags':         '[]',
      'X-Sage-Clinical-Flags':       '[]',
      'X-Sage-Emotional-Intensity':  '5',
      'X-Sage-Crisis-State':         'none',
      'X-Sage-Distress-Trajectory':  '[]',
      'X-Sage-Intent':               'general_chat',
      'X-Sage-Semantic-Score':       '0.87',
      'X-Sage-Prompt-Layers':        '["persona","history"]',
      'X-Sage-Token-Usage':          '{"input":200,"output":45,"total":245}',
      'X-Sage-Turn-Number':          '1',
      ...overrideHeaders,
    },
  })
}

global.fetch = vi.fn().mockResolvedValue(makeSageResponse())

describe('POST /api/chat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(makeSageResponse())
  })

  it('returns a streaming response', async () => {
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'I feel overwhelmed' }],
        sessionId: 'test-session-id',
      }),
    })
    const res = await POST(req)
    expect(res).toBeInstanceOf(Response)
  })

  it('persists new trace columns in the AI message insert', async () => {
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'hello' }],
        sessionId: 'test-session-id',
      }),
    })
    await POST(req)
    await new Promise((r) => setTimeout(r, 50))

    const calls = mockInsert.mock.calls
    const aiInsert = calls.find((c) => c[0]?.role === 'ai' || c[0]?.role === 'crisis')
    expect(aiInsert).toBeDefined()
    const payload = aiInsert![0]
    expect(payload).toMatchObject({
      intent_classification: 'general_chat',
      semantic_score: 0.87,
      prompt_layers: ['persona', 'history'],
      token_usage: { input: 200, output: 45, total: 245 },
      turn_number: 1,
    })
  })

  // ── INT-C1: crisis state forwarded to sage-poc ────────────────────────────
  it('forwards crisisState from request body to sage-poc as crisis_state', async () => {
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'I feel better now' }],
        sessionId: 'test-session-id',
        crisisState: 'monitoring',
      }),
    })
    await POST(req)

    const fetchCalls = (global.fetch as ReturnType<typeof vi.fn>).mock.calls
    const sageCall = fetchCalls.find((c) => (c[0] as string).includes('/chat'))
    expect(sageCall).toBeDefined()
    const body = JSON.parse(sageCall![1].body as string)
    expect(body.crisis_state).toBe('monitoring')
  })

  it('forwards activeSkillId and activeStepId to sage-poc', async () => {
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'continue' }],
        sessionId: 'test-session-id',
        activeSkillId: 'cbt_thought_record',
        activeStepId: 'explore_distortion',
      }),
    })
    await POST(req)

    const fetchCalls = (global.fetch as ReturnType<typeof vi.fn>).mock.calls
    const sageCall = fetchCalls.find((c) => (c[0] as string).includes('/chat'))
    const body = JSON.parse(sageCall![1].body as string)
    expect(body.active_skill_id).toBe('cbt_thought_record')
    expect(body.active_step_id).toBe('explore_distortion')
  })

  it('uses default values for missing state fields (backward compatibility)', async () => {
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'hello' }],
        sessionId: 'test-session-id',
        // crisisState, activeSkillId, etc. intentionally omitted
      }),
    })
    await POST(req)

    const fetchCalls = (global.fetch as ReturnType<typeof vi.fn>).mock.calls
    const sageCall = fetchCalls.find((c) => (c[0] as string).includes('/chat'))
    const body = JSON.parse(sageCall![1].body as string)
    expect(body.crisis_state).toBe('none')
    expect(body.active_skill_id).toBeNull()
    expect(body.active_step_id).toBeNull()
    expect(body.clinical_flags).toEqual([])
    expect(body.distress_trajectory).toEqual([])
  })

  // ── INT-C2: sage-poc headers forwarded to browser ─────────────────────────
  it('forwards X-Sage-Crisis-State to the browser response', async () => {
    ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      makeSageResponse('hello', { 'X-Sage-Crisis-State': 'monitoring' })
    )
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'I am struggling' }],
        sessionId: 'test-session-id',
      }),
    })
    const res = await POST(req)
    expect(res.headers.get('X-Sage-Crisis-State')).toBe('monitoring')
  })

  it('forwards X-Sage-Skill-Id and X-Sage-Active-Step-Id to the browser response', async () => {
    ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      makeSageResponse('Let us try step 2.', {
        'X-Sage-Skill-Id':       'cbt_thought_record',
        'X-Sage-Active-Step-Id': 'explore_distortion',
      })
    )
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'ok' }],
        sessionId: 'test-session-id',
      }),
    })
    const res = await POST(req)
    expect(res.headers.get('X-Sage-Skill-Id')).toBe('cbt_thought_record')
    expect(res.headers.get('X-Sage-Active-Step-Id')).toBe('explore_distortion')
  })

  it('forwards X-Sage-Clinical-Flags and X-Sage-Distress-Trajectory to the browser', async () => {
    ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      makeSageResponse('I hear you.', {
        'X-Sage-Clinical-Flags':        '["trauma_indicator"]',
        'X-Sage-Distress-Trajectory':   '[8,7,6]',
      })
    )
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'yes' }],
        sessionId: 'test-session-id',
      }),
    })
    const res = await POST(req)
    expect(res.headers.get('X-Sage-Clinical-Flags')).toBe('["trauma_indicator"]')
    expect(res.headers.get('X-Sage-Distress-Trajectory')).toBe('[8,7,6]')
  })
})
```

- [ ] **Step 6.2: Run to confirm new tests fail**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
npx vitest run apps/web/app/api/chat/__tests__/route.test.ts
```

Expected: existing 2 tests pass, new 6 tests fail.

- [ ] **Step 6.3: Update `route.ts` — extend request destructuring and sage-poc POST body**

Replace lines 30–58 of `route.ts` with:

```typescript
export async function POST(req: Request) {
  // route.ts is a deliberate security boundary:
  //   - SAGE_API_URL is a server-side env var; it never reaches the browser
  //   - Supabase persistence happens here, not in the browser
  //   - Auth checks (Group 2) will be added here
  // All sage-poc calls originate from this server process — CORS headers on sage-poc
  // are irrelevant to this call path.
  const {
    messages,
    sessionId,
    crisisState        = 'none',
    activeSkillId      = null,
    activeStepId       = null,
    clinicalFlags      = [],
    distressTrajectory = [],
  } = await req.json() as {
    messages:            { role: string; content: string }[]
    sessionId:           string
    crisisState?:        string
    activeSkillId?:      string | null
    activeStepId?:       string | null
    clinicalFlags?:      string[]
    distressTrajectory?: number[]
  }

  if (!sessionId || !messages?.length) {
    return new Response('Bad Request', { status: 400 })
  }

  const lastMessage = messages[messages.length - 1]?.content ?? ''
  const intent = await classifyIntent(lastMessage).catch(() => 'emotional' as Intent)

  const supabase = await createClient()
  await supabase.from('messages').insert({
    session_id: sessionId,
    role: 'user',
    content: lastMessage,
    intent,
  })

  const sageStart = Date.now()
  const sageRes = await fetch(`${SAGE_API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages:            messages.map((m) => ({ role: m.role, content: m.content })),
      session_id:          sessionId,
      crisis_state:        crisisState,
      active_skill_id:     activeSkillId,
      active_step_id:      activeStepId,
      clinical_flags:      clinicalFlags,
      distress_trajectory: distressTrajectory,
    }),
  })

  if (!sageRes.ok || !sageRes.body) {
    return new Response('Upstream error', { status: 502 })
  }
```

- [ ] **Step 6.4: Update `route.ts` — forward state headers back to browser**

Replace the final `return new Response(clientStream, ...)` (lines 170–175) with:

```typescript
  return new Response(clientStream, {
    headers: {
      'Content-Type':                 'text/plain; charset=utf-8',
      'X-Sage-Ai-Message-Id':         aiMessageId,
      // Ferry headers: read by chat-interface.tsx and sent back on the next request.
      // These are the only sage-poc headers forwarded to the browser — all others
      // are consumed here for Supabase persistence.
      'X-Sage-Crisis-State':          sageRes.headers.get('X-Sage-Crisis-State') ?? 'none',
      'X-Sage-Skill-Id':              sageRes.headers.get('X-Sage-Skill-Id') ?? '',
      'X-Sage-Active-Step-Id':        sageRes.headers.get('X-Sage-Active-Step-Id') ?? '',
      'X-Sage-Clinical-Flags':        sageRes.headers.get('X-Sage-Clinical-Flags') ?? '[]',
      'X-Sage-Distress-Trajectory':   sageRes.headers.get('X-Sage-Distress-Trajectory') ?? '[]',
    },
  })
```

- [ ] **Step 6.5: Run all route tests**

```bash
npx vitest run apps/web/app/api/chat/__tests__/route.test.ts
```

Expected: all 8 tests pass.

- [ ] **Step 6.6: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/app/api/chat/route.ts apps/web/app/api/chat/__tests__/route.test.ts
git commit -m "fix(route): forward session state through proxy in both directions (INT-C1, INT-C2)

Inbound: destructure crisisState, activeSkillId, activeStepId, clinicalFlags,
distressTrajectory from the request body and forward them to sage-poc as
crisis_state, active_skill_id, active_step_id, clinical_flags, distress_trajectory.

Outbound: forward X-Sage-Crisis-State, X-Sage-Skill-Id, X-Sage-Active-Step-Id,
X-Sage-Clinical-Flags, X-Sage-Distress-Trajectory from the sage-poc response
to the browser response.

Previously route.ts destructured only { messages, sessionId }, silently
dropping all ferried state. crisis_state always arrived at sage-poc as 'none'.
X-Sage-Crisis-State was never visible to the browser. The crisis state machine
could not persist across any turn boundary.

Closes INT-C1, INT-C2."
```

---

## Task 7: Fix `chat-interface.tsx` — use refs for ferry state, reduce `useCallback` deps (INT-C1 + INT-C2)

**Why last:** The frontend only needs to change after the proxy is confirmed to forward the headers. By this point all preceding tests prove the headers flow correctly to the browser; this task closes the loop.

**Why `useRef` not `useState`:** Ferry state (`crisisState`, `activeSkillId`, `activeStepId`, `clinicalFlags`, `distressTrajectory`) only flows into the outbound request body — it drives no UI rendering. Using `useState` for the array fields (`clinicalFlags`, `distressTrajectory`) would produce a new array reference on every `set`, causing `useCallback` to recreate `stream` on every turn, and enqueue a re-render on every response header read. `useRef` gives a stable object identity, so the `useCallback` deps reduce to `[sessionId]` only — `stream` is created once per session, not once per turn.

**Files:**
- Modify: `cdai/apps/web/components/chat/chat-interface.tsx`

Note: `chat-interface.tsx` has no dedicated unit test for the ferry state reads. The primary validation is the end-to-end pipeline proven by Tasks 4–6. The regression check in Step 7.3 confirms no existing behaviour breaks.

- [ ] **Step 7.1: Replace `useState` ferry vars with `useRef` in `useStreamingChat`**

Replace the four `useState` declarations at lines 38–42 with:

```typescript
  const [messages, setMessages]   = useState<SdkMessage[]>(initialMessages)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError]         = useState<Error | null>(null)
  const abortRef                  = useRef<AbortController | null>(null)

  // Ferry state: values computed by sage-poc on turn N, returned as response headers,
  // and sent back as request body fields on turn N+1. None of these drive UI rendering,
  // so useRef avoids new array references that would force useCallback to recreate
  // `stream` on every turn.
  const crisisStateRef        = useRef<string>('none')
  const activeSkillIdRef      = useRef<string | null>(null)
  const activeStepIdRef       = useRef<string | null>(null)
  const clinicalFlagsRef      = useRef<string[]>([])
  const distressTrajectoryRef = useRef<number[]>([])
```

Ensure `useRef` is imported at the top of the file alongside `useState`. It likely already is (for `abortRef`) — if not, add it to the React import.

- [ ] **Step 7.2: Update the fetch body inside `stream` to read from refs**

Replace the `body: JSON.stringify({...})` block (lines 58–64) with:

```typescript
          body: JSON.stringify({
            sessionId,
            messages:            history.map((m) => ({ role: m.role, content: m.content })),
            crisisState:         crisisStateRef.current,
            activeSkillId:       activeSkillIdRef.current,
            activeStepId:        activeStepIdRef.current,
            clinicalFlags:       clinicalFlagsRef.current,
            distressTrajectory:  distressTrajectoryRef.current,
          }),
```

- [ ] **Step 7.3: Update the response header reads inside `stream` to write to refs**

Replace the existing single-header read (lines 67–71) with:

```typescript
        // Ferry: write updated state into refs; refs are read on the next send.
        // Writing to a ref does not trigger a re-render — correct, since none of these
        // values are shown in the UI.
        const nextCrisisState = res.headers.get('X-Sage-Crisis-State')
        if (nextCrisisState) crisisStateRef.current = nextCrisisState

        const nextSkillId = res.headers.get('X-Sage-Skill-Id')
        activeSkillIdRef.current = nextSkillId || null

        const nextStepId = res.headers.get('X-Sage-Active-Step-Id')
        activeStepIdRef.current = nextStepId || null

        const nextClinicalRaw = res.headers.get('X-Sage-Clinical-Flags')
        if (nextClinicalRaw) {
          try { clinicalFlagsRef.current = JSON.parse(nextClinicalRaw) } catch { /* keep previous */ }
        }

        const nextTrajRaw = res.headers.get('X-Sage-Distress-Trajectory')
        if (nextTrajRaw) {
          try { distressTrajectoryRef.current = JSON.parse(nextTrajRaw) } catch { /* keep previous */ }
        }
```

- [ ] **Step 7.4: Reduce `useCallback` dependency array to `[sessionId]`**

Replace the closing dependency array of the `useCallback` (line 117, currently `[sessionId, crisisState]`) with:

```typescript
  ), [sessionId])
```

Refs are stable objects — their `.current` value changes but the ref object itself does not. They must not appear in dependency arrays. `stream` is now created once per session and reads the latest ferry values on every invocation via `.current`.

- [ ] **Step 7.5: Run the chat component test suite**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
npx vitest run apps/web/components/chat/__tests__/
```

Expected: all existing tests pass with no new failures. If any test references `crisisState` as a returned state value (e.g. `result.current.crisisState`), that test was testing internal implementation detail — remove the assertion or replace it with a fetch-body inspection mock.

- [ ] **Step 7.6: Commit**

```bash
git add apps/web/components/chat/chat-interface.tsx
git commit -m "fix(chat-interface): use refs for ferry state, reduce useCallback deps (INT-C1, INT-C2)

useStreamingChat now stores crisisState, activeSkillId, activeStepId,
clinicalFlags, and distressTrajectory in useRef instead of useState.

Why refs: these values drive outbound requests only — no UI rendering
depends on them. useState for the array fields produced a new reference
on every header read, forcing useCallback to recreate `stream` every turn
and enqueuing a spurious re-render on each response. useRef eliminates
both problems and reduces the useCallback deps to [sessionId].

The hook reads from sageRes headers on each response (writing into refs)
and includes all ref values in the next request body. The full ferry
circuit is now closed: sage-poc → headers → route.ts → browser →
request body → route.ts → sage-poc."
```

---

## Task 8: Add 2-turn server integration tests for the full ferry pipeline

**Why:** All previous tests validate individual components. This task proves the whole pipeline at the HTTP layer: a crisis on turn 1 survives to turn 2 as `monitoring`, and an active skill on turn 1 continues on turn 2. These are the regression tests that would have caught the original bugs.

**Files:**
- Modify: `sage-poc/tests/test_server.py`

- [ ] **Step 8.1: Write the 2-turn crisis pipeline test**

Add to `sage-poc/tests/test_server.py`:

```python
def test_crisis_state_survives_two_turns_through_http(monkeypatch):
    """Full ferry: crisis_state='monitoring' returned on turn 1 must reach
    the graph on turn 2.

    This is the regression test for the bug that killed post-crisis monitoring:
    - Turn 1: server sets X-Sage-Crisis-State: monitoring in response headers
    - Turn 2: client sends crisis_state=monitoring in request body
    - graph receives crisis_state=monitoring (not 'none')

    INT-C1 + INT-C2 + BE-C1 must all be fixed for this test to pass.
    """
    import server as srv
    import json as _json

    turn_states = []

    async def _two_turn_mock(state):
        turn_states.append(state.get("crisis_state"))
        return {
            "path": ["safety_check", "output_gate"],
            "is_safe": True,
            "response": "I am here with you.",
            "crisis_state": "monitoring",   # server always returns monitoring in this mock
            "crisis_flags": ["si_explicit"],
            "clinical_flags": [],
            "emotional_intensity": 8,
            "active_skill_id": None,
            "active_step_id": None,
            "executed_step_id": None,
            "gate_path": "standard",
            "distress_trajectory": [8],
        }

    monkeypatch.setattr(srv, "_graph", type("G", (), {"ainvoke": staticmethod(_two_turn_mock)})())
    client = get_client()

    # Turn 1: user sends a normal message; server returns crisis_state=monitoring
    res1 = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I feel hopeless"}],
        "session_id": "test-ferry",
        "crisis_state": "none",
    })
    assert res1.status_code == 200
    # The server must return the updated crisis state so the client can ferry it
    crisis_after_turn1 = res1.headers.get("x-sage-crisis-state")
    assert crisis_after_turn1 == "monitoring", (
        f"Turn 1 response must include x-sage-crisis-state=monitoring, got {crisis_after_turn1!r}. "
        "Check X-Sage-Crisis-State is in the StreamingResponse headers."
    )

    # Turn 2: client ferries crisis_state=monitoring back
    res2 = client.post("/chat", json={
        "messages": [
            {"role": "user",      "content": "I feel hopeless"},
            {"role": "assistant", "content": "I am here with you."},
            {"role": "user",      "content": "Still feeling bad"},
        ],
        "session_id": "test-ferry",
        "crisis_state": crisis_after_turn1,  # ferried from turn 1 header
    })
    assert res2.status_code == 200

    assert len(turn_states) == 2, f"Expected 2 graph invocations, got {len(turn_states)}"
    assert turn_states[0] == "none", "Turn 1 should start with crisis_state='none'"
    assert turn_states[1] == "monitoring", (
        f"Turn 2 must arrive at graph with crisis_state='monitoring' but got {turn_states[1]!r}. "
        "The ferry is still broken — check server.py _VALID_CRISIS_STATES and _build_state."
    )
```

- [ ] **Step 8.2: Run to confirm it passes**

```bash
pytest tests/test_server.py::test_crisis_state_survives_two_turns_through_http -v
```

Expected: `PASSED`

- [ ] **Step 8.3: Write the 2-turn skill continuation test**

Add to `sage-poc/tests/test_server.py`:

```python
def test_skill_continuation_survives_two_turns_through_http(monkeypatch):
    """active_skill_id ferried from turn 1 reaches the graph on turn 2.

    This proves multi-turn guided skills work through the HTTP API.
    BE-C5 must be fixed for this test to pass.
    """
    import server as srv

    turn_skill_states = []

    async def _skill_mock(state):
        turn_skill_states.append({
            "active_skill_id": state.get("active_skill_id"),
            "active_step_id":  state.get("active_step_id"),
        })
        return {
            "path": ["skill_executor", "output_gate"],
            "is_safe": True,
            "response": "Now let us explore the distortion.",
            "crisis_state": "none",
            "crisis_flags": [],
            "clinical_flags": [],
            "emotional_intensity": 6,
            "active_skill_id": "cbt_thought_record",
            "active_step_id":  "explore_distortion",
            "executed_step_id": "identify_thought",
            "gate_path": "standard",
            "distress_trajectory": [],
        }

    monkeypatch.setattr(srv, "_graph", type("G", (), {"ainvoke": staticmethod(_skill_mock)})())
    client = get_client()

    # Turn 1: no active skill
    res1 = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to do CBT"}],
        "session_id": "skill-ferry",
    })
    assert res1.status_code == 200
    skill_after_turn1 = res1.headers.get("x-sage-skill-id")
    step_after_turn1  = res1.headers.get("x-sage-active-step-id")
    assert skill_after_turn1 == "cbt_thought_record"
    assert step_after_turn1  == "explore_distortion"

    # Turn 2: ferry the skill state
    res2 = client.post("/chat", json={
        "messages": [
            {"role": "user",      "content": "I want to do CBT"},
            {"role": "assistant", "content": "Now let us explore the distortion."},
            {"role": "user",      "content": "My thought is that I am worthless"},
        ],
        "session_id":      "skill-ferry",
        "active_skill_id": skill_after_turn1,
        "active_step_id":  step_after_turn1,
    })
    assert res2.status_code == 200

    assert len(turn_skill_states) == 2
    assert turn_skill_states[0]["active_skill_id"] is None, \
        "Turn 1 should start with no active skill"
    assert turn_skill_states[1]["active_skill_id"] == "cbt_thought_record", (
        f"Turn 2 must arrive with active_skill_id='cbt_thought_record', "
        f"got {turn_skill_states[1]['active_skill_id']!r}"
    )
    assert turn_skill_states[1]["active_step_id"] == "explore_distortion"
```

- [ ] **Step 8.4: Run to confirm it passes**

```bash
pytest tests/test_server.py::test_skill_continuation_survives_two_turns_through_http -v
```

Expected: `PASSED`

- [ ] **Step 8.5: Run full server test suite**

```bash
pytest tests/test_server.py -v
```

Expected: all tests pass. Count: all existing tests + 4 new tests from Tasks 2, 4, 5, and 8.

- [ ] **Step 8.6: Final commit**

```bash
git add tests/test_server.py
git commit -m "test(server): 2-turn HTTP integration tests for crisis and skill ferry

Proves the full ferry pipeline end-to-end at the HTTP layer:
- Crisis state returned in turn 1 headers reaches the graph in turn 2
- Skill state (active_skill_id, active_step_id) ferried from turn 1 headers
  reaches the graph in turn 2

These are the regression tests for BE-C1, BE-C5, INT-C1, INT-C2.
Previously only single-turn behaviour was tested; the multi-turn HTTP path
that all real users experience had zero coverage."
```

---

## Final Verification

After all 8 tasks are complete, run the full test suites for both codebases:

```bash
# sage-poc
cd /Users/knowledgebase/Documents/Sage/sage-poc
source .venv/bin/activate
pytest tests/ -v --tb=short

# cdai
cd /Users/knowledgebase/Documents/Sage/cdai
npx vitest run
```

Both suites must pass with zero failures before this plan is considered complete.

---

## What This Does NOT Fix (Out of Scope for Group 1)

These remain open for their respective groups:

- **BE-C3** (regex rules silently broken) — Group 3
- **BE-C4** (BGE-M3 thread-unsafe init) — Group 3
- **BE-H2** (jailbreak bypass during crisis monitoring) — Group 3
- **BE-H3** (two-word negation false positives) — Group 3
- **FE-C1** (chat API unauthenticated) — Group 2
- **FE-C2** (`/auth/callback` missing) — Group 2
- **FE-C3** (password reset non-functional) — Group 2
- **FE-C4** (`sessionId` ownership not verified) — Group 2
- **FE-C5** (`new` key in searchParams) — Group 4
- **FE-C6** (dead Zustand chat store) — Group 4
- **FE-C7** (StepGuard forward-skip) — Group 2

The `CORS allow_origins` on sage-poc does not need updating — the Next.js server (not the browser) calls sage-poc, so CORS is not in play for this call path.
