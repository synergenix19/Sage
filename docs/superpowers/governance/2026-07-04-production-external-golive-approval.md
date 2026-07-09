# Production External Go-Live — Approval Requirements

**Requested:** 2026-07-04 — "push this live in production."
**Prepared by:** engineering. **Requires:** product owner + clinical lead sign-off (this document).

---

## READ FIRST — what "live in production" means here

**Everything built in this cycle is ALREADY deployed and running on production** for the **internal tester cohort** (crisis tiering / item A flag ON, W4 Arabic mood anchor, v7.2 Node-2 keyword pre-pass, W5 therapy-term glossary, C+D lexicon). Nothing below is about deploying code — it is deployed.

**"Push live in production" = opening the app to EXTERNAL / real users** (pilot, patients, CDA demo, public) — i.e. anyone beyond the internal test cohort. That crosses the **external-exposure gate**, which has been deliberately parked. This document is that gate.

---

## 🔴 HARD BLOCKER — cannot be signed away by anyone

### GL-0 · Crisis-recall pilot KPI (Gate 1) — currently FAIL, external go-live is NO-GO
- **KPI:** ≥95% crisis recall. **Production today: ~37%** (S1-lexicon 86/232 on CRADLE EN; **Arabic UNMEASURED**).
- This is a **signed, fail-closed NO-GO** (gate `fedd99f`) — a documented P0 ([[project_safety_detection_baseline]]).
- **A wellness app that misses ~63% of crisis disclosures cannot be opened to real users at risk.** The tiering work made the *response* graded and the *UX* better; it did **not** raise detection recall (it can't — recall is a detector property).
- **The only thing that clears this: S2/MARBERT** (the trained bilingual crisis classifier, issue #18 — **not yet built**), plus a validated bilingual (EN + Gulf-AR) eval set.
- **No clinician or product-owner signature can waive this.** It is a duty-of-care floor. Until recall clears the KPI on a validated bilingual eval, external exposure stays NO-GO.

> **This is the honest headline: we are not ready to go live to external users, and the reason is detection recall, not anything approvable on this page.** The items below are the *remaining* gate — necessary but NOT sufficient while GL-0 fails.

---

## 🟠 SAFETY-CRITICAL FIX — required before ANY external user (independent of GL-0)

### GL-1 · Correct the crisis helpline (W7 commit-2) — ☐ clinician sign-off
Production currently emits **`800 46342`** labelled **"24/7"**. Both are wrong:
- Correct national line: **`800 4673`** (800-HOPE / "Mental Support Line"), hours **8am–8pm daily** (NOT 24/7).
- Fix rides the staged W7 commit-2: swap value + label + hours in `config.py`, the rules JSONs, **and `L0_persona.json`** (which hardcodes `800 46342`), + the 5 skill-JSON edits.
- **Requires:** (a) **dial-test** of `800 4673` (confirm it's live + correct), (b) **L0 fast-track re-sign** (persona artifact), (c) clinician confirmation of the copy.
- For the **internal cohort** this was a product-owner risk acceptance (G8: mislabelled-not-dead, 999 co-listed). **For external users that acceptance does NOT hold** — a real at-risk user must get a correct, reachable line.

> **⏸️ DEFERRED — product-owner risk acceptance (2026-07-04).** Owner directed: keep the current helpline `800 46342` / "24/7" **as-is for now, correct later.** This extends the existing G8 internal-cohort risk acceptance to remain in force. **Residuals explicitly accepted:** (a) `800 46342` is mislabelled (IWRC, reachable-but-not-the-ideal-line); (b) the "24/7" hours claim is FALSE for any UAE mental-support line — a user told 24/7 may find it unavailable off-hours; `999` emergency is co-listed and always correct. **Not changed unilaterally by engineering.** **Re-arm condition:** the correction (→ `800 4673` / "Mental Support Line" / "8am–8pm", W7 commit-2 across config + rules JSON + L0 re-sign + 5 skill JSONs) ships the moment `800 4673` is **dial-tested + confirmed** — the dial-test is the human action engineering cannot perform. This deferral does NOT lift GL-0.

☐ **Clinical lead:** helpline copy `800 4673` / "Mental Support Line" / "8am–8pm" approved, dial-test confirmed. Date: ______

---

## 🟡 OUTSTANDING CLINICIAN APPROVALS (the G4-b consolidated form — needed regardless)

### GL-2 · Monitoring-turn conversational copy (G4-b) — ☐ clinician sign-off
Post-crisis monitoring turns currently repeat a canned card (the F2 "sticky card" complaint). W2 shipped the step-down *mechanics*; the *copy* frame needs wording sign-off. Full draft: `governance/2026-07-04-G4b-monitoring-copy-form.md`.
☐ **Clinical lead:** monitoring posture frame approved (or amended). Date: ______

### GL-3 · Infidelity → mood_check_in (W6 fix #3) — ☐ clinician decision
"i just found out my partner cheated" routes to freeflow support, not mood_check_in. Is that correct? (Eng recommendation: freeflow support is appropriate.)
☐ Freeflow support correct (no change)  ☐ Route to mood_check_in. Date: ______

### GL-4 · L0 dialect line (W5 / G6) — ☐ verification, likely no action
No false "mirrors your dialect" claim was found in `L0_persona.json` (already tone/register-scoped per v2.2.0).
☐ **Clinical lead:** confirmed, no edit needed  ☐ residual line to fix at: ______

---

## 🟡 ENGINEERING / GOVERNANCE PRE-CONDITIONS (no clinician sign-off; eng owns)

| # | Item | Owner |
|---|------|-------|
| GL-5 | **Gate/strip `/health/version` deep diagnostics** (currently UNAUTHENTICATED — exposes module paths, PYTHONPATH, resolver, flag). Must be auth-gated or stripped before external exposure. | eng |
| GL-6 | **§G monitors run CLEAN on real crisis traffic.** Day-one check (2026-07-04) verified the write path but was trivially clean — **0 real crisis/distress turns**, 6 sessions/48h. Invariants unexercised. Needs meaningful crisis-traffic exposure before "clean". | eng + PO |
| GL-7 | **Pilot consent / onboarding / PDPL data-subject flows** — MVP-phase items, out of the POC AI-layer scope but required for real users ([[project_poc_scope_boundary]]). | product |
| GL-8 | Arabic crisis eval set built (no CRADLE-AR corpus exists) — needed to even MEASURE the Arabic half of GL-0. | eng/clinical |

---

## Summary — what approval do you need?

1. **You cannot go live to external users now.** GL-0 (recall ~37% vs ≥95%) is a fail-closed NO-GO that no signature waives. Requires **S2/MARBERT** + a validated bilingual eval. This is the real blocker.
2. **Even setting GL-0 aside, before any external user you need:** GL-1 helpline fix (clinician + dial-test), GL-5 endpoint hardening, GL-7 consent/PDPL flows.
3. **Clinician signatures needed on this page:** GL-1 (helpline), GL-2 (monitoring copy), GL-3 (infidelity), GL-4 (L0 verify). GL-2/3/4 are the consolidated G4-b form.
4. **For the INTERNAL cohort (already live):** the only outstanding clinician item is GL-2/3/4 (the G4-b form). Internal exposure is covered by the existing G8 risk acceptance.

**Recommended path:** keep prod on the internal cohort; relay the G4-b form (GL-2/3/4) to close W2; land GL-1 helpline fix + GL-5 endpoint hardening as the external-gate prep; and treat **GL-0 (S2/MARBERT recall) as the true critical path to any external launch.** Do not open to external users until GL-0 clears.

**Signatures**
Product owner: ______________  Clinical lead: ______________  Date: __________
