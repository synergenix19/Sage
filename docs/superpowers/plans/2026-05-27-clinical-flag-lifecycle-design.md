# Clinical Flag Lifecycle Design Document

**Date:** 2026-05-27  
**Status:** DRAFT — Requires clinical sign-off before Sprint 1 implementation  
**Gate:** Blocks X1 + M1 bug fixes in `nodes/skill_executor.py` and `nodes/safety_check.py`  
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
| `third_party_si` | User mentions concern about someone else | L5 description, third-party crisis block | No — turn-level signal |

**Design rule:** Category A flags MUST NOT appear in `check_escalation()` logic. Their effect is entirely in the prompt layer (L5, Rules Service), not the executor.

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
| `user_stop_request` | L1_EXIT_PHRASES match in current turn's `message_en` | Exit skill gracefully (L1 escalation) |
| `resistance` | POC heuristic: `engagement < 3 for 2+ consecutive turns` | Hold step, ease back (step policy) |

**Design rule:** Category C signals are computed from current-turn state inside `skill_executor_node` or `evaluate_step_policy()`. They are never stored in state between turns.

---

## 3. Clinical Decisions Required

The following questions require explicit clinical sign-off before implementation. Engineering will implement whichever answer the clinical team provides.

### 3.1 Cross-Session Persistence of Category A Flags

When a new session starts, should the prior session's clinical flags pre-populate state?

**Option A — Session-scoped only:** Each session starts with an empty `clinical_flags`. The Rules Service may still fire clinical adaptations if the user discloses the same context again, but prior disclosures are not automatically carried forward. Simpler, more privacy-preserving.

**Option B — Cross-session persistence via therapeutic_profile:** Prior session flags are stored in `therapeutic_profile` (or a dedicated field) and pre-populate the session's `clinical_flags` on first turn. The user does not need to re-disclose trauma history on every visit.

**Clinical recommendation needed for each flag:**

| Flag | Session-only (A) or Cross-session (B)? | Notes |
|---|---|---|
| `substance_use` | ? | User in recovery — context is highly relevant across sessions |
| `trauma_indicator` | ? | Trauma history doesn't resolve; relevant across sessions |
| `eating_concern` | ? | Ongoing condition vs. discrete disclosure |
| `medication_mention` | Session-only (recommended) | Informational, changes frequently |
| `domestic_situation` | ? | Safety concern — may escalate or resolve between sessions |

### 3.2 Flag Removal Within a Session

Should any Category A flag ever be removed within a session? For example:
- User disclosed substance use early in session, has since clarified it was in the past
- User retracted a domestic situation concern

**Option A — Flags are immutable once set** (current design, deliberate): Once a clinical flag is set within a session, it stays. This is the conservative safe default — it is clinically safer to continue applying adapted framing when uncertain.

**Option B — Flags can be cleared by explicit user statement**: Add a `clear_flag` action to the rules engine, triggerable by specific retraction patterns. Higher implementation complexity.

**Recommended default:** Option A (immutable within session). If the clinical team disagrees, specify which flags can be retracted and the evidence patterns required.

### 3.3 L2 Escalation Trigger Scope

Currently L2 fires on ANY non-empty `clinical_flags`. The proposed fix narrows it to **new flags detected this turn only** (delta, not accumulated set). This means:

- A user who disclosed medication in turn 3 will NOT trigger L2 in turns 7, 10, 15 etc. just because the flag persists
- A user who discloses a new clinical context in turn 7 WILL trigger L2 in turn 7 only

**Clinical question:** Is this the correct trigger scope? Should L2 re-trigger on any subsequent turn where a clinical flag was active (current behavior), or only on the turn where a flag is first detected (proposed behavior)?

**Recommended answer:** First-detection only. The clinical review happens once. If the clinical team wants re-triggering (e.g., flag detected on turn 3, user discloses escalation on turn 8), the `flag_for_review` tool (already available to the LLM in freeflow) is the correct mechanism — it gives the LLM agency to escalate contextually.

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
- `_log_clinical_review()` in `output_gate_node` fires (already exists — this is the mechanism)
- No change to LLM prompt beyond what PI-CF rules already inject

---

## 5. State Changes Required

### 5.1 New Fields in `SageState`

```python
# In state.py — add alongside clinical_flags
new_clinical_flags_turn: list[str]  # flags detected this turn only; reset by _build_state()
                                     # used by skill_executor check_escalation() instead of clinical_flags
```

Note: because `new_clinical_flags_turn` must reset every turn, it must be declared in `_build_state()` with a default of `[]`. This collocates it with the M4 fixes (resetting `knowledge_abstain`, `knowledge_passages`, `knowledge_source`) — one function owns all per-turn resets.

### 5.2 `safety_check_node` Return

Add `new_clinical_flags_turn` to the return dict (the already-computed `new_clinical_flags` local variable at `safety_check.py:100-102`).

### 5.3 `escalating_distress` Removal from `clinical_flags`

```python
# safety_check.py — before line 148
persisted_non_computed = [f for f in state.get("clinical_flags", []) if f != "escalating_distress"]
all_clinical = list(set(new_clinical_flags + persisted_non_computed))
# escalating_distress: injected into L5 descriptor separately if distress_signal is True
```

`escalating_distress` should be passed to `compose_prompt` as a separate signal if needed, or derived inline in `_build_l5_user_context_block()` from `clinical_flags` filtering. It must NOT be in the persisted set.

### 5.4 `check_escalation()` Signature Change

```python
# skill_executor.py
def check_escalation(message_en: str, new_clinical_flags_turn: list[str]) -> dict | None:
    # L1: unchanged
    # L2: fires on new_clinical_flags_turn, not accumulated clinical_flags
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

### 5.5 L2 Branch in `skill_executor_node`

Remove the early return on L2. L2 now writes to the audit trail but continues to `evaluate_step_policy`:

```python
if escalation:
    if escalation["action"] == "exit_skill":  # L1 only
        # ... existing L1 early return unchanged ...
    # L2 (and future L3/L4): log, then fall through to step policy
    crisis_update: dict = {}
    if escalation["action"] == "exit_skill" and skill_id == "post_crisis_check_in":
        crisis_update = {"crisis_state": "resolved"}
    # Note: L2 does NOT return early — step policy continues below

# evaluate_step_policy runs for ALL non-exit escalations
result = evaluate_step_policy(...)
```

---

## 6. Category C Signal Plumbing (M5 Fix)

`evaluate_step_policy()` signature extension:

```python
def evaluate_step_policy(
    skill: Skill,
    current_step_id: str,
    emotional_intensity: int,
    engagement: int,
    message_en: str = "",
    re_escalation_detected: bool = False,   # new
    user_stop_request: bool = False,         # new  
    resistance: bool = False,                # new (POC heuristic)
) -> dict:
    signals = {
        "emotional_intensity": emotional_intensity,
        "engagement": engagement,
        "re_escalation_detected": re_escalation_detected,
        "user_stop_request": user_stop_request,
        "resistance": resistance,
    }
```

Caller in `skill_executor_node`:

```python
result = evaluate_step_policy(
    skill=skill,
    current_step_id=step_id,
    emotional_intensity=state["emotional_intensity"],
    engagement=state["engagement"],
    message_en=state["message_en"],
    re_escalation_detected=(state.get("s7_result") == "NEW_CRISIS"),
    user_stop_request=any(p in state["message_en"].lower() for p in L1_EXIT_PHRASES),
    resistance=(state.get("engagement", 5) < 3),  # POC heuristic — document as simplification
)
```

Note: `resistance` POC heuristic is `engagement < 3` (single-turn). The v7 spec references Falcon-3B classification for resistance detection; this heuristic is an explicit simplification, to be replaced with the Falcon-3B path pre-production.

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

### Sprint 2 Regression Tests

**T5 — re_escalation_detected routes back to safety:**
- User in `post_crisis_check_in` skill, `crisis_state = "monitoring"`
- `s7_result = "NEW_CRISIS"` set by safety_check → assert skill_executor does NOT return step_instruction for post_crisis step → assert `crisis_state = "monitoring"` continues (new crisis path)

---

## 8. Clinical Sign-Off

This document requires explicit sign-off from clinical advisors on:

- [ ] §3.1: Cross-session persistence decision per flag type
- [ ] §3.2: Within-session flag immutability confirmation  
- [ ] §3.3: L2 trigger scope (first-detection only vs. any active turn)
- [ ] §4.2: Proposed L2 semantics (background queue, no prompt injection, step continues)
- [ ] §6: Resistance heuristic (`engagement < 3`) as POC simplification

Engineering will not proceed with Sprint 1 code changes until all five items above are checked.

---

## 9. Files Affected

| File | Change |
|---|---|
| `src/sage_poc/state.py` | Add `new_clinical_flags_turn: list[str]` |
| `src/sage_poc/server_helpers.py` | Reset `new_clinical_flags_turn`, `knowledge_abstain`, `knowledge_passages`, `knowledge_source` in `_build_state()` |
| `src/sage_poc/nodes/safety_check.py` | Return `new_clinical_flags_turn`; remove `escalating_distress` from persisted set |
| `src/sage_poc/nodes/skill_executor.py` | `check_escalation()` uses `new_clinical_flags_turn`; L2 no longer early-returns; `evaluate_step_policy()` signature extended |
| `src/sage_poc/prompts/composer.py` | `escalating_distress` handling in `_build_l5_user_context_block()` if needed |
| `tests/test_skill_executor.py` | T1, T2, T4 |
| `tests/test_safety_check.py` | T2 |
| `tests/test_compose_prompt.py` | T3 |
| `tests/test_post_crisis.py` | T5 |
