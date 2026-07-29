# Delivery-shape ask — should a psychoed consult turn carry Further Reading? (Vee + PO, 2026-07-29)

**One ruling requested.** Since the 2026-07-23 Mechanism-A flip, a question like "what is anxiety?"
that the consult routes to a psychoed skill (`psychoed_anxiety` etc.) is answered conversationally by
the skill, with **no Further Reading source cards**. The same question in a fresh session with no
consult match still takes the KB path and **does** show cards. The user cannot see which internal path
served them; on a Learn surface whose Scoping-Brief commitment is "synthesised responses that cite
their sources," the inconsistency is a product-contract question — and delivery shape is clinical
territory, so it is yours to rule, not engineering's.

This is NOT a v7 conformance question: §4.2 usage mode 2 licenses skill-injected psychoed without
retrieval or citations, and the audit trail on consult turns is faithful and complete. The 11/36
matrix baseline was measured with consult prompts carrying no KB context and is not at risk from any
option below except where explicitly gated.

## Recommendation (engineering; the ruling is yours)

| Rec | Basis | Your call |
|---|---|---|
| **Option 1 — C1 interim, cards-only** | The inconsistency is live TODAY on a citation-bearing surface (RFQ commitment), and Phase-2 per-category flips are gated on the (unsigned) Phase-1 packet + fixture gates — timeline not short. C1 adds **zero new clinical content**: the cards are the same top-3 passages the KB path would have shown for the same question, same ABSTAIN floor, and the conversational reply you signed is **byte-untouched** (no evidence enters the prompt). Built inert (default-OFF flag), flipped only on this ruling, and **self-retiring**: each Phase-2 category flip replaces its C1 retrieval cards with the signed kb_ref cards in the same change, mirroring the consult-set retirement you already ratified. Reversible at any moment by flag. | ______ |

If you judge the Phase-2 packet signature to be imminent, **Option 2 is equally sound and cheaper** — the only cost is the inconsistency persisting until each category flips.

## The ruling

**Should a psychoed consult turn carry Further Reading cards?**

- ☐ **Yes, and before Phase-2 category flips** → we ship **C1 only**: retrieval runs in parallel to
  populate the cards and the audit row; **the composed reply is untouched** (no evidence enters the
  prompt). Cards obey the existing ABSTAIN floor — weak evidence means no cards, never weak cards.
  **Three conditions are part of this ruling, not implementation detail:**
  1. **Label mandate — the cards must not claim grounding they don't have.** On a C1 turn the reply
     is grounded in your signed skill content and the cards in retrieval; rendering them as
     "Sources" would assert the reply was generated from those passages — a faithfulness
     misrepresentation on the exact surface the Scoping-Brief citation commitment covers, worse
     than no cards. The ruling mandates the **"Further Reading"** label (related KB material, not
     provenance of the reply). The frontend already renders this label; this ruling pins it, and
     the C1 build carries a fixture asserting the label key so it cannot drift to "Sources".
  2. **Audit purpose discriminator** — on C1 turns `knowledge_passage_ids` becomes non-empty
     without evidence-grounded generation, the same false inference as (1) recreated in the audit
     trail. The audit row therefore records **retrieval purpose (`evidence` | `cards_only`)**
     alongside source provenance (`retrieval` | `kb_ref`); C1 turns stamp `cards_only`. No future
     auditor can read non-empty passage IDs as grounding.
  3. **Same-change retirement coupling** — a category's consult-set entry and its C1 fan-out
     predicate retire **in the same change** (riding the Phase-2 handoff §0 convention), so no
     turn can ever emit retrieval cards and kb_ref cards together; the invariant's disjointness
     assumption holds throughout the transition.
- ☐ **Yes, but Phase-2 timing is fine** → no interim build. Phase 2's signed `kb_ref` pointers become
  the card source (deterministic, signed, no retrieval call), landing per category as each pathway
  flips.
- ☐ **No** — consult turns are a guided-skill surface, not a cited-answer surface; cards would blur
  the two registers. **Note before selecting:** this option reinterprets a commitment made to Sage in
  the RFQ response (Learn cites its sources) by scoping it to the KB-answer path only. If selected,
  **that scope reading is itself the recorded decision** — it gets its own ruling line below, so a
  future RFQ-compliance review finds a ruling, not an inference buried in rationale. Options 1 and 2
  do not carry this exposure.
  - Scope reading ruling (only if this option is selected): *"The Scoping-Brief citation commitment
    applies to the KB-answer path only."* ☐ approve ☐ edit ☐ reject

**Explicitly out of scope of this ask:** injecting retrieved evidence into the consult turn's prompt
(C2). That changes signed, just-verified output and is gated separately on the Phase-1 packet
sign-off plus a guarded, parity-verified matrix re-run.

**Ruling:** ☑ approve (which option: **Option 1**) ☐ edit ☐ reject

---

## RULING RECORDED — 2026-07-29

**Option 1 APPROVED (Vee), with the three in-ruling conditions (label mandate, audit purpose
discriminator, same-change retirement coupling) as part of the approval.** Provenance: relayed by
the PO in-session 2026-07-29; Vee's verbatim reply to be pinned here on receipt, per the v7.3
transcription protocol. This ruling is the flip gate for the C1 sources flag: the build merges
inert and flips only against this record.
