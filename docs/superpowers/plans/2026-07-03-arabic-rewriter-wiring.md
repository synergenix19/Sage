# Arabic Query Rewriter Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the existing `normalize_arabic_query` rewriter into both knowledge-retrieval paths via a repository-agnostic base layer, restore the spec-mandated tests as real (non-vacuous) coverage, thread raw/searched query into the audit trail, and produce a TD5-forward AR-recall probe.

**Architecture:** Refactor `KnowledgeRepository` into a template method — the base `retrieve()` applies script-gated normalization (`_preprocess_query`) then delegates to an abstract `_search()`. Any repository implementation (Postgres now, Azure later) inherits the rewrite. Both call sites (`knowledge_retrieve` node, `knowledge_lookup` tool) are unchanged. Normalization coverage is asserted at the `_search` boundary so tests cannot pass vacuously.

**Tech Stack:** Python 3, LangChain (`@tool`), asyncpg + pgvector, pytest / pytest-asyncio, BGE-M3 embeddings.

## Global Constraints

- Rewrite lives in a **repository-agnostic** layer (base class), never inside a concrete repository — a concrete-class placement recreates the silent-loss regression on the Azure swap. (Spec §2, Amendment 1)
- Normalization is gated on **Arabic script presence in the query string** (Unicode `؀-ۿ`), NOT on the `language` flag. (Spec §2, Amendment 2)
- Normalization-coverage tests (node + tool) MUST observe at the `_search` boundary, never at `retrieve()`. A `retrieve()`-level mock observes the pre-normalization query and passes vacuously. (Plan note 1)
- The retrieval record carries both `query_raw` and `query_searched`; both reach the audit trail. (Plan note 2)
- v1 rewriter is orthographic-only (Alef أإآ→ا, Ta-marbuta ة→ه, tatweel strip). No lexical Khaleeji→MSA translation — that is post-POC, out of scope. (Spec §1)
- The graph-completion design doc is amended in the SAME PR (binding condition on the flagged base-layer placement). (Spec §2, Amendment 1)
- Commit per task. TDD: failing test first, then minimal implementation.

---

## File Structure

- `src/sage_poc/knowledge/repository.py` — base `KnowledgeRepository`: concrete `retrieve()` template, `_preprocess_query`, `_contains_arabic`, abstract `_search`.
- `src/sage_poc/knowledge/postgres_repository.py` — `retrieve` renamed to `_search` (body unchanged).
- `src/sage_poc/knowledge/models.py` — `KnowledgeResult` gains `query_raw`, `query_searched`.
- `src/sage_poc/knowledge/rewriter.py` — unchanged; used as-is.
- `src/sage_poc/state.py` — `SageState` gains `knowledge_query_raw`, `knowledge_query_searched`.
- `src/sage_poc/nodes/knowledge_retrieve.py` — propagate `query_raw`/`query_searched` from result to state.
- `src/sage_poc/nodes/tools/knowledge_lookup.py` — include `query_raw`/`query_searched` in returned JSON.
- `src/sage_poc/nodes/freeflow_respond.py` — capture tool-path query trace into state alongside `knowledge_source="tool_lookup"`.
- `src/sage_poc/audit.py` + `src/sage_poc/nodes/output_gate.py` — include the two query fields in the audit record.
- `Docs/superpowers/specs/2026-05-25-v7-graph-completion-design.md` — amend line ~146 to base-layer placement.
- Tests: `tests/test_knowledge_repository.py`, `tests/test_knowledge_retrieve_node.py`, `tests/test_knowledge_lookup.py`, `tests/test_knowledge_audit_trace.py` (new).
- Probe: `tests/fixtures/knowledge_probe/ar_recall_probe.jsonl` (new), `tests/fixtures/knowledge_probe/README.md` (new), `scripts/knowledge_ar_recall_probe.py` (new), `tests/test_knowledge_probe_harness.py` (new).

---

### Task 1: Template-method refactor + script-gated preprocessing

**Files:**
- Modify: `src/sage_poc/knowledge/repository.py`
- Modify: `src/sage_poc/knowledge/postgres_repository.py` (rename `retrieve` → `_search`, lines 72-116)
- Test: `tests/test_knowledge_repository.py`

**Interfaces:**
- Produces: `KnowledgeRepository.retrieve(query, language="en", top_k=5) -> KnowledgeResult` (concrete template); `KnowledgeRepository._preprocess_query(query: str) -> str` (staticmethod); `KnowledgeRepository._contains_arabic(text: str) -> bool` (staticmethod); abstract `KnowledgeRepository._search(query, language, top_k) -> KnowledgeResult`.
- Consumes: `normalize_arabic_query` from `sage_poc.knowledge.rewriter`.

- [ ] **Step 1: Write the failing interface-contract test**

Add to `tests/test_knowledge_repository.py`:

```python
@pytest.mark.asyncio
async def test_base_retrieve_normalizes_arabic_before_search():
    """Interface contract: any KnowledgeRepository normalizes an Arabic query
    BEFORE the backend _search sees it. Guarantees the rewrite survives a
    repository swap (Postgres -> Azure)."""
    from sage_poc.knowledge.repository import KnowledgeRepository
    from sage_poc.knowledge.models import KnowledgeResult

    seen = {}

    class RecordingRepo(KnowledgeRepository):
        async def _search(self, query, language="en", top_k=5):
            seen["query"] = query
            return KnowledgeResult(passages=[], abstain=True)

    repo = RecordingRepo()
    # 'أنا' contains an Alef-hamza that normalizes to 'انا'
    await repo.retrieve("أنا قلقان", language="ar", top_k=5)
    assert seen["query"] == "انا قلقان"


@pytest.mark.asyncio
async def test_base_retrieve_passes_english_through_untouched():
    from sage_poc.knowledge.repository import KnowledgeRepository
    from sage_poc.knowledge.models import KnowledgeResult

    seen = {}

    class RecordingRepo(KnowledgeRepository):
        async def _search(self, query, language="en", top_k=5):
            seen["query"] = query
            return KnowledgeResult(passages=[], abstain=True)

    repo = RecordingRepo()
    await repo.retrieve("what is CBT?", language="en")
    assert seen["query"] == "what is CBT?"


def test_contains_arabic_detects_script():
    from sage_poc.knowledge.repository import KnowledgeRepository
    assert KnowledgeRepository._contains_arabic("ما هو") is True
    assert KnowledgeRepository._contains_arabic("what is CBT") is False
    assert KnowledgeRepository._contains_arabic("CBT ما هو") is True  # mixed Araglish
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_knowledge_repository.py -k "base_retrieve or contains_arabic" -v`
Expected: FAIL — `KnowledgeRepository` is abstract / `_search` and `_contains_arabic` not defined.

- [ ] **Step 3: Refactor the base class into a template method**

Replace the body of `src/sage_poc/knowledge/repository.py` with:

```python
from __future__ import annotations
import re
from abc import ABC, abstractmethod
from sage_poc.knowledge.models import KnowledgeResult
from sage_poc.knowledge.rewriter import normalize_arabic_query

_ARABIC_RE = re.compile(r"[؀-ۿ]")


class KnowledgeRepository(ABC):
    """Abstract retrieval interface. Swap the _search implementation for Azure
    AI Search at production; query preprocessing (rewrite) lives here in the
    base so every backend inherits it — see 2026-07-03 rewriter-wiring spec §2."""

    async def retrieve(
        self,
        query: str,
        language: str = "en",
        top_k: int = 5,
    ) -> KnowledgeResult:
        """Template method: normalize the query, then delegate to the backend."""
        searched = self._preprocess_query(query)
        return await self._search(searched, language, top_k)

    @staticmethod
    def _contains_arabic(text: str) -> bool:
        return bool(_ARABIC_RE.search(text or ""))

    @classmethod
    def _preprocess_query(cls, query: str) -> str:
        # Script-gated, NOT language-flag-gated: the tool path supplies an
        # LLM-authored query that can mismatch conversation-level language.
        if cls._contains_arabic(query):
            return normalize_arabic_query(query)
        return query

    @abstractmethod
    async def _search(
        self,
        query: str,
        language: str = "en",
        top_k: int = 5,
    ) -> KnowledgeResult:
        """Backend retrieval over the ALREADY-normalized query. Returns
        KnowledgeResult with abstain=True when empty."""
        ...
```

- [ ] **Step 4: Rename the Postgres implementation's entry point**

In `src/sage_poc/knowledge/postgres_repository.py`, rename the method at line 72 from `retrieve` to `_search`. Change only the signature line; the body (lines 78-116) is unchanged:

```python
    async def _search(
        self,
        query: str,
        language: str = "en",
        top_k: int = 5,
    ) -> KnowledgeResult:
        # 'simple' tokenises on whitespace (language-agnostic); 'english' adds stemming+stopwords.
        tsconfig = "simple" if language == "ar" else "english"
        ...  # (rest of the existing body unchanged)
```

- [ ] **Step 5: Run the new + existing repository tests to verify pass**

Run: `pytest tests/test_knowledge_repository.py -v`
Expected: PASS — new contract tests pass; existing `test_postgres_repo_*` tests still pass (they mock the pool and call `repo.retrieve(...)`, which now flows through the template into `_search`).

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/knowledge/repository.py src/sage_poc/knowledge/postgres_repository.py tests/test_knowledge_repository.py
git commit -m "feat(knowledge): rewrite in repository base template, script-gated"
```

---

### Task 2: Carry query_raw / query_searched onto the result and into the audit trail

**Files:**
- Modify: `src/sage_poc/knowledge/models.py` (KnowledgeResult, lines 20-23)
- Modify: `src/sage_poc/knowledge/repository.py` (template `retrieve`, from Task 1)
- Modify: `src/sage_poc/state.py` (SageState, after line 68)
- Modify: `src/sage_poc/audit.py` (`_build_session_audit_row`, lines 110-112)
- Modify: `src/sage_poc/nodes/output_gate.py` (lines 641-645) — **log line only**, not a DB write
- Create: `migrations/005_add_knowledge_query_trace_to_session_audit.sql`
- Test: `tests/test_knowledge_repository.py`, `tests/test_knowledge_audit_trace.py` (new)

**Audit-sink note:** `_build_session_audit_row` feeds a Supabase PostgREST insert into the **fixed-column** `session_audit` table (`audit.py:140`, `write_session_audit`). New keys in that row will fail the insert (PostgREST rejects unknown columns) unless the columns exist — hence the migration below. The `output_gate.py:641` dict is only `json.dumps`'d into a `_log.info` line (`output_gate.py:651`), so it needs no migration; adding keys there is a pure logging enrichment.

**Interfaces:**
- Consumes: `KnowledgeRepository.retrieve` (Task 1).
- Produces: `KnowledgeResult.query_raw: str`, `KnowledgeResult.query_searched: str` (default `""`); state keys `knowledge_query_raw`, `knowledge_query_searched`; audit-record keys `knowledge_query_raw`, `knowledge_query_searched`.

- [ ] **Step 1: Write the failing test — template stamps raw + searched**

Add to `tests/test_knowledge_repository.py`:

```python
@pytest.mark.asyncio
async def test_retrieve_stamps_raw_and_searched_query():
    from sage_poc.knowledge.repository import KnowledgeRepository
    from sage_poc.knowledge.models import KnowledgeResult

    class RecordingRepo(KnowledgeRepository):
        async def _search(self, query, language="en", top_k=5):
            return KnowledgeResult(passages=[], abstain=True)

    result = await RecordingRepo().retrieve("أنا قلقان", language="ar")
    assert result.query_raw == "أنا قلقان"
    assert result.query_searched == "انا قلقان"
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_knowledge_repository.py::test_retrieve_stamps_raw_and_searched_query -v`
Expected: FAIL — `KnowledgeResult` has no attribute `query_raw`.

- [ ] **Step 3: Add fields to KnowledgeResult**

In `src/sage_poc/knowledge/models.py`, replace the `KnowledgeResult` dataclass:

```python
@dataclass
class KnowledgeResult:
    passages: list[KnowledgePassage] = field(default_factory=list)
    abstain: bool = False
    query_raw: str = ""       # query as submitted by the caller (pre-normalization)
    query_searched: str = ""  # query actually sent to the backend (post-normalization)
```

- [ ] **Step 4: Stamp the fields in the template**

In `src/sage_poc/knowledge/repository.py`, update `retrieve`:

```python
    async def retrieve(self, query, language="en", top_k=5) -> KnowledgeResult:
        searched = self._preprocess_query(query)
        result = await self._search(searched, language, top_k)
        result.query_raw = query
        result.query_searched = searched
        return result
```

- [ ] **Step 5: Run to verify it passes**

Run: `pytest tests/test_knowledge_repository.py::test_retrieve_stamps_raw_and_searched_query -v`
Expected: PASS.

- [ ] **Step 6: Write the failing audit-trace test**

Create `tests/test_knowledge_audit_trace.py`:

```python
"""The audit record must carry both the raw and the searched query so the
normalization applied inside the repository is not invisible to the trail."""
from sage_poc.audit import _build_session_audit_row


def test_audit_record_includes_raw_and_searched_query():
    state = {
        "knowledge_source": "node_6",
        "knowledge_passages": [],
        "knowledge_abstain": True,
        "knowledge_query_raw": "أنا قلقان",
        "knowledge_query_searched": "انا قلقان",
    }
    record = _build_session_audit_row(state)
    assert record["knowledge_query_raw"] == "أنا قلقان"
    assert record["knowledge_query_searched"] == "انا قلقان"
```

- [ ] **Step 7: Run to verify it fails**

Run: `pytest tests/test_knowledge_audit_trace.py -v`
Expected: FAIL — keys absent from the record.

- [ ] **Step 8: Add state fields and thread into both audit assemblers**

In `src/sage_poc/state.py`, after line 68 add to `SageState`:

```python
    knowledge_query_raw: str        # query as submitted (pre-normalization)
    knowledge_query_searched: str   # query actually searched (post-normalization)
```

In `src/sage_poc/audit.py`, inside `_build_session_audit_row` after line 112 (`"knowledge_abstain": ...`) add:

```python
        "knowledge_query_raw":      state.get("knowledge_query_raw") or None,
        "knowledge_query_searched": state.get("knowledge_query_searched") or None,
```

In `src/sage_poc/nodes/output_gate.py`, after line 645 add (log-line enrichment only — no DB/migration impact):

```python
            "knowledge_query_raw": state.get("knowledge_query_raw", ""),
            "knowledge_query_searched": state.get("knowledge_query_searched", ""),
```

- [ ] **Step 9: Add the session_audit column migration**

The `session_audit` table is fixed-column (Supabase PostgREST), so the two new keys need real columns or the insert fails. Create `migrations/005_add_knowledge_query_trace_to_session_audit.sql`, matching the idempotent style of `004_add_s3_score_to_session_audit.sql`:

```sql
-- Add knowledge_query_raw / knowledge_query_searched to session_audit.
-- The knowledge rewriter now normalizes Arabic queries inside the repository
-- base layer, so the query actually searched differs from the query submitted.
-- Recording both keeps that transform visible to the audit trail (v7 traceability).
-- Existing rows get NULL (no backfill — historical turns predate the columns).
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS knowledge_query_raw text;
ALTER TABLE session_audit ADD COLUMN IF NOT EXISTS knowledge_query_searched text;
```

> This migration must be applied to the target Supabase project **before** the change is deployed (the same one holding `session_audit`; see the prod-vs-repo project note in the deploy checklist). Applying it is a deploy step, not something the test suite exercises.

- [ ] **Step 10: Run to verify it passes**

Run: `pytest tests/test_knowledge_audit_trace.py tests/test_knowledge_repository.py -v`
Expected: PASS.

- [ ] **Step 11: Commit**

```bash
git add src/sage_poc/knowledge/models.py src/sage_poc/knowledge/repository.py src/sage_poc/state.py src/sage_poc/audit.py src/sage_poc/nodes/output_gate.py migrations/005_add_knowledge_query_trace_to_session_audit.sql tests/test_knowledge_repository.py tests/test_knowledge_audit_trace.py
git commit -m "feat(knowledge): carry raw+searched query into retrieval result and audit trail"
```

---

### Task 3: Node-path normalization coverage (observed at `_search`) + state propagation

**Files:**
- Modify: `src/sage_poc/nodes/knowledge_retrieve.py` (lines 44-49)
- Test: `tests/test_knowledge_retrieve_node.py`

**Interfaces:**
- Consumes: `KnowledgeRepository._search` seam (Task 1), `KnowledgeResult.query_raw/query_searched` (Task 2).
- Produces: node result dict gains `knowledge_query_raw`, `knowledge_query_searched`.

- [ ] **Step 1: Write the failing test — Arabic query reaches `_search` normalized**

Add to `tests/test_knowledge_retrieve_node.py`. This patches `_search`, NOT `retrieve`, so it exercises the real template (non-vacuous per plan note 1):

```python
@pytest.mark.asyncio
async def test_node_arabic_query_normalized_before_search():
    """Node path: an Arabic turn reaches the backend _search with a normalized
    query. Observed at _search so the assertion cannot pass without the rewrite."""
    from sage_poc.knowledge.models import KnowledgeResult
    from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository
    from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node

    seen = {}

    async def fake_search(self, query, language="en", top_k=5):
        seen["query"] = query
        seen["language"] = language
        return KnowledgeResult(passages=[], abstain=True)

    with patch.object(PostgresKnowledgeRepository, "_search", fake_search):
        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
            await knowledge_retrieve_node(
                _kr_state(detected_language="ar", raw_message="أنا قلقان", message_en="I am anxious")
            )

    assert seen["query"] == "انا قلقان"   # normalized, not raw "أنا قلقان"
    assert seen["language"] == "ar"


@pytest.mark.asyncio
async def test_node_writes_query_trace_to_state():
    from sage_poc.knowledge.models import KnowledgeResult
    from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository
    from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node

    async def fake_search(self, query, language="en", top_k=5):
        return KnowledgeResult(passages=[], abstain=True)

    with patch.object(PostgresKnowledgeRepository, "_search", fake_search):
        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
            result = await knowledge_retrieve_node(
                _kr_state(detected_language="ar", raw_message="أنا قلقان", message_en="I am anxious")
            )

    assert result["knowledge_query_raw"] == "أنا قلقان"
    assert result["knowledge_query_searched"] == "انا قلقان"
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_knowledge_retrieve_node.py -k "normalized_before_search or writes_query_trace" -v`
Expected: FAIL — node result has no `knowledge_query_raw`; and (before fix) if it read normalization elsewhere it would not be present. `seen["query"]` assertion drives the coverage.

- [ ] **Step 3: Propagate the query trace from result to state**

In `src/sage_poc/nodes/knowledge_retrieve.py`, replace the return block (lines 44-49):

```python
    return {
        "knowledge_passages": [p.to_dict() for p in result.passages],
        "knowledge_abstain": result.abstain,
        "knowledge_source": "node_6",
        "knowledge_query_raw": result.query_raw,
        "knowledge_query_searched": result.query_searched,
        "path": path,
    }
```

(No other change: the node still calls `repo.retrieve(query, language=lang, top_k=5)`; the template does the normalization. The `test_knowledge_retrieve_routes_arabic_to_ar_corpus` test still asserts the node passes `raw_message` to `retrieve` — still true, since normalization happens below `retrieve`.)

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_knowledge_retrieve_node.py -v`
Expected: PASS — all node tests, new and existing.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/nodes/knowledge_retrieve.py tests/test_knowledge_retrieve_node.py
git commit -m "test(knowledge): node-path Arabic normalization asserted at _search; emit query trace"
```

---

### Task 4: Tool-path normalization coverage + language-mismatch guard + JSON trace

**Files:**
- Modify: `src/sage_poc/nodes/tools/knowledge_lookup.py` (lines 52-57)
- Modify: `src/sage_poc/nodes/freeflow_respond.py` (tool-lookup capture near line 211-213)
- Test: `tests/test_knowledge_lookup.py`

**Interfaces:**
- Consumes: `KnowledgeRepository._search` seam (Task 1), `KnowledgeResult.query_raw/query_searched` (Task 2).
- Produces: tool JSON gains `query_raw`, `query_searched`; state gains tool-path `knowledge_query_raw/searched`.

- [ ] **Step 1: Write the failing tests — normalization + mismatch guard + JSON trace**

Add to `tests/test_knowledge_lookup.py`:

```python
@pytest.mark.asyncio
async def test_tool_arabic_query_normalized_before_search():
    """Tool path: an Arabic tool query reaches _search normalized. Observed at
    _search (non-vacuous)."""
    from sage_poc.knowledge.models import KnowledgeResult
    from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository
    from sage_poc.nodes.tools.knowledge_lookup import make_knowledge_lookup_tool

    seen = {}

    async def fake_search(self, query, language="en", top_k=5):
        seen["query"] = query
        return KnowledgeResult(passages=[], abstain=True)

    tool = make_knowledge_lookup_tool(language="ar")
    with patch.object(PostgresKnowledgeRepository, "_search", fake_search):
        with patch("sage_poc.nodes.tools.knowledge_lookup._get_pool", return_value=MagicMock()):
            await tool.ainvoke({"query": "أنا قلقان"})

    assert seen["query"] == "انا قلقان"


@pytest.mark.asyncio
async def test_tool_english_query_in_arabic_conversation_not_normalized():
    """Language flag is 'ar' but the LLM-authored query is English — script
    gating means it is NOT normalized (reaches _search unchanged)."""
    from sage_poc.knowledge.models import KnowledgeResult
    from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository
    from sage_poc.nodes.tools.knowledge_lookup import make_knowledge_lookup_tool

    seen = {}

    async def fake_search(self, query, language="en", top_k=5):
        seen["query"] = query
        return KnowledgeResult(passages=[], abstain=True)

    tool = make_knowledge_lookup_tool(language="ar")  # Arabic conversation
    with patch.object(PostgresKnowledgeRepository, "_search", fake_search):
        with patch("sage_poc.nodes.tools.knowledge_lookup._get_pool", return_value=MagicMock()):
            await tool.ainvoke({"query": "what is CBT?"})   # English query

    assert seen["query"] == "what is CBT?"   # untouched


@pytest.mark.asyncio
async def test_tool_json_includes_query_trace():
    from sage_poc.knowledge.models import KnowledgeResult
    from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository
    from sage_poc.nodes.tools.knowledge_lookup import make_knowledge_lookup_tool

    async def fake_search(self, query, language="en", top_k=5):
        return KnowledgeResult(passages=[], abstain=True)

    tool = make_knowledge_lookup_tool(language="ar")
    with patch.object(PostgresKnowledgeRepository, "_search", fake_search):
        with patch("sage_poc.nodes.tools.knowledge_lookup._get_pool", return_value=MagicMock()):
            raw = await tool.ainvoke({"query": "أنا قلقان"})

    data = json.loads(raw)
    assert data["query_raw"] == "أنا قلقان"
    assert data["query_searched"] == "انا قلقان"
```

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_knowledge_lookup.py -k "normalized_before_search or not_normalized or query_trace" -v`
Expected: FAIL — `query_raw`/`query_searched` absent from JSON; `_search` unknown until Task 1 is present (it is).

- [ ] **Step 3: Include the query trace in the tool's returned JSON**

In `src/sage_poc/nodes/tools/knowledge_lookup.py`, replace the success return (lines 52-57):

```python
            repo = PostgresKnowledgeRepository(pool)
            result = await repo.retrieve(query, language=language, top_k=5)
            return json.dumps({
                "passages": [p.to_dict() for p in result.passages],
                "abstain": result.abstain,
                "query_raw": result.query_raw,
                "query_searched": result.query_searched,
            })
```

- [ ] **Step 4: Capture the tool-path trace into state in freeflow_respond**

In `src/sage_poc/nodes/freeflow_respond.py`, where `knowledge_source` is set to `"tool_lookup"` after the tool loop (near line 211-213), parse the last `knowledge_lookup` tool result and surface its query trace. Add a helper near `_knowledge_lookup_fired` (line 35):

```python
def _knowledge_lookup_trace(messages: list) -> dict:
    """Extract query_raw/query_searched from the last knowledge_lookup tool result."""
    for msg in reversed(messages or []):
        name = getattr(msg, "name", None) or (isinstance(msg, dict) and msg.get("name"))
        if name == "knowledge_lookup":
            content = getattr(msg, "content", None) or (isinstance(msg, dict) and msg.get("content"))
            try:
                data = json.loads(content)
                return {
                    "knowledge_query_raw": data.get("query_raw", ""),
                    "knowledge_query_searched": data.get("query_searched", ""),
                }
            except (TypeError, ValueError):
                return {}
    return {}
```

Then update the existing `knowledge_source_update` block (lines 211-214) — the dict is already merged into the return via `**knowledge_source_update` at line 223, so adding the trace here surfaces it to state:

```python
    # Determine knowledge_source: if knowledge_lookup tool was invoked, override with "tool_lookup"
    knowledge_source_update = {}
    if _knowledge_lookup_fired(tool_ai_messages):
        knowledge_source_update = {"knowledge_source": "tool_lookup"}
        knowledge_source_update.update(_knowledge_lookup_trace(tool_ai_messages))
```

> `import json` must be present at the top of `freeflow_respond.py`; add it if the module does not already import it.

- [ ] **Step 5: Run to verify pass**

Run: `pytest tests/test_knowledge_lookup.py -v`
Expected: PASS — all tool tests, new and existing.

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/nodes/tools/knowledge_lookup.py src/sage_poc/nodes/freeflow_respond.py tests/test_knowledge_lookup.py
git commit -m "test(knowledge): tool-path Arabic normalization + language-mismatch guard; emit query trace"
```

---

### Task 5: Amend the graph-completion design doc (binding condition)

**Files:**
- Modify: `Docs/superpowers/specs/2026-05-25-v7-graph-completion-design.md` (line ~146 and the Node 6 flow at ~228, ~300)

**Interfaces:** none (documentation).

- [ ] **Step 1: Update the Node 6 rewriter description**

At line ~146, change the literal *"Calls rewriter if `detected_language == 'ar'`"* to reflect base-layer placement. Replace with:

```markdown
Reads `user_message`, `detected_language`, `intent` from state. Calls
`postgres_repository.retrieve()`. Query normalization (Khaleeji→MSA, POC-level
orthographic) is applied inside the repository base layer
(`KnowledgeRepository.retrieve` template, script-gated), so BOTH the node path
and the `knowledge_lookup` tool path inherit it and the Azure AI Search swap
preserves it. See 2026-07-03 Arabic-rewriter-wiring spec §2. Writes
`knowledge_passages`, `knowledge_abstain`, `knowledge_source="node_6"`,
`knowledge_query_raw`, `knowledge_query_searched` to state.
```

- [ ] **Step 2: Update the flow diagram note and the test-matrix row**

At line ~228 (`rewriter (if detected_language == "ar")`) change the annotation to `repository base normalizes Arabic (script-gated) before search`. At line ~300, change the test-matrix row from *"Node 6 — Arabic rewriter called"* to:

```markdown
| Node 6 — Arabic query normalized before search | `test_knowledge_retrieve_node.py::test_node_arabic_query_normalized_before_search` | Observed at `_search`; Arabic query normalized, English untouched |
```

- [ ] **Step 3: Commit**

```bash
git add "Docs/superpowers/specs/2026-05-25-v7-graph-completion-design.md"
git commit -m "docs(v7): Node 6 rewrite placed in repository base layer (spec-code alignment)"
```

---

### Task 6: TD5-forward AR-recall probe (fixture + README + harness)

**Files:**
- Create: `tests/fixtures/knowledge_probe/ar_recall_probe.jsonl`
- Create: `tests/fixtures/knowledge_probe/README.md`
- Create: `scripts/knowledge_ar_recall_probe.py`
- Test: `tests/test_knowledge_probe_harness.py`

**Interfaces:**
- Consumes: `KnowledgeRepository._search` (rewrite-off baseline) vs `retrieve` (rewrite-on), `KnowledgeResult`.
- Produces: `scripts/knowledge_ar_recall_probe.py::recall_at_k(gold_ids, retrieved_ids, k) -> float`, `reciprocal_rank(gold_ids, retrieved_ids) -> float`, `score_probe(rows, retrieve_fn) -> dict` (metrics split by `variance_type`).

- [ ] **Step 1: Locate the authored Khaleeji triggers (probe seed source)**

Run: `grep -rln "trigger\|examples" src/sage_poc/skills 2>/dev/null; ls src/sage_poc/skills 2>/dev/null | head`
Then inspect one skill JSON to find the Arabic trigger/example fields (Arabic example is at position `[0]` per the Arabic-example-ordering convention). Record which field holds Khaleeji phrasings. These seed the `khaleeji` probe rows where an info-request framing exists; author net-new phrasings only where no trigger covers the info need.

- [ ] **Step 2: Define the probe fixture schema with two seed rows**

Create `tests/fixtures/knowledge_probe/ar_recall_probe.jsonl` (one JSON object per line). Two illustrative rows — extend to ~20–30 following Step 1's seeding rule, each info-need present in BOTH a `khaleeji` and an `msa` phrasing:

```jsonl
{"query": "شو هو العلاج المعرفي السلوكي؟", "gold_article_ids": ["cbt-001-ar"], "relevance_judgment": "relevant", "dialect_tag": "khaleeji", "variance_type": "lexical"}
{"query": "ما هو العلاج المعرفي السلوكي؟", "gold_article_ids": ["cbt-001-ar"], "relevance_judgment": "relevant", "dialect_tag": "msa", "variance_type": "baseline"}
```

**Tagging rule (do not deviate):** `variance_type` classifies **Khaleeji** queries by what the orthographic rewriter can reach (`orthographic` = within reach, `lexical` = needs post-POC translation). **MSA** rows are the regression baseline and are tagged `variance_type: "baseline"` — never `orthographic`. Tagging MSA rows `orthographic` would pollute the `msa/orthographic` bucket and muddy the split. This makes the pass conditions map one-to-one onto buckets: `msa/baseline` → no regression; `khaleeji/orthographic` → expected lift; `khaleeji/lexical` → reported only.

- [ ] **Step 3: Write the README (sovereignty + provenance)**

Create `tests/fixtures/knowledge_probe/README.md`:

```markdown
# AR-recall probe (TD5-forward)

Retrieval-relevance labels only (which corpus article answers a factual query),
NOT clinical-safety judgments. Synthetic harness asset under POC data-sovereignty
rules — engineering-authored, not clinical sign-off gated. Native-Khaleeji review
is the upgrade path toward true TD5.

Schema per row: query, gold_article_ids[], relevance_judgment, dialect_tag
(khaleeji|msa), variance_type (orthographic|lexical|baseline).

variance_type classifies KHALEEJI queries by what the rewriter can reach; MSA rows
are the regression baseline:

- orthographic (khaleeji): differs from corpus text only by Alef/Ta-marbuta/tatweel —
  within the v1 rewriter's reach. Expected: lift, or at minimum no loss.
- lexical (khaleeji): differs by dialect vocabulary — needs post-POC CAMeL/translation;
  results are REPORTED, not gated.
- baseline (msa): standard MSA phrasing, the no-regression control. Never tag MSA rows
  "orthographic" — it pollutes the split.

Bucket-to-acceptance mapping: msa/baseline = no regression; khaleeji/orthographic =
expected lift; khaleeji/lexical = reported only.

Khaleeji rows seeded from authored skill triggers where an info-request framing
exists (see plan Task 6 Step 1); net-new phrasings authored only for uncovered needs.
```

- [ ] **Step 4: Write the failing harness metric tests**

Create `tests/test_knowledge_probe_harness.py`:

```python
from scripts.knowledge_ar_recall_probe import recall_at_k, reciprocal_rank


def test_recall_at_k_hit_and_miss():
    assert recall_at_k(["a"], ["x", "a", "y"], k=5) == 1.0
    assert recall_at_k(["a"], ["x", "y", "z"], k=5) == 0.0
    assert recall_at_k(["a"], ["x", "y", "a"], k=2) == 0.0  # 'a' is at rank 3, outside k=2


def test_reciprocal_rank():
    assert reciprocal_rank(["a"], ["a", "b"]) == 1.0
    assert reciprocal_rank(["a"], ["b", "a"]) == 0.5
    assert reciprocal_rank(["a"], ["b", "c"]) == 0.0
```

- [ ] **Step 5: Run to verify it fails**

Run: `pytest tests/test_knowledge_probe_harness.py -v`
Expected: FAIL — `scripts.knowledge_ar_recall_probe` does not exist.

- [ ] **Step 6: Implement the harness**

Create `scripts/knowledge_ar_recall_probe.py`:

```python
"""AR-recall probe: recall@5 + MRR, rewrite-off vs rewrite-on, split by
variance_type. Rewrite-off calls _search directly (raw query); rewrite-on calls
retrieve() (template normalizes). See 2026-07-03 rewriter-wiring spec §5."""
from __future__ import annotations
import asyncio
import json
from pathlib import Path

_PROBE = Path(__file__).parent.parent / "tests" / "fixtures" / "knowledge_probe" / "ar_recall_probe.jsonl"


def recall_at_k(gold_ids, retrieved_ids, k=5) -> float:
    top = retrieved_ids[:k]
    return 1.0 if any(g in top for g in gold_ids) else 0.0


def reciprocal_rank(gold_ids, retrieved_ids) -> float:
    for i, rid in enumerate(retrieved_ids, start=1):
        if rid in gold_ids:
            return 1.0 / i
    return 0.0


def load_rows(path=_PROBE):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


async def score_probe(rows, retrieve_fn) -> dict:
    """retrieve_fn(query, language) -> list[source_id]. Aggregates recall@5 + MRR
    overall and per (dialect_tag, variance_type) cell."""
    buckets: dict = {}
    for row in rows:
        ids = await retrieve_fn(row["query"], "ar")
        r = recall_at_k(row["gold_article_ids"], ids, k=5)
        rr = reciprocal_rank(row["gold_article_ids"], ids)
        for key in ("overall", f'{row["dialect_tag"]}/{row["variance_type"]}'):
            b = buckets.setdefault(key, {"n": 0, "recall_sum": 0.0, "rr_sum": 0.0})
            b["n"] += 1
            b["recall_sum"] += r
            b["rr_sum"] += rr
    return {
        k: {"n": b["n"], "recall_at_5": b["recall_sum"] / b["n"], "mrr": b["rr_sum"] / b["n"]}
        for k, b in buckets.items()
    }


async def _main():
    import os
    import asyncpg
    from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository

    # Build our own pool from DATABASE_URL — do NOT import `server.app`: its
    # app.state._db_pool is only populated by FastAPI startup hooks, so a
    # standalone run would get None and crash on the first query. Use the same
    # connection string the server uses (server.py:212, :240).
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL not set — cannot run the AR-recall probe.")
    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=4)
    try:
        repo = PostgresKnowledgeRepository(pool)
        rows = load_rows()

        async def rewrite_off(query, language):
            res = await repo._search(query, language=language, top_k=5)   # raw query, no normalization
            return [p.source_id for p in res.passages]

        async def rewrite_on(query, language):
            res = await repo.retrieve(query, language=language, top_k=5)   # template normalizes
            return [p.source_id for p in res.passages]

        off = await score_probe(rows, rewrite_off)
        on = await score_probe(rows, rewrite_on)
        print(json.dumps({"rewrite_off": off, "rewrite_on": on}, ensure_ascii=False, indent=2))
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(_main())
```

- [ ] **Step 7: Run to verify the metric tests pass**

Run: `pytest tests/test_knowledge_probe_harness.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add tests/fixtures/knowledge_probe/ scripts/knowledge_ar_recall_probe.py tests/test_knowledge_probe_harness.py
git commit -m "feat(knowledge): TD5-forward AR-recall probe harness (recall@5+MRR, split by variance_type)"
```

- [ ] **Step 9: Run the live probe and record the before/after (manual, needs DB)**

Run: `python -m scripts.knowledge_ar_recall_probe`
Record the `rewrite_off` vs `rewrite_on` JSON. Acceptance (spec §5): no regression on `msa`; measurable lift or no loss on `khaleeji/orthographic`; `khaleeji/lexical` reported, not gated. Paste results into the PR description as the rewrite's evidence base.

---

## Full regression

- [ ] **Final: Run the knowledge suite + broader regression**

Run: `pytest tests/test_knowledge_repository.py tests/test_knowledge_retrieve_node.py tests/test_knowledge_lookup.py tests/test_knowledge_audit_trace.py tests/test_knowledge_probe_harness.py tests/test_routing.py -v`
Expected: PASS. Then run the full suite (`pytest -q`) to confirm no collateral regressions before opening the PR.
