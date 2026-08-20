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
import json

import numpy as np
import pytest

from sage_poc.safety import s3_semantic
from sage_poc.safety.s3_semantic import (
    S3_THRESHOLD,
    check_s3,
    check_s3_bilingual,
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

# ── BILINGUAL EXTENSION (P2 Task 5) ────────────────────────────────────────────────────────
# check_s3_bilingual(text_en, text_ar) is the production entry point (safety_check_node calls
# it every turn, not check_s3 — see nodes/safety_check.py). Before this task only its EN-only
# dispatch (text_ar is None: EN and Arabizi turns route through check_s3 -> query_embedding,
# cached since P2 Task 4) was cached; the AR arm (text_ar set — the batched dual-encode path
# used for lang="ar" turns) re-encoded on every call. Resolve the to-be-built plural cache API
# (Step 2 of this task) the same way _CACHE_API is resolved above — absent until implemented.
try:
    _BILINGUAL_CACHE_API = (
        s3_semantic.cached_get_embeddings,  # type: ignore[attr-defined]
        s3_semantic.get_embeddings,         # type: ignore[attr-defined]
    )
    _BILINGUAL_CACHE_READY = True
except AttributeError:
    _BILINGUAL_CACHE_API = None
    _BILINGUAL_CACHE_READY = False

_requires_bilingual_cache = pytest.mark.skipif(
    not _BILINGUAL_CACHE_READY,
    reason="Bilingual EMBED-CACHE not implemented yet (cached_get_embeddings / get_embeddings "
           "absent). DoD: implement, remove this skip, file goes green.",
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


# ── BILINGUAL PROBE SET (P2 Task 5) ────────────────────────────────────────────────────────
# Arabizi (Gulf English) SI phrases reused verbatim from tests/test_rules_safety.py's S1
# Arabizi corpus (SK-AZ family) — this file does not invent a parallel phrase set.
ARABIZI_PHRASES = [
    "wallah i want to die",
    "abi amoot",
    "khalas i give up",
]


def _phrases_by_language() -> dict[str, list[str]]:
    data = json.loads(s3_semantic._PHRASES_PATH.read_text())
    out: dict[str, list[str]] = {}
    for entry in data["phrases"]:
        out.setdefault(entry.get("language", "en"), []).append(entry["text"])
    return out


def _ar_corpus() -> list[str]:
    """The crisis corpus's Arabic-language entries (language == 'ar' in crisis_phrases.json).
    23 entries as of the manifest this file already pins via EXPECTED_MIN_PHRASES."""
    return _phrases_by_language().get("ar", [])


def _bilingual_probe_set() -> list[tuple[str, str | None]]:
    """(text_en, text_ar) pairs spanning check_s3_bilingual's three production input shapes
    (mirrors safety_check_node's language branch, nodes/safety_check.py lines ~128-133):
      - AR corpus entries: text_ar set -> the batched dual-encode path this task caches
      - Arabizi:           text_ar=None -> delegates to check_s3 (single EN-only path,
                            already cached since P2 Task 4)
      - EN corpus entries: text_ar=None -> same single-encode path
    The EN carrier paired with each AR phrase is a fixed neutral placeholder: this file tests
    cache IDENTITY (does caching perturb the returned vector/score/verdict), not translation
    semantics, so only the AR text needs to vary within that group.
    """
    by_lang = _phrases_by_language()
    pairs: list[tuple[str, str | None]] = [
        ("I need to talk to someone about how I'm feeling.", ar) for ar in by_lang.get("ar", [])
    ]
    pairs += [(az, None) for az in ARABIZI_PHRASES]
    pairs += [(en, None) for en in by_lang.get("en", [])]
    return pairs


def _s3_score_bilingual_uncached(text_en: str, text_ar: str | None) -> float:
    """Uncached reference score for a (text_en, text_ar) pair: independent single-text
    encodes via the EXISTING get_embedding (bypasses any cache and any batching), scored
    against the S3 index the same way check_s3_bilingual does. Empirically confirmed (PR
    body) that this model/revision's batched encode([a, b]) == [encode([a]), encode([b])]
    bit-for-bit on CPU — so this reference is equivalent to, but independent of, however
    check_s3_bilingual internally batches its two texts, making it a fair uncached baseline
    regardless of which side of the implementation is being changed."""
    assert _ensure_s3_ready()
    if text_ar is None or not text_ar.strip():
        return _s3_score(get_embedding(text_en))
    if not text_en or not text_en.strip():
        return _s3_score(get_embedding(text_ar))
    en_emb = np.array(get_embedding(text_en), dtype=np.float32)
    ar_emb = np.array(get_embedding(text_ar), dtype=np.float32)
    q = np.stack([en_emb, ar_emb])
    norms = np.linalg.norm(q, axis=1, keepdims=True)
    norms[norms < 1e-9] = 1.0
    q = q / norms
    return float((s3_semantic._embedding_index @ q.T).max())


def test_bilingual_probe_set_covers_ar_arabizi_and_en():
    """Corpus-pinning sibling for the bilingual probe set (mirrors test_crisis_corpus_pinned):
    a future refactor must not silently shrink the AR arm and let the gate below pass on a
    near-empty set."""
    probe = _bilingual_probe_set()
    ar_count = sum(1 for _, ar in probe if ar is not None)
    assert ar_count >= 20, f"AR arm of the bilingual probe set shrank to {ar_count} (floor 20)"
    assert len(probe) == ar_count + len(ARABIZI_PHRASES) + len(_phrases_by_language().get("en", []))


@pytest.mark.slow
def test_bilingual_score_identical_across_repeat_calls_over_full_probe_set():
    """Property 1 sibling for check_s3_bilingual: calling it twice with the SAME
    (text_en, text_ar) pair must return a bit-identical score and an identical crisis
    VERDICT, for every pair in the bilingual probe set (AR corpus + Arabizi + EN).

    @slow (PR #566 fix-round-1, F2): the non-slow tier runs under conftest.py's
    _stub_bge_m3 zero-vector MagicMock, which trivially returns 0.0 == 0.0 for every pair
    regardless of whether the implementation is correct — a vacuous pass caught by review
    instrumentation, not by this test. Marked @slow so it exercises the real BGE-M3 model;
    run via `pytest tests/test_embed_cache_equivalence.py -m ""` (the file's default marker
    filter deselects @slow, matching the rest of this suite's convention) or the project's
    warmed/slow tier. It does NOT by itself prove a cache is wired (a deterministic uncached
    re-encode also passes this) — that is test_ar_arm_cache_hit_avoids_second_encode's job,
    below, which is intentionally NOT @slow (its call-count assertion is marker-independent —
    see that test's docstring).
    """
    assert _ensure_s3_ready()
    reset_query_embedding_cache = s3_semantic.reset_query_embedding_cache
    reset_query_embedding_cache()
    probe = _bilingual_probe_set()
    checked = 0
    for text_en, text_ar in probe:
        first = check_s3_bilingual(text_en, text_ar)
        second = check_s3_bilingual(text_en, text_ar)
        assert first == second, (
            f"check_s3_bilingual score diverged across repeat calls for "
            f"(text_en={text_en!r}, text_ar={text_ar!r}): first={first} second={second}"
        )
        assert (first >= S3_THRESHOLD) == (second >= S3_THRESHOLD), (
            f"check_s3_bilingual VERDICT flipped across repeat calls for "
            f"(text_en={text_en!r}, text_ar={text_ar!r}): first={first} second={second} "
            f"thr={S3_THRESHOLD}"
        )
        checked += 1
    assert checked == len(probe), "gate did not run over the full bilingual probe set"


def test_ar_arm_cache_hit_avoids_second_encode(monkeypatch):
    """CACHE-HIT EVIDENCE for the AR arm (Step 1 requirement): check_s3_bilingual's AR arm
    (text_ar set) must hit the cache on a repeat call with the SAME (text_en, text_ar) pair —
    the encoder must NOT be invoked a second time. Counts calls to the real encode() (a
    wraps= spy around the SAME model instance _warm_bge_m3_once warmed, or the non-slow
    zero-vector stub — either way the COUNT behavior under test is identical), so this
    exercises the actual production dispatch, not a reimplementation of it.

    PRE-IMPLEMENTATION (check_s3_bilingual always re-encodes both texts): RED — encode() is
    called again on the second, identical call.
    POST-IMPLEMENTATION (routes through cached_get_embeddings): GREEN — the second
    check_s3_bilingual call is a pure cache hit, zero additional model inference.

    Deliberately NOT @slow: unlike the score-value tests above, this test's assertion is a
    call COUNT, which is identical whether encode() is the real model or the non-slow tier's
    zero-vector stub — the stub is still a callable that increments the same counter. Keeping
    it in the fast tier means this specific regression (the AR arm silently falling out of
    the cache) is caught by the default CI safety-gate run, not only by a local `-m ""` pass.
    """
    assert _ensure_s3_ready()
    reset_query_embedding_cache = s3_semantic.reset_query_embedding_cache
    reset_query_embedding_cache()
    import sage_poc.nodes.skill_select as _ss

    text_en = "I want to end my life"
    text_ar = _ar_corpus()[0]
    real_encode = _ss._embed_model.encode
    calls = {"n": 0}

    def _counting_encode(*args, **kwargs):
        calls["n"] += 1
        return real_encode(*args, **kwargs)

    monkeypatch.setattr(_ss._embed_model, "encode", _counting_encode)

    check_s3_bilingual(text_en, text_ar)
    after_first = calls["n"]
    check_s3_bilingual(text_en, text_ar)
    after_second = calls["n"]

    assert after_second == after_first, (
        f"AR-arm cache MISS on repeat call: encode() was invoked {after_second - after_first} "
        f"more time(s) on an IDENTICAL (text_en, text_ar) pair — the AR arm is not sharing "
        f"the embed cache (encode call count {after_first} -> {after_second})"
    )


# AR threshold-spanning boundary pair (P2-3 ruling: bit-identity evidence must span the S3
# decision boundary, not just interior corpus phrases, which mostly score near 1.0 as verbatim
# entries or near 0.0 as unrelated text). Both paraphrases below are NOT verbatim corpus
# entries — checked at write time against crisis_phrases.json — naturalistic AR paraphrases
# empirically probed (see PR body) to land on either side of S3_THRESHOLD=0.8059 on this
# model/revision, device="cpu".
AR_JUST_BELOW_THRESHOLD = "تعبت نفسياً وودي انهي كل شي بحياتي"          # ~0.8040 (below)
AR_JUST_ABOVE_THRESHOLD = "تعبت نفسياً وبصراحة ودي انهي كل شي بحياتي"  # ~0.8083 (above)
# NEUTRAL EN carrier (~0.6085 on its own, well clear of S3_THRESHOLD=0.8059): check_s3_bilingual
# scores max(EN row, AR row) against the index, so an EN carrier that is ITSELF crisis-like would
# dominate the max and mask the AR arm's boundary position entirely — verified empirically that a
# crisis-toned EN carrier ("I want to end everything in my life", ~0.83 alone) does exactly this,
# making both boundary points score identically regardless of the AR text. This carrier's low score
# keeps the max attributable to the AR arm, which is the arm this test exists to isolate.
_AR_BOUNDARY_EN_CARRIER = "Can you help me understand this better?"


@pytest.mark.slow
@pytest.mark.parametrize(
    "text_ar,expect_fires",
    [(AR_JUST_BELOW_THRESHOLD, False), (AR_JUST_ABOVE_THRESHOLD, True)],
)
def test_ar_threshold_boundary_pair_cached_vs_uncached_verdict_identical(text_ar, expect_fires):
    """SAFETY-CRITICAL boundary evidence (ruling P2-3): the pair above straddles
    S3_THRESHOLD on the real model. For EACH point on the boundary, the cached-vs-uncached
    CRISIS-FIRE VERDICT (score >= S3_THRESHOLD) must be identical — not just the raw score.
    This is the assertion a future safety auditor needs stated directly: caching the AR arm
    must not move a real message from one side of the crisis threshold to the other.

    expect_fires pins the pair actually straddling the boundary as claimed (below=False,
    above=True) — without this, a broken/dominant EN carrier could make both points collapse
    onto the same side and this test would still pass on cached==uncached alone, silently
    proving nothing about the boundary. (This is exactly the failure mode caught empirically
    while writing this test: a crisis-toned EN carrier scored ~0.83 on its own and dominated
    check_s3_bilingual's max() over both languages, making both AR points fire identically
    regardless of the AR text — see _AR_BOUNDARY_EN_CARRIER's comment above.)

    Requires the real model (parametrized values are only meaningful at real BGE-M3 scores —
    the non-slow zero-vector stub would put both points at score 0.0, silently vacuous), so
    this is @slow and must be run with `-m ""` locally (Step 3 of this task's brief) alongside
    the fast-tier crisis suites.
    """
    assert _ensure_s3_ready()
    reset_query_embedding_cache = s3_semantic.reset_query_embedding_cache
    reset_query_embedding_cache()

    uncached_score = _s3_score_bilingual_uncached(_AR_BOUNDARY_EN_CARRIER, text_ar)
    assert (uncached_score >= S3_THRESHOLD) == expect_fires, (
        f"AR boundary probe {text_ar!r} did not land on the expected side of S3_THRESHOLD="
        f"{S3_THRESHOLD}: score={uncached_score} expect_fires={expect_fires}. The probe pair "
        f"no longer spans the boundary (or the EN carrier is dominating the max again) — "
        f"re-probe and update the pair, do not silently accept a same-side pair."
    )
    # Two live calls: the first populates the cache (cold), the second reads it (warm) —
    # exactly the cache's own cold-miss-then-warm-hit shape, exercised end-to-end through the
    # production entry point rather than the cache primitives directly.
    check_s3_bilingual(_AR_BOUNDARY_EN_CARRIER, text_ar)
    cached_score = check_s3_bilingual(_AR_BOUNDARY_EN_CARRIER, text_ar)

    assert uncached_score == cached_score, (
        f"AR boundary score diverged cached vs uncached: uncached={uncached_score} "
        f"cached={cached_score} thr={S3_THRESHOLD} text_ar={text_ar!r}"
    )
    assert (uncached_score >= S3_THRESHOLD) == (cached_score >= S3_THRESHOLD), (
        f"AR boundary CRISIS-FIRE VERDICT flipped by caching: "
        f"uncached_fires={uncached_score >= S3_THRESHOLD} "
        f"cached_fires={cached_score >= S3_THRESHOLD} text_ar={text_ar!r}"
    )


@pytest.mark.slow
@_requires_bilingual_cache
def test_cached_get_embeddings_equals_uncached_over_bilingual_probe_set():
    """Property 1, plural form: once cached_get_embeddings exists (Step 2 of this task),
    assert bit-for-bit vector equality AND downstream score/verdict equality directly against
    the plural cache API, over the full bilingual probe set — the deepest form of the
    equivalence-test convention this file already applies to the EN-only singular API above.

    The ground truth here is get_embedding PER TEXT (singular, one call each) — NOT the
    batched get_embeddings(texts) — because those two are no longer claimed equivalent
    (PR #566 fix-round-1, F1: BGE-M3 batch-pads the shorter row, so get_embeddings(texts) can
    diverge from [get_embedding(t) for t in texts] by ~1.5e-07; cached_get_embeddings encodes
    each miss individually for exactly this reason, so ITS ground truth is the per-item
    singular call, not the batch call).

    @slow (F2): the non-slow tier's zero-vector stub makes bit-identity trivially true
    regardless of correctness; run via `-m ""` against the real model.
    """
    cached_get_embeddings, _get_embeddings_unused = _BILINGUAL_CACHE_API
    assert _ensure_s3_ready()
    s3_semantic.reset_query_embedding_cache()
    probe = _bilingual_probe_set()
    checked = 0
    for text_en, text_ar in probe:
        texts = [text_en] if text_ar is None or not text_ar.strip() else [text_en, text_ar]
        # Per-item singular reference (NOT the batched get_embeddings) — see docstring above.
        uncached = np.array([get_embedding(t) for t in texts], dtype=np.float32)
        cached = np.array(cached_get_embeddings(texts), dtype=np.float32)
        # (a) the layer being changed: bit-for-bit, zero tolerance
        assert np.array_equal(uncached, cached), (
            f"cached_get_embeddings != [get_embedding(t) for t in texts] for {texts!r} "
            f"(max abs diff {np.abs(uncached - cached).max():.3e})"
        )
        # (b) end-to-end backstop: identical downstream score AND verdict
        norms = np.linalg.norm(uncached, axis=1, keepdims=True)
        norms[norms < 1e-9] = 1.0
        q_un = uncached / norms
        q_ca = cached / norms
        s_un = float((s3_semantic._embedding_index @ q_un.T).max())
        s_ca = float((s3_semantic._embedding_index @ q_ca.T).max())
        assert s_un == s_ca, f"S3 score diverged for {texts!r}: uncached={s_un} cached={s_ca}"
        assert (s_un >= S3_THRESHOLD) == (s_ca >= S3_THRESHOLD), (
            f"S3 crisis VERDICT flipped for {texts!r}: uncached={s_un} cached={s_ca} "
            f"thr={S3_THRESHOLD}"
        )
        checked += 1
    assert checked == len(probe), "gate did not run over the full bilingual probe set"


@pytest.mark.parametrize("fill_order", ["singular_first", "plural_first"])
def test_singular_and_plural_cache_agree_regardless_of_fill_order(fill_order):
    """PIN (PR #566 fix-round-1, F5): cached_get_embedding (singular) and cached_get_embeddings
    (plural) are DELIBERATELY independent implementations — reviewer-adjudicated shape (see
    cached_get_embedding's docstring): they share only the cache dict/lock/key scheme, not
    code, so that existing tests pinning get_embedding's exact miss-path call stay valid. That
    independence is exactly the thing that could let them silently diverge, so pin the
    invariant directly: whichever one FILLS the cache first for a given text, the OTHER one
    reading it back afterward returns the bit-identical vector — checked in both fill orders,
    since a one-directional check would miss an asymmetric bug (e.g. only the plural writer
    normalising differently on write).

    Not @slow: both implementations resolve to the same get_embedding call on a miss (F1), so
    this holds under the non-slow zero-vector stub too — it is pinning STRUCTURAL agreement
    between the two call paths, not a real-embedding value claim (that is covered by the
    @slow tests above).
    """
    s3_semantic.reset_query_embedding_cache()
    text = _corpus()[0]
    if fill_order == "singular_first":
        first = s3_semantic.cached_get_embedding(text)
        second = s3_semantic.cached_get_embeddings([text])[0]
    else:
        first = s3_semantic.cached_get_embeddings([text])[0]
        second = s3_semantic.cached_get_embedding(text)
    first_arr = np.array(first, dtype=np.float32)
    second_arr = np.array(second, dtype=np.float32)
    assert np.array_equal(first_arr, second_arr), (
        f"cached_get_embedding and cached_get_embeddings diverged for {text!r} "
        f"(fill_order={fill_order}, max abs diff {np.abs(first_arr - second_arr).max():.3e})"
    )
