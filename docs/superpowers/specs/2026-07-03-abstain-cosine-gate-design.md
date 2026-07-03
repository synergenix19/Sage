# Interim Abstain-Floor Fix — Cosine Relevance Gate — Design Spec

- **Date:** 2026-07-03
- **Status:** Approved (approach), pending spec review → implementation plan
- **Scope:** INTERIM fix for a live, safety-relevant defect. Proper fix remains reranker (#45) + full calibration at the corpus >100 gate — see the gate bundle in [[project_ar_recall_probe_2026_07_03]].
- **Proportionality:** hallucination-grounding defect (KPI-level, <5% target), NOT crisis-safety. Layer 1 (crisis detection) is upstream, deterministic, and unaffected. Fast-follow, not an incident.

## 1. Problem

The live knowledge abstain floor `KNOWLEDGE_ABSTAIN_THRESHOLD = 0.015` is **structurally incapable of abstaining**. RRF's minimum meaningful score is `1/(k+1) = 1/61 = 0.0164` (k=60); the entire top-5 single-list RRF range (`1/61..1/65 = 0.0164..0.0154`) sits **above** 0.015. pgvector always returns nearest neighbours, so the top passage always clears the floor. Verified 2026-07-03: **0/12 out-of-domain queries abstained** (taxes, capital of Australia, cake recipe, wifi, EN+AR), every one returning 5 passages with identical `top rrf = 0.0164`. The `config.py` comment ("just above single-list rank-2+ noise") had the math wrong — that error is how this shipped.

Consequence: ask Sage an off-domain question and the knowledge layer surfaces mental-health passages the LLM may present as an answer — the "Google is better" hallucination-grounding mode the floor exists to prevent. The interim mitigation currently gives **false assurance**.

**Root cause of the root cause:** RRF is pure *rank* fusion. The pipeline computes the only relevance-bearing signal it has (pgvector cosine distance, in the `<=>` ORDER BY) and then **discards it**, keeping only rank. No rank-based threshold can measure relevance.

## 2. Approach — gate abstention on cosine similarity

Abstain on **raw cosine similarity** (relevance-bearing); keep RRF for **ranking**. Two questions, two signals:
- "Should we abstain?" → *was anything in the corpus actually similar to this query?* → **cosine** (authoritative).
- "In what order do we show what we keep?" → **RRF** (unchanged).

Cosine is the correct signal AND dialect-friendly: a Khaleeji query semantically near a passage scores high cosine even when FTS misses the dialect wording — the exact case an RRF-gap value (~0.020) would push toward false abstention in our primary population. That failure mode is why the config-only RRF-gap alternative was rejected.

## 3. Design

### 3.1 SQL — surface the already-computed distance (bounded, no fusion restructure)
In `_HYBRID_SQL` (`knowledge/postgres_repository.py`):
- `vector_ranked`: add `chunk_embedding <=> $1::vector AS vec_distance` to the SELECT (the value is already computed for the ORDER BY / ROW_NUMBER).
- `combined`: carry `v.vec_distance` through (FTS-only rows — no vector match — get NULL, which correctly means "not among the semantically nearest").
- Final SELECT: add `vec_distance`.
- RRF fusion arithmetic is **unchanged**. `<=>` is cosine **distance** (0 = identical, 2 = opposite); similarity = `1 − distance`.

### 3.2 Abstain logic — best similarity across the returned evidence pack (Constraint 1)
Gate on the best cosine across the **returned top-5 evidence pack**, not the vector CTE's rank-1 (which would conflate vector-list order with corpus relevance, and could miss a highly-similar passage that entered the pack via FTS):
```
sims = [1 - row.vec_distance for row in rows if row.vec_distance is not None]
top_similarity = max(sims) if sims else 0.0
abstain = top_similarity < COSINE_ABSTAIN_THRESHOLD
```
- If **no** returned passage has a vec_distance (pure FTS pack, nothing semantically near) → `top_similarity = 0.0` → abstain. Correct: nothing was similar.
- Passages that pass the gate are still ordered by RRF for presentation.

**Abstain semantics — empty evidence pack, no L4 injection.** `abstain=True` MUST produce an **empty** pack: `KnowledgeResult.passages = []` on the node path (so the L4 knowledge block injects nothing into the prompt) and `passages: []` in the tool JSON. Abstention must NOT mean "passages included with an advisory flag the LLM may ignore" — that reintroduces the exact defect (weak passages presented as answers). Enforced by a test asserting an abstain result carries empty passages through to the prompt composer (no L4 knowledge block rendered).

**Candidate-depth assumption (verified):** the NULL-vec_distance-means-not-semantically-near claim holds only if the vector candidate list is materially deeper than the final top-5. It is: the vector CTE `LIMIT $3 = top_k*4 = 20` (`postgres_repository.py`, `$3` bind), so the 20 nearest by cosine all carry a `vec_distance`; a passage with NULL vec_distance is outside the top-20 nearest and is correctly treated as not-near. If `top_k*4` is ever reduced below a small multiple of `top_k`, revisit this.

### 3.3 Two gates with clear semantics (Constraint 2)
- **Cosine gate = authoritative abstain decision.** New config `COSINE_ABSTAIN_THRESHOLD` (env `SAGE_COSINE_ABSTAIN_THRESHOLD`).
- **RRF floor retained as a documented secondary guard**, NOT deleted. Fix its `config.py` comment (state the `1/(k+1)` math and that it cannot abstain alone). It remains a per-passage filter; the spec states cosine is authoritative and the RRF floor is a secondary, currently near-inert guard pending calibration. Keeping both with explicit semantics beats one silently-dead gate.

### 3.4 Threshold selection — empirical, from existing assets (Constraint 3)
Run the **28 positives + 12 negatives** through the modified SQL against the prod corpus (read-only) and capture cosine-similarity distributions **per bucket**: `msa/baseline`, `khaleeji/orthographic`, `khaleeji/lexical`, `negatives`. **Record the per-bucket distributions in this spec** (Appendix A) as the evidence for the chosen value.

**Decision rule for distribution overlap (do NOT assume clean separability).** Dense-embedding (BGE-M3) similarity distributions frequently do not separate cleanly — off-domain queries against a small mental-health corpus can score deceptively high cosine, and `khaleeji/lexical` positives can score low. If the distributions overlap, apply this rule (consistent with the margin principle):
1. **Positives are inviolable.** Set `COSINE_ABSTAIN_THRESHOLD` at or below the **minimum positive similarity observed in any dialect bucket**, so false abstention on positives is **zero, per-bucket**. Systematic false abstention on Khaleeji queries is a product failure in the primary population; a rare weak answer is recoverable.
2. **Maximize negative abstention subject to (1).** With positives protected, the threshold catches every negative that scores below the weakest positive.
3. **Report the residual.** Negatives that still clear the threshold (the overlap region) are recorded in Appendix A as the **measured protection gap the reranker (#45) closes at the >100 gate**. Partial protection, honestly documented, beats today's zero protection — but it must not be reported as full protection.

This converts a possible mid-implementation stall (two unsatisfiable criteria) into a pre-decided outcome and makes honest room for the plausible result that the interim gate catches most-but-not-all off-domain queries.

### 3.5 Audit trace — record the deciding similarity (Constraint 4)
Add the top similarity that drove the abstain decision to the audit trail, alongside `query_raw`/`query_searched`, so future (>100-gate) calibration reads real production score distributions for free:
- `KnowledgeResult` gains `top_similarity: float | None`.
- Node + tool propagate it; `SageState` gains `knowledge_top_similarity`.
- `audit._build_session_audit_row` + `output_gate` log dict include it.
- Migration `006_add_knowledge_top_similarity_to_session_audit.sql` (`ADD COLUMN IF NOT EXISTS knowledge_top_similarity double precision`) — fixed-column `session_audit`, so the column must exist before deploy (same ordering rule as migration 005).

### 3.6 Abstain-path end-to-end verification (Constraint 3/4)
The downstream ABSTAIN behaviour has **plausibly never fired in production** (the gate could not trigger). It must be verified, not assumed:
- Node path: `knowledge_abstain=True` → `freeflow_respond` renders the anti-hallucination / "I don't have specific info" response.
- Tool path: `abstain=true` JSON → the LLM says it doesn't have specific information and offers to find out.
- **Prod verification: one off-domain turn each in EN and AR**, showing the abstain response renders correctly end-to-end (Playwright on chat.biosight.ai, same discipline as the rewriter test).

### 3.7 Rollback lever — fail-open, zero-latency (deploy runbook)
Because the threshold is env-configurable, **`SAGE_COSINE_ABSTAIN_THRESHOLD=0.0` restores exactly today's behaviour instantly, without a code deploy** (similarity is always ≥ 0, so nothing ever abstains on the cosine gate). Migration 006 is additive and inert under it. This is the **designated rollback** in the deploy runbook: if the gate miscalibrates and suppresses legitimate clinical answers in production, flip the env var to `0.0` — a config change, not an incident. Set the initial deployed value to the calibrated threshold; keep the rollback documented alongside the deploy step.

## 4. Files touched
- `src/sage_poc/knowledge/postgres_repository.py` — `_HYBRID_SQL` (+vec_distance), `_search` abstain logic + `top_similarity`.
- `src/sage_poc/knowledge/models.py` — `KnowledgeResult.top_similarity`.
- `src/sage_poc/config.py` — add `COSINE_ABSTAIN_THRESHOLD`; **correct** the `KNOWLEDGE_ABSTAIN_THRESHOLD` comment.
- `src/sage_poc/nodes/knowledge_retrieve.py`, `nodes/tools/knowledge_lookup.py`, `nodes/freeflow_respond.py` — propagate `top_similarity` to state/JSON.
- `src/sage_poc/state.py`, `src/sage_poc/audit.py`, `src/sage_poc/nodes/output_gate.py` — audit field.
- `migrations/006_add_knowledge_top_similarity_to_session_audit.sql` — new.
- `tests/test_knowledge_repository.py` (+node/tool/audit tests) — abstain-on-low-cosine, retrieve-on-high-cosine, negatives abstain, positives retrieve, audit carries similarity.
- `tests/fixtures/knowledge_probe/ar_recall_probe.jsonl` — fold in 12 negatives (`relevance_judgment: "none"`, `gold_article_ids: []`, `variance_type: "negative"`).
- `scripts/negatives_smoke.py` — commit as durable safety-verification asset.
- `scripts/knowledge_ar_recall_probe.py` — extend to capture per-bucket cosine distributions for calibration.

## 5. Acceptance criteria (Constraint 4)
1. **Zero false abstention on the 28 positives, per dialect bucket** (msa / khaleeji-orthographic / khaleeji-lexical) — inviolable (§3.4 rule 1). This is the hard gate.
2. **Negative abstention maximized subject to (1)**, with the residual (negatives still clearing the threshold) recorded in Appendix A as the measured protection gap the reranker closes. Target is 12/12 abstaining; if distributions overlap, the honestly-reported residual is acceptable — partial protection documented, not reported as full.
3. **Prod-verified off-domain abstain turn in EN and AR** renders the abstain response end-to-end (empty pack → abstain message).
4. `negatives_smoke.py` committed; 12 negatives folded into the TD5-forward fixture (`relevance_judgment: "none"`).
5. `vec_distance`/`top_similarity` in the audit trace (migration 006 applied before deploy).
6. `config.py` comment corrected.
7. Chosen threshold justified by the recorded per-bucket distributions (§3.4 appendix).

## 6. Out of scope
Reranker (#45), full calibration at scale, Azure AI Search migration. This is interim; the proper fix and this fix converge at the corpus >100 gate bundle ([[project_ar_recall_probe_2026_07_03]]).

## Appendix A — calibration distributions (2026-07-03)

**Method:** 28 positives + 12 negatives from `tests/fixtures/knowledge_probe/ar_recall_probe.jsonl` run through `PostgresKnowledgeRepository.retrieve()` (the DEPLOYED normalization path, not `_search`) against the prod corpus, read-only; `top_similarity` captured per query.

**Per-bucket cosine similarity:**

| bucket | n | min | median | max |
|---|---|---|---|---|
| msa/baseline | 14 | 0.4339 | 0.6954 | 0.7823 |
| khaleeji/orthographic | 5 | 0.6018 | 0.7181 | 0.7459 |
| khaleeji/lexical | 9 | **0.4283** | 0.6172 | 0.7399 |
| en/negative | 6 | 0.3274 | 0.3911 | **0.4395** |
| ar/negative | 6 | 0.3062 | 0.3892 | 0.4322 |

**Overlap (as Amendment-1 anticipated — no clean separation):** the weakest positive (`0.4283`, khaleeji/lexical "شو هو التواصل الحازم؟") sits *below* the strongest negatives (`0.4395` en "photosynthesis", `0.4322` ar "book a flight ticket"). Dense-embedding tail overlap, not a bug.

**§3.4 decision rule applied:**
1. Positives inviolable → threshold ≤ min positive similarity across buckets = **0.4283**.
2. Maximize negative abstention subject to (1). The gap between the 3rd-strongest negative (0.4175) and the weakest positive (0.4283) contains no data, so any threshold in `(0.4175, 0.4283]` catches the same 10/12 negatives.

**Chosen threshold: `COSINE_ABSTAIN_THRESHOLD = 0.42`** (deploy env `SAGE_COSINE_ABSTAIN_THRESHOLD=0.42`; committed default stays `0.0`/fail-open). Placed at 0.42 (not 0.4283) for a ~0.008 positive-safety margin below the weakest observed positive, per the margin principle, at no cost to negative coverage.

**Verified at threshold 0.42:** false abstention on the 28 positives = **0/28** (per-bucket zero); negatives caught = **10/12 (83%)**.

**Residual (measured protection gap the reranker #45 closes at the >100 gate):** 2/12 negatives still clear 0.42 — "how does photosynthesis work" (0.4395) and "كيف أحجز تذكرة طيران؟ / book a flight ticket" (0.4322). Both are genuinely off-domain but BGE-M3 assigns them moderate similarity, above the weakest legitimate (short-form assertive-communication) positive. Interim gate = partial protection (0→83%), honestly documented; not full protection.

**Comparison direction:** gate is `abstain iff top_similarity < COSINE_ABSTAIN_THRESHOLD` (strict `<`). A positive exactly equal to the threshold is retrieved. 0.42 < all 28 positives, so all retrieve.
