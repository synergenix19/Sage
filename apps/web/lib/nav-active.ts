// apps/web/lib/nav-active.ts
//
// Shared "is this nav item active for the current route" predicate + the
// active/inactive class-picker built on top of it (Task 6b).
//
// tab-bar.tsx and app-side-nav.tsx each used `pathname.startsWith(href)`,
// which over-matches any route that merely shares href as a PREFIX — e.g.
// a `/chatbot` route would show the `/chat` tab as active. staff-nav.tsx
// already had the correct boundary-safe form (exact match, or a `/`-bounded
// child route); that form is unified here as the one implementation every
// nav component imports.
export function isActiveHref(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(href + '/')
}

// Picks between an active and inactive className given the isActiveHref
// result. Each nav component still owns its own visual classes (tab-bar,
// app-side-nav, and staff-nav each render a distinct active style) — this
// just removes the repeated `active ? x : y` ternary shape at every call
// site down to one function.
export function navItemClass(active: boolean, activeClass: string, inactiveClass: string): string {
  return active ? activeClass : inactiveClass
}
