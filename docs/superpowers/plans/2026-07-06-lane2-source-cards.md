# Lane 2 — Structured-Content Affordance Layer: Source Cards + KB Video Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface KB article sources — as a link card (`article`) or an embedded video (`video`) — rendered *outside* the reply prose, so "Ask" answers become linkable/watchable, with zero change to the safety path.

**Architecture:** Additive pass-through on the existing `X-Sage-*` response-header channel. `citation_metadata` already carries `title`/`source_url` (ingestion.py:103-108) and gains an optional provider-agnostic `video_url`. The repository reads these keys; the API emits one new header `X-Sage-Sources` = a **typed list** `[{type, title, url, citation}]`; the Next.js frontend parses it (mirroring the existing `X-Sage-Crisis-Flags` pattern) and renders a card (`article` → link, `video` → embed). No LLM-prose change (L0 forbids markdown), no `SkillStep`/`Skill` schema change, no Node-1/precedence touch. **Videos ride the *knowledge* channel (KB articles) only — videos attached to *skill steps* remain the deferred, approval-gated Item 3; this line is not blurred to get samples up faster.**

**Tech Stack:** Python 3.12 / FastAPI / pydantic-dataclasses (backend, repo `sage-poc`); Next.js / TypeScript / React (frontend, repo `cdai`); pytest (backend), vitest + Playwright (frontend).

## Plan corrections (2026-07-06, post-topology-check)
- **Package manager is `npm`, NOT `pnpm`.** `apps/web` uses npm (`package-lock.json`; `"test": "vitest run"`). Frontend test command: `cd /Users/knowledgebase/Documents/Sage/cdai-lane2-wt/apps/web && npm test -- <pattern>`. (The original plan said `pnpm --filter web` — wrong; do not resurrect in Item 2's plan.)
- **One remote, dual-root.** `sage-poc` (backend) and `cdai` (frontend) share `github.com/synergenix19/Sage`, but `master` = backend and `main` = frontend. Backend branch `feat/lane2-source-cards` off `master` (PR #118 → master). Frontend branch **`cdai/feat/lane2-source-cards` off `main`** (per the `cdai/` prefix convention), PR → `main`.
- **Frontend runs in an isolated worktree:** `/Users/knowledgebase/Documents/Sage/cdai-lane2-wt` (off `origin/main`), leaving `feat/chat-ui-polish` + its uncommitted files untouched. Overlap check: NONE of the Lane 2 files are dirty on `feat/chat-ui-polish`.

## Global Constraints
- **One remote, dual-root (see corrections above):** backend on `master` (branch `feat/lane2-source-cards`, PR #118); frontend on `main` (branch `cdai/feat/lane2-source-cards`, worktree `cdai-lane2-wt`). Two coordinated PRs. Backend ships first (additive, inert without the frontend).
- **Byte-identical when empty:** no KB passages → header absent → no card → identical to today. New model fields default `""`.
- **Safety-path suppression is an ALLOWLIST, not a denylist.** `X-Sage-Sources` is emitted ONLY when `gate_path` is in an explicit allowlist of ordinary content paths. `== "crisis"` would fail *open* for every future safety route (medical/HR/IPV set their own `gate_path`); the allowlist fails *safe* on those and on any unknown value.
- **Bilingual is a validation rule, not an edge case.** `_sources_header` uses `json.dumps(..., ensure_ascii=True)` (HTTP headers are latin-1; Arabic titles MUST be `\uXXXX`-escaped and round-trip through `JSON.parse`). Arabic-title round-trip + RTL card rendering are asserted, not assumed.
- **Dedupe + cap:** dedupe sources by `source_url` (hierarchical chunking yields multiple chunks per article → duplicate entries), cap at **3** (matches L4's `max_passages` evidence budget; bounds header size).
- **Audit-traceability invariant:** the emitted sources are a **subset of the audited passage set** (`session_audit.knowledge_passage_ids`) — a source shown to the user is always traceable to an audited passage. Enforced by construction (sources derive from `result["knowledge_passages"]`, the same list that is audited) and stated in a comment.
- **Provider-agnostic video field:** store the **canonical video URL** (full URL), detect provider at render time. The field is `video_url` — **never** named or shaped `youtube_id`. This makes "replace with our own hosted videos" a data swap (update the URL) + one renderer branch (HTML5 `<video>`), not a migration.
- **No L0 change, no skill-schema change, no Node-1 / precedence / safety-flag touch. Crisis path excluded.**
- **Commit trailer:** end each commit with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **Scope:** Item 1 (source cards + KB video). Items 2 (affordance contract) & 3 (`SkillStep.media`) are separate plans — see "Deferred".

---

## File Structure (Item 1)

**Backend (`sage-poc`):**
- `src/sage_poc/knowledge/models.py` — `KnowledgePassage` gains `source_url`, `title`, `video_url`; `to_dict()` emits them.
- `src/sage_poc/knowledge/ingestion.py` — `citation_metadata` gains optional `video_url`; `video_url` added to `_HASHED_FIELDS`.
- `src/sage_poc/knowledge/postgres_repository.py` — `_row_to_passage(row)` populates the three fields from `citation_metadata`.
- `src/sage_poc/server.py` — `_sources_header(result)` (allowlist, ensure_ascii, dedupe+cap, typed entries) + conditional `X-Sage-Sources`.
- `src/sage_poc/state.py` — `knowledge_passages` doc-comment.
- `tests/test_knowledge_source_cards.py` — all backend tests.

**Frontend (`cdai`):**
- `packages/types/src/index.ts` — `Source = {type, title, url, citation}` + `sources?` on the message type.
- `apps/web/app/api/chat/route.ts` — parse `X-Sage-Sources`, thread onto the message, expose-headers.
- `apps/web/components/chat/SourceCard.tsx` — new; type-switch (`article` link / `video` embed via `VideoEmbed`).
- `apps/web/components/chat/VideoEmbed.tsx` — new; provider detection (youtube → `youtube-nocookie.com` iframe; else HTML5 `<video>`).
- `apps/web/components/chat/message-bubble.tsx` — render `<SourceCard>` when `message.sources?.length`.

---

## Task 1: `KnowledgePassage` carries `source_url`, `title`, `video_url` (backend)

**Files:** Modify `src/sage_poc/knowledge/models.py:4-17`; Test `tests/test_knowledge_source_cards.py`.

**Interfaces:** Produces `KnowledgePassage(text, source_id, citation, relevance_score, source_url="", title="", video_url="")`; `to_dict()` includes those three keys.

- [ ] **Step 1: Write the failing test** (replace the two placeholder tests already in the file)

```python
from sage_poc.knowledge.models import KnowledgePassage

def test_existing_construction_defaults_new_fields_empty():
    d = KnowledgePassage(text="t", source_id="a-en-000", citation="Anxiety 101", relevance_score=0.5).to_dict()
    assert d["source_url"] == "" and d["title"] == "" and d["video_url"] == ""
    assert d["text"] == "t" and d["citation"] == "Anxiety 101"

def test_passage_carries_url_title_video_through_to_dict():
    d = KnowledgePassage(
        text="t", source_id="a-en-000", citation="Anxiety 101", relevance_score=0.5,
        source_url="https://kb.sage/a", title="Understanding Anxiety",
        video_url="https://www.youtube.com/watch?v=abc123",
    ).to_dict()
    assert d["source_url"] == "https://kb.sage/a"
    assert d["title"] == "Understanding Anxiety"
    assert d["video_url"] == "https://www.youtube.com/watch?v=abc123"
```

- [ ] **Step 2: Run to verify it fails** — `cd sage-poc && uv run pytest tests/test_knowledge_source_cards.py -q` → FAIL (`KeyError: 'source_url'`).

- [ ] **Step 3: Add the fields + emit in `to_dict`**

```python
@dataclass
class KnowledgePassage:
    text: str
    source_id: str
    citation: str
    relevance_score: float
    source_url: str = ""    # article link from citation_metadata
    title: str = ""         # article title from citation_metadata
    video_url: str = ""     # canonical (provider-agnostic) video URL, "" when none

    def to_dict(self) -> dict:
        return {
            "text": self.text, "source_id": self.source_id, "citation": self.citation,
            "relevance_score": self.relevance_score,
            "source_url": self.source_url, "title": self.title, "video_url": self.video_url,
        }
```

- [ ] **Step 4: Run to verify pass** — same command → PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(knowledge): KnowledgePassage carries source_url + title + video_url\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"`.

---

## Task 2: Ingestion carries `video_url` in `citation_metadata` (backend)

**Files:** Modify `src/sage_poc/knowledge/ingestion.py:30-31,103-108`; Test `tests/test_knowledge_source_cards.py` (+ existing `tests/test_knowledge_ingestion.py` stays green).

**Interfaces:** `citation_metadata` dict gains `"video_url"`. `video_url` is OPTIONAL in the article JSON (absent → `""`), so existing corpus is unaffected.

- [ ] **Step 1: Write the failing test**

```python
def test_ingestion_citation_meta_includes_video_url():
    from sage_poc.knowledge.ingestion import content_hash  # video_url must affect the hash
    a = {"article_id": "v-001", "language": "en", "title": "T", "source_url": "https://kb/v",
         "citation": "C", "content": "body", "is_crisis_content": False,
         "video_url": "https://www.youtube.com/watch?v=abc"}
    b = {**a, "video_url": ""}
    assert content_hash(a) != content_hash(b)   # changing the video re-ingests
```

- [ ] **Step 2: Run to verify it fails** — `uv run pytest tests/test_knowledge_source_cards.py -k video_url -q` → FAIL (hash equal; `video_url` not hashed).

- [ ] **Step 3: Implement** — in `ingestion.py`:
  - Add `"video_url"` to `_HASHED_FIELDS` (after `"source_url"`).
  - In `citation_meta` (:103-108) add `"video_url": article.get("video_url", "")`.
  - `video_url` is NOT added to `_REQUIRED_FIELDS` (optional).

- [ ] **Step 4: Run to verify pass** — `uv run pytest tests/test_knowledge_source_cards.py tests/test_knowledge_ingestion.py -q` → PASS.
- [ ] **Step 5: Commit** — `feat(knowledge): optional video_url in citation_metadata (KB video)`.

---

## Task 3: Repository populates the three fields (backend)

**Files:** Modify `src/sage_poc/knowledge/postgres_repository.py:115-126`; Test `tests/test_knowledge_source_cards.py`.

**Interfaces:** Consumes Task 1's `KnowledgePassage`. Produces module-level `_row_to_passage(row) -> KnowledgePassage`.

- [ ] **Step 1: Write the failing test**

```python
def test_row_to_passage_reads_url_title_video_from_metadata():
    from sage_poc.knowledge.postgres_repository import _row_to_passage
    row = {"chunk_text": "x", "article_id": "anx-001-en-000", "rrf_score": 0.0123,
           "citation_metadata": '{"title": "Understanding Anxiety", "source_url": "https://kb/a", '
                                '"citation": "Anxiety 101", "video_url": "https://youtu.be/xyz"}'}
    p = _row_to_passage(row)
    assert p.title == "Understanding Anxiety" and p.source_url == "https://kb/a"
    assert p.video_url == "https://youtu.be/xyz" and p.citation == "Anxiety 101"

def test_row_to_passage_defaults_missing_metadata_fields():
    from sage_poc.knowledge.postgres_repository import _row_to_passage
    p = _row_to_passage({"chunk_text": "x", "article_id": "a-en", "rrf_score": 0.5, "citation_metadata": "{}"})
    assert p.title == "" and p.source_url == "" and p.video_url == "" and p.citation == "a-en"
```

- [ ] **Step 2: Run to verify it fails** — `uv run pytest tests/test_knowledge_source_cards.py -k row_to_passage -q` → FAIL (`ImportError`).

- [ ] **Step 3: Extract + populate** — add module-level:

```python
def _row_to_passage(row) -> KnowledgePassage:
    raw_meta = row["citation_metadata"] or {}
    meta = json.loads(raw_meta) if isinstance(raw_meta, str) else raw_meta
    return KnowledgePassage(
        text=row["chunk_text"], source_id=row["article_id"],
        citation=meta.get("citation", row["article_id"]),
        relevance_score=round(float(row["rrf_score"]), 4),
        source_url=meta.get("source_url", ""), title=meta.get("title", ""),
        video_url=meta.get("video_url", ""),
    )
```
Replace the inline construction at :115-126 with `passages.append(_row_to_passage(row))` (keeping the `_passes_abstain` guard).

- [ ] **Step 4: Run to verify pass** — `uv run pytest tests/test_knowledge_source_cards.py tests/test_knowledge_repository.py -q` → PASS.
- [ ] **Step 5: Commit** — `feat(knowledge): populate passage url/title/video from citation_metadata`.

---

## Task 4: `_sources_header` — allowlist, ensure_ascii, dedupe+cap, typed entries (backend)

**Files:** Modify `src/sage_poc/server.py` (module-level helper + headers dict ~:453-476), `src/sage_poc/state.py` (doc-comment); Test `tests/test_knowledge_source_cards.py`.

**Interfaces:** Produces `_sources_header(result: dict) -> str | None`. Header `X-Sage-Sources` = JSON `[{type: "article"|"video", title, url, citation}]`, ascii-escaped; present only when `gate_path` ∈ allowlist AND ≥1 usable source.

- [ ] **Step 1: Write the failing tests** (allowlist fail-safe + bilingual + dedupe/cap + audit subset)

```python
import json
from sage_poc.server import _sources_header

def _p(**kw):  # passage dict helper
    base = {"text": "t", "source_id": "a-en-000", "citation": "c", "source_url": "https://kb/a",
            "title": "T", "video_url": "", "relevance_score": 0.5}
    return {**base, **kw}

def test_allowlist_suppresses_crisis_medical_and_unknown():
    # ALLOWLIST: only ordinary content paths emit. Future safety routes + unknown values fail SAFE.
    for gp in ("crisis", "medical", "hr", "ipv", "jailbreak", "scope_refusal", "future_route", None):
        assert _sources_header({"gate_path": gp, "knowledge_passages": [_p()]}) is None

def test_allowlist_emits_on_standard():
    hdr = _sources_header({"gate_path": "standard", "knowledge_passages": [_p()]})
    assert json.loads(hdr) == [{"type": "article", "title": "T", "url": "https://kb/a", "citation": "c"}]

def test_video_entry_type_and_url():
    hdr = _sources_header({"gate_path": "standard", "knowledge_passages": [
        _p(video_url="https://www.youtube.com/watch?v=abc")]})
    assert json.loads(hdr)[0] == {"type": "video", "title": "T",
                                  "url": "https://www.youtube.com/watch?v=abc", "citation": "c"}

def test_arabic_title_is_header_safe_and_roundtrips():
    hdr = _sources_header({"gate_path": "standard", "knowledge_passages": [_p(title="القلق")]})
    assert hdr.isascii()                      # HTTP-header-safe (ensure_ascii=True)
    assert json.loads(hdr)[0]["title"] == "القلق"   # round-trips

def test_dedupe_by_source_url_and_cap_at_three():
    passages = [_p(source_url="https://kb/a", source_id=f"a-en-{i:03d}") for i in range(3)]  # same article, 3 chunks
    passages += [_p(source_url=f"https://kb/{x}") for x in ("b", "c", "d", "e")]
    entries = json.loads(_sources_header({"gate_path": "standard", "knowledge_passages": passages}))
    urls = [e["url"] for e in entries]
    assert urls.count("https://kb/a") == 1     # deduped
    assert len(entries) == 3                   # capped

def test_no_header_when_no_usable_source():
    assert _sources_header({"gate_path": "standard", "knowledge_passages": [_p(source_url="", video_url="", title="")]}) is None
    assert _sources_header({"gate_path": "standard", "knowledge_passages": []}) is None
```

- [ ] **Step 2: Run to verify they fail** — `uv run pytest tests/test_knowledge_source_cards.py -k "allowlist or arabic or dedupe or video_entry or usable_source" -q` → FAIL (`ImportError`).

- [ ] **Step 3: Implement**

```python
# ordinary content paths only. Any safety route (crisis now; medical/hr/ipv/future) or unknown
# value fails SAFE (no sources). VERIFY a KB info_request turn carries gate_path == "standard"
# (Step 3a below); if it is None, add None here explicitly — do not widen to a denylist.
_SOURCE_ALLOWED_GATE_PATHS = frozenset({"standard"})

def _sources_header(result: dict) -> str | None:
    # Sources are a SUBSET of result["knowledge_passages"] — the exact list audited in
    # session_audit.knowledge_passage_ids — so every shown source is audit-traceable.
    if result.get("gate_path") not in _SOURCE_ALLOWED_GATE_PATHS:
        return None
    entries: list[dict] = []
    seen: set[str] = set()
    for p in (result.get("knowledge_passages") or []):
        video, url = p.get("video_url", ""), p.get("source_url", "")
        if not (video or url):
            continue
        key = url or video                          # dedupe by article-level URL
        if key in seen:
            continue
        seen.add(key)
        entries.append({"type": "video" if video else "article", "title": p.get("title", ""),
                        "url": video or url, "citation": p.get("citation", "")})
        if len(entries) >= 3:                        # cap = L4 max_passages evidence budget
            break
    return json.dumps(entries, ensure_ascii=True) if entries else None
```
In the `StreamingResponse` construction, compute `_sources = _sources_header(result)` and merge `**({"X-Sage-Sources": _sources} if _sources else {})` into the `headers` dict. Update `state.py`'s `knowledge_passages` comment to list `source_url, title, video_url`.

- [ ] **Step 3a: Confirm the ordinary `gate_path`** — drive one KB `info_request` turn on staging and read `X-Sage-Gate-Path`; confirm it is `"standard"`. If `None`, add `None` to `_SOURCE_ALLOWED_GATE_PATHS` and to `test_allowlist_emits_on_standard`.

- [ ] **Step 4: Run to verify pass** — `uv run pytest tests/test_knowledge_source_cards.py -q` → PASS.
- [ ] **Step 5: Commit** — `feat(api): X-Sage-Sources header (allowlist, ascii, dedupe+cap, typed article/video)`. **→ Backend PR opens here.**

---

## Task 5: Frontend types + header parse (`cdai`)

**Files:** Modify `packages/types/src/index.ts`, `apps/web/app/api/chat/route.ts` (mirror `crisisFlags` at :139, message assembly :219-223, expose-headers :269); Test `apps/web/app/api/chat/__tests__/route.test.ts`.

**Interfaces:** `Source = { type: 'article' | 'video'; title: string; url: string; citation: string }`; `sources?: Source[]` on the AI message type. (Header is already camelCase-friendly: `{type, title, url, citation}` — no snake_case remap needed.)

- [ ] **Step 1: Write the failing test**

```ts
it('threads X-Sage-Sources onto the message', async () => {
  const sources = [{ type: 'video', title: 'القلق', url: 'https://youtu.be/x', citation: 'c' }]
  const res = mockSageResponse({ headers: { 'X-Sage-Sources': JSON.stringify(sources) } })
  const msg = await buildAiMessageFromSageResponse(res)   // verify real helper name in route.ts
  expect(msg.sources).toEqual(sources)
})
```

- [ ] **Step 2: Run to verify it fails** — `cd /Users/knowledgebase/Documents/Sage/cdai-lane2-wt/apps/web && npm test -- route.test` → FAIL (`msg.sources` undefined).

- [ ] **Step 3: Implement** — add `Source` interface + `sources?: Source[]` in `packages/types`; in `route.ts`:
```ts
const sources = parseJsonHeader<Source[]>(sageRes.headers.get('X-Sage-Sources'), null)
// ...thread `sources,` into the message object near node_path/crisis_flags (:219-223)
```
Add `'x-sage-sources'` to the exposed-headers list (~:269).

- [ ] **Step 4: Run to verify pass** — same command → PASS.
- [ ] **Step 5: Commit** — `feat(chat): parse X-Sage-Sources into message.sources`.

---

## Task 6: `SourceCard` + `VideoEmbed` render (`cdai`)

**Files:** Create `apps/web/components/chat/SourceCard.tsx`, `apps/web/components/chat/VideoEmbed.tsx`; Modify `apps/web/components/chat/message-bubble.tsx`; Test `apps/web/components/chat/__tests__/message-bubble.test.tsx`.

**Interfaces:** Consumes `message.sources?: Source[]`, `message.direction?: 'ltr'|'rtl'`.

- [ ] **Step 1: Write the failing tests** (article link, video iframe host, RTL, absent)

```tsx
it('renders an article link', () => {
  render(<MessageBubble message={{ role: 'ai', content: 'x',
    sources: [{ type: 'article', title: 'Understanding Anxiety', url: 'https://kb/a', citation: 'c' }] }} />)
  expect(screen.getByRole('link', { name: /Understanding Anxiety/ })).toHaveAttribute('href', 'https://kb/a')
})
it('embeds YouTube via youtube-nocookie', () => {
  render(<MessageBubble message={{ role: 'ai', content: 'x',
    sources: [{ type: 'video', title: 'V', url: 'https://www.youtube.com/watch?v=abc123', citation: 'c' }] }} />)
  expect(screen.getByTitle('V').getAttribute('src')).toContain('youtube-nocookie.com/embed/abc123')
})
it('renders the Arabic card RTL', () => {
  render(<MessageBubble message={{ role: 'ai', content: 'x', direction: 'rtl',
    sources: [{ type: 'article', title: 'القلق', url: 'https://kb/a', citation: 'c' }] }} />)
  expect(screen.getByLabelText('Sources')).toHaveAttribute('dir', 'rtl')
})
it('renders no card when sources absent', () => {
  render(<MessageBubble message={{ role: 'ai', content: 'x' }} />)
  expect(screen.queryByLabelText('Sources')).toBeNull()
})
```

- [ ] **Step 2: Run to verify they fail** — `cd /Users/knowledgebase/Documents/Sage/cdai-lane2-wt/apps/web && npm test -- message-bubble` → FAIL.

- [ ] **Step 3: Implement** — `VideoEmbed.tsx` detects provider from the canonical URL (provider-agnostic; swap-friendly):
```tsx
function youtubeId(url: string): string | null {
  const m = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([\w-]{11})/)
  return m ? m[1] : null
}
export function VideoEmbed({ url, title }: { url: string; title: string }) {
  const yt = youtubeId(url)
  if (yt) return <iframe title={title} src={`https://www.youtube-nocookie.com/embed/${yt}`}
    allow="encrypted-media" referrerPolicy="strict-origin-when-cross-origin" loading="lazy" />
  return <video controls src={url} aria-label={title} />   // self-hosted / other providers: data swap, one branch
}
```
`SourceCard.tsx` type-switches per entry (`article` → `next/link`, `video` → `<VideoEmbed>`); wrapper `<aside aria-label="Sources" dir={direction}>`. Render in `message-bubble.tsx` for AI messages when `message.sources?.length`.

- [ ] **Step 4: Run to verify pass** — same command → PASS.
- [ ] **Step 5: Commit** — `feat(chat): render Sources card + provider-agnostic VideoEmbed (youtube-nocookie)`.

---

## Task 7: Sample data + end-to-end verification (staging)

- [ ] **Step 1: Populate `video_url` on 1-2 sample KB articles** (content JSON only, re-ingest via existing sync) so a `video` source appears on a real "Ask" turn. No skill JSON touched.
- [ ] **Step 2: Deploy backend + frontend to staging.**
- [ ] **Step 3: Playwright — KB article turn:** ask a KB question → **article Sources card with a clickable link**.
- [ ] **Step 4: Playwright — KB video turn:** ask about the sampled article → **`youtube-nocookie` iframe embeds** in the card.
- [ ] **Step 5: Playwright — crisis turn:** send a crisis message → **no Sources card / no video** (allowlist suppression).
- [ ] **Step 6: Playwright — Arabic turn:** an Arabic KB turn → card renders **RTL**, title legible.
- [ ] **Step 7: Regression** — a normal non-KB message → no card, unchanged.

---

## Self-Review
- **Feedback coverage:** (1) allowlist + `test_allowlist_suppresses_crisis_medical_and_unknown` ✅; (2) `ensure_ascii=True` + `test_arabic_title_is_header_safe_and_roundtrips` + RTL test (T6) ✅; (3) dedupe-by-`source_url` + cap-3 + `test_dedupe_by_source_url_and_cap_at_three` ✅; (4) audit-subset invariant comment (T4) ✅. Video: typed list, `video_url` in `citation_metadata` (T2), provider-agnostic field + `youtube-nocookie` + HTML5 fallback (T6), crisis auto-suppressed + T7 video staging check ✅; no `SkillStep.media`, Item 3 untriggered ✅.
- **Placeholders:** every code step shows real code. The one lookup: the real helper name in `route.ts` (Task 5) — the implementer confirms it.
- **Type consistency:** header + `Source` type are both `{type, title, url, citation}` (no snake_case remap); `video_url` (backend) → `url` with `type:"video"` (header) → `VideoEmbed({url})` (frontend), consistent end to end. `_SOURCE_ALLOWED_GATE_PATHS` used only in `_sources_header`.

---

## Deferred to separate plans (Lane 2 items 2 & 3)
- **Item 2 — Structured-affordance contract.** Design spec first (typed `X-Sage-Affordances` envelope + one renderer); absorbs the content-inventory §4 deferrals (three-button check-in, topic menus) and later migrates `source_card`/`video` onto the general envelope. → brainstorm → spec → its own plan.
- **Item 3 — `SkillStep.media`.** Schema delta → Absolute Rule 1 approval entry + Item 2 contract; **skill-step** video (distinct from KB-article video shipped here). Post-POC content.
- **Before-external-exposure checklist (tracked):** **self-hosted video replacement** — at external exposure, sovereignty + content-governance (where videos are hosted, who approved them) become real; the provider-agnostic `video_url` is exactly what makes that transition a data swap + one renderer branch. Also on this checklist: GL-1 helpline dial-test, GL-0 crisis recall.

---

## Execution Handoff
Plan complete and saved to `docs/superpowers/plans/2026-07-06-lane2-source-cards.md`. Two execution options:
1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks.
2. **Inline Execution** — tasks in this session with checkpoints.
