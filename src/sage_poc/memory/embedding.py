"""BGE-M3 embedding wrapper for the unified memory layer (Task 3.2).

Model is loaded lazily on first call and cached for the process lifetime.
No model is instantiated at import time.
"""
from __future__ import annotations

import asyncio
from functools import lru_cache


@lru_cache(maxsize=1)
def _get_model():
    """Return the shared BGE-M3 model from skill_select — loaded once per process.

    Reuses the skill_select model instance to avoid loading a second copy of BAAI/bge-m3.
    """
    from sage_poc.nodes.skill_select import _ensure_semantic_ready, _model  # noqa: PLC0415
    _ensure_semantic_ready()
    return _model


def get_embedding(text: str) -> list[float]:
    """Return a 1024-dim BGE-M3 embedding for *text* as a plain list of floats.

    The vector is L2-normalised (``normalize_embeddings=True``), matching the
    convention used by the skill-select semantic search layer.
    """
    model = _get_model()
    result = model.encode([text], normalize_embeddings=True)[0]
    # numpy arrays expose .tolist(); plain lists (e.g. from mocks) do not.
    return result.tolist() if hasattr(result, "tolist") else list(result)


async def get_embedding_async(text: str) -> list[float]:
    """Async variant of get_embedding — offloads CPU work to the default executor.

    Uses ``run_in_executor(None, ...)`` so the event loop is not blocked during
    model inference.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_embedding, text)
