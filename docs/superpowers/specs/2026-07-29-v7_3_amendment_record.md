# v7.3 Amendment Record — Node-4 info_request consult, TRANSITIONAL (Psychoed Mechanism-A) (2026-07-29)

**Status:** RETROSPECTIVE spec artifact. The behaviour it records has been LIVE in production since
2026-07-23 (flip) and merged inert since PR#343. This record closes the spec-edit debt: the change was
approved and governed at every gate (chain below) but the v7 spec text was never amended — the v7.1/v7.2
Absolute-Rule-1 convention (spec + code merge together) was not followed for this change. Same debt family
as the §5.4 Falcon→GPT item. Nothing in this record changes behaviour.

**Amendment sign-off:** PENDING — product owner. ☐ approve ☐ edit ☐ reject
**Design:** `specs/2026-07-17-psychoed-mechanism-a-design.md` · **Go-live:** `governance/2026-07-23-psychoed-consult-golive-verification.md`

---

## §4 Node 4 (skill_select) transition table — amended

**v7 (superseded):** *"Skill → executor. Info → knowledge. None → freeflow."*

**v7.3:** *"Skill → executor. **Info → consult first:** if the top skill match is in
`INFO_REQUEST_SKILL_CONSULT_SET` (disposition-scoped, doc-derived) → executor; else → knowledge,
unchanged. None → freeflow."*

Gated by `SAGE_INFO_REQUEST_CONSULT` (kill-switch; only literal `"true"` enables). **OFF is
byte-identical to v7:** the consult matching never runs and the knowledge path is exactly the
pre-amendment behaviour (`config.py` inverted strict parse; `skill_select.py` info_request branch;
`graph.py _route_after_skill_select` keyed on `skill_match_method == "info_request_skill_consult"`,
never on `active_skill_id` alone).

## What it does and why (measured, characterized)

23/30 psychoed presentations (§1f, §6d, §3c, S2c; §7c partial) **correctly** classify as
`info_request` — the classifier is right; the wrong assumption was the router's
`info_request → knowledge_retrieve` fulfillment. The BOT BEHAVIOUR doc prescribes skills for these
presentations. The consult asks the disposition question (does the doc prescribe a skill for this
presentation?) before the KB short-circuit; fail-open by construction — no match, or a match outside
the set, flows to KB untouched. `intent_route` is not touched. Measured recovery: EN conformance
matrix 8/36 → 11/36 (§1f, S2c, §6d full; §3c 4/5), guarded + parity-verified vs serving.

## Approval chain (the record this amendment was missing)

| Gate | Date | Record |
|---|---|---|
| Design approved to build (PO directive) | 2026-07-17 | `specs/2026-07-17-psychoed-mechanism-a-design.md` |
| Merged INERT, flag-OFF (governed inert-merge) | PR#343 | `governance/2026-07-17-inert-merge-policy.md` (names this consult as precedent) |
| Clinician flip gate: consult-set confirmation | 2026-07-23 | Vee-approved B1, consolidated approval sheet (pin below) |
| Flip + live behavioural verify + guarded re-measure | 2026-07-23 | `governance/2026-07-23-psychoed-consult-golive-verification.md` (PR#362) |
| Desired-state drift (`false`, no rationale found) resolved; `true` restored, owner-ratified, readback-confirmed (build `09013f19`) | 2026-07-29 | drift-resolution record (command-session ledger) |

**Approval-sheet pin — REQUIRED FIELD, OPEN:** the consolidated approval sheet carrying Vee's B1
consult-set confirmation is not in this repo. Owner to pin **location + content hash** here before
sign-off: `location: ______ · sha256: ______`. **Template rule going forward:** every amendment record
MUST carry a location+hash pin for any sign-off artifact that lives outside the repo.

## TRANSITIONAL — retirement condition (do not build on this mechanism)

Mechanism-A is a **bridge, scheduled to retire per category.** Per the Phase-2 carry-forward
(`plans/2026-07-28-psychoed-phase2-handoff-notes.md` §0): **each pathway-category flip retires its
`info_request_consult_set.py` entry in the same change.** The successor is the psychoeducation
pathways architecture (`specs/2026-07-23-psychoeducation-pathways-design.md`): signed blocks/scripts
carrying `kb_ref` pointers to Understanding-X article families. When the last in-scope category flips,
the consult set is empty and this amendment's §4 branch is dead code to be removed with it. Any new
work that would attach to the consult path must instead target the pathways design.

## Named open item — citation-UX gap (product contract, not a spec breach)

Consult-served turns emit no Further Reading source cards, so the same question can return cards or
not depending on internal routing the user cannot see. Weight comes from the RFQ/Scoping Brief (Learn
cites its sources), not from v7 (§4.2 usage mode 2 licenses skill-injected psychoed without
retrieval or citations; Node-8 audit recording is faithful and complete on these turns). Resolution
path, in order:

1. **Vee/PO delivery-shape ruling** — should a psychoed consult turn carry Further Reading? (ask:
   `governance/2026-07-29-consult-further-reading-delivery-shape-ask.md`)
2. **If cards must return before Phase-2 category flips:** C1 only — parallel `knowledge_retrieve`
   fan-out populating `knowledge_passage_ids` + `X-Sage-Sources`, **prompt untouched** (the 11/36
   baseline was measured with consult prompts carrying no KB context).
3. **Otherwise:** fold into Phase 2 — consult/pathway turns emit **kb_ref-derived** source cards.
4. **C2 (L4 evidence injection into consult prompts): NOT before** packet sign-off + a guarded,
   parity-verified matrix re-run. Injecting ~300 words into just-verified turns ahead of the
   verbatim-pin + Node-8 hash-gate regime is the regression-by-improvement class.

## Sources invariant — restated as a Phase-2 PRECONDITION

Today (`server.py _sources_header`): sources ⊆ `knowledge_passage_ids`. Under Phase 2, kb_ref-derived
cards have no retrieval provenance and would fail this invariant closed on every psychoed turn. It is
restated NOW, before Phase 2 lands:

> **sources ⊆ (knowledge_passage_ids ∪ signed_kb_refs)**, with a per-source provenance discriminator
> (`retrieval` | `kb_ref`) on the audit row. Every card traces to a retrieval ID or a signed pointer.
> The ABSTAIN similarity floor applies **only** to `provenance = retrieval`; kb_ref cards cannot
> abstain because they are signed — that is the audit-clean property being bought.

Phase-2 implementation gate: the audit-row provenance field and the widened invariant land **with**
the first kb_ref card emission, not after.

## Scope invariants (held)

Node-1 safety routing untouched; `intent_route` untouched (classifier unchanged); fail-open to KB for
any non-matching info_request; non-info_request routing byte-identical; flag OFF byte-identical to v7;
consult set is disposition-scoped engineering config derived from the clinician-owned
`target_presentations` — no clinical content changed hands at merge; the flip itself was the
clinician-gated event.
