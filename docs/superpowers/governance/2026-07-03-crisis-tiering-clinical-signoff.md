# Clinical Sign-off Form — Crisis Tiering & Feedback Remediation

**STATUS: ✅ SIGNED — 2026-07-03.** All of G1–G5 + G8 approved as recommended, with concrete POC-sized implementation forms specified by the clinician (below and in plan **§K**, which is the authoritative build spec). G6 = keep fixed Khaleeji for POC; G7 = compliance-parallel; R-series scoped (R5 WhatsApp cut, R7 deferred). **Only remaining external dependency: the G8 compliance dial-test of `800 4673`.**

**Plan:** `docs/superpowers/plans/2026-07-03-crisis-tiering-and-feedback-remediation.md`.
**Original recommendations retained below for the audit trail; the signed concrete values are in plan §K.**

---

## PRODUCT-OWNER RISK ACCEPTANCE — G8 helpline deferral (2026-07-03)
**Decision:** G8 reclassifies from "blocks all crisis-copy" to **"blocks external/pilot exposure."** The dial-test + W7 commit-2 + L0 re-sign are **not** required for the internal-testing phase; they become a **hard release gate for any exposure beyond the internal cohort** (pilot, clinician-external testers, CDA demo, live users).

**What stays true during internal testing:** the app continues to emit `800 46342` labelled "MoHAP Counselling Line" with a "free, 24/7" claim.

**Residual risk (accepted, stated plainly):** internal testers are still people, and the RCA round itself produced genuinely distressed-sounding transcripts. **Bound on the risk:** `999` is co-listed and correct, and `800 46342` **connects to a real support service (IWRC) — mislabelled, not dead.** That is the risk being accepted.

**Owner:** Product owner (synergenix). **Date:** 2026-07-03. **Review trigger:** first approaching external-exposure milestone.
**Signature:** ______________________

**Unchanged by the deferral:** W7 commit-2 (value + label + hours + L0 re-sign + 5 skill JSONs) stays **fully staged on the branch, cherry-pick-ready** — the deferral moves *when* it lands, not *whether* the work is done.

---

### G1 — The T1/T2 boundary  *(blocks W1)*
**Decision:** Does bare hopelessness / low mood / "burden" — with **no** stated intent, plan, or means — belong in the new warm tier (T1) rather than the RED crisis tier (T2)?
**Recommendation:** **Yes.** Route to **T1 (warm)**: "I feel hopeless / low / empty / worthless / like a burden," and English semantic-only (S3-solo) signals. Keep **T2 (RED)** for: any stated intent/plan/means, explicit self-harm, command hallucinations, and all S1 keyword hits (`si_explicit`/`si_passive`). Arabic/Arabizi semantic hits stay **T2** (keyword coverage is weaker there). *Rationale: matches the signed-off L0 line "ordinary sadness/overwhelmed is not a crisis and needs warmth, not a safety check"; production is currently violating it.*
**Also (G1b) — cumulative distress flag:** should a T1 turn write a `flag_for_review`? **Recommendation:** write it **only on repetition** (≥2 T1 turns in a session/window), not every T1 — catches the SF-4 cumulative-distress pattern without flooding the review queue.
☐ Approve as recommended ☐ Amend: ______________________________________________

---

### G2 — T1 warm copy + resource offer  *(blocks W1)*
**Decision:** Approve the tone/wording for a T1 turn (offer resources, don't force).
**Recommended English copy (LLM will vary within this frame, not read verbatim):**
> Validate → gently explore → *offer* (no pressure). e.g. *"That sounds really heavy, and I'm glad you told me. What's been making it feel this way? — and if it ever feels like too much to carry alone, I can share a line where you can talk to a real person, whenever you want that."*
**Rules:** never force the card; never interrogate ("how often/how much"); one question max; the crisis card stays one tap away in the UI regardless (UX Rule 5).
☐ Approve as recommended ☐ Amend: ______________________________________________

---

### G3 — Recall-floor invariant  *(blocks W1)*
**Decision:** Confirm that **no tiering change may reduce measured true-SI recall** — the ≥95% crisis-recall KPI is the hard gate, enforced by a blocking CRADLE + Arabic regression before merge.
**Recommendation:** **Approve.** Detection sensitivity is unchanged; only the *response* to sub-crisis signals is softened. If the regression shows any recall drop, the change does not ship.
☐ Approve as recommended ☐ Amend: ______________________________________________

---

### G4 — De-escalation / exit-from-monitoring criteria  *(blocks W2)*
**Decision:** When may a post-crisis "monitoring" session step back down to normal supportive conversation?
**Recommendation:** step down `monitoring → supportive` after **2 consecutive turns** that S7 reads as clear **AND** with no S1/S3 fire on those turns. S7 re-escalation and all deterministic detection **stay armed** throughout; step-down never relies on S7 alone. Never step to fully "none" in the same session — hold at "supportive."
☐ Approve as recommended ☐ Amend (change turn count / criteria): ______________________

---

### G5 — Arabic mood-rating anchors (instrument fidelity)  *(blocks W4)*
**Decision:** Approve pinning the rating-scale anchors to validated **formal Arabic**, emitted verbatim (not paraphrased into dialect).
**Recommended anchors (already in the skill template, clinically correct):** *"من 1 إلى 10، **واحد يعني صعب جدا وعشرة يعني ممتاز**"* (1 = very hard, 10 = excellent). The conversational wrapper may be Khaleeji; the **anchor clause stays formal and fixed**. *Rationale: validated Arabic instruments are formal MSA (AlHadi 2017); paraphrasing anchors into dialect broke the scale in production ("1 = very good and 10 = very good").*
☐ Approve as recommended ☐ Amend anchor wording: ___________________________________

---

### G8 — Helpline correction + L0 re-sign  *(blocks all crisis-copy)*
**Decision (already product-approved; needs clinical/compliance ratification):** adopt **`800 4673` (800-HOPE), "Mental Support Line", hours 8am–8pm daily**, with **999 co-listed** for out-of-hours; treat `800 46342` as a transcription error; correct the false "24/7" wording. Because the wrong number lives in signed-off **L0 v2.2.0**, this is a **fast-track persona re-sign**.
**Recommendation:** **Approve, conditional on a compliance dial-test** confirming `800 4673` connects and its hours. Sign the L0 copy change.
☐ Approve `800 4673` + 999 + hours copy, pending dial-test ☐ Amend: __________________

---

## Not clinician-blocking (FYI / other owners)
- **G6 (dialect strategy)** — product decision (fixed Khaleeji / MSA-neutral / hybrid). Clinical input needed **only** on instrument wording (covered by G5). Eng will ship the translation-fidelity glossary fix regardless. *Eng lean: hybrid — Khaleeji conversation, formal instruments — but not blocking.*
- **G7 (regulatory scope)** — compliance/legal, runs in parallel; confirm non-clinical wellness posture + "not a crisis service" disclosure.

**Summary sign-off:** ☐ All of G1–G5 + G8 approved as recommended  ☐ Approved with the amendments noted above
**Signature:** ______________________
