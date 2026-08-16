# Ticket: a zero-norm query embedding degrades semantic routing to a silent no-match — no log, no marker, no metric

**Filed:** 2026-08-06 · **Source:** psychoed Phase 3, final pre-merge deflake of
`tests/test_psychoed_mechanism_a.py`'s two `@slow` semantic-consult tests — concern 3 of that
investigation, raised as a follow-up because the deflake trace is the evidence
**Status:** open — fix requires its OWN branch and normal review (`src/`-only change on the
embedding boundary shared by the S3 crisis path); explicitly NOT fixed in the deflake commit,
which was scoped to the test harness · **Type:** bug — observability gap in
`sage_poc/nodes/skill_select.py::_semantic_match_with_runner_up` /
`sage_poc/safety/s3_semantic.py::get_embedding`, of the **warmup-silent-failure class**
(degrade-and-continue with no signal), not a detection-logic defect
**Links:** commit `764e8151` (`tests/conftest.py` deflake — the test-side discovery that
produced this trace), `.superpowers/sdd/2026-07-30-psychoed-phase3-fixtures-plan/deflake-report.md`
(full characterization, concern 1), `src/sage_poc/safety/s3_semantic.py:65-73` (`get_embedding`),
`src/sage_poc/nodes/skill_select.py:385-433` (`_semantic_match_with_runner_up`),
`server.py:250-256` (`_warmup_task`'s BGE-M3 warmup — the production producer of this state),
`tests/test_classifier_degraded_marker.py` (the house degraded-marker precedent this fix should
mirror), `docs/2026-08-05-psychoed-phase3-closeout-145c4e43.md` (close-out ticket list, this entry)

## The gap

`_semantic_match_with_runner_up` accumulates per-skill scores with:

```python
raw_scores = np.dot(_anchor_embeddings, msg_emb)
skill_scores: dict[str, float] = {}
for i, sid in enumerate(_anchor_skill_ids):
    score = float(raw_scores[i])
    if score > skill_scores.get(sid, 0.0):
        skill_scores[sid] = score

if not skill_scores:
    return None, 0.0, None
```

If `msg_emb` is the zero vector, every `raw_scores[i]` is exactly `0.0`; `0.0 > 0.0` is False for
every anchor, so `skill_scores` ends up **empty** and the function short-circuits to
`(None, 0.0, None)`. That return value is indistinguishable from the legitimate, common,
expected outcome "this message genuinely matched no skill." The caller cannot tell the two apart:

- no exception is raised,
- nothing is logged at any level,
- no `path` marker is appended,
- no metric or audit field records that the embedding was degenerate,
- `semantic_score` is written as `0.0`, which is also what a real no-match writes.

The result is **semantic routing that is entirely dead while the model is resident and the anchor
index is healthy**, presenting as a service that has simply stopped matching anything. There is no
signal anywhere in the system that distinguishes it from a quiet day.

## Why this is reachable in production

`s3_semantic.get_embedding` is the shared embedding boundary:

```python
import sage_poc.nodes.skill_select as _ss
if _ss._embed_model is None:
    _ss._ensure_semantic_ready()
result = _ss._embed_model.encode([text], normalize_embeddings=True)[0]
```

Any condition that leaves `_embed_model` returning zeros — or leaves a zero vector memoised in
`_query_embedding_cache`, the bounded LRU that sits in front of this function — produces the state
above for every affected utterance, indefinitely (the cache holds 512 entries and has no TTL).
The production producer of this class is the BGE-M3 warmup path at `server.py:250-256`: a warmup
that fails or half-completes is the tracked **warmup-silent-failure** class (warn-and-continue,
silent crisis-path degradation), and this ticket is the routing-side expression of exactly that
class. `_warmup_reranker` was already hardened to block rather than warn-and-continue for this
reason (`server.py:210`, "This must BLOCK, never warn-and-continue (the warmup-silent-failure
anti-pattern)"); the bi-encoder embedding boundary has no equivalent guard on its *output*.

## Safety adjacency

**S3's crisis path shares `get_embedding`.** `s3_semantic._query_embedding`
(`cached_get_embedding` under `EMBED_CACHE_ENABLED`, `get_embedding` otherwise) is the same
function `check_s3` encodes through. A zero-norm query on that path drives every phrase-index
cosine to `0.0`, i.e. **below `S3_THRESHOLD` for every crisis phrase in the corpus** — S3 detects
nothing and reports nothing unusual. S3 is the sole detection path for crisis phrasings that carry
no S1 keyword (see `tests/test_crisis_smoke.py:100-102`), so this failure mode is a **silent total
loss of the semantic crisis tier**, not merely a routing-quality regression.

This ticket does not claim such an event has occurred in production. It claims the system has no
way to tell us if one did — which is the property the fix must change.

## Evidence

Observed directly, not inferred, in the 2026-08-06 deflake investigation. Running the real 78-file
unit-gate `CANDIDATES` list as one pytest invocation with `@slow` included, instrumentation
injected immediately before the failing test reported:

```
_embed_model: SentenceTransformer(... XLMRoberta ...)      <- REAL model, resident
SKILL_ROUTING_V2: False      SEMANTIC_THRESHOLD: 0.4593
n_anchor_ids: 25   _anchor_embeddings: (25, 1024) float32  abs-sum 609.09
top5: [('assertive_communication', 0.5736), ('interpersonal_effectiveness', 0.4716),
       ('psychoed_stress', 0.4653), ('values_clarification', 0.4352),
       ('act_psychological_flexibility', 0.4115)]
```

— a healthy model, a healthy anchor index, and a correct top-1 at 0.5736 against a 0.4593
threshold. And yet, for the identical inputs on the same line of the same process:

```
_semantic_match_with_runner_up('Whats the difference between assertive and aggressive',
                               '', 'en') -> (None, 0.0, None)
_consult_top_match -> None
```

The cause was a poisoned query-embedding cache:

```
EMBED_CACHE_ENABLED: True
cache size: 329
key in cache: True
cached vec abs-sum: 0.0
zero-vector entries in cache: 317 / 329
```

**317 of 329 live cache entries were zero vectors, and the system's only symptom was two
assertions failing in a test file.** Nothing logged, nothing marked, nothing measured. In
production there would have been no test to fail — the semantic tier would simply have gone quiet.

The *source* of the zero vectors in that trace was a test-harness artefact (the conftest
zero-vector stub writing through the shared `_embed_model` global into a cache the fixture did not
restore), fixed test-side in `764e8151`. That specific producer cannot occur in production, where
the model is always real. **The point of this ticket is the consumer, not that producer:** the
embedding boundary accepts a degenerate vector and converts it into a normal-looking negative
answer, so *any* future producer of a zero-norm embedding — warmup failure, a partially-loaded
model, a cache poisoned by a different route, a dtype/serialization bug — lands as silence. The
deflake proved the consumer's behavior with a real resident model; it did not create it.

## Fix shape (not implemented here)

`src/`-only, at the embedding boundary:

1. **Zero-norm guard.** In `s3_semantic.get_embedding` (the shared chokepoint — guarding here
   covers both the skill_select Tier-2 path and the S3 crisis path in one place), check the norm
   of the encoded vector before returning. A zero/degenerate vector is never a legitimate encoder
   output for non-empty input.
2. **Refuse to memoise it.** `cached_get_embedding` must not write a degenerate vector into
   `_query_embedding_cache`. Caching a bad embedding converts a transient fault into a permanent,
   per-utterance one — the mechanism that made the deflake trace so durable (no TTL, 512 entries).
3. **Degraded marker + log.** Emit a loud `WARNING` (with the same startup/observability
   discipline as `server.py`'s warmup logging) and surface a path marker so the condition is
   *distinguishable downstream*, not merely printed. Mirror the existing house precedent —
   `tests/test_classifier_degraded_marker.py`'s `classifier_degraded`: a pure additive path
   marker, no flag, PRESENT only on the degraded shape and ABSENT on genuine negatives (a real
   no-match must NOT carry it; that population belongs to ordinary routing). Naming should follow
   that convention (e.g. `embedding_degraded`).
4. **Decide the disposition deliberately, and record it.** Whether a zero-norm embedding should
   fail closed (raise / abstain, so the turn degrades visibly) or fail open (return no-match, but
   loudly) is a design call with different answers on the routing path and the S3 crisis path —
   the crisis path's fail-closed standard argues for the former there. The reviewing branch should
   state the chosen disposition per call site rather than inherit today's implicit one.

No behavior change is intended for healthy turns: on any non-degenerate embedding the guard is a
norm check and the routing result is byte-identical.

## Definition of done

1. **Regression test asserting the degraded marker fires on a zero-norm embedding.** Drive
   `_semantic_match_with_runner_up` (and the S3 path) with an encoder stubbed to return a zero
   vector and assert the degraded marker/log is PRESENT — the positive-path assertion the C3
   discipline requires, not merely "it still returns None."
2. **Companion negative case:** a genuine no-match (healthy embedding, all scores below threshold)
   must NOT carry the marker. Without this pair the marker is untrustworthy the moment it fires,
   and this is exactly the both-direction requirement the regression-by-improvement standing rule
   exists for.
3. **Cache-poisoning case:** assert a degenerate vector is never written to
   `_query_embedding_cache` (a transient fault must not become a durable one).
4. Verify healthy-turn routing is unchanged — the existing semantic suites
   (`tests/test_skill_select.py`, `tests/test_v2_*`, `tests/test_embed_cache_equivalence.py`,
   `tests/test_arabic_tier_guard.py`) green, with `test_embed_cache_equivalence.py` specifically
   confirming the guard did not perturb the cached-vs-uncached bit-identity contract it pins.
5. Add the new suite to the unit-gate `CANDIDATES` block if it is deterministic and LLM-free, per
   that file's standing "new deterministic safety suites should be ADDED" instruction.

## Cross-references

- `764e8151` — `fix(psychoed-f): deterministic test-side pin (disposition (i)) for
  semantic-consult batch flake (gate precondition)`. The test-side fix that produced this trace.
  It closes the *harness* leak (conftest now snapshots and restores
  `s3_semantic._query_embedding_cache` around every test, and clears it at setup of the `@slow`
  branch); it deliberately makes no `src/` change, which is why this consumer-side gap remains
  open and is filed separately.
- `.superpowers/sdd/2026-07-30-psychoed-phase3-fixtures-plan/deflake-report.md` — full
  characterization, including the falsified BGE-M3-nondeterminism hypothesis and the complete
  instrumentation trace excerpted above. This ticket is that report's concern 1.
- Tracked warmup-silent-failure class (warn-and-continue on BGE-M3 warmup failure, silent
  crisis-path degradation) — same class, this is its routing/embedding-boundary expression.
- `tests/test_classifier_degraded_marker.py` — the marker shape and the PRESENT/ABSENT contract
  discipline to copy.
