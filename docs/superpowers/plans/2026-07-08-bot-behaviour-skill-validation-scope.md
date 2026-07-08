# Work item — BOT BEHAVIOUR → skill-JSON validation (QUEUED, not started)

**Status:** scoped 2026-07-08, on the queue as its own work item. Not on the current engineering critical path (Lane 1 E7 Part 2 / MARBERT data-readiness).

**Cardinal Rule frame:** the BOT BEHAVIOUR spec is a substantial clinician-authored *behavioral* specification. Its content belongs in **skill JSON, not code**. This item validates that the encoding is clean and confirms no new graph node is required.

## Mapping to validate when encoded (PO/architect read, 2026-07-08)
| BOT BEHAVIOUR construct | Encodes as |
|---|---|
| Severity tiers + step-up / step-down | `step_policy` rules on `emotional_intensity` |
| Per-category guards | `contraindications` + `escalation_matrix` (TIPP cardiac branch = a `cultural_override`-style branch-with-step) |
| Loop-prevention / ceiling | L1 / L4 escalation levels |
| Universal crisis override | Node 1 (deterministic) — already its job; "silently divert, don't ask questions at High tier" matches the crisis-UX rules |
| §1d depressive-rumination + OCD routing exclusions | skill-matching rules in Node 4 |

## Two items needing explicit design (not assumption)
1. **High-tier Better/Same/Worse three-button check-in** — a UI affordance the executor must be able to *request* (structured-response instruction to the frontend).
2. **§1f topic menu** — likewise a structured-response affordance to the frontend.

## The affordance contract is BIDIRECTIONAL — it touches the state schema (checklist item)
The check-in affordances are not just "instruction out." The Better/Same/Worse buttons and the 1–10 scales feed **structured responses back into state**:
- their values drive `step_policy` evaluation — the step-up / step-down triggers **key on** the check-in response;
- they update the mood / engagement state components.

So the executor↔frontend contract is **instruction out → structured response back into state**. This is the ONE place the affordance work touches the **state schema**, and it is the real design risk. The confirming scoping pass must verify this data flow explicitly (schema fields for the returned check-in value, how it reaches `step_policy` and mood/engagement) — it belongs on the pass's checklist, not discovered mid-encoding.

## Scoping conclusion
On this read, **nothing here requires a ninth node** — it is all skill content plus the two frontend affordances above. A scoping pass should confirm this before encoding begins, and must include the bidirectional check-in data-flow verification above.

## Provenance
Raised during the video-channel fork resolution (`../../kb/2026-07-08-video-channel-fork-resolution.md`), where the skill-video curation doc surfaced that the BOT BEHAVIOUR spec is broader than a video answer. Cross-refs the BOT BEHAVIOUR ingestion workstream.
