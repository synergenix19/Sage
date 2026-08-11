# Deroute record — mindfulness_body_scan + safe_place_visualization (2026-08-06)

**Ruling executed:** body_scan packet option (a) (PR#407), PO-directed 2026-08-06, with
the SPV signature-status rule: "the deciding fact is signature status, not taxonomy — if
SPV's record shows the same 'signature record not found' status as body_scan, rule it in;
if verifiably signed with its trauma contraindication authored, it stays; if her sentence
doesn't resolve it, default to the protective reading pending the record check."

**SPV record check (the deciding fact, verified 2026-08-06):** authored 2026-05-22
(commit `857f8eef`, a compliance-fixes batch); no entry in `signed_clinical_fields.json`;
no dedicated sign-off record anywhere in the governance directory. Status: **signature
record not found — same as body_scan.** Ruled IN; both derouted under the protective
reading. **CONFIRMED by Vee 2026-08-11** (approval-list rows 5a/5b, PO relay —
`2026-08-11-vee-approval-record.md`): both stay derouted until she signs each
registration. If she issues a signature for either skill, re-route = delete its
`KEYWORD_SEMANTIC_SKIP` entry + restore its offer blurb from this commit's parent, one
line each.

## Checklist compliance — measured landing zones (semantic tier, BGE-M3, threshold 0.4593)

With mm + body_scan + SPV all derouted:

| request shape | lands at | signature status of catcher |
|---|---|---|
| "I want to try mindfulness meditation…" | act_psychological_flexibility (0.560) | original v7 spec-set (clinician-authored at spec time) |
| "guided meditation" | dbt_tipp (0.530) | original v7 spec-set; NOTE: TIPP is a distress-tolerance skill catching a calm request — odd fit, not a §1a-§6 risk; flagged for the routing-quality backlog, not a deroute matter |
| "i want to meditate" | box_breathing (0.547) | original v7 spec-set, Tier-1 first-line |
| "can we do some sitting meditation" | box_breathing (0.534) | original v7 spec-set, Tier-1 first-line |
| "body scan" | progressive_muscle_relaxation (0.456) — **below threshold, NO offer** | n/a (falls to freeflow/KB) |
| "visualize a safe place" | grounding_5_4_3_2_1 (0.499) | original v7 spec-set, Tier-1 first-line |

**Terminal state:** the §1a-§6 grounding/mindfulness/imagery family chain is fully
terminated — every above-threshold catcher is an original v7 spec-set skill outside the
contraindicated family. No member of the family with an unresolved signature record
remains reachable by keyword or semantic matching.

**Honest wording note:** the landing skills' "signature status" is stated as provenance
(original v7 spec-set, clinician-authored at spec time), not as per-skill signature
records — the repo does not carry per-skill signatures for the original set (family
audit, PR#407). The distinction that matters for this ruling is unresolved-late-addition
vs spec-set, and every catcher is spec-set.

## Serving

Goes live with the next deploy; until then desired-only. MM's regime-aware Tier-A smoke
check continues to assert the family deroute live on every deploy (it passes on any
non-mm catcher, and the landing zones above are all non-family).
