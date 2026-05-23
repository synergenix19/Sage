"""BGE-M3 embedding wrapper for the unified memory layer (Task 3.2).

Model is loaded lazily on first call and cached for the process lifetime.
No model is instantiated at import time.
"""
from __future__ import annotations

import asyncio
from functools import lru_cache


@lru_cache(maxsize=1)
def _get_model():
    """Return a loaded SentenceTransformer for BAAI/bge-m3.

    Uses lru_cache so the model is loaded exactly once per process.
    Import of SentenceTransformer is deferred to this function so that the
    heavy dependency is not triggered at module import time.
    """
    from sentence_transformers import SentenceTransformer  # noqa: PLC0415

    return SentenceTransformer("BAAI/bge-m3")


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
