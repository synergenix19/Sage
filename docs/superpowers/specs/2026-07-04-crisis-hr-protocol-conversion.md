# CRISIS (§C) + HIGH-RISK (§HR) Protocol Conversion — BOT BEHAVIOUR → Architecture

**Status:** DRAFT — engineering conversion map for clinician review. No prod change yet.
**Branch:** `feat/bot-behaviour-safety-protocols` · **Source:** clinician "BOT BEHAVIOUR" spec §C, §HR
**Sequencing:** these two universal overrides land BEFORE anxiety tiering (E1/E2) — every other category delegates to them.

Guiding finding: **§C and §HR require no new architecture.** Both map onto approved, in-production machinery. The work is lexicon expansion, content alignment, and verification — done under clinical sign-off, not eng self-assessment.

---

## Part 1 — §C CRISIS (self-harm & suicidal ideation)

### 1.1 Existing machinery it maps onto
| Spec element | Existing mechanism | Notes |
|---|---|---|
| "Destination for every universal crisis override" | `safety_check` → `crisis_response` (bypasses output_gate → END); `skill_executor` re-escalation → `crisis_response` | Override semantics already implemented (arch §2.2/2.3) |
| Graded acuity | `crisis_tier` T1 warm / T2 acute (v7.1, `safety/crisis_tier.py`, kill-switch `SAGE_CRISIS_TIERING`) | Signed 2026-07-03 |
| Canonical trigger table (8 rows) | S1 `crisis_keywords.json` + `passive_si_patterns.json`; S3 BGE-M3 semantic | **This table is the recall test set** |
| Immediate-response principles | `crisis_response` deterministic protocol (resources in-message, stay present) | Content alignment |
| Behavioral guardrails | crisis_response + L0 persona safety block | Content alignment |

### 1.2 Detection gap — THE hard dependency (GL-0)
The canonical table's **passive-ideation, burden, can't-continue, hopelessness** rows are exactly the known recall gap. Current CRADLE recall ~37% / self-harm ~18% vs a ≥95% fail-closed gate = **GL-0 NO-GO for external launch**. Faithful §C is *gated on GL-0* (S2/MARBERT + validated bilingual eval). The distress-vs-passive-SI classifier must **not** ride BGE-M3 (semantic-anchors-infeasible: the distress/SI bleed is the safety property). **Action:** convert the 8-row table into `crisis_keywords.json` + `passive_si_patterns.json` fixtures + a CRADLE recall harness case-set. Corpus/recall is the work here — not routing.

### 1.3 Resource block — DEFERRED (GL-1 commit-2 payload, DO NOT SHIP until dial-test)
Prod currently emits `800 46342` / "24/7" — **retained as-is** under the PO risk-acceptance dated 2026-07-04 (`governance/2026-07-04-production-external-golive-approval.md`). The corrected copy below is the **staged W7 commit-2 payload**; it ships the moment `800 4673` is dial-tested + the L0 artifact is re-signed. Web-verified 2026-07-04:

- **Primary:** National Mental Support Line **800-HOPE / 800 4673** — 8am–8pm daily, AR/EN, WhatsApp. (NOT 24/7; NOT "MoHAP Counselling Line".)
- **Immediate danger:** **999** (lead with 999 ONLY on specific plan / access to means / intent to act now).
- **24/7 mental-health anchor** (for "call now / any time" contexts): Abu Dhabi **800-SAKINA / 800 725462** (psychological first aid, 24/7) — recommended anchor; DHA **800 111** (24/7) alternate.
- **Youth:** Sharjah **800 51115** (9–5, Mon–Fri; outside hours → 999/ER).

Commit-2 surface (9 source files + ~15 test assertions): `config.py` `CRISIS_CONFIG`; `L0_persona.json`; `crisis_content/{en,ar}_uae.json`; `prompt_injection/{clinical_flag_adaptations,third_party_guidance}.json`; skills `post_crisis_check_in`, `psychoed_depression`, `psychotic_referral`. **Off-hours rule:** any "available any time / 24 hours" phrasing currently attached to the primary line must re-anchor on 999 + SAKINA, since 800 4673 is 8am–8pm.

### 1.4 Behavioral guardrails to verify in crisis_response / L0
No categorical confidentiality claims; don't argue feelings ("so much to live for"); don't reinforce help-avoidance; never disengage for behavioral reasons; regional-stigma-aware warmth. Means-restriction safety questions ("Are you safe right now?", "access to something to hurt yourself?", "someone who can be with you?") are the ONLY permitted questions — no exploratory probing before resources.

---

## Part 2 — §HR HIGH RISK (psychosis / mania / dissociation)

### 2.1 Existing machinery — this is the "E4 deterministic HR route"
`skill_select` early-return #3: `psychotic_disclosure` flag active AND referral not yet delivered → `psychotic_referral` auto-selected (no keyword/semantic step). Flag set from `clinical_flag_patterns.json`. `psychotic_referral` is a one-step, non-diagnostic referral skill with L1/L3/L4 escalation. **The deterministic route already exists** — §HR is expansion + shape-alignment, not new architecture.

### 2.2 Gaps vs the spec (verified against `psychotic_referral.json` + `clinical_flag_patterns.json`)
1. **Trigger coverage:** psychosis is represented; **mania is NOT** (no sleepless-euphoria / grandiosity / risk-spending patterns) and **dissociation is partial**. → expand `clinical_flag_patterns.json` with the spec's mania + dissociation phrase lists. Detection risk = Gap #65 (keyword-only, no semantic tier; naturalistic disclosures miss EN+AR).
2. **Shape:** spec wants **one distress question (0–10) FIRST → standardized neutral message → referral**. Current `psychotic_referral` jumps straight to the referral message with no distress-rating step. → add a leading distress-rating step; forbid content follow-up ("who is following you", "what do the voices say").
3. **Escalate-by-distress:** high distress / agitation / danger / mania-driven risk → **Crisis framing (999)**; low distress → prompt to see a professional soon. Current L1 handles risk→crisis; needs the distress-score branch.
4. **Dissociation → safety:** dissociation co-occurs with self-harm → run the §C check and divert to crisis if present.
5. **Hours copy:** `psychotic_referral` says "24 hours a day" / "متاح كل وقت" — same GL-1 defect; rides commit-2 (staged, deferred).

### 2.3 Guardrails to verify
Never confirm/validate delusional/hallucination content as real; never argue against it; stay neutral on content, focus on distress + getting to support; no diagnosis/labels (no "psychosis"/"bipolar"); mania-specific (don't match energy, gently flag pausing big decisions); no coping skill / no psychoeducation-in-the-moment.

---

## Part 3 — What is NEW vs REUSE

| | Reuse (exists) | New (this branch) |
|---|---|---|
| §C | crisis_response, crisis_tier, S1/S3, override routing | 8-row trigger table → fixtures + recall cases; guardrail content verify; **[staged/deferred]** resource block |
| §HR | psychotic_referral, psychotic_disclosure auto-select (E4) | mania+dissociation triggers; distress-rating step; escalate-by-distress branch; dissociation→§C safety check |

**No E1/E2/E3/E5/E6/E7 mechanism is required for §C/§HR.** They exercise E4 (already present) + crisis infra.

## Part 4 — Dependencies & gate summary
- **GL-0** (crisis recall ≥95%): hard gate on faithful §C; external-launch NO-GO until S2/MARBERT clears.
- **GL-1** (helpline): DEFERRED; §C/§HR corrected copy staged as commit-2, fires on dial-test + L0 re-sign. No unilateral eng change.
- **Gap #65** (clinical-flag detection): §HR mania/dissociation recall risk; keyword-tier only today.
- **Clinical sign-off:** every trigger-table, guardrail, and referral-copy change is clinician-owned (Cardinal Rule 4 / Absolute Rule 1).
