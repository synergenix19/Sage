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

## The ruling

**Should a psychoed consult turn carry Further Reading cards?**

- ☐ **Yes, and before Phase-2 category flips** → we ship **C1 only**: retrieval runs in parallel to
  populate the cards and the audit row; **the composed reply is untouched** (no evidence enters the
  prompt). Cards obey the existing ABSTAIN floor — weak evidence means no cards, never weak cards.
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

**Ruling:** ☐ approve (which option: ____) ☐ edit ☐ reject
