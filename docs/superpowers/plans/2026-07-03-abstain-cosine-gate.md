# Abstain-Floor Cosine Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the structurally-ineffective RRF abstain floor with a cosine-similarity relevance gate, so the knowledge layer abstains on off-domain queries instead of surfacing weak passages as answers.

**Architecture:** Surface pgvector's already-computed cosine distance from the hybrid SQL (bounded column add, RRF fusion untouched); abstain when the best cosine similarity across the returned evidence pack is below `COSINE_ABSTAIN_THRESHOLD` (cosine = authoritative; RRF stays for ranking, retained as a corrected secondary guard). Record the deciding similarity in the audit trace. Threshold is env-configurable and calibrated empirically from 28 positives + 12 negatives.

**Tech Stack:** Python 3, asyncpg + pgvector, BGE-M3 embeddings, pytest/pytest-asyncio, Supabase PostgREST (session_audit), Railway.

## Global Constraints

- **Base branch: `master`** (has PR#84's `_search`/template/`query_raw`/`query_searched`/migration 005). NOT `feat/crisis-tiering`.
- Cosine is the **authoritative** abstain signal; RRF floor is a **retained, corrected secondary guard** — do NOT delete `KNOWLEDGE_ABSTAIN_THRESHOLD`, fix its comment.
- Gate on **best cosine across the returned evidence pack**: `top_similarity = max(1 - vec_distance)` over returned rows with non-NULL vec_distance; `0.0` if none.
- **Abstain = empty evidence pack**: `abstain=True` ⇒ `passages=[]` (node) and `passages: []` (tool JSON). Never "passages with an advisory flag."
- Committed `COSINE_ABSTAIN_THRESHOLD` default = **`0.0` (fail-open)** — merging is inert; the calibrated value is set at deploy via `SAGE_COSINE_ABSTAIN_THRESHOLD`. `=0.0` is the designated zero-latency rollback.
- pgvector `<=>` is cosine **distance** (0=identical); similarity = `1 - distance`. Vector CTE `LIMIT $3 = top_k*4 = 20` (deeper than top-5, so NULL vec_distance = not-near — verified).
- Migration `007` (fixed-column `session_audit`) applies BEFORE the code deploy (same rule as 005).
- Interim fix only; proper fix = reranker (#45) + calibration at the corpus >100 gate.
- Spec: `docs/superpowers/specs/2026-07-03-abstain-cosine-gate-design.md`. Commit per task; TDD.

---

## File Structure

- `src/sage_poc/config.py` — add `COSINE_ABSTAIN_THRESHOLD`; correct `KNOWLEDGE_ABSTAIN_THRESHOLD` comment.
- `src/sage_poc/knowledge/models.py` — `KnowledgeResult.top_similarity`.
- `src/sage_poc/knowledge/postgres_repository.py` — `_HYBRID_SQL` (+vec_distance), `_search` cosine gate + empty-pack abstain + `top_similarity`.
- `src/sage_poc/nodes/knowledge_retrieve.py`, `nodes/tools/knowledge_lookup.py`, `nodes/freeflow_respond.py` — propagate `top_similarity`.
- `src/sage_poc/state.py`, `src/sage_poc/audit.py`, `src/sage_poc/nodes/output_gate.py` — audit field.
- `migrations/007_add_knowledge_top_similarity_to_session_audit.sql` — new.
- `tests/test_knowledge_repository.py`, `tests/test_knowledge_retrieve_node.py`, `tests/test_knowledge_lookup.py`, `tests/test_knowledge_audit_trace.py` — behavior.
- `tests/fixtures/knowledge_probe/ar_recall_probe.jsonl` — +12 negatives.
- `scripts/negatives_smoke.py` — commit; `scripts/knowledge_ar_recall_probe.py` — per-bucket cosine capture.

---

### Task 1: config threshold + corrected comment + result field

**Files:**
- Modify: `src/sage_poc/config.py` (lines 27-31)
- Modify: `src/sage_poc/knowledge/models.py` (KnowledgeResult, lines 20-25)
- Test: `tests/test_knowledge_repository.py`

**Interfaces:**
- Produces: `config.COSINE_ABSTAIN_THRESHOLD: float` (env `SAGE_COSINE_ABSTAIN_THRESHOLD`, default `0.0`); `KnowledgeResult.top_similarity: float | None` (default `None`).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_knowledge_repository.py`:

```python
def test_cosine_threshold_config_defaults_fail_open():
    import importlib, sage_poc.config as cfg
    importlib.reload(cfg)
    assert cfg.COSINE_ABSTAIN_THRESHOLD == 0.0  # fail-open until deploy sets the env var

def test_knowledge_result_has_top_similarity():
    from sage_poc.knowledge.models import KnowledgeResult
    r = KnowledgeResult(passages=[], abstain=True, top_similarity=0.12)
    assert r.top_similarity == 0.12
    assert KnowledgeResult().top_similarity is None
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest tests/test_knowledge_repository.py -k "cosine_threshold_config or top_similarity" -v`
Expected: FAIL — `COSINE_ABSTAIN_THRESHOLD` and `top_similarity` don't exist.

- [ ] **Step 3: Implement**

In `src/sage_poc/config.py`, replace the knowledge-threshold block (lines 27-31):

```python
# Knowledge abstain gates. RRF is pure RANK fusion: its minimum meaningful score is
# 1/(k+1) = 1/61 = 0.0164 (k=60), and the whole top-5 single-list range (1/61..1/65 =
# 0.0164..0.0154) sits ABOVE 0.015, so KNOWLEDGE_ABSTAIN_THRESHOLD at 0.015 can NEVER
# abstain (verified 2026-07-03: 0/12 off-domain queries abstained). It is retained as a
# SECONDARY per-passage guard only; the AUTHORITATIVE abstain decision is the cosine gate
# below. Proper fix = reranker (#45) + calibration at the corpus >100 gate.
KNOWLEDGE_ABSTAIN_THRESHOLD = float(os.getenv("SAGE_KNOWLEDGE_ABSTAIN_THRESHOLD", "0.015"))

# Authoritative abstain gate: cosine SIMILARITY (1 - pgvector distance) of the best passage
# in the returned evidence pack. Abstain when best similarity < threshold. Default 0.0 is
# FAIL-OPEN (never abstains = pre-fix behaviour); deploy sets SAGE_COSINE_ABSTAIN_THRESHOLD
# to the calibrated value (spec 2026-07-03 Appendix A). Set to 0.0 to roll back instantly.
COSINE_ABSTAIN_THRESHOLD = float(os.getenv("SAGE_COSINE_ABSTAIN_THRESHOLD", "0.0"))
```

In `src/sage_poc/knowledge/models.py`, update `KnowledgeResult`:

```python
@dataclass
class KnowledgeResult:
    passages: list[KnowledgePassage] = field(default_factory=list)
    abstain: bool = False
    query_raw: str = ""
    query_searched: str = ""
    top_similarity: float | None = None  # best cosine sim in the returned pack; drives abstain
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_knowledge_repository.py -k "cosine_threshold_config or top_similarity" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/config.py src/sage_poc/knowledge/models.py tests/test_knowledge_repository.py
git commit -m "feat(knowledge): cosine abstain threshold config (fail-open default) + result.top_similarity; correct RRF-floor comment"
```

---

### Task 2: surface cosine in SQL + cosine gate in _search

**Files:**
- Modify: `src/sage_poc/knowledge/postgres_repository.py` (`_HYBRID_SQL`, `_search`)
- Test: `tests/test_knowledge_repository.py`

**Interfaces:**
- Consumes: `config.COSINE_ABSTAIN_THRESHOLD`, `KnowledgeResult.top_similarity` (Task 1).
- Produces: `_search` returns `KnowledgeResult` with `top_similarity` set and `abstain` decided by the cosine gate; empty `passages` on abstain.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_knowledge_repository.py`:

```python
def _mk_pool(rows):
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=rows)
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock(return_value=None)))
    return mock_pool

@pytest.mark.asyncio
async def test_search_abstains_when_top_cosine_below_threshold(monkeypatch):
    """Off-domain: best cosine similarity low -> abstain with EMPTY pack."""
    import sage_poc.knowledge.postgres_repository as pr
    monkeypatch.setattr(pr, "COSINE_ABSTAIN_THRESHOLD", 0.30)
    rows = [  # vec_distance 0.85 -> sim 0.15 < 0.30
        {"article_id": "x", "chunk_text": "t", "citation_metadata": {}, "rrf_score": 0.0164, "vec_distance": 0.85},
    ]
    with patch.object(pr, "_get_embedding", return_value=[0.1] * 1024):
        r = await pr.PostgresKnowledgeRepository(_mk_pool(rows))._search("recipe for cake", language="en")
    assert r.abstain is True
    assert r.passages == []            # empty pack, no L4 injection
    assert round(r.top_similarity, 2) == 0.15

@pytest.mark.asyncio
async def test_search_retrieves_when_top_cosine_above_threshold(monkeypatch):
    import sage_poc.knowledge.postgres_repository as pr
    monkeypatch.setattr(pr, "COSINE_ABSTAIN_THRESHOLD", 0.30)
    rows = [  # vec_distance 0.20 -> sim 0.80 >= 0.30
        {"article_id": "cbt-001-en", "chunk_text": "CBT...", "citation_metadata": {"citation": "Beck"}, "rrf_score": 0.03, "vec_distance": 0.20},
    ]
    with patch.object(pr, "_get_embedding", return_value=[0.1] * 1024):
        r = await pr.PostgresKnowledgeRepository(_mk_pool(rows))._search("what is CBT", language="en")
    assert r.abstain is False
    assert len(r.passages) == 1 and r.passages[0].source_id == "cbt-001-en"
    assert round(r.top_similarity, 2) == 0.80

@pytest.mark.asyncio
async def test_search_fail_open_when_threshold_zero(monkeypatch):
    """Threshold 0.0 (committed default / rollback) skips the gate even for NEGATIVE
    similarity (distance > 1.0). Guarantees merging Tasks 1-4 is inert in prod."""
    import sage_poc.knowledge.postgres_repository as pr
    monkeypatch.setattr(pr, "COSINE_ABSTAIN_THRESHOLD", 0.0)
    rows = [  # vec_distance 1.3 -> sim -0.30 (negative); rrf 0.0164 > 0.015 secondary guard
        {"article_id": "x", "chunk_text": "t", "citation_metadata": {}, "rrf_score": 0.0164, "vec_distance": 1.3},
    ]
    with patch.object(pr, "_get_embedding", return_value=[0.1] * 1024):
        r = await pr.PostgresKnowledgeRepository(_mk_pool(rows))._search("q", language="en")
    assert r.abstain is False          # fail-open: cosine gate skipped
    assert len(r.passages) == 1        # retrieved via retained RRF secondary guard

@pytest.mark.asyncio
async def test_search_null_vec_distance_counts_as_not_similar(monkeypatch):
    """FTS-only rows (NULL vec_distance) don't create similarity -> abstain."""
    import sage_poc.knowledge.postgres_repository as pr
    monkeypatch.setattr(pr, "COSINE_ABSTAIN_THRESHOLD", 0.30)
    rows = [{"article_id": "x", "chunk_text": "t", "citation_metadata": {}, "rrf_score": 0.0164, "vec_distance": None}]
    with patch.object(pr, "_get_embedding", return_value=[0.1] * 1024):
        r = await pr.PostgresKnowledgeRepository(_mk_pool(rows))._search("q", language="en")
    assert r.abstain is True and r.passages == [] and r.top_similarity == 0.0
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest tests/test_knowledge_repository.py -k "top_cosine or null_vec_distance" -v`
Expected: FAIL — `vec_distance` not in rows / cosine gate not implemented.

- [ ] **Step 3: Add vec_distance to the SQL**

In `src/sage_poc/knowledge/postgres_repository.py`, edit `_HYBRID_SQL`. In `vector_ranked` SELECT add the distance column:

```sql
    SELECT
        id, article_id, chunk_text, citation_metadata,
        (chunk_embedding <=> $1::vector) AS vec_distance,
        ROW_NUMBER() OVER (ORDER BY chunk_embedding <=> $1::vector) AS vec_rank
```

In `combined` SELECT add (text-only rows have no vector match → NULL):

```sql
        v.vec_distance AS vec_distance,
```

In the final SELECT add `vec_distance`:

```sql
SELECT article_id, chunk_text, citation_metadata, rrf_score, vec_distance
FROM combined
ORDER BY rrf_score DESC
LIMIT $6
```

- [ ] **Step 4: Implement the cosine gate in `_search`**

Replace the block from `if not rows:` through the final `return` in `_search`:

```python
        if not rows:
            return KnowledgeResult(passages=[], abstain=True, top_similarity=0.0)

        # Authoritative abstain gate: best cosine SIMILARITY across the returned pack.
        # pgvector <=> is distance; similarity = 1 - distance. FTS-only rows (NULL
        # vec_distance) are outside the top-20 nearest, so they don't count as similar.
        sims = [1.0 - float(r["vec_distance"]) for r in rows if r["vec_distance"] is not None]
        top_similarity = max(sims) if sims else 0.0
        # Cosine gate is authoritative WHEN ENABLED. threshold <= 0.0 is FAIL-OPEN
        # (committed default + rollback): skip the gate entirely, so negative similarities
        # (distance > 1.0 -> sim < 0) never trigger abstain and merging stays inert /
        # =0.0 restores pre-fix behaviour EXACTLY.
        if COSINE_ABSTAIN_THRESHOLD > 0.0 and top_similarity < COSINE_ABSTAIN_THRESHOLD:
            return KnowledgeResult(passages=[], abstain=True, top_similarity=top_similarity)

        passages = []
        for row in rows:
            if not _passes_abstain(row["rrf_score"]):  # retained secondary RRF guard
                continue
            raw_meta = row["citation_metadata"] or {}
            meta = json.loads(raw_meta) if isinstance(raw_meta, str) else raw_meta
            passages.append(KnowledgePassage(
                text=row["chunk_text"],
                source_id=row["article_id"],
                citation=meta.get("citation", row["article_id"]),
                relevance_score=round(float(row["rrf_score"]), 4),
            ))
        # POC substitute for Azure AI Search + BGE-reranker (corpus >100 gate). See #45.
        return KnowledgeResult(passages=passages, abstain=len(passages) == 0, top_similarity=top_similarity)
```

Add the import at the top of the file (line 4 area):

```python
from sage_poc.config import KNOWLEDGE_ABSTAIN_THRESHOLD, COSINE_ABSTAIN_THRESHOLD
```

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest tests/test_knowledge_repository.py -v`
Expected: PASS (new cosine tests + existing repository tests; existing tests mock rows WITHOUT `vec_distance` — see note).

> If any pre-existing repository test builds `fake_row` without `vec_distance` and now hits a KeyError, add `"vec_distance": 0.1` (a high-similarity value) to that row so it still retrieves. Update only those fixtures; do not change assertions.

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/knowledge/postgres_repository.py tests/test_knowledge_repository.py
git commit -m "feat(knowledge): cosine relevance gate for abstain (empty pack); surface vec_distance from hybrid SQL"
```

---

### Task 3: propagate top_similarity into state + audit trail + migration 007

**Files:**
- Modify: `src/sage_poc/nodes/knowledge_retrieve.py`, `src/sage_poc/nodes/tools/knowledge_lookup.py`, `src/sage_poc/nodes/freeflow_respond.py`
- Modify: `src/sage_poc/state.py`, `src/sage_poc/audit.py` (`_build_session_audit_row`), `src/sage_poc/nodes/output_gate.py`
- Create: `migrations/007_add_knowledge_top_similarity_to_session_audit.sql`
- Test: `tests/test_knowledge_retrieve_node.py`, `tests/test_knowledge_lookup.py`, `tests/test_knowledge_audit_trace.py`

**Interfaces:**
- Consumes: `KnowledgeResult.top_similarity` (Task 2).
- Produces: state key `knowledge_top_similarity`; tool JSON `top_similarity`; audit-record key `knowledge_top_similarity`.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_knowledge_retrieve_node.py`:

```python
@pytest.mark.asyncio
async def test_node_emits_top_similarity_to_state():
    from sage_poc.knowledge.models import KnowledgeResult
    from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository
    from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node
    async def fake_search(self, query, language="en", top_k=5):
        return KnowledgeResult(passages=[], abstain=True, top_similarity=0.11)
    with patch.object(PostgresKnowledgeRepository, "_search", fake_search):
        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
            r = await knowledge_retrieve_node(_kr_state(detected_language="en"))
    assert r["knowledge_top_similarity"] == 0.11
```

Add to `tests/test_knowledge_audit_trace.py`:

```python
def test_audit_record_includes_top_similarity():
    from sage_poc.audit import _build_session_audit_row
    rec = _build_session_audit_row({"knowledge_source": "node_6", "knowledge_top_similarity": 0.11})
    assert rec["knowledge_top_similarity"] == 0.11
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest tests/test_knowledge_retrieve_node.py::test_node_emits_top_similarity_to_state tests/test_knowledge_audit_trace.py::test_audit_record_includes_top_similarity -v`
Expected: FAIL — key absent.

- [ ] **Step 3: Node path** — in `knowledge_retrieve.py` return dict, add:

```python
        "knowledge_top_similarity": result.top_similarity,
```

- [ ] **Step 4: Tool path** — in `knowledge_lookup.py` success-return JSON add `"top_similarity": result.top_similarity,`. In `freeflow_respond.py` `_knowledge_lookup_trace`, add to the returned dict:

```python
                "knowledge_top_similarity": data.get("top_similarity"),
```

- [ ] **Step 5: State + audit** — in `state.py` `SageState` add `knowledge_top_similarity: float | None`. In `audit.py` `_build_session_audit_row` (after the knowledge_query_searched line) add:

```python
        "knowledge_top_similarity": state.get("knowledge_top_similarity"),
```

In `output_gate.py` knowledge audit log dict (after knowledge_query_searched) add:

```python
            "knowledge_top_similarity": state.get("knowledge_top_similarity"),
```

- [ ] **Step 6: Migration 007**

Create `migrations/007_add_knowledge_top_similarity_to_session_audit.sql`:

```sql
-- Add knowledge_top_similarity to session_audit: the best cosine similarity in the
-- returned evidence pack, which drives the abstain decision. Recording it lets future
-- (corpus >100 gate) calibration read production score distributions for free.
-- Existing rows get NULL. Fixed-column table (Supabase PostgREST) — apply before deploy.
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS knowledge_top_similarity double precision;
```

- [ ] **Step 7: Run to verify pass**

Run: `uv run pytest tests/test_knowledge_retrieve_node.py tests/test_knowledge_lookup.py tests/test_knowledge_audit_trace.py -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/sage_poc/nodes/knowledge_retrieve.py src/sage_poc/nodes/tools/knowledge_lookup.py src/sage_poc/nodes/freeflow_respond.py src/sage_poc/state.py src/sage_poc/audit.py src/sage_poc/nodes/output_gate.py migrations/007_add_knowledge_top_similarity_to_session_audit.sql tests/test_knowledge_retrieve_node.py tests/test_knowledge_lookup.py tests/test_knowledge_audit_trace.py
git commit -m "feat(knowledge): record abstain-deciding cosine similarity into audit trail (migration 007)"
```

---

### Task 4: calibration assets — negatives fixture, smoke test, per-bucket capture

**Files:**
- Modify: `tests/fixtures/knowledge_probe/ar_recall_probe.jsonl` (+12 negatives)
- Create: `scripts/negatives_smoke.py`
- Modify: `scripts/knowledge_ar_recall_probe.py` (per-bucket cosine capture)
- Test: `tests/test_knowledge_probe_harness.py`

**Interfaces:**
- Produces: `scripts/knowledge_ar_recall_probe.py::cosine_distributions(rows, search_fn) -> dict` (per-bucket min/median/max similarity).

- [ ] **Step 1: Fold 12 negatives into the fixture**

Append to `tests/fixtures/knowledge_probe/ar_recall_probe.jsonl` (one per line; 6 EN + 6 AR, clearly off-domain):

```jsonl
{"query": "how do I file my income taxes this year?", "gold_article_ids": [], "relevance_judgment": "none", "dialect_tag": "en", "variance_type": "negative"}
{"query": "what is the capital of Australia?", "gold_article_ids": [], "relevance_judgment": "none", "dialect_tag": "en", "variance_type": "negative"}
{"query": "how do I fix a flat car tire?", "gold_article_ids": [], "relevance_judgment": "none", "dialect_tag": "en", "variance_type": "negative"}
{"query": "what is the best recipe for chocolate cake?", "gold_article_ids": [], "relevance_judgment": "none", "dialect_tag": "en", "variance_type": "negative"}
{"query": "how does photosynthesis work in plants?", "gold_article_ids": [], "relevance_judgment": "none", "dialect_tag": "en", "variance_type": "negative"}
{"query": "how do I reset my wifi router password?", "gold_article_ids": [], "relevance_judgment": "none", "dialect_tag": "en", "variance_type": "negative"}
{"query": "كيف أطبخ الأرز بالبخار؟", "gold_article_ids": [], "relevance_judgment": "none", "dialect_tag": "ar", "variance_type": "negative"}
{"query": "ما هي عاصمة اليابان؟", "gold_article_ids": [], "relevance_judgment": "none", "dialect_tag": "ar", "variance_type": "negative"}
{"query": "كيف أصلح إطار السيارة المثقوب؟", "gold_article_ids": [], "relevance_judgment": "none", "dialect_tag": "ar", "variance_type": "negative"}
{"query": "ما هو سعر صرف الدولار اليوم؟", "gold_article_ids": [], "relevance_judgment": "none", "dialect_tag": "ar", "variance_type": "negative"}
{"query": "كيف أحجز تذكرة طيران؟", "gold_article_ids": [], "relevance_judgment": "none", "dialect_tag": "ar", "variance_type": "negative"}
{"query": "ما هي أفضل وصفة للكيك؟", "gold_article_ids": [], "relevance_judgment": "none", "dialect_tag": "ar", "variance_type": "negative"}
```

Update `tests/fixtures/knowledge_probe/README.md`: add `variance_type: negative` (off-domain, no relevant answer; `relevance_judgment: "none"`; first-class TD5 negatives, partially unblocks Item #2's negatives condition).

- [ ] **Step 2: Commit the durable smoke test**

Create `scripts/negatives_smoke.py`:

```python
"""Negatives smoke test of the live abstain gate. Off-domain queries with no relevant
corpus answer -> correct behaviour is abstain=True. Runs read-only against the DB in
DATABASE_URL. Valid at current corpus scale only (see RESULTS caveat)."""
import os, asyncio, asyncpg
from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository

NEG = [
    ("en", "how do I file my income taxes this year?"), ("en", "what is the capital of Australia?"),
    ("en", "how do I fix a flat car tire?"), ("en", "what is the best recipe for chocolate cake?"),
    ("en", "how does photosynthesis work in plants?"), ("en", "how do I reset my wifi router password?"),
    ("ar", "كيف أطبخ الأرز بالبخار؟"), ("ar", "ما هي عاصمة اليابان؟"),
    ("ar", "كيف أصلح إطار السيارة المثقوب؟"), ("ar", "ما هو سعر صرف الدولار اليوم؟"),
    ("ar", "كيف أحجز تذكرة طيران؟"), ("ar", "ما هي أفضل وصفة للكيك؟"),
]

async def main():
    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=4)
    repo = PostgresKnowledgeRepository(pool)
    ab = 0
    for lang, q in NEG:
        r = await repo.retrieve(q, language=lang, top_k=5)
        ab += r.abstain
        print(f"[{lang}] {'ABSTAIN' if r.abstain else 'LEAK'} sim={r.top_similarity} | {q}")
    print(f"\n{ab}/{len(NEG)} abstained")
    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Write failing test for per-bucket capture**

Add to `tests/test_knowledge_probe_harness.py`:

```python
@pytest.mark.asyncio
async def test_cosine_distributions_buckets_by_dialect_and_variance():
    from scripts.knowledge_ar_recall_probe import cosine_distributions
    rows = [
        {"query": "a", "dialect_tag": "msa", "variance_type": "baseline"},
        {"query": "b", "dialect_tag": "en", "variance_type": "negative"},
    ]
    async def search_fn(query, language):
        return 0.8 if query == "a" else 0.1  # returns top_similarity
    dist = await cosine_distributions(rows, search_fn)
    assert dist["msa/baseline"]["max"] == 0.8
    assert dist["en/negative"]["max"] == 0.1
```

- [ ] **Step 4: Run to verify fail**

Run: `uv run pytest tests/test_knowledge_probe_harness.py -k cosine_distributions -v`
Expected: FAIL — `cosine_distributions` undefined.

- [ ] **Step 5: Implement per-bucket capture**

Add to `scripts/knowledge_ar_recall_probe.py`:

```python
async def cosine_distributions(rows, search_fn) -> dict:
    """search_fn(query, language) -> top_similarity float. Buckets by dialect_tag/variance_type."""
    buckets: dict = {}
    for row in rows:
        lang = "ar" if row["dialect_tag"] in ("khaleeji", "msa") else "en"
        sim = await search_fn(row["query"], lang)
        buckets.setdefault(f'{row["dialect_tag"]}/{row["variance_type"]}', []).append(sim)
    out = {}
    for k, sims in buckets.items():
        s = sorted(sims)
        out[k] = {"n": len(s), "min": s[0], "median": s[len(s)//2], "max": s[-1]}
    return out
```

- [ ] **Step 6: Run to verify pass + commit**

Run: `uv run pytest tests/test_knowledge_probe_harness.py -q`
Expected: PASS.

```bash
git add tests/fixtures/knowledge_probe/ scripts/negatives_smoke.py scripts/knowledge_ar_recall_probe.py tests/test_knowledge_probe_harness.py
git commit -m "test(knowledge): TD5 negatives fixture + negatives_smoke + per-bucket cosine capture for calibration"
```

---

### Task 5: Calibration run (RUNBOOK — read-only prod, produces the threshold)

**Files:** Modify `docs/superpowers/specs/2026-07-03-abstain-cosine-gate-design.md` (fill Appendix A).

- [ ] **Step 1: Capture per-bucket cosine distributions against prod**

From a checkout of this branch: build the query set from the probe fixture (28 positives + 12 negatives), and for each run **`PostgresKnowledgeRepository(pool).retrieve(query, language, top_k=5)`** capturing `top_similarity`, then `cosine_distributions(rows, search_fn)` with `search_fn = lambda q, lang: repo.retrieve(q, lang, top_k=5).top_similarity`. Run read-only:
`railway run uv run python -m scripts.knowledge_ar_recall_probe` (extend `_main` to print `cosine_distributions`), or a one-off script.

> **CRITICAL — calibrate via `retrieve()`, NOT `_search()`.** `retrieve()` is the base-template path that applies PR#84 Arabic normalization before search; `_search()` receives the raw query. Calibrating on `_search()` would measure every khaleeji/orthographic positive on its UN-normalized query — systematically lower similarity than production sees — which under the §3.4 rule (threshold ≤ min positive similarity per bucket) would drag the chosen threshold below what the data supports, calibrated from a path that no longer exists in prod. `negatives_smoke.py` already uses `repo.retrieve()`; match it. Calibration measures the deployed path or it measures nothing.

- [ ] **Step 2: Apply the §3.4 decision rule and pick the threshold**

Positives inviolable: set `COSINE_ABSTAIN_THRESHOLD` ≤ the **minimum positive similarity in any dialect bucket** (zero false abstention per-bucket). Then it catches every negative below the weakest positive. Record min/median/max per bucket (msa/baseline, khaleeji/orthographic, khaleeji/lexical, negatives) and the chosen value + margin in **Appendix A**. Record the **residual** (negatives still clearing the threshold) as the measured gap the reranker closes.

> Comparison direction (state in Appendix A): the gate is `abstain iff top_similarity < COSINE_ABSTAIN_THRESHOLD` (strict `<`). So a threshold set exactly equal to the weakest positive similarity STILL retrieves that positive (it is not `<`). Pick the threshold accordingly when targeting zero positive false-abstention.

- [ ] **Step 3: Commit the filled Appendix A**

```bash
git add docs/superpowers/specs/2026-07-03-abstain-cosine-gate-design.md
git commit -m "docs(spec): abstain-gate calibration distributions + chosen threshold (Appendix A)"
```

---

### Task 6: Deploy + prod verification (RUNBOOK — prod mutation, gated on review)

- [ ] **Step 1: Apply migration 007 to prod session_audit, verify column present**

`railway run` an idempotent `ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS knowledge_top_similarity double precision`, then re-query `information_schema.columns` to confirm. BEFORE code deploy.

- [ ] **Step 2: Deploy with the calibrated threshold**

Set `SAGE_COSINE_ABSTAIN_THRESHOLD=0.42` (Appendix A) in the Railway prod service, then `railway up` master from a clean worktree.

- [ ] **Step 3: Prod verification — calibration must TRANSFER (acceptance criteria 1-3)**

Run `railway run uv run python -m scripts.negatives_smoke` → **expect 10/12 abstaining**, with the two named residuals leaking ("how does photosynthesis work" 0.4395, "book a flight ticket" 0.4322). **12/12 is a discrepancy to investigate, not a bonus.** Run the positives probe → confirm **0/28 false abstention per dialect bucket**. Playwright on chat.biosight.ai: one off-domain turn in **EN** ("how do I file my income taxes") and one in **AR** ("ما هو سعر صرف الدولار اليوم؟") — both *abstaining* negatives, not the residual-leak strings — confirm the abstain response renders (empty pack → "I don't have specific info… want me to find out?") and `session_audit` shows `knowledge_abstain=true` + a low `knowledge_top_similarity`.

- [ ] **Step 4: Record rollback lever + monitoring obligation (§3.7, §3.8)**

Document in the deploy note: `SAGE_COSINE_ABSTAIN_THRESHOLD=0.0` restores pre-fix behaviour instantly (no code deploy). **Standing check (first week, daily):** query `session_audit` for abstained turns with `knowledge_top_similarity` in ~0.40–0.44 — any abstained legitimate query there is the thin-margin early-warning; lever = nudge the env var down or fail-open. Update memory: interim gate DEPLOYED + 0.42 + 10/12 + residual + the >100-gate reranker convergence.

---

## Full regression

- [ ] **Final:** `uv run pytest tests/test_knowledge_repository.py tests/test_knowledge_retrieve_node.py tests/test_knowledge_lookup.py tests/test_knowledge_audit_trace.py tests/test_knowledge_probe_harness.py tests/test_routing.py tests/test_freeflow_respond.py -q` → all pass. Then `uv run pytest -q` (knowledge-relevant subset) before PR.
