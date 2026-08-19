# Ticket (SAFETY-ADJACENT): prod ivfflat index (lists=50, probes=1) has measured recall holes — crisis-on-topic KB queries mis-route or abstain

**Filed:** 2026-08-19 · **Source:** KB corpus refresh deploy verification (PR #457), pre/post-deploy
retrieval probes against prod (tcekehffneiqcdyhzobi) vs exact-scan A/B on identical content
**Status:** open — routed for review; tagged SAFETY-ADJACENT (owner directive 2026-08-19: must not
queue behind cosmetic items)
**Type:** serving-layer retrieval debt, not a content defect (measured on BOTH old and new corpus)

## Measured evidence (2026-08-19)

Pre-deploy baseline (old corpus, 222 chunks) and post-deploy run (new corpus, 262 chunks), both
through the real `PostgresKnowledgeRepository` against prod, threshold 0.42 by mechanical readback
(`Sage_KB_Retrieval_Baseline_PreRefresh_2026-08-19.json`; PR #457 comments carry both tables):

- "where can I get urgent mental health help in the UAE" → **ABSTAINS in prod** (both corpora).
  Exact-scan on identical content finds crisis articles at 0.72–0.78.
- "what should I do in a mental health crisis" → prod top-1 grounding-001 (old) /
  self-compassion-001 (new) at ~0.48. Exact-scan: crisis-001 at 0.73–0.77.
- Non-crisis example of the same hole: "I have been feeling really stressed lately, how do I cope"
  → prod finds 0.631 (mindfulness chunk) where exact scan finds the stress chunk at 0.668.

Mechanism: `ivfflat (lists=50)` with default `probes=1` on a ~260-row table — the planner probes
1/50 lists, so true nearest neighbours are frequently not in the probed list. Cosine values are
consistent with local embeddings (parity verified to 3 decimals on hits), so this is index recall,
not embedding drift.

## Why safety-adjacent

A user *asking about crisis support* (info_request path, not the crisis-detection path — S1/S3 and
the crisis card are unaffected and verified separately) may get an unrelated passage or an abstain
instead of the crisis-resources KB content. The KB is a secondary crisis surface, but it is a
crisis surface.

## Fix candidates (assess together — same ranking layer as PR #45)

1. `SET ivfflat.probes` (session or GUC) — cheap, immediate recall improvement; needs a latency check.
2. Drop ivfflat entirely at this corpus size (~260 rows) — exact scan is microseconds here and is
   what every offline measurement already models.
3. Fold into PR #45's BGE-reranker scope (cross-encoder pass) — the reranker cannot rescue a
   candidate the index never returned, so 1 or 2 is needed regardless.

Decision belongs with the retrieval-core re-arch owner; clinical sign-off required only if the
chosen fix changes what surfaces on crisis-adjacent queries (measure before/after with the PR #457
probe set).

## Related

- PR #457 (corpus refresh; probe tables in comments)
- PR #45 (reranker scoping, deliberately open)
- `docs/superpowers/audits/2026-06-23-knowledge-abstain-threshold-calibration.md` (RRF structural
  weakness — a sibling defect in the same layer, distinct mechanism)
- Exp 4.5 fixture debt: `tests/experiment_4_5/query_corpus.py` expects retired article-ID prefixes
  (`anx-`, `mbct-`, `dbt-`) — refresh alongside whichever fix lands so the eval can gate it.
