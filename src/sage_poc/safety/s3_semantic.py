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
# TODO: Run S3 on both message_en and raw Arabic text for bilingual coverage. Currently EN-only.
from __future__ import annotations
import json
import logging
import pathlib
import numpy as np

_log = logging.getLogger(__name__)

_PHRASES_PATH = pathlib.Path(__file__).parent / "crisis_phrases.json"

# Calibrated 2026-06-05 via scripts/calibrate_s3_threshold.py (corpus expanded 54→73 phrases).
# Gap = 0.3234 (unchanged). Re-run after editing crisis_phrases.json.
# SF-6 "الله ياخذني من هالدنيا" scored 0.6087 (must be < threshold).
# v7 target: <50ms total for Layer 1. S3 embedding adds ~200-500ms per turn.
# Acceptable for POC; production requires async pre-warm and potential GPU inference.
S3_THRESHOLD: float = 0.8059

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
        import sage_poc.nodes.skill_select as _ss  # noqa: PLC0415
        _ss._ensure_semantic_ready()  # ensure model is loaded
        texts = _load_phrase_texts()
        # Batch-encode all phrases in one call — matches skill_select's encoding pattern.
        # 48 sequential single-text calls took ~8-12s on Railway CPU (no ANE); one batched
        # call takes ~3-5s. Combined with startup warmup this path only runs once at boot.
        matrix = np.array(
            _ss._embed_model.encode(texts, normalize_embeddings=True, batch_size=32),
            dtype=np.float32,
        )
        _phrase_texts = texts
        _embedding_index = matrix
        _log.info("[S3] Index built: %d phrases", len(texts))
        return True
    except Exception as exc:
        _log.warning("[S3] Index build failed, semantic safety check disabled: %s", exc)
        return False


def get_embedding(text: str) -> list[float]:
    # Use _embed_model directly to avoid triggering _ensure_semantic_ready(), which
    # rebuilds the 20-skill embedding matrix (~5-8s on CPU). S3 only needs the model
    # loaded (guaranteed by _ensure_s3_ready()) and the phrase index (built above).
    import sage_poc.nodes.skill_select as _ss  # noqa: PLC0415
    if _ss._embed_model is None:
        _ss._ensure_semantic_ready()
    result = _ss._embed_model.encode([text], normalize_embeddings=True)[0]
    return result.tolist() if hasattr(result, "tolist") else list(result)


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
