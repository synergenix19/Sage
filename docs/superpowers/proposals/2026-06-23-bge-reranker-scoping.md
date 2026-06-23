# BGE-reranker-v2-m3 Retrieval Gate — Scoping (for authorization, not a build order)

**Date:** 2026-06-23
**Status:** SCOPING — produced so the calibration approach and eval bar are agreed
**before** any implementation. This document is the deliverable; the build is gated on
sign-off of the target below (same discipline as F3/F4: the agreed target is what makes it
conformant, not the code).
**Prerequisite finding:** `docs/superpowers/audits/2026-06-23-knowledge-abstain-threshold-calibration.md`
— a single-score cutoff (RRF or cosine) cannot gate relevance on the current corpus.

---

## 1. Why a reranker (the structural problem it solves)

Node 6 retrieval is hybrid RRF over `knowledge_articles` (vector + FTS, k=60). Measured
against the live corpus:
- **RRF score cannot gate relevance** — it is rank-based, and the vector subsystem always
  returns a rank-1 nearest neighbour, so off-topic queries score identically to relevant
  ones (gap 0.0000) and retrieve wrong/alarming articles ("pharmacy hours" → a crisis
  article).
- **Raw cosine overlaps** (gap −0.11) because short queries embed weakly.

A cross-encoder reranker scores the **(query, passage) pair jointly** rather than as two
independent embeddings, producing a calibrated relevance score on which a meaningful abstain
threshold *can* sit. This is the already-flagged pre-prod TODO in `postgres_repository.py`,
not new architecture.

## 2. What gets reranked (scope of the change)

- Retrieve top-N candidates via the existing hybrid RRF (proposed **N = 20**; cheap, RRF is
  fine as a *recall* stage — its weakness is *precision*, which the reranker supplies).
- Rerank those N with **BGE-reranker-v2-m3** → a relevance score per candidate.
- Apply a **single abstain threshold on the reranker score**: keep candidates above it; if
  none clear it, **ABSTAIN** (return `knowledge_abstain=True`, the existing closed-RAG
  contract). Return top-k (≤5) of those that clear.
- `KNOWLEDGE_ABSTAIN_THRESHOLD` (the RRF constant) stays `0.0`/retired in favour of the
  reranker threshold — the RRF stage no longer gates, it only recalls.

**Out of scope:** the v7-mandated migration to Azure AI Search + UAE-North reranker
(§20.1 CKPT-REGION) — this scopes the *POC-Postgres* reranker only. Same interface.

## 3. Calibration method (reuse the harness pattern)

- Extend `scripts/calibrate_knowledge_threshold.py` to emit **reranker** scores for the same
  RELEVANT vs OFF-TOPIC query sets, plus expanded sets per clinical topic (anxiety, CBT,
  depression, stress, sleep, grief, panic, self-worth, …) in **both EN and AR**.
- Find the threshold in the gap between the lowest RELEVANT reranker score and the highest
  OFF-TOPIC reranker score (same gap-analysis decision table as the sibling scripts).
- **Bilingual is mandatory** — Khaleeji-AR is the untested leap (cf. the semantic-routing
  Phase-0 reasoning); the AR reranker recall must be measured, not assumed from EN.
- Re-run on every corpus change or model-revision bump (the harness is the standing tool).

## 4. The target to AGREE before building (the conformance bar)

These numbers are the deliverable that authorizes the build. Proposed starting points —
**owner to set/confirm**:

| Dimension | Proposed target | Rationale |
|---|---|---|
| **Off-topic abstain rate** | ≥ 95% of off-topic queries abstain | the "pharmacy → crisis article" class must not reach a user |
| **Relevant recall** | ≥ 90% of in-corpus topical queries still retrieve their article | abstain must not silently swallow legitimate questions |
| **Crisis-article false-surface** | **0** off-topic queries surface an `is_crisis_content` article | hard floor — see §6 |
| **Short-query handling** | "what is CBT" retrieves cbt-001, not grounding | the measured failure; may need query expansion alongside the reranker |
| **Bilingual** | targets met **independently** in EN and Khaleeji-AR | AR is not assumed from EN |
| **Latency** | added rerank latency within the Node 6 budget (measure on Railway CPU) | reranker on CPU is the cost; N=20 keeps it bounded |

A recall/abstain trade-off is unavoidable; the agreed point on that curve is what sign-off
fixes. "Maximise precision" without a recall floor would abstain on everything.

## 5. Sequence (once the target is signed off)

1. Add reranker model load + warmup (parallels BGE-M3 warmup; CPU cost on Railway).
2. Insert rerank pass after RRF in `PostgresKnowledgeRepository.retrieve` (the marked TODO).
3. Calibrate threshold against the expanded bilingual eval set → record the value + gap.
4. Regression tests: off-topic abstains, relevant retrieves, crisis-floor = 0, both languages.
5. Verify in prod (the harness + live retrieval), then enable.

## 6. Sign-off gate — this is a CLINICAL gate, not a code-review gate

The abstain threshold the reranker enables is a **clinical-relevance gate on a mental-health
corpus**. "what time does the pharmacy close → crisis article" is a line in a calibration log
today; in front of a pilot user it is a clinical-safety event. Therefore:

- The **threshold/target sign-off** belongs with the **F3/F4 clinical approver**, not a code
  reviewer — the right approver must be in the loop **from the start of scoping**, not shown
  the number after the fact.
- The crisis-article false-surface floor (**0**) is non-negotiable and is the clinical
  reviewer's to ratify.
- Engineering owns: the harness, the recall/latency measurement, the implementation.
- Clinical owns: the recall floor, the abstain target, the crisis floor — the conformance bar.

## 7. What this unblocks / relates to

- Closes out the abstain-threshold question ("superseded, not tuned").
- Independent of, but compounded by, corpus/short-query gaps (e.g. cbt-001 short-query miss;
  the AR pair was added separately).
- Pre-prod step before broad pilot exposure of the Ask/info-request path.
