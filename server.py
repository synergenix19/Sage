from __future__ import annotations
import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from sage_poc.graph import build_graph
from sage_poc.config import RESPONDER_MODEL
# Import SKILL_REGISTRY from the zero-dependency module — does NOT load numpy or BGE-M3.
from sage_poc.skill_ids import SKILL_REGISTRY as _SKILL_REGISTRY

app = FastAPI(title="SageAI API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # TODO: read from env var for production deployment
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

_graph = build_graph()

CRISIS_SIGNAL = "[[CRISIS_DETECTED]]"

# Closed set enforced at the HTTP boundary — v7 §5.5.
# crisis_state is client-ferried between turns; arbitrary strings must never enter the graph.
_VALID_CRISIS_STATES = frozenset({"none", "monitoring", "active_crisis", "resolved"})

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


async def _stream_words(text: str) -> AsyncGenerator[bytes, None]:
    for word in text.split():
        yield (word + " ").encode()
        await asyncio.sleep(0.025)


@app.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    if not req.messages or req.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="Last message must be from the user")

    state = _build_state(req)

    # ainvoke for all languages: full result is available before streaming begins,
    # so metadata (node path, model) can be set as response headers — never in the body.
    try:
        result = await _graph.ainvoke(state)
    except Exception as exc:
        logging.getLogger(__name__).error("[sage/graph] invoke failed: %s", exc)
        async def _err() -> AsyncGenerator[bytes, None]:
            yield b"\n[[SERVER_ERROR]]"
        return StreamingResponse(_err(), media_type="text/plain; charset=utf-8")

    path: list[str] = result.get("path") or []
    is_safe: bool = result.get("is_safe", True)
    response_text: str = result.get("response") or ""

    async def _body() -> AsyncGenerator[bytes, None]:
        if not is_safe:
            yield (CRISIS_SIGNAL + "\n").encode()
        async for chunk in _stream_words(response_text):
            yield chunk

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
            "X-Sage-Crisis-State":        result.get("crisis_state") or "none",
            # Trace fields: Priority 1
            "X-Sage-Intent":              result.get("primary_intent") or "",
            "X-Sage-Semantic-Score":      str(result.get("semantic_score") or ""),
            "X-Sage-Prompt-Layers":       json.dumps(result.get("prompt_layers") or []),
            "X-Sage-Token-Usage":         json.dumps(result.get("token_usage") or {}),
            "X-Sage-Turn-Number":         str(result.get("turn_count") or 0),
        },
    )
