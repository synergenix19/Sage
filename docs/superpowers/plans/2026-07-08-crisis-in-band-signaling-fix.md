# Crisis In-Band Signaling — Eliminate the Sentinel-Leak Class (issue #191)

> **For agentic workers:** crisis-path change → clinical/PO sign-off REQUIRED before merge. TDD. Verify in a real browser (EN + AR). Do NOT touch the helpline number/copy here (that is the separate GL-1 escalation). Run `next build` before any deploy.

**Execution sequence (PO-directed 2026-07-08):** Task 2 (invariant) → Tasks 3–4 (reload `isCrisis` + latest-pin) → Task 1 (root-cause confirmation) → Task 5 (browser verify EN+AR) → persist-side pin → assemble sign-off packet → merge.

## Root cause: IN-BAND SIGNALING (the disease; the sentinel leak is the symptom)

Crisis state travels as a **magic-string prefix (`[[CRISIS_DETECTED]]`) inside the message content**. Every render/parse/persist path must then *independently remember* to strip it and re-derive "this is a crisis." That contract has now produced exactly the failure class it was always going to produce: a path that didn't strip/derive rendered the raw sentinel as plain text and dropped the pinned helpline card (observed 2026-07-08 in a history-loaded conversation, prod).

**The real elimination is out-of-band signaling.** Phase 0b's **terminal metadata frame** (spec §4.2) carries explicit `render_mode` / crisis fields *beside* the content, not embedded in it — so crisis disposition is read from a typed field, not recovered from a string prefix by each path. **This incident is the strongest argument yet that Phase 0b is a SAFETY improvement, not just a UX/latency heartbeat — it should raise 0b's priority.** Task 2's render invariant below remains as belt-and-suspenders *after* 0b lands (defense in depth is correct on the crisis path).

Cross-ref: [[streaming-design-parked]] (Tier 2 gate), `2026-07-07-presence-indicator-typewriter-spec.md` §4.2 (0b terminal frame), issue #191.

## What's known (investigation to date)
- **DB is clean:** no `messages` row (any role, any age) contains the sentinel; persist strips correctly. This is a client-render bug, not data corruption.
- **Live-stream strip works** (`cdai/apps/web/components/chat/chat-interface.tsx:162-172`).
- **Clean new conversation + two crises → no leak** (verified live).
- **Leak reproduces only in a reloaded, `initialMessages`-history-loaded conversation** + crisis turns. Exact state transition not yet pinned (Task 1).

---

## Task 2 — Render-boundary crisis invariant (PRIMARY safety fix; ships first)

**File:** `cdai/apps/web/components/chat/chat-interface.tsx` (the `messages.map` guard ~L395, and `pinnedCrisis` ~L304-307); possibly `message-bubble.tsx`.

**Invariant:** a message is crisis if `m.isCrisis === true` **OR** `m.content.startsWith(CRISIS_SIGNAL)`. A crisis message must NEVER render as a normal bubble, and crisis content must be sentinel-stripped **everywhere it is read**. This makes the leak structurally impossible regardless of how `isCrisis` got mis-set upstream.

- Map guard: `const isCrisis = m.isCrisis === true || m.content.startsWith(CRISIS_SIGNAL); if (isCrisis) return null`.
- `pinnedCrisis`: strip the sentinel from the chosen crisis content (`content.startsWith(CRISIS_SIGNAL) ? content.slice(CRISIS_SIGNAL.length).trimStart() : content`) so a sentinel-prefixed message still renders a clean card.
- **Tests (TDD):** (a) a message with `isCrisis:false` but sentinel-prefixed content → returns null from the map (never a plain bubble) AND its *stripped* content appears in the pinned card; (b) existing non-crisis rendering unchanged.

## Task 3 — Reload correctness: derive `isCrisis` for history

**File:** wherever `initialMessages` are built (the server/route mapping of Supabase rows → `SdkMessage`; crisis replies persist with `role='crisis'`).

Map `role='crisis'` → `isCrisis: true` (content is already clean in the DB). A reloaded crisis reply then shows the pinned card, not a plain transcript bubble.

- **Hypothesis-driven** — Task 1 confirms this mapping gap is the mechanism.
- **Test:** `initialMessages` containing a `role='crisis'` message → pinned card, not a bubble.

## Task 4 — Multi-crisis pin = LATEST (findLast) — SIGN-OFF PACKET line item

**File:** `chat-interface.tsx` `pinnedCrisis` (~L306): `messages.find(m => m.isCrisis)` → `messages.findLast(m => m.isCrisis)`.

- Consecutive crises pin the **most recent** disclosure's card.
- **This is a crisis-UX behavior change** (which card a user in repeated crisis sees). Latest-pinned is almost certainly clinically right, but the reviewer must tick it **consciously as its own line in the sign-off packet**, not discover it inside a diff.
- **Test:** two crisis messages → pinned content = the second.

## Task 1 — Confirm the exact transition (NOT optional; runs after the fix works)

Reproduce deterministically (history-loaded conversation → crisis turns); log `messages[].{id,role,isCrisis,content.slice(0,20)}` at each `setMessages`/render. Identify the precise render where a crisis message has `isCrisis=false` and/or sentinel content.

**Why it's mandatory even though Task 2 makes the leak impossible:** "the invariant makes it impossible, so skip understanding it" must NOT be the quiet outcome. An unexplained path where `isCrisis` is lost may have **siblings** — does the same history-mapping gap affect anything else derived at load? Explicitly check: **`direction` (RTL), the Supabase message-id (feedback wiring), and `isCrisis`** on `initialMessages`. Task 3 is hypothesis-driven; Task 1 confirms the hypothesis was the *whole* story (or surfaces the siblings).

## Task 5 — Browser verify (EN + AR) on the exact failing scenario

Drive the ORIGINAL failing scenario in prod-equivalent build: **history-loaded conversation → EN crisis → AR crisis → assert zero sentinel-leak nodes, latest card pinned, both replies hidden, `role=alert` present, `tel:` live.** Both languages.

**QA checklist entry (exact, executable — add to `PRESENCE_QA_CHECKLIST.md` with the fix):**
> Crisis multi-turn / reload: open a conversation WITH prior history → send an EN crisis disclosure → send an AR crisis disclosure → confirm (1) NO node contains `[[CRISIS_DETECTED]]`, (2) exactly one pinned red card (`role=alert`) showing the LATEST disclosure's response, (3) both crisis replies hidden from the transcript, (4) helpline `tel:` tap-target live.

## Persist-side pin (turn the DB-clean observation into a test)

Make "the sentinel never reaches storage" a **pinned invariant**, not a point-in-time observation: a unit test on the persist/strip function (or an integration assertion on the persist path in `cdai/apps/web/app/api/chat/route.ts`) that a crisis stream body (`CRISIS_SIGNAL + "\n" + text`) persists with the sentinel stripped. Closes the boundary on the storage side.

---

## Sign-off packet (assemble before merge; reviewer ticks each)
- [ ] Render invariant (Task 2): crisis content never renders as a plain bubble; sentinel never displayed.
- [ ] Reload `isCrisis` derivation (Task 3) — and the Task 1 sibling audit result (direction / message-id / feedback).
- [ ] **Latest-pin behavior change (Task 4)** — a user in repeated crisis now sees the MOST RECENT card. Clinically confirm this is the intended disposition.
- [ ] Task 1 root-cause finding (the confirmed transition + any siblings).
- [ ] Persist-side pin present.
- [ ] Browser-verified EN + AR on the exact failing scenario; QA-checklist entry landed.
- [ ] Out-of-band follow-up: Phase 0b linked from #191, priority raised as a safety item.

## Guardrails
- Crisis path → clinical/PO sign-off before merge. Do NOT alter the helpline number/copy (separate GL-1 escalation). `next build` before deploy. Deploy from an isolated worktree, not the shared checkout.
