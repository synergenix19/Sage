# Batched Clinical Review Session Brief

**Date prepared:** 2026-06-13
**For:** Clinical lead (+ Rule 1 approver where a routing/control change is implied)
**Source:** PR #4 engagement audit register + sign-off alignment check
**Purpose:** four findings that each need a clinical decision, batched into one session so the clinical team gets one coherent queue instead of a drip. Items are ordered by clinical severity, not tractability.
**Estimated time:** ~60–90 min. Two items (S2-10, bucketing) arrive partly pre-answered by evidence; two (S2-7, S2-4) are open clinical calls.

## How this session fits the merge / launch path

Three human tracks for the PR #4 merge run **in parallel**, not in sequence — kick all three off at once or the merge slips by their sum rather than the max:
1. Four non-gated clinical sign-offs (proceed independently of this session).
2. The **acute-substitution re-decision** (escalation doc; gates the fifth sign-off, `skill_matching_rules.json`).
3. The **two-rater scoring upgrade** (gates the English offer-turn sign-off evidence + Arabic exposure; the Khaleeji calibration is the long pole — start it today).

**This session naturally absorbs track 2.** The acute-substitution re-decision and item C below (keyword bucketing) are the *same* clinical question — the acute skill set and its priority order — so take them together here. The session also clears the safety queue (S2-10) and two product-quality items (S2-7, S2-4). Decisions captured here unblock track 2 and the post-merge work queue.

## Decisions-needed summary

| # | Item | Clinical severity | Decision in one line | Evidence status |
|---|---|---|---|---|
| A | S2-10 psychotic-referral reachability | **Highest (safety)** | Confirm: interrupt next turn; deterministic routing is the gate, not prompting | 2 of 3 questions evidence-answered |
| B | S2-7 ungoverned freeflow exercise delivery | High (consent + contraindication bypass) | Where is the boundary between supportive suggestion and governed-only protocol delivery? | Open clinical call |
| C | Keyword bucketing (+ acute pool order) | Medium (acute routing correctness + unsigned content) | Which acute skill owns panic-breathing symptoms? Sign off or revert the unaudited edits | Partly factual, partly clinical |
| D | S2-4 R5 budget shadowed by hold rules | Lower (pacing UX) | Are deterministic clinical holds senior to the pacing budget by design? | Open clinical call |

---

## A — S2-10: psychotic-referral reachability (SAFETY — highest)

**Finding.** The `psychotic_referral` skill auto-selects only on routing paths that reach `skill_select`. A user who discloses psychotic symptoms and then keeps chatting in ordinary register routes to freeflow, which engaged with the content unreferred — in the live audit it asked *"what did the voices say?"*. Pre-existing on master; the engagement branch did not cause it. Full detail + evidence: `docs/superpowers/escalations/2026-06-13-psychotic-referral-reachability.md`.

**Why it matters clinically.** This is the most clinically serious item in the register. The documented failure mode for LLMs with psychotic content is delusion *reinforcement* (Stanford FAccT 2025: inappropriate responses ≥20% even in therapy-tuned bots; "Psychogenic Machine" arXiv 2509.10970: delusion-confirmation 0.91, no safety intervention in ~40% of scenarios). Every un-redirected turn is a draw from that distribution. Separately, delay to real-world care worsens outcomes (duration-of-untreated-psychosis literature).

**Decisions required.**
- **A1 (timing) — evidence recommends: interrupt on the NEXT turn**, regardless of topic, as a *warm interrupt* (validate the emotion, do not explore or argue the content, connect to help), not a conversation kill. Clinical lead to confirm or override. *Direct head-to-head outcome data for "next turn vs within N turns" does not exist; the recommendation rests on per-turn failure rates + DUP harms + OpenAI's 170-clinician spec, which routes within the response.*
- **A2 (interim) — evidence recommends: L5 prompt adaptation alone is NOT an acceptable interim safety mechanism** (it is the configuration that already failed in the audit). Deterministic routing is the gate; prompt adaptation is defense-in-depth on the redirect's *wording* only. Clinical lead to confirm whether pilot exposure must wait on the routing fix, or whether a strengthened interim is acceptable and on what terms.
- **A3 (content) — approve the redirect approach and authorize the referral phrasing/resources** (the warm-interrupt wording the implementation will use).
- *A4 (engineering, FYI not a clinical call): one-off clinical-flag branch vs a general flag-routing table — engineering design choice; noted so the table option isn't accidentally foreclosed.*

**On decision →** engineering implements the `_route_after_intent` clinical-flag branch under the normal Rule 1 + clinical gate; this session supplies the clinical half.

**Decision capture**
- A1 timing: ☐ next turn ☐ within N turns (N = ___) ☐ other — reasoning: __________
- A2 interim: ☐ pilot waits on routing fix ☐ strengthened interim acceptable (terms: ______) — reasoning: __________
- A3 referral phrasing/resources approved: ☐ yes ☐ revisions: __________

---

## B — S2-7: ungoverned freeflow exercise delivery (consent + contraindication bypass)

**Finding.** Freeflow can deliver a structured exercise as free prose, with no executor, no step tracking, and **no entry-screen**. Observed twice in the audit: a declined `box_breathing` was then delivered as a full breathing walkthrough in prose (D2); a user who named a skill after a missed accept got a complete self-compassion exercise via freeflow, ungoverned (Arabic ar-04). The consent/safety rails govern *state* (which skill is active), not *content* (what the LLM says).

**Why it matters clinically.** Two harms. (1) Consent: a user who declined the structured skill gets its content anyway, which partly defeats the consent gate's purpose. (2) The sharper one — contraindication bypass: the entry screens exist to catch contraindications (e.g., breathing work activating for a trauma survivor; PMR with a pain/injury; TIPP cold-water cautions). Prose delivery routes around that screening entirely. This is pre-existing capability that R1 made more visible.

**Decisions required.**
- **B1 (boundary).** Where is the line between (i) general supportive coping language freeflow may always offer, and (ii) step-by-step protocol delivery that should only happen inside a governed skill with its entry screen? Concretely: should freeflow be instructed never to deliver a named skill's step sequence as prose — especially for skills that carry an entry screen, and especially for a skill declined this session?
- **B2 (declined-skill signal).** Should the composer actively signal declined skills to freeflow so it avoids re-delivering declined content?
- **B3 (severity).** Is this a pre-pilot blocker, or a logged item for after the engagement merge? (Clinical call — it is pre-existing, but it intersects the contraindication safety surface.)

**Engineering view (not the clinical call).** Implementable as a freeflow guardrail instruction (persona/L0 or a freeflow-specific block) plus a declined-skills composer signal; both need clinical wording. The boundary in B1 is the hard part and is genuinely a clinical judgment, not an engineering one.

**Decision capture**
- B1 boundary: __________ (and: forbid prose delivery of entry-screen skills? ☐ yes ☐ no)
- B2 declined-skill signal to freeflow: ☐ yes ☐ no — reasoning: __________
- B3 severity: ☐ pre-pilot blocker ☐ logged post-merge — reasoning: __________

---

## C — Keyword bucketing + acute pool order (acute routing + unsigned content)

**Finding — two sub-items.**

**C(i) — which acute skill owns panic-breathing symptoms.** Panic/somatic phrases are owned by `grounding_5_4_3_2_1`: `"can't breathe"`, `"heart racing"`, `"heart is pounding"`, and the Khaleeji `"قلبي يدق"`, `"ما أقدر أتنفس"`. `"can't calm down"` is owned by `dbt_tipp`. `box_breathing` owns explicit-breathing-request phrases (`"help me breathe"`, `"box breathing"`, `"calm my breathing"`). All three are in the acute set, so `acute_direct_entry` fires regardless of which — but *which acute skill the user enters* depends on this ownership + longest-keyword match. In the audit, "heart is pounding" (grounding) won over "can't calm down" (dbt_tipp); a user saying "I can't breathe" enters grounding, not box_breathing.

**C(ii) — unsigned keyword edits live in production.** Four `target_presentations` edits (commits d234ec6, 8433410) merged without clinical sign-off. Highest priority: `interpersonal_effectiveness` "setting limits in" and `box_breathing` "do with my breathing". These need a governance entry (sign-off) or a revert.

**Why it matters clinically.** C(i) is acute-response appropriateness — is grounding the right first technique for someone reporting "can't breathe"/"heart racing", or should breathing-symptom language route to box_breathing? C(ii) is unsigned clinical content currently shaping live routing.

**Decisions required.**
- **C1.** Confirm the intended acute-skill owner for panic-breathing symptoms ("can't breathe", "heart racing", and Arabic equivalents): keep with `grounding_5_4_3_2_1` (current) or move to `box_breathing`? **This decision also sets the substitution-pool order in the held acute amendment (item below) — the pool order is the clinical priority order for acute down-regulation.** Take this with the acute re-decision.
- **C2.** Sign off or revert the unaudited edits (d234ec6, 8433410) — specifically IE "setting limits in" and BB "do with my breathing".

**Linked: the held acute-substitution re-decision.** `docs/superpowers/escalations/2026-06-13-acute-substitution-redecision.md` asks the clinical lead to (a) replace `ignore_declined` with substitution-within-the-acute-set, and (b) affirm that the four acute skills are clinically substitutable for acute down-regulation, setting the substitution order. C1 here *is* the ordering input for that pool. Decide them together.

**Decision capture**
- C1 panic-breathing owner: ☐ grounding (keep) ☐ box_breathing (move) — reasoning: __________
- Acute pool substitution order (default `box_breathing, grounding, stop_technique, dbt_tipp`): __________
- Four acute skills substitutable for acute down-regulation? ☐ affirmed ☐ not freely substitutable (constraints: ______)
- C2 unaudited edits: ☐ sign off (IE "setting limits in", BB "do with my breathing") ☐ revert ☐ mixed: __________

---

## D — S2-4: R5 pacing budget shadowed by deterministic hold rules (pacing UX)

**Finding.** The R5 `criteria_hold_budget` (advance after one criteria-not-met hold) is structurally bypassed by deterministic step_policy hold rules. `mood_check_in` carries `criteria_hold_budget: 1` AND a rule `emotional_intensity <= 3 @ score_mood → hold_and_explore`. Terse answers ("ok") classify as low intensity, the rule fires in Phase 1 and returns *before* the budget branch is reached, and `criteria_hold_count` does not increment on rule-holds — so a terse low-mood user can be held at the mood-score step indefinitely. (In practice `hold_and_explore` varies its wording, so it doesn't read as a broken loop, but the user is not advanced.)

**Why it matters clinically.** Lowest clinical stakes of the four (pacing, not safety), but it is a real loop and the decision is genuinely clinical, not engineering: for a low-mood user giving minimal answers, is continued gentle exploration the *right* behavior (a withdrawn low-mood user may need drawing out, not advancing), or should the system stop re-asking and move forward after a couple of attempts?

**Decisions required.**
- **D1 (mood_check_in specific).** When a low-mood user gives minimal answers at the mood-score step, should `hold_and_explore` keep gently exploring (current), or should the pacing budget advance them after N holds?
- **D2 (general principle).** Should deterministic clinical hold rules be *senior* to the R5 pacing budget by design (clinical holds outrank pacing — current behavior), or should they count toward / be capped by the budget for uniform pacing?

**Engineering view (not the clinical call).** Two implementable options: (i) leave as-is — clinical holds senior, budget applies only to criteria-not-met holds, not rule-holds (defensible; arguably a withdrawn low-mood user *should* be drawn out); or (ii) make rule-holds increment the counter so the budget caps them (uniform pacing, but it caps a clinically-motivated hold). **If the answer is (i), the recommendation is to document it as an intentional clinical design choice rather than leave it as an accident of evaluation order** — so a future audit sees a decision, not a gap.

**Decision capture**
- D1 mood_check_in low-mood terse user: ☐ keep exploring ☐ advance after N holds (N = ___) — reasoning: __________
- D2 clinical holds vs budget: ☐ clinical holds senior (document as intentional) ☐ budget caps rule-holds — reasoning: __________

---

## After the session

- A → routing fix implemented under Rule 1 + clinical gate; pilot-exposure decision recorded.
- B → freeflow guardrail + composer signal drafted to the agreed boundary (or logged with severity).
- C1 → sets the acute substitution-pool order; unblocks the held acute amendment and the `skill_matching_rules.json` sign-off. C2 → sign-off recorded or edits reverted.
- D → behavior confirmed or changed; if "senior by design," documented as intentional.

Every decision above should capture the **reasoning**, not just the choice — a future auditor (and the planned external pre-launch audit) needs a considered call on record, not a bare verdict. This is especially load-bearing for A (safety) and for the linked acute re-decision.
