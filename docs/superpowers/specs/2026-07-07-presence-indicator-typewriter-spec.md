# Sage Presence Indicator + Typewriter Reveal — Design Spec — 2026-07-07

**Goal:** make Sage's chat *feel* like live, real-time generation and cut perceived time-to-first-paint, without touching the clinical safety gate. Two components: a **Presence Indicator** (the waiting state, replacing today's single static typing dot) and a **Typewriter Reveal** (word-level progressive reveal of the gated answer, replacing today's one-burst paint).

**Scope:** the frontend experience layer (`cdai`) in Phase 0a; a small, safety-neutral backend liveness channel (`sage-poc` + `cdai`) in Phase 0b. **No change to the Node 8 output_gate, no early emission of un-gated content.** This is "Tier 0" of the streaming conversation — perceived-latency polish. Real token streaming (decomposing the safety post-check) is Tier 2 and remains the parked `2026-06-23-streaming-design.md` project.

---

## 1. Context — why this exists, and what it is NOT

Today `chat()` (`sage-poc/server.py:382`) runs the entire 9-node LangGraph to completion via `await graph.ainvoke()` (`:440`) — safety detection, routing, generation, **and** the `output_gate` post-check — before a single byte leaves the server. Only then does `_body()` (`:519-523`) yield. `_stream_tokens` (`:91`) is a pure `re.findall` that re-slices the *finished* string and flushes it with no pacing, so the client receives the whole answer in one burst ("displays everything at once"). The frontend (`cdai/apps/web/components/chat/chat-interface.tsx`, `useStreamingChat`) consumes it as a stream but, because the first byte only arrives at turn-end, **TTFT ≈ full turn latency.**

**Honesty statement (must appear verbatim in the shipped spec and PR description):**
> POC p50 turn latency ≈ 17s (2026-06-24 Latency RCA: ~7.4s graph + ~8.5s outside-graph), against an architecture target of `<3s` p95. The Presence Indicator and Typewriter Reveal are **POC perceived-latency mitigations**. They improve time-to-first-paint and the felt experience; they are **never** counted against the `<3s` p95 total-latency KPI, and their existence is **not** evidence the KPI is met. The p50 gap is a tracked engineering item — likely contributors: model choice, cold starts, and sequential LLM calls that v7 specifies as parallel fan-out — owned separately (see §9).

This spec must not quietly mask that gap. It mitigates the *experience* of the gap while the gap itself stays visible and tracked.

### 1.1 Measured latency (2026-07-07, prod `tcekehffneiqcdyhzobi`, `session_audit`, n=547, 2026-06-23→07-07)

| percentile | graph-internal `latency_ms` | est. user-perceived total\* |
|---|---|---|
| p50 | 6.4s | ~15s |
| p95 | 11.7s | ~20s |
| p99 | 14.5s | ~23s |
| max | 30.7s | ~39s |

\* total = graph-internal + ~8.5s outside-graph. The ~8.5s is from the 2026-06-24 Latency RCA (log-derived: `pre_graph` checkpoint read + `post_graph_write`); it is **not** stored in `session_audit`, so it is carried here as an inherited assumption. Phase 0b's `ainvoke_total` logging can replace it with a measured total later.

Findings: only **1/547** turns exceeded 30s graph-internal; **0** exceeded 45s; the 58s client timeout is never approached. The graph itself is well-behaved (p99 14.5s) — the ~17s total is dominated by the **~8.5s outside-graph** span (checkpointer `saver_pool` stuck at 4, per the RCA), which is the real KPI-gap contributor (§9), not the graph. `freeflow_gen_ms`/`translate_out_ms` are NULL in prod (a separate, non-blocking observability gap).

**Envelope calibration from this data:** `PRESENCE_SLOW_MS` 9000 ≈ mid-wait of the ~15s total p50 (reassurance lands where needed). `PRESENCE_DEGRADED_MS` 25000 ≈ total p99 (~23s) + margin — only the genuine ~1% tail ever sees the honesty phrase; a healthy p95 turn (~20s) never does. The 0b `HEARTBEAT_DEAD_MS` (5s) catches a truly-dead request long before 25s.

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
- Arabic gender (addressing the user): gender-neutral phrasing where possible; otherwise gendered variants keyed to `gender_address` in `cultural_preferences`.
- **OPEN ITEM — Sage-persona self-description gender (do NOT resolve in this spec):** "موجود معك" is gendered by Sage's *own* persona (موجود / موجودة — masculine / feminine self-reference), which is a **persona-definition** question, not a user-preference one. `gender_address` governs how Sage addresses the *user*, not how Sage *describes itself*. This must go to the clinical/persona review as an explicit decision — it must **not** be silently defaulted to masculine. Until resolved, prefer self-reference-neutral Arabic phrasing in the pool (e.g. "معك…", "لحظة…", "أسمعك…") so no shipped phrase forces the persona-gender choice.
- Selection is **random-without-repeat** (shuffle-bag): never the same opening phrase twice in a row across turns.

### 2.3 Timing envelope — RECALIBRATED to observed POC latency, driven by CONFIG not constants
The originally-proposed envelope (2nd phrase at 4s, fallback at 12s) was calibrated to the `<3s` p95 *target*. Against the observed ~17s p50, a 12s fallback would fire on the majority of **healthy** turns — the indicator would routinely apologize for normal operation. Recalibrated to the real distribution:

| Phase | Threshold (config key) | Default (provisional) | Behavior |
|---|---|---|---|
| 0 | — | 0–600ms | Breathing dot only, no phrase |
| 1 | `PRESENCE_PHRASE_MS` | 600ms | First phrase fades in and is **held** (no in-turn rotation — rotation signals "long computation" and induces anxiety) |
| 2 | `PRESENCE_SLOW_MS` | ~8000–10000ms | Cross-fade to the steadier "still with you" phrase — lands mid-wait on a typical turn, exactly where reassurance is needed |
| 3 | `PRESENCE_DEGRADED_MS` | **25000ms** (≈ total p99, §1.1) | Cross-fade to the degraded/honesty phrase — OR on actual request failure, **whichever comes first** |

- **All four thresholds are configuration values** (a config module / env), never inlined constants. When production latency drops toward the 3s target, the envelope tightens by config change, not code change.
- `PRESENCE_DEGRADED_MS` = 25000ms is set from the real distribution measured in §1.1 (≈ total p99 ~23s + margin), not guessed — a healthy p95 turn never trips it. Re-tune by config if the distribution shifts.
- The existing request timeout (`FIRST_BYTE_TIMEOUT_MS = 58_000` in `chat-interface.tsx`) is unchanged and remains the hard ceiling.

**Resend semantics (Phase 3):** the degraded phrase invites "try sending again" while the original request may still be in flight. The resend affordance MUST **supersede** the in-flight request — abort the current `AbortController` before issuing the retry — so there is never more than one server-side turn for a single user utterance. (A client abort does not cancel the backend `ainvoke`, but issuing the retry only *after* aborting the client stream, gated by the existing `inFlightRef`, prevents the client from *stacking* a second concurrent run — the same retry-storm guard already in `reload()`.) Two concurrent turns for one utterance would also write **two `session_audit` rows for one utterance** — explicitly disallowed.

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
- **Bidi-safe chunking for code-switched text.** Target users code-switch mid-sentence (e.g. "أحس بضغط كبير and my boss…"). Chunk boundaries MUST respect bidi runs: never reveal a boundary that splits a partial LTR run embedded in an RTL context (or vice-versa) such that already-revealed words re-order or re-position when the following words land. Segment on Unicode word boundaries **within** each bidi run — a chunk never straddles a direction change. The revealed prefix must render at each step exactly as it will in the final laid-out message.

### 3.2 Speed
- ~25–35 words/second, easing slightly **faster** as it progresses.
- **Total reveal capped at ~2.5s** (`TYPEWRITER_MAX_MS`, config). For long responses, **accelerate** — never make the user wait longer than the cap.
- `TYPEWRITER_WPS` (default 30) is config.

### 3.3 Skip affordances
- Tap anywhere on the message → full text instantly.
- User starts typing in the input → reveal completes immediately.

### 3.4 Render mode — three-valued (as shipped 2026-07-08)
- Render mode is **three-valued**: **instant** | **fade** | **typewriter**.
  - **instant** — crisis-path responses render in a **single frame** (no typewriter), helpline card present from **first paint** (structurally: crisis content renders in `CrisisCard`, never the reveal path).
  - **fade** — replies containing **block-level Markdown** (lists/headings/blockquotes/bold, via `hasBlockMarkdown`) **or** under `prefers-reduced-motion` skip the typewriter and render as one **calm ~300ms fade** (no raw→snap seam). ~6% of prod replies are block-Markdown.
  - **typewriter** — plain prose (motion allowed) reveals word-by-word.
- **Phase 0a source of truth:** crisis derived from the `CRISIS_SIGNAL` body prefix + `X-Sage-Crisis-Tier` header; fade-vs-typewriter decided client-side from `hasBlockMarkdown(content)` + `prefers-reduced-motion`. No new backend needed.
- **Phase 0b source of truth:** the crisis signal becomes an explicit field on the terminal metadata frame (§4.2).
- **Implementation note (2026-07-08):** the fade path must NOT fire `onRevealComplete` — doing so clears the reveal and strips the fade class before the 300ms animation plays (measured ~12ms → invisible). Completion fires only on the typewriter path.

### 3.5 Accessibility
- `prefers-reduced-motion` → the **fade** render mode (§3.4); `motion-safe:` gating means reduced-motion users get an instant, animation-free appearance while motion-allowed users get the ~300ms fade.
- Screen readers: the **full** text is announced once on arrival, not incrementally (announcing each word would flood the live region).

---

## 4. Backend wiring

### 4.1 Phase 0a — none
The entire visible experience (Presence Indicator + Typewriter) is 100% frontend. `render_mode` is derived from today's `CRISIS_SIGNAL` + `X-Sage-Crisis-Tier`. No `server.py` change ships in 0a.

The only thing 0a gives up is **early-dead detection**: with no backend signal, the frontend cannot distinguish "slow but alive" from "dead" before its local `PRESENCE_DEGRADED_MS` timer. This is acceptable for a first ship; the `PRESENCE_DEGRADED_MS` (25s ≈ total p99) fallback still fires on the local timer.

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
| `PRESENCE_DEGRADED_MS` | 0a | 25000 (≈ total p99, §1.1) | Or on request failure, whichever first |
| `TYPEWRITER_WPS` | 0a | 30 | 25–35 range, eases faster |
| `TYPEWRITER_MAX_MS` | 0a | 2500 | Hard cap; long responses accelerate |
| `HEARTBEAT_INTERVAL_MS` | 0b | 2500 | Content-free tick cadence (server) |
| `HEARTBEAT_DEAD_MS` | 0b | 5000 | No tick within → early degraded (client) |

---

## 7. Testing

- **Unit (0a):** shuffle-bag never repeats consecutively; timer phase transitions at configured thresholds; typewriter word-chunking (EN + AR, RTL); **code-switched reveal — a bidi-mixed response (e.g. "أحس بضغط كبير and my boss…", drawn from the C-2 eval cases) reveals with no chunk straddling a direction change and no re-ordering of already-revealed words**; cap/acceleration for long text; skip affordances (tap, type) complete the reveal; `prefers-reduced-motion` → fade path; `render_mode='instant'` for crisis skips typewriter.
- **A11y:** `aria-live` announces phrase once (not per frame); full answer announced once on arrival (not per word); RTL placement.
- **Indistinguishability (safety):** automated screenshot diff of the waiting state across a normal turn vs a crisis turn — must be identical. **The waiting state includes a randomly selected phrase, so the shuffle-bag MUST be deterministically seeded in test mode** (both turns render the identical phrase) before the full-frame diff — otherwise the diff fails on phrase variance, not path leakage, and gets quietly weakened when it flakes. Deterministic-seed is the chosen approach (not phrase-region masking), so the diff still covers the full frame including the phrase region.
- **0b:** heartbeat emitted during a slow `ainvoke`; terminal metadata frame parsed correctly; header-contract parity (every field previously in `X-Sage-*` present in the frame, incl. `render_mode`); no-tick-within-`HEARTBEAT_DEAD_MS` → early degraded.

---

## 8. Phasing

- **Phase 0a (ships first, frontend-only, `cdai`):** Presence Indicator + Typewriter Reveal, all thresholds config, `render_mode` from existing signals. De-risked for Gitex — no `server.py` change, no contract migration.
- **Phase 0b (committed fast-follow, `sage-poc` + `cdai`):** content-free heartbeat + metadata-to-body frame + early-dead detection. Seeds Tier 2.

---

## 9. Out of scope / tracked follow-ups

- **The 17s p50 KPI gap itself** — separate engineering item (model choice, cold starts, v7 parallel fan-out of currently-sequential LLM calls). Cross-ref the 2026-06-24 Latency RCA and the parked streaming design. This spec mitigates the *experience*, not the gap.
- **Tier 2 real streaming** — decomposing the Node 8 safety post-check into a streamable per-sentence gate (the parked `2026-06-23-streaming-design.md`, binding constraint §4.4). 0b's terminal-frame contract is a deliberate stepping-stone toward it.
- **Fresh p50/p95/p99 query** — DONE 2026-07-07 (§1.1); `PRESENCE_DEGRADED_MS` set to 25000 from real prod data. Re-run and re-tune by config if the latency distribution shifts.
- **Measured user-perceived total latency** — the ~8.5s outside-graph span is currently an RCA-inherited assumption (not in `session_audit`). Phase 0b's `ainvoke_total` logging should persist a measured total so the envelope can be re-derived without the assumption. Also: `freeflow_gen_ms`/`translate_out_ms` are NULL in prod — wire them (separate observability fix).
