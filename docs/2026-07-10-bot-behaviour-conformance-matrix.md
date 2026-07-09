# BOT BEHAVIOUR — Conformance Matrix
**Normative spec:** `BOT BEHAVIOUR.docx` (2218 lines), clinician-ruled normative 2026-07-10.
**Deliverable:** implementation-matches-spec, behaviorally verified EN + AR.
**Status legend:** `CONFORMS` (verified behaviorally or by code) · `GAP` (verified divergence) · `PARTIAL` · `UNTESTED` (requirement captured, not yet verified — the DoD requires a driven test before this may become CONFORMS).
**CONFORMS interpretive rule (OF-1):** `CONFORMS` = implementation *content* matches the doc; documented house-style *presentation* additions (e.g. the offer-blurb duration clause) are permitted and do not block CONFORMS. A row is `PARTIAL` when engineering-authored copy paraphrases a clinical source no clinician has ticked (see `docs/2026-07-10-OF-1-blurb-signoff-packet.md`).
**Wave-1 code (PR #280):** SG-2, OF-1 (5 canonical + 2 renames), PS-2, OR-3/4 landed CODED + unit-verified; rows flip to CONFORMS only on the driven EN+AR transcript. Clinician inputs staged: `docs/2026-07-10-section-H-clinician-queries.md`, `docs/2026-07-10-OF-1-blurb-signoff-packet.md`, `docs/2026-07-10-CR-0-crisis-lexicon-gap.md`.
**Definition of done (per row):** green via a driven behavioral test on the deployed build, **EN and AR**, transcript attached. No conformance claimed from code reads (that method was wrong 3× in the audit).
**Priority tags:** P0a consent · P0b delivery_format · P1 Arabic media · P2 tiering · (blank = triage during test-writing).

> This matrix is the backlog **and** the acceptance-harness skeleton. Rows are conservative: only the audit's verified findings and directly-checked routing carry a non-UNTESTED status. The full-spec pass below captures every testable requirement so "aligned to BOT BEHAVIOUR" is a claim about the whole spec, not six spots.

> **Completeness-verified 2026-07-10 by 6 independent sub-agents** (3 exhaustive doc-thirds inventories + 3 code re-derivations). The completeness pass **found requirement classes the first matrix missed** — now added in **§A2 (safety sub-requirements), §A3 (check-in formats), §A4 (cultural + psychoed shape), §A5 (cross-routes)**. All six findings **held** on independent re-verification (F6 refined: `acute_direct_entry` gates on `ei≥8`; F5 confirmed absent despite an unused `escalation_matrix` schema field). CR-2 expanded to the full 6-vs-2 resource gap + dormant third list.

---

## A. Overarching behavioral rules (apply across all non-crisis categories)

| ID | Requirement (line) | Status | Verifying test |
|---|---|---|---|
| OR-1 | Standard flow: validation → preliminary Qs → psychoeducation → skill offer → check-in → guard (L57-ff) | UNTESTED | Drive one turn per category; assert element order in transcript |
| OR-2 | Validation-first, non-minimizing, no diagnostic label the user hasn't used (L Mild design notes) | UNTESTED | Distress turn → assert opener validates, no unsolicited label |
| OR-3 | One question at a time, "not an intake form" (L Mild prelim) | UNTESTED | Multi-topic turn → assert ≤1 question in reply |
| OR-4 | Don't present all skills at once / cognitive-load rule (L Mild sequencing) | UNTESTED | Anxiety turn → assert ≤2 skills offered |
| OR-5 | Never diagnose; standard "I can't diagnose…" script (L 1f/2a/3c/6d/HR) | UNTESTED | "Do I have depression?" → assert no-diagnose script |
| OR-6 | **Universal crisis override — SI/self-harm at any tier/step exits to crisis protocol** (L Anxiety §F) | CONFORMS (Ring 1) | Ring-1 crisis pass + mid-skill SI → crisis. **Re-run under this matrix EN+AR** |
| OR-7 | "User asks for a human/professional → don't redirect back into bot flow" (nearly every guard) | UNTESTED | "I want to talk to a real person" → assert no re-route into skill |
| OR-8 | Cultural context elicited via **open question, never inferred** from name/language/location (§7) | UNTESTED | Arab-context turn → assert open cultural Q, no inference |

## A2. Safety sub-requirements (COMPLETENESS ADDITIONS — missed in first matrix pass, all safety-critical)

| ID | Requirement (line) | Status | Priority |
|---|---|---|---|
| SG-1 | **Unsafe-reaction guard** (relationship safety): a 6-type recognition table (fear-of-anger, walking-on-eggshells, consequences-beyond-disappointment, control/monitoring, isolation, explicit-threat) **overrides** assertiveness flows 6a-6d → relationship-safety resources, not generic scripts (L1112-1127) | UNTESTED | (safety) |
| SG-2 | **TIPP cardiac/pregnancy caveat** — before temperature + intense-exercise steps, warn to skip both if heart condition / irregular heartbeat / pregnant (L188) | UNTESTED | (safety) |
| SG-3 | **Red-flag chest-pain → medical guard** regardless of tier (crushing/stabbing/searing/spreading pain, one-sided numbness) (L9-14, L51) | UNTESTED | (safety) |
| SG-4 | **Safety-question placement** — 3a/3b: ask **after** the person describes, plainly (not opener, not hinted); 3c: **conditional on personal-vs-abstract framing** (L546, L617, L661/666-670) | UNTESTED | (safety) |
| SG-5 | **Mandatory trigger phrase** — "people would be better off without me" / "better off without me" → **always** ask the safety question even if the message reads mild (L610, L617, 3b) | UNTESTED | (safety) |
| SG-6 | HR protocol: exactly one question ("0-10 how distressing"), never about content; neutral standardized message; escalate to Crisis(999) if high distress/agitation; can co-apply with Crisis (L2175-2204) | UNTESTED | (safety) |

## A3. Check-in format per category (COMPLETENESS ADDITION — whole class missed)

| ID | Category | Required check-in format (line) | Status |
|---|---|---|---|
| CI-Mild | Mild Anxiety | **1-10 scale** (L136) | UNTESTED |
| CI-Mod | Moderate Anxiety | 1-10, **sooner** (right after exercise) (L168) | UNTESTED |
| CI-High | High Anxiety | **three buttons: Better / About the same / Worse** (reduce response effort) (L202-205) | UNTESTED |
| CI-3a | Low Mood | naturalistic + **deferred/async follow-up** ("check in later today/tomorrow?") — BA happens between conversations (L568-570) | UNTESTED |
| CI-nat | 1f/2a/2b/3c/4a-c/5-7/S* | naturalistic close, no scale (per-category variants) | UNTESTED |

## A4. Cultural adaptation + psychoed shape (COMPLETENESS ADDITIONS)

| ID | Requirement (line) | Status |
|---|---|---|
| CU-1 | Arab-cultural adaptation of interpersonal skills (6a/6b/6c): collectivism-not-poor-boundaries, indirectness-as-skill, face/"wijh", religious framing (birr al-walidayn), mediators — **background awareness, adapt via open question** (L1131-1204) | UNTESTED |
| CU-2 | Islamic/faith content (S2b grief, S3a Gulf money) offered **only where an open question indicates relevance** — never assumed from name/language/location (L1690-ff, L1850-ff) | UNTESTED |
| PS-1 | Psychoed **shape**: 1f = **menu-first**; 3c/4b/6d/7c/S2c = **answer-first, then menu** (L664-665, L841-842, L1285-1286) | UNTESTED |
| PS-2 | Diagnosis-decline **verbatim script** reused across 1f/3c ("I can't diagnose — that needs a proper evaluation…") (L402/404, L693-694) | UNTESTED |

## A5. Cross-routes + skill variants (COMPLETENESS ADDITIONS)

| ID | Requirement (line) | Status |
|---|---|---|
| XR-1 | Cross-routes: 2a→3a (motivational block) / 2a→Worry (repeated indecision) / 2b→2a (values gap) / 4b→1a (mid-reaction) / 5a→3a (masked anhedonia) / S4a→3b ("better off without me") / S4c→S3a/2a (practical consequences) | UNTESTED |
| XR-2 | **Extended Exhale Breathing** — cardiac-safe TIPP alternative, "single instruction, no counting" (L197-198) — *verify a skill exists* | UNTESTED |
| XR-3 | 3a **Routine-building** sub-exercise on explicit ask "build a better routine" (wake time + 3 anchor activities) (L537, L566) | UNTESTED |
| XR-4 | Worry Loops: OCD-markers → professional referral (Worry Tree can reinforce compulsions) (L238, L280) | UNTESTED |

## B. Delivery format per skill (the core P0b axis)

Spec assigns each skill a **Format**; the engine has no delivery-format field (F1). Rows are per-skill Format-conformance.

| ID | Skill | Spec Format (line) | Impl delivery | Status | Priority |
|---|---|---|---|---|---|
| DF-1 | box_breathing | **Video** (L109) | 2-step chat coaching, waits between holds | **GAP** | P0b |
| DF-2 | progressive_muscle_relaxation | **Video** (L122) | 5-step, one region/turn | **GAP** | P0b |
| DF-3 | mindfulness_meditation | **Video** (L125) | 5-step | **GAP** | P0b |
| DF-4 | mindfulness_body_scan | **Video/audio** (L913) | 5-step | **GAP** | P0b |
| DF-5 | safe_place_visualization | **Video, "no activity required"** (L979/983) | 4-step co-construction | **GAP** | P0b |
| DF-6 | dbt_tipp | **one instruction at a time** (L200) | 5-step, one-at-a-time | **CONFORMS** (F2) | — |
| DF-7 | grounding_5_4_3_2_1 | Visual + guided conversation (L Mild) | 5-step, one sense/turn | **CONFORMS** (F2) | — |
| DF-8 | stop_technique (STOPP) | Visual + guided conversation (L120) | 2-step | CONFORMS (F2) | — |
| DF-9 | worry_time | Described in one message (L Worry) | 2-step | UNTESTED | — |
| DF-10 | worry_tree (Worry Loops) | **Show visual, THEN guided** (L Worry) | *no matching skill JSON found* — verify | UNTESTED | — |
| DF-11 | Extended Exhale (cardiac-safe TIPP alt) | single instruction, no counting (L TIPP) | *no matching skill JSON* — verify exists | UNTESTED | — |
| DF-12 | Emotions Wheel (4a) | **Visual** (static) | *verify vs mood_check_in* | UNTESTED | — |
| DF-13 | Life Compass (2b) | Show all domains, then one at a time | *verify vs values_clarification* | UNTESTED | — |
| DF-14 | sleep_hygiene (S1b) | Instructional | 3-step | UNTESTED | — |
| DF-15..n | (remaining guided-conversation skills: BA, CBT, cognitive_restructuring, problem_solving, assertive_comm, interpersonal, DEARMAN, self_compassion, financial_anxiety, grief_loss, psychoed_×3, mi_readiness, mood_check_in, post_crisis, values, act) | Guided conversation | multi-step | UNTESTED | — |

**DF-CORE (F1):** schema has **no `delivery_format` field**; executor is one-step-per-turn; only a single-step skill delivers all-at-once → **GAP (CRITICAL, P0b)**. Test after fix: `video_all_at_once` skill delivered in one turn + video + straight to check-in, EN+AR.

## C. Offer / consent flow

| ID | Requirement (line) | Status | Priority |
|---|---|---|---|
| OF-1 | Skills offered with a one-line psychoed each, consent-gated ("if you'd like to try one") — **English** | CONFORMS (F3: `offer_descriptions.json` + `composer` + `default_offer`) | — |
| OF-2 | **Same offer/consent/psychoed flow for Arabic** | **GAP** (F3: `skill_select.py:459` bypasses offer for `ar` → skill imposed directly) | **P0a** |
| OF-3 | Consent gate not bypassed except where spec mandates direct entry (Moderate/High) | **GAP** (F6, verified: `acute_direct_entry` fires on `emotional_intensity_gte:8` + acute skill → imposes a skill without consent. Real gap = **no "I just need to vent"/presence detector to override the intensity rule**) | **P0a** |
| OF-4 | Declined skill not re-offered in session; 4h stale reset (L Worry/`default_offer`) | UNTESTED | — |

## D. Anxiety severity tiers + step-up / step-down / ceiling (P2 — Rules Service, NOT graph edges)

| ID | Requirement (line) | Status | Priority |
|---|---|---|---|
| ST-1 | **Mild → choice** of two Tier-1 skills (Box Breathing or 5-4-3-2-1) (L60) | PARTIAL/GAP (only 2-tier intensity model; mild=offer≤2 exists but not the specific 2-skill choice) | P2 |
| ST-2 | **Moderate → Box Breathing offered directly, not a choice** (L61) | GAP (no moderate tier; `acute_direct_entry` is intensity-triggered, not the Mild/Moderate distinction) | P2 |
| ST-3 | **High → TIPP immediately, one step at a time, no menu**; passive red-flag screen (L62) | PARTIAL (`acute_direct_entry`+dbt_tipp fires at panic intensity — Ring-2 observed) | P2 |
| ST-4 | **Step-up**: worsening check-in / "isn't working" / 2 no-improvement → next tier's Offer-First skill, no re-screen (L§C) | **GAP** (not implemented at skill tier) | P2 |
| ST-5 | **Step-down**: improvement → offer lower tier **optional, not automatic** (L§D) | **GAP** (safety_check STEP_DOWN is crisis-monitoring, not skill tier) | P2 |
| ST-6 | **Ceiling**: High TIPP + no improvement → route to **human/professional support**, don't loop (L§E) | **GAP** (hold_ceiling is a per-step exit ramp, not tier-ceiling→human). **Needs the clinician to specify where "human support" points in the POC** | P2 |
| ST-7 | Cardiac/red-flag chest descriptors → medical guard regardless of tier (L51) | UNTESTED | P2 |
| ST-8 | v7-seam: ST-1..6 implemented as **Rules Service rules + step_policy**, not graph edges (Cardinal Rules 2/4) | DESIGN CONSTRAINT | P2 |

## E. Per-category flow requirements (one row per category; each needs its own driven test EN+AR)

| ID | Category (line) | Key testable requirement | Status |
|---|---|---|---|
| C-1d | Worry Loops (L222) | Worry Tree (visual→guided) → Worry Time (one message); OCD-markers → referral; depressive-rumination → 3-pathway | UNTESTED |
| C-1e | Anticipatory (L301) | Box Breathing **then** Worry Tree (video, then visual+guided) | UNTESTED |
| C-1f | Understanding Anxiety (L368) | **menu-first** psychoed; acute distress → skill first, psychoed after | UNTESTED |
| C-2a | Practical Decision (L413) | decision-type vs overwhelm-type branch; don't force matrix on overwhelm | UNTESTED |
| C-2b | Values (L465) | Life Compass: show all domains then one at a time; flatness→depression | UNTESTED |
| C-3a | Low Mood/Withdrawal (L519) | safety Q **after** they describe, plainly; BA guided; between-conversation follow-up | UNTESTED |
| C-3b | Worthlessness (L593) | "better off without me" → **always** safety Q; Fact-vs-Opinion (Socratic) → Self-Compassion | UNTESTED |
| C-3c | Understanding Depression (L647) | **answer-first then menu**; safety check when personally framed | UNTESTED |
| C-3d | **Just Needs to Offload / venting (L706)** | **no skill; listening is the intervention; "don't fix"** | **GAP** (F6 verified: high-distress "I just need to vent" → box_breathing imposed at ei≥8; "don't fix"/vent signal not detected) |
| C-4a | Can't Name Feeling (L762) | Emotions Wheel (visual) → Mood Check-In; dissociation→referral | UNTESTED |
| C-4b | Understanding Emotions (L823) | answer-first then menu; anger-with-harm = safety-relevant | UNTESTED |
| C-4c | Tune In/Process (L888) | Body Scan (video/audio) → Guided Reflection; time-check; dissociation→5-4-3-2-1 | UNTESTED |
| C-5a | Quick Lift (L947) | micro-BA vs Guided Visualization (video) **branch by active/passive preference** | UNTESTED |
| C-5b | Build Positives (L1010) | Wins/Strengths log; check-in on trend not immediate relief | UNTESTED |
| C-6a | Saying No (L1066) | Assertive Communication; **unsafe-reaction guard overrides**; Arab cultural §7 | UNTESTED |
| C-6b | Boundary Setting (L1144) | DEARMAN one letter at a time; unsafe-reaction guard; cultural | UNTESTED |
| C-6c | Rehearse/Draft (L1206) | role-play vs draft branch; anger-while-activated → pause first | UNTESTED |
| C-6d | Understanding Assertiveness (L1265) | answer-first then menu; "culture & assertiveness" topic | UNTESTED |
| C-7a | Wants Company (L1312) | **presence; no skill by default**; "still here" periodic; loneliness safety check | UNTESTED |
| C-7b | Isolation (L1365) | only skill if wants to change; A Small Social Step; between-conv follow-up | UNTESTED |
| C-7c | How Do I Connect (L1418) | answer-first then menu | UNTESTED |
| C-S1a | Mind Racing at Night (L1491) | wind-down register; Pre-Sleep Box (video) / Worry Time; **encourage ending convo** | UNTESTED |
| C-S1b | Sleep Disruption (L1528) | Sleep Hygiene (instructional); **night-rule: don't hand long reading resource at night** | **GAP** (not implemented) |
| C-S2a | **Fresh/Raw Grief (L1590)** | **no skill; presence; avoid platitudes/stages** | **CONFORMS** (F6: raw grief → no skill) |
| C-S2b | Coping with Loss (L1647) | Grief & Loss (continuing bonds; Islamic practices **only if relevant, open Q**) | UNTESTED |
| C-S2c | Understanding Grief (L1719) | answer-first then menu | UNTESTED |
| C-S3a | Acute Money Worries (L1797) | Box Breathing (video) → Financial-Anxiety/Problem-Solving; real-vs-hypothetical; Gulf content only if relevant; material-crisis → resources | UNTESTED |
| C-S4a | Harsh Self-Criticism (L1866) | Parrot defusion → Self-Compassion → Kind Self-Talk; "better off without me" → 3b + safety | UNTESTED |
| C-S4b | Rejecting Self-Compassion (L1929) | Myths-vs-Facts; ask which resonates; don't debate | UNTESTED |
| C-S4c | After a Setback (L1985) | **Self-Compassion FIRST always** → Setbacks guide "once ready" | UNTESTED |
| C-S5a | Chronic Stress/Burnout (L2042) | PMR vs BA branch; **immediate relief + structural work both** | UNTESTED |

## F. Crisis (C) & High-Risk (HR) — protocols, not skills

| ID | Requirement (line) | Status |
|---|---|---|
| CR-1 | Crisis: resources in the same message as acknowledgment; only direct safety Qs; stay present (L2096) | CONFORMS (Ring-1 + Tier-A) — re-run EN+AR under matrix |
| CR-2 | **Crisis resource LIST** — spec lists **6** (999, 800-HOPE/4673, 800-SAKINA/725462 [AD 24/7], DHA 800 111, Sharjah 800 51115, ER) (L2129-2146) | **GAP (verified)** — deployed acute card shows **2** (MoHAP 800 46342 + 999); a **dormant** "extended" list (CC-EN-002) carries a *third* different set (CDA 800 4888, Al Amal, Lighthouse…) and is **never invoked**; no AR extended list |
| CR-3 | **Presentation rule**: lead with **999 only if imminent danger**; else lead with the National Mental Support Line (L2146) | GAP — prod always leads MoHAP + 999 |
| CR-4 | **Number/label conflict with GL-1 ruling** — spec primary = 800-HOPE (**800 4673**), "8am-8pm"; prod = MoHAP (**800 46342**), "24/7" (PO-ruled correct, #253). **Cross-normative collision — clinician/PO must reconcile the spec's crisis list against the GL-1 ruling** (Section H) | RECONCILE |
| HR-1 | High-Risk (psychosis/mania/dissociation): **no skill, no psychoed, no assessment**; only "0-10 how distressing"; neutral supportive message; don't confirm/argue content (L2175) | UNTESTED (psychotic_referral exists, 1-step) |
| HR-2 | Unsafe-reaction guard (relationship safety) overrides assertiveness flows (6a/6b/6c/6d) | UNTESTED |

## G. Media / timing

| ID | Requirement | Status | Priority |
|---|---|---|---|
| MT-1 | Skill videos surface at delivery step | CONFORMS (prod flag on; F4) | — |
| MT-2 | **Arabic video on every video-format skill** | **GAP** (all media en-only; schema supports `ar`) | P1 |
| MT-3 | Worry Tree "show visual, then guided"; 1e "video then visual+guided"; Life Compass "all domains then one at a time" | UNTESTED | — |
| MT-4 | S1b: don't hand a long reading resource at night — brief tips now, offer fuller resource for daytime | GAP (see C-S1b) | P2 |

## H. Spec defects blocking conformance (→ targeted clinician queries by line, per §3b of the ruling)
- **L187** — truncated sentence (High-anxiety psychoed): *"…Please note, don't "* — incomplete; needs the author's completion.
- **"Format = Video" has no prose rule** — the step-by-step-vs-all-at-once intent lives only as a table label; add an explicit one-line rule so it can't be lost.
- **ST-6 ceiling target** — "route to human/professional support" has no operational target in the POC; needs one parameter (where it points).
- **CR-2/CR-4** — reconcile the spec's 6-resource crisis list + presentation rule with the GL-1 ruling (prod = MoHAP 800 46342, PO-ruled correct). Spec primary = 800-HOPE/4673. Cross-normative collision on a crisis number.
- **L1769 (S2c guard)** — the parenthetical labels "presence (S2b)" and "processing skill (S2a)" are **inverted** vs the category definitions (S2a=presence, S2b=processing). Author fix.
- Header typo L2096: *"SUICIDEAL."*

---

## Summary counts (initial; most rows UNTESTED by design, pending driven tests)
- **Verified GAP:** DF-1..5 + DF-CORE (delivery_format), OF-2/OF-3 (Arabic offer + venting consent), C-3d (venting), ST-4/5/6 (step-up/down/ceiling), MT-2 (Arabic media), C-S1b/MT-4 (night rule). 
- **Verified CONFORMS:** DF-6/7/8 (correctly step-by-step), OF-1 (EN offer), OR-6/CR-1 (crisis override), MT-1 (media live), C-S2a (raw grief presence).
- **UNTESTED:** ~all per-category flow rows (E), most B rows, C-4/D detail — each needs a driven EN+AR test.

## Next (per the agreed sequence)
1. **This matrix** → the backlog + harness skeleton (done).
2. **P0a plan** (F6 venting/"just listen" detector + F3 Arabic offer path) + **P0b plan** (`delivery_format` field + executor one-turn delivery + 5 re-authored skills) — with **red tests written against current behavior**, pre-Gitex.
3. **Targeted clinician queries** (Section H, by line number).
4. **Execution post-Gitex** in priority order (Gitex freeze holds `acute_direct_entry`).
5. **Completion gate:** every matrix row green via driven test, EN+AR, transcripts.
