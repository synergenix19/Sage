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

**Proposed fix:** Add a negation-window guard. Before accepting a keyword match, check whether any of `["not", "no longer", "won't", "never", "i'm not", "i don't", "don't want to"]` appears within a 6-token window immediately preceding the matched keyword. If so, suppress the match.

---

### IMP-002 — No crisis de-escalation state; system cannot exit crisis mode
**Severity:** high  
**Source:** Live chat test — same session as IMP-001  
**Affected:** `src/sage_poc/state.py`, `src/sage_poc/graph.py`

`SageState` has no `crisis_acknowledged` or `crisis_resolved` field. Once `is_safe = False` is set, the graph routes `crisis_response → END` every turn. Even when the LLM generates a safety follow-up question ("Are you still having thoughts of hurting yourself?"), the user's answer bypasses the LLM entirely — it is re-scanned by the keyword checker, which re-triggers crisis if the answer contains any crisis phrase. There is architecturally no exit path from crisis mode.

**Proposed fix:**  
1. Add `crisis_acknowledged: bool` to `SageState`.  
2. When `intent_route` (or a dedicated de-escalation check) receives an explicit safety confirmation, set `crisis_acknowledged = True` and route to `freeflow_respond` with a warm-handoff prompt rather than repeating the crisis banner.

---
