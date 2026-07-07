# Sage Presence Indicator + Typewriter Reveal — Design Spec — 2026-07-07

**Goal:** make Sage's chat *feel* like live, real-time generation and cut perceived time-to-first-paint, without touching the clinical safety gate. Two components: a **Presence Indicator** (the waiting state, replacing today's single static typing dot) and a **Typewriter Reveal** (word-level progressive reveal of the gated answer, replacing today's one-burst paint).

**Scope:** the frontend experience layer (`cdai`) in Phase 0a; a small, safety-neutral backend liveness channel (`sage-poc` + `cdai`) in Phase 0b. **No change to the Node 8 output_gate, no early emission of un-gated content.** This is "Tier 0" of the streaming conversation — perceived-latency polish. Real token streaming (decomposing the safety post-check) is Tier 2 and remains the parked `2026-06-23-streaming-design.md` project.

---

## 1. Context — why this exists, and what it is NOT

Today `chat()` (`sage-poc/server.py:382`) runs the entire 9-node LangGraph to completion via `await graph.ainvoke()` (`:440`) — safety detection, routing, generation, **and** the `output_gate` post-check — before a single byte leaves the server. Only then does `_body()` (`:519-523`) yield. `_stream_tokens` (`:91`) is a pure `re.findall` that re-slices the *finished* string and flushes it with no pacing, so the client receives the whole answer in one burst ("displays everything at once"). The frontend (`cdai/apps/web/components/chat/chat-interface.tsx`, `useStreamingChat`) consumes it as a stream but, because the first byte only arrives at turn-end, **TTFT ≈ full turn latency.**

**Honesty statement (must appear verbatim in the shipped spec and PR description):**
> POC p50 turn latency ≈ 17s (2026-06-24 Latency RCA: ~7.4s graph + ~8.5s outside-graph), against an architecture target of `<3s` p95. The Presence Indicator and Typewriter Reveal are **POC perceived-latency mitigations**. They improve time-to-first-paint and the felt experience; they are **never** counted against the `<3s` p95 total-latency KPI, and their existence is **not** evidence the KPI is met. The p50 gap is a tracked engineering item — likely contributors: model choice, cold starts, and sequential LLM calls that v7 specifies as parallel fan-out — owned separately (see §9).

This spec must not quietly mask that gap. It mitigates the *experience* of the gap while the gap itself stays visible and tracked.

---

## 2. Component A — Sage Presence Indicator (the waiting state)

### 2.1 Register (the core adaptation)
The mechanic is Claude/ChatGPT's "living micro-copy while waiting," but the **register shifts from playful to present**: the indicator should feel like a therapist's attentive silence, not a computer working. Sage's users may be typing while distressed.

**Three word-classes are banned from the copy pool:**
- **Process words** — "Analyzing…", "Checking…", "Assessing…", "Processing…" (clinical/surveillance feel; also narrates the pipeline).
- **Promise words** — "Finding the answer…", "Solving…" (over-promises; therapy does not deliver answers).
- **Whimsy words** — "Pondering…", "Brewing…" (tone-deaf after a painful disclosure).

### 2.2 Copy pool (proposed — clinician + native-Khaleeji sign-off REQUIRED before ship)
Static frontend i18n strings, first-person presence. ~8–12 items. **Every phrase must survive the test:** read it after (a) a crisis disclosure, (b) a casual greeting, (c) a long trauma story — if it feels wrong after any of them, cut it.

| EN | AR (Khaleeji-warm) |
|---|---|
| Listening… | أسمعك… |
| I'm with you… | معك… |
| Taking that in… | أستوعب كلامك… |
| One moment… | لحظة… |
| Thinking about what you said… | أفكر في اللي قلته… |
| Here with you… | موجود معك… |
| Giving this a moment… | أعطي هذا وقته… |

- Slow phrase (Phase 2, see §2.3): EN "Still with you — taking a little longer…" / AR "معك، بس أحتاج شوي وقت…"
- Degraded phrase (Phase 3): EN "This is taking longer than it should. Give me one more moment, or try sending again." / AR (pending sign-off).
- Arabic gender: gender-neutral phrasing where possible; otherwise gendered variants keyed to `gender_address` in `cultural_preferences`.
- Selection is **random-without-repeat** (shuffle-bag): never the same opening phrase twice in a row across turns.

### 2.3 Timing envelope — RECALIBRATED to observed POC latency, driven by CONFIG not constants
The originally-proposed envelope (2nd phrase at 4s, fallback at 12s) was calibrated to the `<3s` p95 *target*. Against the observed ~17s p50, a 12s fallback would fire on the majority of **healthy** turns — the indicator would routinely apologize for normal operation. Recalibrated to the real distribution:

| Phase | Threshold (config key) | Default (provisional) | Behavior |
|---|---|---|---|
| 0 | — | 0–600ms | Breathing dot only, no phrase |
| 1 | `PRESENCE_PHRASE_MS` | 600ms | First phrase fades in and is **held** (no in-turn rotation — rotation signals "long computation" and induces anxiety) |
| 2 | `PRESENCE_SLOW_MS` | ~8000–10000ms | Cross-fade to the steadier "still with you" phrase — lands mid-wait on a typical turn, exactly where reassurance is needed |
| 3 | `PRESENCE_DEGRADED_MS` | **observed p95 (query real logs), provisional 30000ms** | Cross-fade to the degraded/honesty phrase — OR on actual request failure, **whichever comes first** |

- **All four thresholds are configuration values** (a config module / env), never inlined constants. When production latency drops toward the 3s target, the envelope tightens by config change, not code change.
- `PRESENCE_DEGRADED_MS` default MUST be set from a fresh `session_audit.latency_ms` p95 query, not guessed (blocking plan task). The 30000ms placeholder is provisional pending that query.
- The existing request timeout (`FIRST_BYTE_TIMEOUT_MS = 58_000` in `chat-interface.tsx`) is unchanged and remains the hard ceiling.

### 2.4 Visual + accessibility
- **Animation:** slow "breathing" pulse (~4s cycle), borrowed from breathing-exercise UX — the pacing itself is regulating. Subtle, low-contrast. NOT fast typing dots.
- **Uniformity / crisis indistinguishability (safety property):** the waiting state is **byte-identical on every path.** It must never reveal that a turn is going down the crisis path. All path differentiation happens only at *render* (§3.4). This is why the Phase-2/3 transitions are driven by **local timers**, and why the Phase 0b heartbeat (§4) is **content-free** — no tick ever selects or changes a phrase, so turn-path cannot leak via timing.
- **`prefers-reduced-motion`:** static dot (no pulse), phrase still shown.
- **Screen readers:** the current phrase is announced once via `aria-live="polite"` (the chat log already has `role="log" aria-live="polite"`), not on every animation frame.
- **RTL:** correct placement and direction for Arabic.

---

## 3. Component B — Typewriter Reveal (the arrival)

Fixes "displays everything at once." Once the gated answer arrives complete, it is revealed progressively client-side so it reads like live generation — the closest feel to Abby / ChatGPT / Claude continuous streaming. This is **pure presentation of already-gated text** — zero safety risk.

### 3.1 Granularity
- **Word-level (or 2–3-word chunks), NEVER character-level.** In Arabic, character-by-character reveal causes contextual glyph re-shaping jitter as letters join; word-level is visually identical to streaming and RTL-safe.

### 3.2 Speed
- ~25–35 words/second, easing slightly **faster** as it progresses.
- **Total reveal capped at ~2.5s** (`TYPEWRITER_MAX_MS`, config). For long responses, **accelerate** — never make the user wait longer than the cap.
- `TYPEWRITER_WPS` (default 30) is config.

### 3.3 Skip affordances
- Tap anywhere on the message → full text instantly.
- User starts typing in the input → reveal completes immediately.

### 3.4 Crisis exception — `render_mode`
- Crisis-path responses render in a **single frame** (no typewriter), helpline card present from **first paint**.
- Driven by a single `render_mode` flag: `'instant'` for crisis, `'typewriter'` otherwise.
- **Phase 0a source of truth:** derive `render_mode` from signals already present today — the `CRISIS_SIGNAL` body prefix and `X-Sage-Crisis-Tier` header. No new backend needed.
- **Phase 0b source of truth:** `render_mode` becomes an explicit field on the terminal metadata frame (§4.2).

### 3.5 Accessibility
- `prefers-reduced-motion` → whole-message **fade-in** (~300ms), no per-word timing. Build this fade path regardless (~20 lines) — it doubles as both the reduced-motion fallback and the crisis-adjacent calm-render option.
- Screen readers: the **full** text is announced once on arrival, not incrementally (announcing each word would flood the live region).

---

## 4. Backend wiring

### 4.1 Phase 0a — none
The entire visible experience (Presence Indicator + Typewriter) is 100% frontend. `render_mode` is derived from today's `CRISIS_SIGNAL` + `X-Sage-Crisis-Tier`. No `server.py` change ships in 0a.

The only thing 0a gives up is **early-dead detection**: with no backend signal, the frontend cannot distinguish "slow but alive" from "dead" before its local `PRESENCE_DEGRADED_MS` timer. This is acceptable for a first ship; the 12s→p95 fallback still fires on the local timer.

### 4.2 Phase 0b — content-free liveness heartbeat + metadata-to-body frame (COMMITTED fast-follow)
At ~17s turns, users will wonder if it's broken; a content-free heartbeat is the only honest "still alive" signal. 0b is committed, not optional. It also seeds the Tier 2 streaming architecture (two-birds).

**The architectural coupling (why 0b is not frontend-only):** HTTP commits response headers at the first body byte. The moment the server emits a liveness tick (e.g. at 2s), the `X-Sage-*` headers lock **before `graph.ainvoke` has produced a result.** Today the frontend reads crisis-state, direction, message-id, sources, skill-media, tier, node-path, etc. from those headers. So the heartbeat forces migrating that metadata **out of headers into a trailing in-body frame**, emitted last (post-gate, exactly as safe as today's headers).

**0b changes:**
- `sage-poc/server.py`: restructure `chat()` so `graph.ainvoke` runs as a task; the `StreamingResponse` generator emits a **content-free** tick every `HEARTBEAT_INTERVAL_MS` (~2000–3000ms) until the task completes, then emits the gated answer, then a **terminal metadata frame** (a sentinel-delimited JSON line) carrying everything the `X-Sage-*` headers carry today, including explicit `render_mode`.
- `cdai/apps/web/app/api/chat/route.ts` + `chat-interface.tsx`: read metadata from the terminal frame instead of headers; if no tick arrives within `HEARTBEAT_DEAD_MS` (~5000ms), jump to the degraded state **early** instead of waiting for `PRESENCE_DEGRADED_MS`.
- Ticks are content-free and never influence phrase selection — the crisis-indistinguishability property (§2.4) is preserved.

---

## 5. Governance

- Copy pool lives in the `cdai` i18n string files, PR-reviewed. **Clinician + native-Khaleeji sign-off required to add or modify any phrase.** Ship with the proposed pool marked pending sign-off; do not invent additional Arabic phrasing without review.
- **New eval scenario:** waiting-state screenshot review **after a crisis-path turn**, asserting the waiting state is indistinguishable from a normal turn. Slot alongside the persona/pressure tests.
- **Analytics boundary:** log the shown-phrase ID **client-side only** (UX analytics). It must **never** enter the clinical audit trail (`session_audit`).
- Em-dash note: the microcopy strings are static UI copy, not rule/action content that mirrors into LLM output, so the em-dash-ban rule does not apply to them; preserve the phrasing as reviewed.

---

## 6. Configuration summary

| Key | Phase | Default | Notes |
|---|---|---|---|
| `PRESENCE_PHRASE_MS` | 0a | 600 | First phrase fade-in |
| `PRESENCE_SLOW_MS` | 0a | 9000 | Cross-fade to "still with you" |
| `PRESENCE_DEGRADED_MS` | 0a | **from real p95** (prov. 30000) | Or on request failure, whichever first |
| `TYPEWRITER_WPS` | 0a | 30 | 25–35 range, eases faster |
| `TYPEWRITER_MAX_MS` | 0a | 2500 | Hard cap; long responses accelerate |
| `HEARTBEAT_INTERVAL_MS` | 0b | 2500 | Content-free tick cadence (server) |
| `HEARTBEAT_DEAD_MS` | 0b | 5000 | No tick within → early degraded (client) |

---

## 7. Testing

- **Unit (0a):** shuffle-bag never repeats consecutively; timer phase transitions at configured thresholds; typewriter word-chunking (EN + AR, RTL); cap/acceleration for long text; skip affordances (tap, type) complete the reveal; `prefers-reduced-motion` → fade path; `render_mode='instant'` for crisis skips typewriter.
- **A11y:** `aria-live` announces phrase once (not per frame); full answer announced once on arrival (not per word); RTL placement.
- **Indistinguishability (safety):** automated screenshot diff of the waiting state across a normal turn vs a crisis turn — must be identical.
- **0b:** heartbeat emitted during a slow `ainvoke`; terminal metadata frame parsed correctly; header-contract parity (every field previously in `X-Sage-*` present in the frame, incl. `render_mode`); no-tick-within-`HEARTBEAT_DEAD_MS` → early degraded.

---

## 8. Phasing

- **Phase 0a (ships first, frontend-only, `cdai`):** Presence Indicator + Typewriter Reveal, all thresholds config, `render_mode` from existing signals. De-risked for Gitex — no `server.py` change, no contract migration.
- **Phase 0b (committed fast-follow, `sage-poc` + `cdai`):** content-free heartbeat + metadata-to-body frame + early-dead detection. Seeds Tier 2.

---

## 9. Out of scope / tracked follow-ups

- **The 17s p50 KPI gap itself** — separate engineering item (model choice, cold starts, v7 parallel fan-out of currently-sequential LLM calls). Cross-ref the 2026-06-24 Latency RCA and the parked streaming design. This spec mitigates the *experience*, not the gap.
- **Tier 2 real streaming** — decomposing the Node 8 safety post-check into a streamable per-sentence gate (the parked `2026-06-23-streaming-design.md`, binding constraint §4.4). 0b's terminal-frame contract is a deliberate stepping-stone toward it.
- **Fresh p50/p95 query** — blocking task in the implementation plan; sets `PRESENCE_DEGRADED_MS` from real prod data.
