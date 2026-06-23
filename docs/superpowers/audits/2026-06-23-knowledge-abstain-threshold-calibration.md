# Knowledge Retrieval Abstain Threshold — Calibration Finding

**Date:** 2026-06-23
**Question:** can `KNOWLEDGE_ABSTAIN_THRESHOLD` (postgres_repository.py, currently `0.0`)
be recalibrated to stop weak/off-topic info questions from surfacing irrelevant articles?
**Method:** ran real relevant + off-topic queries through the live Node 6 retrieval
(`PostgresKnowledgeRepository`) against the prod corpus (50 articles / 217 chunks).
Harness: `scripts/calibrate_knowledge_threshold.py`.

## Result: recalibration is NOT a viable fix. Both candidate signals fail to separate.

### RRF score (what the constant actually thresholds)
| set | range |
|---|---|
| relevant top RRF | 0.0164 – 0.0323 |
| off-topic top RRF | 0.0164 – 0.0164 |
| **gap** | **0.0000** |

RRF is rank-based: `1/(60+rank)`. The vector subsystem **always** returns a nearest
neighbour, so every query — relevant or not — gets a rank-1 result at 0.0164. Off-topic
queries don't just tie; they retrieve **wrong, sometimes alarming** articles:
- "what time does the pharmacy close" → **crisis-002-en**
- "how do I cook rice" → assertiveness-001
- "best phone to buy this year" → crisis-002-en

No value of the constant separates 0.0164 (relevant) from 0.0164 (off-topic). Raising it
abstains on everything; lowering it changes nothing.

### Vector cosine similarity (the signal RRF discards)
| set | range |
|---|---|
| relevant top cosine | 0.3351 – 0.7367 |
| off-topic top cosine | 0.3136 – 0.4456 |
| **gap** | **−0.1105** (overlap) |

Closer to a real signal (most relevant 0.55–0.74, most off-topic 0.31–0.45), but it still
overlaps because of two effects:
1. **Short/acronym queries embed poorly.** "what is CBT" → 0.3351 and retrieved
   `grounding-001`, not `cbt-001` (despite cbt-001-en existing). The 3-token query has too
   little signal for BGE-M3 to land the right chunk.
2. **Tangential off-topic lands mid-range.** "write me a cover letter" → 0.4456.

A cosine gate at ~0.5 would drop ~5/6 off-topic but also abstain on legitimate short
questions (CBT, the AR stress query at 0.4375) — a recall regression on real users.

## Conclusion & recommendation
The abstain problem is **retrieval-quality limited, not threshold-limited.** No single-score
cutoff fixes it on the current corpus. Do **not** change `KNOWLEDGE_ABSTAIN_THRESHOLD`
(it stays `0.0`; a change can only hurt).

The real fix is the one already flagged as a pre-prod TODO in `postgres_repository.py`:
1. **BGE-reranker-v2-m3 pass** over the top-N RRF candidates. A cross-encoder scores true
   query↔passage relevance on a calibrated scale, pushing off-topic down and relevant up so
   a meaningful abstain threshold becomes possible. **This is the unblocker.**
2. **Short-query handling** (query expansion / acronym normalisation) so "what is CBT"
   retrieves cbt-001 — independently improves both recall and the gap.
3. Corpus gaps compound it (e.g. no `cbt-001-ar`).

The reranker is a retrieval-architecture change and needs its own calibration + sign-off;
it is NOT a same-day constant bump. `scripts/calibrate_knowledge_threshold.py` is the
harness to re-run once the reranker lands.

## Severity
Medium. Today every info question returns *some* passage; off-topic ones can surface
tangential or crisis-flavoured articles into the L4 context block. The model + L4 directive
still compose the final answer (the passage is context, not forced output), so this is a
relevance/quality issue, not a safety-gate failure — but it should be fixed via the reranker
before broad pilot exposure.
