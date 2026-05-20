# Sage Improvements Log

Findings from live testing, audits, and architecture reviews. Add new entries here as they surface.

---

## Format

Each entry: **date · source · severity · affected file(s)**

**Severity:** `critical` | `high` | `medium` | `low`

---

## 2026-05-20

### IMP-001 — Crisis keyword scanner has no negation awareness
**Severity:** high  
**Source:** Live chat test — user said "No I'm fine, I'm not going to hurt myself"  
**Affected:** `src/sage_poc/nodes/safety_check.py:82`

`_contains_crisis()` uses pure substring matching (`kw.lower() in text_lower`). A denial or reassurance that contains a crisis keyword — e.g. "I am **not going to hurt myself**" — still matches and re-triggers the crisis path. The function has no concept of negation.

**Decision (2026-05-21):** Rejected as a code change. Crisis keyword suppression is a clinical calibration decision, not a code logic decision. The correct path is TD3 review with the clinical team. If negated phrases cause UX friction in the POC, the response tone can be softened within the existing `crisis_response` node — detection stays untouched. No implementation.

---

### IMP-002 — No crisis de-escalation state; system cannot exit crisis mode
**Severity:** high  
**Source:** Live chat test — same session as IMP-001  
**Affected:** `src/sage_poc/state.py`, `src/sage_poc/graph.py`

`SageState` has no `crisis_acknowledged` or `crisis_resolved` field. Once `is_safe = False` is set, the graph routes `crisis_response → END` every turn. Even when the LLM generates a safety follow-up question ("Are you still having thoughts of hurting yourself?"), the user's answer bypasses the LLM entirely — it is re-scanned by the keyword checker, which re-triggers crisis if the answer contains any crisis phrase. There is architecturally no exit path from crisis mode.

**Decision (2026-05-21):** The clinical need is valid. The implementation path follows the v7 spec §4.2 pattern 3 — do not add a 9th node. Instead:

1. **State extension only:** Add `crisis_acknowledged: bool` to `SageState` (enriched state, not a graph change). `crisis_response_node` sets it to `True` in its return dict. `run.py` carries it across turns alongside `clinical_flags`.

2. **Post-crisis recovery as a skill:** Author `post_crisis_recovery.json` as a clinician-authored skill JSON, loaded by `skill_executor` like any other skill. `skill_select` matches when `crisis_acknowledged = True` in state (requires a state-signal match path alongside keyword matching — a small extension to `skill_select`).

3. **Rationale:** Keeps the graph at 8 nodes. Keeps post-event clinical behavior in clinician-authored content, not graph code. Sets the correct precedent: every future post-event behavior (post-crisis, post-skill-completion, returning-user greeting) follows the same pattern — state flag → skill_select matches → executor loads skill → freeflow renders. One pattern, not special-case nodes.

---
