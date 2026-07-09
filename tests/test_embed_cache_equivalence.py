"""EMBED-CACHE ship gate — pre-written BEFORE the optimization exists (TDD: the test encodes
the contract, the code must satisfy it).

EMBED-CACHE (arch §20.2) caches the BGE-M3 query embedding of `message_en` so S3 (Layer 1
crisis encode) and skill_select Tier 2 don't encode the same text twice. S3 is the safety
path, so under "safety is deterministic" a latency win MUST NOT perturb crisis detection.

THE INVARIANT THIS GATES (not a frozen snapshot):
    for all text:  cached_get_embedding(text) == get_embedding(text)
computed FRESH on both sides over the FULL crisis corpus. We do NOT hardcode today's vectors
as golden expectations — a legitimate model/normaliser update must be free to change the
embeddings, as long as cached == uncached still holds. The gate is equivalence, not a 2026
freeze.

Three properties, each a real failure mode rather than a green check:
  1. Assert the EMBEDDING (the layer being changed), not just the verdict — bit-for-bit — AND
     the downstream S3 score/verdict as an end-to-end backstop. Both, not either: a near-miss
     vector that happens not to flip THIS corpus's verdicts is exactly the silent perturbation
     the rule exists to catch.
  2. Exercise the cache's failure modes (the key, not the hit): cold miss, warm hit, and
     key-collision safety — two genuinely different `message_en` must never share an entry
     (covers whitespace/normalisation variants, script/Arabizi variants, empty/degenerate).
  3. Pin the corpus and make a miss LOUD: assert the full corpus ran (count floor + the test
     iterated every phrase), and on any per-phrase divergence fail with the phrase NAMED.

REFERENCE (exists today): `get_embedding` (uncached encode) and `check_s3` (verdict) in
sage_poc.safety.s3_semantic; corpus = crisis_phrases.json via `_load_phrase_texts`.

CONTRACT the EMBED-CACHE implementation MUST expose for the cache-specific tests to run
(until then they SKIP with a clear reason — see _CACHE_API):
  * cached_get_embedding(text: str) -> list[float]   # keyed cache over get_embedding
  * reset_query_embedding_cache() -> None            # clear (for cold-miss observation)
  * query_embedding_cache_key(text: str) -> str      # the cache key derivation
Definition-of-done for EMBED-CACHE includes: these symbols exist and this file goes green
(the skips lift). Do not ship EMBED-CACHE with this file skipped.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pytest

from sage_poc.safety import s3_semantic
from sage_poc.safety.s3_semantic import (
    S3_THRESHOLD,
    check_s3,
    get_embedding,
    _ensure_s3_ready,
    _load_phrase_texts,
)

# Corpus floor: 84 phrases as of manifest 68d7b889d772 (2026-06-25). A deliberate clinical
# change updates this floor in the same commit; a SILENT shrink (refactor drops phrases) fails
# here. Floor is >=, so legitimate growth passes untouched.
EXPECTED_MIN_PHRASES = 84

# Resolve the to-be-built cache API once. Absent until EMBED-CACHE lands → cache tests skip.
try:
    _CACHE_API = (
        s3_semantic.cached_get_embedding,        # type: ignore[attr-defined]
        s3_semantic.reset_query_embedding_cache, # type: ignore[attr-defined]
        s3_semantic.query_embedding_cache_key,   # type: ignore[attr-defined]
    )
    _CACHE_READY = True
except AttributeError:
    _CACHE_API = None
    _CACHE_READY = False

_requires_cache = pytest.mark.skipif(
    not _CACHE_READY,
    reason="EMBED-CACHE not implemented yet — pre-written ship gate (cached_get_embedding / "
           "reset_query_embedding_cache / query_embedding_cache_key absent). DoD: implement, "
           "remove this skip, file goes green.",
)


def _corpus() -> list[str]:
    return _load_phrase_texts()


def _s3_score(embedding: list[float]) -> float:
    """Replicate check_s3's cosine-vs-index scoring for an arbitrary query embedding, so we can
    compare the DOWNSTREAM verdict produced by the uncached vs cached vector (property 1)."""
    assert _ensure_s3_ready(), "S3 index unavailable — cannot evaluate the gate"
    q = np.array(embedding, dtype=np.float32)
    n = np.linalg.norm(q)
    if n < 1e-9:
        return 0.0
    q = q / n
    return float((s3_semantic._embedding_index @ q).max())


# ── Prerequisite + corpus-pinning tests (run NOW; no cache required) ──────────────────────

def test_reference_encoder_is_deterministic():
    """Caching is only sound if the encode is deterministic. If get_embedding(x) != get_embedding(x)
    bit-for-bit, NO cache can preserve S3 output — fail loudly before EMBED-CACHE is even attempted."""
    assert _ensure_s3_ready()
    for phrase in _corpus():
        a = np.array(get_embedding(phrase), dtype=np.float32)
        b = np.array(get_embedding(phrase), dtype=np.float32)
        assert np.array_equal(a, b), f"non-deterministic encode for phrase: {phrase!r}"


def test_crisis_corpus_pinned():
    """A future refactor must not silently shrink the corpus to a near-empty set and let the
    gate pass. Assert the floor and surface the manifest for diagnosis."""
    corpus = _corpus()
    manifest = hashlib.sha256("".join(sorted(corpus)).encode()).hexdigest()[:12]
    assert len(corpus) >= EXPECTED_MIN_PHRASES, (
        f"crisis corpus shrank to {len(corpus)} (floor {EXPECTED_MIN_PHRASES}); "
        f"manifest={manifest}. If intentional, lower EXPECTED_MIN_PHRASES in the SAME commit."
    )
    assert len(set(corpus)) == len(corpus), "duplicate phrases in crisis corpus"


# ── Property 1: cached vector == uncached vector AND downstream verdict identical ─────────

@_requires_cache
def test_cache_equals_uncached_embedding_and_verdict_over_full_corpus():
    cached_get_embedding, reset_query_embedding_cache, _ = _CACHE_API
    assert _ensure_s3_ready()
    reset_query_embedding_cache()
    corpus = _corpus()
    assert len(corpus) >= EXPECTED_MIN_PHRASES  # no silent subsample
    checked = 0
    for phrase in corpus:
        uncached = np.array(get_embedding(phrase), dtype=np.float32)
        cached = np.array(cached_get_embedding(phrase), dtype=np.float32)
        # (a) the layer being changed: bit-for-bit, zero tolerance
        assert np.array_equal(uncached, cached), (
            f"cached embedding != uncached for phrase: {phrase!r} "
            f"(max abs diff {np.abs(uncached - cached).max():.3e})"
        )
        # (b) end-to-end backstop: identical score AND identical crisis verdict
        s_un, s_ca = _s3_score(uncached.tolist()), _s3_score(cached.tolist())
        assert s_un == s_ca, f"S3 score diverged for {phrase!r}: uncached={s_un} cached={s_ca}"
        assert (s_un >= S3_THRESHOLD) == (s_ca >= S3_THRESHOLD), (
            f"S3 crisis VERDICT flipped for {phrase!r}: uncached={s_un} cached={s_ca} thr={S3_THRESHOLD}"
        )
        checked += 1
    assert checked == len(corpus), "gate did not run over the full corpus"


@_requires_cache
def test_check_s3_verdict_unchanged_with_cache_live():
    """Full-path backstop: check_s3 itself (which EMBED-CACHE rewires to the cache) must return
    the identical score for every corpus phrase as the uncached reference scoring."""
    cached_get_embedding, reset_query_embedding_cache, _ = _CACHE_API
    assert _ensure_s3_ready()
    reset_query_embedding_cache()
    for phrase in _corpus():
        reference = _s3_score(get_embedding(phrase))
        live = check_s3(phrase)
        assert reference == live, f"check_s3 diverged from uncached reference for {phrase!r}: {live} vs {reference}"


# ── Property 2: cache failure modes — cold miss, warm hit, key-collision safety ───────────

@_requires_cache
def test_cold_miss_then_warm_hit_returns_identical_vector():
    cached_get_embedding, reset_query_embedding_cache, _ = _CACHE_API
    assert _ensure_s3_ready()
    phrase = _corpus()[0]
    reset_query_embedding_cache()
    cold = np.array(cached_get_embedding(phrase), dtype=np.float32)   # miss → compute + store
    assert np.array_equal(cold, np.array(get_embedding(phrase), dtype=np.float32)), "cold miss returned wrong vector"
    warm = np.array(cached_get_embedding(phrase), dtype=np.float32)   # hit → stored vector
    assert np.array_equal(cold, warm), "warm hit returned a different vector than the cold miss stored"


@_requires_cache
def test_distinct_phrases_never_share_a_cache_entry():
    """The cache risk is the KEY, not the hit. Every genuinely-different crisis phrasing must get
    a distinct key — a key that collapses two distinct crisis utterances is a recall hole."""
    _, _, query_embedding_cache_key = _CACHE_API
    corpus = _corpus()
    keys = {}
    for phrase in corpus:
        k = query_embedding_cache_key(phrase)
        assert k not in keys or keys[k] == phrase, (
            f"key collision between distinct phrases: {phrase!r} and {keys[k]!r} share key {k!r}"
        )
        keys[k] = phrase
    assert len(keys) == len(corpus), "cache key collapsed distinct crisis phrases"


@_requires_cache
@pytest.mark.parametrize("base", ["I want to kill myself", "I want to end my life"])
def test_key_safety_invariant_on_normalisation_variants(base):
    """KEY-SAFETY INVARIANT: key(a)==key(b)  ⟹  encode(a)==encode(b). If a normalising key
    (whitespace, casing, script/Arabizi forms fed by the S5 normaliser) collapses two inputs
    onto one entry, their underlying encodes MUST be identical, or the cache returns a stale
    vector for one of them. Variants whose key differs are also safe (just no sharing)."""
    _, _, query_embedding_cache_key = _CACHE_API
    variants = [base, f"  {base}  ", f"{base}\n", base.upper(), base.lower()]
    for v in variants:
        if query_embedding_cache_key(v) == query_embedding_cache_key(base):
            ev = np.array(get_embedding(v), dtype=np.float32)
            eb = np.array(get_embedding(base), dtype=np.float32)
            assert np.array_equal(ev, eb), (
                f"key collapses {v!r} onto {base!r} but their encodes differ "
                f"(max abs diff {np.abs(ev - eb).max():.3e}) — cache would return a stale vector"
            )


@_requires_cache
@pytest.mark.parametrize("degenerate", ["", "   ", "\n\t"])
def test_degenerate_input_is_safe_and_non_colliding(degenerate):
    """Empty/whitespace input must not crash the cache nor share a key with a real crisis phrase."""
    cached_get_embedding, reset_query_embedding_cache, query_embedding_cache_key = _CACHE_API
    reset_query_embedding_cache()
    # Must not raise (S3 itself returns 0.0 for empty; the cache must be equally robust).
    try:
        cached_get_embedding(degenerate)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"cache raised on degenerate input {degenerate!r}: {exc!r}")
    real = _corpus()[0]
    assert query_embedding_cache_key(degenerate) != query_embedding_cache_key(real), (
        f"degenerate input {degenerate!r} shares a cache key with crisis phrase {real!r}"
    )
