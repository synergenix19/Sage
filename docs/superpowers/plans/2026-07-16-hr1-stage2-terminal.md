# HR-1 Stage 2 — High-Risk Terminal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Replace Stage 1's LLM-rendered `psychotic_referral` delivery with a deterministic two-turn `high_risk_response` safety terminal that implements BOT BEHAVIOUR §HR verbatim: ask distress (0–10) → branch → standardized message + professional referral, with §3's score-based escalation. Flag-gated so OFF = Stage-1 behavior.

**Architecture:** A dedicated 2-step node modeled on `medical_response` (NOT a skill — the branch is a safety-control decision on a parsed user value; Cardinal Rule 1). Routes at `_route_after_safety` as the 4th safety terminal. Reuses `select_crisis_resources()`/`CRISIS_CONFIG`, the LangGraph checkpointer (2-turn persistence), the audit conditional-column pattern. Crisis-precedence is free (safety_check every turn; crisis returned first).

**Tech Stack:** Python, pytest, LangGraph, psycopg.

## Global Constraints
- **Fixed copy verbatim from §HR** (bot_behaviour.txt L1512–1526): the distress question, the §2 message, the §3 redirects. Single-sourced in config, never LLM-rendered. No em dashes in copy content (commas).
- **Flag gate:** `SAGE_HIGH_RISK_TERMINAL` (strict idiom — only literal "true" enables; garbage→OFF, survives Railway empty-string). OFF ⇒ HR flags fall through to Stage-1 `psychotic_referral` path, byte-identical to current master.
- **Ratified route order** `crisis > medical > hr`. HR terminal routes AFTER medical, AFTER crisis. SI/crisis always wins (safety_check → `_route_after_safety` returns crisis first).
- **Deterministic only on the HR path** — no `evaluate_completion_criteria`/LLM call. The node must not be added to `_LLM_CRITERIA_SKILLS` and must not call the classifier.
- **Scope guard by construction:** "one question, asked at most twice; two branch evaluations, ever." A third question must be unrepresentable (the marker has exactly {await_distress, reask}; after reask any input terminates).
- **SG-2 channel discipline:** the new persistence marker is a DECLARED SageState channel, reset on terminal delivery AND cleared by crisis_response, verified by `scripts/check_state_channels.py`.
- Assert on routing state / branch, never on copy strings.

## File Structure
- `src/sage_poc/config.py` — `SAGE_HIGH_RISK_TERMINAL` flag + `HR_DISTRESS_QUESTION`, `HR_SUPPORTIVE_MESSAGE`, `HR_REDIRECT_HIGHER`, `HR_REDIRECT_LOWER`, `HR_REASK` copy constants.
- `src/sage_poc/safety/hr_distress.py` (new) — deterministic parser + branch resolver.
- `src/sage_poc/nodes/high_risk_response.py` (new) — the 2-step terminal node (medical_response-patterned).
- `src/sage_poc/state.py` — declare `hr_terminal_step` + `hr_escalate_regardless` channels (both reset on terminal delivery AND cleared by crisis_response — SG-2).
- `src/sage_poc/graph.py` — `_route_after_safety` entry + re-entry branch; `add_node`/edge; crisis_response clears `hr_terminal_step`.
- `src/sage_poc/audit.py` — conditional `hr_distress_score`/`hr_branch` columns.
- `migrations/013_add_hr_terminal_to_session_audit.sql` (+ claim 013 in migrations/MIGRATIONS.md).
- `docs/SageAI_architecture_current.md` — node-catalogue entry for `high_risk_response` (+ close the missing `medical_response` entry); node count 9→11. Proposed addition, human sign-off (living ref).
- Tests: `tests/test_hr_distress_parse.py`, `tests/test_hr_terminal.py` (new).

---

## Task 1: Deterministic distress parser + branch resolver

**Files:** Create `src/sage_poc/safety/hr_distress.py`; Test `tests/test_hr_distress_parse.py`.

**Interfaces — Produces:**
- `parse_distress(text: str) -> DistressParse` (dataclass: `score: int|None`, `risk_language: bool`). **STRICT numeric parse (Finding 2):** only scale-forms yield a score; numbers embedded in content sentences do NOT parse (they fall through to re-ask, which is safe because the default is fail-to-higher).
- `mania_behavior_underway(text: str) -> bool` **(Finding 1):** true if a §3 "risky behavior already underway" mania phrase fired — the spending/risk-taking subset of CF-007 ("i've been spending loads of money", "i'm taking huge risks"). Phrase-class, same discipline as the CF rules.
- `resolve_hr_branch(parse, *, is_reask, escalate_regardless) -> str` → `"higher"` | `"lower"` | `"reask"`.

**Branch condition (Finding 1 — §3 is a conjunction of evidence types, not a score cutoff):**
`higher` if **`parse.risk_language` OR `escalate_regardless` (mania behavior-underway) OR (`parse.score is not None` and `parse.score >= HR_HIGH_FLOOR`)**. `lower` only if a score is present AND below the floor AND neither risk nor behavior-underway (the doc's "lower distress, no immediate danger indicated" — BOTH conditions). No score & not is_reask → `reask`. No score & is_reask → `higher` (fail-to-higher).

- [ ] **Step 1: Write failing tests.**
  - **Must-PARSE (score):** "7"→7, "a 7"→7, "maybe a seven"→7, "7/10"→7, "7 out of 10"→7, "0"→0, "10"→10.
  - **Must-NOT-PARSE (Finding 2 — deterministic dead-leg-to-ER controls, score stays None):** "I haven't slept for 4 days", "there are 3 of them outside", "I've spent 10 thousand", "15" (out of range). These fall through — and note two of them are ALSO caught by the risk/behavior screens below (which run first), so they route `higher`, never `lower`.
  - **risk_language=True:** "they're outside right now", "I can't stay here", "I'm not safe".
  - **mania_behavior_underway=True (Finding 1):** "I've been spending loads of money", "I'm taking huge risks". And **mood-only mania is False:** "I feel amazing", "I don't need sleep" → `mania_behavior_underway=False` (they don't escalate on their own).
  - **Non-answer:** "who told you that", "the voices are loud" → `score=None, risk_language=False, mania_behavior_underway=False`.
  - **Branch resolver:** the critical case — `score=2, escalate_regardless=True` (manic user reports low distress while spending) → **"higher"** (NOT "lower"); `score=2, all False` → "lower"; `risk_language=True` → "higher" regardless of is_reask; `score None, not is_reask` → "reask"; `score None, is_reask` → "higher".

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement.** **Strict numeric (Finding 2):** parse a score ONLY from these forms — bare number as (near-)whole reply, "N/10", "N out of 10", "(maybe )(a )N", "(a )<verbal-number>". A digit adjacent to a content noun (days/people/them/thousand/dollars/etc.) or inside a longer content clause does NOT parse. `HR_HIGH_FLOOR` = 7 (config; clinician-confirmed, packet). `mania_behavior_underway`: substring phrase-class over the spending/risk-taking CF-007 subset. `risk_language`: threat/agitation/danger phrase-class. Verbal-high terms ("terrible/unbearable/worst") → conservative, map to a high score or risk. Document every choice inline; when unsure, DON'T parse (fail-to-higher covers it).

- [ ] **Step 4: Run — expect PASS.**  - [ ] **Step 5: Commit** `feat(hr): strict distress parser + mania-behavior escalation + branch resolver`.

---

## Task 2: Config flag + fixed copy

**Files:** Modify `src/sage_poc/config.py`; Test in `tests/test_hr_terminal.py` (copy-presence + flag default).

- [ ] **Step 1: Write failing test** — `config.HIGH_RISK_TERMINAL_ENABLED` defaults False; the 5 copy constants exist and contain the §HR verbatim anchors (distress question contains "0 to 10"; higher-redirect assembled from `select_crisis_resources`/999; lower-redirect contains "doctor or mental health professional"). Assert on the config values (this is config data, not prose-in-code).
- [ ] **Step 2: Run — expect FAIL.**
- [ ] **Step 3: Implement.** `HIGH_RISK_TERMINAL_ENABLED` via the strict idiom (mirror `ROUTE_PRECEDENCE_ENABLED` at config.py:170-178). Copy constants = §HR verbatim (spec "Fixed copy"). Higher-redirect composes `select_crisis_resources()` output (999/ER-lead); lower-redirect uses the see-a-doctor text + same UAE resources.
- [ ] **Step 4: Run — expect PASS.**  - [ ] **Step 5: Commit** `feat(hr): HIGH_RISK_TERMINAL flag + §HR fixed copy`.

---

## Task 3: State channel + the high_risk_response node

**Files:** Modify `src/sage_poc/state.py` (declare `hr_terminal_step: Optional[str]` AND `hr_escalate_regardless: bool` — Finding 1); Create `src/sage_poc/nodes/high_risk_response.py`; Test `tests/test_hr_terminal.py`.

**Interfaces — Consumes:** `hr_distress.parse_distress`/`resolve_hr_branch`/`mania_behavior_underway`, config copy, `select_crisis_resources`, `write_session_audit`. **Produces:** `high_risk_response_node(state) -> dict`.

- [ ] **Step 1: Write failing node tests** (call the node directly with constructed state):
  - `hr_terminal_step=None` (entry): returns the distress question, sets `hr_terminal_step="await_distress"`, clears `active_skill_id`/`active_step_id`/`offered_skill_ids`, `gate_path="high_risk"`, audit fields present. At entry it computes `mania_behavior_underway(message_en)` and persists `hr_escalate_regardless`.
  - **Finding 1 case:** entry on "I've been spending loads of money and I feel unstoppable" → `hr_escalate_regardless=True` persisted; then `="await_distress"` + reply **"2"** → **higher** redirect (mania behavior escalates regardless of the low score), `hr_branch="higher"`, NOT "lower".
  - `hr_terminal_step="await_distress"` + reply "4" (no escalate_regardless) → returns supportive message + lower redirect, `hr_terminal_step=None`, `hr_branch="lower"`, `hr_distress_score=4`. (Boundary: "7" → **higher**, since `HR_HIGH_FLOOR=7` is inclusive — add that as an explicit boundary test.)
  - `="await_distress"` + reply "9" → higher redirect, `hr_branch="higher"`.
  - `="await_distress"` + reply "they're outside right now" → higher redirect (no re-ask), `hr_branch="higher"`.
  - `="await_distress"` + reply "who told you that" (non-answer) → re-ask copy, `hr_terminal_step="reask"`.
  - `="reask"` + reply "still nothing" (non-answer) → higher redirect (fail-to-higher), `hr_terminal_step=None`, `hr_branch="higher"`.
  - `="reask"` + reply "3" → lower redirect, cleared.
- [ ] **Step 2: Run — expect FAIL.**
- [ ] **Step 3: Implement**, cloning `medical_response.py` structure (full-turn latency from `turn_started_at`; own `write_session_audit` via `asyncio.create_task` with done-callback; entry-clear of skill fields; return `response`/`response_en`, `gate_path="high_risk"`, `path`). At entry, compute `mania_behavior_underway(state["message_en"])` → persist `hr_escalate_regardless`; on the branch turn, pass `escalate_regardless=state.get("hr_escalate_regardless", False)` to `resolve_hr_branch`, and clear it (→ False) with `hr_terminal_step` on terminal delivery. Declare BOTH `hr_terminal_step` and `hr_escalate_regardless` in `state.py` next to `active_step_id`. The node is pure-deterministic — no LLM call.
- [ ] **Step 4: Run — expect PASS + `python scripts/check_state_channels.py` clean** (new channel declared).
- [ ] **Step 5: Commit** `feat(hr): high_risk_response 2-step terminal node`.

---

## Task 4: Routing (entry + re-entry, gated) + crisis clears the marker

**Files:** Modify `src/sage_poc/graph.py`; Test `tests/test_hr_terminal.py` (full-graph).

- [ ] **Step 1: Write failing full-graph tests** (mirror `tests/test_medical_redflag_guard.py` for LLM-stubbing):
  - flag ON + HR flag (turn 1) → routes to `high_risk_response`, asks distress; turn 2 "8" → higher branch delivered; assert on `gate_path`/`hr_branch`, not `active_skill_id`.
  - **Finding 3 — the 3-turn crisis-clears-state test (REQUIRED, blocks flip; the active-resumable bug's 4th appearance — structural, not a review catch):** turn 1 HR entry (asks distress) → turn 2 SI reply ("nothing feels real and I want to die") → `gate_path=="crisis"` (crisis pierces by graph shape) → turn 3 benign message asserts the terminal does NOT resume the distress question (no HR re-entry). This proves both `hr_terminal_step` AND `hr_escalate_regardless` were cleared when crisis fired — the stateful-thing-leaves-a-resumable-marker bug must be killed on introduction, not discovered later.
  - flag OFF + HR flag → routes to Stage-1 `psychotic_referral` (byte-identical), never to `high_risk_response`.
  - in-progress skill + HR fires (flag ON) → skill cleared on entry.
  - scope guard: reask then non-answer → higher + terminal; a would-be 3rd turn (new message after terminal) does NOT re-enter HR.
- [ ] **Step 2: Run — expect FAIL.**
- [ ] **Step 3: Implement** in `_route_after_safety` (after the crisis and medical branches, per ratified order): entry `if _cfg.HIGH_RISK_TERMINAL_ENABLED and hr_disclosure_present(...) : return "high_risk"`; re-entry `if state.get("hr_terminal_step"): return "high_risk"` (also gated on flag; placed so crisis still returns first). `add_node("high_risk_response", ...)`, add `"high_risk"` to the safety conditional-edge map, `add_edge("high_risk_response", END)`. In `_crisis_response_node`, add `"hr_terminal_step": None` AND `"hr_escalate_regardless": False` to its cleared fields (SG-2 reset so a pierced protocol leaves no stale marker on EITHER channel — Finding 3).
- [ ] **Step 4: Run — expect PASS.** Regression: `tests/test_routing.py tests/test_medical_redflag_guard.py tests/test_hr_routing.py tests/test_skill_select_psychotic.py` green; `check_state_channels.py` clean.
- [ ] **Step 5: Commit** `feat(hr): route high_risk_response (entry+re-entry, gated); crisis clears marker`.

---

## Task 5: Audit migration + arch-doc catalogue

**Files:** Create `migrations/013_add_hr_terminal_to_session_audit.sql` (+ MIGRATIONS.md claim); Modify `src/sage_poc/audit.py`; Modify `docs/SageAI_architecture_current.md`.

- [ ] **Step 1: Write failing audit test** — when `state.get("hr_branch")` set, `_build_session_audit_row` adds `hr_distress_score`, `hr_branch`; when absent, row is byte-identical to before (conditional block pattern like medical_flags at audit.py:163-169).
- [ ] **Step 2: Run — expect FAIL.**
- [ ] **Step 3: Implement.** Migration 013: `ADD COLUMN IF NOT EXISTS hr_distress_score int; ... hr_branch text;` (header notes it is the deploy gate before the flag flip). Conditional audit block.

  **Arch doc (§2.1/§2.2) — introduce the SAFETY-EXIT TERMINAL CLASS, do NOT just bump a node count.** State the class CONTRACT once: routed from `_route_after_safety`; goes straight to `END`; bypasses `output_gate`; writes its own audit row; clears skill state (`active_skill_id`/`active_step_id`/`offered_skill_ids`) on entry; uses fixed/templated (deterministic) copy; holds a precedence rank (`crisis > medical > hr`). List its three members against that contract: `crisis_response`, `medical_response`, `high_risk_response`. Distinguish it from the ~8-stage processing pipeline (which exits via `output_gate`). Future safety terminals build against this documented contract, not by imitation of the nearest neighbour — that is the difference between a pattern and a class.

  **BOUNDARY — state explicitly (do not let the class blur into an exemption):** the `output_gate` bypass is **licensed by the copy being deterministic/templated, NOT by being safety-related.** Any future terminal whose response is LLM-rendered does NOT inherit the bypass — it goes through the gate. The bypass is a property of templated copy.

  **Log the altitude correction (conformance):** Stage 1 routed HR at the *post-intent* altitude (`_route_after_intent` → skill layer) — a temporary non-conformance, since a protocol the doc ranks *with crisis* was sitting below `intent_route`, so intent classification ran on HR turns it had no business classifying. Stage 2 doesn't just upgrade the terminal, it **corrects HR's rank** to the pre-intent safety-exit altitude. Record this as a line in the conformance matrix.

  Mark all arch-doc edits as proposed additions pending human sign-off (living ref).
- [ ] **Step 4: Run — expect PASS.**
- [ ] **Step 5: Commit** `feat(hr): 013 audit columns + node-catalogue entry`.

---

## Post-tasks (controller)
- Final whole-branch review (most-capable model): verify OFF byte-identical, crisis-pierce, scope-guard-by-construction, deterministic-no-LLM, copy verbatim, channel reset.
- Clinician packet already carries the non-answer default + `HR_HIGH_FLOOR` (the score threshold) — surface the chosen floor (default 7) for ratification.
- Flip: same clinician ratification event; `SAGE_HIGH_RISK_TERMINAL=true` rides the Stage-1 flip PR or a follow-up, with migration 013 applied first (deploy gate) + live post-flip verification.
