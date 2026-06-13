# Work Order — C-4: session_audit Intermediate-Write Race (409)

**Date opened:** 2026-06-13 (finding originates in the 2026-06-04 system audit, C-4; independently reproduced in the PR #4 audit, Phase C and Phase F-data)
**Owner:** Engineering
**Blocking:** reliability of the offer acceptance-rate KPI denominator (see below); clean audit rows on banned-opener retry turns

## The defect

`output_gate` writes an intermediate `session_audit` row before the banned-opener retry and a final row after; the two writes race, producing duplicate-key 409s (`session_audit_session_turn`) and, intermittently, a dropped row. Confirmed fix approach (2026-06-08 analysis, supersedes the rejected 6f7a07a upsert): **remove the intermediate write at output_gate (~line 280/304)** and let the single final write (~line 412) capture `banned_opener_retry_count` from state.

Independent reproductions in the PR #4 audit:
- Phase C flake diagnosis logs: `duplicate key … session_audit_session_turn` CRITICAL on the intermediate write.
- Phase F-data: exactly 1 of 101 expected rows missing (`audit-e-r5-box` turn 1, an offer-bearing turn) — the dropped write is the one that 409'd; 10 other retried turns persisted, i.e., the drop is racy.

## KPI bias this fix must resolve (reviewer-mandated acceptance criterion, 2026-06-13)

The offer acceptance-rate KPI is `count(offer_accepted) / (count(skill_offer_made) − count(offer_voided_fallback))` over `session_audit.node_path` (architecture doc §5.2). Two C-4-coupled biases:

1. **Dropped offer-bearing rows** remove `skill_offer_made` from the denominator while the acceptance can survive in the next turn's row → over-counts acceptance (observed: stored 11/28 = 39.3% vs reconstructed 11/29 = 37.9%).
2. **Errored-turn rows that survive** carry `skill_offer_made` with no reachable accept and no guaranteed `offer_voided_fallback` companion marker — the S1-1b server-side void is a checkpoint state write, not an audit row — → under-counts acceptance by the surviving-errored population.

**Acceptance test for this work order:** after the fix, voided and errored offers reconcile in the store — every `skill_offer_made` row is either followed by an accept/decline/ignore/unparsed lifecycle row, carries `offer_voided_fallback`, or is attributable to a server-errored turn via an explicit marker (adding an `offer_voided_error` audit marker for the S1-1b path is in scope for this fix if needed for reconciliation). A reconciliation query over a scripted batch must balance exactly.

## Status

OPEN. Fix approach confirmed; not implemented. The 2026-06-04 audit's C-4 branch work (6f7a07a) is confirmed WRONG and must not be revived.
