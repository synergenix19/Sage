# Clinical Flag Lifecycle Design Document

**Date:** 2026-05-27  
**Status:** DRAFT — Ready for clinical review; Sprint 1 implementation proceeds with safe defaults  
**Gate:** Clinical sign-off changes config values only — no code changes, no migrations after Sprint 1 ships  
**Authors:** Engineering  
**Clinical review required from:** Both clinical advisors  

---

## 1. Problem Statement

A 2026-05-27 code audit (see `docs/superpowers/audits/2026-05-27-v7-gitex-content-sprint-results.md`) identified two compounding bugs:

**X1 — Skill executor permanently blocks on clinical flags.**  
`check_escalation()` in `nodes/skill_executor.py:51` fires L2 whenever `clinical_flags` is non-empty. Since flags accumulate across turns via set-union, once any flag is set (e.g., `medication_mention` from a passing mention), every subsequent skill execution turn triggers L2. L2 holds `active_step_id` at the same step — the skill never advances. A user who mentions medication in turn 3 then tries a breathing exercise in turn 7 is permanently stuck at step 1 of that skill for the rest of the session.

**M1 — `escalating_distress` never clears.**  
`escalating_distress` is added to `clinical_flags` via set-union with the persisted flag set. Once added, it is never removed, even if distress drops to baseline. Combined with X1: a user who experiences three consecutive high-intensity turns (intensity ≥ 6) is permanently locked out of all skills — precisely when structured support is most needed.

Both bugs trace to a single root cause: **the v7 spec defines clinical flags as prompt framing modifiers but the implementation treats them as skill delivery gates.** The spec (v7 §9.3) defines L2 as "clinician review within 24 hours" — a background action, silent to the user. The current code interprets L2 as "halt therapeutic delivery indefinitely," which is the opposite of the clinical intent.

**This design document formalises the clinical flag lifecycle model that the v7 spec left implicit, so the implementation can be corrected.**

---

## 2. Clinical Flag Taxonomy

### 2.1 Category A — Session Facts (Persistent, Non-Blocking)

These flags are set when the user discloses a specific clinical context. Once set, they persist for the full session and inform prompt framing. They do **not** gate skill delivery. The user still receives skills; the flags change *how* the skill is delivered (via L5 user context block and Rules Service clinical adaptations PI-CF-001 through PI-CF-005).

| Flag | Trigger | Prompt effect | Persists across sessions? |
|---|---|---|---|
| `substance_use` | User discloses substance use | PI-CF-001: MI approach, UAE legal framing | **Clinical judgment** — see §3.1 |
| `trauma_indicator` | User discloses trauma history | PI-CF-002: trauma-sensitive, no probing | **Clinical judgment** — see §3.1 |
| `eating_concern` | User discloses eating concern | PI-CF-003: body-neutral language | **Clinical judgment** — see §3.1 |
| `medication_mention` | User mentions medication | PI-CF-004: no dosage/cessation advice | **No** — informational disclosure, session only |
| `domestic_situation` | User discloses domestic safety concern | PI-CF-005: safety-first, UAE resources | **Clinical judgment** — see §3.1 |

**Design rule:** Category A flags MUST NOT appear in `check_escalation()` logic. Their effect is entirely in the prompt layer (L5, Rules Service), not the executor.

> **Note — `third_party_si` is not a Category A flag.** A user expressing concern about someone else's safety is detected via rule SK-EN-004 with action type `third_party_crisis` (not `clinical_flag`). It is routed as a separate boolean `third_party_crisis: bool` in state, never enters `clinical_flags`, and is therefore outside this lifecycle entirely. See §2.4.

### 2.2 Category B — Computed Signals (Derived, Non-Persistent)

These are derived each turn from raw turn-level data. They are never stored in the persisted flag set. Functionally analogous to a database view (re-evaluated on every read) rather than a stored column.

| Signal | How derived | Effect |
|---|---|---|
| `escalating_distress` | `len(trajectory) >= 3 AND all(s >= 6 for s in trajectory[-3:])` | L5 descriptor, L2 `validate_only` step policy — NOT a `clinical_flags` entry |

**Design rule:** `escalating_distress` MUST NOT be added to `clinical_flags`. It must be passed as a separate field (`distress_escalating: bool`) or derived inline when building the L2/L5 context. It is not a fact about the user; it is a turn-level heuristic.

### 2.3 Category C — Escalation Signals (Turn-Level, Executor-Only)

These signals are evaluated within the skill executor to decide whether step policy should be modified or review should be triggered. They do NOT persist to `clinical_flags`.

| Signal | Source | Effect |
|---|---|---|
| `re_escalation_detected` | `s7_result == "NEW_CRISIS"` from current turn's safety_check | Exit post_crisis_check_in, re-enter crisis protocol |
| `user_stop_request` | L1_EXIT_PHRASES match in current turn's `message_en` | Exit skill gracefully (L1 escalation in `check_escalation()`) |
| `resistance_score` | Falcon-3B 1–10 classification via Rules Service prompt (see §6) | Feed `resistance_history`; step policy rule 3 fires when `all(r > 6 for r in resistance_history[-3:])` |

> **Note — `user_stop_request` scope:** L1 exit detection lives in `check_escalation()` and returns before `evaluate_step_policy()` is called. The `user_stop_request` parameter in `evaluate_step_policy()` exists solely for `post_crisis_check_in` step policy rules that reference it as a Category C signal for that skill's internal logic. General skill exit is always L1 in `check_escalation()`, never a step policy rule.

**Design rule:** Category C signals are computed from current-turn state inside `skill_executor_node` or `evaluate_step_policy()`. They are never stored in state between turns, with the sole exception of `resistance_history` (see §5.1).

### 2.4 `third_party_crisis` — Separate Detection Path (Not in Clinical Flags Lifecycle)

A user reporting concern about someone else's safety ("my friend wants to die") is detected by rule SK-EN-004 in `crisis_keywords.json` with action type `third_party_crisis`, flag_id `third_party_si`. This is architecturally distinct from a `clinical_flag` type action.

**In `safety_check_node`:** `third_party_si` is captured in `third_party_flags` (not `new_clinical_flags`), stored as `third_party_crisis: bool` in state, and never enters `clinical_flags`. The retired prompt injection rule PI-TP-001 (`third_party_guidance.json`) had a `flag_present` trigger on `third_party_si` in `clinical_flags`; because `third_party_si` was never routed into `clinical_flags`, this rule was structurally unreachable from the moment SK-EN-004 was written. It is correctly marked `active: false`.

**Prompt effect:** `composer.py` injects third-party guidance directly when `state.get("third_party_crisis")` is `True` (lines 400–407), bypassing the `_FLAG_DESCRIPTIONS` / L5 pathway entirely. The `_FLAG_DESCRIPTIONS["third_party_si"]` entry at `composer.py:157` is dead code and should be removed as part of Sprint 1 cleanup.

**Clinical note for awareness (does not block Sprint 1):** The current architecture treats a third-party report purely as a response-mode switch — provide resources for the friend, do not apply crisis protocol to the current user. It does not record anything about the current user's state. A user reporting third-party SI may themselves be experiencing secondary trauma, acting as a proxy reporter, or be in a caregiver role affecting their mental health. If the clinical team wants to track "this user has reported third-party SI concern" as a cross-session signal, that requires a new Category A flag (CF-006, type `clinical_flag`) — a separate clinical decision, not a reuse of SK-EN-004. This is a clinical design question; engineering is not recommending it for Sprint 1.

---

## 3. Configuration, Clinical Decisions, and Implementation Approach

Clinical decisions in this section are implemented as configuration, not as code branches. The v7 architecture puts clinical decisions in the Rules Service precisely so clinicians can change them without engineering. The full persistence machinery and audit infrastructure ship in Sprint 1 with safe defaults. When the clinical team signs off, they flip config values — no migrations, no sprint planning, no code changes.

### 3.1 Cross-Session Persistence of Category A Flags

**Implementation: ships in Sprint 1 with all flags defaulting to session-scoped.**

`flag_lifecycle_config.json` (new file, see §9) controls per-flag cross-session persistence:

```json
{
  "cross_session_persistence": {
    "substance_use": false,
    "trauma_indicator": false,
    "eating_concern": false,
    "medication_mention": false,
    "domestic_situation": false
  }
}
```

The full persistence machinery ships now regardless of these values:
- **New column:** `persisted_clinical_flags JSONB DEFAULT '[]'` on `user_therapeutic_profiles` (migration in Sprint 1)
- **Write path:** end-of-session summarizer (`POST /summarize`) checks `flag_lifecycle_config.cross_session_persistence[flag_id]` before writing each flag to the column. When all values are `false`, nothing is written.
- **Read path:** `server.py` loads `persisted_clinical_flags` from Supabase at session start (alongside `therapeutic_profile`) and pre-populates `clinical_flags`. When the column is empty, `clinical_flags` starts as `[]` — functionally identical to session-scoped behavior.

With all defaults `false`, the system behaves as session-scoped. The clinical team flips individual flags to `true` whenever they're ready. No code changes needed.

**Architecture context for the clinical team:** `clinical_flags` is scoped to the LangGraph checkpoint, which is per-session (keyed by `session_id`). A new session has an empty checkpoint — `clinical_flags` starts as `[]` unless explicitly hydrated via `persisted_clinical_flags`. The therapeutic profile (`user_therapeutic_profiles` in Supabase) is the only store that survives across sessions and is loaded at session start.

**Clinical sign-off needed:** Confirm the default (`false` for all flags) is clinically safe as the starting configuration. When ready to enable persistence for any flag (e.g., `trauma_indicator`), edit the JSON and publish — no engineering involvement.

| Flag | Default | Notes for clinical review |
|---|---|---|
| `substance_use` | `false` | User in recovery — context highly relevant across sessions |
| `trauma_indicator` | `false` | Trauma history doesn't resolve; relevant across sessions |
| `eating_concern` | `false` | Ongoing condition vs. discrete disclosure |
| `medication_mention` | `false` | Informational, changes frequently — session-only recommended permanently |
| `domestic_situation` | `false` | Safety concern — may escalate or resolve between sessions |

### 3.2 Flag Immutability Within a Session

**Implementation: ships in Sprint 1 with immutability enabled by default.**

Same config file:

```json
{
  "flag_immutable_within_session": true
}
```

`safety_check_node` checks this value before removing any flag from `clinical_flags`. When `true` (the default), flags set within a session are never cleared — the conservative safe default. The `clear_flag` action path in the rules engine is not built yet; retraction logic is additive and will be authored by the clinical team in the Rules Service (as specific keyword patterns triggering `clear_flag` actions) only if the clinical team changes this to `false`.

**Clinical sign-off needed:** Confirm `true` is the correct default. If the clinical team ever wants retraction enabled for specific flags (e.g., a user who clarifies a domestic situation concern was historical), they set this to `false` and the engineering team adds the retraction patterns — that is the only code change required.

### 3.3 L2 Escalation Trigger Scope — Not Configurable

This is the X1 bug fix. The current behavior (L2 fires on any non-empty accumulated `clinical_flags`) is broken. The fix (`new_clinical_flags_turn` delta, first-detection only) is not a clinical preference — it is the correct implementation of the v7 spec definition of L2. This ships as specified in §5. It is not a config toggle.

If the clinical team wants re-triggering in specific clinical scenarios (e.g., flag detected on turn 3, user discloses escalation on turn 8), the `flag_for_review` tool already available to the LLM in freeflow is the correct mechanism — it gives the LLM agency to escalate contextually and does not require modifying `check_escalation()`.

### 3.4 Clinician Review Queue — Append Strategy Ships in Sprint 1

**Implementation: append strategy ships in Sprint 1. No config needed.**

The append strategy is strictly a superset of the current behavior — it never loses data. The `ON CONFLICT (session_id) DO UPDATE` clause is updated to append each L2 event to a `flags_timeline JSONB DEFAULT '[]'` array on the row. One row per session is preserved for dashboard simplicity; the full event timeline is preserved for PDPL audit compliance (v7 §13).

If the dashboard query currently reads `reason`, it continues to work by reading `flags_timeline[-1].reason` for the most recent event. No dashboard changes required.

Migration runs in Sprint 1: add `flags_timeline JSONB DEFAULT '[]'` to `clinician_review_queue`, update the `ON CONFLICT` clause in `notification.py`.

---

## 4. Proposed L2 Escalation Semantics

### 4.1 Current (Broken) Behavior

```
L2 fires → active_step_id held at current step → evaluate_step_policy skipped
→ user stuck at same step forever → skill delivery halted
```

### 4.2 Proposed Behavior

```
L2 fires (new flag detected this turn only)
→ write to clinician_review_queue (background, silent to user)
→ evaluate_step_policy CONTINUES NORMALLY
→ active_step_id advances as usual
→ step_instruction unchanged (skill executes normally)
→ escalation_triggered set for audit logging only
```

The L2 escalation_matrix text in each skill JSON becomes the payload written to the review queue, not an instruction to the LLM. Example for `cbt_thought_record`:

```json
"L2": "Add clinician_review flag if trauma or substance mention detected"
```

This text should be the review reason written to the `clinician_review_queue` table, not injected into the prompt. The LLM prompt already has the correct clinical adaptation via PI-CF-001 through PI-CF-005.

### 4.3 Audit Trail

When L2 fires:
- `escalation_triggered: {"level": "L2", "reason": ..., "action": "clinician_review_queued"}` written to state for `output_gate` audit log
- `_log_clinical_review()` in `output_gate_node` fires (already exists — this is the mechanism); it calls `PostgresNotifier.notify_review_required()` which writes to `public.clinician_review_queue` in Supabase and fires `pg_notify("clinician_review", ...)` for real-time delivery
- No change to LLM prompt beyond what PI-CF rules already inject
- The `ON CONFLICT` clause in `notification.py` appends to `flags_timeline` (see §3.4 — this ships in Sprint 1)

---

## 5. State Changes Required

> **Escalation level map — where each level is handled:**
>
> | Level | Handler | Mechanism |
> |---|---|---|
> | L1 — user exit | `check_escalation()` in `skill_executor.py` | Early return before `evaluate_step_policy` |
> | L2 — clinical flag | `check_escalation()` + `output_gate_node` | Log to `clinician_review_queue`; step policy continues |
> | L3 — crisis signal | `_route_after_safety()` in `graph.py` | Graph routes directly to `crisis_response`; `skill_executor` is never called |
> | L4 — human handoff | Out of scope for Sprint 1 | See v7 §9.3; requires a session-level crisis event counter not yet in schema |
>
> **L3 is structurally unreachable from `check_escalation()`.** When `safety_check_node` returns `is_safe=False`, the graph edge at `graph.py:132–136` routes to `crisis_response` and terminates (`graph.add_edge("crisis_response", END)`). `skill_executor_node` is never invoked. `check_escalation()` therefore only ever encounters L1 and L2 situations.
>
> **L4** is out of scope for Sprint 1. Clinical reviewers should note: L4 trigger conditions per v7 §9.3 (user requests human handoff, active flag + distress, 3+ crises within 30 days) require a session-level crisis event counter that does not exist in the current schema.

### 5.1 New and Updated Fields in `SageState`

```python
# In state.py — add alongside clinical_flags

new_clinical_flags_turn: list[str]   # flags detected this turn only; reset by _build_state()
                                      # used by skill_executor check_escalation() instead of clinical_flags

resistance_history: list[int]         # rolling 3-turn buffer of Falcon-3B resistance scores (1–10)
                                      # persisted via LangGraph checkpoint across turns within a session
                                      # reset to [] at session start (new thread_id = empty checkpoint)

resistance_score: Optional[int]       # current turn's Falcon-3B resistance score; reset each turn in _build_state()
```

`new_clinical_flags_turn` and `resistance_score` must be declared in `_build_state()` with defaults of `[]` and `None` respectively. This collocates them with the M4 per-turn resets (`knowledge_abstain`, `knowledge_passages`, `knowledge_source`). `resistance_history` is intentionally absent from `_build_state()` — LangGraph checkpoint carries it across turns.

### 5.2 `safety_check_node` Return

Add `new_clinical_flags_turn` to the return dict (the already-computed `new_clinical_flags` local variable at `safety_check.py:100–102`).

### 5.3 `escalating_distress` Removal from `clinical_flags`

```python
# safety_check.py — replace line 148
persisted_non_computed = [f for f in state.get("clinical_flags", []) if f != "escalating_distress"]
all_clinical = list(set(new_clinical_flags + persisted_non_computed))
# escalating_distress is derived inline in _build_l5_user_context_block() from distress_trajectory
```

`escalating_distress` must NOT be in the persisted set. Derive it inline in `_build_l5_user_context_block()` from `distress_trajectory` if the L5 descriptor needs it.

### 5.4 `check_escalation()` — Complete Revised Signature

The full function must be shown here because the prior pseudocode omitted the L1 branch, creating a drop risk during implementation.

```python
# skill_executor.py
def check_escalation(message_en: str, new_clinical_flags_turn: list[str]) -> dict | None:
    """Evaluates escalation matrix before step_policy. Returns escalation dict or None.

    L1 and L2 only. L3 (crisis) is handled upstream by _route_after_safety in graph.py
    and never reaches this function. L4 (human handoff) is out of scope for Sprint 1.
    """
    message_lower = message_en.lower()

    # L1: user requests to stop — early return, step policy is skipped entirely
    if any(phrase in message_lower for phrase in L1_EXIT_PHRASES):
        return {
            "level": "L1",
            "reason": "User requested to stop the skill",
            "action": "exit_skill",
        }

    # L2: new clinical flag detected this turn only (not accumulated set)
    if new_clinical_flags_turn:
        return {
            "level": "L2",
            "reason": f"New clinical flags this turn: {', '.join(new_clinical_flags_turn)}",
            "action": "clinician_review_queued",
        }

    return None
```

Caller in `skill_executor_node`:
```python
escalation = check_escalation(
    message_en=state["message_en"],
    new_clinical_flags_turn=state.get("new_clinical_flags_turn", []),
)
```

### 5.5 L2 Branch in `skill_executor_node` — Corrected Control Flow

The prior pseudocode had two bugs: (1) no explicit `return` on the L1 path, making fall-through ambiguous; (2) a second `exit_skill` check after the L1 block that was either dead code or an accidental double-processing path. The corrected structure:

```python
if escalation:
    if escalation["action"] == "exit_skill":  # L1 only — returns unconditionally
        crisis_update = (
            {"crisis_state": "resolved"}
            if state.get("active_skill_id") == "post_crisis_check_in"
            else {}
        )
        return {
            **crisis_update,
            "escalation_triggered": escalation,
            "active_skill_id": None,
            "active_step_id": None,
            "gate_path": "standard",
        }
    # L2 only reaches here — L1 returned above
    # Write to audit trail; step policy continues normally below
    # (output_gate_node calls _log_clinical_review() which writes to clinician_review_queue)

# evaluate_step_policy runs for all non-exit escalations (L2) and no-escalation turns
result = await evaluate_step_policy(...)
```

---

## 6. Resistance Architecture — Full Falcon-3B Implementation

The prior §6 proposed a boolean POC heuristic (`engagement < 3`). This is rejected because:
1. Step policy rules using `resistance > 6` can never fire against a boolean (`False == 0 < 6` always)
2. V7 §5.5 is explicit: deterministic rules evaluate first; Falcon-3B is called only when no deterministic rule fires — resistance is the textbook case for this path

### 6.1 Design

`evaluate_step_policy()` becomes async and executes in two phases:

**Phase 1 — Deterministic rules** (`emotional_intensity`, `engagement` — numeric, no LLM call):  
Iterate step_policy rules as today. If any rule fires, return immediately. Resistance scoring does not occur.

**Phase 2 — Resistance scoring** (only when Phase 1 fires no rule):  
Call the Rules Service resistance-scoring prompt to obtain a 1–10 score for the current turn. Append the score to `resistance_history`. Evaluate any step_policy rules that reference `resistance` using the numeric score.

**Temporal condition for rule 3 (`resistance > 6 for 3 turns`):**
```python
rule_3_fires = (
    len(resistance_history) >= 3
    and all(r > 6 for r in resistance_history[-3:])
)
```
Rule 3 is structurally unreachable on turns 1 and 2 of a skill session. This is intentional: resistance is a sustained pattern, not a single-turn event.

### 6.2 Resistance Scoring Prompt — Rules Service

The resistance-scoring prompt is a clinician-tunable artifact. It lives in the Rules Service as a JSON template — threshold language, scale anchors, and Khaleeji cultural framing are all editable by the clinical team through the CMS workflow (draft → review → publish) without engineering involvement.

**The file ships in Sprint 1 with the initial prompt below.** Phase 2 is not mocked — it runs live from day one. Having real resistance scores flowing through the system immediately validates the Phase 2 mechanics end-to-end. The clinical team refines the prompt language via CMS; the scoring pipeline is already proven.

```
src/sage_poc/rules/data/resistance_scoring/resistance_prompt.json
```

```json
{
  "template_id": "resistance_score_v1",
  "authored_by": "sage_clinics",
  "prompt": "You are a clinical assistant evaluating therapeutic engagement. Score the user's resistance to continuing the current therapeutic activity on a scale from 1 to 10, where 1 is full engagement and 10 is complete refusal or active disengagement. Consider: reluctance, deflection, topic-changing, one-word replies, expressions of futility, or explicit refusal. In a Gulf Arab context, indirect refusal (e.g., changing subject, short answers, invoking busyness) carries equal weight to direct refusal. Message: {message_en}. Recent context: {recent_context}. Return only a single integer between 1 and 10.",
  "output_type": "integer",
  "scale_min": 1,
  "scale_max": 10
}
```

In the POC, "Falcon-3B" maps to the existing OpenRouter/ChatOpenAI LLM. The model identifier is a deployment concern; the interface is a 1–10 integer response. If the clinical team disagrees with the scale anchors or the Khaleeji cultural framing, they edit the JSON through the CMS — that is a content operation, not an engineering change.

### 6.3 Updated `evaluate_step_policy()` Signature

**Step_policy JSON encoding for resistance rules:**

Clinicians write resistance rules against the `resistance` signal (matching v7 §9.1 signal names exactly). The temporal qualifier "for N turns" is expressed as an optional `for_turns` field on the condition — not as a separate signal name. The evaluator handles the temporal aggregation internally against `resistance_history`. Skill authors do not need to know about `resistance_history` or any internal derived signal.

Rule 3, as it should appear in skill JSON:
```json
{
  "condition": { "step": "ANY", "signal": "resistance", "operator": ">", "value": 6, "for_turns": 3 },
  "action": "ease_back",
  "instruction": "User has shown sustained resistance across 3 turns. Offer a skill switch or a short break rather than continuing to the next step.",
  "next_step_id": "current"
}
```

A rule without `for_turns` fires on the single-turn resistance score only (e.g., `"value": 9` to catch immediate severe refusal). This gives clinicians a two-level authoring model: single-turn threshold for acute disengagement, `for_turns` for sustained pattern. The `for_turns` field is part of the `StepPolicyCondition` schema and must be added to `skills/schema.py`.

```python
async def evaluate_step_policy(
    skill: Skill,
    current_step_id: str,
    emotional_intensity: int,
    engagement: int,
    message_en: str = "",
    re_escalation_detected: bool = False,
    user_stop_request: bool = False,       # post_crisis_check_in step policy only — see §2.3 note
    resistance_history: list[int] | None = None,
) -> tuple[dict, int | None]:
    """Returns (step_policy_result, resistance_score_this_turn).

    resistance_score_this_turn is None if Phase 2 was not reached (deterministic rule fired).
    The caller writes resistance_score_this_turn back to state so it can be appended to
    resistance_history in the LangGraph state update.
    """
    history = list(resistance_history or [])

    # Phase 1: deterministic rules (no LLM call)
    # Rules referencing "resistance" are skipped here — they require a numeric score from Phase 2.
    deterministic_signals = {
        "emotional_intensity": emotional_intensity,
        "engagement": engagement,
        "re_escalation_detected": re_escalation_detected,
        "user_stop_request": user_stop_request,
    }
    for rule in skill.step_policy:
        cond = rule.condition
        if cond.step not in ("ANY", current_step_id):
            continue
        if cond.signal not in deterministic_signals:
            continue  # "resistance" rules are skipped — evaluated in Phase 2
        op_fn = _OPERATOR_MAP.get(cond.operator)
        if op_fn and op_fn(deterministic_signals[cond.signal], cond.value):
            return (
                {"action": rule.action, "instruction": rule.instruction,
                 "next_step_id": current_step_id if rule.next_step_id == "current" else rule.next_step_id,
                 "skill_complete": False},
                None,  # resistance not scored — Phase 1 fired
            )

    # Phase 2: resistance scoring via Rules Service (Falcon-3B / OpenRouter in POC)
    resistance_score = await _score_resistance_via_rules_service(message_en)
    updated_history = (history + [resistance_score])[-3:]  # keep last 3 for temporal condition

    for rule in skill.step_policy:
        cond = rule.condition
        if cond.step not in ("ANY", current_step_id):
            continue
        if cond.signal != "resistance":
            continue
        op_fn = _OPERATOR_MAP.get(cond.operator)
        if not op_fn:
            continue
        for_turns = getattr(cond, "for_turns", None)
        if for_turns:
            # Temporal condition: all scores in the last for_turns turns must satisfy the threshold.
            # Structurally unreachable until resistance_history has for_turns entries.
            if len(updated_history) < for_turns:
                continue
            if all(op_fn(r, cond.value) for r in updated_history[-for_turns:]):
                return (
                    {"action": rule.action, "instruction": rule.instruction,
                     "next_step_id": current_step_id if rule.next_step_id == "current" else rule.next_step_id,
                     "skill_complete": False},
                    resistance_score,
                )
        else:
            # Single-turn threshold: fires on the current turn's score alone
            if op_fn(resistance_score, cond.value):
                return (
                    {"action": rule.action, "instruction": rule.instruction,
                     "next_step_id": current_step_id if rule.next_step_id == "current" else rule.next_step_id,
                     "skill_complete": False},
                    resistance_score,
                )

    # No rule fired — advance normally
    # ... existing completion criteria and step advance logic unchanged ...
    return (advance_result, resistance_score)
```

Caller in `skill_executor_node` writes resistance back to state:
```python
step_result, resistance_score_this_turn = await evaluate_step_policy(
    skill=skill,
    current_step_id=step_id,
    emotional_intensity=state["emotional_intensity"],
    engagement=state["engagement"],
    message_en=state["message_en"],
    re_escalation_detected=(state.get("s7_result") == "NEW_CRISIS"),
    user_stop_request=any(p in state["message_en"].lower() for p in L1_EXIT_PHRASES),
    resistance_history=state.get("resistance_history", []),
)

# Update resistance_history if Phase 2 ran
updated_resistance_history = state.get("resistance_history", [])
if resistance_score_this_turn is not None:
    updated_resistance_history = (updated_resistance_history + [resistance_score_this_turn])[-3:]
```

### 6.4 Latency Impact

Phase 2 adds one LLM inference call per skill execution turn where no deterministic rule fires. At current OpenRouter latency (~200–400ms p50), this pushes the per-turn budget toward the v7 p95 target of 3s. Document this in the latency audit. If Phase 2 latency becomes a blocker pre-production, the mitigation is running the resistance scoring call concurrently with the step instruction generation (both can be fired as parallel async tasks in `skill_executor_node`).

### 6.5 Follow-up Required — Rule 4 and `engagement_history`

V7 §9.2 rule 4 says "IF engagement < 3 for 3 turns → check_in micro-skill." This is the same temporal pattern as rule 3. The current implementation does not have an `engagement_history` rolling buffer — `engagement` is scored per-turn by `intent_route_node` and only the current value is evaluated in Phase 1. Rule 4 as written in v7 §9.2 is therefore structurally unreachable with the current data shape: Phase 1 evaluates `engagement` as a single-turn signal, so `for_turns: 3` on an `engagement` rule would require `engagement_history` in state.

This does not block the current design document (it is not part of the flag lifecycle) but must be tracked as a follow-up item before shipping rule 4 in any skill JSON. The fix follows the same pattern as `resistance_history`: add `engagement_history: list[int]` to `SageState`, accumulate it in `safety_check_node` (which already computes `engagement_trajectory`), and pass it to `evaluate_step_policy()`. The `engagement_trajectory` field that already exists in state tracks the same data for safety purposes — `engagement_history` for step policy evaluation can likely reuse or alias it rather than adding a duplicate buffer.

**Flag for post-Sprint-1 design review.** Do not author step_policy rules with `signal: "engagement", for_turns: N` until this buffer is implemented.

---

## 7. Required Tests Per Fix

### Sprint 1 Regression Tests

**T1 — Clinical flag does not block skill:**
- Turn 1: User mentions "medication" → `medication_mention` in `clinical_flags`
- Turn 3: User starts breathing skill → skill_select matches
- Turn 4–7: skill_executor runs → assert skill advances through all steps → assert no turn returns `escalation_triggered` with `action != "exit_skill"`

**T2 — escalating_distress clears when distress drops:**
- Turns 1–3: `emotional_intensity = 8` → `escalating_distress` in `clinical_flags` for turn 3
- Turn 4: `emotional_intensity = 3` → assert `escalating_distress` NOT in `clinical_flags` for turn 4

**T3 — Stale knowledge_abstain does not fire:**
- Turn 1: `info_request` → `knowledge_retrieve` sets `knowledge_abstain=True`, no passages
- Turn 2: `skill_continuation` → assert composed prompt does NOT contain "No relevant clinical evidence"

**T4 — L2 fires once, not on accumulated flags:**
- Turn 5: New `trauma_indicator` flag detected → assert `escalation_triggered` is set, skill step advances
- Turn 6: Same `trauma_indicator` in accumulated `clinical_flags`, nothing new → assert `escalation_triggered` is None, skill step advances

**T5 — third_party_si dead code removed:**
- Assert `_FLAG_DESCRIPTIONS` in `composer.py` does not contain key `"third_party_si"`
- Assert `composer.py` `_build_l5_user_context_block()` with `clinical_flags=["third_party_si"]` returns no reference to third-party content (the flag cannot reach this path — the test confirms the dead code was removed)

**T6 — re_escalation_detected routes back to safety:**
- User in `post_crisis_check_in` skill, `crisis_state = "monitoring"`
- `s7_result = "NEW_CRISIS"` set by safety_check → assert skill_executor does NOT return step_instruction for post_crisis step → assert `crisis_state = "monitoring"` continues (new crisis path)

**T7 — resistance rule 3 requires 3 turns:**
- Turns 1–2: Falcon-3B returns score 9 each turn → assert rule 3 does NOT fire (history length < 3)
- Turn 3: Falcon-3B returns score 9 → assert rule 3 fires, step policy returns "offer skill switch or break"
- Turn 4: Falcon-3B returns score 3 → assert rule 3 does NOT fire (history is [9, 9, 3], last 3 not all > 6)

**T8 — cross-session persistence respects config:**
- `flag_lifecycle_config.cross_session_persistence.trauma_indicator = false` → end-of-session write path does NOT write `trauma_indicator` to `persisted_clinical_flags`
- `flag_lifecycle_config.cross_session_persistence.trauma_indicator = true` → write path writes it; session-start hydration in `server.py` pre-populates `clinical_flags` with `trauma_indicator`

**T9 — flag immutability config respected:**
- `flag_immutable_within_session = true` → assert `safety_check_node` does not remove any flag from `clinical_flags` even if the LLM signals retraction intent
- `flag_immutable_within_session = false` → retraction path is additive; test confirms no crash (retraction logic is not yet implemented, so the `false` path is a no-op for now)

---

## 8. Clinical Sign-Off

**Implementation proceeds with safe defaults.** Engineering does not wait for clinical sign-off to write code. The Sprint 1 implementation ships with all configurable defaults set to the conservative safe value. Clinical sign-off results in config changes — not migrations, not sprint planning, not code review.

Clinical advisors are asked to verify:

- [ ] §3.1: Confirm the default (`false` for all cross-session persistence flags) is clinically safe as the starting configuration. When ready to enable any flag, edit `flag_lifecycle_config.json` and publish — no engineering involvement.
- [ ] §3.2: Confirm `flag_immutable_within_session: true` is the correct default. If retraction is ever needed for specific flags, the clinical team sets this to `false` and specifies the retraction evidence patterns for engineering to add as rules.
- [ ] §4.2: Confirm proposed L2 semantics (background queue, no prompt injection, step continues) match clinical intent for "clinician review within 24 hours."
- [ ] §6.2: Review the initial resistance scoring prompt. If the scale anchors or Khaleeji cultural framing need adjustment, edit the JSON through the CMS — no engineering change required.
- [ ] §2.4 note: Third-party SI as a future Category A flag (CF-006) — confirm whether tracking a "this user has reported third-party SI concern" signal is wanted for any sprint, or deferred post-Gitex.

No item above blocks Sprint 1 code delivery. Sign-off is required before enabling any non-default config value in a production environment.

---

## 9. Files Affected

| File | Change |
|---|---|
| `src/sage_poc/state.py` | Add `new_clinical_flags_turn: list[str]`, `resistance_history: list[int]`, `resistance_score: Optional[int]` |
| `src/sage_poc/server_helpers.py` | Reset `new_clinical_flags_turn`, `resistance_score`, `knowledge_abstain`, `knowledge_passages`, `knowledge_source` in `_build_state()`; load `persisted_clinical_flags` from Supabase at session start |
| `src/sage_poc/nodes/safety_check.py` | Return `new_clinical_flags_turn`; remove `escalating_distress` from persisted set |
| `src/sage_poc/skills/schema.py` | Add optional `for_turns: int \| None = None` field to `StepPolicyCondition` |
| `src/sage_poc/nodes/skill_executor.py` | `check_escalation()` complete rewrite (§5.4); L2 control flow fix (§5.5); `evaluate_step_policy()` becomes async, two-phase (§6.3); caller writes `resistance_history` back to state |
| `src/sage_poc/prompts/composer.py` | Remove dead code `_FLAG_DESCRIPTIONS["third_party_si"]`; `escalating_distress` derived inline in `_build_l5_user_context_block()` |
| `src/sage_poc/memory/notification.py` | Update `ON CONFLICT` clause to append to `flags_timeline` JSONB array |
| `src/sage_poc/rules/data/flag_lifecycle_config.json` | New — `cross_session_persistence` per-flag booleans (all `false`); `flag_immutable_within_session: true` |
| `src/sage_poc/rules/data/resistance_scoring/resistance_prompt.json` | New — initial resistance scoring prompt; ships live (not mocked) |
| `migrations/` | Add `persisted_clinical_flags JSONB DEFAULT '[]'` to `user_therapeutic_profiles`; add `flags_timeline JSONB DEFAULT '[]'` to `clinician_review_queue`; both unconditional — ship in Sprint 1 |
| `tests/test_skill_executor.py` | T1, T4, T7 |
| `tests/test_safety_check.py` | T2, T8, T9 |
| `tests/test_compose_prompt.py` | T3, T5 |
| `tests/test_post_crisis.py` | T6 |
