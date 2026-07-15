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
- `src/sage_poc/state.py` — declare `hr_terminal_step` channel.
- `src/sage_poc/graph.py` — `_route_after_safety` entry + re-entry branch; `add_node`/edge; crisis_response clears `hr_terminal_step`.
- `src/sage_poc/audit.py` — conditional `hr_distress_score`/`hr_branch` columns.
- `migrations/013_add_hr_terminal_to_session_audit.sql` (+ claim 013 in migrations/MIGRATIONS.md).
- `docs/SageAI_architecture_current.md` — node-catalogue entry for `high_risk_response` (+ close the missing `medical_response` entry); node count 9→11. Proposed addition, human sign-off (living ref).
- Tests: `tests/test_hr_distress_parse.py`, `tests/test_hr_terminal.py` (new).

---

## Task 1: Deterministic distress parser + branch resolver

**Files:** Create `src/sage_poc/safety/hr_distress.py`; Test `tests/test_hr_distress_parse.py`.

**Interfaces — Produces:**
- `parse_distress(text: str) -> DistressParse` (dataclass: `score: int|None`, `risk_language: bool`).
- `resolve_hr_branch(parse: DistressParse, *, is_reask: bool) -> str` returning `"higher"` | `"lower"` | `"reask"`.

- [ ] **Step 1: Write failing tests.** Numeric: "7"→7, "an 8"→8, "it's like a 9 honestly"→9, "0"→0, "10"→10, ">10"/"15"→None (out of range). Verbal-high: "really bad", "terrible", "unbearable", "the worst" → risk/high. Verbal-low: "not too bad", "a little", "manageable" → low-ish (score None but no risk). Risk-language: "they're outside right now", "I can't stay here", "I'm not safe", mania-risk "I've been spending everything" → `risk_language=True`. Non-answer: "who told you that", "the voices are loud" (content, no score, no risk) → `score=None, risk_language=False`. Branch resolver: `risk_language=True` → "higher" (regardless of is_reask); `score>=HR_HIGH_FLOOR` → "higher"; `score<HR_HIGH_FLOOR` (and not None) → "lower"; `score None & not risk & not is_reask` → "reask"; `score None & not risk & is_reask` → "higher" (fail-to-higher default).

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement.** Numeric: `re.search(r'\b(10|[0-9])\b', text)` with verbal-number map ("zero".."ten", "a/an <n>"). `HR_HIGH_FLOOR` (propose 7, confirm with clinician — put in the packet's tier discussion, default 7). Risk-language: a phrase-class list (threat/agitation/danger/mania-risk), same discipline as CF rules, lowercased substring. Verbal-high terms map to `risk_language=True` OR a high sentinel — keep it conservative (map "terrible/unbearable/worst" to higher). Document every choice inline.

- [ ] **Step 4: Run — expect PASS.**  - [ ] **Step 5: Commit** `feat(hr): deterministic distress parser + branch resolver`.

---

## Task 2: Config flag + fixed copy

**Files:** Modify `src/sage_poc/config.py`; Test in `tests/test_hr_terminal.py` (copy-presence + flag default).

- [ ] **Step 1: Write failing test** — `config.HIGH_RISK_TERMINAL_ENABLED` defaults False; the 5 copy constants exist and contain the §HR verbatim anchors (distress question contains "0 to 10"; higher-redirect assembled from `select_crisis_resources`/999; lower-redirect contains "doctor or mental health professional"). Assert on the config values (this is config data, not prose-in-code).
- [ ] **Step 2: Run — expect FAIL.**
- [ ] **Step 3: Implement.** `HIGH_RISK_TERMINAL_ENABLED` via the strict idiom (mirror `ROUTE_PRECEDENCE_ENABLED` at config.py:170-178). Copy constants = §HR verbatim (spec "Fixed copy"). Higher-redirect composes `select_crisis_resources()` output (999/ER-lead); lower-redirect uses the see-a-doctor text + same UAE resources.
- [ ] **Step 4: Run — expect PASS.**  - [ ] **Step 5: Commit** `feat(hr): HIGH_RISK_TERMINAL flag + §HR fixed copy`.

---

## Task 3: State channel + the high_risk_response node

**Files:** Modify `src/sage_poc/state.py` (declare `hr_terminal_step: Optional[str]`); Create `src/sage_poc/nodes/high_risk_response.py`; Test `tests/test_hr_terminal.py`.

**Interfaces — Consumes:** `hr_distress.parse_distress`/`resolve_hr_branch`, config copy, `select_crisis_resources`, `write_session_audit`. **Produces:** `high_risk_response_node(state) -> dict`.

- [ ] **Step 1: Write failing node tests** (call the node directly with constructed state):
  - `hr_terminal_step=None` (entry): returns the distress question, sets `hr_terminal_step="await_distress"`, clears `active_skill_id`/`active_step_id`/`offered_skill_ids`, `gate_path="high_risk"`, audit fields present.
  - `hr_terminal_step="await_distress"` + reply "7" → returns supportive message + lower redirect, `hr_terminal_step=None`, `hr_branch="lower"`, `hr_distress_score=7`.
  - `="await_distress"` + reply "9" → higher redirect, `hr_branch="higher"`.
  - `="await_distress"` + reply "they're outside right now" → higher redirect (no re-ask), `hr_branch="higher"`.
  - `="await_distress"` + reply "who told you that" (non-answer) → re-ask copy, `hr_terminal_step="reask"`.
  - `="reask"` + reply "still nothing" (non-answer) → higher redirect (fail-to-higher), `hr_terminal_step=None`, `hr_branch="higher"`.
  - `="reask"` + reply "3" → lower redirect, cleared.
- [ ] **Step 2: Run — expect FAIL.**
- [ ] **Step 3: Implement**, cloning `medical_response.py` structure (full-turn latency from `turn_started_at`; own `write_session_audit` via `asyncio.create_task` with done-callback; entry-clear of skill fields; return `response`/`response_en`, `gate_path="high_risk"`, `path`). Declare `hr_terminal_step` in `state.py` next to `active_step_id`. The node is pure-deterministic — no LLM call.
- [ ] **Step 4: Run — expect PASS + `python scripts/check_state_channels.py` clean** (new channel declared).
- [ ] **Step 5: Commit** `feat(hr): high_risk_response 2-step terminal node`.

---

## Task 4: Routing (entry + re-entry, gated) + crisis clears the marker

**Files:** Modify `src/sage_poc/graph.py`; Test `tests/test_hr_terminal.py` (full-graph).

- [ ] **Step 1: Write failing full-graph tests** (mirror `tests/test_medical_redflag_guard.py` for LLM-stubbing):
  - flag ON + HR flag (turn 1) → routes to `high_risk_response`, asks distress; turn 2 "8" → higher branch delivered; assert on `gate_path`/`hr_branch`, not `active_skill_id`.
  - flag ON, mid-protocol SI on turn 2 ("nothing feels real and I want to die") → `gate_path=="crisis"` (crisis pierces), and `hr_terminal_step` cleared afterward.
  - flag OFF + HR flag → routes to Stage-1 `psychotic_referral` (byte-identical), never to `high_risk_response`.
  - in-progress skill + HR fires (flag ON) → skill cleared on entry.
  - scope guard: reask then non-answer → higher + terminal; a would-be 3rd turn (new message after terminal) does NOT re-enter HR.
- [ ] **Step 2: Run — expect FAIL.**
- [ ] **Step 3: Implement** in `_route_after_safety` (after the crisis and medical branches, per ratified order): entry `if _cfg.HIGH_RISK_TERMINAL_ENABLED and hr_disclosure_present(...) : return "high_risk"`; re-entry `if state.get("hr_terminal_step"): return "high_risk"` (also gated on flag; placed so crisis still returns first). `add_node("high_risk_response", ...)`, add `"high_risk"` to the safety conditional-edge map, `add_edge("high_risk_response", END)`. In `_crisis_response_node`, add `"hr_terminal_step": None` to its cleared fields (SG-2 reset so a pierced protocol leaves no stale marker).
- [ ] **Step 4: Run — expect PASS.** Regression: `tests/test_routing.py tests/test_medical_redflag_guard.py tests/test_hr_routing.py tests/test_skill_select_psychotic.py` green; `check_state_channels.py` clean.
- [ ] **Step 5: Commit** `feat(hr): route high_risk_response (entry+re-entry, gated); crisis clears marker`.

---

## Task 5: Audit migration + arch-doc catalogue

**Files:** Create `migrations/013_add_hr_terminal_to_session_audit.sql` (+ MIGRATIONS.md claim); Modify `src/sage_poc/audit.py`; Modify `docs/SageAI_architecture_current.md`.

- [ ] **Step 1: Write failing audit test** — when `state.get("hr_branch")` set, `_build_session_audit_row` adds `hr_distress_score`, `hr_branch`; when absent, row is byte-identical to before (conditional block pattern like medical_flags at audit.py:163-169).
- [ ] **Step 2: Run — expect FAIL.**
- [ ] **Step 3: Implement.** Migration 013: `ADD COLUMN IF NOT EXISTS hr_distress_score int; ... hr_branch text;` (header notes it is the deploy gate before the flag flip). Conditional audit block. Arch doc: add `high_risk_response` to §2.1 node catalogue (4th safety terminal; medical_response-patterned; 2-step; own audit; bypasses output_gate), close the missing `medical_response` entry, bump node count. Mark as proposed addition pending human sign-off.
- [ ] **Step 4: Run — expect PASS.**
- [ ] **Step 5: Commit** `feat(hr): 013 audit columns + node-catalogue entry`.

---

## Post-tasks (controller)
- Final whole-branch review (most-capable model): verify OFF byte-identical, crisis-pierce, scope-guard-by-construction, deterministic-no-LLM, copy verbatim, channel reset.
- Clinician packet already carries the non-answer default + `HR_HIGH_FLOOR` (the score threshold) — surface the chosen floor (default 7) for ratification.
- Flip: same clinician ratification event; `SAGE_HIGH_RISK_TERMINAL=true` rides the Stage-1 flip PR or a follow-up, with migration 013 applied first (deploy gate) + live post-flip verification.
