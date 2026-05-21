# Trace Completeness + User Feedback

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emit 5 new per-turn trace fields from the Python backend, persist them through the Next.js API route, and add thumbs up/down feedback that links to Supabase message rows.

**Architecture:** Python `freeflow_respond_node` computes `prompt_layers` (list of layer names) and `token_usage` (dict from LLM usage metadata) and stores them in `SageState`. `server.py` emits 5 new response headers. `route.ts` parses those headers, generates a deterministic `aiMessageId` UUID, emits it as a response header, and persists all fields. `FeedbackButtons` appears below completed AI messages and POSTs to `/api/feedback`.

**Tech Stack:** Python 3.12, LangChain `ChatOpenAI`, FastAPI; Next.js 14, Supabase JS v2, Vitest, React Testing Library

**Prerequisite:** `003_complete_trace_fields.sql` migration must be applied before this runs in a connected environment. Local tests mock Supabase, so tests pass without it.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `sage-poc/src/sage_poc/state.py` | Modify | Add `prompt_layers`, `token_usage` fields |
| `sage-poc/src/sage_poc/nodes/freeflow_respond.py` | Modify | Compute layers, switch to `ainvoke`, return usage |
| `sage-poc/server.py` | Modify | Emit 5 new response headers |
| `sage-poc/tests/test_freeflow_respond.py` | Create | Unit tests for layers and token_usage |
| `sage-poc/tests/test_server.py` | Modify | Assert all 5 new headers present |
| `cdai/packages/types/src/index.ts` | Modify | Add `MessageFeedback` type |
| `cdai/apps/web/app/api/chat/route.ts` | Modify | Parse new headers, persist new columns, emit `X-Sage-Ai-Message-Id` |
| `cdai/apps/web/app/api/feedback/route.ts` | Create | Upsert thumbs up/down into `message_feedback` |
| `cdai/apps/web/components/chat/feedback-buttons.tsx` | Create | Thumbs up/down UI |
| `cdai/apps/web/components/chat/message-bubble.tsx` | Modify | Render `FeedbackButtons` below AI messages |
| `cdai/apps/web/components/chat/chat-interface.tsx` | Modify | Read `X-Sage-Ai-Message-Id` header, store in message, pass `onFeedback` |
| `cdai/apps/web/app/api/chat/__tests__/route.test.ts` | Modify | Test new headers parsed |
| `cdai/apps/web/app/api/feedback/__tests__/route.test.ts` | Create | Test feedback upsert |
| `cdai/apps/web/components/chat/__tests__/feedback-buttons.test.tsx` | Create | Test render + click |
| `cdai/apps/web/components/chat/__tests__/message-bubble.test.tsx` | Modify | Test feedback buttons shown for AI messages |

---

### Task 1: Extend SageState with trace fields

**Files:**
- Modify: `sage-poc/src/sage_poc/state.py`

- [ ] **Step 1: Write the failing test**

Create `sage-poc/tests/test_trace_fields.py`:

```python
from sage_poc.state import SageState

def test_state_accepts_prompt_layers():
    state: SageState = {
        "raw_message": "hi", "detected_language": "en", "message_en": "hi",
        "is_safe": True, "crisis_flags": [], "clinical_flags": [],
        "crisis_state": "none", "s7_result": None, "s7_method": None,
        "distress_trajectory": [], "code_switching": False,
        "primary_intent": None, "secondary_intent": None, "intent_confidence": 0.0,
        "emotional_intensity": 5, "engagement": 7,
        "active_skill_id": None, "active_step_id": None, "executed_step_id": None,
        "step_instruction": None, "skill_match_method": None, "semantic_score": None,
        "escalation_triggered": None, "gate_path": None,
        "response_en": None, "response": None,
        "path": [], "turn_count": 0, "conversation_history": [],
        "prompt_layers": ["persona", "history"],
        "token_usage": {"input": 100, "output": 50, "total": 150},
    }
    assert state["prompt_layers"] == ["persona", "history"]
    assert state["token_usage"]["total"] == 150
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
python -m pytest tests/test_trace_fields.py -v
```
Expected: FAIL — `TypedDict` does not have `prompt_layers` key.

- [ ] **Step 3: Add fields to SageState**

In `sage-poc/src/sage_poc/state.py`, add after the `semantic_score` line (line 36):

```python
    prompt_layers: list[str]       # layer names included in the composed LLM prompt
    token_usage: dict              # {"input": N, "output": N, "total": N} from LLM
```

The full relevant section of `state.py` after the edit:
```python
    skill_match_method: Optional[str]   # "keyword" | "semantic" | None
    semantic_score: Optional[float]     # cosine similarity if semantic match
    prompt_layers: list[str]            # layer names included in the composed LLM prompt
    token_usage: dict                   # {"input": N, "output": N, "total": N} from LLM
    escalation_triggered: Optional[dict]  # {"level": "L1"|"L2", "reason": str, "action": str}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
python -m pytest tests/test_trace_fields.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git add src/sage_poc/state.py tests/test_trace_fields.py
git commit -m "feat(state): add prompt_layers and token_usage to SageState"
```

---

### Task 2: Compute prompt_layers and token_usage in freeflow_respond_node

**Files:**
- Modify: `sage-poc/src/sage_poc/nodes/freeflow_respond.py`
- Create: `sage-poc/tests/test_freeflow_respond.py`

- [ ] **Step 1: Write the failing tests**

Create `sage-poc/tests/test_freeflow_respond.py`:

```python
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from sage_poc.nodes.freeflow_respond import compose_prompt, freeflow_respond_node

# Minimal state for testing
_BASE_STATE = {
    "raw_message": "I've been feeling anxious for weeks",
    "detected_language": "en",
    "message_en": "I've been feeling anxious for weeks",
    "is_safe": True, "crisis_flags": [], "clinical_flags": [],
    "crisis_state": "none", "s7_result": None, "s7_method": None,
    "distress_trajectory": [], "code_switching": False,
    "primary_intent": "new_skill", "secondary_intent": None,
    "intent_confidence": 0.9, "emotional_intensity": 7, "engagement": 6,
    "active_skill_id": None, "active_step_id": None, "executed_step_id": None,
    "step_instruction": None, "skill_match_method": None, "semantic_score": None,
    "escalation_triggered": None, "gate_path": None,
    "response_en": None, "response": None,
    "path": ["safety_check", "intent_route"],
    "turn_count": 0, "conversation_history": [],
    "prompt_layers": [], "token_usage": {},
}


def test_compose_prompt_returns_layers():
    _, _, layers = compose_prompt(_BASE_STATE)
    assert "persona" in layers
    assert isinstance(layers, list)
    assert all(isinstance(l, str) for l in layers)


def test_compose_prompt_history_layer():
    state = {**_BASE_STATE, "conversation_history": [
        {"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}
    ]}
    _, _, layers = compose_prompt(state)
    assert "history" in layers


def test_compose_prompt_skill_instruction_layer():
    state = {**_BASE_STATE, "step_instruction": "Ask the user to name one small worry."}
    _, _, layers = compose_prompt(state)
    assert "skill_instruction" in layers


def test_compose_prompt_no_skill_instruction_when_absent():
    _, _, layers = compose_prompt(_BASE_STATE)
    assert "skill_instruction" not in layers


def test_freeflow_respond_node_returns_prompt_layers():
    mock_msg = MagicMock()
    mock_msg.content = "That sounds really difficult."
    mock_msg.usage_metadata = {"input_tokens": 200, "output_tokens": 40, "total_tokens": 240}

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_msg)

    result = asyncio.run(freeflow_respond_node(_BASE_STATE, llm=mock_llm))

    assert "prompt_layers" in result
    assert isinstance(result["prompt_layers"], list)
    assert "persona" in result["prompt_layers"]


def test_freeflow_respond_node_returns_token_usage():
    mock_msg = MagicMock()
    mock_msg.content = "That sounds really difficult."
    mock_msg.usage_metadata = {"input_tokens": 200, "output_tokens": 40, "total_tokens": 240}

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_msg)

    result = asyncio.run(freeflow_respond_node(_BASE_STATE, llm=mock_llm))

    assert result["token_usage"] == {"input": 200, "output": 40, "total": 240}


def test_freeflow_respond_node_handles_missing_usage_metadata():
    mock_msg = MagicMock()
    mock_msg.content = "I hear you."
    mock_msg.usage_metadata = None

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_msg)

    result = asyncio.run(freeflow_respond_node(_BASE_STATE, llm=mock_llm))

    assert result["token_usage"] == {"input": 0, "output": 0, "total": 0}


def test_compose_prompt_intent_layer_always_present():
    # L2 per v7 §5.6 is always included regardless of path
    _, _, layers = compose_prompt(_BASE_STATE)
    assert "intent" in layers


def test_compose_prompt_cultural_layer_tracked():
    # When rules_engine fires a cultural action, the "cultural" layer must appear.
    # Patch rules_engine.evaluate to return a cultural action on the cultural call.
    from unittest.mock import patch
    from sage_poc.rules.engine import EvalResult

    cultural_result = MagicMock()
    cultural_result.actions = [{"target": "system", "content": "Acknowledge Islamic framing.", "priority": 1}]
    injection_result = MagicMock()
    injection_result.actions = []

    def fake_evaluate(category, _ctx):
        if category == "cultural":
            return cultural_result
        return injection_result

    with patch("sage_poc.nodes.freeflow_respond.rules_engine.evaluate", side_effect=fake_evaluate):
        _, _, layers = compose_prompt(_BASE_STATE)

    assert "cultural" in layers


def test_compose_prompt_clinical_adaptation_layer_tracked():
    # When prompt_injection fires a system-targeted injection, "clinical_adaptation" must appear.
    from unittest.mock import patch
    from sage_poc.rules.engine import EvalResult

    cultural_result = MagicMock()
    cultural_result.actions = []
    injection_result = MagicMock()
    injection_result.actions = [{"target": "system", "content": "User has disclosed substance use history."}]

    def fake_evaluate(category, _ctx):
        if category == "cultural":
            return cultural_result
        return injection_result

    with patch("sage_poc.nodes.freeflow_respond.rules_engine.evaluate", side_effect=fake_evaluate):
        state = {**_BASE_STATE, "clinical_flags": ["substance_use"]}
        _, _, layers = compose_prompt(state)

    assert "clinical_adaptation" in layers
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
python -m pytest tests/test_freeflow_respond.py -v
```
Expected: FAIL — `compose_prompt` returns a 2-tuple, not 3-tuple; `freeflow_respond_node` has no `ainvoke`.

- [ ] **Step 3: Rewrite freeflow_respond.py**

Replace the entire content of `sage-poc/src/sage_poc/nodes/freeflow_respond.py`:

```python
import re
from sage_poc.state import SageState
from sage_poc.llm import get_responder
from sage_poc.knowledge import lookup_knowledge
from sage_poc.rules import engine as rules_engine

_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001F9FF"   # misc symbols, emoticons, transport, flags
    r"\U00002600-\U000027BF"    # misc symbols and dingbats
    r"\U0001FA00-\U0001FAFF"    # extended symbols and pictographs
    r"\U0000FE00-\U0000FE0F"    # variation selectors (emoji presentation modifiers)
    r"\U0000200D"               # zero-width joiner (stripped individually; base emoji caught by ranges above)
    r"]"
)


def _sanitize_assistant_turn(text: str) -> str:
    """Strip formatting artifacts from assistant history before prompt injection.

    Operates on prompt strings only — never called on stored state data.
    Preserves text content when removing markdown markers.
    """
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)                    # **bold** -> bold
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"\1", text)      # *italic* -> italic (not bold remnants)
    text = text.replace("—", ", ")                               # em dash -> comma space
    text = _EMOJI_RE.sub("", text)
    return text


PERSONA = """IMPORTANT. FORMAT: Write in plain prose. Use commas or short sentences instead of dashes. Use no emojis. Use no markdown (no **, no *, no bullets). Do not copy punctuation patterns from the skill instructions you receive. Those are guidance for you, not templates to mirror.

FORMATTING EXAMPLE:
WRONG: "That really resonates, sometimes things pile up. What's been **weighing on you**?"
RIGHT: "That makes sense. What's been on your mind lately?"

You are Sage, a warm Khaleeji wellness companion. You provide emotional support grounded in evidence-based approaches (CBT, DBT, motivational interviewing). Speak the way a calm, attentive person would in a quiet one-on-one conversation. Short sentences. Plain words. No decoration. If something matters, say it clearly. Warmth comes from what you say, not how you format it.

You do NOT diagnose, prescribe, or replace professional mental health care. If someone is in crisis, your only role is to express care and provide emergency resources.

Keep responses concise (2-4 sentences unless the user needs more). Match the user's energy and register. Be present before being helpful."""

_CULTURAL_BUDGET_WORDS = 150


def compose_prompt(state: SageState) -> tuple[str, str, list[str]]:
    """Return (system_str, user_str, prompt_layers) for role-separated LLM invocation.

    system_str: persona + culturally-triggered injections + clinical adaptations.
    user_str:   history + intent + secondary-intent framing + skill instruction +
                knowledge snippet + user message.
    prompt_layers: ordered list of named layers that were included in this prompt.
    """
    message_en = state.get("message_en", "")
    language = state.get("detected_language", "en")
    clinical_flags = state.get("clinical_flags", [])
    primary_intent = state.get("primary_intent")
    secondary_intent = state.get("secondary_intent")

    layers: list[str] = []

    # ---- System role -------------------------------------------------------
    system_parts = [PERSONA]
    layers.append("persona")

    code_switch = state.get("code_switching", False)
    cultural_result = rules_engine.evaluate("cultural", {
        "text": message_en,
        "text_ar": state.get("raw_message") if language == "ar" else None,
        "language": language,
        "code_switch": code_switch,
    })
    cultural_actions = sorted(
        [a for a in cultural_result.actions if a.get("target") == "system"],
        key=lambda a: a.get("priority", 5),
    )
    word_count = 0
    for action in cultural_actions:
        content = action["content"]
        words = len(content.split())
        if word_count + words <= _CULTURAL_BUDGET_WORDS or word_count == 0:
            system_parts.append(content)
            word_count += words
        else:
            break
    if cultural_actions:
        layers.append("cultural")

    session_flags: list[str] = []
    if state.get("crisis_state") in ("active", "monitoring", "resolved"):
        session_flags.append("crisis_occurred")

    injection_result = rules_engine.evaluate("prompt_injection", {
        "text": message_en,
        "clinical_flags": clinical_flags,
        "primary_intent": primary_intent,
        "secondary_intent": secondary_intent,
        "session_flags": session_flags,
    })
    system_injections = [
        a["content"] for a in injection_result.actions if a.get("target") == "system"
    ]
    if system_injections:
        system_parts.append(
            "\nCLINICAL ADAPTATIONS (follow these strictly):\n"
            + "\n".join(f"- {c}" for c in system_injections)
        )
        layers.append("clinical_adaptation")

    system_str = "\n\n".join(system_parts)

    # ---- User role ---------------------------------------------------------
    user_parts = []

    if state["conversation_history"]:
        history = state["conversation_history"][-4:]
        lines = []
        for m in history:
            content = (
                _sanitize_assistant_turn(m["content"])
                if m["role"] == "assistant"
                else m["content"]
            )
            lines.append(f"{m['role'].upper()}: {content}")
        user_parts.append(f"CONVERSATION HISTORY:\n" + "\n".join(lines))
        layers.append("history")

    intensity = state.get("emotional_intensity", 5)
    intent_line = f"INTENT: {primary_intent or 'general_chat'}"
    if secondary_intent:
        intent_line += f" + {secondary_intent} (blended)"
    user_parts.append(f"{intent_line} | Emotional intensity: {intensity}/10")
    layers.append("intent")  # L2: always present per v7 §5.6

    # L5 placeholder: therapeutic profile summary ("This user tends toward
    # catastrophising. Grounding works well.") — not yet implemented.
    # When Priority 3 cross-session memory is built, inject the profile
    # summary here and append layers.append("therapeutic_profile").

    if state.get("crisis_state") == "monitoring":
        s7 = state.get("s7_result") or "UNCLEAR"
        user_parts.append(
            f"POST-CRISIS CONTEXT: The user was recently in crisis. "
            f"S7 recovery classifier result: {s7}. "
            f"Respond with extra warmth, patience, and safety-consciousness. "
            f"Do not probe for details of the crisis. Meet the user where they are."
        )
        layers.append("post_crisis_context")

    user_injections = [
        a["content"] for a in injection_result.actions if a.get("target") == "user"
    ]
    for content in user_injections:
        user_parts.append(content)

    if state.get("step_instruction"):
        user_parts.append(f"SKILL INSTRUCTION:\n{state['step_instruction']}")
        layers.append("skill_instruction")

    intent_set = {primary_intent, secondary_intent}
    if "info_request" in intent_set:
        snippet = lookup_knowledge(message_en)
        if snippet:
            user_parts.append(
                f"KNOWLEDGE (weave naturally into your response if relevant):\n{snippet}"
            )
            layers.append("knowledge")

    user_parts.append(f"USER: {message_en}")
    user_str = "\n\n".join(user_parts)

    return system_str, user_str, layers


async def freeflow_respond_node(state: SageState, llm=None) -> dict:
    if llm is None:
        llm = get_responder()

    system_str, user_str, prompt_layers = compose_prompt(state)
    messages = [
        {"role": "system", "content": system_str},
        {"role": "user", "content": user_str},
    ]

    response_msg = await llm.ainvoke(messages)
    response = response_msg.content.strip()

    usage_meta = response_msg.usage_metadata or {}
    token_usage = {
        "input":  usage_meta.get("input_tokens", 0),
        "output": usage_meta.get("output_tokens", 0),
        "total":  usage_meta.get("total_tokens", 0),
    }

    return {
        "response_en":    response,
        "prompt_layers":  prompt_layers,
        "token_usage":    token_usage,
        "path":           state["path"] + ["freeflow_respond"],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
python -m pytest tests/test_freeflow_respond.py -v
```
Expected: all 6 tests PASS.

- [ ] **Step 5: Verify existing tests still pass**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
python -m pytest tests/ -v --ignore=tests/test_freeflow_respond.py -x
```
Expected: all passing (the `compose_prompt` signature change is internal to `freeflow_respond.py`; no other module calls it directly).

- [ ] **Step 6: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git add src/sage_poc/nodes/freeflow_respond.py tests/test_freeflow_respond.py
git commit -m "feat(freeflow): compute prompt_layers and token_usage, switch to ainvoke"
```

---

### Task 3: Emit 5 new headers from server.py

**Files:**
- Modify: `sage-poc/server.py`
- Modify: `sage-poc/tests/test_server.py`

- [ ] **Step 1: Write the failing test**

Read the current `tests/test_server.py` first, then add these assertions to the existing test class/function, or add a new test function. The test uses a mocked graph. Add after the existing test:

```python
# In tests/test_server.py — add to existing import section if needed:
# (verify the existing test structure before deciding where to insert)

def test_chat_response_has_all_trace_headers(client, mock_graph_result):
    """All 9 existing + 5 new trace headers must be present in every /chat response."""
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "test"}],
        "session_id": "s1",
    })
    assert res.status_code == 200
    for header in [
        "x-sage-node-path",
        "x-sage-model",
        "x-sage-skill-id",
        "x-sage-step-id",
        "x-sage-gate-path",
        "x-sage-crisis-flags",
        "x-sage-clinical-flags",
        "x-sage-emotional-intensity",
        # New headers:
        "x-sage-intent",
        "x-sage-semantic-score",
        "x-sage-prompt-layers",
        "x-sage-token-usage",
        "x-sage-turn-number",
    ]:
        assert header in res.headers, f"Missing header: {header}"
```

(Read `tests/test_server.py` first to find the right fixture names — `client` and `mock_graph_result` may be named differently.)

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
python -m pytest tests/test_server.py -v -k "trace_headers"
```
Expected: FAIL — the 5 new headers are not present.

- [ ] **Step 3: Add the 5 new headers to server.py**

In `sage-poc/server.py`, replace the `return StreamingResponse(...)` block (starting at line 109) with:

```python
    return StreamingResponse(
        _body(),
        media_type="text/plain; charset=utf-8",
        headers={
            "X-Sage-Node-Path":           json.dumps(path),
            "X-Sage-Model":               RESPONDER_MODEL,
            "X-Sage-Skill-Id":            result.get("active_skill_id") or "",
            "X-Sage-Step-Id":             result.get("executed_step_id") or "",
            "X-Sage-Gate-Path":           result.get("gate_path") or "",
            "X-Sage-Crisis-Flags":        json.dumps(result.get("crisis_flags") or []),
            "X-Sage-Clinical-Flags":      json.dumps(result.get("clinical_flags") or []),
            "X-Sage-Emotional-Intensity": str(result.get("emotional_intensity") or 0),
            # Trace fields: Priority 1
            "X-Sage-Intent":              result.get("primary_intent") or "",
            "X-Sage-Semantic-Score":      str(result.get("semantic_score") or ""),
            "X-Sage-Prompt-Layers":       json.dumps(result.get("prompt_layers") or []),
            "X-Sage-Token-Usage":         json.dumps(result.get("token_usage") or {}),
            "X-Sage-Turn-Number":         str(result.get("turn_count") or 0),
        },
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
python -m pytest tests/test_server.py -v
```
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git add server.py tests/test_server.py
git commit -m "feat(server): emit 5 new trace headers (intent, semantic_score, prompt_layers, token_usage, turn_number)"
```

---

### Task 4: Add MessageFeedback type to packages/types

**Files:**
- Modify: `cdai/packages/types/src/index.ts`

- [ ] **Step 1: Write the failing test**

In `cdai/packages/types/src/__tests__/types.test.ts`, add:

```typescript
import type { MessageFeedback } from '../index'

it('MessageFeedback type accepts thumbs up', () => {
  const fb: MessageFeedback = {
    id: 'abc',
    messageId: 'msg-1',
    userId: 'user-1',
    value: 1,
    createdAt: '2026-05-22T00:00:00Z',
  }
  expect(fb.value).toBe(1)
})

it('MessageFeedback type accepts thumbs down', () => {
  const fb: MessageFeedback = {
    id: 'abc',
    messageId: 'msg-1',
    userId: 'user-1',
    value: -1,
    createdAt: '2026-05-22T00:00:00Z',
  }
  expect(fb.value).toBe(-1)
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm --filter @cdai/types test
```
Expected: FAIL — `MessageFeedback` not exported.

- [ ] **Step 3: Add MessageFeedback to types/index.ts**

Append to `cdai/packages/types/src/index.ts`:

```typescript
export interface MessageFeedback {
  id: string
  messageId: string
  userId: string
  value: 1 | -1
  createdAt: string
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm --filter @cdai/types test
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add packages/types/src/index.ts packages/types/src/__tests__/types.test.ts
git commit -m "feat(types): add MessageFeedback type"
```

---

### Task 5: Parse new headers and persist new columns in route.ts

**Files:**
- Modify: `cdai/apps/web/app/api/chat/route.ts`
- Modify: `cdai/apps/web/app/api/chat/__tests__/route.test.ts`

- [ ] **Step 1: Write the failing tests**

Replace `cdai/apps/web/app/api/chat/__tests__/route.test.ts` with:

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
    from: () => ({ insert: mockInsert, select: mockSelect, eq: mockEq, single: mockSingle, update: mockUpdate }),
  }),
}))

import { POST } from '../route'

function makeSageResponse(headers: Record<string, string> = {}) {
  const body = new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode('hello world'))
      controller.close()
    },
  })
  return new Response(body, {
    status: 200,
    headers: {
      'X-Sage-Node-Path':           '["safety_check","intent_route","freeflow_respond","output_gate"]',
      'X-Sage-Model':               'anthropic/claude-haiku-4-5',
      'X-Sage-Skill-Id':            '',
      'X-Sage-Step-Id':             '',
      'X-Sage-Gate-Path':           'standard',
      'X-Sage-Crisis-Flags':        '[]',
      'X-Sage-Clinical-Flags':      '[]',
      'X-Sage-Emotional-Intensity': '5',
      'X-Sage-Intent':              'general_chat',
      'X-Sage-Semantic-Score':      '0.87',
      'X-Sage-Prompt-Layers':       '["persona","history"]',
      'X-Sage-Token-Usage':         '{"input":200,"output":45,"total":245}',
      'X-Sage-Turn-Number':         '1',
      'X-Sage-Ai-Message-Id':       'test-ai-msg-uuid',
      ...headers,
    },
  })
}

vi.mock('node-fetch', () => ({ default: vi.fn() }))

// Override global fetch for the sage backend call
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
    // Give the background persist time to run
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
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm --filter @web test
```
Expected: FAIL — `intent_classification` and friends not in the persist call.

- [ ] **Step 3: Rewrite route.ts**

Replace the full content of `cdai/apps/web/app/api/chat/route.ts`:

```typescript
// apps/web/app/api/chat/route.ts
import { generateText } from 'ai'
import { createOpenAI } from '@ai-sdk/openai'
import { createClient } from '@/lib/supabase/server'
import type { Intent } from '@cdai/types'

const openrouter = createOpenAI({
  baseURL: 'https://openrouter.ai/api/v1',
  apiKey: process.env.OPENROUTER_API_KEY!,
})

const CLASSIFIER_MODEL = 'anthropic/claude-haiku-4-5-20251001'
const SAGE_API_URL = process.env.SAGE_API_URL ?? 'http://localhost:8000'
const CRISIS_SIGNAL = '[[CRISIS_DETECTED]]'

async function classifyIntent(message: string): Promise<Intent> {
  const { text } = await generateText({
    model: openrouter(CLASSIFIER_MODEL),
    prompt: `Classify this message as "knowledge" (asking for information or resources) or "emotional" (seeking support, sharing feelings). Reply with exactly one word.\n\nMessage: "${message}"`,
    maxOutputTokens: 5,
  })
  return text.trim().toLowerCase().startsWith('k') ? 'knowledge' : 'emotional'
}

function parseJsonHeader<T>(raw: string | null, fallback: T): T {
  if (!raw) return fallback
  try { return JSON.parse(raw) as T } catch { return fallback }
}

export async function POST(req: Request) {
  const { messages, sessionId } = await req.json() as {
    messages: { role: string; content: string }[]
    sessionId: string
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
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
      session_id: sessionId,
    }),
  })

  if (!sageRes.ok || !sageRes.body) {
    return new Response('Upstream error', { status: 502 })
  }

  // Existing metadata headers
  const sageModel    = sageRes.headers.get('X-Sage-Model')
  const skillId      = sageRes.headers.get('X-Sage-Skill-Id') || null
  const stepId       = sageRes.headers.get('X-Sage-Step-Id') || null
  const gatePath     = sageRes.headers.get('X-Sage-Gate-Path') || null

  const sageNodePath  = parseJsonHeader<string[] | null>(sageRes.headers.get('X-Sage-Node-Path'), null)
  const crisisFlags   = parseJsonHeader<string[] | null>(sageRes.headers.get('X-Sage-Crisis-Flags'), null)
  const clinicalFlags = parseJsonHeader<string[] | null>(sageRes.headers.get('X-Sage-Clinical-Flags'), null)

  const intensityStr       = sageRes.headers.get('X-Sage-Emotional-Intensity')
  const emotionalIntensity = intensityStr ? (parseInt(intensityStr, 10) || null) : null

  // New trace headers (Priority 1)
  const intentClassification = sageRes.headers.get('X-Sage-Intent') || null
  const semanticScoreStr     = sageRes.headers.get('X-Sage-Semantic-Score')
  const semanticScore        = semanticScoreStr ? (parseFloat(semanticScoreStr) || null) : null
  const promptLayers         = parseJsonHeader<string[] | null>(sageRes.headers.get('X-Sage-Prompt-Layers'), null)
  const tokenUsage           = parseJsonHeader<object | null>(sageRes.headers.get('X-Sage-Token-Usage'), null)
  const turnNumberStr        = sageRes.headers.get('X-Sage-Turn-Number')
  const turnNumber           = turnNumberStr ? (parseInt(turnNumberStr, 10) || null) : null

  // Deterministic AI message UUID: generated here so it can be used in both
  // the Supabase insert and the response header for the feedback flow.
  const aiMessageId = crypto.randomUUID()

  const [clientStream, persistStream] = sageRes.body.tee()

  void (async () => {
    try {
      const reader = persistStream.getReader()
      const decoder = new TextDecoder()
      let accumulated = ''
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        accumulated += decoder.decode(value, { stream: true })
      }
      accumulated += decoder.decode()
      const latencyMs = Date.now() - sageStart

      if (accumulated.includes('[[SERVER_ERROR]]')) {
        console.error('[chat/persist] server error sentinel received, skipping persist')
      } else {
        const isCrisis = accumulated.startsWith(CRISIS_SIGNAL)
        const content = isCrisis
          ? accumulated.slice(CRISIS_SIGNAL.length).trimStart()
          : accumulated

        await supabase.from('messages').insert({
          id:                    aiMessageId,
          session_id:            sessionId,
          role:                  isCrisis ? 'crisis' : 'ai',
          content,
          intent,
          model:                 sageModel,
          latency_ms:            latencyMs,
          node_path:             sageNodePath,
          skill_id:              skillId,
          step_id:               stepId,
          gate_path:             gatePath,
          crisis_flags:          crisisFlags,
          clinical_flags:        clinicalFlags,
          emotional_intensity:   emotionalIntensity,
          // New trace fields
          intent_classification: intentClassification,
          semantic_score:        semanticScore,
          prompt_layers:         promptLayers,
          token_usage:           tokenUsage,
          turn_number:           turnNumber,
          // Timestamped clinical flag detail for clinician timeline and
          // cross-session aggregation (Priority 3). Only written when flags present.
          clinical_flags_detail: clinicalFlags?.length
            ? Object.fromEntries(
                clinicalFlags.map(flag => [
                  flag,
                  { detected_at: new Date().toISOString(), turn_number: turnNumber },
                ])
              )
            : null,
        })
      }

      const { data: session } = await supabase
        .from('chat_sessions')
        .select('name')
        .eq('id', sessionId)
        .single()

      if (session && !session.name) {
        const { text: sessionName } = await generateText({
          model: openrouter(CLASSIFIER_MODEL),
          prompt: `Give this conversation a short title (3-5 words, no quotes):\n\nUser: "${lastMessage}"`,
          maxOutputTokens: 15,
        }).catch(() => ({ text: lastMessage.slice(0, 30) }))
        await supabase.from('chat_sessions')
          .update({ name: sessionName.trim(), updated_at: new Date().toISOString() })
          .eq('id', sessionId)
      }
      // POST-PILOT: Add mood scoring and insight generation here.
    } catch (err) {
      console.error('[chat/persist] failed:', err)
    }
  })()

  return new Response(clientStream, {
    headers: {
      'Content-Type':          'text/plain; charset=utf-8',
      'X-Sage-Ai-Message-Id':  aiMessageId,
    },
  })
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm --filter @web test -- --reporter=verbose
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/app/api/chat/route.ts apps/web/app/api/chat/__tests__/route.test.ts
git commit -m "feat(route): parse trace headers, persist new columns, emit X-Sage-Ai-Message-Id"
```

---

### Task 6: Create /api/feedback route

**Files:**
- Create: `cdai/apps/web/app/api/feedback/route.ts`
- Create: `cdai/apps/web/app/api/feedback/__tests__/route.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `cdai/apps/web/app/api/feedback/__tests__/route.test.ts`:

```typescript
// apps/web/app/api/feedback/__tests__/route.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockUpsert = vi.fn().mockResolvedValue({ error: null })
const mockGetUser = vi.fn().mockResolvedValue({
  data: { user: { id: 'user-abc' } },
  error: null,
})

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: { getUser: mockGetUser },
    from: () => ({ upsert: mockUpsert }),
  }),
}))

import { POST } from '../route'

describe('POST /api/feedback', () => {
  beforeEach(() => vi.clearAllMocks())

  it('returns 401 when user is not authenticated', async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: null }, error: null })
    const req = new Request('http://localhost/api/feedback', {
      method: 'POST',
      body: JSON.stringify({ messageId: 'msg-1', value: 1 }),
    })
    const res = await POST(req)
    expect(res.status).toBe(401)
  })

  it('returns 400 when value is not 1 or -1', async () => {
    const req = new Request('http://localhost/api/feedback', {
      method: 'POST',
      body: JSON.stringify({ messageId: 'msg-1', value: 0 }),
    })
    const res = await POST(req)
    expect(res.status).toBe(400)
  })

  it('upserts feedback for thumbs up', async () => {
    const req = new Request('http://localhost/api/feedback', {
      method: 'POST',
      body: JSON.stringify({ messageId: 'msg-1', value: 1 }),
    })
    const res = await POST(req)
    expect(res.status).toBe(200)
    expect(mockUpsert).toHaveBeenCalledWith(
      { message_id: 'msg-1', user_id: 'user-abc', value: 1 },
      { onConflict: 'message_id,user_id' }
    )
  })

  it('upserts feedback for thumbs down', async () => {
    const req = new Request('http://localhost/api/feedback', {
      method: 'POST',
      body: JSON.stringify({ messageId: 'msg-1', value: -1 }),
    })
    const res = await POST(req)
    expect(res.status).toBe(200)
    expect(mockUpsert).toHaveBeenCalledWith(
      { message_id: 'msg-1', user_id: 'user-abc', value: -1 },
      { onConflict: 'message_id,user_id' }
    )
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm --filter @web test -- feedback
```
Expected: FAIL — route does not exist.

- [ ] **Step 3: Create the feedback route**

Create `cdai/apps/web/app/api/feedback/route.ts`:

```typescript
// apps/web/app/api/feedback/route.ts
import { createClient } from '@/lib/supabase/server'

export async function POST(req: Request) {
  const { messageId, value } = await req.json() as {
    messageId: string
    value: unknown
  }

  if (value !== 1 && value !== -1) {
    return new Response('value must be 1 or -1', { status: 400 })
  }

  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()

  if (authError || !user) {
    return new Response('Unauthorized', { status: 401 })
  }

  const { error } = await supabase
    .from('message_feedback')
    .upsert(
      { message_id: messageId, user_id: user.id, value: value as 1 | -1 },
      { onConflict: 'message_id,user_id' }
    )

  if (error) {
    console.error('[feedback] upsert failed:', error)
    return new Response('Internal Server Error', { status: 500 })
  }

  return new Response('OK', { status: 200 })
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm --filter @web test -- feedback
```
Expected: all 4 PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/app/api/feedback/route.ts apps/web/app/api/feedback/__tests__/route.test.ts
git commit -m "feat(api): add /api/feedback route for thumbs up/down message feedback"
```

---

### Task 7: Create FeedbackButtons component

**Files:**
- Create: `cdai/apps/web/components/chat/feedback-buttons.tsx`
- Create: `cdai/apps/web/components/chat/__tests__/feedback-buttons.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `cdai/apps/web/components/chat/__tests__/feedback-buttons.test.tsx`:

```typescript
// components/chat/__tests__/feedback-buttons.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { FeedbackButtons } from '../feedback-buttons'

describe('FeedbackButtons', () => {
  it('renders thumbs up and thumbs down buttons', () => {
    render(<FeedbackButtons messageId="msg-1" onFeedback={vi.fn()} />)
    expect(screen.getByRole('button', { name: /thumbs up/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /thumbs down/i })).toBeInTheDocument()
  })

  it('calls onFeedback with 1 when thumbs up clicked', () => {
    const onFeedback = vi.fn()
    render(<FeedbackButtons messageId="msg-1" onFeedback={onFeedback} />)
    fireEvent.click(screen.getByRole('button', { name: /thumbs up/i }))
    expect(onFeedback).toHaveBeenCalledWith('msg-1', 1)
  })

  it('calls onFeedback with -1 when thumbs down clicked', () => {
    const onFeedback = vi.fn()
    render(<FeedbackButtons messageId="msg-1" onFeedback={onFeedback} />)
    fireEvent.click(screen.getByRole('button', { name: /thumbs down/i }))
    expect(onFeedback).toHaveBeenCalledWith('msg-1', -1)
  })

  it('shows selected state after clicking thumbs up', () => {
    render(<FeedbackButtons messageId="msg-1" onFeedback={vi.fn()} />)
    const upBtn = screen.getByRole('button', { name: /thumbs up/i })
    fireEvent.click(upBtn)
    expect(upBtn).toHaveAttribute('aria-pressed', 'true')
  })

  it('disables both buttons after a selection', () => {
    render(<FeedbackButtons messageId="msg-1" onFeedback={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /thumbs up/i }))
    expect(screen.getByRole('button', { name: /thumbs up/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /thumbs down/i })).toBeDisabled()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm --filter @web test -- feedback-buttons
```
Expected: FAIL — component does not exist.

- [ ] **Step 3: Create the FeedbackButtons component**

Create `cdai/apps/web/components/chat/feedback-buttons.tsx`:

```typescript
'use client'
import { useState } from 'react'
import { cn } from '@cdai/ui'

interface Props {
  messageId: string
  onFeedback: (messageId: string, value: 1 | -1) => void
}

// Inline SVG icons — no icon library dependency required.
function ThumbsUpIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z" />
      <path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
    </svg>
  )
}

function ThumbsDownIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z" />
      <path d="M17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" />
    </svg>
  )
}

export function FeedbackButtons({ messageId, onFeedback }: Props) {
  const [selected, setSelected] = useState<1 | -1 | null>(null)

  function handleClick(value: 1 | -1) {
    if (selected !== null) return
    setSelected(value)
    onFeedback(messageId, value)
  }

  return (
    <div className="flex gap-1 mt-1">
      <button
        aria-label="Thumbs up"
        aria-pressed={selected === 1}
        disabled={selected !== null}
        onClick={() => handleClick(1)}
        className={cn(
          'rounded-full p-1.5 transition-all',
          selected === 1
            ? 'text-[var(--color-primary)] opacity-100'
            : 'text-[var(--color-text-secondary)] opacity-70 hover:opacity-100 hover:text-[var(--color-primary)]',
          'disabled:cursor-default'
        )}
      >
        <ThumbsUpIcon />
      </button>
      <button
        aria-label="Thumbs down"
        aria-pressed={selected === -1}
        disabled={selected !== null}
        onClick={() => handleClick(-1)}
        className={cn(
          'rounded-full p-1.5 transition-all',
          selected === -1
            ? 'text-[var(--color-crisis)] opacity-100'
            : 'text-[var(--color-text-secondary)] opacity-70 hover:opacity-100 hover:text-[var(--color-crisis)]',
          'disabled:cursor-default'
        )}
      >
        <ThumbsDownIcon />
      </button>
    </div>
  )
}
```

The opacity is set to 70% (not 50%) so icons are discoverable without being intrusive. After selection, the chosen icon highlights in primary/crisis color and both disable.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm --filter @web test -- feedback-buttons
```
Expected: all 5 PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add components/chat/feedback-buttons.tsx components/chat/__tests__/feedback-buttons.test.tsx
git commit -m "feat(ui): add FeedbackButtons component for per-message thumbs up/down"
```

---

### Task 8: Wire feedback into ChatInterface and MessageBubble

**Files:**
- Modify: `cdai/apps/web/components/chat/chat-interface.tsx`
- Modify: `cdai/apps/web/components/chat/message-bubble.tsx`
- Modify: `cdai/apps/web/components/chat/__tests__/message-bubble.test.tsx`

- [ ] **Step 1: Write the failing tests**

Read `cdai/apps/web/components/chat/__tests__/message-bubble.test.tsx` first to understand the existing test shape, then add:

```typescript
// Append to the existing message-bubble test file:
import { FeedbackButtons } from '../feedback-buttons'

vi.mock('../feedback-buttons', () => ({
  FeedbackButtons: vi.fn(() => <div data-testid="feedback-buttons" />),
}))

describe('MessageBubble feedback buttons', () => {
  it('shows FeedbackButtons for ai messages that have a supabaseId', () => {
    const message: ChatMessage = {
      id: 'sdk-id', role: 'ai', content: 'Hello', intent: null,
      sessionId: 'sess-1', createdAt: '',
    }
    render(
      <MessageBubble
        message={message}
        supabaseId="supabase-uuid-123"
        onFeedback={vi.fn()}
      />
    )
    expect(screen.getByTestId('feedback-buttons')).toBeInTheDocument()
  })

  it('does not show FeedbackButtons for user messages', () => {
    const message: ChatMessage = {
      id: 'sdk-id', role: 'user', content: 'Hello', intent: null,
      sessionId: 'sess-1', createdAt: '',
    }
    render(
      <MessageBubble
        message={message}
        supabaseId="supabase-uuid-123"
        onFeedback={vi.fn()}
      />
    )
    expect(screen.queryByTestId('feedback-buttons')).not.toBeInTheDocument()
  })

  it('does not show FeedbackButtons when supabaseId is absent', () => {
    const message: ChatMessage = {
      id: 'sdk-id', role: 'ai', content: 'Hello', intent: null,
      sessionId: 'sess-1', createdAt: '',
    }
    render(<MessageBubble message={message} />)
    expect(screen.queryByTestId('feedback-buttons')).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm --filter @web test -- message-bubble
```
Expected: FAIL — `MessageBubble` does not accept `supabaseId` or `onFeedback` props.

- [ ] **Step 3: Update MessageBubble**

Replace `cdai/apps/web/components/chat/message-bubble.tsx`:

```typescript
import { cn } from '@cdai/ui'
import type { ChatMessage } from '@cdai/types'
import { FeedbackButtons } from './feedback-buttons'

interface Props {
  message: ChatMessage
  supabaseId?: string
  onFeedback?: (messageId: string, value: 1 | -1) => void
}

export function MessageBubble({ message, supabaseId, onFeedback }: Props) {
  if (message.role === 'crisis') return null
  if (message.role === 'system') {
    return (
      <div className="mx-auto w-full max-w-xs rounded-xl border border-[var(--color-border)] px-4 py-2 text-center text-xs text-[var(--color-text-secondary)]">
        {message.content}
      </div>
    )
  }

  const isUser = message.role === 'user'
  return (
    <div className={cn('flex flex-col', isUser ? 'items-end' : 'items-start')}>
      <div
        className={cn(
          'max-w-[78%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
          isUser
            ? 'bg-[var(--color-primary-dark)] text-white rounded-ee-sm'
            : 'bg-[var(--color-surface-tinted)] text-[var(--color-text-primary)] rounded-es-sm'
        )}
      >
        {message.content}
      </div>
      {!isUser && supabaseId && onFeedback && (
        <FeedbackButtons messageId={supabaseId} onFeedback={onFeedback} />
      )}
    </div>
  )
}
```

- [ ] **Step 4: Update chat-interface.tsx**

In `cdai/apps/web/components/chat/chat-interface.tsx`, make these changes:

**4a. Extend SdkMessage to include supabaseId:**
```typescript
interface SdkMessage {
  id: string
  role: SdkRole
  content: string
  supabaseId?: string  // Supabase UUID from X-Sage-Ai-Message-Id header
}
```

**4b. In `useStreamingChat.stream()`, read the header after `const res = await fetch(...)`:

Add after the `if (!res.ok || !res.body)` check:
```typescript
        const aiSupabaseId = res.headers.get('X-Sage-Ai-Message-Id') ?? undefined
```

Then, after the stream completes (after the `accumulated += decoder.decode()` line), update the assistant message with the supabaseId. Replace the final `setMessages` update pattern after the stream loop with:
```typescript
        // Stream complete — attach the Supabase message UUID for the feedback flow.
        if (aiSupabaseId) {
          setMessages((curr) =>
            curr.map((m) => (m.id === assistantId ? { ...m, supabaseId: aiSupabaseId } : m))
          )
        }
```

**4c. Add handleFeedback in ChatInterface:**
```typescript
  async function handleFeedback(messageId: string, value: 1 | -1) {
    try {
      await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messageId, value }),
      })
    } catch {
      // feedback is best-effort — do not surface errors to the user
    }
  }
```

**4d. Update the MessageBubble render call to pass the new props:**
```typescript
            return (
              <MessageBubble
                key={m.id}
                message={{
                  id: m.id,
                  role,
                  content,
                  intent: null,
                  sessionId: initialSession?.id ?? '',
                  createdAt: '',
                }}
                supabaseId={m.supabaseId}
                onFeedback={handleFeedback}
              />
            )
```

- [ ] **Step 5: Run all frontend tests**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm --filter @web test
```
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add \
  apps/web/components/chat/chat-interface.tsx \
  apps/web/components/chat/message-bubble.tsx \
  apps/web/components/chat/__tests__/message-bubble.test.tsx
git commit -m "feat(chat): wire FeedbackButtons into chat UI via X-Sage-Ai-Message-Id header"
```

---

## Final: Run full test suites

- [ ] **Run Python tests**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
python -m pytest tests/ -v
```
Expected: all PASS

- [ ] **Run frontend tests**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm test
```
Expected: all PASS
