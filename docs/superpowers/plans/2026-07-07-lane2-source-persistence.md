# Lane 2 Item 1.5 — Source-Card Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development to execute task-by-task. Steps use `- [ ]` checkboxes.

**Goal:** Persist the source card so a **reopened** conversation shows the same card the live turn showed. Today sources ride the `X-Sage-Sources` response header only (live-turn) and are dropped on reload.

**Architecture:** Additive nullable `sources jsonb` column on `messages`; write the **already-parsed, deduped, capped, typed** list onto the AI row in the existing `after()` persist block; hydrate it back into `initialMessages` on conversation load and carry it onto the rendered `ChatMessage`, rendering through the **same** `source-card`/`video-embed` components. Frontend-only (cdai); no sage-poc / safety-path touch. Repo `cdai`, branch `cdai/feat/lane2-source-persistence` off `main`, worktree `/Users/knowledgebase/Documents/Sage/cdai-persist-wt` (npm).

## Global Constraints (the three signed requirements)
- **(a) Stored == rendered.** Persist EXACTLY what the header carried — the deduped/capped/typed `[{type,title,url,citation}]` list (`sourcesHeader`), NOT the raw passage set. The stored artifact must equal the rendered artifact.
- **(b) Safety invariant (by construction + tested).** Crisis turns never emit `X-Sage-Sources` (allowlist suppression is upstream in sage-poc), so a persisted crisis-turn row can never carry sources. Persist defensively as `isCrisis ? null : parsedSources` (belt-and-braces), and ADD A TEST asserting a crisis-turn AI row persists `sources = null`.
- **(c) Malformed-data safety.** Hydration renders through the same `source-card`/`video-embed` with the same guard: stored jsonb of an unexpected shape (older schema version, hand-edited row) must degrade to **no card**, never a crashed bubble. Guard = the hydrate mapping only passes `sources` through when it is a non-empty array; anything else → `undefined`.
- Byte-identical when null; additive migration; commit trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`; `git add` only changed files (never `-A`). npm test: `cd apps/web && npm test -- <pattern>`.

---

## Task 1: Migration — `sources jsonb` on `messages`
**Files:** Create `supabase/migrations/016_add_sources_to_messages.sql`.
- [ ] **Step 1: Write the migration**
```sql
-- Lane 2 Item 1.5: persist the rendered source-card list per AI message.
-- Additive, nullable — existing rows get NULL (no card on reopen, as before this feature).
-- Holds the deduped/capped/typed [{type,title,url,citation}] list the X-Sage-Sources header carried.
ALTER TABLE messages ADD COLUMN IF NOT EXISTS sources jsonb;
```
- [ ] **Step 2: Apply to the DB** (zero-user mode → prod Supabase, same as the seeding): `railway run bash -lc 'psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f supabase/migrations/016_add_sources_to_messages.sql'` (verify: column present in `information_schema.columns`).
- [ ] **Step 3: Commit** `feat(db): migration 016 — sources jsonb on messages (source-card persistence)`.

---

## Task 2: Persist sources on the AI row (`route.ts`)
**Files:** Modify `apps/web/app/api/chat/route.ts` (parse near the `sourcesHeader` capture ~:146; add the field in the AI insert row ~:220-247). Test `apps/web/app/api/chat/__tests__/route.test.ts`.
**Interfaces:** Consumes `sourcesHeader` (raw string, already forwarded). Produces `messages.sources` (jsonb) on the AI row.
- [ ] **Step 1: Write the failing tests**
```ts
it('persists the parsed sources list on the AI message row', async () => {
  const sources = [{ type: 'article', title: 'What is anxiety?', url: 'https://kb/a', citation: 'c' }]
  const res = mockSageResponse({ headers: { 'X-Sage-Sources': JSON.stringify(sources) } })
  const insert = captureMessagesInsert(res)   // the array passed to .from('messages').insert([...])
  const aiRow = insert.find(r => r.role === 'ai')
  expect(aiRow.sources).toEqual(sources)
})
it('persists sources = null on a crisis-turn row (safety invariant)', async () => {
  // crisis turn: backend emits NO X-Sage-Sources (allowlist suppression upstream)
  const res = mockSageResponse({ crisis: true, headers: {} })
  const insert = captureMessagesInsert(res)
  const crisisRow = insert.find(r => r.role === 'crisis')
  expect(crisisRow.sources).toBeNull()
})
```
- [ ] **Step 2: Run → FAIL** (`aiRow.sources` undefined). `cd apps/web && npm test -- route.test`.
- [ ] **Step 3: Implement** — near `sourcesHeader` capture (~:146):
```ts
let parsedSources: unknown = null
if (sourcesHeader) { try { parsedSources = JSON.parse(sourcesHeader) } catch { parsedSources = null } }
```
In the AI insert row object (~:220), add (belt-and-braces null on crisis, though the header is already absent there):
```ts
          sources:                         isCrisis ? null : parsedSources,
```
- [ ] **Step 4: Run → PASS.** `npm test -- route.test`.
- [ ] **Step 5: Commit** `feat(chat): persist X-Sage-Sources on the AI message row (crisis→null)`.

---

## Task 3: Hydrate sources on conversation load (`page.tsx` + `chat-interface.tsx`)
**Files:** Modify `apps/web/app/(app)/chat/page.tsx` (select ~:63, `InitialMessage` type ~:8, map ~:70), `apps/web/components/chat/chat-interface.tsx` (initialMessages→ChatMessage mapping). Tests `apps/web/components/chat/__tests__/*` + a page-map unit if present.
**Interfaces:** Consumes `messages.sources` (jsonb). Produces `InitialMessage.sources?: Source[]` → `ChatMessage.sources`.
- [ ] **Step 1: Write the failing tests**
```tsx
it('hydrates a valid stored sources array onto the message', () => {
  const src = [{ type: 'article', title: 'T', url: 'https://kb/a', citation: 'c' }]
  expect(hydrateSources(src)).toEqual(src)         // helper under test (see Step 3)
})
it('degrades malformed stored sources to undefined (no card, no crash)', () => {
  expect(hydrateSources({ not: 'an array' })).toBeUndefined()
  expect(hydrateSources(null)).toBeUndefined()
  expect(hydrateSources([])).toBeUndefined()
})
```
- [ ] **Step 2: Run → FAIL** (`hydrateSources` undefined). `npm test -- chat-interface` (or the file you place the helper's test in).
- [ ] **Step 3: Implement**
  - Add the guard helper (requirement c), e.g. in `chat-interface.tsx` or a small `lib/sources.ts`:
```ts
export function hydrateSources(raw: unknown): Source[] | undefined {
  return Array.isArray(raw) && raw.length > 0 ? (raw as Source[]) : undefined
}
```
  - `page.tsx`: extend the select to `'id, role, content, sources'`; add `sources?: Source[]` to `interface InitialMessage`; in the `.map`, add `sources: hydrateSources(row.sources)`.
  - `chat-interface.tsx`: where it builds its `ChatMessage[]` from `initialMessages`, carry `sources: m.sources` onto each assistant message (read the existing mapping and add the field, mirroring how `id/role/content` are carried).
- [ ] **Step 4: Run → PASS**, plus the full suite `cd apps/web && npm test` (no regressions).
- [ ] **Step 5: Commit** `feat(chat): hydrate persisted sources onto reopened conversations (malformed→no card)`.

---

## Task 4: End-to-end verification (prod, zero-user mode)
- [ ] Deploy: `vercel deploy --prod --yes` from the worktree (`.vercel` link copied in).
- [ ] Playwright on chat.biosight.ai: send a KB turn ("what is anxiety") → card renders; **reload / reopen the conversation from the sidebar → the SAME card (video + article) is still there.**
- [ ] Reopen an OLDER conversation (pre-persistence, sources NULL) → no card, no crash (byte-identical).
- [ ] Reopen a crisis conversation → no card (sources null by construction).

---

## Self-Review
Requirement (a): stored = `sourcesHeader` parsed (the rendered list), not raw passages — Task 2. (b): `isCrisis ? null` + explicit crisis-null test — Task 2. (c): `hydrateSources` array-guard + malformed test + renders through the same source-card — Task 3. Additive/nullable migration; frontend-only; no safety-path touch. Types: `Source` reused end-to-end (header → persist → hydrate → render), no snake/camel remap (header already `{type,title,url,citation}`).

## Execution Handoff
Subagent-driven (recommended): fresh subagent per task, review between; final whole-branch review; then merge #→main + deploy + E2E.
