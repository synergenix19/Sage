# PR #4 Sign-off Package — Independent Best-Practices Alignment Check

**Date:** 2026-06-13
**Trigger:** Clinicians signed off on the PR #4 draft artifacts + the `criteria_hold_count` schema extension; before recording the sign-offs, an independent literature check was run on the *clinical-design decisions being signed* so nothing is ratified that the evidence contradicts.
**Method:** three targeted research passes (peer-reviewed / clinical-guidance sources preferred over blogs; actively searched for contrary evidence, not confirmation) against (1) the consent-gate design decisions, (2) the psychotic-referral handling, (3) the human-scoring design.
**Outcome:** aligned on most; **two items should not proceed as signed.** Both have cheap, evidence-aligned fixes. The product owner endorsed both adjustments and held the sign-offs pending resolution.

---

## Verdicts

| Decision | Verdict | Disposition |
|---|---|---|
| Acute direct-entry: no menu at intensity ≥8 | **Aligned** | Keep — cognitive-load rationale is sound (PFA/crisis directiveness) |
| Acute `ignore_declined`: override a prior decline of the *same* technique | **Contradicted** | **Amend** — substitution package, clinical re-decision required (see [acute-substitution-redecision](../escalations/2026-06-13-acute-substitution-redecision.md)) |
| Decline persistence: session-scoped, may re-offer next session | **Aligned** | Keep — two non-blocking enhancements backlogged |
| R5 one-hold pacing budget | **Aligned** | Keep — exit-ramp wording refinement folded into the draft (autonomy-supportive constraint) |
| S2-10 psychotic referral: interrupt timing + prompt-vs-gate | **Aligned, strengthened** | Research promotes both open questions to evidence-backed answers; routing fix still Rule 1 + clinical gated |
| Direct Khaleeji authoring (not back-translation) | **Aligned-with-conditions** | Keep — ahead of instrument-grade practice; conditions in scoring protocol |
| Human scoring: single rater each side | **Below measurement floor** | **Upgrade** — two raters + agreement stat (see [human-scoring-protocol](../work-orders/human-scoring-protocol.md)) |

---

## 1. Acute-distress consent bypass — `ignore_declined`

**Aligned-with-conditions: directive *entry* supported; overriding a prior "no" to the same exercise contradicted.**

Supporting the no-menu entry: crisis models are genuinely more directive than ordinary therapy (Psychological First Aid prioritizes directive, action-oriented stabilization; the MI literature concedes a strictly evocative non-directive stance is "ethically and clinically inadequate" where safety is at stake — the righting-reflex prohibition relaxes in acute crisis). Agitated users have reduced information-processing capacity, so launching a simple exercise rather than a multi-option menu has a real cognitive-load rationale (Project BETA de-escalation consensus, PubMed 22461917; PanicToCalm proactive-guidance agent, arXiv 2510.21143).

Contradicting `ignore_declined` (three independent lines):
1. **Project BETA** lists *"offer choices and optimism"* as one of its ten de-escalation domains — choice is *part of* de-escalation for agitated patients, not an obstacle. The directive element is structure and limited options, not removal of choice.
2. **Trauma-informed care** treats choice during overwhelm as the mechanism of recovery ("each small yes or no teaches the nervous system it can influence outcomes"); overriding a remembered refusal is the textbook TIC failure mode (wtcs nursingmhcc 15-3).
3. **Bioethics** grounds overriding a refusal in *lack of decision-making capacity, not distress intensity* (Karger clinical ethics 30/1/17; AMA Journal of Ethics, overwhelmed patient, 2016-09). Panic 8/10 is not incapacity.

The "low-risk" framing does unearned work: breath-focused work can be *activating*, not calming, for trauma survivors (suffocation/choking histories; over-breathing → hyperventilation). A prior decline of a breathing exercise may be clinical signal, not friction — which is the entire reason entry screens exist. "Safety over preference" only carries for crisis-line handoff, not a low-risk somatic exercise.

**Evidence-aligned fix:** direct entry stays (no menu); a declined acute skill is substituted by the first non-declined member of the acute set, entering the declined one only if all are declined (safety floor). Full package + diff in the linked re-decision doc. Also resolves an internal contradiction: the session-scoped decline rule was being nullified by `ignore_declined` for exactly the acute skills.

## 2. Decline persistence — **Aligned**

Within-session suppression matches the dark-pattern literature exactly (re-prompting after refusal = nagging/coercion: NN/g deceptive patterns; felt-manipulation study arXiv 2010.11046). Cross-session re-offering is separately supported clinically (MI: declines "plant seeds," readiness changes between sessions; Leeds MI guide). Two non-blocking enhancements backlogged: (a) the cross-session re-offer should acknowledge the earlier "no" rather than silently reset (needs cross-session decline memory we don't yet have); (b) a durable "don't suggest this again" opt-out should exist somewhere.

## 3. R5 one-hold pacing budget — **Aligned**

SDT-based digital-health research shows autonomy-supportive (invitational) language improves engagement while controlling/insisting language undermines it (PMC6393822); users of CA-led anxiety programs explicitly request pacing control (JMIR Human Factors 2025 e76377); repeated identical questions are the conversational form of nagging and drive disengagement (arXiv 2602.05111). **Condition (folded in):** two minimal answers are ambiguous between "respecting my brevity" and "I'm checked out" — the move-forward is paired with a lightweight exit ramp, phrased as the user's choice of pace and never as the system wanting to wind down (an exit ramp that signals system disengagement is its own nudge). Implemented in `soft_advance_instruction.json` v0.2.0 (draft-pending-review) on the feature branch.

## 4. Psychotic referral (S2-10) — **Aligned, strengthened**

The research converts two open clinical questions into evidence-backed recommendations. Detail appended to [the escalation doc](../escalations/2026-06-13-psychotic-referral-reachability.md). Summary: interrupt on the next turn (every un-redirected turn is a draw from a documented collusion distribution); prompt-level adaptation is acceptable only as the *tone* of the redirect, never as the *gate* deciding whether the redirect fires (the studied bots were already prompt-adapted and still colluded). The routing fix remains a safety-surface control-layer change under the normal Rule 1 + clinical gate.

## 5. Direct Khaleeji authoring — **Aligned-with-conditions**

Beaton/back-translation was written for validated psychometric instruments; chatbot UX microcopy carries no such psychometric load, and back-translation is itself criticized in modern survey methodology (translationese; TRAPD/Behr-Hanke favor team-based original-language drafting). Direct dialect authoring with register guidance is closer to current best practice than translation-back-translation. **Conditions:** a bilingual clinician verifies each blurb's clinical *intent* against the English contract (the fidelity check back-translation would otherwise provide), and more than one set of language intuitions touches the content — both captured in the scoring protocol.

## 6. Human scoring — **Below the measurement floor**

Single-rater everywhere, plus a calibration circularity: the same Khaleeji reviewer scores the transcripts that set the register bar and then accepts the blurbs against that bar — no external standard enters the loop. The floor common to psychometrics and lightweight NLG evaluation alike is two raters + an agreement statistic (COSMIN PMC2957386; van der Lee et al. ACL W19-8643). Cheap upgrades specified in the [scoring protocol](../work-orders/human-scoring-protocol.md). Honest caveat: COSMIN/Beaton are written for outcome instruments and are arguably over-strict for 11 microcopy turns — but "two raters + an agreement stat" is the floor, and it is currently unmet.

---

## Governance note

Routing the `ignore_declined` decision back to the clinical lead *with the contrary evidence attached* is not a delay — it is what makes the eventual signature mean something. Signing the original now and discovering BETA/TIC/bioethics later would mean the clinical lead signed something they had not fully seen. Present the evidence; they re-affirm or amend; either is clean. The same logic applies to the scoring upgrade: a sign-off resting on single-rater evidence is weaker than the rest of this effort's evidentiary standard.

**Status:** assessment delivered; the two amendments are the gating items before sign-offs are recorded and PR #4 merges. Everything else proceeds as signed.
