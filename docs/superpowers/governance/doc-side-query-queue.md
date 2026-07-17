# Doc-side query queue — amendments/clarifications owed by the BOT BEHAVIOUR document itself

Running queue of questions/errata about the **normative document** (distinct from the code and from the clinician *ratification* packet). These are "fix the source" items — if the doc keeps them, every future reader re-derives the same error. Route at the next doc-owner touchpoint.

| # | Doc location | Query / erratum | Why it matters | Raised |
|---|---|---|---|---|
| DQ-1 | Format column, §1f rows ("Give options from 1f") and §6d row ("Info (6d)") | The **Format** column contains **disposition/routing** values (a routing destination — "go to the 1f/6d menu"), not delivery values. Confirm the Format column should carry **delivery-only**, and move these routing directives to the disposition/prescription column. | The disposition-vs-delivery axis conflation we spent a session removing from the *code* exists in the *normative doc's own column*. If unfixed, every future reader re-derives the category error from the source. (Quiet vindication of the pair-level reframe: the orthogonality is the doc's own structure, imperfectly executed here.) | 2026-07-17 (P0b grounding) |
| DQ-2 | Format column, `worry_time` (§1d vs §S1a) and `problem_solving_therapy` (§1e/§2a/§S3a vs §1d/§S5a) | These skills carry **different Format values depending on invoking category**. Confirm this is **intentional** (format-depends-on-presentation, which the P0b override seam then represents) or an **authoring inconsistency** to reconcile at source. | Determines whether the (presentation, skill) override is representing real clinical intent or papering over drift. | 2026-07-17 (P0b grounding) |

*(The clinician ratification items — enum members, the sharpened `staged_iterative` call, the 4 Format-less-skill defaults, §3c/§4a/§7c content — live in the ratification packet, not here. This queue is only for changes to the document.)*
