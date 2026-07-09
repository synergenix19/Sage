# Clinician Approval Queue (2026-07-09) — rendered content + recommendations, one-touch approve/edit/reject

Each item shows the **rendered wording/patterns** (not just the question), so one approval covers the faithfulness rule. Recommendations are engineering-clinical reads vs best practice + spec (spec_version_sha=56fde86); the ruling is the clinician's.

## 1. §6b/§6c rehome → `interpersonal_effectiveness` (DEARMAN) — RECOMMEND APPROVE
**Why:** spec §6b step-4 *"walks through DEARMAN one letter at a time"*; DEARMAN is `interpersonal_effectiveness`'s core DBT technique (assertive_communication is DESC). So this is the spec-primary skill — fixing a fit error, with the different-neighborhood (margin) benefit as a bonus. The clause is **scoped to §6b/§6c prep**, not the whole boundary/relationship territory.
**Rendered clause (prepended to interpersonal_effectiveness.semantic_description):**
> *"Interpersonal effectiveness DEARMAN skill for preparing a specific difficult, tough, or hard conversation, setting a boundary you need to raise, or wording, drafting, or rehearsing what to say or send before that conversation."*
→ **approve / edit wording / reject.** **PRE-REGISTERED gate acceptance (so the run isn't interpreted after the fact):** id_oos restored to the ~0.9219 band (margin healthy), §6b/§6c recall at-or-near the assertive edit's 10/11 + 12/12, no new anchor leak. If DEARMAN's neighborhood carries its OWN anchor cost and both can't hold → returns as a finding with frontier options, not a silent ship.

## 2. #219 harm-to-others deterministic backstop — RECOMMEND APPROVE Group A, HOLD Group B
**Placement (built this way, PR #240, `active:false`/inert):** this is a **Node-1 crisis-lexicon rule, NOT a skill_select veto.** Explicit intent to harm another is a *safety event* — it must reach the crisis/escalation path + the audit trail, not merely fail to offer a skill. Fires as an S1 keyword flag → **T2 (crisis)** via the existing `s1_any` tier rule (crisis supremacy). Ships inert until you approve; on approval it activates + runs the full gate (crisis-detection recall fixtures, plus downstream-shadow check).
**⚠️ The FP asymmetry INVERTS here — the opposite of every veto shipped.** For OCD/harm-intrusive, broad was safe (a false positive = a warm abstain). Here a false positive is a **crisis card served to someone venting about their boss** — a trust-damaging over-escalation. English AND Khaleeji venting both lean figurative ("I could kill him", "I'll strangle my brother"). So broad is HARMFUL here.
**Group A — explicit intent (recommend APPROVE):** `want/going/planning to hurt him/her/them/someone`, `feel like hurting someone`. (negation_check on, so "I would never hurt him" is suppressed.)
**Group B — figurative/anger-adjacent (recommend HOLD, default NO ACTION pending your ruling):** `could kill him`, `strangle`, `could hurt him`, `might do something I regret`. These the LLM classifier handles better with context; a deterministic lexicon over-escalates them.
→ **approve Group A / rule Group B item-by-item / reject.** (Seed fixtures = Layer-2 transcripts.)

## 3. #218 OCD referral line — RECOMMEND APPROVE (content only)
**Why:** the OCD veto fires but the served copy lacks the spec §1d professional-referral signpost. Pure content edit to the vetoed-OCD Node-3 response; no architecture.
**Rendered copy:**
> *"It sounds like these thoughts are really distressing and hard to sit with. Thoughts like these often respond well to support from a mental health professional who works with OCD, they use specific approaches that can genuinely help. I'm here to keep talking in the meantime if that would help."*
→ **approve / edit / reject.**

## (Item 4 moved OUT of this queue) — Containment Task 0 is an ARCHITECTURE SIGNATURE, not a content approval
Deliberately NOT bundled here: items 1–3 are one-touch content approvals; Task 0 is a heavy architecture signature with two co-signatories (arch-doc owner, PO) and its own dated chase (`2026-07-09-containment-signature-chase.md`, PR #223). Bundling invites clearing the light items and deferring the heavy one. **Task 0 runs on its own channel as the named 07-31 escalation.**


## ✅ APPROVED 2026-07-09 — Vee (clinical lead): item 1 rehome clause, item 2 #219 Group A, item 3 #218 ERP copy (incl. ERP-modality enrichment). #218 rendered-composition + rehome-clause clinician-confirm GIVEN.

---

## 5. interpersonal_effectiveness semantic_description TRIM (591 chars) — AWAITING CONFIRM · DEPLOY HELD
**What changed & why:** the approved rehome clause (item 1) pushed the field to 762 chars, over the 600-char `semantic_description` cap enforced by `test_trimmed_semantic_descriptions_within_cap` (a real CI regression, shipped to master under the then-advisory gate; now fixed, PR #273). To fit the cap I removed only REDUNDANT technique-identity tokens from the DEARMAN body — the duplicate "Dialectical Behavior Therapy relationship skills", "Validation and relationship repair", "Managing interpersonal conflict", and the "Boundary setting" lead-in the clause already covers. **Your approved scoped clause is preserved verbatim**; DEAR MAN / GIVE / FAST and the "family and close relationships" distinction are intact.
**Rendered field (byte-for-byte, the exact 591 chars on master now):**
> *"Interpersonal effectiveness DEARMAN skill for preparing a specific difficult, tough, or hard conversation, setting a boundary you need to raise, and rehearsing out loud what to say before that conversation. DBT interpersonal effectiveness skills module. DEAR MAN assertiveness technique. GIVE skills: Gentle, Interested, Validate, Easy manner. FAST skills: Fair, Apologies, Stick to values, Truthful. Assertiveness in family and close relationships. Expressing needs without shame or guilt. Saying no without destroying the relationship. Balancing relationship, self-respect, and objectives."*
**Status:** the `semantic_description` is a signed clinical field; this is a changed-field edit → needs your one-line confirm. **Mechanism-4 re-gate PASSED** (A/B trimmed-591 vs live-762 on the §6b/§6c/id_oos fixtures: §6b 8/11→8/11, §6c 6/12→**7/12**, id_oos abstain 14/34→14/34, no new leak) — but A/B-identity proves only that the RERANKER can't distinguish the texts; it does NOT substitute for your read of whether the trimmed wording still says what you signed. **Prod stays on the 762 (confirmed) version; the trim is HELD from deploy until this line lands.** Rides the same channel as the T4 content below.
→ **confirm trimmed rendering / edit wording / revert to 762 (accept the cap exception instead).**

## NOTE — item 1's rendered clause above is the STALE pre-scoping wording
The clause quoted under item 1 ("…or wording, drafting, or rehearsing what to say or send…") is the pre-scoping draft; the rehome verdict records you approving the SCOPED clause (message-drafting removed: "…and rehearsing out loud what to say before that conversation"), which is what shipped and what item 5 quotes. Flagged so the record is not read as approving message-drafting language.
