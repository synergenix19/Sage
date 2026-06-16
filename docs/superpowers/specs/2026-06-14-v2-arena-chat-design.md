# V2 Arena Chat — Side-by-Side Generation Experiment Design

> **Status:** Design / spec. Awaiting user review before writing the implementation plan.
> **Date:** 2026-06-14
> **Author:** brainstormed with Claude Code

## 1. Goal

Let us compare two generation strategies head-to-head and learn which users prefer:

- **v1** — the current production experience: the full 9-node LangGraph (intent routing, skill selection, skill execution, knowledge retrieval, freeflow).
- **v2** — a single-prompt experience: the MIND-SAFE system prompt (People/Pain/LLMs research brief, June 2026) run as one LLM call with conversation memory, **no skills, no routing, nothing else**.

Both arms are tested through a **side-by-side arena**: one user message produces a reply from each arm; the user picks the one they prefer. Position is randomized to remove left/right bias.

## 2. Core architectural principle — share the guards, fork only the middle

This is non-negotiable and is what makes the experiment safe.

```
                          ┌─────────────────────────────────────────┐
   user message ────────► │  INPUT GUARD  (safety_check_node)         │   ← shared, runs ONCE
                          │  crisis lexicon + clinical flags + S3      │
                          └───────────────┬──────────────────────────┘
                                          │
                       crisis? ───────────┴──────────── safe?
                          │                                  │
                  single crisis card               ┌─────────┴─────────┐
                  (no arena, no "pick")             │   FORK THE MIDDLE  │
                                                    │                    │
                                          ┌─────────▼────────┐  ┌────────▼─────────┐
                                          │ v1 arm           │  │ v2 arm           │
                                          │ existing graph   │  │ MIND-SAFE single │
                                          │ middle           │  │ prompt + memory  │
                                          └─────────┬────────┘  └────────┬─────────┘
                                                    │                    │
                          ┌─────────────────────────▼────────────────────▼─────────┐
                          │  OUTPUT GUARD  (output_gate_node)  — runs per arm        │   ← shared
                          │  cultural rules + banned-opener + identity + audit       │
                          └─────────────────────────┬───────────────────────────────┘
                                                     │
                                       both replies → arena UI (randomized L/R)
                                                     │
                                            user picks a side
                                                     │
                                  log preference + chosen reply becomes thread history
```

Both arms call the **same node functions** (`safety_check_node`, `output_gate_node`) as middleware, so "identical guards" is guaranteed by construction, not by discipline. Crisis detection is live and identical on both arms — real users type real distress even in internal testing.

## 3. Decisions locked (from brainstorming)

| # | Decision | Choice |
|---|----------|--------|
| 1 | Comparison UX | **Side-by-side arena** (one message → both arms reply → user picks); position randomized |
| 2 | Audience | **Staff / testers only**, behind a flag. No real-pilot-user exposure in this scope |
| 3 | Pilot single-arm surface | **Deferred** — not built now |
| 4 | Guards | **Shared** — same `safety_check_node` (in) and `output_gate_node` (out) for both arms |
| 5 | Crisis | Live + identical on both arms; on detection the arena **collapses to one crisis card** (never gamified) |
| 6 | v2 content | MIND-SAFE prompt **verbatim** in its own editable file |
| 7 | Memory | **In-session, pick-then-continue**: the chosen reply becomes canonical conversation history; passed forward via the request `messages` array |
| 8 | Preference capture | **Logged** per turn (version, position, pick, session) — this is the "which do they prefer" signal |

### Noted wart (user's call, not a blocker)
The MIND-SAFE prompt contains the US hotline `988`. With shared guards restored, the deterministic UAE crisis card (MoHAP `800 46342`) fires on *detected* crises regardless of arm, so `988` can only ever surface on an *undetected* crisis. Recommended one-word edit: `988 → UAE crisis line` in the v2 prompt file. Left to the author's discretion since "verbatim" was requested.

## 4. Components & files

### Backend
- **`sage-poc/server.py`**
  - **New endpoint `POST /chat/arena`** (staff-gated): takes one message, returns both arms' replies + a `comparison_id`. Streams both, or returns both after generation (see §6). (No `version` field is added to `ChatRequest` in this scope — the arena always runs both arms; a per-request `version` selector belongs to the deferred single-arm surface.)
  - **New endpoint `POST /chat/arena/vote`**: records `{comparison_id, chosen_version, left_version, right_version, chosen_side, session_id, user_id}`.
  - Existing `POST /chat` (v1 production) is **unchanged**.
- **New `sage-poc/src/sage_poc/arena/orchestrator.py`**
  - Runs the input guard **once**; on crisis returns the single card; otherwise generates both arms (in parallel) and runs the output guard per arm.
- **New `sage-poc/src/sage_poc/arena/v2_generate.py`**
  - The v2 generator: loads the MIND-SAFE prompt, threads conversation history, calls the LLM (reusing v1's existing LLM client/factory — no new model wiring), returns `response_en`.
- **New `sage-poc/src/sage_poc/arena/mind_safe_prompt.md`**
  - The MIND-SAFE system prompt, verbatim, in its own file so clinical reviewers can edit it without a code change.

### v1 arm — reuse, don't refactor
For the v1 arm we run the **existing compiled graph as-is**. The orchestrator runs `safety_check_node` once up front for the authoritative crisis-collapse decision; if safe, the v1 arm invokes the full production graph (which re-runs its own guards on the same input — deterministic, same result, behaviorally identical) and the v2 arm runs `safety_check_node` → `v2_generate` → `output_gate_node`.

- **Pro:** production v1 graph is touched **zero** times → no regression risk on the safety-critical path.
- **Con:** the v1 arm runs `safety_check` redundantly (extra S3/BGE-M3 latency). Acceptable for a staff arena.
- **Future (out of scope):** if the arena graduates, extract the graph "middle" into a reusable subgraph so guards truly run once. Recorded as deferred cleanup, not done now.

### Frontend
- **`cdai/apps/web/app/api/chat/route.ts`** — add an arena route (or extend) that calls `/chat/arena`; Zod schema gains the arena fields; persistence tags each stored message with its version.
- **`cdai/apps/web/components/chat/`** — new arena view: two response panels side by side (randomized L/R), a "pick this one" affordance per panel, and the staff gate. Reuses the existing `CrisisCard` component for the collapse case. Crisis turns render a single card, no panels.
- **Staff gate:** arena UI + endpoints are visible/allowed only behind `V2_CHAT_ENABLED` (env flag, default off) **and** staff role. No real pilot user can reach it.

## 5. Data flow

**Normal turn (safe):**
1. Client → `POST /chat/arena` with full `messages` history + `session_id`.
2. Orchestrator runs `safety_check_node` once. `is_safe = True`.
3. In parallel: v1 arm (full graph) and v2 arm (`v2_generate`) produce `response_en` each.
4. `output_gate_node` runs on each `response_en` (cultural rules, banned-opener, identity audit, Arabic translation, per-arm audit trail).
5. Server returns both replies + `comparison_id`, with L/R order randomized server-side (and the mapping stored so the vote can be de-randomized).
6. User picks → `POST /chat/arena/vote`. The chosen reply is appended to the conversation; the next turn continues from it.

**Crisis turn:**
1–2. Input guard fires (`is_safe = False`).
3. Orchestrator returns the **single deterministic crisis card** (`_crisis_response_node` output). No arena, no panels, no vote. `crisis_state` transitions exactly as in v1.

## 6. Memory model

- Memory = the **conversation thread**, carried in the request `messages` array (already how v1 works; already persisted per-thread to Supabase by the Next.js route, so it survives reloads).
- **Pick-then-continue:** only the chosen arm's reply enters history. The unchosen reply is logged for analysis but never threaded — this keeps one coherent conversation and avoids divergent histories.
- The v2 generator threads the full thread under the MIND-SAFE system prompt, with a simple history cap (last N turns / token budget) to prevent context overflow. The cap is a sensible default, not extra machinery.

## 7. Preference / comparison logging

Recorded per comparison (table or structured log, following existing audit conventions):
`comparison_id`, `session_id`, `user_id`, `turn_number`, `left_version`, `right_version`, `chosen_version`, `chosen_side` (to measure residual position bias), `timestamp`, and token usage per arm. This is the dataset that answers "which do they prefer." Because the audience is staff, this is evaluation data, not clinical-population data.

## 8. Safety & governance

- Crisis perimeter is **fully preserved** on both arms (the whole point of sharing the guards), so the earlier "no-perimeter" risk-acceptance escalation is **no longer needed**.
- Remaining governance item: a short note recording that v2 swaps the entire generation strategy for the MIND-SAFE prompt and that the arena is **staff-gated**; clinical awareness sign-off before any change to the audience (i.e., before building the deferred pilot single-arm surface). This is awareness, not a blocker for the staff arena.
- Recommended prompt edit `988 → UAE crisis line` (see §3).

## 9. Testing

- **v1 regression:** production `POST /chat` and the compiled graph behave identically (the arena adds code; it must not modify v1's path). Existing suite stays green.
- **Shared-guard identity:** assert the arena calls the same `safety_check_node` / `output_gate_node` functions; assert crisis input collapses to a single card with no panels and no vote path.
- **v2 arm:** MIND-SAFE prompt loads verbatim; full history is threaded; output streams; assert no skill/intent/knowledge node is invoked for the v2 arm.
- **Arena orchestration:** both arms generate; L/R randomization present; vote endpoint records the correct mapping; pick-then-continue threads only the chosen reply.
- **Staff gate:** arena endpoints/UI unreachable when `V2_CHAT_ENABLED` is off or role is non-staff.

## 10. Out of scope (deferred)

- Single-arm sticky pilot surface for real users.
- Extracting the graph middle into a reusable subgraph (guard-runs-once optimization).
- Any cross-session / persistent (pgvector / therapeutic-profile) memory for v2 — in-session only.
- In-app preference UI beyond the binary pick (e.g., per-message thumbs, free-text).

## 11. Risks / open items

- **v1-arm double guard latency** — accepted for staff arena; revisit if it hurts the testing experience.
- **History cap value** — pick a default (e.g., last 20 turns or a token budget) during implementation; confirm it doesn't truncate mid-thread in a way that disadvantages either arm.
- **Randomization fairness** — ensure the same RNG seeding approach is auditable so position bias can be measured, not just assumed gone.
