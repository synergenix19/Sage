# Arabic Query Rewriter Wiring — Design Spec

- **Date:** 2026-07-03
- **Status:** Approved (design), pending spec review → implementation plan
- **Scope item:** Knowledge-retrieval Item #1 (Arabic rewriter wiring + test restoration + TD5-forward AR-recall probe)
- **Governance:** Restores v7 spec compliance; proceeds under standard review. No deviation approval required. One flagged, approved structural choice (see §2, Amendment 1).

## 1. Problem

`normalize_arabic_query` (`src/sage_poc/knowledge/rewriter.py`) exists but is **never called** anywhere in the codebase. Both knowledge-retrieval paths feed raw Arabic text to `PostgresKnowledgeRepository.retrieve()`:

- **Node path** — `nodes/knowledge_retrieve.py:39`: `query = raw_message (ar) | message_en (en)` → `repo.retrieve(query, language, top_k=5)`
- **Tool path** — `nodes/tools/knowledge_lookup.py:53`: `query = <LLM-supplied string>` → `repo.retrieve(query, language, top_k=5)`

This is out of spec on both paths:

- **Node:** graph-completion design (`Docs/superpowers/specs/2026-05-25-v7-graph-completion-design.md:146`) — *"Calls rewriter if `detected_language == 'ar'`"* — and the mandated test at line 300 (*"Node 6 — Arabic rewriter called | `test_nodes.py`"*), which **does not exist**.
- **Tool:** v7 master §6.5.2 — `knowledge_lookup` *"rewrites query (Khaleeji → MSA parallel), calls search, runs reranker."*

The gap sits precisely in the EN→Khaleeji retrieval cell, the documented highest open risk for the knowledge layer. The missing test is the reason the deviation went unnoticed and is treated as a first-class acceptance criterion here, not an afterthought.

**Non-goal / expectation-setting:** the v1 rewriter is *orthographic normalization only* (Alef variants أإآ→ا, Ta-marbuta ة→ه, tatweel strip). It is **not** lexical Khaleeji→MSA translation. The full CAMeL-Tools rewriter is a post-POC upgrade and out of scope. This spec deliberately instruments the probe (§5) so its results tell us whether that upgrade is warranted.

## 2. Design

### Placement — repository-agnostic base layer (Amendment 1)

Rewrite is applied in a **repository-agnostic** layer so **any** `retrieve()` implementation inherits it. Rationale: placing normalization inside the concrete `PostgresKnowledgeRepository` would recreate the exact regression pattern being fixed — when the v7-mandated migration to Azure AI Search ships a new repository class, the rewrite would be silently dropped again. The base owns it; concrete backends only implement search.

Refactor `KnowledgeRepository` (`knowledge/repository.py`) from a single abstract `retrieve()` into a **template method**:

```python
class KnowledgeRepository(ABC):
    async def retrieve(self, query, language="en", top_k=5) -> KnowledgeResult:
        query = self._preprocess_query(query)      # backend-agnostic, inherited by ALL impls
        return await self._search(query, language, top_k)

    @staticmethod
    def _preprocess_query(query: str) -> str:
        if _contains_arabic(query):                 # script-gated, not language-flag-gated (Amendment 2)
            return normalize_arabic_query(query)
        return query

    @abstractmethod
    async def _search(self, query, language, top_k) -> KnowledgeResult: ...
```

`PostgresKnowledgeRepository.retrieve()` is renamed to `_search()`; its body is otherwise unchanged (hybrid RRF, embedding, FTS). Because the normalized `query` now enters `_search`, it feeds **both** `_get_embedding(query)` and the FTS `$4` bind — the rewrite precedes both the dense and lexical sides, as required. Call sites (node + tool) are unchanged: the Azure migration is a true `_search`-only repository swap, no re-plumb.

**Spec-letter note (flagged + approved):** this differs from graph-completion design line 146's literal *"Node 6 calls rewriter."* The v7 master frames Node 6 as *"RAG: rewrite, search, rerank, evidence pack"* — rewrite as a **pipeline stage**, not a node responsibility — so base-layer placement is closer to the master spec than the line-146 literal. **Condition:** the graph-completion design doc is amended in the **same PR** so spec and code do not diverge again.

### Language guard (Amendment 2)

Normalization is gated on the **query string actually containing Arabic script** (`_contains_arabic`, Unicode Arabic block `؀-ۿ`), **not** on the passed `language` flag. The tool path's `query` is an LLM-supplied string while `language` comes from conversation-level detection; the two can mismatch (an English query formed inside an Arabic conversation, or vice versa). Script-gating is authoritative and makes the normalization intent directly testable. Running orthographic normalization on non-Arabic text would be a no-op regardless; the guard makes that explicit and prevents accidental application.

## 3. Test restoration (Amendment 2 + condition #2) — acceptance criteria

Because rewrite is repository-internal, the spec's "rewriter invoked" *intent* is asserted as **observable behavior at each boundary**, which is stronger than a mock-call assertion. **All of the following must exist and pass:**

1. **Interface-contract test** (base layer): a fake `KnowledgeRepository` subclass records the query its `_search` receives; assert an Arabic query is normalized **before any backend sees it**. This is the guarantee that survives the Azure swap.
2. **Repository behavior test:** an Arabic query containing an Alef/Ta-marbuta variant retrieves the same gold passage as its already-normalized form; differs demonstrably with normalization bypassed.
3. **Node-path test** (`test_knowledge_retrieve_node` / `test_nodes.py`): an `ar` turn results in a normalized query reaching retrieval. Satisfies the spec-mandated line-300 assertion at the observable boundary.
4. **Tool-path test** (`test_knowledge_lookup.py`): an `ar` `knowledge_lookup(query)` normalizes before search.
5. **Mismatch guard test** (Amendment 2): Arabic conversation + **English** tool query → **no** normalization applied (query reaches `_search` unchanged).

This set also satisfies the validation-checklist item *"Arabic/Khaleeji handling: detect → translate → process → translate back"* with real coverage rather than assumed behavior.

## 4. TD5-forward AR-recall probe — contract

The before/after measurement harness produces **TD5-shaped** data so it feeds the same forward-compatible asset used later for threshold calibration (Item #2) and reranker eval (Item #4), rather than a throwaway probe.

**Row schema:**

| field | meaning |
|---|---|
| `query` | AR info-request query text |
| `gold_article_id(s)` | corpus article(s) that answer the info need |
| `relevance_judgment` | retrieval relevance label |
| `dialect_tag` | `khaleeji` \| `msa` (per-utterance tagging requirement) |
| `variance_type` | `orthographic` \| `lexical` (Amendment 4 — see §5) |

**Set construction:**

- ~20–30 AR info-request queries against the existing 21 AR corpus articles. Each info-need phrased **both** in Khaleeji dialect and MSA, so the probe isolates exactly what the rewrite targets.
- **Seed Khaleeji variants from existing authored triggers (Amendment 3).** The skill trigger inventory (~600+ user triggers with cultural-adaptation / Khaleeji phrasings already through clinical/cultural authoring) is the source. Reuse trigger phrasings wherever an info-request framing exists; author net-new phrasings **only** where no trigger covers the info need. *First probe task: locate where those triggers actually live — they are in the skill JSON trigger/example fields, not `docs/SageAI_Skills_Knowledge_Base.md` (which has no trigger entries).*
- **Native review is the upgrade path to true TD5**, not a v1 blocker.

**Sourcing / sovereignty:** these are *retrieval-relevance* labels (which article answers a factual question), **not** clinical-safety judgments. Per the test-harness data-sovereignty posture they are synthetic harness assets — engineering-authorable, documented in a probe README, **not** gated on clinical sign-off. POC rules apply (current Railway/Supabase stack, no sovereignty blocker).

## 5. Success criteria — failure-mode tagging (Amendment 4)

The v1 rewriter is orthographic-only, so a flat Khaleeji result would be ambiguous (rewriter ineffective vs. gap is lexical and out of v1's reach). Each Khaleeji probe query is therefore tagged `variance_type`:

- **`orthographic`** — differs from corpus text only by Alef/Ta-marbuta/tatweel variation (within v1's reach).
- **`lexical`** — differs by dialect vocabulary/word choice (needs CAMeL-Tools / translation, out of v1's reach).

**Metrics:** recall@5 + MRR, **rewrite-off vs rewrite-on**, reported **split by `variance_type`**.

**Pass conditions:**

- **No regression** on MSA queries (rewrite-on must not lower MSA recall).
- **Measurable lift, or at minimum no loss,** on `orthographic` Khaleeji queries — this is what v1 is expected to fix.
- `lexical` Khaleeji results are **reported, not gated** — they form the evidence base for whether the post-POC CAMeL/translation upgrade is warranted.

Retrieval scores are captured alongside recall so the same asset seeds Item #2's abstain-threshold calibration (de-risks Item #2 for free).

## 6. Out of scope

- CAMeL-Tools lexical Khaleeji→MSA rewriter (post-POC upgrade).
- BGE-reranker-v2-m3 (Item #4, gated on corpus > 100 articles + Azure migration).
- Abstain-threshold *value* change (Item #2; this spec only produces the calibration-ready probe).
- Azure AI Search migration (this design makes it a `_search`-only swap; the migration itself is separate).

## 7. Files touched

- `src/sage_poc/knowledge/repository.py` — template-method refactor; `_preprocess_query` + `_contains_arabic`.
- `src/sage_poc/knowledge/postgres_repository.py` — `retrieve` → `_search` rename (body unchanged).
- `src/sage_poc/knowledge/rewriter.py` — unchanged (used as-is).
- Call sites `nodes/knowledge_retrieve.py`, `nodes/tools/knowledge_lookup.py` — **unchanged**.
- Tests: `test_knowledge_repository.py` (interface-contract + behavior), `test_knowledge_retrieve_node.py` / `test_nodes.py` (node), `test_knowledge_lookup.py` (tool + mismatch guard).
- Probe: new TD5-shaped AR probe fixture + README + before/after harness script.
- `Docs/superpowers/specs/2026-05-25-v7-graph-completion-design.md` — amend line 146 to reflect base-layer placement (same PR, Amendment 1 condition).
