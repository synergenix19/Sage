# Conversational-Style (D4 / D3 / D5) — Decisions & Sign-off Register
**Date:** 2026-06-24 · **For:** product owner + clinical lead
**Plan:** `docs/superpowers/plans/2026-06-24-conversational-style-d3-d4-d5.md` · **Spec:** `docs/superpowers/specs/2026-06-24-conversational-style-d3-d4-d5-design.md`
**Status:** all five code tasks built, individually reviewed, and whole-branch reviewed. Nothing merged, pushed, or deployed. Pre-merge audit A–E complete and green (§6). **Nothing ships into an unsigned state.**

---

## 0. How to read this

`master` **auto-deploys to production** on merge. That means **the merge is the last gate** — every behaviour that goes live does so the instant we merge, with no separate "turn it on" step except where a code flag holds it back. So anything user-facing that lands in this release needs its sign-off **before** merge, not after.

The plan is one clean release: **hold everything → collect the signatures below → ship the full reviewed set in one pull request → re-audit → merge → smoke on staging → promote → keep rollback armed.** One bypass, one deploy, one smoke window. The code tree you audited is the tree that merges, so the isolation audit stays valid.

Each decision states: **what you approve**, **who signs**, **what goes live on merge if you approve**, **my recommendation**, and a **decision box**. Recommendations are advisory; the call is yours.

---

## 1. The release plan (agreed)

1. **Hold** all five tasks on branch `feat/2026-06-24-conversational-style` (done — nothing merged).
2. **Collect signatures:** A1, A2, A3, C2, C3 (§2). These are the only blockers for this release.
3. **If C3 lags** the others: I add a default-off flag to the cooldown (T4a) so it rides the release **inert** and flips later on a short C3 sign-off — same pattern as D5/T5. (Contingency, §4.)
4. **One pull request** for the full reviewed set (T1, T2, T3, T4a, T5-inert).
5. **Re-run audit A–E on the final merge commit** (the tree changes once T3 is folded in; the A-result in §6 is for the current tip and must be re-verified on the actual merge SHA).
6. **Merge.** Repo is sole-account, so a second-reviewer approval is not mechanically available; merge uses the admin path on `REVIEW_REQUIRED` — **logged** (approver, SHA, reason, link to the green whole-branch review), per standing practice. This is the operational-reality exception, not a judgment override.
7. **Staging smoke** on `sage-api-staging`: a handful of §9 audit-replay IDs + a crisis probe in **English and Khaleeji Arabic** + an empty-response probe (to exercise the T2 fallback).
8. **Promote** to production. **Rollback armed** on prod deploy pin `1c1fff96-641` (the current SUCCESS deploy) for the smoke window.
9. **Held, not in this release:** T4b offer copy (C1 + canary), T5 flag flip (B1 + EN/AR regression), Task 6 behavioural acceptance.

---

## 2. Decisions that BLOCK this release (please sign)

> What ships in this release: **T1** Arabic question-mark fix, **T2** fallback-copy fix, **T3** answer-first (D4), **T4a** offer cooldown (D3), **T5** D5 acuity gate **shipped inert** (default-off flag, no behaviour change in prod).

### A1 — Behavioural gates live in engineer code (POC) · **Signer: Product owner**
Three conversational gates stay as Python node logic, not clinician-editable rules, because the current rules schema is blocklist/substitute-only and cannot count, trim, or pattern-match: **question-discipline** (one-question + trailing-question strip), **directive-detect**, and the **banned-opener** check. This is the **same deviation already accepted for the shipped advice-posture work (PR#25)**. This release **extends** it in two ways, both covered by this signature:
- **T3 (D4):** adds an `info_request` trigger to directive-detect (answer-first when the user wants information).
- **T1:** makes the question-discipline strip language-aware (handles the Arabic question mark `؟`, not only `?`). *This edits the very mechanic A1 governs, so T1 rides this approval. (The implementation plan called T1 "no precondition"; that is superseded — T1 is governed by A1. See snag 1, §4.)*
The clinical **values** still live in data (offer-cooldown N in the rules, D5 floor in config). Full-build migration of the mechanics into the Rules Service is ticketed (A2).
- **Recommendation:** **Approve.** The mechanic-vs-value split is correct and consistent with PR#25; T1 is a correctness fix to an already-approved mechanic, not a new behaviour.
- [ ] Approve · [ ] Approve with conditions: ________ · [ ] Hold
- Signer: ____________  Date: ______

### A2 — Assign the #22 LOCK-QDISC-22 owner · **Signer: Product owner / Eng lead**
#22 is the already-agreed **hard-condition** full-build task: add a `structural_output` rules schema so question-discipline migrates out of code into the clinician-editable Rules Service. Its owner line is currently blank. Assign an owner (no work now; post-POC).
- **Recommendation:** **Assign now** so the full-build commitment is not orphaned. The deviation in A1 is acceptable *because* this migration is owned.
- Owner assigned: ____________  · Date: ______

### A3 — Banned-opener phrase set is therapeutic content · **Signer: Clinical lead**
The phrases Sage is blocked from opening with (they read as generic filler) are a clinical judgment that currently sits in code. A clinician should own and sign the list now, even while it stays in code (it is first to migrate under #22). Current set: reflective fillers ("it sounds like", "that sounds tough/hard/…", "it seems like", "I can hear/see…", "it looks like"), praise-openers ("that's great/good to hear", "I'm glad to hear"), and sympathy-openers ("I'm sorry to hear/that/you…", "so sorry").
- **Recommendation:** **Approve as-is**; add or remove phrases here if clinically warranted.
- [ ] Approve as-is · [ ] Approve with edits: ________ · Signer: ____________  Date: ______

### C2 — Fallback message copy (goes live this release) · **Signer: Clinical lead**
When generation fails, Sage shows a vetted fallback. T2 changes it from a **question** to a **statement** so the downstream answer-first stripping cannot gut it into a bare fragment. New wording, served to users on merge:
> "I'm here with you, and what you've shared matters. Take a moment, I'm listening whenever you're ready."
(Replaces: "I'm here with you. What would feel most helpful to share right now?")
- **Why this is a blocking sign-off:** auto-deploy makes this user-facing therapeutic copy live on merge. *(This was listed as non-blocking in the prior draft; that was written before the auto-deploy implication was accounted for. It blocks.)*
- **Recommendation:** **Approve** — it fixes a live bug (the old question could be stripped to "I'm here with you.") and reads as warm presence, not a prompt.
- [ ] Approve · [ ] Approve with edits: ________ · Signer: ____________  Date: ______

### C3 — Offer cooldown value N = 2 (goes live this release) · **Signer: Clinical lead**
After Sage offers a coping skill, it will **not** re-offer for **N = 2** turns (stops the repeat-menu feel users flagged). The value lives in the `skill_matching` rule (data, not code); the suppression mechanic is in code (governed by A1).
- **Why this is a blocking sign-off:** there is currently **no flag holding this inert**, so merging makes N = 2 live immediately (see snag 2, §4). If you approve, it ships live; if it lags, see the §4 contingency.
- **Recommendation:** **Approve N = 2.** Two turns is the lightest cooldown that removes the repeat-offer feel without hiding a genuinely needed second offer.
- [ ] Approve N = 2 · [ ] Set N = ___ · [ ] Hold (→ ship inert via §4 flag) · Signer: ____________  Date: ______

---

## 3. Decisions HELD for later (not in this release — sign when we get there)

### B1 — D5 high-intensity behaviour (the one real clinical gate) · **Signer: Clinical lead (standalone)**
At high distress (`emotional_intensity ≥ floor`), Sage will **validate the feeling by naming the specific thing said, and not challenge or question a distorted belief — stay purely supportive.** This replaces the current blunt "do not reflect back" wording, which can read as going cold. The code ships in this release but **inert behind a default-off flag**; it goes live only on this sign-off. Three things to confirm when ready:
1. **Behaviour text** above — approve or amend.
2. **Pin `ACUITY_FLOOR`** — recommend **8** (`emotional_intensity > 7`, matching the existing `validate_only` floor, v7 §9.2 rule 1). Set **7** to cover the entire "high" band. *(At 8, intensity-7 turns keep the standard high guidance.)*
3. **Release evidence** — a dedicated high-intensity regression in **English and Khaleeji Arabic** (planted distortion at/above floor → purely supportive + specific naming, no challenge, no cold filler) as the condition to flip the flag. *(Composition-level EN+AR tests already exist as the first half of this evidence; the live behavioural run is Task 6.)*
- **Recommendation:** approve the behaviour + `ACUITY_FLOOR = 8` + the EN/AR regression gate.
- [ ] Approve (floor 8) · [ ] Approve (floor 7) · [ ] Approve with edits: ________ · [ ] Hold · Signer: ____________  Date: ______
- **Interim:** until B1 is signed, the current "do not reflect back" wording stays live (functional, just blunt). [ ] Interim acceptable · [ ] Want a faster standalone wording correction

### C1 — Offer copy (Task 4b, separate canary) · **Signer: Clinical lead**
`skill_offer.json`: drop the fixed "Ask which they would prefer?" close; the offer becomes one woven suggestion, not a menu. This edits a **live, clinician-approved template**, so it ships as its own draft → review → canary change, not in this release.
- **Recommendation:** Approve, then canary.
- [ ] Approve · [ ] Approve with edits: ________ · Signer: ____________  Date: ______

### Task 6 — Behavioural acceptance (staging) · **Owner: Eng + Clinical**
The live EN/AR behavioural run that is both D5's flip evidence (B1.3) and the end-to-end check that all five behaviours hold on staging against real conversations. Runs after merge, on staging.
- Not a signature; a gate on the T5 flip and on declaring the tranche behaviourally accepted.

---

## 4. The two snags found in audit, and how they clear

**Snag 1 — T1 edits the gate A1 governs.** T1's Arabic `؟` fix modifies the question-discipline mechanic that A1's Rule-1 deviation covers. The implementation plan said "T1 no precondition"; the governance position is that T1 is governed by A1. **Resolution:** A1 (above) now explicitly covers T1. Signing A1 clears T1 and T3 together. No separate action.

**Snag 2 — T4a has no inert flag, so N = 2 goes live on merge by side effect.** Unlike D5 (which ships behind a default-off flag), the cooldown has no off-switch; merging makes the C3 value live immediately. **Resolution, in order of preference:**
1. **Sign C3** (cheap, recommended) — then N = 2 ships live as an approved value. No code change.
2. **If C3 lags:** I add `SAGE_SKILL_OFFER_COOLDOWN_ENABLED` (default **false**), so T4a rides the release inert and flips later on a one-line C3 sign-off — identical to the D5/T5 pattern. (Small, reviewed code change; re-audit covers it.)
3. **Explicit "provisional N = 2 live" call** by PO + clinical — only if you want it live before formal C3.

---

## 5. Operational decisions (record, not clinical sign-off)

- **Merge mechanics — logged bypass.** Sole-account repo → no second approver is mechanically available → the admin path on `REVIEW_REQUIRED` is the only way to merge. Treat as the operational-reality exception: **log** approver (you), merge SHA, reason ("sole-account, no second reviewer"), and a link to the green whole-branch review. Compensate for the absent human gate with the staging smoke (§1.7) and armed rollback (§1.8). Confirm this is acceptable, or name a second approver if one now exists.
  - [ ] Logged-bypass acceptable (sole-account) · [ ] Second approver available: ____________
- **Rollback pin:** prod deploy `1c1fff96-641` (SUCCESS, 2026-06-24 13:23). Revert = re-pin this deploy on Railway + `git revert` the merge.
- **Re-audit on final SHA:** mandatory before promote (§1.5).

---

## 6. Evidence — pre-merge audit A–E (Exhibit A, own-system data)

Run 2026-06-24 on branch tip `abf1f8a` (current tip; **must be re-run on the final merge commit** per §1.5).

| | Check | Result |
|---|---|---|
| **A** | Partial-merge isolation | **CLEAN** — all D4 logic lives only in `abf1f8a`; the pre-T3 range `e5edd91..470eb7b` contains zero directive/`info_request` logic. The tree audited is the tree that merges. |
| **B** | "Inert in prod" actually inert | **CLEAN** — production env has no `SAGE_D5_ACUITY_GATE` (D5 off by env-absence); T1 touched question-discipline only (6 lines), not banned-opener, translation, or any native-Arabic path. |
| **C** | Existing-session safety on auto-deploy | **SAFE** — `last_offer_turn: Optional[int]`; both readers use `.get()`; a live checkpointed session missing the new channel reads `None` → cooldown is a no-op. No deserialization throw. |
| **D** | Batch + crisis regression | **GREEN** — 359 batch tests pass (the 2 failures are pre-existing on master, out of scope); 314 crisis/safety tests pass incl. Arabic node-level crisis; both fallbacks clear the banned-opener check (no self-retry loop) and survive stripping unchanged. |
| **E** | Rollback ready | Pin `1c1fff96-641`; staging `sage-api-staging` available for smoke-then-promote. |

*The 2 pre-existing master failures (`test_output_gate_offer_voiding::test_empty_response_on_retry_voids_offer_created_this_turn`, `test_prompts_composer::test_compose_prompt_no_overflow_with_large_cultural_override`) are independent of this branch and tracked separately.*

---

## 7. File as tickets (no approval — tracking only)

- **Post-merge (Minor, from final review):** add `last_offer_turn = None` to the 4-hour stale-gap reset alongside the existing offer-state clears, so a returning user (4h+ gap) whose prior session ended on an offer cannot have a fresh offer suppressed. Graceful today (falls through to freeflow), narrow trigger.
- **#22 LOCK-QDISC-22:** migrate question-discipline / directive-detect / banned-opener into a `structural_output` rules schema (owner per A2).
- **Architecture-doc debt:** `SageAI_architecture_current.md` stale on L0 version/budget (says v1.4.0; live v2.3.0); owed v8 "§17 Architecture Evolution" ratification entry.
- **L0 prompt-budget review:** L0 is ~633 words live vs ~150 ratified (~4× the always-on budget); a prompt-architecture review is plausibly higher long-session-reliability leverage than these tone fixes.

---

## 8. Routing summary

| Signer | Blocks this release | Held for later |
|---|---|---|
| **Product owner** | **A1** (Rule-1 deviation, covers T1+T3), **A2** (#22 owner), §5 logged-bypass | — |
| **Clinical lead** | **A3** (banned-opener set), **C2** (fallback copy), **C3** (cooldown N=2) | **B1** (D5 flip — the big one), **C1** (offer copy) |

**Minimum to ship the full reviewed set:** A1 + A2 + A3 + C2 + C3 (+ logged-bypass acknowledgement). If C3 lags, ship inert via the §4 flag and sign C3 later. **B1, C1, Task 6 stay held.**
