# Conversational-Style (D4/D3/D5) — Governance Sign-off Sheet
**Date:** 2026-06-24 · **For:** product owner + clinical lead · **Plan:** `docs/superpowers/plans/2026-06-24-conversational-style-d3-d4-d5.md` · **Spec:** `…/specs/2026-06-24-conversational-style-d3-d4-d5-design.md`

**How to read this:** three gates. **Gate 1** unblocks *merging* the D3/D4 tranche. **Gate 2** is the one real clinical gate, it unblocks *turning on* D5. **Gate 3** is clinical copy that rides an existing review gate. Each item: what you approve, who signs, my recommendation, a decision box. Nothing here is live until signed.

---

## GATE 1 — unblocks merging Tasks 1–4 (D3/D4: answer-first + de-script + Arabic question-mark fix)

### A1 — Rule-1 deviation: behavioural gates live in engineer code (POC)  ·  **Signer: Product owner**
We keep three conversational gates as Python node logic, not clinician-editable rules, because the current rules schema is blocklist/substitute-only and can't count/trim/regex: question-discipline (one-question + trailing-question strip), directive-detect, and the banned-opener check. This is the **same deviation already accepted for the shipped advice-posture work (PR#25)** — D4 *extends* it (adds the `info_request` trigger). The existing Rule-1 governance lines were left blank; this signs them, now covering the extension.
- **Recommendation:** approve. The mechanic-vs-value split is correct; the clinical *values* (offer-cooldown, D5 floor) DO live in data; full-build migration is ticketed (see A2).
- [ ] Approve  · [ ] Approve with conditions: ______ · [ ] Hold
- Signer: __________  Date: ______

### A2 — Assign the #22 LOCK-QDISC-22 owner  ·  **Signer: Product owner / Eng lead**
#22 is the already-agreed **HARD-condition** full-build task to add a `structural_output` rules schema so question-discipline migrates out of code into the clinician-editable Rules Service. It currently has **"Named owner: ____" blank**. Assign an owner (no work now, post-POC).
- **Recommendation:** assign now so the full-build commitment isn't orphaned.
- Owner assigned: __________  · Date: ______

### A3 — Banned-opener pattern set is therapeutic content  ·  **Signer: Clinical lead**
The list of phrases Sage is blocked from opening with (because they read as generic filler) is a clinical judgment that currently sits in code. A clinician should own + sign it now, even while it stays in code (first to migrate under #22). Current set: reflective fillers ("it sounds like", "that sounds tough/hard/…", "it seems like", "I can hear/see…", "it looks like"), praise-openers ("that's great/good to hear", "I'm glad to hear"), and sympathy-openers ("I'm sorry to hear/that/you…", "so sorry").
- **Recommendation:** approve the set as-is; add/remove phrases here if clinically warranted.
- [ ] Approve as-is · [ ] Approve with edits: ______ · Signer: __________  Date: ______

> **Gate 1 cleared (A1+A2+A3) → Tasks 1, 2, 4 merge, and Task 3 (D4) merges.**

---

## GATE 2 — the real clinical gate: turning ON D5 (peak-distress behaviour)  ·  **Signer: Clinical lead (standalone)**

### B1 — D5 high-intensity acuity edit
At high distress (`emotional_intensity ≥ floor`), Sage will: **validate the feeling by naming the specific thing said, and NOT challenge or question a distorted belief — stay purely supportive.** This replaces the current high-intensity instruction's blunt "do not reflect back" wording (which can read as going cold). It edits the **highest-stakes path in the tranche**, so it ships behind a default-OFF flag and goes live only on this sign-off. Three things to confirm:
1. **Behaviour text** above — approve / amend wording.
2. **Pin `ACUITY_FLOOR`** — recommend **8** (`emotional_intensity > 7`, matching the existing `validate_only` floor, v7 §9.2 rule 1). Set to **7** instead if you want it to cover the entire "high" band. *(At 8, intensity-7 turns get the standard high guidance, not the challenge-suppress.)*
3. **Release evidence** — accept a dedicated high-intensity regression run in **English and Khaleeji Arabic** (planted distortion at/above floor → purely supportive + specific naming, no challenge, no cold filler) as the condition to flip the flag.
- **Recommendation:** approve the behaviour + `ACUITY_FLOOR = 8` + the EN/AR regression gate. (Belief *detection* stays prompt-led; this gate is the deterministic acuity guarantee.)
- [ ] Approve (floor = 8) · [ ] Approve (floor = 7) · [ ] Approve with edits: ______ · [ ] Hold
- Signer: __________  Date: ______

> **Note:** until B1 is signed and flipped, the current high-intensity "do not reflect back" wording stays live (it is functional, just blunt). Confirm that interim is acceptable, or request a faster standalone wording correction.
- [ ] Interim acceptable · [ ] Want faster correction

---

## GATE 3 — clinical copy (rides the existing `draft-pending-review` gate; needed before those templates go live, not blocking code merge)  ·  **Signer: Clinical lead**

| Item | What changes | Recommendation | Decision |
|---|---|---|---|
| **C1 — offer copy** | `skill_offer.json`: drop the fixed "Ask which they would prefer?" closing question; offer becomes one woven suggestion, not a menu. | Approve | ☐ approve ☐ edit: ___ |
| **C2 — fallback copy** | New `_VETTED_FALLBACK_RESPONSE` (a warm *statement*, not a question, so it can't be gutted): "I'm here with you, and what you've shared matters. Take a moment, I'm listening whenever you're ready." | Approve (fixes a live bug) | ☐ approve ☐ edit: ___ |
| **C3 — offer cooldown N** | Suppress a fresh skill offer for **N=2** turns after one was made (stop the repeat-menu feel). Value lives in the `skill_matching` rule. | Approve N=2 | ☐ approve ☐ set N=___ |

Signer: __________  Date: ______

---

## FILE AS TICKETS (no approval needed — tracking only)
- 3 architecture divergences: (1) `sage-poc/docs` vs `sage-poc-phase0/docs` governance trees diverge; (2) `SageAI_architecture_current.md` stale on L0 version/budget (says v1.4.0; live v2.3.0); (3) owed v8 "§17 Architecture Evolution" ratification entry.
- **L0 prompt-budget review** (separate pre-Gitex item): L0 is ~600 words live vs ~150 ratified (≈4× the always-on budget). Recommend a prompt-architecture review — plausibly higher long-session-reliability leverage than these tone fixes.

---

## Summary for routing
- **Product owner:** A1 (Rule-1 deviation), A2 (assign #22 owner).
- **Clinical lead:** A3 (banned-opener list), **B1 (D5 high-intensity — the big one)**, C1/C2/C3 (copy + cooldown).
- **Minimum to start shipping today:** A1 + A2 + A3 → Tasks 1/2/4 merge now (Arabic `؟` fix, Bug A, de-script cooldown); Task 3 (answer-first) merges on the same gate. **B1 is the only item gating D5**, and it can follow in parallel.
