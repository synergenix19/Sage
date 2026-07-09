# Three-Lane Execution Plan + Structured-Content Affordance Workstream (2026-07-06)

## Standing rule (written down, non-negotiable)
**Lane 1 (Safety/ML) is the critical path and is protected.** It has **first claim on any shared resource, and any conflict resolves in its favor.** Lanes 2–3 exist only so parallelizable work proceeds without pulling the critical path off-course or adding to the clinician queue.

---

## Lane 1 — Safety / ML (critical path, protected)
The launch gate is **GL-0 crisis recall (~37% naturalistic vs ≥95%)**. Nothing ships to external launch until this clears.
- **S2/MARBERT crisis classifier** (SI-vs-distress): data-readiness assessment *now* → fine-tune when TD3-scale data lands → the recall harness is the acceptance instrument.
- **E7 remediation Parts 2–3** (tasks #9–10): referent-aware co-occurrence matching can be **built behind the flag against provisional rules** while Part 1's clinician decision is pending — *the rule values are clinician-owned; the co-occurrence mechanism is not.* Part 3 graduated consequence likewise.
- **E3 / E4 route builds** as their gates clear (E3 medical; E4 §HR shape now, detection post-Gap-#65).

## Lane 2 — Structured-content affordance layer (parallel, this doc's scope)
Sequenced by cost/risk. **Delivery mechanism (discovered 2026-07-06):** `/chat` already emits structured metadata via **`X-Sage-*` response headers** (Node-Path, Crisis-Flags, Token-Usage…) alongside the streamed prose. Structured content rides this same channel — rendered by the frontend *outside* the prose, so **L0's no-markdown rule is never touched.**

1. **Source cards first.** `source_url` + `title` already exist in the KB corpus (`knowledge/ingestion.py`) but are dropped at retrieval (`KnowledgePassage` carries only text/source_id/citation/relevance). Change is pass-through: add the fields to `KnowledgePassage` + `to_dict` → populate from the repository query → emit an `X-Sage-Sources` header → frontend renders a source card. **No L0 re-sign, no content authoring, no skill-schema change, additive/byte-identical when empty.** Ships in days.
2. **Structured-affordance contract second.** ONE frontend delivery mechanism for cards / embeds / menus / buttons, designed once. The deferred **three-button check-in** and **selectable topic menus** (content inventory §4) land here too — same bucket, one contract, prevents three ad-hoc mechanisms.
3. **`media` field on `SkillStep` third.** The one piece that crosses into governed territory: a skill-schema extension → per **Absolute Rule 1**, a lightweight approval entry (same discipline as E2's metadata fields — nullable, additive, byte-identical when absent). Video *content* is clinician/CMS-authored and honestly **post-POC**; the schema slot + delivery contract are what's buildable now.

## Lane 3 — Clinician / content (external clock)
Queue already in their hands — **Lane 2 adds nothing to it** (items 1–2 need no clinician signature): TD3/crisis-corpus data, E7 referent scope (Part 1), burnout-inherited gate confirmation, Gap #65, Worry Tree CMS, Fact-vs-Opinion fold execution, GL-1 dial-test.

---

## Boundaries that make the split safe
- **Lane 2 NEVER touches:** Node 1, the precedence chain, L0's prose rules, or any flag-gated safety path.
- **Separate branches + PRs per lane** (Lane 2 item 1 = `feat/lane2-source-cards`).
- **Crisis path excluded from Lane 2 scope.** If source cards ever render on crisis responses, the helpline resource presentation is **governed content (GL-1 territory)** — the crisis path stays out of Lane 2 until explicitly reviewed. (Naturally excluded today: crisis routes to END, bypasses output_gate, and never populates `knowledge_passages`. The `X-Sage-Sources` header must additionally be suppressed on crisis turns as a belt-and-braces guard.)
- Content inventory amended with the media-gap row (this doc's companion change), so the parallel stream is a **tracked decision, not scope drift.**
