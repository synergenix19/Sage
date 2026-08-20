// ─── newChatHref (P4 Task 4) ─────────────────────────────────────────────────
// The "/chat?new=<ts>-<rand>" recipe was copied verbatim at three call sites
// (app-side-nav.tsx, history-panel.tsx, chat-header.tsx). Consolidated here so
// the id-generation scheme has exactly one definition. Behavior-preserving:
// same format, same entropy source, same route.
export function newChatHref(): string {
  return `/chat?new=${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}
