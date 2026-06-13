# Work Order — Human-Scoring Protocol (PR #4 pending-human items)

**Date opened:** 2026-06-13
**Owner:** Clinical lead (English rubric scoring + acceptance gate); native Khaleeji-speaker reviewers (Arabic dimensions)
**Source:** PR #4 audit PENDING-HUMAN items + [sign-off alignment check](../audits/2026-06-13-signoff-alignment-check.md) §6
**Blocking:** recording the PR #4 clinical sign-offs (English offer-turn quality evidence) and Arabic exposure (Khaleeji register evidence + blurb acceptance)
**Why this exists:** the original plan was single-rater on both sides, with the Arabic reviewer scoring the transcripts that set the register bar *and then* accepting the blurbs against that bar — a calibration circularity with no external standard in the loop. The floor common to psychometrics and lightweight NLG evaluation alike is two raters + an agreement statistic (COSMIN PMC2957386; van der Lee et al., ACL W19-8643). This is the minimum defensible measurement for a system under DESC accountability, not a nicety. Honest scope note: COSMIN/Beaton are written for validated outcome instruments and are arguably over-strict for microcopy; the protocol below applies the *floor* (two raters + agreement), not full instrument-grade compliance.

---

## Element 1 — English offer-turn quality (11 turns, 7-point contract rubric)

- **Raters:** the original clinician PLUS a second clinician, scoring independently. With only 11 items, sampling is pointless — both score all 11 (~1 hour each).
- **Rubric:** the offer-turn contract (names the user's disclosure; ≤2 options; durations stated; keep-talking alternative present; no exercise content in the offer turn; no clinical jargon; no pressure), scored per turn.
- **Agreement:** report weighted Cohen's kappa (ordinal) or Krippendorff's alpha. Adjudicate any turn where the two raters differ by ≥2 points.
- **Pass:** alpha ≥ 0.67 → rubric usable, scores stand. Below 0.67 → the *rubric* needs anchor descriptions per scale point (not the content); re-score after anchoring.
- **Source material:** the 11 EN offer turns in `docs/superpowers/audits/2026-06-13-engagement-pr4-audit-transcripts.md`.

## Element 2 — Khaleeji Arabic transcript scoring (C-7 dimensions)

- **Dimensions:** grammar, naturalness, register, gendered forms (the four flagged in the audit; "naturalness"/"register" in a diglossic context are exactly where single-idiolect bias dominates — Emirati/Qatari/Saudi-Gulf variation is real).
- **Raters:** reviewer 1 (the original native Khaleeji speaker, who remains the blurb acceptance gate) PLUS a second native Khaleeji speaker (need not be clinical) who double-rates a 20–30% sample of the transcripts on the four dimensions.
- **Calibration (breaks the circularity):** before scoring, both reviewers agree a small anchor set — 3–5 examples per dimension at high and low — in one calibration session (~half a day). The anchors are the external standard that enters the loop; without them, reviewer 1's preferences silently become the acceptance bar.
- **Agreement:** report per-dimension agreement on the double-rated sample. Any item reviewer 2 flagged routes to joint adjudication.
- **Division of authority:** reviewer 1 stays the acceptance gate for authored blurbs; reviewer 2 exists to break the self-referential loop, not to override.

## Element 3 — Direct Khaleeji blurb authoring (not back-translation)

Endorsed as the authoring method (ahead of instrument-grade back-translation practice; see alignment check §5). Two conditions attach:
1. **Intent fidelity check:** a bilingual clinician verifies each authored blurb's clinical *intent* against the English contract — this is the source-anchoring that skipping back-translation would otherwise lose. Verify intent, not wording.
2. **More than one set of language intuitions** touches the content (covered by Element 2's second reviewer + calibration). The authoring/review must not collapse back into a single reviewer.

The Khaleeji-explicit register guidance (MSA-correct is not the bar; "خمس عشر دقيقة" → "ربع ساعة" precedent; position-[0] skill-JSON Arabic examples as the in-repo reference; gendered-form flagging) lives in the blurb work order that the S2-2 plan produces; this protocol governs how that work order's output is scored and accepted.

---

## Cheapest-path summary

| Element | Original | Floor-meeting upgrade | Cost |
|---|---|---|---|
| 1 — EN offer turns | 1 clinician, 11 turns | +1 clinician scores all 11; weighted kappa; adjudicate ≥2pt gaps | ~1 hr |
| 2 — Khaleeji transcripts | 1 reviewer scores + accepts | +1 native speaker double-rates 20–30%; anchor calibration session; reviewer 1 stays gate | ~half day |
| 3 — Blurb authoring | direct authoring (good) | + bilingual intent-check vs EN contract; ≥2 language intuitions | folded into 2 |

## Critical-path note — start the Khaleeji calibration today

Element 2 is now on the critical path to Arabic launch (S2-2), so it must not drift as a "nice to have." The **long pole is the half-day Khaleeji calibration session**, which needs two things lined up before it can run: (1) **reviewer 2 identified** (a second native Khaleeji speaker, non-clinical is fine) and (2) **the anchor examples prepared** (3–5 per dimension at high/low). Both can start today, before the English scoring (Element 1) completes — the three human tracks (Element 1, Element 2, and the acute re-decision) are independent and should run in parallel, not in series. Identifying reviewer 2 and drafting anchors is the action to take first; the scoring itself is fast once the calibration is done.

## Status

OPEN. Gates the English offer-turn sign-off evidence and Arabic exposure. **Element 2 (Khaleeji) is the long pole — start reviewer-2 identification + anchor prep now.** Not started.
