> **DEPLOYED TO PRODUCTION 2026-06-24.** PR #60 admin-merged (logged bypass, sole-account) → `origin/master` `81e03ee`; manually deployed to prod (`railway up`, auto-deploy not wired) as deploy `255eab8d`, then `ef5c73f4` after the C3 flag flip. Tested merge tree = `24a623e`. Rollback pin = prod deploy `1c1fff96-641`. Prod smoke + live-UI functional test green (crisis EN/AR, D4 answer-first, must-fix reflect-preservation, banned-opener + one-question).
>
> **LIVE in prod:** T1 (Arabic `؟` discipline), T2 (fallback statement), T3 (D4 answer-first), **T4a cooldown (C3 flipped: `SAGE_SKILL_OFFER_COOLDOWN_ENABLED=true`)**.
>
> **APPROVED BUT NOT LIVE — signed ≠ live:** **D5/T5 is approved in principle but the flag is NOT flipped** (`SAGE_D5_ACUITY_GATE` unset in prod → inert). **Task 6 evidence has now been produced** (`2026-06-24-d5-task6-evidence.md`) — but D5 is **still inert**, pending the clinician's **floor pin (7 vs 8) + B1 sign-off on that evidence**. Producing evidence ≠ flipping the gate. Do **not** read "all signatures in" or "Task 6 ran" as "D5 behaviour live." This is the one place signed and live legitimately diverge in this release. **T4b** offer copy (C1) is a separate canary, not in this branch.
>
> **APPROVALS RECORDED 2026-06-24** (relayed by product owner `synergenix.global@gmail.com`, acting approver for PO + clinical): **A1, A2, A3, C2, C3 approved**; sanctioned-merge path approved (user = named approver); staging-smoke run as a hard gate before promote. Release scope: **T1, T2, T3, T4a (cooldown live via C3); T5 shipped inert.**
>
> **Follow-up filed:** Arabic question-stacking (`؟ … ؟`) surfaced by the live test — `docs/superpowers/tickets/2026-06-24-arabic-question-stacking-translate-after-gate.md` (pre-existing translate-after-gate residual, not a regression; resolved by native-Arabic generation).

# Conversational-Style (D4 / D3 / D5) — Decisions & Sign-off Register
**Date:** 2026-06-24 · **For:** product owner + clinical lead
**Plan:** `docs/superpowers/plans/2026-06-24-conversational-style-d3-d4-d5.md` · **Spec:** `docs/superpowers/specs/2026-06-24-conversational-style-d3-d4-d5-design.md`
**Status:** all five code tasks built, individually reviewed, and whole-branch reviewed. Nothing merged, pushed, or deployed. Pre-merge audit A–E complete and green; **full test suite run — branch is regression-free, all 16 remaining failures proven pre-existing on `master`** (§6). T4a cooldown now ships **inert behind a default-off flag** so it can merge without C3, with the flip gated on C3 (§C3/§4). **Nothing ships into an unsigned state.**

---

## 0. How to read this

`master` **auto-deploys to production** on merge. That means **the merge is the last gate** — every behaviour that goes live does so the instant we merge, with no separate "turn it on" step except where a code flag holds it back. So anything user-facing that lands in this release needs its sign-off **before** merge, not after.

The plan is one clean release: **hold everything → collect the signatures below → ship the full reviewed set in one pull request → re-audit → merge → smoke on staging → promote → keep rollback armed.** One bypass, one deploy, one smoke window. The code tree you audited is the tree that merges, so the isolation audit stays valid.

Each decision states: **what you approve**, **who signs**, **what goes live on merge if you approve**, **my recommendation**, and a **decision box**. Recommendations are advisory; the call is yours.

---

## 1. The release plan (agreed)

1. **Hold** all five tasks on branch `feat/2026-06-24-conversational-style` (done — nothing merged).
2. **Collect signatures:** A1, A2, A3, C2, C3 (§2). These are the only blockers for this release.
3. **C3-lag is already handled (done):** the cooldown ships **inert** behind `SAGE_SKILL_OFFER_COOLDOWN_ENABLED` (default OFF, commit `90ec0ac`), so T4a can merge without C3. **The flip to live is the C3 sign-off** — an explicit, logged, signed decision, not an auto-flip (§C3/§4). T5 (D5) ships inert the same way.
4. **One pull request** for the full reviewed set (T1, T2, T3, T4a-inert, T5-inert).
5. **Re-run the full test suite on the final merge commit** (the tree changes once T3 is folded in; §6 numbers are for the current tip). This is non-negotiable — it is what caught the `offer_variation` stale mock (§6.2). Re-confirm the A–E checks on the merge SHA too.
6. **Merge via the sanctioned path (§5):** sole-account → no second reviewer is mechanically available → admin path on `REVIEW_REQUIRED`, with a **named approver** and a full log (approver, SHA, reason, link to the green whole-branch + full-suite audit). This must be the agreed release mechanism, not "how it was done last time." The live-prod boundary is a real gate.
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

### C3 — Offer cooldown value N = 2 (ships inert; flip is this sign-off) · **Signer: Clinical lead**
After Sage offers a coping skill, it will **not** re-offer for **N = 2** turns (stops the repeat-menu feel users flagged). The value lives in the `skill_matching` rule (data, not code); the suppression mechanic is in code (governed by A1).
- **No longer blocks the merge, but still gates the behaviour.** The cooldown now ships **inert** behind `SAGE_SKILL_OFFER_COOLDOWN_ENABLED` (default OFF, commit `90ec0ac`) — when off, behaviour is byte-identical to today (no cooldown). So the code can merge without C3, **but the behaviour does not go live without C3.** Approving C3 is what authorises flipping the flag to ON. The flip is an explicit, logged, signed decision — the same control the merge would have been — **not** an auto-flip. This decouples merge timing from your sign-off; it does **not** route around it.
- **Recommendation:** **Approve N = 2.** Two turns is the lightest cooldown that removes the repeat-offer feel without hiding a genuinely needed second offer. On approval, the flag is flipped (logged) and the cooldown goes live.
- [ ] Approve N = 2 (→ flip flag, logged) · [ ] Set N = ___ · [ ] Hold (code stays inert) · Signer: ____________  Date: ______

---

## 3. Decisions HELD for later (not in this release — sign when we get there)

### B1 — D5 high-intensity behaviour (the one real clinical gate) · **Signer: Clinical lead (standalone)**
At high distress (`emotional_intensity ≥ floor`), Sage will **validate the feeling by naming the specific thing said, and not challenge or question a distorted belief — stay purely supportive.** This replaces the current blunt "do not reflect back" wording, which can read as going cold. The code ships in this release but **inert behind a default-off flag**; it goes live only on this sign-off. Three things to confirm when ready:
1. **Behaviour text** above — approve or amend.
2. **Pin `ACUITY_FLOOR`** — recommend **8** (`emotional_intensity > 7`, matching the existing `validate_only` floor, v7 §9.2 rule 1). Set **7** to cover the entire "high" band. *(At 8, intensity-7 turns keep the standard high guidance.)*
3. **Release evidence** — a dedicated high-intensity regression in **English and Khaleeji Arabic** (planted distortion at/above floor → purely supportive + specific naming, no challenge, no cold filler) as the condition to flip the flag. *(Composition-level EN+AR tests already exist as the first half of this evidence; the live behavioural run is Task 6.)*
   - **Task 6 evidence is now produced and ready for review: `docs/superpowers/governance/2026-06-24-d5-task6-evidence.md`** — three-cell floor 7-vs-8 comparison (EN + Khaleeji), non-endorsement held in every cell, crisis path re-verified unaffected. **Producing this evidence did NOT change D5's status: D5 remains approved-in-principle and INERT, pending your floor pin + sign-off ON this evidence.** "Task 6 ran" is not "D5 live."
- **Clinical decision-support received 2026-06-24 (advisory; clinical-lead sign-off still required).** Recommends, on a Psychological First Aid basis (stabilize before explore; debriefing/event-elaboration probes can backfire at acuity — cite Hobfoll's safety/calmness/efficacy/connectedness/hope in the spec):
  1. **Floor = 7** (D5 ON at intensity 7) — *contingent on condition 4 below.*
  2. **Refined wording** (replaces "stay purely supportive / do not question"): *"validate by naming the specific thing said and do not minimize it; stay supportive and gently normalizing without arguing them out of the feeling; do not challenge the belief and do not ask event-elaboration questions (what happened, why); a present-focused needs-oriented check-in is permitted (how are you managing now, what would help you feel steadier); no reflective opener; no advice/tools yet."* This resolves the C3 trailing-question point (present-focused check-in = right kind; event-elaboration = wrong kind) and the over-normalizing risk.
  3. Single-distortion evidence is **supportive-but-not-sufficient**; flip is gated on **four conditions**, not just transcripts.
- **Four flip conditions (all must clear before `SAGE_D5_ACUITY_GATE=true`):**
  1. **Crisis-gate false-negative rate at the freeflow boundary — HARD PREREQUISITE, not a separate D5 check.** D5 is *downstream* of crisis recall: it only acts on freeflow turns and merely *contains*; a misrouted crisis turn gets containment instead of escalation. This **IS the existing crisis-recall critical path** (CRADLE ~37%/self-harm recall, S2/MARBERT unbuilt, passive-SI unmeasured) that already gates pilot — **tracked as one gate, not two.** **D5 must not flip ahead of crisis recall even if conditions 2–4 are met.** See the binding statement: `2026-06-24-d5-gated-on-crisis-recall.md`. *Live proof: turn-3 passive-SI forced to freeflow was merely contained.* **Not ours to close alone.**
  2. **Multi-turn pushback durability — OPEN, blocked on the L0/L1 budget fix.** This round held per-turn EN+AR, **but the L0-bloat overflow evicted conversation history to 0 turns**, so the case that matters (guardrails degrading across an *accumulating* conversation — the finding that started this tranche) is **unproven**. The **L0 prompt-architecture review is now on D5's critical path** (a blocking dependency for this condition), not a parallel pre-Gitex ticket. Re-run after L0 is fixed.
  3. **Native-clinician review of the AR cells** (cultural fit, not just translation fidelity).
  4. **Intensity classifier confusion at the 6–7 boundary** — narrower than a generic 7-vs-8 A/B: *how often, and in which direction, does the classifier confuse 6 and 7?* If it under-rates genuine acuity as 6, the gate may need to fire lower / the classifier needs work (a bigger finding than 7-vs-8). Floor 7 (PFA basis) is largely direction-independent; this refines it. **No intensity-labeled eval set exists yet** — needs building.
- **Evidence:** `docs/superpowers/governance/2026-06-24-d5-task6-evidence.md` (+ Round 2 + raw transcripts). **D5 remains approved-in-principle and INERT.** The refined wording is applied in-process for evidence only; the committed clinical string changes only on formal sign-off.
- [ ] Approve (floor 7, refined wording, 4 conditions) · [ ] Approve (floor 8) · [ ] Approve with edits: ________ · [ ] Hold · Signer (clinical lead): ____________  Date: ______
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

**Snag 2 — T4a had no inert flag, so N = 2 would go live on merge by side effect. RESOLVED (commit `90ec0ac`).** The cooldown now ships behind `SAGE_SKILL_OFFER_COOLDOWN_ENABLED` (default OFF), exactly like the D5/T5 gate. Effect:
- **Merge timing is decoupled from C3** — the code can land in the PR without C3, inert (byte-identical to today; a unit test proves the off-default).
- **Behaviour is NOT decoupled from C3** — the cooldown only fires once the flag is flipped, and the flip is the C3 sign-off (an explicit, logged, signed decision, §C3). This is deliberately not an auto-flip: a quiet flag-flip would be exactly the kind of unlogged behaviour change the PDPL/v7 audit trail forbids. The flip is gated as explicitly as the merge would have been.
- If you would rather **not** use the flag and instead ship N = 2 live on merge, sign C3 before merge and we leave the flag ON — your call.

---

## 5. Operational decisions (record, not clinical sign-off)

- **Merge mechanics — must be a sanctioned named-approver path, not "how it was done last time."** This is clinical content on a clinical system with auto-deploy, so the merge **is** the deploy. The sole-account repo means a second-reviewer approval is not mechanically available, so the admin path on `REVIEW_REQUIRED` is the only mechanism. For a five-signature clinical change hitting prod on merge, "logged" is necessary but not sufficient — it must be the **agreed release mechanism**, with a **named approver** and the **staging-smoke-then-promote step actually exercised, not assumed.** Decision needed: confirm this is the sanctioned path (or name a second approver if one now exists), and that staging-smoke is a hard gate before promote.
  - [ ] Sanctioned: admin-merge with named approver + log (approver / SHA / reason / link to green whole-branch + full-suite audit) · [ ] Second approver available: ____________
  - [ ] Staging-smoke is a hard gate before promote (not assumed)
- **Rollback pin:** prod deploy `1c1fff96-641` (SUCCESS, 2026-06-24 13:23). Revert = re-pin this deploy on Railway + `git revert` the merge.
- **Two non-negotiables before promote:**
  1. **Full-suite re-audit on the final merge SHA** (after T3 folds in). The `offer_variation` catch (§6) proves why: per-task and batch runs were green; only the full suite surfaced a stale mock against T3's changed signature. The signature-caller audit (§6) confirms that mock was the only stale one, but the full suite on the final SHA is the backstop that proves it for the merged tree, not just the current tip.
  2. **Sanctioned merge path + staging-smoke genuinely run** (above) — the live-prod boundary is a real gate, exercised, not waved through.

---

## 6. Evidence — pre-merge audit A–E (Exhibit A, own-system data)

Run 2026-06-24 on branch tip `90ec0ac` (current tip; the A–E checks below were first run on `abf1f8a` and re-confirmed after the inert-flag + test-mock fixes; **the full suite must be re-run on the final merge commit** per §1.5 and §5).

### 6.1 Pre-merge audit A–E
| | Check | Result |
|---|---|---|
| **A** | Partial-merge isolation | **CLEAN** — all D4 logic lives only in `abf1f8a`; the pre-T3 range `e5edd91..470eb7b` contains zero directive/`info_request` logic. The tree audited is the tree that merges. |
| **B** | "Inert in prod" actually inert | **CLEAN** — production env (`railway variables`, sage-api/production) has **no** `SAGE_D5_ACUITY_GATE` and **no** `SAGE_SKILL_OFFER_COOLDOWN_ENABLED` set → both D5 and the cooldown are OFF by env-absence. T1 touched question-discipline only (6 lines), not banned-opener, translation, or any native-Arabic path. |
| **C** | Existing-session safety on auto-deploy | **SAFE** — `last_offer_turn: Optional[int]`; both readers use `.get()`; a live checkpointed session missing the new channel reads `None` → cooldown is a no-op. No deserialization throw. |
| **D** | Batch + crisis regression | **GREEN** — see 6.2 for the full-suite numbers; 314 crisis/safety tests pass incl. Arabic node-level crisis; both fallbacks clear the banned-opener check (no self-retry loop) and survive stripping unchanged. |
| **E** | Rollback ready | Pin `1c1fff96-641` (SUCCESS, 13:23); staging `sage-api-staging` available for smoke-then-promote. |

### 6.2 Full test suite (the production-readiness gate)
**Branch HEAD: 2407 passed, 12 skipped, 4 xfailed, 16 failed.** **The branch is regression-free — every one of the 16 failures is pre-existing on `master`**, proven by checking each out and running it on `master` itself.

| Failing test(s) | Count | Pre-existing on master? | Proof |
|---|---|---|---|
| `test_wrong_skill_routing::test_full_routing[…]` | 10 | **Yes** | Whole file run on both trees: **10 failed / 240 passed, identical**. Known deferred wrong-skill gaps (post-Gitex). |
| `test_graph::test_extended_session_15_turns`, `…::test_post_crisis_monitoring_routes_safe_and_activates_skill` | 2 | **Yes** | Both fail when run from `master` source. |
| `test_skill_routing_ba_pd::test_no_new_substring_keyword_shadowing` | 1 | **Yes** | Fails from `master` source. |
| `test_output_gate_offer_voiding::test_empty_response_on_retry_voids_offer_created_this_turn` | 1 | **Yes** | Fails from `master` source; test last touched 2026-06-14 (#4). |
| `test_prompts_composer::test_compose_prompt_no_overflow_with_large_cultural_override` | 1 | **Yes** | Fails from `master` source; test last touched 2026-06-23 (stall-guard). |
| `test_entry_screen_integration::…test_ar_therapeutic_acceptance_advances_act` | 1 | **Yes (flake)** | **Passes in isolation on both** trees; only fails in the full run (LLM non-determinism / ordering), not a deterministic defect. |

**Regression found and fixed during this audit (the reason the full-suite step is non-negotiable):** 4 `test_offer_variation` tests passed on `master` but failed on the branch. Cause: T3 added a `primary_intent` kwarg to `detect_directive_request`, and `test_offer_variation`'s `_route` helper still mocked the old signature (`lambda s: False`) → `TypeError`. **Production code was correct; the stale mock was the bug.** Fixed in `d33f53b`. A targeted signature-caller audit then confirmed this was the **only** stale mock: `detect_directive_request` has exactly one production caller (correct) and one mock (now fixed); T3 changed no other signature; the new kwarg has a default so all direct callers stay compatible.

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
