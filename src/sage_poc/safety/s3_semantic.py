"""S3: BGE-M3 semantic crisis detection.

Runs alongside S1 (lexicon) in safety_check_node. OR-fusion: S1 OR S3 catching
triggers the crisis protocol. Fail-open: any exception or timeout produces
score 0.0, safety_check_node continues with S1 result only.

Reuses the shared BGE-M3 model from sage_poc.memory.embedding (single instance,
already loaded by skill_select). No additional model weight loaded.

Threshold calibrated by scripts/calibrate_s3_threshold.py.
Must satisfy: all SF-1 GATE phrases score >= threshold, all SF-6 FP phrases score < threshold.
Re-run calibration after editing crisis_phrases.json.
"""
from __future__ import annotations
import json
import logging
import pathlib
import numpy as np

_log = logging.getLogger(__name__)

_PHRASES_PATH = pathlib.Path(__file__).parent / "crisis_phrases.json"

# Calibrated placeholder — updated after Task 3 (calibrate_s3_threshold.py) completes.
# v7 target: <50ms total for Layer 1. S3 embedding adds ~200-500ms per turn.
# Acceptable for POC; production requires async pre-warm and potential GPU inference.
S3_THRESHOLD: float = 0.82

_phrase_texts: list[str] = []
_embedding_index: np.ndarray | None = None  # shape (N, 1024), L2-normalised rows


def _load_phrase_texts() -> list[str]:
    data = json.loads(_PHRASES_PATH.read_text())
    return [entry["text"] for entry in data["phrases"]]


def _ensure_s3_ready() -> bool:
    global _phrase_texts, _embedding_index
    if _embedding_index is not None:
        return True
    try:
        from sage_poc.memory.embedding import get_embedding  # noqa: PLC0415
        texts = _load_phrase_texts()
        vecs = [np.array(get_embedding(t), dtype=np.float32) for t in texts]
        matrix = np.stack(vecs)  # (N, 1024)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        matrix = matrix / np.clip(norms, 1e-9, None)
        _phrase_texts = texts
        _embedding_index = matrix
        _log.info("[S3] Index built: %d phrases", len(texts))
        return True
    except Exception as exc:
        _log.warning("[S3] Index build failed, semantic safety check disabled: %s", exc)
        return False


def get_embedding(text: str) -> list[float]:
    from sage_poc.memory.embedding import get_embedding as _get  # noqa: PLC0415
    return _get(text)


def check_s3(text: str) -> float:
    """Return max cosine similarity between *text* and the crisis phrase index.

    Returns 0.0 when:
    - text is empty or whitespace
    - index is unavailable (model load failed)
    - any exception during embedding or similarity computation

    Never raises. Called from safety_check_node inside asyncio.wait_for.
    """
    if not text or not text.strip():
        return 0.0
    if not _ensure_s3_ready():
        return 0.0
    try:
        query = np.array(get_embedding(text), dtype=np.float32)
        norm = np.linalg.norm(query)
        if norm < 1e-9:
            return 0.0
        query = query / norm
        scores: np.ndarray = _embedding_index @ query  # (N,)
        return float(scores.max())
    except Exception as exc:
        _log.warning("[S3] Similarity check failed: %s", exc)
        return 0.0
