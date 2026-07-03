# SageState + Audit Schema Delta — Crisis Tiering (2026-07-03)

Spec artifact riding `feat/crisis-tiering`. Documents every state/audit field the tiering adds.

## SageState additions
| Field | Type | Meaning |
|-------|------|---------|
| `crisis_tier` | `Literal["none","T1","T2"]` \| None | Resolved tier for the turn (from `tier_routing.json`). None when the flag is OFF. |
| `crisis_state` | extend enum with **`"supportive"`** | Non-locking T1 state (warm). Distinct from `"monitoring"` (post-T2). |
| `supportive_posture` | bool | Set True on a T1 turn; freeflow adopts the warm offer-not-force posture (G2). |
| `tier_rule_id` | str \| None | The `tier_routing.json` rule id that resolved the tier (audit traceability). |

These are additions to the enriched-state model; T1 is conceptually adjacent to Clinical Flags + Engagement.

## Audit-row additions (PDPL classification-decision traceability)
`crisis_tier` and `tier_rule_id` are written to the `session_audit` / `messages` audit row so a T1-vs-T2 classification decision is reconstructable.

### Flag-OFF nullability decision (audit checklist B + refinement #3) — DECIDED
> **When `SAGE_CRISIS_TIERING` is OFF, the tier audit fields are NOT written (absent), so a flag-off audit row is BYTE-IDENTICAL to master.**

Rationale: master has no tier columns; writing them present-but-null would make flag-off rows differ from master and muddy the "merging dark is safe" guarantee (B). Absent-when-off keeps flag-off == master exactly; present-and-populated only when the flag is ON (F). This is asserted by `test_crisis_tiering` (flag-off audit payload has no `crisis_tier` key) and by the flag-off byte-identical replay.

### Audit-column migration 006 — DEPLOY GATE (found during PR prep)
`session_audit` is a **curated** row (`audit._build_session_audit_row`), not `{**state}`. So the tier fields required their own columns: **`migrations/006_add_crisis_tier_to_session_audit.sql`** adds `crisis_tier` + `tier_rule_id`. `_build_session_audit_row` adds them to the row **only when present in state** (flag ON), so a flag-OFF row is byte-identical to master (Check B) and 006 is needed **only before the flag is flipped ON**. **Deploy gate:** run migration 006 on the target env (staging, then prod) *before* setting `SAGE_CRISIS_TIERING=true` there, or the flag-ON audit write fails on unknown columns. (Mirrors 005's knowledge-trace columns from PR #84.)

### G1b — cumulative-distress flag
On the **2nd** T1 turn in a session (`t1_count == 2`), write **one** `flag_for_review(severity=low)`. Once per session, no windowing. Written only when the flag is ON.
