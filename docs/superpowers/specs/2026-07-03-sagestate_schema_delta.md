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

### G1b — cumulative-distress flag
On the **2nd** T1 turn in a session (`t1_count == 2`), write **one** `flag_for_review(severity=low)`. Once per session, no windowing. Written only when the flag is ON.
