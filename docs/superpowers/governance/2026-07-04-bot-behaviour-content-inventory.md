# BOT BEHAVIOUR — Content-Type → Architectural-Home Map (Content Inventory)

**Status:** DRAFT (§1 filled; §2–§4 one review turn each, Phase-2 discipline).
**Companions:** `2026-07-04-extensions-e1-e7-approval.md` (mechanism — this doc is its named content destination) · `2026-07-04-crisis-hr-protocol-conversion.md` (§C/§HR content + safety lexicons).

## §0 — Purpose & scope

This inventory **proves every clinician content-*type* in the spec has a tunable, clinician-editable architectural home**, and **flags the reconcile cases** where spec copy would modify already-signed behaviour. It is deliberately **type-level with per-category coverage accounting — not a block-level transcription** of the spec's ~170 content blocks. That reframe is the point: the architecture holds the words, and content population is the ordinary iterative tune lane (the spec's own copy is "illustrative, not exhaustive — tune against real usage data"). This doc exists so nothing falls *between* documents; it does not pull content authoring onto the critical path.

Out of scope of the E1–E7 approval record (mechanism); this is the destination its §0 scope note names.

## §1 — Content-type → home map

Every content type in the spec maps one-to-one onto a v7 ownership surface. "Clinician-editable (CR2)" = tunable without an engineering change (Cardinal Rule 2), made auditable per type.

| Content type | Architectural home (v7) | Clinician-editable (CR2) | Present vs to-add | Reconcile-risk | Notes |
|---|---|---|---|---|---|
| **Validating / framing statements** | skill JSON `steps[]` — first-step `goal` / `tone` / `examples` | **Yes** | Home present + populated (existing skills open with validation); spec's **tier-specific** statements are add/reconcile | **Yes** — tier-specific vs current generic openers | "validate before inform" is also enforced globally by L0 (row 5) |
| **Preliminary / screening questions** | skill JSON `steps[]` — screening steps + `completion_criteria` | **Yes** | Home present; per-category question sets add where a new flow | Low–Med — condensed vs full sets differ per tier | one-question-per-turn is an L0 rule (row 5), not per-skill copy |
| **Psychoeducation scripts** | psychoed_* skill `steps[]` **and** `info_request` → RAG (KB corpus) | **Yes** (skill JSON + CMS-managed corpus) | psychoed_anxiety/depression/stress present; §HR / grief / emotions / assertiveness psychoed **to-add** | Low — additive | Two homes: in-flow step vs selectable menu → RAG. Pick per delivery shape (§2 records which) |
| **Check-in + guided-technique copy** | skill JSON `steps[]` + `step_policy` (check-in step + advancement rules) | **Yes** | Home present; per-tier check-in copy to-add | **Yes** — the check-in **format** change (1–10 → three-button *Better/Same/Worse*) is more than copy | The signal (`emotional_intensity`) exists; the **structured-UI affordance is a deferrable enhancement** (§4), degrades to text today |
| **Cross-cutting tone / constraint rules** | **L0 persona / output_gate rules** — NOT per-skill `steps[]` | **Yes**, but L0 is a signed artifact → edits are **re-sign-gated** | **Mixed:** "no unbidden diagnostic label," "concise / plain," "validate before advice" **present** in L0; §C "no categorical confidentiality claims" only partially present (L0 PRIVACY clause) → **to-add** in crisis copy | **High** — an L0 change is an L0 re-sign (same authority as the helpline payload) | A global rule mis-homed in per-skill tone would be re-authored ~30× and drift — these live **once** in L0/output_gate. Present-vs-add is called per rule (§2/§3) |
| **Trigger words / phrases** | Rules Service lexicons — Node-4 skill-matching (`target_presentations`, `keyword_matcher`) | **Yes** | category-matching tables add/tune per category | Low | **⚠ GOVERNANCE SPLIT:** the **safety-route** lexicons (crisis / medical / HR / IPV — `crisis_keywords`, medical red-flag, psychosis/mania/dissociation, `domestic_situation`) are governed by the **conversion doc + recall-gated fixtures** and tracked **there**, NOT here. **Only the non-safety category-matching trigger tables (Node-4 skill selection) are homed through this inventory** — so the same lexicon never appears under two authorities |

**Read of §1:** every type has a clinician-editable home on an existing v7 structure; none requires one of the five extensions to *hold* content (E1/E2 change how skills are *sequenced*, not where their copy lives). The two rows carrying real risk are **check-in format** (an enhancement, not copy) and **cross-cutting rules** (L0 re-sign-gated) — both surfaced in the reconcile register (§3).

## §2 — Per-category coverage checklist
*pending — next turn (destinations verified against the 97-item Skills & Knowledge Base inventory; UNVERIFIED marked, not asserted)*

## §3 — Reconcile register
*pending (each item names its re-sign path: skill copy → clinical CMS re-approval; L0 → L0 re-sign)*

## §4 — New content-skills + deferred enhancements
*pending (each new skill carries an `evidence_base` obligation — schema-mandatory, clinician-sourced)*
