# Sage API Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bridge the SageAI LangGraph backend to the production Next.js frontend via a FastAPI streaming server, replacing the direct OpenRouter call in `/api/chat/route.ts` with a Sage-aware endpoint.

**Architecture:** A FastAPI server (`sage-poc/server.py`) wraps `build_graph()` and exposes a streaming `POST /chat` endpoint. The Next.js route replaces `streamText` from the AI SDK with a `fetch` to FastAPI, teeing the response body for simultaneous client streaming and Supabase persistence. Task 3 upgrades from fake word-delay streaming to real LLM token streaming for English conversations using `graph.astream_events()`, with a graceful word-delay fallback for Arabic (which requires a final translation step).

**Tech Stack:** FastAPI 0.115+, Uvicorn, LangGraph (existing), LangChain `ChatOpenAI` with `.astream()` (existing), `asyncio.to_thread` for sync↔async bridging, Next.js App Router + `ReadableStream.tee()` (existing frontend), Supabase (existing), `langdetect` (existing, reused for language pre-detection in server)

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `sage-poc/pyproject.toml` | Modify | Add `fastapi`, `uvicorn` to main deps; `requests`, `httpx` to dev |
| `sage-poc/server.py` | Create | FastAPI streaming chat server wrapping the compiled graph |
| `sage-poc/tests/test_server.py` | Create | Endpoint tests: bad request, happy path (slow), crisis (fast) |
| `cdai/apps/web/app/api/chat/route.ts` | Modify | Replace `streamText` with `fetch` to FastAPI; tee stream for persistence |
| `cdai/apps/web/.env.local` | Modify | Add `SAGE_API_URL=http://localhost:8000` |
| `sage-poc/src/sage_poc/nodes/freeflow_respond.py` | Modify (Task 3) | `async def` node; replace `.invoke()` with `.astream()` |
| `sage-poc/src/sage_poc/nodes/low_confidence_respond.py` | Modify (Task 3) | Same async upgrade |

---

## Task 1: FastAPI Server with Fake Streaming

**Files:**
- Modify: `sage-poc/pyproject.toml`
- Create: `sage-poc/server.py`
- Create: `sage-poc/tests/test_server.py`

### Why fake streaming for Task 1?

The LangGraph nodes currently use synchronous `.invoke()`. Task 1 gets the integration working end-to-end using `asyncio.to_thread(_graph.invoke, state)` (non-blocking sync call) followed by word-by-word yield with 25ms delay — identical UX to AI typing. Task 3 upgrades to real token streaming once the nodes are async.

---

- [ ] **Step 1.1: Write failing tests for the FastAPI server**

Create `sage-poc/tests/test_server.py`:

```python
import pytest
from fastapi.testclient import TestClient


def get_client():
    from server import app
    return TestClient(app)


def test_chat_bad_request_empty_messages():
    client = get_client()
    res = client.post("/chat", json={"messages": [], "session_id": "test"})
    assert res.status_code == 400


def test_chat_bad_request_last_message_not_user():
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "assistant", "content": "Hello"}],
        "session_id": "test",
    })
    assert res.status_code == 400


def test_chat_crisis_message_has_signal():
    # "end it all" is a CRISIS_KEYWORD — triggers keyword match, no LLM call.
    # _crisis_response_node returns a hardcoded string. Zero API calls.
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": "test-session",
    }, timeout=10)
    assert res.status_code == 200
    assert res.text.startswith("[[CRISIS_DETECTED]]")


@pytest.mark.slow
def test_chat_returns_text_for_valid_message():
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I've been feeling really anxious lately."}],
        "session_id": "test-session",
    }, timeout=30)
    assert res.status_code == 200
    assert len(res.text.strip()) > 10
```

- [ ] **Step 1.2: Run tests to verify they fail (server module missing)**

Run from `sage-poc/`:
```bash
uv run pytest tests/test_server.py -v -k "not slow"
```

Expected: `ModuleNotFoundError: No module named 'server'`

- [ ] **Step 1.3: Add dependencies to pyproject.toml**

Open `sage-poc/pyproject.toml`. Add `fastapi` and `uvicorn` to the `[project]` `dependencies` list, and `requests` + `httpx` to `[project.optional-dependencies]` dev. Also add `pythonpath = ["."]` to `[tool.pytest.ini_options]` so `from server import app` resolves in tests.

Final `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "sage-poc"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "langgraph>=1.0.0,<2.0.0",
    "langchain-openai>=1.0.0,<2.0.0",
    "langchain-core>=1.0.0,<2.0.0",
    "langdetect>=1.0.9,<2.0.0",
    "pydantic>=2.0.0,<3.0.0",
    "python-dotenv>=1.0.0,<2.0.0",
    "fastapi>=0.115.0,<1.0.0",
    "uvicorn>=0.30.0,<1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "requests>=2.32.0,<3.0.0",
    "httpx>=0.27.0,<1.0.0",
]

[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow (requires Ollama or real LLM)",
]
pythonpath = ["."]

[tool.hatch.build.targets.wheel]
packages = ["src/sage_poc"]
```

- [ ] **Step 1.4: Sync dependencies**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc && uv sync
```

Expected: lock file updated, fastapi and uvicorn installed.

- [ ] **Step 1.5: Create server.py**

Create `sage-poc/server.py`:

```python
from __future__ import annotations
import asyncio
from collections.abc import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from sage_poc.graph import build_graph

app = FastAPI(title="SageAI API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # TODO: read from env var for production deployment
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

_graph = build_graph()

CRISIS_SIGNAL = "[[CRISIS_DETECTED]]"


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    session_id: str


def _build_state(req: ChatRequest) -> dict:
    previous = req.messages[:-1]
    current = req.messages[-1]
    history = [
        {"role": m.role if m.role == "user" else "assistant", "content": m.content}
        for m in previous
    ]
    turn_count = sum(1 for m in previous if m.role != "user")
    return {
        "raw_message": current.content,
        "detected_language": "en",      # safety_check_node overwrites
        "message_en": current.content,  # safety_check_node overwrites for Arabic
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 5,
        "engagement": 7,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": turn_count,
        # Raw message pairs from the client. compose_prompt() in freeflow_respond.py
        # windows this to the last 4 turns — windowing is the graph's responsibility.
        "conversation_history": history,
    }


async def _stream_words(text: str) -> AsyncGenerator[bytes, None]:
    for word in text.split():
        yield (word + " ").encode()
        await asyncio.sleep(0.025)


async def _stream_response(state: dict) -> AsyncGenerator[bytes, None]:
    result = await asyncio.to_thread(_graph.invoke, state)
    response = result.get("response") or ""
    is_safe = result.get("is_safe", True)
    if not is_safe:
        yield (CRISIS_SIGNAL + "\n").encode()
    async for chunk in _stream_words(response):
        yield chunk


@app.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    if not req.messages or req.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="Last message must be from the user")
    state = _build_state(req)
    return StreamingResponse(_stream_response(state), media_type="text/plain; charset=utf-8")
```

- [ ] **Step 1.6: Run tests to verify they pass**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc && uv run pytest tests/test_server.py -v -k "not slow"
```

Expected: 3 tests PASS — `test_chat_bad_request_empty_messages`, `test_chat_bad_request_last_message_not_user`, `test_chat_crisis_message_has_signal`

- [ ] **Step 1.7: Manual smoke test — start the server**

In one terminal:
```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc && uv run uvicorn server:app --reload --port 8000
```

Expected: `INFO: Application startup complete.`

In another terminal:
```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "I feel overwhelmed with work"}], "session_id": "demo"}' 
```

Expected: streaming text appears word by word over ~2-3 seconds.

- [ ] **Step 1.8: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git add pyproject.toml uv.lock server.py tests/test_server.py
git commit -m "feat: add FastAPI streaming server wrapping LangGraph graph"
```

---

## Task 2: Next.js Route Update

**Files:**
- Modify: `cdai/apps/web/app/api/chat/route.ts`
- Modify: `cdai/apps/web/.env.local`

### What changes and what stays

**Removed:** `streamText`, `KNOWLEDGE_SYSTEM`, `EMOTIONAL_SYSTEM`, `CRISIS_SYSTEM_ADDITION`, `CHAT_MODEL` — Sage's graph handles all AI routing and response generation.

**Kept:** `generateText` for `classifyIntent()` (intent stored in Supabase for analytics) and session naming. All Supabase persistence logic is preserved, moved to a background async IIFE that reads from a tee'd copy of the FastAPI response stream.

**Crisis detection shift:** Previously the LLM was prompted to prepend `[[CRISIS_DETECTED]]`. Now `server.py` prepends it when `is_safe is False`. The frontend's `useStreamingChat` hook already reads raw bytes and handles the prefix — no frontend changes needed.

---

- [ ] **Step 2.1: Write failing test (manual)**

With the server from Task 1 NOT running:

```bash
cd /Users/knowledgebase/Documents/Sage/cdai && pnpm dev
```

Send a message in the chat UI. Expected: the browser console shows a 200 with working response (still hitting OpenRouter directly). Verify the chat works BEFORE the change.

- [ ] **Step 2.2: Add SAGE_API_URL to .env.local**

Open `cdai/apps/web/.env.local`. Append:

```
SAGE_API_URL=http://localhost:8000
```

- [ ] **Step 2.3: Replace route.ts**

Replace the full contents of `cdai/apps/web/app/api/chat/route.ts` with:

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

export async function POST(req: Request) {
  const { messages, sessionId } = await req.json() as {
    messages: { role: string; content: string }[]
    sessionId: string
  }

  if (!sessionId || !messages?.length) {
    return new Response('Bad Request', { status: 400 })
  }

  const lastMessage = messages[messages.length - 1]?.content ?? ''
  const intent = await classifyIntent(lastMessage)

  const supabase = await createClient()
  await supabase.from('messages').insert({
    session_id: sessionId,
    role: 'user',
    content: lastMessage,
    intent,
  })

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

      const isCrisis = accumulated.startsWith(CRISIS_SIGNAL)
      const content = isCrisis
        ? accumulated.slice(CRISIS_SIGNAL.length).trimStart()
        : accumulated

      await supabase.from('messages').insert({
        session_id: sessionId,
        role: isCrisis ? 'crisis' : 'ai',
        content,
        intent,
      })

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
        })
        await supabase.from('chat_sessions')
          .update({ name: sessionName.trim(), updated_at: new Date().toISOString() })
          .eq('id', sessionId)
      }
    } catch (err) {
      console.error('[chat/persist] failed:', err)
    }
  })()

  return new Response(clientStream, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  })
}
```

- [ ] **Step 2.4: Run TypeScript check**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai && pnpm --filter web tsc --noEmit
```

Expected: no errors.

- [ ] **Step 2.5: Manual integration test**

Ensure the FastAPI server is running (`uv run uvicorn server:app --reload --port 8000` in the `sage-poc/` directory), then:

```bash
cd /Users/knowledgebase/Documents/Sage/cdai && pnpm dev
```

Open `http://localhost:3000` and send a message. Verify:
1. Response streams in (word by word)
2. No browser console errors
3. Check Supabase table `messages` — user message and AI response both appear
4. Send `I want to end it all` — verify the CrisisCard component appears in the UI

- [ ] **Step 2.6: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/app/api/chat/route.ts apps/web/.env.local
git commit -m "feat: route chat through FastAPI/Sage instead of OpenRouter directly"
```

---

## Task 3: Real Token Streaming (English Path)

**Files:**
- Modify: `sage-poc/src/sage_poc/nodes/freeflow_respond.py`
- Modify: `sage-poc/src/sage_poc/nodes/low_confidence_respond.py`
- Modify: `sage-poc/server.py`
- Modify: `sage-poc/tests/test_server.py`

### Streaming architecture

`graph.astream_events(state, version="v2")` propagates `on_chat_model_stream` events for each token from LangChain async LLM calls. These events carry `metadata.langgraph_node` = the node name. By making `freeflow_respond_node` and `low_confidence_respond_node` async and using `llm.astream()`, their tokens stream through.

**Language routing in server.py:** Arabic messages require a final translation step in `output_gate_node` (Ollama call, sync). Streaming the English draft to an Arabic user then stopping is bad UX. Pre-detect language with `langdetect.detect()` (no API call, pure Python) BEFORE calling the graph. If Arabic → fall back to `asyncio.to_thread(graph.invoke)` + word-delay on the translated result.

**Hardcoded paths (crisis, scope_refusal, jailbreak):** These don't go through freeflow/low_confidence, so `streamed=False` after `astream_events` completes. Detect via accumulated `on_chain_end` outputs and emit the full response word-by-word.

---

- [ ] **Step 3.1: Write failing tests**

Add to `sage-poc/tests/test_server.py`:

```python
import inspect
from sage_poc.nodes.freeflow_respond import freeflow_respond_node
from sage_poc.nodes.low_confidence_respond import low_confidence_respond_node


def test_freeflow_node_is_coroutine():
    assert inspect.iscoroutinefunction(freeflow_respond_node)


def test_low_confidence_node_is_coroutine():
    assert inspect.iscoroutinefunction(low_confidence_respond_node)
```

- [ ] **Step 3.2: Run to verify they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc && uv run pytest tests/test_server.py::test_freeflow_node_is_coroutine tests/test_server.py::test_low_confidence_node_is_coroutine -v
```

Expected: 2 FAIL — `assert False` (nodes are currently sync)

- [ ] **Step 3.3: Make freeflow_respond_node async**

In `sage-poc/src/sage_poc/nodes/freeflow_respond.py`, replace the `freeflow_respond_node` function (lines 90–104) with:

```python
async def freeflow_respond_node(state: SageState, llm=None) -> dict:
    if llm is None:
        llm = get_responder()

    system_str, user_str = compose_prompt(state)
    messages = [
        {"role": "system", "content": system_str},
        {"role": "user", "content": user_str},
    ]

    chunks: list[str] = []
    async for chunk in llm.astream(messages):
        if chunk.content:
            chunks.append(chunk.content)
    response = "".join(chunks).strip()

    return {
        "response_en": response,
        "path": state["path"] + ["freeflow_respond"],
    }
```

- [ ] **Step 3.4: Make low_confidence_respond_node async**

In `sage-poc/src/sage_poc/nodes/low_confidence_respond.py`, replace `low_confidence_respond_node` with:

```python
async def low_confidence_respond_node(state: SageState, llm=None) -> dict:
    if llm is None:
        llm = get_responder()

    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": state["message_en"]},
    ]

    chunks: list[str] = []
    async for chunk in llm.astream(messages):
        if chunk.content:
            chunks.append(chunk.content)
    response = "".join(chunks).strip()

    return {
        "response_en": response,
        "path": state["path"] + ["low_confidence_respond"],
    }
```

- [ ] **Step 3.5: Run async node tests — verify they pass**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc && uv run pytest tests/test_server.py::test_freeflow_node_is_coroutine tests/test_server.py::test_low_confidence_node_is_coroutine -v
```

Expected: 2 PASS

- [ ] **Step 3.6: Verify existing node + graph tests still pass (fast subset)**

The async nodes are called via `graph.invoke()` in existing tests. LangGraph handles async nodes in sync invocations using an internal event loop (safe when called from a thread with no running loop — which is the pytest context).

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc && uv run pytest tests/test_nodes.py tests/test_graph.py -v -k "not slow"
```

Expected: all fast tests PASS. If any fail, check that `asyncio.run()` nesting is not occurring (pytest runs sync by default — should be fine).

- [ ] **Step 3.7: Replace _stream_response in server.py**

Replace the `_stream_words` helper, `_stream_response` function, and add the new streaming infrastructure. The full updated `server.py`:

```python
from __future__ import annotations
import asyncio
from collections.abc import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langdetect import detect as _langdetect, LangDetectException
from pydantic import BaseModel

from sage_poc.graph import build_graph

app = FastAPI(title="SageAI API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # TODO: read from env var for production deployment
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

_graph = build_graph()

CRISIS_SIGNAL = "[[CRISIS_DETECTED]]"
_STREAMING_NODES = frozenset({"freeflow_respond", "low_confidence_respond"})


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    session_id: str


def _build_state(req: ChatRequest) -> dict:
    previous = req.messages[:-1]
    current = req.messages[-1]
    history = [
        {"role": m.role if m.role == "user" else "assistant", "content": m.content}
        for m in previous
    ]
    turn_count = sum(1 for m in previous if m.role != "user")
    return {
        "raw_message": current.content,
        "detected_language": "en",
        "message_en": current.content,
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 5,
        "engagement": 7,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": turn_count,
        # Raw message pairs from the client. compose_prompt() in freeflow_respond.py
        # windows this to the last 4 turns — windowing is the graph's responsibility.
        "conversation_history": history,
    }


async def _stream_words(text: str) -> AsyncGenerator[bytes, None]:
    for word in text.split():
        yield (word + " ").encode()
        await asyncio.sleep(0.025)


async def _stream_events(state: dict) -> AsyncGenerator[bytes, None]:
    """Real token streaming for English via graph.astream_events.

    Accumulates on_chain_end output dicts to reconstruct final state for
    hardcoded paths (crisis / scope_refusal / jailbreak) that emit no
    on_chat_model_stream events.
    """
    streamed = False
    accumulated_output: dict = {}

    async for event in _graph.astream_events(state, version="v2"):
        etype = event["event"]

        if etype == "on_chat_model_stream":
            node = event["metadata"].get("langgraph_node", "")
            if node in _STREAMING_NODES:
                content = event["data"]["chunk"].content or ""
                if content:
                    streamed = True
                    yield content.encode()

        elif etype == "on_chain_end":
            out = event["data"].get("output")
            if isinstance(out, dict):
                # Later nodes overwrite earlier keys. output_gate runs last and its
                # "response" value is the authoritative final output — correct by graph order.
                accumulated_output.update(out)

    if not streamed:
        response = accumulated_output.get("response") or ""
        is_safe = accumulated_output.get("is_safe", True)
        if not is_safe:
            yield (CRISIS_SIGNAL + "\n").encode()
        async for chunk in _stream_words(response):
            yield chunk


async def _stream_response(state: dict) -> AsyncGenerator[bytes, None]:
    # Pre-detect language for streaming-path routing only. safety_check_node (Node 1)
    # re-detects authoritatively using the same langdetect library and handles edge cases
    # (directional mark stripping, Arabic Unicode block override, code-switching). Do NOT
    # remove Node 1's detection — these serve different purposes: this chooses the
    # streaming strategy; Node 1 sets the pipeline language for all downstream nodes.
    try:
        is_arabic = _langdetect(state["raw_message"]) == "ar"
    except LangDetectException:
        is_arabic = False

    if is_arabic:
        # Arabic requires output_gate_node's translation to complete before streaming.
        # Run sync invoke in a thread, then word-delay stream the final translated response.
        result = await asyncio.to_thread(_graph.invoke, state)
        response = result.get("response") or ""
        is_safe = result.get("is_safe", True)
        if not is_safe:
            yield (CRISIS_SIGNAL + "\n").encode()
        async for chunk in _stream_words(response):
            yield chunk
    else:
        async for chunk in _stream_events(state):
            yield chunk


@app.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    if not req.messages or req.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="Last message must be from the user")
    state = _build_state(req)
    return StreamingResponse(_stream_response(state), media_type="text/plain; charset=utf-8")
```

- [ ] **Step 3.8: Run all fast server tests**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc && uv run pytest tests/test_server.py -v -k "not slow"
```

Expected: 5 PASS — 2 bad-request tests, 1 crisis signal test, 2 async-node tests.

- [ ] **Step 3.9: Manual streaming verification**

Restart the server (Ctrl+C then):
```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc && uv run uvicorn server:app --reload --port 8000
```

Test real token streaming:
```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "I have been feeling very anxious about my job"}], "session_id": "demo"}'
```

Expected: tokens appear in real-time (not all at once after a delay). The gap between words should feel natural, not uniform 25ms — this confirms `astream_events` is providing real LLM token cadence rather than the word-delay loop.

Test Arabic fallback:
```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "أشعر بالقلق الشديد"}], "session_id": "demo"}'
```

Expected: response in Arabic, word-by-word stream (uniform delay — confirms fallback path).

- [ ] **Step 3.10: Run slow integration test**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc && uv run pytest tests/test_server.py::test_chat_returns_text_for_valid_message -v -m slow
```

Expected: PASS, response text > 10 chars.

- [ ] **Step 3.11: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git add src/sage_poc/nodes/freeflow_respond.py src/sage_poc/nodes/low_confidence_respond.py server.py tests/test_server.py
git commit -m "feat: real token streaming for English via graph.astream_events"
```

---

## Self-Review

**Spec coverage:**

| Requirement | Task | Covered? |
|-------------|------|----------|
| FastAPI server wrapping build_graph() | 1 | ✅ |
| POST /chat with messages + session_id | 1 | ✅ |
| Streaming response (word delay) | 1 | ✅ |
| [[CRISIS_DETECTED]] prefix when is_safe=False | 1 | ✅ |
| Replace streamText in Next.js route | 2 | ✅ |
| Supabase persistence preserved | 2 | ✅ |
| Session naming preserved | 2 | ✅ |
| Real token streaming for English | 3 | ✅ |
| Arabic fallback to word-delay | 3 | ✅ |
| Hardcoded paths (crisis/scope/jailbreak) emit correct response | 3 | ✅ |

**Placeholder scan:** No TBD, no "implement later", all code blocks are complete, all file paths are exact.

**Type consistency:**
- `Message.role` is `str` throughout (not `Literal`) — allows "assistant" from frontend
- `CRISIS_SIGNAL = "[[CRISIS_DETECTED]]"` is identical in `server.py` and `route.ts`'s CRISIS_SIGNAL constant and the frontend's `chat-interface.tsx` constant
- `_build_state` returns all 22 `SageState` fields — verified against `state.py` TypedDict
- `_stream_events` references `_STREAMING_NODES` which matches the exact node names registered in `build_graph()` ("freeflow_respond", "low_confidence_respond")

**Known limitation documented in Task 3:** Arabic path does not get real token streaming. The word-delay fake streaming gives equivalent demo UX and the architecture is correct — upgrading Arabic to real streaming would require making `translate_to_arabic` async and streaming the Arabic tokens, which is out of scope for the POC.
