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

# Hoisted (P2 Task 5): this was 3 separate mid-function `import sage_poc.nodes.skill_select
# as _ss` statements (_ensure_s3_ready, get_embedding, check_s3_bilingual). skill_select does
# not import this module (checked: no circular import), so one module-level import replaces
# all three call sites.
import sage_poc.nodes.skill_select as _ss

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
    if _ss._embed_model is None:
        _ss._ensure_semantic_ready()
    result = _ss._embed_model.encode([text], normalize_embeddings=True)[0]
    return result.tolist() if hasattr(result, "tolist") else list(result)


# ── EMBED-CACHE (arch §20.2) ──
# Dedupe the BGE-M3 query encode of message_en shared by S3 (here) and skill_select Tier 2.
# Keyed on sha256(text) — NOT raw text — so plaintext user messages are not held as cache
# keys, and key(a)==key(b) ⇒ a==b ⇒ get_embedding(a)==get_embedding(b) (key-safety invariant
# the gate asserts). Bounded LRU; thread-safe (called inside asyncio.to_thread from S3 and
# skill_select). get_embedding is deterministic, so a hit returns a bit-identical vector.
# PRODUCTION HARDENING (deferred): a per-turn / state-scoped cache holds zero cross-turn user
# data; this process-global bounded form is the POC shape (hashed keys, capped). The PRIMITIVE
# always exists; config.EMBED_CACHE_ENABLED gates only the check_s3 / skill_select wiring.
import hashlib  # noqa: E402
import threading  # noqa: E402
from collections import OrderedDict  # noqa: E402

_QUERY_EMBED_CACHE_MAX = 512
_query_embedding_cache: "OrderedDict[str, list[float]]" = OrderedDict()
_query_embedding_cache_lock = threading.Lock()


def query_embedding_cache_key(text: str) -> str:
    """Cache key = sha256 of the exact text. Exact-match semantics (no normalisation)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def reset_query_embedding_cache() -> None:
    with _query_embedding_cache_lock:
        _query_embedding_cache.clear()


def cached_get_embedding(text: str) -> list[float]:
    """get_embedding with a bounded LRU; returns a vector bit-identical to get_embedding(text).
    Encode runs OUTSIDE the lock so concurrent turns don't serialise on it.

    Deliberately self-contained (does NOT delegate to cached_get_embeddings([text])[0]):
    existing unit tests (tests/test_s3_semantic.py) mock get_embedding directly and pin this
    exact miss-path call. cached_get_embeddings below is the independent batched sibling for
    the bilingual path; the two share the same cache dict/lock/key scheme, not code, so the
    EN-only single-text contract this function has always had stays byte-for-byte unchanged."""
    key = query_embedding_cache_key(text)
    with _query_embedding_cache_lock:
        hit = _query_embedding_cache.get(key)
        if hit is not None:
            _query_embedding_cache.move_to_end(key)
            return hit
    emb = get_embedding(text)
    with _query_embedding_cache_lock:
        _query_embedding_cache[key] = emb
        _query_embedding_cache.move_to_end(key)
        while len(_query_embedding_cache) > _QUERY_EMBED_CACHE_MAX:
            _query_embedding_cache.popitem(last=False)
    return emb


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Batch, UNCACHED encode of *texts* in ONE forward pass. Used as query_embeddings'
    fallback when EMBED_CACHE_ENABLED is False -- preserving check_s3_bilingual's original
    (pre-Task-5) one-forward-pass latency behaviour on that path -- and as a genuine-batch
    reference in tests.

    NOT bit-identical to get_embedding(text) row-by-row in general: BGE-M3 pads the shorter
    sequence when a batch's texts differ in token length, which can perturb the shorter row's
    embedding by up to ~1.5e-07 versus encoding it alone (measured; PR #566 fix-round-1, F1).
    cached_get_embeddings below does NOT call this function for its miss path for exactly
    this reason -- see its docstring."""
    if _ss._embed_model is None:
        _ss._ensure_semantic_ready()
    result = _ss._embed_model.encode(texts, normalize_embeddings=True)
    return [r.tolist() if hasattr(r, "tolist") else list(r) for r in result]


def cached_get_embeddings(texts: list[str]) -> list[list[float]]:
    """Batch version of cached_get_embedding (P2 Task 5): checks the shared LRU per text;
    each MISS is encoded INDIVIDUALLY via get_embedding(text) -- NOT a batched get_embeddings
    call -- so the vector written to the cache for a given text is bit-identical to
    get_embedding(text) REGARDLESS of what else was a cache-miss in the SAME call. Bit-identity
    is true BY CONSTRUCTION, not by an (incorrect) assumption that batch encode == single
    encode.

    (PR #566 fix-round-1, F1: an earlier version batched all misses into one get_embeddings()
    call for a one-forward-pass latency win on the cold path. BGE-M3 pads the shorter sequence
    when a batch's rows differ in token length, which measurably perturbed the shorter row's
    vector (~1.5e-07) versus its own single encode -- meaning a text's CACHED vector depended
    on what else happened to be a miss in the same call, which cache history must never affect
    on a safety surface. Fixed by dropping the batched-miss optimisation: the cold path costs
    one encode() call per miss (up to 2 for the AR arm) instead of one batched call for all
    misses (measured +66ms on a 2-text cold AR-arm call). The warm path -- a cache hit on
    either or both texts, which is what actually matters once the process has been running --
    is unaffected: still zero additional encode() calls.)

    Duplicate texts within the same call are encoded once (de-duped by cache key) and their
    result is fanned back out to every matching position.

    Lock discipline matches cached_get_embedding: cache reads happen under the lock, misses
    are encoded OUTSIDE it (so concurrent turns don't serialise on inference), and cache
    writes are taken back under the lock.
    """
    keys = [query_embedding_cache_key(t) for t in texts]
    results: list[list[float] | None] = [None] * len(texts)
    miss_positions: list[int] = []
    with _query_embedding_cache_lock:
        for i, key in enumerate(keys):
            hit = _query_embedding_cache.get(key)
            if hit is not None:
                _query_embedding_cache.move_to_end(key)
                results[i] = hit
            else:
                miss_positions.append(i)

    if miss_positions:
        # De-dupe misses by key so an identical text appearing twice in one call (e.g. the
        # EN carrier reused across a batch) is encoded once, not twice.
        miss_text_by_key: dict[str, str] = {}
        for i in miss_positions:
            miss_text_by_key.setdefault(keys[i], texts[i])
        # Each miss individually -- NOT get_embeddings(list) -- see docstring above (F1).
        emb_by_key = {key: get_embedding(text) for key, text in miss_text_by_key.items()}
        with _query_embedding_cache_lock:
            for key, emb in emb_by_key.items():
                _query_embedding_cache[key] = emb
                _query_embedding_cache.move_to_end(key)
            while len(_query_embedding_cache) > _QUERY_EMBED_CACHE_MAX:
                _query_embedding_cache.popitem(last=False)
        for i in miss_positions:
            results[i] = emb_by_key[keys[i]]

    return results  # type: ignore[return-value]


def query_embedding(text: str) -> list[float]:
    """The ONE flag-gated (EMBED_CACHE_ENABLED) query-embedding accessor. Used by both S3
    (check_s3, below) and skill_select Tier 2 (_semantic_match_with_runner_up) -- P2 Task 4
    mechanics-only consolidation: the two call sites previously duplicated this exact
    if-cache-else-encode shape (skill_select inlined its own copy). Caching semantics are
    UNCHANGED by the consolidation -- same key (sha256 of the exact text), same bound
    (_QUERY_EMBED_CACHE_MAX). Formerly private (`_query_embedding`); renamed on going
    cross-module. The plural sibling below (query_embeddings) is Task 5's bilingual batch
    accessor, same flag, same cache."""
    from sage_poc.config import EMBED_CACHE_ENABLED  # noqa: PLC0415
    return cached_get_embedding(text) if EMBED_CACHE_ENABLED else get_embedding(text)


def query_embeddings(texts: list[str]) -> list[list[float]]:
    """The plural sibling of query_embedding (P2 Task 5) -- the ONE flag-gated
    (EMBED_CACHE_ENABLED) accessor for check_s3_bilingual's AR arm. Same flag, same
    underlying cache/keying as query_embedding. When the cache is enabled, misses are encoded
    INDIVIDUALLY (see cached_get_embeddings' docstring, F1) so a text's vector never depends
    on what else was a miss in the same call. When disabled, falls back to get_embeddings'
    true one-forward-pass batch encode -- preserving check_s3_bilingual's pre-Task-5 latency
    behaviour on that (cache-off) path."""
    from sage_poc.config import EMBED_CACHE_ENABLED  # noqa: PLC0415
    return cached_get_embeddings(texts) if EMBED_CACHE_ENABLED else get_embeddings(texts)


def _max_similarity(embeddings: list[list[float]]) -> float:
    """Return the max cosine similarity between _embedding_index and ANY of the given query
    embeddings. Shared by check_s3 (single query) and check_s3_bilingual (EN+AR batch) so
    both paths run the identical index-dot-product arithmetic instead of two copies that can
    drift out of sync.

    Each embedding is defensively re-normalised (guards the near-zero-norm case check_s3
    always guarded, e.g. an all-zero vector from a degenerate encode); a degenerate embedding
    is dropped rather than propagating a NaN/Inf into the max. Returns 0.0 if every embedding
    is degenerate or the list is empty.
    """
    valid_rows = []
    for emb in embeddings:
        vec = np.array(emb, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm < 1e-9:
            continue
        valid_rows.append(vec / norm)
    if not valid_rows:
        return 0.0
    queries = np.stack(valid_rows)  # (K, 1024)
    scores: np.ndarray = _embedding_index @ queries.T  # (N_phrases, K)
    return float(scores.max())


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
        return _max_similarity([query_embedding(text)])
    except Exception as exc:
        _log.warning("[S3] Similarity check failed: %s", exc)
        return 0.0


def check_s3_bilingual(text_en: str, text_ar: str | None) -> float:
    """Return max cosine similarity across all (query, phrase) pairs, sharing the CACHED
    query embedding with the EN-only path (P2 Task 5 -- previously this path always
    re-encoded).

    For Arabic messages: looks up [text_en, text_ar] through query_embeddings, sharing the
    same LRU query_embedding uses for the EN-only path -- a cache hit on either or both
    texts skips inference entirely. A miss is encoded individually (get_embedding per miss,
    not a batched call) so a text's cached vector is bit-identical to get_embedding(text)
    regardless of what else was a miss at the same time (F1, PR #566 fix-round-1) -- the cold
    path costs one encode() call per miss (up to 2) rather than the original single batched
    forward pass; the warm path (cache hit) costs zero.
    For English/Arabizi messages (text_ar=None): delegates to check_s3 (single-text path,
    cached since P2 Task 4).
    Never raises.
    """
    if text_ar is None or not text_ar.strip():
        return check_s3(text_en)
    if not text_en or not text_en.strip():
        return check_s3(text_ar)
    if not _ensure_s3_ready():
        return 0.0
    try:
        return _max_similarity(query_embeddings([text_en, text_ar]))
    except Exception as exc:
        _log.warning("[S3] Bilingual batch check failed: %s", exc)
        return 0.0
