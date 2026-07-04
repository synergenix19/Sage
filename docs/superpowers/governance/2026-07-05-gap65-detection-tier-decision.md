# Gap #65 — §HR flag detection tier: decision request (2026-07-05)

**Decision owners (joint):** clinical lead + engineering. **Requested by:** _____ (proposed: within 5 working days — this bounds E4-detection's start; every slipped day is E4-gate schedule risk).
**Scope of this decision:** the detection tier for the §HR clinical flags — **psychosis, mania, dissociation** (E4/B2b), and by the same mechanism coercive-control naturalistic phrasing (E7 beyond the verbatim §6a set). It does **not** touch crisis/SI detection (that is the separate S1→S2/MARBERT track) or E4's *shape* work (B2a, signed and proceeding).

---

## 1. What must be decided
Which detection tier backs the §HR flags, so their ≥95% per-class recall gates are treated as *achievable-as-specified* rather than aspirational. **Until this is answered, E4-detection (B2b) and CF-006 activation cannot start**, and the E4 gate cannot be called reachable.

## 2. Measured evidence (POC harness, `bot_behaviour_recall_baseline.py`, flag-ON ship config)
| §HR class | Keyword-only recall | n |
|---|---|---|
| Psychosis | **6.7%** | 1/15 |
| Mania | **0%** | 0/10 |
| Dissociation | **0%** | 0/11 |
| Psychosis (deployed AR lexicon) | 100% | 4/4 — *self-consistent, NOT naturalistic generalization* |

The naturalistic-English recall floor is **0–6.7%**. The 100% Arabic figure measures the lexicon against itself (transcribed from the deployed set); it validates the path, not generalization.

## 3. What the evidence eliminates
**Keyword-only is not a tuning gap — it is a category error for these flags.** 0% mania / 0% dissociation is not "raise the threshold"; the naturalistic phrasing (spec §HR L1843–1844 — "I haven't slept for days but I feel amazing", "I don't feel real") shares no surface keywords with the deployed triggers. No keyword-list expansion reaches ≥95% on open phrasing. **Option (a) keyword-only is off the table.** This mirrors the S1→S2 escalation crisis already required.

## 4. The two live options
| | **(b) Semantic tier now** | **(c) Hybrid — keyword now, semantic deferred** |
|---|---|---|
| **Mechanism** | Add a semantic detector for the 3 classes, reusing the existing BGE-M3 skill-select infrastructure | Ship E4 shape + keyword detection now; accept the measured ceiling as a *known, documented* gap; defer the semantic tier to a scoped post-POC workstream |
| **Recall reachable** | Plausibly ≥95% — **pending a validated bilingual per-class eval** (see caveat) | No; E4 detection stays at the 0–6.7% floor until the deferred work lands |
| **Latency/cost** | +1 embedding pass on the §HR path (~BGE-M3 encode, already in the stack); no new model | None now |
| **Timeline** | Build + the eval set is the critical path; needs EN + Gulf-AR/MSA/Arabizi §HR eval authored | Fastest to ship shape; detection debt tracked, dated later |
| **Risk** | Semantic viability for these classes is **unproven** (caveat below) | Ships a route whose detection is known-weak; must be explicit that E4 does not yet *detect* mania/dissociation |

**Caveat that must inform the choice (honest gap-flag):** BGE-M3 was found *infeasible* for the distress-vs-passive-SI boundary (2026-06-14, closed — "the bleed IS the safety property"). That result is **domain-specific to SI**; psychosis/mania/dissociation phrasing is more lexically distinctive, so semantic separation is *plausibly* more tractable here — **but this has not been measured.** Option (b) is therefore "semantic tier **conditional on** a validated per-class bilingual eval clearing," not "semantic tier assumed to work." Either option requires that eval before any §HR gate is declared met.

## 5. Recommendation (engineering)
Choose the **direction** now, decouple the **eval** as the shared gate. Recommended: commit to **(b) semantic-tier** as the target, with the bilingual per-class eval as the explicit precondition to calling the gate met — so E4-detection can start building against a decided target while the eval is authored in parallel. If clinical judgment is that the semantic-viability risk is too high to commit pre-eval, **(c)** with a dated deferral is acceptable *provided* E4's shipped shape is documented as "referral route live, mania/dissociation detection pending" so no one reads E4 as fully detecting.

## 6. What this unblocks / depends on
- **Unblocks:** E4/B2b (mania+dissociation detection), CF-006 activation motion, the E7 naturalistic-AR detection debt.
- **Independent of this decision:** E4/B2a shape-work (signed, proceeding now); E3 medical; B0/E7 (shipped).
- **Shared precondition either way:** an authored EN + Gulf-AR/MSA/Arabizi §HR eval set (TD3/TD6-class Arabic debt).

**Requested action:** joint owners select (b) or (c) + a target date for the bilingual eval, and sign below.

| Role | Decision (b / c) | Eval target date | Name | Date |
|---|---|---|---|---|
| Clinical lead | | | | |
| Engineering | | | | |
