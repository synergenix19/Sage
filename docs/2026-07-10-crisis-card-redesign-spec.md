# Crisis Card Redesign — Spec (Abby-informed, multi-resource, hours-aware)

**Date:** 2026-07-10 · **Status:** design spec for review · **Owner surfaces:** frontend `cdai/apps/web` + backend `sage-poc` (H4). Benchmark: Abby (chat.abby.gg), captured `memory/assets/abby-crisis-*-2026-07-10.png`.

## Goal
Evolve the current crisis card (2 hardcoded buttons: MoHAP + 999) into a **prominent, always-reachable, multi-resource, hours-aware, bilingual** crisis affordance fed by the H4 `CRISIS_RESOURCES` + `select_crisis_resources` lead-logic. **Not greyed, not hidden behind a modal** — the opposite of de-emphasis.

## Benchmark delta (vs Abby)
**Take from Abby:** categorized multi-resource list; per-resource **Call/Text** action buttons; **hours + "confidential"** tags; a **persistent "get help" affordance** available every turn (their Crisis nav), not only on detection; conversation stays open (no hard stop).
**Beat Abby on:** (1) don't bury resources one-tap-behind-a-modal for a higher-acuity crisis context — keep **pinned-until-resolved** (safer, can't scroll away), restyled lighter/warmer; (2) **bilingual AR/EN + RTL**; (3) **hours-aware lead-logic** — 24/7 lines lead at night, National (8am–8pm) leads by day (Abby has zero hours-awareness); (4) never greyed.

## Design

### Data (source of truth = backend)
- Backend `select_crisis_resources(immediate_danger, now)` already returns the **ordered** resource list (lead-logic + always-pair-24/7). **The server computes ordering** (it holds the tier/`immediate_danger` signal and the authoritative clock) and sends the frontend an ordered array — via the `/chat` response (body field or a header alongside `X-Sage-Crisis-State`). Single source of truth; no client-side clock drift.
- `crisis-config.ts` reshapes: single object → **array** of `{ labelEn, labelAr, number, tel, hours, scope }`, kept as the **static fallback** (mirrors backend `CRISIS_RESOURCES`; cross-stack test enforces parity). When the server sends the ordered list, use it; else fall back to the static array with client-side lead-logic.

### Card (`crisis-card.tsx`)
- Renders an **ordered list** (`.map`) instead of 2 fixed buttons. Each row: label (localized) + **hours chip** + **"confidential" chip** (where applicable) + a **`tel:` Call button** (44px, crisis-colored). Emergency (999) always present.
- Keep: `role="alert"` `aria-atomic`, bilingual heading, `dir="auto"` body, Latin numbers wrapped `dir="ltr"` inside AR, pinned-until-`resolved` (backend `X-Sage-Crisis-State`).
- Restyle lighter/warmer so "prominent" ≠ "alarming" (Abby's tone) — but still high-contrast crisis color on the actions.
- Show at most ~3 leading resources inline + a "more options" expander (avoid a wall), lead-logic decides the top 3.

### Persistent affordance (new — biggest gap vs Abby)
- Add an always-available **"Get help now"** entry point in the chat header/nav — reachable **every turn**, not only on crisis detection. Opens the same resource list. This is Abby's Crisis nav item; we don't have it.

### Behavior
- Conversation stays open (we already do — monitoring state). No hard stop.
- On detection: pinned card + the resource list. Off detection: the persistent "Get help now" affordance.

## Non-goals / phasing
- **Phase 1 (this spec):** multi-resource card + persistent affordance, fed by the static array (backend value change is H4, gated on verify/deploy). Ships the *structure*.
- **Phase 2:** server-sends-ordered-list (hours-aware at runtime). Requires the `/chat` contract addition.
- Out of scope: changing detection (server-side, unchanged); the H4 value ruling (separate).

## Testing
- **Cross-stack parity:** frontend array === backend `CRISIS_RESOURCES` (extend existing cross-stack test to the array shape).
- **a11y:** role=alert, 44px targets, `tel:` hrefs, bilingual aria-labels — extend `crisis-card.test.tsx`.
- **Hours-aware:** unit — night → a 24/7 line leads; day → National leads (mirror backend `select_crisis_resources` tests).
- **Bilingual/RTL:** AR locale renders localized labels, LTR-wrapped numbers.
- **Playwright E2E:** crisis message → card shows the ordered list with working `tel:` links; "Get help now" reachable off-detection.

## Dependencies
- Backend H4: `CRISIS_RESOURCES` + `select_crisis_resources` (structure **built**, PR #288; values gated on GL-1 reversal + verify + deploy).
- Frontend `crisis-config.ts` value must mirror the backend value when H4 deploys (both change together).

## Open questions (for PO/clinical)
1. Inline count — show top 3 + expander, or all? (I recommend 3 + expander.)
2. Persistent "Get help now" wording/placement (header vs nav) — bilingual copy needs a quick clinical tick.
3. "Confidential" tag — confirm it applies to the UAE lines as it does to Abby's US lines.
