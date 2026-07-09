# L2 Engagement Batch — Spec Deviation Register — 2026-07-07

**Recorded by:** Engineering, ahead of the clinical review session for the L2 engagement template batch (info_request v2.0.0 / new_skill / exit_skill / low_confidence rewrite) and the PI-SI-001 blended-intent upgrade.
**Purpose:** Absolute Rule 1 requires every departure from the v7 spec to be **explicit and approved**, never folded silently into a fix. This one-page register carries the deviations a diligent clinical reviewer must see **before** evaluating the template drafts — most critically, the L2 per-intent budget amendment, without which an ~80–150w `info_request` draft is correctly rejected for violating the ~50w L2 spec.
**Signer of record:** `clinical_lead` (role) for items requiring clinical ratification; product owner for POC-scope sanction. Substitute named individuals into the audit trail as needed.

## Why this register exists (read first)

The 2026-06-14 engagement rewrite (PR #4) enriched `L2_general_chat` (→200w) and `L0_persona` but never migrated the other conversational L2 surfaces. `info_request` — which governs every KB/RAG answer — is still `v1.0.0 / 2026-05-22 / approved_by: null / budget 50` with an explicit anti-engagement clause ("Answer clearly and briefly... Do not pad the response with unsolicited support"). The engagement batch closes that gap. Doing so **necessarily** crosses the ~50w L2 budget the v7 spec fixes, so the budget deviation must be ratified as part of this batch, not discovered mid-review.

RCA reference: memory `project_info_request_engagement_gap.md`. Blended-intent trace: PI-SI-001 is **live-but-partial** (a generic symmetric DBT "address both" frame), not the v7 §5.6.1 **ordered** validate-then-inform contract, and single-intent `info_request` bypasses it entirely — so the template rewrite is required regardless of PI-SI-001.

## Deviations

### 1. L2 per-intent word budgets (vs v7 ~50w fixed L2 budget) — **APPROVAL-PENDING**

- **v7 spec position:** L2 intent framing is fixed at ~50 words.
- **Actual state:** already deviated. `L2_general_chat` v1.5.0 = **200w** (approved 2026-06-14). `skill_offer` = 170w, `skill_offer_reoffer` = 90w, `general_chat_directive` = 100w. All the pre-engagement surfaces remain at 50w.
- **Amendment requested:** replace the single ~50w L2 ceiling with **explicit per-intent budgets**. Target ranges for the engagement batch, aligned to the Intelligence Evaluation R-1 word targets: psychoeducation / `info_request` **80–150w**; `new_skill` and `exit_skill` sized to their contracts; `low_confidence` stays **≤50w** (short clarifying turn, behaviour-frozen — see item 4).
- **Headroom:** the cumulative six-layer prompt stays under the `_TOTAL_WORD_BUDGET` ~1100w ceiling; L0 alone is ~684w and total composed prompts remain within budget. No ceiling change requested.
- **Coupled defect (do not land independently):** the overflow-guard/L1-budget accounting has a pre-existing bug (issue #125, `test_compose_prompt_no_overflow_with_large_cultural_override` fails on master). The per-intent budgets touch the same `_compute_l1_budget` accounting. **Fix #125 as part of, or immediately before, wiring the new budgets** so the accounting is corrected once against the new numbers.
- **Status:** requested; ratify in the batch review session. Until ratified, template drafts >50w carry `approved_by: null` and must not ship.

### 2. Intent-taxonomy simplification — no `emotional_support` intent — **RECORD / SANCTION**

- **v7 spec position:** the §5.6.1 blended example presumes an emotional-support primary (distress) blended with an info secondary.
- **Actual state:** the POC intent enum has **8 categories** and **no `emotional_support`**: `skill_continuation | new_skill | general_chat | crisis | info_request | exit_skill | scope_refusal | jailbreak`. Distress maps to `general_chat` (brief affect) or `new_skill` (specific symptoms). This is a workable POC simplification.
- **Consequence for blended intent:** an emotional+factual turn classifies as `new_skill`/`general_chat` primary + `info_request` secondary (per the classifier's own example). It shapes how the PI-SI-001 upgrade (item in the batch) must be written and tested, and how blended intent behaves at scale.
- **Status:** undocumented divergence from the v7 taxonomy; recorded here for completeness. No behavioural change requested — flag for awareness in the PI-SI-001 review.

### 3. POC deploy-target / data-sovereignty deviation — **SANCTIONED BY PROTOCOL (recorded for completeness)**

- **v7 spec position:** sovereign / in-region hosting for clinical data.
- **Actual state:** POC deploy targets and external LLM usage are already sanctioned for the POC phase under the documented data-sovereignty protocol (synthetic test assets ≠ clinical data; external LLM in the loop is PDPL-considered for POC).
- **Status:** already covered by protocol; **not a new deviation and not blocking this batch.** Recorded solely so the register is a complete picture of active departures, not because it needs re-approval here.

### 4. `low_confidence` historical composer bypass — **REMEDIATED (PR #124)**

- **v7 spec position (§5.6.3):** all prompt templates in the CMS, version-controlled, with L0 always composed.
- **Prior state:** `low_confidence_respond_node` used a hardcoded `_SYSTEM` string and bypassed `compose_prompt` entirely — L0 never composed on that surface. An outright §5.6.3 violation.
- **Remediation:** PR #124 migrates the node to `compose_prompt(l2_intent_override="low_confidence")` (mechanism-only, behaviour-frozen; freeflow-only blocks suppressed on the path). Engineering-reviewed.
- **Residual for THIS batch:** the `low_confidence.json` content is behaviour-frozen and remains `approved_by: null`. Its real engagement rewrite is one of the four template drafts under clinical review in this batch. **Merging PR #124 does not confer content approval.**

## What clinical sign-off in this batch clears — and what it does not

Clinical sign-off in the batch review session clears the **clinical content gate** for: (i) items 1's per-intent budget amendment (ratification), and (ii) the four template drafts + the PI-SI-001 ordered-contract upgrade (`approved_by` set, `status: approved`). It does **not** clear:

- Engineering review of PR #124 (separate, done) or the L2-enumeration regression test (separate small eng PR).
- Any measurement/scoring gate that applies to engagement quality.
- Merge/deploy authority (product owner triggers; deploys are manual — neither Railway nor Vercel auto-deploys on merge).

## Cross-references

- PR #124 — low_confidence composer migration (item 4).
- Issue #125 — overflow/L1-budget accounting defect (coupled to item 1).
- Memory `project_info_request_engagement_gap.md` — RCA + blended-intent trace + approved sequence.
- Template drafts (this batch) — `docs/superpowers/drafts/2026-07-07-l2-engagement-*` (to follow).
