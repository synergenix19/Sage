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
    # session_id is received from the client but intentionally not stored in SageState —
    # the graph has no concept of sessions; persistence is the frontend's responsibility.
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
                # Accumulate all node outputs; later nodes overwrite earlier keys.
                # output_gate (last node) sets the final "response" — correct by graph order.
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
        try:
            result = await asyncio.to_thread(_graph.invoke, state)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("[sage/graph] invoke failed: %s", exc)
            yield b"[[SERVER_ERROR]]"
            return
        response = result.get("response") or ""
        is_safe = result.get("is_safe", True)
        if not is_safe:
            yield (CRISIS_SIGNAL + "\n").encode()
        async for chunk in _stream_words(response):
            yield chunk
    else:
        try:
            async for chunk in _stream_events(state):
                yield chunk
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("[sage/graph] astream_events failed: %s", exc)
            yield b"[[SERVER_ERROR]]"


@app.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    if not req.messages or req.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="Last message must be from the user")
    state = _build_state(req)
    return StreamingResponse(_stream_response(state), media_type="text/plain; charset=utf-8")
