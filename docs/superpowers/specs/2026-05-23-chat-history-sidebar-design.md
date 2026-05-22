# Chat History Sidebar Design

**Date:** 2026-05-23
**Status:** Approved
**Prereq:** Responsive app shell (2026-05-22) must be merged first — this extends `AppSideNav`.

---

## Goal

Replace the 500px of empty vertical space in the desktop sidebar with a conversation history list and a prominent "+ New conversation" button, following the ChatGPT/Claude navigation pattern. Mobile UX is unchanged except for the addition of a compose icon in `ChatHeader`.

---

## Sidebar Structure (desktop, `md+`)

```
┌──────────────────────────────────┐
│  Sage by CDA                     │  ← brand (unchanged)
├──────────────────────────────────┤
│  [+ New conversation           ] │  ← full-width button, primary-styled
├──────────────────────────────────┤
│  Feeling stressed lately   2h ago│
│  Anxiety about work     Yesterday│  ← scrollable conversation list (flex-1)
│  Untitled conversation    May 19 │    max 20 sessions, overflow-y-auto
│  ...                             │    active session: surface-tinted bg
├──────────────────────────────────┤
│  Chat                            │
│  Progress                        │  ← nav section (bottom, not top)
│  Voice (if enabled)              │
├──────────────────────────────────┤
│  [Language toggle]               │
│  [Avatar] email@...  [sign-out]  │
└──────────────────────────────────┘
```

Key decisions:
- `Chat` nav link is **kept** alongside Progress/Voice. The conversation list is for switching history; the nav link is the "go to chat" section affordance. They serve different mental models.
- `+ New conversation` is a full-width prominent button — its own row, not compressed into the brand header row.
- The conversation list occupies `flex-1` with `overflow-y-auto`. Nav section and footer are always visible.

---

## Mobile (below `md`)

No structural changes to the sidebar (it is hidden below `md`). Two additions to `ChatHeader`:

1. **Compose icon** (pencil/edit) — new, visible only on mobile (`md:hidden`). Navigates to `/chat?new=<timestamp>-<random>`. Positioned to the left of the clock icon (LTR) / right of the clock icon (RTL).
2. **Clock icon** — unchanged. Opens `HistoryPanel` sheet as before.

Desktop `ChatHeader` simplifies to: conversation title — language toggle — settings gear. Clock icon is `hidden md:hidden` (not shown on desktop).

---

## Component Architecture

### New file: `lib/hooks/use-chat-sessions.ts`

Shared data hook. Extracted from `HistoryPanel` fetch logic.

```ts
interface ChatSession {
  id: string
  title: string | null
  updated_at: string
}

function useChatSessions(): {
  sessions: ChatSession[]
  loading: boolean
  error: string | null
  refresh: () => void
}
```

Supabase query:
```sql
SELECT id, title, updated_at
FROM chat_sessions
WHERE user_id = <current_user>
ORDER BY updated_at DESC
LIMIT 20
```

The hook exposes `refresh()` so callers can re-fetch after creating a new session — e.g., after the user sends the first message in a new conversation, the sidebar updates to show the session at the top without a page reload.

### Modified: `components/app-side-nav.tsx`

- Consumes `useChatSessions()`
- Renders `+ New conversation` button below brand
- Renders scrollable conversation list in `flex-1` zone
- Moves nav links (`ALL_TABS`) from the top nav block to a bottom nav section above the footer
- Active session detected via `useSearchParams()` reading `?session=<id>`

### Modified: `components/chat/history-panel.tsx`

- Refactors inline fetch to use `useChatSessions()` hook
- Removes duplicated Supabase call and state management
- UI and behaviour otherwise unchanged (mobile-only sheet)

### Modified: `components/chat/chat-header.tsx`

- Removes clock icon on desktop (`hidden md:block` → removed entirely from desktop render path)
- Adds compose icon button (`md:hidden`) for new conversation
- Compose icon routes to `/chat?new=<timestamp>-<random>` (same format as HistoryPanel)

---

## Conversation List Item

Each item is a single row:

```
[● active indicator]  [Title truncated, flex-1]   [2h ago, text-xs muted]
```

- Min height: `44px` (WCAG touch target)
- Title: `truncate` single line, `text-sm`, primary text color
- Timestamp: `text-xs`, `--color-text-secondary`, formatted with `formatRelativeTime()` utility
- Active state: `bg-[var(--color-surface-tinted)]` — NOT primary green (reserved for nav links)
- `aria-current="page"` on the active session item
- Focus: `focus-visible:ring-2 focus-visible:ring-[var(--focus-ring-color)]`

### Relative timestamp formatting

```ts
function formatRelativeTime(updatedAt: string): string
```

Rules (simple, no library):
- `< 1h` → `Xm ago`
- `1h–23h` → `Xh ago`
- `yesterday` → `Yesterday`
- `this week` → day name (e.g., `Monday`)
- `older` → `MMM D` (e.g., `May 19`)

---

## RTL

- All layout uses CSS logical properties (`ps-`, `pe-`, `border-s`, `border-e`) — inherited from existing `AppSideNav` conventions
- Compose icon in `ChatHeader`: positioned with logical margin (`me-`) so it sits correctly in both LTR and RTL
- Timestamp on list items: `text-end` in LTR, `text-start` in RTL — handled automatically by `dir` on `<html>`

---

## Accessibility

- `+ New conversation` button: `aria-label` in both locales
- Compose icon in `ChatHeader`: `aria-label` (`locale === 'ar' ? 'محادثة جديدة' : 'New conversation'`)
- Conversation list: rendered as `<ul>` with `<li>` wrappers; each item is a Next.js `<Link href={/chat?session=${id}}>` (renders as `<a>`). This gives correct semantic markup (`role="link"`), right-click → open in new tab, browser history entries, and screen reader link navigation. Client-side navigation is handled natively by Next.js App Router — no `router.push` needed.
- Loading state: list zone shows a muted "Loading..." or skeleton while `loading === true`
- Error state: compact retry button (reuses `HistoryPanel` error pattern)

---

## Out of Scope

- **Conversation titling**: all sessions display their stored `title` (currently `null` → "Untitled conversation"). A separate sprint will generate titles from first-message content. The timestamp differentiator covers usability until that ships.
- **Real-time session list**: `refresh()` is called on component mount and after new-chat navigation. No Supabase Realtime subscription.
- **Sidebar collapse/hamburger**: not planned pre-Gitex. If added later, the clock icon returns to `ChatHeader` at that point.
- **Pagination**: sidebar is capped at 20. HistoryPanel handles the full list independently (it already fetches 20 — if pagination is needed there, it's a separate ticket).

---

## Success Criteria

- [ ] `+ New conversation` button visible in sidebar on desktop; one click creates a new session
- [ ] Conversation list shows up to 20 sessions, ordered newest-first, with relative timestamps
- [ ] Active session highlighted in list
- [ ] Clicking a session navigates to `/chat?session=<id>` without page reload
- [ ] Clock icon absent from desktop `ChatHeader`; compose icon visible on mobile
- [ ] RTL layout correct (sidebar on right, logical-property icons, Arabic labels)
- [ ] All existing tests pass; new unit tests cover hook, list item, and compose icon
