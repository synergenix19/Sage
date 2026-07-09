# Semantic Routing (V2) — Approvals & Sign-off

**For:** clinical lead · native Khaleeji reviewer · product owner
**Date:** 2026-06-24 · **Purpose:** the inputs needed to proceed with the semantic-routing (V2 retrieval-core) evaluation, so it can be signed off in one pass.

## What you are approving (read this first)
Approving this does **not** flip V2 on in production. It authorizes **completing the held-out evaluation**: freeze the eval set → run the calibration + flip-gate → **V2 ships only if it beats the current router (V1) on the gate, within every language × stratum cell.** The current V2 build was measured to *regress* without calibration, so "ship V2" is conditional on it actually winning — not a foregone conclusion. This sign-off unblocks the *evaluation*; the gate decides the *flip*.

**One human gate stands between here and that evaluation: freezing the eval set.** Everything after it (freeze → calibrate → gate → wire → deploy) is engineering. The freeze is blocked only on the items below.

---

## Open approvals / inputs needed

### A. Native Khaleeji reviewer — author the 3 Arabic eval cells  **(the binding constraint)**
The English side is complete and power-sufficient. The Arabic cells are empty of native-authored cases and are the *only* thing blocking the freeze. Spec + kickoff are ready (`2026-06-23-arabic-cells-build-RECOMMENDATION.md`, `2026-06-23-native-reviewer-kickoff.md`).
- [ ] `ar/in_scope` (~30), `ar/far_oos` (~30), `ar/id_oos` (~66) — authored natively, route labels confirmed.
- [ ] **Register decision:** casual typed-chat (recommended) vs formal — applied consistently.
- [ ] Confirm the case-29 **Arabic cardiac red-flag idioms** (native phrasing; clinical floor already set).

### B. Clinical lead — two items still open
- [ ] **Collectivist-route joint read** (with the native reviewer). Conditional, do-not-rubber-stamp: natural coaching → confirm `assertive_communication`/`interpersonal_effectiveness`; imported "boundary" script → prefer a differently-framed skill or ABSTAIN. **Must happen before/while `ar/in_scope` interpersonal cases are authored**, not after (else those cases are authored against an unsettled label).
- [ ] **Route-label confirmation** within the AR cells as they're authored (esp. the faith-framing risk-screen and ABSTAIN-control cases — methodology already signed; this is per-case confirmation).

### C. Product owner + clinical lead — formalize the calibration values (already endorsed, need signatures)
These were endorsed in review; this just records them.
- [ ] **Per-cell mis-route tolerance:** `in_scope`/`far_oos` ≤10% · `ar/id_oos` ≤4.6% (Arm A) · `en/id_oos` ≤4.6% · crisis/path-assertion cells: no % (harm gate only).
- [ ] **Stopping rule:** the bound holds only at *zero* mis-routes; one mis-route at N≈65 fails the cell.

---

## Already signed (for traceability — no action needed)
- ✅ Retrieval-core approach / spec rev4; the eval methodology + EN dataset.
- ✅ Dispositions: anger → ABSTAIN, substance → ABSTAIN, anger+aggression → ESCALATE.
- ✅ Case-29 cardiac-somatic: stratified route + `MEDICAL_REFERRAL`; harm-OCD↔postpartum-psychosis contrast; ED `safety_net`.
- ✅ Faith-framing 3-way split; Arm A (#4 mis-route arm).

---

## Recommendation
**Proceed.** The fastest and only real path is to **start the native Arabic authoring now** — it's the long pole and nothing downstream can run until it's done. Concretely, in order:
1. Schedule the **collectivist joint read** (clinical lead + native reviewer) — it gates the interpersonal cases, so it goes first.
2. Native reviewer authors `ar/in_scope` + `ar/far_oos` (then `ar/id_oos` ~66).
3. Product owner + clinical lead **sign the calibration values** (Section C) — these can be signed today, in parallel.

Once those land, the engineering is mine and fast: freeze → calibrate → run the gate → and **if V2 wins, wire it behind the flag, prove flag-off is byte-identical to prod, deploy, flip.** If V2 loses the gate, it stays off and we iterate — so this is a route to a *decision*, with a real chance the decision is "not yet."

**Keep distinct:** shipping V2 improves *routing*; it does **not** make the pilot safe to widen. The crisis/safety gates (recall, red-flag detector, the freeflow backstop) are a separate, orthogonal track and are unaffected by this sign-off.

---

## Sign-off
```
Native Khaleeji reviewer (AR cells + register + idioms): ______________  Date: ______
Clinical lead (collectivist read + route labels + values): ____________  Date: ______
Product owner (calibration values):                         ____________  Date: ______
```
On these, the eval set freezes and the flip-gate runs — the step that makes V2 flip-eligible (if it wins).
